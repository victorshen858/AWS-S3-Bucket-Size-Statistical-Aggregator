import os
import json
import boto3

# Defaults
DEFAULT_CONFIG = {
    "MAX_THREADS": 10,
    "BUCKET_FILTER_PREFIX": "",
    "REPORT_OUTPUT_S3_BUCKET": None  # optional
}

CONFIG_BUCKET = os.environ.get("CONFIG_S3_BUCKET")
config = DEFAULT_CONFIG.copy()

if CONFIG_BUCKET:
    s3 = boto3.client("s3")
    try:
        resp = s3.get_object(Bucket=CONFIG_BUCKET, Key="config.json")
        file_config = json.loads(resp["Body"].read())
        config.update(file_config)
        print(f"Loaded config from {CONFIG_BUCKET}/config.json")
    except s3.exceptions.NoSuchKey:
        print(f"No config.json found in {CONFIG_BUCKET}, using defaults.")
    except Exception as e:
        print(f"Error reading config.json: {e}, using defaults.")
else:
    print("CONFIG_S3_BUCKET env var not set, using defaults.")

# Now use `config["MAX_THREADS"]`, `config["BUCKET_FILTER_PREFIX"]`, etc.
