#!/usr/bin/python

import sys
sys.path.append('/opt/blobserver')
from settings import mysql_opts

import MySQLdb
from random import seed, randint
seed()

from urllib import unquote_plus
import cgi

def parseQueryString(environ):
    q = environ['QUERY_STRING'].split('&')
    d = {}
    if len(q) > 0:
        for e in q:
            s = e.split('=')
            if len(s) > 1:
                d[s[0]] = unquote_plus('='.join(s[1:]))
    return d

class Encapsulated:
    def __init__(self, request_body):
        s = request_body.split('\n')
        boundary = s[0]
        content_disposition = s[1]
        content_type = s[2]
        header = '\n'.join(s[:4])
        self.data = request_body[len(header)+1:len(request_body)-len(boundary)]

def randomChar():
    #return chr(65+(32*randint(0,1))+randint(0,25))
    return chr(97+randint(0,25))

#vocals = ['A','E','I','O','U','a','e','i','o','u']
vocals = ['a','e','i','o','u']

def randomVocal():
    return vocals[randint(0,len(vocals)-1)]

def randomConsonant():
    c = 'a'
    while c in vocals:
        c = randomChar()
    return c

def randomID():
    return randomConsonant()+randomVocal()+randomConsonant()+randomVocal()+randomConsonant()

def uploadForm(environ, start_response):
    page = """<html>
<body style="padding:20%;">
<form name="upload" method="post" enctype="multipart/form-data">
<input name="blob" type="file" onchange="document.forms['upload'].submit();"/>
</form>
</body>
</html>"""
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [page]

#
# http://www.python.org/dev/peps/pep-0333/
# http://www.online-tutorials.net/mysql/mysql-zugriff-mit-python/sourcecodes-t-130-316.html
#
def upload(environ, start_response):
    # return upload form
    if environ['REQUEST_METHOD'] == 'GET':
        return uploadForm(environ, start_response)
    
    # only accept data from HTTP POST
    elif environ['REQUEST_METHOD'] == 'POST':
        # the environment variable CONTENT_LENGTH may be empty or missing
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0
        request_body = environ['wsgi.input'].read(request_body_size)
        BLOB = Encapsulated(request_body).data
        
        # BLOB too large
        if len(BLOB) > 500*1024: # max 500 KB
            # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
            start_response('413 Request Entity Too Large', [('Content-Type', 'text/plain')])
            return ['413 Request Entity Too Large: Rejecting large BLOB']
        
        # BLOB empty
        if len(BLOB) == 0:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return ['400 Bad Request: Submitted BLOB is empty']
        
        # save BLOB to database
        ID = randomID()
        IP = environ['REMOTE_ADDR']
        mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
        cursor = mysql.cursor()
        cursor.execute("INSERT INTO `%s` (`ID`,`from`,`blob`) VALUES ('%s','%s','%s');" % (mysql_opts['table:blobs'],ID,IP,mysql.escape_string(BLOB)))
        start_response('200 OK', [('Content-Type', 'text/html')])
        return ['Upload complete.<br/>Your BLOB is available here: <a href="download?id='+ID+'">http://blob.interoberlin.de/download?id='+ID+'</a>']
    else:
        # reject anything that is not GET or POST
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['400 Bad Request']

def download(environ, start_response):
    # query mysql database
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    ID = parseQueryString(environ)['id']
    try:
        cursor.execute("SELECT `BLOB` FROM `%s` WHERE `ID`='%s'" % (mysql_opts['table:blobs'],ID)) 
        BLOB = cursor.fetchone()[0]
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [BLOB]
    except:
        start_response("404 Not Found", [('Content-Type', 'text/plain')])
        return ['404 Not Found: Unable to fetch BLOB from database']

def application(environ, start_response):
    if environ['PATH_INFO'] == '/upload':
        return upload(environ, start_response)
    elif environ['PATH_INFO'] == '/download':
        return download(environ, start_response)
    else:
        start_response("302 Moved Permanently", [('Content-Type', 'text/plain'),('Location','http://blob.interoberlin.de/upload')])
        return ['302 Moved Permanently']
