variable "lambda_name" {
  type        = string
  default     = "s3-bucket-size-aggregator"
  description = "Lambda function name"
}

variable "config_s3_bucket" {
  type        = string
  description = "S3 bucket containing Lambda config.json"
}

variable "lambda_memory" {
  type    = number
  default = 1024
}

variable "lambda_timeout" {
  type    = number
  default = 900
}
