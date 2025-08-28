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

Terraform

You can also deploy using Terraform (see main.tf example below).

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


---

## **Terraform Equivalent (`main.tf`)**

```hcl
provider "aws" {
  region = "us-east-1"  # change as needed
}

resource "aws_iam_role" "s3_size_aggregator_role" {
  name = "s3-bucket-size-aggregator-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_readonly" {
  role       = aws_iam_role.s3_size_aggregator_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch" {
  role       = aws_iam_role.s3_size_aggregator_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_lambda_function" "s3_size_aggregator" {
  function_name = "s3-bucket-size-aggregator"
  runtime       = "python3.11"
  role          = aws_iam_role.s3_size_aggregator_role.arn
  handler       = "lambda_function.lambda_handler"
  filename      = "lambda_function.zip" # Zip your code
  source_code_hash = filebase64sha256("lambda_function.zip")
  timeout       = 900
  memory_size   = 1024
}

Notes:

Zip the Lambda code (lambda_function.py) before running terraform apply.
Terraform automatically creates the IAM role and attaches necessary policies.
Works equivalently to the CloudFormation template.
