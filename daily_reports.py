#!/usr/bin/env python
import re
import os
import sys
import boto3
import string
import base64
import pprint
import pexpect
import MySQLdb
import logging
import smtplib
import traceback
import ConfigParser
from logging import Formatter
from tabulate import tabulate
from datetime import datetime
from datetime import timedelta
from logging import FileHandler
from email.mime.text import MIMEText
from simplecrypt import encrypt, decrypt
from email.mime.multipart import MIMEMultipart
from logging.handlers import TimedRotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler

# Configuration setup
cfg_file = 'daily_reports.cfg'
cfg = ConfigParser.ConfigParser()
cfg.readfp(open(cfg_file))

# Read configuration
log = cfg.get('common','log')
sql_1 = cfg.get('query','sql_1')
sql_2 = cfg.get('query','sql_2')
sql_3 = cfg.get('query','sql_3')
sql_4 = cfg.get('query','sql_4')
s3_whitelist = cfg.get('common','s3_whitelist')
s3_whitelist = s3_whitelist.split(',')

LOG_LEVEL = logging.INFO

# logger setup
APP_LOG = log
APP_LOG_FORMAT = ("%(asctime)s [%(levelname)s] [%(funcName)s]: %(message)s in %(pathname)s:%(lineno)d")
APP_LOG_HANDLER = TimedRotatingFileHandler(APP_LOG, when='midnight', interval=1, backupCount=5)
app_logger = logging.getLogger('__name__')
app_logger.setLevel(LOG_LEVEL)
app_logger_file_handler = FileHandler(APP_LOG)
app_logger_file_handler = APP_LOG_HANDLER
app_logger_file_handler.setLevel(LOG_LEVEL)
app_logger_file_handler.setFormatter(Formatter(APP_LOG_FORMAT))
app_logger.addHandler(app_logger_file_handler)

# Read DB configurations
db_host = cfg.get('db','db_host')
db_user = cfg.get('db', 'db_user')
db_pass = cfg.get('db', 'db_pass')
db_name = cfg.get('db', 'db_name')
db_port = cfg.getint('db', 'db_port')
db_pass = base64.b64decode(db_pass)

# email report
def send_report(data,field_names,subj,details):

    FROM = 'aws-security-report@vonage.com'
    #TO = ['nasir.ahmed@vonage.com','nirav.kadakia@vonage.com','VIS-AWS-Alerts@vonage.com']
    #TO = ['nasir.ahmed@vonage.com','nirav.kadakia@vonage.com']
    TO = ['nasir.ahmed@vonage.com']
    relay = 'mail-sysrelay.vgcva0.prod.vonagenetworks.net'
    #relay = 'prodmx.kewr0.s.vonagenetworks.net'

    text = """
    Hello,

    {body}

    {table}

    --"""

    html = """
    <html><head>
    <style>
    table, th, td {{ border: 1px solid black; border-collapse: collapse; font-size: 10px; font-family: monospace; }}
    th, td {{ padding: 5px; }}
    th {{ background-color: silver; }}
    p {{ font-size: 11px; font-family: monospace; }}
    </style></head>
    <body><p>Hello,</p>
    <p>{body}</p>
    {table}
    <p>--</p>
    </body></html>
    """
    
    try:
        text = text.format(table=tabulate(data, field_names, tablefmt="grid"),body=details)
        html = html.format(table=tabulate(data, field_names, tablefmt="html"),body=details)
    except:
        traceback.print_exc(file=sys.stdout)

    message = MIMEMultipart(
        "alternative", None, [MIMEText(text), MIMEText(html,'html')])

    message['Subject'] = "Daily %s" % subj
    message['From'] = FROM
    message['To'] = ','.join(TO)
    message['Reply-to'] = 'nasir.ahmed@vonage.com'
    try:
        server = smtplib.SMTP(relay)
        server.sendmail(FROM, TO, message.as_string())
        server.quit()
    except smtplib.SMTPException as e:
        app_logger.error('Failed to send email %s', str(e))
        print(str(e))

    return None

def get_report(sql):

    translator = {'ts': 'Date/Time', 'account_name': 'Acccount', 'region': 'Region', 'db': 'DB Instance', 'ingress_rule': 'Ingress Rule', 'security_group': 'Security Group', 'db_type': 'Database Type', 'is_public': 'Public', 'id': 'Instance ID','private_ip': 'Private IP', 'public_ip': 'Public IP', 'name': 'Instance Name', 'keypair': 'Keypair', 'owner': 'Owner', 'bucket_name': 'Bucket Name', 'bucket_read': 'Bucket Read', 'bucket_write': 'Bucket Write', 'bucket_read_acp': 'Read (Bucket Permissions)', 'bucket_write_acp': 'Write (Bucket Permissions)', 'bucket_full_cont': 'Full Control', 'contact': 'Contact', 'host': 'Host/IP', 'status': 'Status', 'az': 'Region(AZ)', 'detector_id': 'Detector', 'finding_id': 'Finding', 'sev': 'Severity', 'count': 'Count', 'title': 'Title', 'description': 'Description', 'resource_type': 'Resource', 'ami': 'AMI', 'local_ip': 'Local IP', 'remote_ip': 'Remote IP', 'last_seen': 'Last Seen', 'action': 'Action','org': 'Organization', 'isp': 'ISP', 'city': 'City', 'country': 'Country', 'blocked': 'Blocked', 'instance_id': 'Instance', 'type': 'Type'}

    db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_pass, db=db_name, port=db_port)
    cur = db.cursor()
    try:
        recs = cur.execute(sql)
        num_fields = len(cur.description)
        field_names = [translator[i[0]] for i in cur.description]
        data = []
        if recs > 0:
            for row in cur.fetchall():
                if re.findall(r's3_sec_info', sql) and row[2] in s3_whitelist:
                    print row[2], 'skipped'
                    app_logger.info('Skipped, found in whitelist: %s', row[2])
                    pass
                else:
                    # Fix un-printable chars in city name
                    fix_city = list(row)
                    fix_city[16] = ''.join(filter(lambda x: x in string.printable, fix_city[16]))
                    sanitized_row = tuple(fix_city)
                    data.append(sanitized_row)
    except MySQLdb.Error, e:
        app_logger.warning('Unable to query: %s, Got error: %s', sql, e)
        print 'Unable to query %s' % e

    #print tabulate(data, field_names, tablefmt="fancy_grid")
    #exit(1)
    if len(data) > 0:
        if re.findall(r'db_sec_info',sql):
            subj = "Database Report"
            body = "Please review the database instance(s) for possible public access:"
            send_report(data,field_names,subj,body)
        elif re.findall(r's3_sec_info', sql):
            subj = "S3 Bucket Report"
            body = "Please review the S3 bucket(s) for possible public access:"
            send_report(data,field_names,subj,body)
        elif re.findall(r'ec2_sec_info', sql):
            subj = "EC2 Instance Report"
            body = "Please review the EC2 instance(s) for possible public access:"
            send_report(data,field_names,subj,body)
        elif re.findall(r'gd_find_info', sql):
            subj = "GuardDuty Report"
            body = "Please review the GuardDuty Findings for possible Vulnerablities/Attacks:"
            send_report(data,field_names,subj,body)
    else:
        app_logger.warning('No data returned to email')

def main():

    #for job in sched.get_jobs():
    #    print("name: %s, trigger: %s, next run: %s, handler: %s" % (job.name, job.trigger, job.next_run_time, job.func))
    #    app_logger.info("name: %s, trigger: %s, next run: %s, handler: %s", job.name, job.trigger, job.next_run_time, job.func)

    app_logger.info('Calling EC2 Report')
    app_logger.info('Query: %s', sql_1)
    #get_report(sql_1)

    app_logger.info('Calling S3 Report')
    app_logger.info('Query: %s', sql_2)
    #get_report(sql_2)

    app_logger.info('Calling DB Report')
    app_logger.info('Query: %s', sql_3)
    #get_report(sql_3)

    app_logger.info('Calling GuardDuty Report')
    app_logger.info('Query: %s', sql_4)
    get_report(sql_4)

if __name__ == "__main__":
    app_logger.info('Starting %s', os.path.basename(__file__))
    #main()
    sched = BlockingScheduler()
    now = datetime.now() + timedelta(minutes = 1)
    #sched.add_job(main, "interval", minutes = 60, start_date=now.strftime('%Y-%m-%d %H:%M:%S'), max_instances = 1, coalesce = True, replace_existing = True)
    sched.add_job(main, "cron", hour = "8", minute = "1", max_instances = 1, coalesce = True, replace_existing = True, timezone="America/New_York", name="daily_reports")
        sched.start()
