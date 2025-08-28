import boto3
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# AWS clients
s3 = boto3.client('s3')

# Default configuration
DEFAULT_CONFIG = {
    "MAX_THREADS": 10,
    "BUCKET_FILTER_PREFIX": "",
    "REPORT_OUTPUT_S3_BUCKET": ""
}

def load_config(bucket_name, key="config.json"):
    """Load JSON config from S3; return defaults if not present."""
    try:
        resp = s3.get_object(Bucket=bucket_name, Key=key)
        config_data = json.loads(resp['Body'].read())
        print(f"Loaded config from {bucket_name}/{key}: {config_data}")
        return {**DEFAULT_CONFIG, **config_data}  # merge defaults
    except s3.exceptions.NoSuchKey:
        print(f"Config file {key} not found in {bucket_name}, using defaults.")
        return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config from S3: {e}. Using defaults.")
        return DEFAULT_CONFIG

def get_bucket_size(bucket_name):
    try:
        size = 0
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                size += sum(obj['Size'] for obj in page['Contents'])
        return bucket_name, size
    except Exception as e:
        print(f"Error accessing bucket {bucket_name}: {e}")
        return bucket_name, 0

def lambda_handler(event, context):
    start_time = time.time()

    # Read configuration from S3 if provided
    config_bucket = event.get("config_s3_bucket")
    if config_bucket:
        config = load_config(config_bucket)
    else:
        config = DEFAULT_CONFIG
        print("No config_s3_bucket provided, using defaults.")

    max_threads = config.get("MAX_THREADS", 10)
    prefix_filter = config.get("BUCKET_FILTER_PREFIX", "")
    report_output_bucket = config.get("REPORT_OUTPUT_S3_BUCKET", "")

    try:
        buckets_response = s3.list_buckets()
        buckets = [b['Name'] for b in buckets_response.get('Buckets', []) if b['Name'].startswith(prefix_filter)]
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Failed to list buckets: {e}"
        }

    if not buckets:
        return {'statusCode': 200, 'body': "No S3 buckets found matching the prefix."}

    total_size_bytes = 0
    bucket_details = []
    total_buckets = len(buckets)

    print(f"Starting threaded scan of {total_buckets} buckets with {max_threads} threads...")

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_bucket = {executor.submit(get_bucket_size, bucket): bucket for bucket in buckets}
        for i, future in enumerate(as_completed(future_to_bucket), 1):
            bucket, size = future.result()
            size_gib = round(size / (1024 ** 3), 2)
            total_size_bytes += size
            bucket_details.append((bucket, size, size_gib))
            print(f"[{i}/{total_buckets}] {bucket}: {size} bytes ({size_gib} GiB)")

    total_size_gib = round(total_size_bytes / (1024 ** 3), 2)
    elapsed_seconds = round(time.time() - start_time, 2)

    summary_lines = [
        "---------------------------------------------------",
        f"Total buckets processed: {total_buckets}",
        f"Total size of all S3 buckets: {total_size_bytes} bytes",
        f"Total size of all S3 buckets: {total_size_gib} GiB",
        f"Elapsed time: {elapsed_seconds} seconds",
        "---------------------------------------------------",
        "Per-bucket sizes:"
    ]

    for name, size, gib in sorted(bucket_details, key=lambda x: x[0]):
        summary_lines.append(f"- {name}: {size} bytes ({gib} GiB)")

    result = "\n".join(summary_lines)
    print(result)

    # Optionally write report to S3
    if report_output_bucket:
        report_key = f"s3_bucket_size_report_{int(time.time())}.txt"
        try:
            s3.put_object(Bucket=report_output_bucket, Key=report_key, Body=result.encode('utf-8'))
            print(f"Report uploaded to s3://{report_output_bucket}/{report_key}")
        except Exception as e:
            print(f"Failed to upload report to S3: {e}")

    return {
        'statusCode': 200,
        'body': result
    }
