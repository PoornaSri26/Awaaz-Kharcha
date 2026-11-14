# Awaaz Kharcha — serverless audio pipeline on AWS (free-tier friendly)
# terraform init && terraform apply
terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}
provider "aws" { region = var.region }

variable "region" { default = "ap-south-1" }

resource "aws_s3_bucket" "audio" {
  bucket = "awaaz-kharcha-audio-${random_id.suffix.hex}"
}
resource "random_id" "suffix" { byte_length = 4 }

resource "aws_s3_bucket_notification" "trigger" {
  bucket = aws_s3_bucket.audio.id
  lambda_function { lambda_function_arn = aws_lambda_function.worker.arn, events = ["s3:ObjectCreated:*"] }
}

resource "aws_iam_role" "lambda" {
  name = "awaaz-lambda"
  assume_role_policy = jsonencode({ Version = "2012-10-17",
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" },
                   Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "basic" {
  role = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy" "s3" {
  role = aws_iam_role.lambda.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"],
      Resource = "${aws_s3_bucket.audio.arn}/*" }] })
}

resource "aws_lambda_function" "worker" {
  function_name = "awaaz-audio-worker"
  role          = aws_iam_role.lambda.arn
  runtime       = "python3.11"
  handler       = "handler.handler"
  timeout       = 300
  memory_size   = 3008
  filename      = "../lambda/worker.zip"   # zip deploy/lambda + repo code + layer
  source_code_hash = filebase64sha256("../lambda/worker.zip")
}

resource "aws_lambda_permission" "s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_lambda_function.worker.arn
}

output "bucket" { value = aws_s3_bucket.audio.bucket }
output "function" { value = aws_lambda_function.worker.function_name }
