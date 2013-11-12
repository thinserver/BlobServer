#!/usr/bin/python

import sys
sys.path.append('/opt/blobserver')
from settings import mysql_opts

import MySQLdb
from random import seed, randint
seed()

def parseQueryString(environ):
    q = environ['QUERY_STRING'].split('&')
    d = {}
    if len(q) > 0:
        for e in q:
            s = e.split('=')
            if len(s) > 1:
                d[s[0]] = s[1:]
    return d

def randomID():
    return ''.join([chr(65+(32*randint(0,1))+randint(0,25)) for i in range(6)])

#
# http://www.python.org/dev/peps/pep-0333/
# http://www.online-tutorials.net/mysql/mysql-zugriff-mit-python/sourcecodes-t-130-316.html
#
def upload(environ, start_response):
    # only accept data from HTTP POST
    if environ['REQUEST_METHOD'] != 'POST':
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['400 Bad Request: Use POST to upload']
    
    # make sure a BLOB was submitted
    query = parseQueryString(environ);
    if not 'blob' in query.keys():
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['400 Bad Request: No variable "blob" in submitted data']
    BLOB = query['blob']
    
    # BLOB too large
    if len(BLOB) > 50000:
        # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        start_response('413 Request Entity Too Large', [('Content-Type', 'text/plain')])
        return ['413 Request Entity Too Large: Rejecting large BLOB']
    
    # BLOB empty
    elif len(BLOB) > 0:
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['400 Bad Request: Submitted BLOB is empty']
        
    # BLOB not empty
    ID = randomID()
    IP = environ['REMOTE_ADDR']
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    cursor.execute("INSERT INTO `%s` (`ID`,`from`,`blob`) VALUES ('%s','%s','%s');" % (mysql_opts['table:blobs'],ID,IP,BLOB))
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [ID]

def download(environ, start_response):
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    ID = parseQueryString(environ)['id']
    cursor.execute("SELECT `BLOB` FROM `%s` WHERE `ID`='%s'" % (mysql_opts['table:blobs'],ID)) 
    BLOB = cursor.fetchone()[0]
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [BLOB]

def application(environ, start_response):
    if environ['PATH_INFO'] == '/upload':
        return upload(environ, start_response)
    elif environ['PATH_INFO'] == '/download':
        return download(environ, start_response)
    else:
        start_response("404 Not Found", [('Content-Type', 'text/plain')])
        return ['404 Not Found']

