terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "eu-west-1"
}

# S3
resource "aws_s3_bucket" "recordings_bucket" {
  bucket = local.envs["AWS_S3_RECORDINGS_BUCKET"]
  force_destroy = true
}

# SES
resource "aws_ses_email_identity" "sender_email" {
  email = local.envs["AWS_SES_EMAIL_SOURCE_ADDRESS"]
}

resource "aws_ses_email_identity" "recipient_email" {
  email = local.envs["AWS_SES_EMAIL_RECIPIENT_ADDRESS"]
}

# # Kinesis Video Stream
# resource "aws_kinesis_video_stream" "video_stream" {
#   name                    = "kinesis-video-stream"
#   data_retention_in_hours = 1
#   device_name             = "raspberry-pi"
#   # media_type              = "video/h264"
}