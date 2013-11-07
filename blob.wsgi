#!/usr/bin/python

import sys
sys.path.append('/opt/BlobServer')
from settings import mysql_opts

import MySQLdb
from random import seed, randint
seed()

def randchar():
	return chr(65+(32*randint(0,1))+randint(0,25))

def upload(environ, start_response):
    BLOB = "Test"
    if len(BLOB) > 50000:
        # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        # HTTP RESPONSE CODE 413: Request Entity Too Large
        return None
    elif len(BLOB) > 0:
        ID = ''.join([randchar() for i in range(6)])
        IP = "1.2.3.4"
        mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
        cursor = mysql.cursor()
        cursor.execute("INSERT INTO `Lymbo` (`ID`,`IP`,`BLOB`) VALUES ('%s','%s','%s');" % (ID,IP,BLOB))
	start_response('200 OK', [('content-type', 'text/plain')])
        return ID 
    else:
	start_response('200 OK', [('content-type', 'text/plain')])
        return "Error: empty BLOB"

def download(environ, start_response):
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    ID = "TEST"
    cursor.execute("SELECT `BLOB` FROM `Lymbo` WHERE `ID`=%s"% (ID)) 
    BLOB = cursor.fetchone()[0]
    start_response('200 OK', [('content-type', 'text/plain')])
    return [BLOB]

def application(environ, start_response):
    return upload(environ, start_response)

