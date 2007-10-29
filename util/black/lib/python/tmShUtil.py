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

# Some additions (or improvements) to Python's std "shutil" module:
# 
#    Which      - like the Unix "which" command
#    WhichFollowSymLinks
#    Mkdir      - like "mkdir -p" plus a little
#    Copy       - more like "cp"
#    RmTree     - like "rm -rf <dirname>"
#    
#    RunCommands - run a given set of commands s.t. stdio redirection works
#    RunInContext - run a given set of commands in a given environment
#

import sys, os, tempfile, shutil


#---- globals

verbosity = 0     # <0==quiet, 0==normal, >0==versbose
out = sys.stdout  # can be overridden to redirect all output from this module



#---- the utils

def Which(exeName, path=None):
    """Like the Unix 'which' command: find absolute path to given executable.
    If an absolute path cannot be found then the bare exe name is returned.
    Optionally a specific path on which to search can be given.
    """
    # first, if on Windows, look up the Path in the "App Paths" registry
    #XXX does this happen *before* or *after* PATH lookup on Windows???
    if sys.platform.startswith('win'):
        import _winreg
        try:
            ret = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"\
                "\\" + exeName + ".exe")
            return ret
        except _winreg.error:
            pass
    # otherwise use the PATH environment variable
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)
    # windows has the concept of a list of extensions (PATHEXT env var)
    if sys.platform.startswith("win"):
        pathExt = os.environ.get("PATHEXT", None)
        if pathExt:
            exts = pathExt.split(os.pathsep)
        else:
            exts = [".COM", ".EXE", ".BAT"]
        # .DLL is a special case, "start foo.dll" will launch foo.dll
        # but "start foo" will never launch foo.dll.
        exts.append(".DLL")
    else:
        exts = [""]
    # file name cannot have path separators because PATH lookup does not
    # work that way
    if os.sep in exeName or os.altsep and os.altsep in exeName:
        return None
    for dirName in path:
        # on windows the dirName *could* be quoted, drop the quotes
        if sys.platform.startswith("win") and\
           len(dirName) >= 2 and\
           dirName[0] == '"' and dirName[-1] == '"':
            dirName = dirName[1:-1]
        # check to see if given exeName already has a known extension on it
        exeRoot, exeExt = os.path.splitext(exeName)
        for ext in exts:
            if exeExt.lower() == ext.lower():
                absExeName = os.path.join(dirName, exeName)
                if os.path.isfile(absExeName):
                    return os.path.normpath(absExeName)
        # try looking by adding each of the valid exts (see .DLL note above)
        for ext in [ext for ext in exts if ext.upper() != ".DLL"]:
            absExeName = os.path.join(dirName, exeName+ext)
            if os.path.isfile(absExeName):
                return os.path.normpath(absExeName)
    else:
        return None


def WhichFollowSymLinks(exeName, path=None):
    """Like the Unix 'which' command except symlinks are followed"""
    p = os.path
    fullExeName = Which(exeName, path)
    if fullExeName is not None:
        while p.islink(fullExeName):
            fullExeName = p.normpath( p.join(p.dirname(fullExeName),
                os.readlink(fullExeName)) )
    return fullExeName


def Mkdir(newdir):
    """mymkdir: works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    global verbosity

    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise InstallError("a file with the same name as the desired " \
            "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)
        if verbosity > 0:
            print "mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


def Copy(src, dst):
    """mycopy: works the way a good copy should:
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
    """
    import string, glob, shutil
    global verbosity

    # determine if filename wildcarding is being used
    # (only raise error if non-wildcarded source file does not exist)
    if string.find(src, '*') != -1 or \
       string.find(src, '?') != -1 or \
       string.find(src, '[') != -1:
        usingWildcards = 1
        srcFiles = glob.glob(src)
    else:
        usingWildcards = 0
        srcFiles = [src]

    for srcFile in srcFiles:
        if os.path.isfile(srcFile):
            if usingWildcards:
                srcFileHead, srcFileTail = os.path.split(srcFile)
                srcHead, srcTail = os.path.split(src)
                dstHead, dstTail = os.path.split(dst)
                if dstTail == srcTail:
                    dstFile = os.path.join(dstHead, srcFileTail)
                else:
                    dstFile = os.path.join(dst, srcFileTail)
            else:
                dstFile = dst
            dstFileHead, dstFileTail = os.path.split(dstFile)
            if not os.path.isdir(dstFileHead):
                Mkdir(dstFileHead)
            if verbosity > 0:
                print "copy %s to %s" % (repr(srcFile), repr(dstFile))
            if os.path.isfile(dstFile):
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, 0755)
            shutil.copy(srcFile, dstFile)
        elif os.path.isdir(srcFile):
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                Mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    Copy(s, d)
                except (IOError, os.error), why:
                    raise InstallError("Can't copy %s to %s: %s"\
                          % (repr(s), repr(d), str(why)))
        elif not usingWildcards:
            raise InstallError("Source file %s does not exist" % repr(srcFile))


def _RmTree_OnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def RmTree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _RmTree_OnError)


def RunCommands(commands):
    """Run the given commands such that output redirection actually works
    on all platforms.

    A child shell is spawned in which to set the environment and run the
    commands.
        "commands" is a list of shell commands.
    """
    import types, tempfile, sys, os
    if type(commands) != types.ListType:
        raise "The 'commands' argument must be of type ListType."
    elif len(commands) == 0:
        raise "No commands to run.";
    elif sys.platform.startswith("win"):
        # With cmd.exe there is no nice way to do this, so must create a batch
        # file which appends the commands after the given environment script.
        batFileName = tempfile.mktemp() + ".bat"
        bat = open(batFileName, "w")
        bat.write("@echo off\n")
        for command in commands:
            bat.write(command + "\n")
        # Must "exit" with the last return value to ensure that
        # cmd.exe will return that value
        bat.write("exit %ERRORLEVEL%\n")
        bat.close()
        cmdLine = "cmd /C %s" % batFileName
        if verbosity > 0:
            out.write("running '''%s'''...\n" % "\n".join(commands))
            out.flush()
        retval = os.system(cmdLine)
        os.unlink(batFileName)
        return retval
    else:
        cmdLine = "%s" % "; ".join(commands)
        if verbosity > 0:
            out.write("running '%s'...\n" % cmdLine)
            out.flush()
        return os.system(cmdLine)

def retvalFromStatus(status):
    if hasattr(os, "WIFEXITED") and os.WIFEXITED(status) \
       and hasattr(os, "WEXITSTATUS"):
        return os.WEXITSTATUS(status)
    else:
        return status

def RunInContext(envScript, commands):
    """Run the given commands in the context of the given environment script.

    A child shell is spawned in which to set the environment and run the
    commands.
        "envScript" is the filename of an environment script (i.e. a .bat
            file on Windows, a .sh file on linux)
        "commands" is a list of shell commands.
    """
    import types
    if type(commands) not in (types.ListType, types.TupleType):
        raise TypeError("The 'commands' argument must be a list or tuple.\n")
    elif len(commands) == 0:
        raise ValueError("No commands to run: commands=%s\n" % commands);
    elif sys.platform.startswith("win"):
        #XXX This only work on WinNT/2K. Should check for that.
        # With cmd.exe there is no nice way to do this, so must create a batch
        # file which appends the commands after the given environment script.
        batFileName = tempfile.mktemp() + ".bat"
        shutil.copy2(envScript, batFileName)
        bat = open(batFileName, "a")
        for command in commands:
            bat.write(command + "\n")
        # Must "exit" with the last return value to ensure that
        # cmd.exe will return that value
        bat.write("exit %ERRORLEVEL%")
        bat.close()
        retval = os.system("cmd /C %s" % batFileName) # always returns 0
        os.unlink(batFileName)
        return retval
    else:
        # On Solaris, os.system runs sh rather than bash.
        # If we *did* run via "sh" then we'd first have to change all
        # the envScript generation to use:
        #   FOO=bar; export FOO
        # rather than the current
        #   export FOO=bar
        #
        # TODO: Quote "'" and "\".
        cmdLine = "bash --norc --noprofile -c '(source %s; %s)'" % (envScript, "; ".join(commands))
        status = os.system(cmdLine)
        retval = retvalFromStatus(status)
        return retval

