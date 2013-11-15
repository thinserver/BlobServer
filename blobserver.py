#!/usr/bin/python

import sys
import MySQLdb
from random import seed, randint
seed()
from urllib import unquote_plus as unescapeURL
import cgi

logfile = '/var/log/blobserver.log'

def parseQueryString(s):
    q = s.split('&')
    d = {}
    if len(q) > 0:
        for e in q:
            s = e.split('=')
            if len(s) > 1:
                d[s[0]] = unescapeURL('='.join(s[1:]))
    return d

#
# MIME Encapsulation
#
# HTTP POST encapsulates uploaded files
#
class Encapsulated:
    def __init__(self, request_body):
        open(logfile,'a').write(request_body+'\n')
        s = request_body.split('\n')
        boundary = s[0]
        content_disposition = s[1]
        content_type = s[2]
        header = '\n'.join(s[:4])
        self.data = request_body[len(header)+1:len(request_body)-len(boundary)-3]

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
<body style="padding-top: 15%; padding-left: 35%;">
<form name="upload" method="post" enctype="multipart/form-data">
<h1>Upload a file: </h1>
<input name="blob" type="file" onchange="document.forms['upload'].submit();"/>
</form>
</body>
</html>
<!--\n"""+("\n".join([str(key)+": "+str(environ[key]) for key in environ.keys()]))+"\n--!>"
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [page]

#
# http://www.python.org/dev/peps/pep-0333/
# http://www.online-tutorials.net/mysql/mysql-zugriff-mit-python/sourcecodes-t-130-316.html
#
def upload(environ, start_response, mysql_opts):
    
    # reject anything that is not GET or POST
    if environ['REQUEST_METHOD'] not in ['GET','POST']:
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['400 Bad Request']
    
    # upload via form or URL
    if environ['REQUEST_METHOD'] == 'GET':
        query = parseQueryString(environ['QUERY_STRING'])
        if query.has_key('blob'):
            BLOB = query['blob']
        else:
            return uploadForm(environ, start_response)
    
    # upload via HTTP POST
    elif environ['REQUEST_METHOD'] == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            # the environment variable CONTENT_LENGTH may be empty or missing
            request_body_size = 0
        request_body = environ['wsgi.input'].read(request_body_size)
        BLOB = Encapsulated(request_body).data
    
    # BLOB is empty
    if len(BLOB) == 0:
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Submitted BLOB is empty']
    
    # BLOB is too large
    if len(BLOB) > 4*(1024**2):
        # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Rejecting too large BLOB']
    
    # save BLOB to database
    ID = randomID()
    IP = environ['HTTP_X_FORWARDED_FOR']
    agent = environ['HTTP_USER_AGENT']
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    cmd = "INSERT INTO `%s` (`ID`,`from`,`agent`,`blob`,`created`) VALUES ('%s','%s','%s','%s',NOW());" % (mysql_opts['table:blobs'],ID,IP,mysql.escape_string(agent),mysql.escape_string(BLOB))
    open(logfile,'a').write(cmd+'\n')
    cursor.execute(cmd)
    start_response('200 OK', [('Content-Type', 'text/html')])
    
    #
    # return URL and QR code
    # http://davidshimjs.github.io/qrcodejs/
    #
    return ["""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta name="id" content=\""""+ID+"""\"/>
<script>
"""+open(environ['SCRIPT_FILENAME'][:-len('/blobserver.py')]+'/qrcode.js').read()+"""
</script>
</head>
<body id='body'>
Upload complete.<br/>
Your BLOB is available here: 
<a href="http://blob.interoberlin.de/download?id="""+ID+"""\">http://blob.interoberlin.de/download?id="""+ID+"""</a><br/>
<a href="upload">Upload more</a>
<br/><br/>
<script>
new QRCode(document.getElementById('body'),'http://blob.interoberlin.de/download?id="""+ID+"""'); 
</script>
</body>
</html>"""]

#
# download?id=vebob
#
# return BLOB
#
def download(environ, start_response, mysql_opts):
    # id specified ?
    query = parseQueryString(environ['QUERY_STRING'])
    if not query.has_key('id'):
        start_response('200 OK', [('Content-Type', 'text/html')])
        return ['Usage: <a href="download?id=vebob">download?id=abcde</a>']
    
    # query mysql database
    mysql = MySQLdb.connect(mysql_opts['host'], mysql_opts['user'], mysql_opts['pass'], mysql_opts['db'])
    cursor = mysql.cursor()
    ID = query['id']
    try:
        # fetch BLOB
        cursor.execute("SELECT `BLOB` FROM `%s` WHERE `ID`='%s'" % (mysql_opts['table:blobs'],ID)) 
        BLOB = cursor.fetchone()[0]
        
        # update access counter
        cursor.execute("UPDATE `%s` SET access_counter = access_counter + 1 WHERE `ID`='%s'" % (mysql_opts['table:blobs'],ID))
        cursor.execute("UPDATE `%s` SET accessed = NOW() WHERE `ID`='%s'" % (mysql_opts['table:blobs'],ID))
        
        # return BLOB
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [BLOB]
    except:
        start_response("404 Not Found", [('Content-Type', 'text/plain')])
        return ['404 Not Found: Unable to fetch BLOB from database']

#
# WSGI entry point
#
def application(environ, start_response):
    
    sys.path.append(environ['SCRIPT_FILENAME'][:-len('/blobserver.py')])
    from settings import mysql_opts
    
    if environ['PATH_INFO'] == '/upload':
        return upload(environ, start_response, mysql_opts)
    elif environ['PATH_INFO'] == '/download':
        return download(environ, start_response, mysql_opts)
    else:
        start_response("302 Moved Permanently", [('Location','http://blob.interoberlin.de/upload')])
        return []
