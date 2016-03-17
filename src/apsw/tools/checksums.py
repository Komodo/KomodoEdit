#!/usr/bin/env python
#
# See the accompanying LICENSE file.
#
import urllib2
import hashlib
import re

sqlitevers=(
    '3081101',
    '3081100',
    '3081002',
    '3081001',
    '3081000',
    '3080900',
    '3080803',
    '3080802',
    '3080801',
    '3080800',
    '3080704',
    '3080703',
    '3080702',
    '3080701',
    '3080700',
    '3080600',
    '3080500',
    '3080403',
    '3080402',
    '3080401',
    '3080400',
    '3080301',
    '3080300',
    '3080200',
    '3080100',
    '3080002',
    '3080001',
    '3080000',
    '3071700',
    '3071602',
    '3071601',
    '3071600',
    '3071502',
    '3071501',
    '3071500',
    '3071401',
    '3071400',
    '3071300',
    '3071201',
    '3071200',
    '3071100',
    '3071000',
    '3070900',
    '3070800',
    '3070701',
    '3070700',
    '3070603',
    '3070602',
    '3070601',
    '3070600',
    )

# Checks the checksums file

def getline(url):
    for line in open("checksums", "rtU"):
        line=line.strip()
        if len(line)==0 or line[0]=="#":
            continue
        l=[l.strip() for l in line.split()]
        if len(l)!=4:
            print "Invalid line in checksums file:", line
            raise ValueError("Bad checksums file")
        if l[0]==url:
            return l[1:]
    return None

def check(url, data):
    d=["%s" % (len(data),), hashlib.sha1(data).hexdigest(), hashlib.md5(data).hexdigest()]
    line=getline(url)
    if line:
        if line!=d:
            print "Checksums mismatch for", url
            print "checksums file is", line
            print "Download is", d
    else:
        print url,
        if url.endswith(".zip"):
            print "  ",
        print d[0], d[1], d[2]

# They keep messing with where files are in URI - this code is also in setup.py
def fixup_download_url(url):
    ver=re.search("3[0-9]{6}", url)
    if ver:
        ver=int(ver.group(0))
        if ver>=3071600:
            if ver>=3080800:
                year="2015"
            elif ver>=3080300:
                year="2014"
            else:
                year="2013"
            if "/"+year+"/" not in url:
                url=url.split("/")
                url.insert(3, year)
                return "/".join(url)
    return url

for v in sqlitevers:
    # Windows amalgamation
    AURL="https://sqlite.org/sqlite-amalgamation-%s.zip" % (v,)
    AURL=fixup_download_url(AURL)
    try:
        data=urllib2.urlopen(AURL).read()
    except:
        print AURL
        raise
    check(AURL, data)
    # All other platforms amalgamation
    AURL="https://sqlite.org/sqlite-autoconf-%s.tar.gz" % (v,)
    AURL=fixup_download_url(AURL)
    try:
        data=urllib2.urlopen(AURL).read()
    except:
        print AURL
        raise
    check(AURL, data)
