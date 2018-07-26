#!/usr/bin/python
import MySQLdb

db = MySQLdb.connect(host="127.0.0.1",    # your host, usually localhost
                     user="root",         # your username
                     passwd="letme1n",  # your password
                     db="OpsGenie")        # name of the data base

# you must create a Cursor object. It will let
#  you execute all the queries you need
def calldb(cluster):
    cur = db.cursor()
    sql = "SELECT * FROM `WatcherAlert` WHERE ts BETWEEN TIMESTAMPADD(MINUTE, -30, NOW()) AND NOW() AND `cluster` = %s AND (SELECT COUNT(cluster) FROM `WatcherAlert` WHERE `cluster` = %s) >= 3 ORDER BY 1,3"
    cur.execute(sql, (cluster,cluster))
     
    file = open("alt.txt","w") 
    
    for row in cur.fetchall():
	    print "Cluster: " + row[1]
	    print row[2] + '\n'
	    #print "Timestamp: " + str(row[2])
            file.write("Cluster: " + row[1] + '\n') 
            file.write(row[2] +'\n') 
    file.close()
    db.close()
    return

cluster = "OR5"
calldb(cluster)

#cur = db.cursor()

#cluster = "OR1"
#description = "Some Alert"

# Use all the SQL you like
#sql = "INSERT INTO WatcherAlert (cluster, description) VALUES (%s, %s)"
#cur.execute(sql, (cluster,description))
#db.commit()
#cur.execute("SELECT * FROM `WatcherAlert` WHERE ts BETWEEN TIMESTAMPADD(MINUTE, -30, NOW()) AND NOW()")

# print all the first cell of all the rows
#for row in cur.fetchall():
#	print "Cluster: " + row[1]
#	print "Description: " + row[2]
#	print "Timestamp: " + str(row[3])
#db.close()