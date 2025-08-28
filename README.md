# AWS-S3-Bucket-Size-Statistical-Aggregator
This AWS Lambda function scans all S3 buckets in an AWS account and aggregates their size statistics.

# S3 Bucket Size Statistical Aggregator

## Overview

The **S3 Bucket Size Statistical Aggregator** Lambda scans all S3 buckets in your AWS account, calculates the total size in bytes and GiB, and optionally writes a CSV report to a configurable S3 bucket.  

It can run:

- **Standalone** using built-in default constants.  
- **With `config.json`** in S3 for dynamic configuration.  

**Purpose:** Quickly assess total S3 usage, estimate costs, or track storage growth across multiple buckets.  

--------------------------------------------------------------------------------------------------------------------------

## Configuration

### Built-in Defaults (Replace `INSERT_*` values before deployment)

DEFAULT_CONFIG = {
    "MAX_THREADS": 10,
    "BUCKET_FILTER_PREFIX": "",
    "REPORT_OUTPUT_S3_BUCKET": "arn:aws:s3:::INSERT_REPORT_BUCKET_HERE",
    "LAMBDA_NAME": "INSERT_LAMBDA_NAME_HERE",
    "IAM_ROLE_ARN": "arn:aws:iam::INSERT_ACCOUNT_ID_HERE:role/INSERT_ROLE_NAME_HERE"
}
Optional S3 Config (config.json)
{
    "MAX_THREADS": 10,
    "BUCKET_FILTER_PREFIX": "",
    "REPORT_OUTPUT_S3_BUCKET": "arn:aws:s3:::your-report-bucket"
}


Place config.json in a bucket and set the Lambda environment variable CONFIG_S3_BUCKET.

If missing, the Lambda uses the built-in constants.

## Deployment

### Using CloudFormation
aws cloudformation deploy \
  --template-file s3-bucket-size-aggregator.yaml \
  --stack-name s3-size-aggregator \
  --capabilities CAPABILITY_NAMED_IAM


Update s3-bucket-size-aggregator.yaml placeholders:

INSERT_LAMBDA_CODE_BUCKET_HERE → S3 bucket with lambda_function.zip

INSERT_CONFIG_BUCKET_HERE → S3 bucket with config.json (optional)

### Using Terraform

Terraform equivalent available in s3-bucket-size-aggregator.tf.

Pass CONFIG_S3_BUCKET and other variables to match the CloudFormation deployment.

Example:

variable "config_bucket" {
  default = "INSERT_CONFIG_BUCKET_HERE"
}

variable "report_bucket" {
  default = "INSERT_REPORT_OUTPUT_BUCKET_HERE"
}

### Running via AWS CloudShell (Bash Script)

You can run a quick total S3 bucket size scan without Lambda:

#!/bin/bash
echo "Listing all S3 buckets..."
buckets=$(aws s3 ls | awk '{print $3}')
if [ -z "$buckets" ]; then
    echo "No S3 buckets found in this account."
    exit 1
fi
total_buckets=$(echo "$buckets" | wc -l)
current_bucket=0
total_size_in_bytes=0

get_bucket_size() {
    local bucket=$1
    size_info=$(timeout 180s aws s3 ls s3://$bucket --recursive --summarize 2>/dev/null)
    if [[ $? -eq 124 ]] || [[ -z "$size_info" ]]; then
        echo 0
        return
    fi
    echo $(echo "$size_info" | grep -oP 'Total Size: \K\d+')
}

if ! command -v bc &>/dev/null; then sudo yum install bc -y; fi

for bucket in $buckets; do
    current_bucket=$((current_bucket + 1))
    size=$(get_bucket_size $bucket)
    if [[ "$size" =~ ^[0-9]+$ ]]; then
        total_size_in_bytes=$((total_size_in_bytes + size))
    fi
done

total_size_in_gib=$(echo "scale=2; $total_size_in_bytes / 1073741824" | bc)
echo "---------------------------------------------------"
echo "Total size of all S3 buckets combined: $total_size_in_bytes bytes"
echo "Total size of all S3 buckets combined: $total_size_in_gib GiB"


Output Example:

Total size of all S3 buckets combined: 957432773261 bytes
Total size of all S3 buckets combined: 891.67 GiB

Lambda Function

Example lambda_function.py:

import boto3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

s3 = boto3.client('s3')

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
    buckets_response = s3.list_buckets()
    buckets = [bucket['Name'] for bucket in buckets_response.get('Buckets', [])]
    total_size_bytes = 0
    bucket_details = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_bucket = {executor.submit(get_bucket_size, bucket): bucket for bucket in buckets}
        for future in as_completed(future_to_bucket):
            bucket, size = future.result()
            total_size_bytes += size
            bucket_details.append((bucket, size, round(size / (1024 ** 3), 2)))

    total_size_gib = round(total_size_bytes / (1024 ** 3), 2)
    elapsed_seconds = round(time.time() - start_time, 2)

    result_lines = [
        f"Total buckets: {len(buckets)}",
        f"Total size (bytes): {total_size_bytes}",
        f"Total size (GiB): {total_size_gib}",
        f"Elapsed time: {elapsed_seconds}s",
        "Per-bucket sizes:"
    ]
    for name, size, gib in sorted(bucket_details, key=lambda x: x[0]):
        result_lines.append(f"- {name}: {size} bytes ({gib} GiB)")

    result = "\n".join(result_lines)
    print(result)
    return {
        "statusCode": 200,
        "body": result
    }

### Notes

-Supports manual run for testing or automated runs via Lambda triggers.
-Configurable with config.json or constants in Lambda.
-Placeholders (INSERT_*) follow AWS ARN format for clarity.
-Both CloudFormation and Terraform deployments supported.
