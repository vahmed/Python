#!/usr/bin/env python
import os
import time
import boto3
from botocore.exceptions import ClientError

REGIONS = ['ap-south-1', 'eu-west-3', 'eu-west-2', 'eu-west-1', 'ap-northeast-2', 'ap-northeast-1', 'sa-east-1', 'ca-central-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-central-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
for REGION in REGIONS:
   print REGION
   rds = boto3.client('rds',region_name=REGION)
   try:
   # get all of the db instances
      dbs = rds.describe_db_instances()
      for db in dbs['DBInstances']:
          print ("%s -> %s -> %s -> %s") % (
               db['AvailabilityZone'],
               db['DBInstanceClass'],
               db['DBInstanceIdentifier'],
               db['Engine'])
          #print(db)
   except Exception as error:
       print error
