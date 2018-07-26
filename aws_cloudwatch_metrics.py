#!/usr/bin/env python

"""
This script pulls CloudWatch metrics for EC2,EBS,RDS,ELB and saves them in csv format
You need your AWS credentials aws_access_key_id, aws_secret_access_key & aws_session_token values populated in your ~/.aws/credentials the easist way to get them is via https://aws.amazon.com/blogs/security/a-new-and-standardized-way-to-manage-credentials-in-the-aws-sdks/
"""

__author__ = "nahmed"
__version__ = "1.0.0"

import boto3
import pprint
import csv
import sys
import os.path
import timeit
import queue
from multiprocessing import Process
from datetime import timedelta
from datetime import datetime
import ConfigParser

# Read AWS Credentials
config = ConfigParser.ConfigParser()
config.readfp(open(r'.aws/credentials'))

# read values from a section
aws_access_key_id = config.get('prod', 'aws_access_key_id')
aws_secret_access_key = config.get('prod', 'aws_secret_access_key')
aws_session_token = config.get('prod', 'aws_session_token')

REGION_NAME = "us-east-1"
AWS_ACCESS_KEY_ID = aws_access_key_id
AWS_SECRET_ACCESS_KEY = aws_secret_access_key
AWS_SESSION_TOKEN = aws_session_token

CW_WINDOW = 5 # Min
PERIOD = 300 # Secs

def get_ec2():
    get_regions = boto3.client('ec2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME, aws_session_token=AWS_SESSION_TOKEN)
    ec2_regions = [region['RegionName'] for region in get_regions.describe_regions()['Regions']]

    inst_count = 0
    for region in ec2_regions:
        ec2 = boto3.resource('ec2', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=region, aws_session_token=AWS_SESSION_TOKEN)
        instances = ec2.instances.filter()
        for instance in instances:
            #print instance.id, instance.private_ip_address, region, instance.state
            if instance.state["Name"] == "running":
                inst_count += 1
                # Get EC2 Metrics
                get_ec2_metrics(instance.id)
                for tag in instance.tags:
                    if 'Name'in tag['Key']:
                        line = (instance.id, instance.instance_type, instance.private_ip_address,tag['Value'])
                        with open('prod_inst.csv', "a") as csv_file:
                            writer = csv.writer(csv_file, delimiter=',')
                            writer.writerow(line)
                csv_file.close()
                #print (instance.id, instance.instance_type, instance.private_ip_address,tag['Value'])

    print 'EC2 Count: ' + str(inst_count)

def get_ebs():
    ec2 = boto3.resource('ec2', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    volumes = ec2.volumes.all()
    split_dict_equally(volumes)
    #volumes = ec2.volumes.filter(Filters=[{'Name': 'status', 'Values': ['in-use']}])
    vol_count =0
    for volume in volumes:
        vol_count += 1
        #get_ebs_metrics(volume.id)
    print 'EBS Count: ' + str(vol_count)

def get_rds():
    rds = boto3.client('rds', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    rdsinstances = rds.describe_db_instances()
    rds_count = 0
    rds = queue.deque()
    rds.queue = queue(rdsinstances['DBInstances'])
    for rdsins in rdsinstances['DBInstances']:
        rds_count += 1
        rdsname = rdsins['DBInstanceIdentifier']
        get_rds_metrics(rdsname)
    print 'RDS Count: ' + str(rds_count)

def get_elb():
    get_elbs = boto3.client('elb', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    elbs = get_elbs.describe_load_balancers()
    elb_count = 0
    for elb in elbs['LoadBalancerDescriptions']:
        elb_count += 1
        elb_name = elb['LoadBalancerName']
        get_elb_metrics(elb_name)
    print 'ELB Count: ' + str(elb_count)

def get_ec2_metrics(instance_id):
    if os.path.isfile('ec2.csv'):
        print "Pulling metrics for: %s" % instance_id
    else:
        print "Creating new file with header"
        with open('ec2.csv', 'w') as csv_header:
            writer = csv.writer(csv_header)
            writer.writerow(["instance_id", "metric_name", "timestamp", "minimum","maximum","average","sum","sample_count","unit"])
        csv_header.close()

    client = boto3.client('cloudwatch', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    metrics = ['StatusCheckFailed','CPUUtilization','NetworkIn','NetworkOut','NetworkPacketsIn','NetworkPacketsOut']
    for metric in metrics:
        response = client.get_metric_statistics(
            Namespace = 'AWS/EC2',
            MetricName = metric,
            Dimensions = [
                {
                    'Name': 'InstanceId',
                    'Value': instance_id
                },
            ],
            StartTime = datetime.utcnow() - timedelta(minutes=CW_WINDOW),
            EndTime = datetime.utcnow(),
            Period = PERIOD,
            Statistics = [
                'Maximum',
                'Minimum',
                'Average',
                'Sum',
                'SampleCount'
            ],
        )
        recs = len(response['Datapoints'])
        #pprint.pprint(response, indent=2)
        count = 0
        if recs > 0:
            while count < recs:
                aws_avg = response['Datapoints'][count]['Average']
                aws_max = response['Datapoints'][count]['Maximum']
                aws_min = response['Datapoints'][count]['Minimum']
                aws_sum = response['Datapoints'][count]['Sum']
                aws_smp = response['Datapoints'][count]['SampleCount']
                aws_tsp = response['Datapoints'][count]['Timestamp']
                aws_unt = response['Datapoints'][count]['Unit']
                line = (instance_id,metric,aws_tsp,aws_min,aws_max,aws_avg,aws_sum,aws_smp,aws_unt)
                with open('ec2.csv', "a") as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    writer.writerow(line)
                csv_file.close()
                #print line
                count += 1

def get_ebs_metrics(volume_id):
    if os.path.isfile('ebs.csv'):
        print "Pulling metrics for: %s" % volume_id
    else:
        print "Creating new file with header"
        with open('ebs.csv', 'w') as csv_header:
            writer = csv.writer(csv_header)
            writer.writerow(["volume_id","volume_type","metric_name", "timestamp", "minimum","maximum","average","sum","sample_count","unit"])
        csv_header.close()
    
    ec2 = boto3.resource('ec2', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    vol = ec2.Volume(id=volume_id)
    vol_type = vol.volume_type
         
    client = boto3.client('cloudwatch', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    metrics = ['VolumeReadOps','VolumeWriteOps','VolumeReadBytes','VolumeWriteBytes','BurstBalance','VolumeThroughputPercentage']
    for metric in metrics:
        response = client.get_metric_statistics(
            Namespace = 'AWS/EBS',
            MetricName = metric,
            Dimensions = [
                {
                    'Name': 'VolumeId',
                    'Value': volume_id
                },
            ],
            StartTime = datetime.utcnow() - timedelta(minutes=CW_WINDOW),
            EndTime = datetime.utcnow(),
            Period = PERIOD,
            Statistics = [
                'Maximum',
                'Minimum',
                'Average',
                'Sum',
                'SampleCount'
            ],
        )
        recs = len(response['Datapoints'])
        #pprint.pprint(response, indent=2)
        count = 0
        if recs > 0:
            while count < recs:
                aws_avg = response['Datapoints'][count]['Average']
                aws_max = response['Datapoints'][count]['Maximum']
                aws_min = response['Datapoints'][count]['Minimum']
                aws_sum = response['Datapoints'][count]['Sum']
                aws_smp = response['Datapoints'][count]['SampleCount']
                aws_tsp = response['Datapoints'][count]['Timestamp']
                aws_unt = response['Datapoints'][count]['Unit']
                line = (volume_id,vol_type, metric,aws_tsp,aws_min,aws_max,aws_avg,aws_sum,aws_smp,aws_unt)
                with open('ebs.csv', "a") as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    writer.writerow(line)
                csv_file.close()
                #print line
                count += 1

def get_rds_metrics(db_instance):
    if os.path.isfile('rds.csv'):
        print "Pulling metrics for: %s" % db_instance
    else:
        print "Creating new file with header"
        with open('rds.csv', 'w') as csv_header:
            writer = csv.writer(csv_header)
            writer.writerow(["db_instance", "metric_name", "timestamp", "minimum","maximum","average","sum","sample_count","unit"])
        csv_header.close()
    
    client = boto3.client('cloudwatch', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    metrics = ['DatabaseConnections','CPUUtilization','ReadIOPS','WriteIOPS','FreeStorageSpace','NetworkReceiveThroughput','NetworkTransmitThroughput']
    for metric in metrics:
        response = client.get_metric_statistics(
            Namespace = 'AWS/RDS',
            MetricName = metric,
            Dimensions = [
                {
                    'Name': 'DBInstanceIdentifier',
                    'Value': db_instance
                },
            ],
            StartTime = datetime.utcnow() - timedelta(minutes=CW_WINDOW),
            EndTime = datetime.utcnow(),
            Period = PERIOD,
            Statistics = [
                'Maximum',
                'Minimum',
                'Average',
                'Sum',
                'SampleCount'
            ],
        )
        recs = len(response['Datapoints'])
        #pprint.pprint(response, indent=2)
        count = 0
        if recs > 0:
            while count < recs:
                aws_avg = response['Datapoints'][count]['Average']
                aws_max = response['Datapoints'][count]['Maximum']
                aws_min = response['Datapoints'][count]['Minimum']
                aws_sum = response['Datapoints'][count]['Sum']
                aws_smp = response['Datapoints'][count]['SampleCount']
                aws_tsp = response['Datapoints'][count]['Timestamp']
                aws_unt = response['Datapoints'][count]['Unit']
                line = (db_instance,metric,aws_tsp,aws_min,aws_max,aws_avg,aws_sum,aws_smp,aws_unt)
                with open('rds.csv', "a") as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    writer.writerow(line)
                csv_file.close()
                #print line
                count += 1

def get_elb_metrics(elb_name):
    if os.path.isfile('elb.csv'):
        print "Pulling metrics for: %s" % elb_name
    else:
        print "Creating new file with header"
        with open('elb.csv', 'w') as csv_header:
            writer = csv.writer(csv_header)
            writer.writerow(["elb_name", "metric_name", "timestamp", "minimum","maximum","average","sum","sample_count","unit"])
        csv_header.close()
    
    client = boto3.client('cloudwatch', region_name=REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    metrics = ['ActiveConnectionCount','HealthyHostCount','UnHealthyHostCount','RequestCount','NewConnectionCount','ProcessedBytes','TargetResponseTime','Latency','SpilloverCount','SurgeQueueLength']
    namespaces = ['AWS/ApplicationELB','AWS/ELB']
    for namespace in namespaces:
        for metric in metrics:
            response = client.get_metric_statistics(
                Namespace = namespace,
                MetricName = metric,
                Dimensions = [
                    {
                        'Name': 'LoadBalancerName',
                        'Value': elb_name
                    },
                ],
                StartTime = datetime.utcnow() - timedelta(minutes=CW_WINDOW),
                EndTime = datetime.utcnow(),
                Period = PERIOD,
                Statistics = [
                    'Maximum',
                    'Minimum',
                    'Average',
                    'Sum',
                    'SampleCount'
                ],
            )
            recs = len(response['Datapoints'])
            #pprint.pprint(response, indent=2)
            count = 0
            if recs > 0:
                while count < recs:
                    aws_avg = response['Datapoints'][count]['Average']
                    aws_max = response['Datapoints'][count]['Maximum']
                    aws_min = response['Datapoints'][count]['Minimum']
                    aws_sum = response['Datapoints'][count]['Sum']
                    aws_smp = response['Datapoints'][count]['SampleCount']
                    aws_tsp = response['Datapoints'][count]['Timestamp']
                    aws_unt = response['Datapoints'][count]['Unit']
                    line = (elb_name,metric,aws_tsp,aws_min,aws_max,aws_avg,aws_sum,aws_smp,aws_unt)
                    with open('elb.csv', "a") as csv_file:
                        writer = csv.writer(csv_file, delimiter=',')
                        writer.writerow(line)
                    csv_file.close()
                    #print line
                    count += 1

def main():
    #p1 = Process(target = get_ec2)
    #p1.start()
    #p2 = Process(target = get_ebs)
    #p2.start()
    p3 = Process(target = get_elb)
    p3.start()
    p4 = Process(target = get_rds)
    p4.start()
    
if __name__=='__main__':
    main()
