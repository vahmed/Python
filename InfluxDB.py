#!/usr/bin/python2.7

import socket
import time
import MySQLdb
import logging
import timeit
import signal
import sys
from logging.handlers import TimedRotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from multiprocessing import Process

# Logger details
log_file = '/var/log/telegraf/influx.log'
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# DB details
db_host = 'xxxxx.yyyyy.com'
db_user = 'nahmed'
db_pass = 'nahmed_p1'
db_name = 'mydb'
db_port = 3306

def calldata():
    teams = ['h2o','h1o']
    for team in teams:
        db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_pass, db=db_name, port=db_port)
        cur = db.cursor()
        sql = "SELECT DISTINCT calldate,callstate,cluster FROM CallData WHERE team = %s AND DATE_SUB(NOW(), INTERVAL 5 MINUTE) < ts ORDER BY calldate"
        recs = cur.execute(sql,([team]))
        #now = str(int(time.time()))
        pattern = '%Y-%m-%d %H:%M:%S'
        if recs > 0:
            logger.info('Sending %s CallData events for %s', str(recs), team)
            for row in cur.fetchall():
                now = str(int(time.mktime(time.strptime(str(row[0]), pattern))))
		        now = now +'000000000'
                c = 'CallData' + ',team=' + team + ',cluster=' + str(row[2]) + ' callstate=' + str(row[1]) + ' ' + now
                print c
    db.close()
    return None

def callqdata():
    teams = ['h2o','h1o']
    for team in teams:
        db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_pass, db=db_name, port=db_port)
        cur = db.cursor()
        sql = "SELECT DISTINCT calldate,amos,apl,bmos,bpl,cluster FROM CallQData WHERE team = %s AND DATE_SUB(NOW(), INTERVAL 5 MINUTE) < ts ORDER BY calldate"
        recs = cur.execute(sql,([team]))
        #now = str(int(time.time()))
        pattern = '%Y-%m-%d %H:%M:%S'
        if recs > 0:
            logger.info('Sending %s CallQData events for %s', str(recs), team)
            for row in cur.fetchall():
                now = str(int(time.mktime(time.strptime(str(row[0]), pattern))))
		        now = now + '000000000'
                amos = 'CallQData' + ',team=' + team + ',cluster=' + str(row[5]) + ' amos=' + str(row[1]) + ' ' + now
                apl = 'CallQData' + ',team=' + team + ',cluster=' + str(row[5]) + ' apl=' + str(row[2]) + ' ' + now
                bmos = 'CallQData' + ',team=' + team + ',cluster=' + str(row[5]) + ' bmos=' + str(row[3]) + ' ' + now
                bpl = 'CallQData' + ',team=' + team + ',cluster=' + str(row[5]) + ' bpl=' + str(row[4]) + ' ' + now

    db.close()
    return None


if __name__ == '__main__':
    calldata()
    callqdata()
