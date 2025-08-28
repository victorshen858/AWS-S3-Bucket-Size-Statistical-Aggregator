import boto3
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Built-in defaults (user can replace INSERT_* placeholders)
DEFAULT_CONFIG = {
    "MAX_THREADS": 10,
    "BUCKET_FILTER_PREFIX": "",
    "REPORT_OUTPUT_S3_BUCKET": "arn:aws:s3:::INSERT_REPORT_BUCKET_HERE",
    "LAMBDA_NAME": "INSERT_LAMBDA_NAME_HERE",
    "IAM_ROLE_ARN": "arn:aws:iam::INSERT_ACCOUNT_ID_HERE:role/INSERT_ROLE_NAME_HERE"
}

# Try to override defaults from S3 config.json if CONFIG_S3_BUCKET env var is set
config = DEFAULT_CONFIG.copy()
CONFIG_BUCKET = os.environ.get("CONFIG_S3_BUCKET")

if CONFIG_BUCKET:
    s3 = boto3.client("s3")
    try:
        resp = s3.get_object(Bucket=CONFIG_BUCKET, Key="config.json")
        file_config = json.loads(resp["Body"].read())
        config.update(file_config)
        print(f"Loaded config from {CONFIG_BUCKET}/config.json")
    except s3.exceptions.NoSuchKey:
        print(f"No config.json found in {CONFIG_BUCKET}, using built-in defaults.")
    except Exception as e:
        print(f"Error reading config.json: {e}, using built-in defaults.")
else:
    print("CONFIG_S3_BUCKET env var not set, using built-in defaults.")

# === Lambda S3 scan logic ===
s3_client = boto3.client("s3")

def get_bucket_size(bucket_name):
    try:
        size = 0
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                size += sum(obj['Size'] for obj in page['Contents'])
        return bucket_name, size
    except Exception as e:
        print(f"Error accessing bucket {bucket_name}: {e}")
        return bucket_name, 0

def lambda_handler(event, context):
    start_time = time.time()
    try:
        buckets_response = s3_client.list_buckets()
        buckets = [b['Name'] for b in buckets_response.get('Buckets', [])]
    except Exception as e:
        return {'statusCode': 500, 'body': f"Failed to list buckets: {e}"}

    total_size_bytes = 0
    bucket_details = []
    total_buckets = len(buckets)

    print(f"Starting threaded scan of {total_buckets} buckets...")

    with ThreadPoolExecutor(max_workers=config["MAX_THREADS"]) as executor:
        future_to_bucket = {executor.submit(get_bucket_size, b): b for b in buckets}
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

    # Optionally write CSV report to S3 if REPORT_OUTPUT_S3_BUCKET is set
    report_bucket = config.get("REPORT_OUTPUT_S3_BUCKET")
    if report_bucket and "INSERT" not in report_bucket:
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["BucketName", "SizeBytes", "SizeGiB"])
        for name, size, gib in bucket_details:
            writer.writerow([name, size, gib])
        report_key = f"s3_bucket_sizes/report_{int(time.time())}.csv"
        try:
            s3_client.put_object(Bucket=report_bucket.replace("arn:aws:s3:::", ""), Key=report_key, Body=output.getvalue())
            print(f"Report written to s3://{report_bucket.replace('arn:aws:s3:::','')}/{report_key}")
        except Exception as e:
            print(f"Failed to write report to {report_bucket}: {e}")

    return {'statusCode': 200, 'body': result}
