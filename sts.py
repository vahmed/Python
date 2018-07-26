#!/usr/bin/python
import re
import boto3
import ConfigParser

# Read AWS Credentials
config = ConfigParser.ConfigParser()
config.readfp(open(r'.aws/credentials'))

# read values from a section
aws_access_key_id = config.get('dev', 'aws_access_key_id')
aws_secret_access_key = config.get('dev', 'aws_secret_access_key')
aws_session_token = config.get('dev', 'aws_session_token')

sts = boto3.client("sts", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,aws_session_token=aws_session_token)
#sts = boto3.client("sts", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
user_arn = sts.get_caller_identity()["Arn"]
print user_arn.split(":")[4]
