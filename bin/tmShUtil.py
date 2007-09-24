#!/usr/bin/env python

# Some additions (or improvements) to Python's std "shutil" module:
# 
#    Which      - like the Unix "which" command
#    WhichFollowSymLinks
#    Mkdir      - like "mkdir -p" plus a little
#    Copy       - more like "cp"
#

import sys, os


#---- globals

verbosity = 1
out = sys.stdout  # can be overridden to redirect all output from this module



#---- the utils

def Which(exeName, path=None):
    """Like the Unix 'which' command: find absolute path to given executable.
    If an absolute path cannot be found then the bare exe name is returned.
    Optionally a specific path on which to search can be given.
    """
    # first, if on Windows, look up the Path in the "App Paths" registry
    if sys.platform.startswith('win'):
        import _winreg
        try:
            ret = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"\
                "\\" + exeName + ".exe")
            # And quote the name incase it has spaces.
            return '"' + ret + '"'
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
            exts = [".EXE", ".COM", ".BAT"]
    else:
        exts = [""]
    # file name cannot have path separators because PATH lookup does not
    # work that way
    if os.sep in exeName or os.altsep and os.altsep in exeName:
        return None
    for dirName in path:
        # check to see if given exeName already has a known extension on it
        exeRoot, exeExt = os.path.splitext(exeName)
        for ext in exts:
            if exeExt.lower() == ext.lower():
                absExeName = os.path.join(dirName, exeName)
                if os.path.isfile(absExeName):
                    return os.path.normpath(absExeName)
        # try looking by adding each of the valid exts
        for ext in exts:
            absExeName = os.path.join(dirName, exeName+ext)
            if os.path.isfile(absExeName):
                return os.path.normpath(absExeName)
    else:
        return exeName


def WhichFollowSymLinks(exeName, path=None):
    """Like the Unix 'which' command except symlinks are followed"""
    p = os.path
    fullExeName = Which(exeName, path)
    while p.islink(fullExeName):
        fullExeName = p.normpath( p.join(p.dirname(fullExeName),
            os.readlink(fullExeName)) )
        print fullExeName
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
        if verbosity > 1:
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
            if verbosity > 1:
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




