#!/usr/bin/python

from settings import mysql_opts
import MySQLdb

def upload(environ, start_response):
    BLOB = "Test"
    if len(BLOB) > 50000:
        # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        # HTTP RESPONSE CODE 413: Request Entity Too Large
        return None
    elif len(BLOB) > 0:
        ID = "TEST"
        IP = "1.2.3.4"
        mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
        cursor = mysql.cursor()
        cursor.execute("INSERT INTO `Lymbo` (`ID`,`IP`,`BLOB`) VALUES ('%s','%s','%s');", ID,IP,BLOB)
        return ID 
    else:
        return None

def download(environ, start_response):
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    ID = "TEST"
    cursor.execute("SELECT `BLOB` FROM `Lymbo` WHERE `ID`=%s", ID) 
    BLOB = cursor.fetchone()[0]
    start_response('200 OK', [('content-type', 'text/plain')])
    return [BLOB]

def application(environ, start_response):
    return upload(environ, start_response)

