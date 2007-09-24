#!/usr/bin/env python
# Copyright (c) 2003-2006 ActiveState Software Inc.

"""
    bugcount - dump a list of numbers of Komodo bugs for various categories
    
    Usage:
        bugcount [<options>...]

    Options:
        -h, --help          Print this help and exit.
        --version           Print the version of this script and exit.
        -v, --verbose       Increase the output verbosity.
"""

import os
import sys
import getopt
import types
import urllib


#---- exceptions

class BugCountError(Exception):
    pass


#---- logging system

class Logger:
    DEBUG, INFO, WARN, ERROR, FATAL = range(5)
    def __init__(self, name, level=None, streamOrFileName=sys.stderr):
        self.name = name
        if level is None:
            self.level = self.WARN
        else:
            self.level = level
        if type(streamOrFileName) == types.StringType:
            self.stream = open(streamOrFileName, 'w')
            self._opennedStream = 1
        else:
            self.stream = streamOrFileName
            self._opennedStream = 0
    def __del__(self):
        if self._opennedStream:
            self.stream.close()
    def _getLevelName(self, level):
        levelNameMap = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARN: "WARN",
            self.ERROR: "ERROR",
            self.FATAL: "FATAL",
        }
        return levelNameMap[level]
    def setLevel(self, level):
        self.level = level
    def isEnabled(self, level):
        return level >= self.level
    def isDebugEnabled(self): return self.isEnabled(self.DEBUG)
    def isInfoEnabled(self): return self.isEnabled(self.INFO)
    def isWarnEnabled(self): return self.isEnabled(self.WARN)
    def isErrorEnabled(self): return self.isEnabled(self.ERROR)
    def isFatalEnabled(self): return self.isEnabled(self.FATAL)
    def log(self, level, msg, *args):
        if level < self.level:
            return
        message = "%s: %s: " % (self.name, self._getLevelName(level).lower())
        message = message + (msg % args) + "\n"
        self.stream.write(message)
        self.stream.flush()
    def debug(self, msg, *args):
        self.log(self.DEBUG, msg, *args)
    def info(self, msg, *args):
        self.log(self.INFO, msg, *args)
    def warn(self, msg, *args):
        self.log(self.WARN, msg, *args)
    def error(self, msg, *args):
        self.log(self.ERROR, msg, *args)
    def fatal(self, msg, *args):
        self.log(self.FATAL, msg, *args)



#---- global data

_version_ = (0, 1, 0)
log = Logger("bugcount", Logger.INFO)



#---- internal routines and classes

### Jimmy in our own urlopener that uses the appropriate
### bugs.activestate.com cookie.
##class AppURLopener(urllib.FancyURLopener):
##    def __init__(self, cookie=None, *args):
##        urllib.FancyURLopener.__init__(self, *args)
##        if cookie:
##            self.addheader("Cookie", cookie)
##_cookie = "ASPSESSIONIDGGGQGOSO=EEKFJBBCFBDCAFJGPDKMLJDO"
##urllib._urlopener = AppURLopener(_cookie)


def _numBugsForNamedSearch(name):
    pass
    # XXX should learn how to do this via SQL
##    uname = urllib.quote_plus(name)
##    url = "http://bugs.activestate.com/Komodo/buglist.cgi?"\
##          "submit=Search&namedcmd=%s&cmdtype=runnamed" % uname
##    log.debug("openning url '%s'" % url)
##    content = urllib.urlopen(url).read()
##    print "XXX content:", content
##    return 0



#---- module API

def bugcount():
    pass
##    nrBugs = _numBugsForNamedSearch("nr")
##    print "Bugs for next release: %d" % nrBugs
##    toTriageBugs = _numBugsForNamedSearch("not yet triaged")
##    print "Bugs to triage: %d" % toTriageBugs



#---- mainline

def main(argv):
    try:
        optlist, args = getopt.getopt(argv[1:], 'hVv',
            ['help', 'version', 'verbose'])
    except getopt.GetoptError, msg:
        log.error("%s. Your invocation was: %s", msg, argv)
        log.error("Try 'bugcount --help'.")
        return 1
    for opt, optarg in optlist:
        if opt in ('-h', '--help'):
            sys.stdout.write(__doc__)
            return 0
        elif opt in ('-V', '--version'):
            print "bugcount %s" % '.'.join([str(i) for i in _version_])
            return 0
        elif opt in ('-v', '--verbose'):
            log.setLevel(Logger.DEBUG)

    return bugcount()


if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0])
    sys.exit( main(sys.argv) )





