#!/usr/bin/python
import MySQLdb
import crayons
import csv
import sys
import os

db = MySQLdb.connect(host="127.0.0.1",    # your host, usually localhost
                     user="root",         # your username
                     passwd="letme1n",  # your password
                     db="aws")        # name of the data base

def calldb():
    
    cur = db.cursor()
    instance = []
    sql_1 = "select aws_host from instances where aws_host NOT IN (select Hostname from nagios)"
    cur.execute(sql_1)
    for aws_host in cur.fetchall():
        instance.append(aws_host[0])
        #print 'sql_1 -> ', aws_host[0]

    if os.path.isfile('checks.csv'):
        print "checks.csv exists"
    else:
        print "Creating new file with header"
        with open('checks.csv', 'w') as csv_header:
            writer = csv.writer(csv_header)
            writer.writerow(["hostname", "services", "nagios_enabled"])
        csv_header.close()

    sql_2 = "SELECT DISTINCT Hostname FROM nagios order by Hostname"
    cur.execute(sql_2)
    for host in cur.fetchall():
        h = host[0]
        #print 'sql_2 -> ', h
        s = ''
        sql_3 = "SELECT Service FROM nagios WHERE Hostname = %s"
        cur.execute(sql_3, [h])
        for service in cur.fetchall():
            s += service[0].rstrip() + ','

        csv_line = (h, s.rstrip(','), 'Y')
        with open('checks.csv', "a") as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            writer.writerow(csv_line)
        csv_file.close()

    for i in instance:
        csv_line = (i, 'NO_SERVICES_FOUND','N')
        with open('checks.csv', "a") as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            writer.writerow(csv_line)
        csv_file.close()
        #exit(1)
    db.close()
    return

calldb()
