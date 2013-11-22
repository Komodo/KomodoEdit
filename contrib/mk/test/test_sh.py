#!/usr/bin/env python
# Copyright (c) 2004-2007 ActiveState Software Inc.

"""Test mklib/sh.py (shell utilities)."""

import sys
import os
from os.path import join
import unittest
import tempfile
import stat
import re
import time



class Error(Exception):
    pass


#---- internal support routines

def _getumask():
    oldumask = os.umask(077)
    os.umask(oldumask)
    return oldumask

def _run(cmd):
    DEBUG = False
    if DEBUG: print "running '%s'" % cmd
    if DEBUG:
        redirect = ""
    elif sys.platform == "win32":
        redirect = " >nul 2>&1"
    else:
        redirect = " >/dev/null 2>&1"
    retval = os.system(cmd+redirect)
    if retval:
        raise Error("error running '%s': retval=%r (see DEBUG var in _run())"
                    % (cmd+redirect, retval))

def _write(path, content):
    f = open(path, 'w')
    try:
        f.write(content)
    finally:
        f.close()

def _read(path):
    f = open(path, 'r')
    try:
        return f.read()
    finally:
        f.close()


#---- test case(s)

class CpTestCase(unittest.TestCase):
    #TODO: Could not use sh2.py for APy debug package install of a
    #      matching partial overlay tree into an existing tree. Dunno what
    #      the right answer is for that.
    #TODO: Test unicode paths.
    #TODO: Testing the logging output scenarios would be good.

    def setUp(self):
        # Create a temporary directory for testing.
        self.startdir = os.getcwd()
        self.tmpdir = tempfile.mktemp()
        os.mkdir(self.tmpdir)
        os.chdir(self.tmpdir)

    def tearDown(self):
        # Clean up temporary directory.
        os.chdir(self.startdir)
        if sys.platform.startswith("win"):
            _run('attrib -R /s "%s"' % self.tmpdir)
            _run('rd /s/q "%s"' % self.tmpdir)
        else:
            _run('chmod -R 0777 "%s"' % self.tmpdir)
            _run('rm -rf "%s"' % self.tmpdir)

    def assertFile(self, path, content=None, mode=None, mtime=None,
                   atime=None):
        self.failIf(not os.path.isfile(path))
        if content is not None:
            self.failIf(_read(path) != content)
        if mode is not None:
            actual_mode = stat.S_IMODE(os.stat(path).st_mode)
            self.failIf(actual_mode != mode,
                        "file '%s' does not have the expected mode: "
                        "expected=%s, actual=%s"
                        % (path, oct(mode), oct(actual_mode)))
        if mtime is not None:
            actual_mtime = os.stat(path).st_mtime
            self.failIf(actual_mtime != mtime,
                        "file '%s' does not have the expected mtime: "
                        "expected=%s, actual=%s"
                        % (path, mtime, actual_mtime))
        if atime is not None:
            actual_atime = os.stat(path).st_atime
            self.failIf(actual_atime != atime,
                        "file '%s' does not have the expected atime: "
                        "expected=%s, actual=%s"
                        % (path, atime, actual_atime))

    def assertDir(self, path, files=None, mode=None, mtime=None, atime=None):
        self.failIf(not os.path.isdir(path))
        if files is not None:
            actual_files = os.listdir(path)
            actual_files.sort()
            files.sort()
            if sys.platform == "win32":
                actual_files = [f.lower() for f in actual_files]
                files = [f.lower() for f in files]
            self.failIf(actual_files != files,
                        "directory '%s' does not contain the expected files: "
                        "expected=%r, actual=%r" % (path, files, actual_files))
        if mode is not None:
            actual_mode = stat.S_IMODE(os.stat(path).st_mode)
            self.failIf(actual_mode != mode,
                        "directory '%s' does not have the expected mode: "
                        "expected=%s, actual=%s"
                        % (path, oct(mode), oct(actual_mode)))
        if mtime is not None:
            actual_mtime = os.stat(path).st_mtime
            self.failIf(actual_mtime != mtime,
                        "directory '%s' does not have the expected mtime: "
                        "expected=%s, actual=%s"
                        % (path, mtime, actual_mtime))
        if atime is not None:
            actual_atime = os.stat(path).st_atime
            self.failIf(actual_atime != atime,
                        "directory '%s' does not have the expected atime: "
                        "expected=%s, actual=%s"
                        % (path, atime, actual_atime))

    def test_bad_args(self):
        from mklib.sh import cp
        self.assertRaises(TypeError, cp)
        self.assertRaises(TypeError, cp, "src") # no 'dst' or 'dstdir'
        self.assertRaises(TypeError, cp, "src", "dst", dstdir="dst") # 'dst' and 'dstdir'
        self.assertRaises(TypeError, cp, "src", "dst", "dstdir") # 'dst' and 'dstdir'
        self.assertRaises(TypeError, cp, None, "dst") # 'src' is None
        self.assertRaises(TypeError, cp, [], "dst") # 'src' is empty

    def test_no_src(self):
        from mklib.sh import cp
        self.assertRaises(OSError, cp, "foo.txt", "bar.txt")
        self.assertRaises(OSError, cp, "nomatch.*", "bar.txt")
        _write("foo.txt", "blah blah")
        self.assertRaises(OSError, cp, "fo*.txt", "bar.txt", noglob=True)

    def test_no_dstdir(self):
        from mklib.sh import cp
        _write("filea", "filea's content")
        # Using 'dst' does not guarantee a dir.
        cp("filea", "dirb")
        self.assertFile("dirb", content="filea's content")
        # Using 'dstdir' **does** guarantee a dir.
        self.assertRaises(OSError, cp, "filea", dstdir="dira")

    def test_samefile(self):
        from mklib.sh import cp
        _write("filea", "filea's content")
        self.assertRaises(OSError, cp, "filea", "filea")
        self.assertRaises(OSError, cp, "filea", join(os.curdir, "filea"))
        self.assertRaises(OSError, cp, "filea", os.path.abspath("filea"))
        self.assertRaises(OSError, cp, "filea", os.curdir)
        self.assertRaises(OSError, cp, "filea", dstdir=os.curdir)
        os.mkdir("dira")
        fileb = join("dira", "fileb")
        _write(fileb, "fileb's content")
        self.assertRaises(OSError, cp, fileb, fileb)
        self.assertRaises(OSError, cp, fileb, "dira")
        self.assertRaises(OSError, cp, fileb, dstdir="dira")

    def test_basic(self):
        from mklib.sh import cp
        _write("filea", "blah blah")
        cp("filea", "fileb")
        self.assertFile("fileb", content="blah blah")

        os.mkdir("dira")
        dst = join("dira", "fileb")
        cp("filea", dst)
        self.assertFile(dst, content="blah blah")

        os.mkdir("dirb")
        cp("filea", "dirb")
        self.assertFile(join("dirb", "filea"), content="blah blah")

        _write("fileb", "fileb's content")
        _write("filec", "filec's content")
        self.assertRaises(OSError, cp, ["fileb", "filec"], "dirc")
        self.assertRaises(OSError, cp, ["fileb", "filec"], "filea")
        os.mkdir("dirc")
        cp(["fileb", "filec"], "dirc")
        self.assertFile(join("dirc", "fileb"), content="fileb's content")
        self.assertFile(join("dirc", "filec"), content="filec's content")

        os.mkdir("dird")
        cp(["fileb", "filec"], dstdir="dird")
        self.assertFile(join("dird", "fileb"), content="fileb's content")
        self.assertFile(join("dird", "filec"), content="filec's content")

    def test_dir(self):
        from mklib.sh import cp
        umask = _getumask()

        os.mkdir("dira")
        mode_dira = stat.S_IMODE(os.stat("dira").st_mode)
        filea = join("dira", "filea")
        _write(filea, "filea's content")
        mode_filea = stat.S_IMODE(os.stat(filea).st_mode)

        self.assertRaises(OSError, cp, "dira", "dirb") # need recursive=True to copy dir
        cp("dira", "dirb", recursive=True)
        self.assertDir("dirb", files=["filea"], mode=mode_dira&~umask)
        self.assertFile(join("dirb", "filea"), content="filea's content",
                        mode=mode_filea&~umask)

    def test_binary_mode(self):
        # Test copying text files with EOLs to make sure copying is
        # being done binary.
        from mklib.sh import cp
        multiline_content = "line1\nline2\r\nline3\rline4"
        _write("textfile", multiline_content)
        cp("textfile", "textfile_copy")
        self.assertFile("textfile_copy", content=multiline_content)

    if sys.platform != "win32":
        def test_copy_to_dir_without_execute_permission(self):
            # Test `cp dira dirb` when 'dirb' exists but the user does NOT
            # have execute permissions (on Unix, obviously). GNU cp:
            #   $ l -d dirb
            #   drw-r-xr-x    2 trentm         48 2004-10-10 14:41 dirb/
            #   $ cp -rv dira dirb
            #   cp: cannot stat `dirb/dira': Permission denied
            # I think any raise OSError is fine. We shouldn't need to
            # special case the failure handling when trying to
            # stat('dirb/dira') -- i.e. do something different for "doesn't
            # exist" and "permission denied".
            from mklib.sh import cp
            os.mkdir("dira")
            os.mkdir("dirb")
            os.chmod("dirb", 0666)
            try:
                self.assertRaises(OSError, cp, "dira", "dirb", recursive=True)
            finally:
                # Have to do this because HP-UX 11's `chmod -R` can't
                # handle it.
                os.chmod("dirb", 0777)

        def test_permissions(self):
            # Test nitpicky permissions on a simple copy:
            #   Rules: if fileb exists, keep permissions, if not then set
            #   permissions to filea&~umask.
            from mklib.sh import cp
            a = "filea"
            b = "fileb"

            old_umask = os.umask(022)
            try:
                # - before: filea (-rw-r--r--), no fileb, umask=0022
                #   action: cp filea fileb
                #   after:  filea (-rw-r--r--), fileb (-rw-r--r--)
                _write(a, "filea's content")
                os.chmod(a, 0644)
                cp(a, b)
                self.assertFile(b, mode=0644)

                # - before: filea (-rwxrwxrwx), no fileb, umask=0022
                #   action: cp filea fileb
                #   after:  filea (-rwxrwxrwx), fileb (-rwxr-xr-x)
                os.remove(b)
                os.chmod(a, 0777)
                cp(a, b)
                self.assertFile(b, mode=0755)

                # - before: filea (-rw-r--r--), fileb (-rwxrwxrwx), umask=0022
                #   action: cp filea fileb
                #   after:  filea (-rw-r--r--), fileb (-rwxrwxrwx)
                os.chmod(a, 0644)
                os.chmod(b, 0777)
                cp(a, b)
                self.assertFile(b, mode=0777)

                # - before: filea (-rwxrwxrwx), fileb (--w-------), umask=0022
                #   action: cp filea fileb
                #   after:  filea (-rwxrwxrwx), fileb (--w-------)
                os.chmod(a, 0777)
                os.chmod(b, 0200)
                cp(a, b)
                self.assertFile(b, mode=0200)
            finally:
                os.umask(old_umask)

    def test_preserve(self):
        from mklib.sh import cp
        a = "filea"; b = "fileb"
        _write(a, "this is filea")
        a_stat = os.stat(a)
        os.chmod(a, 0777)
        cp(a, b, preserve=True)
        self.assertFile(b, mtime=a_stat.st_mtime, atime=a_stat.st_atime)
        if sys.platform != "win32":
            self.assertFile(b, mode=0777)

        os.chmod(a, 0700)
        cp(a, b, preserve=True)
        self.assertFile(b, mtime=a_stat.st_mtime, atime=a_stat.st_atime)
        if sys.platform != "win32":
            self.assertFile(b, mode=0700)

    def test_no_preserve(self):
        from mklib.sh import cp
        a = "filea"; b = "fileb"
        _write(a, "this is filea")
        a_stat = os.stat(a)
        time.sleep(1)
        cp(a, b)   # preserve=False by default
        a_mtime = os.stat(a).st_mtime
        b_mtime = os.stat(b).st_mtime
        self.assertNotEqual(a_mtime, b_mtime,
            "mtime's for src (%s, %s) and dst (%s, %s) were preserved "
            "by default, they should not be" % (a, a_mtime, b, b_mtime))

    if sys.platform != "win32":
        # mtime's and atime's are totally different for dirs on Windows.
        # You can't set them.
        def test_preserve_dir(self):
            from mklib.sh import cp
            a = "dira"; b = "dirb"
            os.mkdir(a)
            a_stat = os.stat(a)
            os.chmod(a, 0777)
            cp(a, b, recursive=True, preserve=True)
            self.assertDir(b, mode=0777, mtime=a_stat.st_mtime,
                           atime=a_stat.st_atime)

    if sys.platform == "win32":
        # To test a read access failure on Windows would have to setup
        # a file lock or something. You cannot turn off "readability" on
        # Windows.
        pass
    else:
        def test_target_not_modified_on_read_fail(self):
            # When don't have read access to src, the target is not
            # modified.
            from mklib.sh import cp
            _write("filea", "filea's content")
            _write("fileb", "fileb's content")
            os.chmod("filea", 0000)
            self.assertRaisesEx(OSError, cp, "filea", "fileb")
            self.assertFile("fileb", content="fileb's content")

    def test_noglob(self):
        from mklib.sh import cp
        # Can't have '*' or '?' in filenames on Windows, so use '[...]'
        # globbing to test.
        _write("foop", "hello from foop")
        _write("foot", "hello from foot")
        _write("foo[tp]", "hello from foo[tp]")
        os.mkdir("dir_with_glob")
        os.mkdir("dir_without_glob")
        cp("foo[tp]", dstdir="dir_with_glob")
        cp("foo[tp]", dstdir="dir_without_glob", noglob=True)
        self.assertDir("dir_with_glob", files=["foop", "foot"])
        self.assertDir("dir_without_glob", files=["foo[tp]"])

        os.mkdir("dir_with_no_files")
        self.assertRaises(OSError, cp, "fo*", dstdir="dir_with_no_files",
                          noglob=True)

    def test_force(self):
        from mklib.sh import cp
        _write("sourcefile", "this is sourcefile")
        sourcefile_mode = stat.S_IMODE(os.stat("sourcefile").st_mode)
        umask = _getumask()

        _write("noaccess", "this is nowrite")
        os.chmod("noaccess", 0000)
        self.assertRaises(OSError, cp, "sourcefile", "noaccess")
        cp("sourcefile", "noaccess", force=True)
        self.assertFile("noaccess", content="this is sourcefile",
                        mode=sourcefile_mode&~umask)

    if sys.platform != "win32":
        # Read-only attrib on directories on Windows has no observable
        # effect that I can tell.
        def test_force_dir(self):
            from mklib.sh import cp
            os.mkdir("sourcedir")
            os.mkdir("noaccess")
            os.chmod("noaccess", 0000)
            try:
                self.assertRaises(OSError, cp, "sourcedir", "noaccess",
                                  recursive=True)
                # As with GNU 'cp', the force option is not sufficient
                # to remove a dir without execute access.
                self.assertRaises(OSError, cp, "sourcedir", "noaccess",
                                  recursive=True, force=True)
            finally:
                # Have to do this because HP-UX 11's `chmod -R` can't
                # handle it.
                os.chmod("noaccess", 0777)

    def test_trailing_slashes(self):
        from mklib.sh import cp

        # Linux:
        #   $ ls -F
        #   dira/  filea
        #   $ cp -v filea/ dira
        #   cp: cannot stat `filea/': Not a directory
        #
        # It seems to work fine on other Unices (Solaris 6, Solaris 8,
        # AIX 5.1, HP-UX 11).
        #
        # This case is a little confused on Windows, but it does fail.
        # Given the _file_ "foo":
        #   C:\> copy foo\ bar
        #   The system cannot find the file specified.
        # **but**:
        #   >>> glob.glob("foo\\")
        #   ['foo\\']
        #   >>> os.stat("foo\\")
        #   (33206, 0L, 3, 1, 0, 0, 6L, 1097450002, 1097450002, 1097450002)
        _write("filea", "this is filea")
        if sys.platform in ("win32", "linux2"):
            self.assertRaisesEx(OSError, cp, "filea"+os.sep, "dira")

        # At one point, cp()'s use of os.path.basename() screws up when
        # the given source and dest have trailing slashes. We cannot
        # just remove the trailing slashes all the time -- I don't think
        # -- because of some obscure POSIX thing (follow the note for
        # --remove-trailing-slashes in `info cp`).
        os.mkdir("dira")
        os.mkdir("dirb")
        cp("dira"+os.sep, "dirb"+os.sep, recursive=True)
        self.assertDir(join("dirb", "dira"))

    def assertRaisesEx(self, exception, callable, *args, **kwargs):
        if "exc_args" in kwargs:
            exc_args = kwargs["exc_args"]
            del kwargs["exc_args"]
        else:
            exc_args = None
        if "exc_pattern" in kwargs:
            exc_pattern = kwargs["exc_pattern"]
            del kwargs["exc_pattern"]
        else:
            exc_pattern = None

        argv = [repr(a) for a in args]\
               + ["%s=%r" % (k,v)  for k,v in kwargs.items()]
        callsig = "%s(%s)" % (callable.__name__, ", ".join(argv))

        try:
            callable(*args, **kwargs)
        except exception, exc:
            if exc_args is not None:
                self.failIf(exc.args != exc_args,
                            "%s raised %s with unexpected args: "\
                            "expected=%r, actual=%r"\
                            % (callsig, exc.__class__, exc_args, exc.args))
            if exc_pattern is not None:
                self.failUnless(exc_pattern.search(str(exc)),
                                "%s raised %s, but the exception "\
                                "does not match '%s': %r"\
                                % (callsig, exc.__class__, exc_pattern.pattern,
                                   str(exc)))
        except:
            exc_info = sys.exc_info()
            print exc_info
            self.fail("%s raised an unexpected exception type: "\
                      "expected=%s, actual=%s"\
                      % (callsig, exception, exc_info[0]))
        else:
            self.fail("%s did not raise %s" % (callsig, exception))

    def test_overwrite_dir_with_file(self):
        # $ ls -ARl dir1 file1
        # -rw-r--r--    1 trentm   trentm          3 2004-10-10 16:22 file1
        #
        # dir1:
        # total 0
        # drwxr-xr-x    2 trentm   trentm         48 2004-10-10 16:22 file1
        #
        # dir1/file1:
        # total 0
        # $ cp file1 dir1
        # cp: cannot overwrite directory `dir1/file1' with non-directory
        # $ cp -f file1 dir1
        # cp: cannot overwrite directory `dir1/file1' with non-directory
        from mklib.sh import cp
        os.mkdir("dir1")
        _write("file1", "this is file1")
        os.mkdir(join("dir1", "file1"))
        self.assertRaisesEx(OSError, cp, "file1", "dir1",
                            exc_pattern=re.compile("cannot overwrite directory"))

    def test_common_sub_sub_dirs(self):
        # The automatic promotion of the target to:
        #   join(target, os.path.basename(source))
        # when the target is a directory must not be applied recursively.
        # Consider this layout:
        #   basedir1
        #   `- commondir
        #      `- commonsubdir
        #         `- file1.txt
        #   basedir2
        #   `- commondir
        #      `- commonsubdir
        #         `- file1.txt
        # Now copy the contents of those two basedirs to a new target:
        #   mkdir targetdir
        #   cp -r basedir1/* targetdir
        #   cp -r basedir2/* targetdir
        # This *should* result in:
        #   targetdir
        #   `- commondir
        #      `- commonsubdir
        #         |- file1.txt
        #         `- file2.txt
        # but will result in this if the promotion is recursive:
        #   targetdir
        #   `- commondir
        #      `- commonsubdir
        #         |- file1.txt
        #         `- commonsubdir
        #            `- file2.txt
        from mklib.sh import cp
        os.makedirs(join("basedir1", "commondir", "commonsubdir"))
        _write(join("basedir1", "commondir", "commonsubdir", "file1.txt"),
               content="this is file1")
        os.makedirs(join("basedir2", "commondir", "commonsubdir"))
        _write(join("basedir2", "commondir", "commonsubdir", "file2.txt"),
               content="this is file2")
        os.mkdir("targetdir")
        cp(join("basedir1", "*"), "targetdir", recursive=True)
        cp(join("basedir2", "*"), "targetdir", recursive=True)
        self.assertDir("targetdir", files=["commondir"])
        self.assertDir(join("targetdir", "commondir"),
                       files=["commonsubdir"])
        self.assertDir(join("targetdir", "commondir", "commonsubdir"),
                       files=["file1.txt", "file2.txt"])
        self.assertFile(
            join("targetdir", "commondir", "commonsubdir", "file1.txt"),
            content="this is file1")
        self.assertFile(
            join("targetdir", "commondir", "commonsubdir", "file2.txt"),
            content="this is file2")


if __name__ == "__main__":
    argv = sys.argv[:]
    argv.insert(1, "-v") # make output verbose by default
    unittest.main(argv=argv)

