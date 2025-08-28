# AWS-S3-Bucket-Size-Statistical-Aggregator
This AWS Lambda function scans all S3 buckets in an AWS account and aggregates their size statistics.

# S3 Bucket Size Statistical Aggregator

This AWS Lambda function scans all S3 buckets in an AWS account and aggregates their size statistics. It provides:

- Total size in bytes
- Total size in GiB
- Per-bucket size breakdown

It can optionally upload the report to an S3 bucket and is fully configurable through a `config.json` stored in S3.

---

## **Features**

- **Parallel scanning:** Uses multiple threads for fast scanning of dozens of buckets.
- **Configurable:** Reads `config.json` from S3 with options:
  - `MAX_THREADS` – Maximum concurrent threads for scanning
  - `BUCKET_FILTER_PREFIX` – Only scan buckets matching this prefix
  - `REPORT_OUTPUT_S3_BUCKET` – Optional S3 bucket to store report
- **CloudWatch logging:** Outputs summary to CloudWatch logs.
- **S3 report upload:** Optional, fully configurable.
- **Generic deployment:** Works across AWS accounts without modifying code.

---

## **Deployment**

### CloudFormation
Use `s3-bucket-size-aggregator.yaml` to deploy Lambda and IAM Role:

aws cloudformation deploy \
  --template-file s3-bucket-size-aggregator.yaml \
  --stack-name s3-bucket-size-aggregator \
  --capabilities CAPABILITY_NAMED_IAM

Usage
Manual Trigger
{
  "config_s3_bucket": "INSERT_CONFIG_BUCKET_HERE"
}


If config_s3_bucket is provided, Lambda will load config.json from this bucket.

If not, default values are used.

Output

Prints detailed summary to CloudWatch logs.

Optionally uploads a .txt report to S3 if REPORT_OUTPUT_S3_BUCKET is configured.

Config File Example (config.json)
{
  "MAX_THREADS": 10,
  "BUCKET_FILTER_PREFIX": "",
  "REPORT_OUTPUT_S3_BUCKET": "INSERT_BUCKET_NAME_HERE"
}

Notes

Works with accounts with dozens of buckets efficiently.

Fully environment/configuration-driven; no code changes needed for new AWS accounts.

Useful for cost estimation and understanding storage usage.


Alternative Terraform IaC Usage (same functionality as CloudFormation AWS stack)

Set variables:

export TF_VAR_config_s3_bucket="your-config-bucket-name"


Zip Lambda code:

zip lambda_function.zip lambda_function.py


Deploy:

terraform init
terraform apply

Lambda Behavior

Automatically reads CONFIG_S3_BUCKET from environment variables.

Falls back to defaults if the S3 config file is not present.

Fully matches CloudFormation deployment behavior.

Threading, bucket filtering, and optional S3 report are all identical.

Notes:

Zip the Lambda code (lambda_function.py) before running terraform apply.
Terraform automatically creates the IAM role and attaches necessary policies.
Works equivalently to the CloudFormation template.
