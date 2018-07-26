#!/usr/bin/python
import re
import csv
import json
import time
import os.path
import boto3
import logging
import pprint
import ConfigParser
from logging.handlers import TimedRotatingFileHandler
from datetime import timedelta
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from influxdb import InfluxDBClient
from celery import Celery
from celery.task import periodic_task

USE_TZ = True
TIME_ZONE = 'America/New York'
CELERY_ENABLE_UTC = False
CELERY_TIMEZONE = TIME_ZONE

app = Celery('lambda_metrics', broker='sqla+mysql://root:letme1n@127.0.0.1/celery', backend='db+mysql://root:letme1n@127.0.0.1/celery')

app.conf.beat_schedule = {
    'add-every-60-seconds': {
        #'task': 'task.add',
        'schedule': 60.0
    },
}

# Logger details
log_file = 'lambda_metrics.log'
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Read AWS Credentials
config = ConfigParser.ConfigParser()
config.readfp(open(r'.aws/credentials'))

# read values from a section
aws_access_key_id = config.get('xx', 'aws_access_key_id')
aws_secret_access_key = config.get('xx', 'aws_secret_access_key')
aws_session_token = config.get('xx', 'aws_session_token')

CW_WINDOW = 5 # Min
PERIOD = 300 # Secs

def get_lambda_metrics(function_name,REGION_NAME):
    influx_client = InfluxDBClient(host='localhost', port=8086, database='telegraf')
    client = boto3.client('cloudwatch', region_name=REGION_NAME, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, aws_session_token=aws_session_token)
    metrics = ['Invocations','Errors','Dead Letter Error','Duration','Throttles','IteratorAge','ConcurrentExecutions','UnreservedConcurrentExecutions']
    for metric in metrics:
        response = client.get_metric_statistics(
            Namespace = 'AWS/Lambda',
            MetricName = metric,
            Dimensions = [
                {
                    'Name': 'FunctionName',
                    'Value': function_name
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
                #print line
                if aws_tsp is not None:
                    pattern = '%Y-%m-%d %H:%M:%S+00:00'
                    aws_tsp = str(int(time.mktime(time.strptime(str(aws_tsp), pattern))))                
                    line = function_name + ',' + metric + ',' + aws_unt + ' ' + 'minimum=' + str(aws_min) + ',' + 'maximum=' + str(aws_max) + ',' + 'average=' + str(aws_avg) + 'sum=' + str(aws_sum) + ',' + 'sample_count=' + str(aws_smp) + ' ' + aws_tsp + '000000000'
                    data = [
                        {
                        "measurement": "LambdaMetrics",
                        "tags": {
                                    "name": function_name,
                                    "unit": aws_unt,
                                    "env": "qa",
                                    "region": REGION_NAME,
                                    "metric": metric,
                                },
                        "time": str(aws_tsp),
                        "fields": 
                                {
                                    "minimum": float(aws_min),
                                    "maximum": float(aws_max),
                                    "average": float(aws_avg),
                                    "sum": float(aws_sum),
                                    "sample": float(aws_smp)
                                }
                            }
                        ]
                    print line
                    print data
                    #time.sleep(1)
                    #influx_client.write_points(data)
                    #print line
                    logger.info('Sending: %s', line)
                count += 1
    return None

#@app.periodic_task(run_every=timedelta(seconds=60))
@app.task
def main():
    REGIONS = ['us-east-1','us-west-2']

    for REGION in REGIONS:
        logger.info('Region: %s', REGION)
        lambda_client = boto3.client('lambda', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,aws_session_token=aws_session_token,region_name=REGION)

        funcs = lambda_client.list_functions()
        #pprint.pprint(funcs)
        count = 0
        total_fcn = len(funcs['Functions'])

    for key, value in funcs.items():
        if key == 'Functions':
            while count < total_fcn:
                #print 'Function Name: %s Description: %s | Runtime: %s | MemorySize: %s' %(value[count]['FunctionName'],value[count]['Description'],value[count]['Runtime'],value[count]['MemorySize'])
                #print value[count]['FunctionName']
                if re.findall(r'h2o',value[count]['FunctionName'],re.IGNORECASE):
                    logger.info('Invoking get_lambda_metrics for %s', value[count]['FunctionName'])
                    get_lambda_metrics(value[count]['FunctionName'],REGION)
                count += 1

if __name__=='__main__':
    main()
