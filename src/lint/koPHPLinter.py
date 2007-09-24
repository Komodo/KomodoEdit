#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, nsError, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from koLintResult import *
from koLintResults import koLintResults
import os, sys, re
import tempfile
import string
import process
import koprocessutils

# php error line format
# \nPHP ERROR NAME: error text in filename.php on line ##\n
# requires php.ini settings
#      display_errors	      = On
#      display_startup_errors = On
# php.ini must reside in os directory (c:\winnt)

class KoPHPCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo PHP Linter"
    _reg_clsid_ = "{F6F8507C-21B0-4047-9E78-A648949B118F}"
    _reg_contractid_ = "@activestate.com/koLinter?language=PHP;1"

    def __init__(self):
        self.phpInfoEx = components.classes["@activestate.com/koAppInfoEx?app=PHP;1"].\
                    getService(components.interfaces.koIPHPInfoEx)

        self._proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
            getService(components.interfaces.nsIProxyObjectManager)
        self._prefSvc = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        self._prefProxy = self._proxyMgr.getProxyForObject(None,
            components.interfaces.koIPrefService, self._prefSvc,
            PROXY_ALWAYS | PROXY_SYNC)
    
    # linting versions are different than what is required for xdebug
    # debugging, so we have our own version checking
    def checkValidVersion(self):
        version = self.phpInfoEx.version
        # last point can be something like 10-beta
        version = tuple([int(x) for x in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups()])
        if version < (4,0,5):
            errmsg = "Could not find a suitable PHP interpreter for "\
                     "linting, need 4.0.5 or later."
            raise COMException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)
        
    def lint(self, request):
        """Lint the given PHP content.
        
        Raise an exception if there is a problem.
        """
        
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd
        
        #print "----------------------------"
        #print "PHP Lint"
        #print text
        #print "----------------------------"
        php = self.phpInfoEx.executablePath
        if php is None:
            errmsg = "Could not find a suitable PHP interpreter for linting."
            raise COMException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

        self.checkValidVersion()

        # save php buffer to a temporary file
        phpfilename = tempfile.mktemp()
        fout = open(phpfilename, 'wb')
        fout.write(text)
        fout.close()

        p = None
        try:
            argv = [php, '-d', 'display_errors=1',
                    '-d', 'display_startup_errors=1',
                    '-d', 'output_buffering=0',
                    '-d', 'xdebug.remote_enable=off',
                    '-d', 'error_reporting=2047',
                    '-q', '-l', phpfilename]
            env = koprocessutils.getUserEnv()
            if self._prefProxy.prefs.hasStringPref("phpConfigFile"):
                ini = self._prefProxy.prefs.getStringPref("phpConfigFile")
                if ini: env["PHPRC"] = ini
            cwd = cwd or None
            # PHP sets stdin, stdout to binary on it's end.  If we do not do
            # the same, some wierd things can happen, most notably with shell
            # comments that end with \r\n.
            p = process.ProcessOpen(argv, mode='b', cwd=cwd, env=env)
            p.stdin.close()
            # XXX The relevant output is either on stdout or stderr. Dunno
            #     which. We should only be parsing over one of the two.
            lines = p.stdout.readlines() + p.stderr.readlines()
        finally:
            os.unlink(phpfilename)
            # For some reason, PHP linter causes an exception on close
            # with errno = 0, will investigate in PHP later.
            try:
                if p: p.close()
            except IOError, e:
                if e.errno == 0:  
                    pass
                else:
                    raise
        
        results = koLintResults()
        if lines:
            datalines = re.split('\r\n|\r|\n',text)
            numLines = len(datalines)
            lines = [l for l in lines if l.find('error') != -1]
            
            for line in lines:
                #print line
                line = line.strip()
                # remove html from error output
                line = re.sub('<.*?>',"",line)
                lineText = line.rfind(' ')
                try:
                    lineNo = int(line[lineText+1:])
                except ValueError, e:
                    continue
                #print "Line Number: ", lineNo
                result = KoLintResult()
                # XXX error in FILENAME at line XXX
                # Previous fix (change  done for bug 42553 -- (change 254015)
                # This fix allows for either "at" or "on" between the
                # filename and the line #
                # Sample error message:
                # PHP Fatal error:  Can't use function return value in write context in C:\home\ericp\lab\komodo\bugs\bz42553a.php on line 3
                m = re.match(r'(.*?)\bin .*?(\b(?:on|at)\s+line\s+\d+)', line)
                if m:
                    result.description = string.join(m.groups())
                else:
                    result.description = line
                result.lineStart = result.lineEnd = lineNo
                result.columnStart = 1
                result.columnEnd = len(datalines[result.lineEnd-1]) + 1
                result.severity = result.SEV_ERROR
                results.addResult(result)
        #print "----------------------------"
        return results

