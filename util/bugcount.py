#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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





