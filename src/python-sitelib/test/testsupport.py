"""
    Support stuff for the test suite in this directory.
"""

import os
import sys
import shutil

def setup():
    # Setup for the test modules.
    # - put process.py on sys.path
    sys.path.insert(0, os.pardir)

    import process
    sys.stdout.write("Setup to test: process.py at '%s'\n"\
                     % process.__file__)
    sys.stdout.write("-"*70 + '\n')


    # Explicitly put the test dir on the PATH so spawning test programs there
    # actually get found (both on Unix were '.' is not implicitly on the PATH
    # and everywhere when testing changing 'cwd').
    os.environ["PATH"] = os.path.abspath(os.curdir) + os.pathsep\
                         + os.environ.get("PATH", "")


def isdir(dirname):
    """os.path.isdir() doesn't work for UNC mount points. Fake it.
    
    # For an existing mount point (want: isdir() == 1)
    os.path.ismount(r"\\crimper\apps") -> 1
    os.path.exists(r"\\crimper\apps") -> 0
    os.path.isdir(r"\\crimper\apps") -> 0
    os.listdir(r"\\crimper\apps") -> [...contents...]
    # For a non-existant mount point (want: isdir() == 0)
    os.path.ismount(r"\\crimper\foo") -> 1
    os.path.exists(r"\\crimper\foo") -> 0
    os.path.isdir(r"\\crimper\foo") -> 0
    os.listdir(r"\\crimper\foo") -> WindowsError
    # For an existing dir under a mount point (want: isdir() == 1)
    os.path.mount(r"\\crimper\apps\Komodo") -> 0
    os.path.exists(r"\\crimper\apps\Komodo") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo") -> 1
    os.listdir(r"\\crimper\apps\Komodo") -> [...contents...]
    # For a non-existant dir/file under a mount point (want: isdir() == 0)
    os.path.ismount(r"\\crimper\apps\foo") -> 0
    os.path.exists(r"\\crimper\apps\foo") -> 0
    os.path.isdir(r"\\crimper\apps\foo") -> 0
    os.listdir(r"\\crimper\apps\foo") -> []  # as if empty contents
    # For an existing file under a mount point (want: isdir() == 0)
    os.path.ismount(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.path.exists(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.listdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> WindowsError
    """
    if sys.platform[:3] == 'win' and dirname[:2] == r'\\':
        if os.path.exists(dirname):
            return os.path.isdir(dirname)
        try:
            os.listdir(dirname)
        except WindowsError:
            return 0
        else:
            return os.path.ismount(dirname)
    else:
        return os.path.isdir(dirname)


def mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not isdir(head):
            mkdir(head)
        if tail:
            #print "mkdir %s" % repr(newdir)
            os.mkdir(newdir)


def copy(src, dst):
    """works the way a good copy should :)
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
    NOTE:
        - This copy CHANGES THE FILE ATTRIBUTES.
    """
    import string, glob, shutil

    assert src != dst, "You are try to copy a file to itself. Bad you! "\
                       "src='%s' dst='%s'" % (src, dst)
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
            if dstFileHead and not isdir(dstFileHead):
                mkdir(dstFileHead)
            if isdir(dstFile):
                dstFile = os.path.join(dstFile, os.path.basename(srcFile))
            if os.path.isfile(dstFile):
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, 0755)
            #print "copy %r %r" % (srcFile, dstFile)
            shutil.copy(srcFile, dstFile)
            # make the new 'dstFile' writeable
            os.chmod(dstFile, 0755)
        elif isdir(srcFile):
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    copy(s, d)
                except (IOError, os.error), why:
                    raise OSError("Can't copy %s to %s: %s"\
                          % (repr(s), repr(d), str(why)))
        elif not usingWildcards:
            raise OSError("Source file %s does not exist" % repr(srcFile))


def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)



