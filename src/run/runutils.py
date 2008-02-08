# Copyright (c) 2000-2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
"""
Utilities for running programs.
"""

import os, sys
import tempfile
import logging


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
        # Escape '%' once for being in a batch file plus once for
        # being on a "call ..." line.
        actualCommand = actualCommand.replace("%", "%%%%")
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
