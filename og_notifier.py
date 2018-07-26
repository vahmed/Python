#!/usr/bin/env python

"""
This script starts an HTTP server which listens on port 8080 accepting PUT method to accept json data then parses the json data and emails to the recipients defined below
To test: curl -X PUT --data @2017-08-23.21-11-35.txt http://xxxx.net:8080
"""

__author__ = "afriling, nahmed"
__version__ = "1.0"

import sys
import string
import os
import json
import smtplib
import logging
import signal
import SimpleHTTPServer
import datetime
import MySQLdb
from os import curdir
from os.path import join as pjoin
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from opsgenie.swagger_client import AlertApi
from opsgenie.swagger_client import configuration
from opsgenie.swagger_client.models import *
from opsgenie.swagger_client.rest import ApiException
from opsgenie import OpsGenie
from opsgenie.config import Configuration

"""
Define configuration parameters
"""
from_addr = 'nahmed@xxx.net'
to_addr_list = ['xxx.xxxx@xxxx.com']
log_file = './og_notifier.log'
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')
data_dir = './'
db = MySQLdb.connect(host="127.0.0.1", user="root", passwd="letme1n", db="OpsGenie") 
#clusters = [ 'OR0', 'OR1', 'OR2', 'OR3', 'OR4', 'OR5', 'OR6', 'OR7', 'OR8', 'OR9', 'OR10', 'OR11', 'OR12', 'OR13', 'OR14', 'OR15', 'VA0', 'VA1','VA2','VA3','VA4','VA5','VA6','VA7','VA8','VA9','VA10','VA11','VA12','VA13','VA14','VA15' ]

"""
Send mail to OpsGenie
"""
def sendemail(subject, message):

   global from_addr, to_addr_list

   header  = 'From: %s\n' % from_addr
   header += 'To: %s\n' % ','.join(to_addr_list)
   header += 'Subject: %s\n\n' % subject
   message = header + message

   server = smtplib.SMTP('localhost')
   problems = server.sendmail(from_addr, to_addr_list, message)
   server.quit()
   return problems

"""
Make API call to OpsGenie
"""
def call_opsgenie(calias,descr):
    configuration.api_key['Authorization'] = ''
    # You can use base64 version of apiKey instead of prefix
    configuration.api_key_prefix['Authorization'] = 'GenieKey'

    client = AlertApi()

    config = Configuration(apikey="")
    client = OpsGenie(config)

    body = CreateAlertRequest(
        message='Watcher Alert',
        alias=calias,
        description=descr,
        teams=[TeamRecipient(name='RnD Team')],
        visible_to=[TeamRecipient(name='RnD Team', type='team')],
        priority='P4',
        user='RND API',
        note='Watcher Alert')
    try:
        response = AlertApi().create_alert(body=body)
        print('request id: {}'.format(response.request_id))
        print('took: {}'.format(response.took))
        print('result: {}'.format(response.result))
        #logging.info("Called OpsGenie API request id: " + response.request_id + " took: " + str(response.took) + " result: " + response.result)
    except ApiException as err:
        print("Exception when calling AlertApi->create_alert: %s\n" % err)
        logging.warning("Exception when calling AlertApi->create_alert: %s\n" % err)
    return

"""
Create/run an HTTP Server Instance
"""
def run_http_server():
    print "Running HTTP Server on 8080"
    logging.info('#')
    logging.info("HTTP Server Started on 8080")
    class PUTHandler(BaseHTTPRequestHandler):
        def do_PUT(self):
                dt = datetime.datetime.now().strftime("%Y-%m-%d.%H-%M-%S") + '.txt'
                self.json_file = pjoin(data_dir, dt)
                length = int(self.headers['content-length'])
                data = self.rfile.read(length)
          
                with open(self.json_file, 'w') as fh:
                    fh.write(data.decode())

                self.send_response(200)
                parse_data(self.json_file)
    
        def do_POST(self):
            self.send_response(405, "Method Not Allowed")
        def do_GET(self):
            self.send_response(405, "Method Not Allowed")

    server = HTTPServer(('', 8080), PUTHandler)
    server.serve_forever()
    return

"""
Push to DB
"""
def push_to_db(cluster,descr):
    print "Pushing Triggered Event for " + cluster + " to MySQL DB" 
    # Create a Cursor object
    cur = db.cursor()
    # Insert an event to DB
    sql = "INSERT INTO WatcherAlert (cluster, description) VALUES (%s, %s)"
    cur.execute(sql, (cluster,descr))
    db.commit()
    return

"""
DB Lookup Cluster event occurence in last 30 mins and returns Description of the event
"""
def db_lookup(cluster):
    # Create a Cursor object
    cur = db.cursor()
    sql = "SELECT * FROM `WatcherAlert` WHERE ts BETWEEN TIMESTAMPADD(MINUTE, -30, NOW()) AND NOW() AND `cluster` = %s AND (SELECT COUNT(cluster) FROM `WatcherAlert` WHERE `cluster` = %s) >= 3 ORDER BY 1,3"
    cur.execute(sql, (cluster,cluster))
    
    msg = "Cluster: " + cluster + '\n'
    # print all events for now
    for row in cur.fetchall():
        msg += row[2] + '\n'
    print msg
    return

"""
Parse the payload
"""
def parse_data(data_file):
    print "Parser Triggered - Check " + log_file + " for more details"
    logging.info('Called argument: %s', data_file)
    logging.info('Input: %s', data_file)

    if not os.path.isfile(data_file):
        print "# # # ERROR: file", data_file, "non-existent"
        logging.critical('file %s - non-existent, skipping', data_file)

    with open( data_file ) as json_file:
        json_data = json.load(json_file)
        json_file.closed
    logging.info('Completed reading: %s', data_file)

    watch_id = json_data['watch_id']
    logging.info('watch_id: %s', watch_id)
    if watch_id not in [ 'asterik_pkt_loss_pct', 'asteriskE2EPLOR' ]:
        logging.warning('NOT %s or %s, exiting', 'asterik_pkt_loss_pct', 'asteriskE2EPLOR')
        sys.exit (0)

    total_hits = json_data['payload']['hits']['total']
    for key,value in json_data.items():
        if key == "payload":
            took_hits = len(value['hits']['hits'])

    print "Took Hits: ", took_hits
    print "Total Hits: ", total_hits

    n = 0
    while n < took_hits:
        logging.info('#')
        logging.info('Event: %d', n)
        cluster             = json_data['payload']['hits']['hits'][n]['_source']['cluster']
        answer_time         = json_data['payload']['hits']['hits'][n]['_source']['answer_time']
        remote_signaling_ip = json_data['payload']['hits']['hits'][n]['_source']['remote_signaling_ip']
        pkt_loss            = json_data['payload']['hits']['hits'][n]['fields']['pkt_loss%'][0]

        str1 = "Watch ID: " + watch_id
        str2 = "Cluster: " + cluster
        str3 = "Answer Time: " + answer_time
        str4 = "Remote Sig. IP: " + remote_signaling_ip
        str5 = "Packet Loss: " + "{0:.2f}".format(pkt_loss)

        logging.info('OG str1: %s', str1)
        logging.info('OG str2: %s', str2)
        logging.info('OG str3: %s', str3)
        logging.info('OG str4: %s', str4)
        logging.info('OG str5: %s', str5)

        #message = ( str1, str2, str3, str4, str5 )
        message = (str3, str4, str5)
        j = "\n"
        MSG = j.join(message)

        logging.info('Pushing Event to DB')
        # Call Push to DB
        push_to_db(cluster,MSG)

        logging.info('Looking up Events >= 3')
        # Lookup Cluster Event
        db_lookup(cluster)

        logging.info('Calling OpsGenie API')
        # Call OpsGenie API
        #call_opsgenie(str2,MSG)
        
        # Disable Email
        #sendemail("Watcher Alert", MSG)
        
        n += 1

        logging.info('#')
        logging.info('END\n#')

    return

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            logging.shutdown
            db.close()
            sys.exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        logging.shutdown
        db.close()
        sys.exit(1)

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

"""
Main Function
"""
if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    # Call to start HTTP Server
    run_http_server()
