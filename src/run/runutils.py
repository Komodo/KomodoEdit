# Copyright (c) 2000-2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
"""
Utilities for running programs.
"""

import os
import sys
import tempfile
import threading

from xpcom import components, nsError, ServerException
from xpcom.server import UnwrapObject

import process
import mozutils

if sys.platform == "darwin":
    def escapecmd(cmd):
        return cmd.replace('"', '\\"').replace('$', '\\$')
    
    def quotevalue(value):
        if "'" in value:
            for ch in "\\$!": # special shell chars to escape
                value = value.replace(ch, '\\'+ch)
            return '"%s"' % value
        else:
            return "'%s'" % value

def createConsoleLaunchScript(actualCommand, cwd, envDict):
    # A shell script that will be run is created.  The script
    # adds the "Press any key to continue..." feature and
    # ensures that the correct return value is returned.
    if sys.platform.startswith("win"):
        scriptFileName = tempfile.mktemp() + ".bat"
        bat = open(scriptFileName, "w")
        bat.write("@echo off\n")
        # Escape '%' once for being on a "call ..." line.
        actualCommand = actualCommand.replace("%", "%%")
        bat.write("call %s\n" % actualCommand)
        bat.write("set KOMODO_COMMAND_ERRORLEVEL=%ERRORLEVEL%\n")
        bat.write("pause\n")
        # Must "exit" with the last return value to ensure that
        # cmd.exe will return that value
        #XXX does the correct retval actually get returned?
        bat.write("exit %KOMODO_COMMAND_ERRORLEVEL%\n")
        bat.close()
    elif sys.platform == "darwin":
        # We can use applescript to run a shell command in a new
        # Terminal.app window. The problem is that the relevant
        # AppleScript command does not wait for the command to
        # terminate. We need to resort to locks and temp files to
        # (a) wait for termination and (b) get the retval.
        #
        # 1. lockfile foo.lock
        # 2. run foo.applescript to run the following in the terminal:
        #    - run the user's command
        #    - write the retval to a temp file
        #    - rm -f foo.lock
        # 3. lockfile -1 foo.lock  # i.e. wait for foo.lock to get rm'd
        # 4. exit with the retval
        #
        base = tempfile.mktemp()
        shEnvFile = base+".environ.sh"
        cshEnvFile = base+".environ.csh"
        data = {
            "lockfile": base+".lock",
            "retvalfile": base+".retval",
            "applescriptfile": base+".applescript",
            "cmd": escapecmd(actualCommand),
            "cwdcmd": "",
            "shenvfile": shEnvFile,
            "cshenvfile": cshEnvFile,
            "envcmd": (r"echo \$shell | grep csh >/dev/null "
                       r" && source %s "
                       r" || source %s" % (cshEnvFile, shEnvFile)),
        }
        if cwd:
            data["cwdcmd"] = r'cd \"%s\";' % cwd

        fenv = open(shEnvFile, "w")
        for name, value in envDict.items():
            fenv.write('    %s=%s; export %s\n' % (name, quotevalue(value), name))
        fenv.close()
        fenv = open(cshEnvFile, "w")
        for name, value in envDict.items():
            fenv.write('    setenv %s %s\n' % (name, quotevalue(value)))
        fenv.close()

        scriptFileName = base+".sh"
        script = open(scriptFileName, "w")
        script.write(r"""
LOCKFILE='%(lockfile)s'
RETVALFILE='%(retvalfile)s'
APPLESCRIPTFILE='%(applescriptfile)s'
SHENVFILE='%(shenvfile)s'
CSHENVFILE='%(cshenvfile)s'

rm -f $LOCKFILE
lockfile $LOCKFILE
cat >$APPLESCRIPTFILE <<HERE
tell app "Terminal"
    do script "clear; %(cwdcmd)s (%(envcmd)s; %(cmd)s); echo \$?>$RETVALFILE; echo Press RETURN to continue ...; /bin/sh -c read RETURN; rm -f $LOCKFILE; exit"
    delay 0.2
    activate
end tell
HERE
#echo debug: running AppleScript in $APPLESCRIPTFILE:
#cat $APPLESCRIPTFILE
#echo debug: which will source one of $SHENVFILE:
#cat $SHENVFILE
#echo debug: or $CSHENVFILE:
#cat $CSHENVFILE
osascript $APPLESCRIPTFILE
#echo debug: waiting for Terminal to finish...
lockfile -1 $LOCKFILE
RETVAL=`cat $RETVALFILE`
#echo debug: retval was \"$RETVAL\"
rm -f $RETVALFILE $LOCKFILE $SHENVFILE $CSHENVFILE $APPLESCRIPTFILE
#XXX Need Komodo to register with OSA (bug 37377).
#osascript -e 'tell app "Komodo" to activate'
exit $RETVAL""" % data)
        script.close()

    else:
        # Create a bash script that will be run.
        scriptFileName = tempfile.mktemp() + ".sh"
        script = open(scriptFileName, "w")
        script.write("#!/bin/sh\n")
        script.write("%s\n" % actualCommand)
        script.write("set KOMODO_COMMAND_RETVAL=$?\n")
        script.write("export KOMODO_COMMAND_RETVAL\n")
        if sys.platform.startswith("sunos"):
            # Solaris /bin/sh is doesn't understand -n
            script.write("echo Press ENTER to continue . . .\\c\n")
        else:
            script.write("echo -n Press ENTER to continue . . .\n")
        script.write("read KOMODO_DUMMY\n")
        script.write("unset KOMODO_DUMMY\n")
        script.write("exit $KOMODO_COMMAND_RETVAL\n")
        script.close()
    return scriptFileName


class KoRunProcess(object):

    _com_interfaces_ = [components.interfaces.koIRunProcess]

    def __init__(self, cmd, cwd=None, env=None):
        self._process = process.ProcessOpen(cmd, cwd=cwd, env=env)

        # Stdout, stderr results get set in the communicate call.
        self._stdoutData = None
        self._stderrData = None
        # Condition object for waiting on the process.
        self.__communicating_event = None
        self.uuid = mozutils.generateUUID()

    def close(self):
        self._process.close()

    def kill(self, exitCode=-1, gracePeriod=None, sig=None):
        self._process.kill(exitCode, gracePeriod, sig)

    def wait(self, timeout=None):
        try:
            retval = self._process.wait(timeout)
            if self.__communicating_event:
                # communicate() was called, need to wait until the
                # communicate call is finished before returning to ensure
                # the stdout, stderr data is ready for use.
                self.__communicating_event.wait()
            return retval
        except process.ProcessError, ex:
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

    def write_stdin(self, input, closeAfterWriting=False):
        """Write data to the process stdin handle."""
        self._process.stdin.write(input)
        if closeAfterWriting:
            self._process.stdin.close()

    # Override process.communicate() with our own method.
    # We do this so we can retain the stdout and stderr results on the
    # process object.
    def communicate(self, input=None):
        # Create a condition, thus if wait is called, it can wait on this
        # condition instead of the process, this will ensure the stdout, stderr
        # data is properly set by the time wait() returns.
        self.__communicating_event = threading.Event()
        try:
            if input:
                # Encode the input using the filesystem's default encoding. This
                # fixes problems where unicode input was not properly passed to
                # the running process:
                # http://bugs.activestate.com/show_bug.cgi?id=74750
                input = input.encode(sys.getfilesystemencoding())
            try:
                stdoutData, stderrData = self._process.communicate(input)
            except IOError, ex:
                if ex.errno == 32: # Broken pipe
                    # If we get this exception, most likely the process has
                    # terminated abruptly (while we're trying to still read
                    # the data).
                    return ("", "")
                raise
            encodingSvc = components.classes['@activestate.com/koEncodingServices;1'].\
                             getService(components.interfaces.koIEncodingServices)
            # Set our internal stdout, stderr objects, so the caller can get the
            # results through the getStdout and getStderr methods below.
            self._stdoutData, enc, bom = encodingSvc.getUnicodeEncodedStringUsingOSDefault(stdoutData)
            self._stderrData, enc, bom = encodingSvc.getUnicodeEncodedStringUsingOSDefault(stderrData)
            return self._stdoutData, self._stderrData
        finally:
            self.__communicating_event.set()

    ##
    # @deprecated since Komodo 4.3.0
    def readStdout(self):
        import warnings
        warnings.warn("process.readStdout() is deprecated, use "
                      "process.getStdout() instead.",
                      DeprecationWarning)
        try:
            return self._process.stdout.read()
        except ValueError:
            # stdout socket has been closed
            data = self._stdoutData
            if data is not None:
                self._stdoutData = ""
                return data
            raise

    ##
    # @deprecated since Komodo 4.3.0
    def readStderr(self):
        import warnings
        warnings.warn("process.readStderr() is deprecated, use "
                      "process.getStderr() instead.",
                      DeprecationWarning)
        try:
            return self._process.stderr.read()
        except ValueError:
            # stdout socket has been closed
            data = self._stderrData
            if data is not None:
                self._stderrData = ""
                return data
            raise

    ##
    # @since Komodo 4.3.0
    def getStdout(self):
        return self._stdoutData or ""

    ##
    # @since Komodo 4.3.0
    def getStderr(self):
        return self._stderrData or ""



class KoTerminalProcess(KoRunProcess):

    _terminal = None

    def linkIOWithTerminal(self, terminal):
        # Need to unwrap the terminal handler because we are not actually
        # passing in koIFile xpcom objects as described by the API, we are
        # using the subprocess python file handles instead.
        self._terminal = UnwrapObject(terminal)
        self._terminal.hookIO(self._process.stdin, self._process.stdout,
                              self._process.stderr, "KoTerminalProcess")

    # Override the KoRunProcess.wait() method.
    def wait(self, timeout=None):
        retval = KoRunProcess.wait(self, timeout)
        if self._terminal:
            # Need to wait until the IO is fully synchronized (due to threads)
            # before returning. Otherwise additional data could arrive after
            # this call returns.
            # 
            # Set timeout to 5 seconds due to bugs 89280 and 88439
            self._terminal.waitForIOToFinish(timeout=5)
            self._terminal = None
        return retval

    def waitAsynchronously(self, runTerminationListener):
        t = threading.Thread(target=_terminalProcessWaiter,
                             args=(self, runTerminationListener))
        t.setDaemon(True)
        t.start()

def _terminalProcessWaiter(runProcess, runListener):
    try:
        if not runProcess._terminal:
            # There is no terminal reading the stdout/stderr, so we need to
            # ensure these io channels still get read in order to stop the
            # possibility of the process stdout/stderr buffers filling up and
            # blocking the wait call.
            runProcess.communicate()
        if runListener:
            retval = runProcess.wait(None)
    except process.ProcessError, ex:
        retval = ex.errno  # Use the error set in the exception.
    if runListener:
        @components.ProxyToMainThread
        def fireCallback(listener, rval):
            listener.onTerminate(rval)
        fireCallback(runListener, retval)
