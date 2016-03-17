#!/usr/bin/env python

# See the accompanying LICENSE file.

import os
import sys
import shlex
import glob
import re
import time
import zipfile, tarfile
import socket

from distutils.core import setup, Extension, Command
from distutils.command import build_ext, build, sdist

##
## Do your customizations here or by creating a setup.cfg as documented at
## http://www.python.org/doc/2.5.2/dist/setup-config.html
##

include_dirs=['src']
library_dirs=[]
define_macros=[]
libraries=[]

# This includes the functionality marked as experimental in SQLite 3.
# Comment out the line to exclude them
define_macros.append( ('EXPERIMENTAL', '1') )

##
## End of customizations
##

# python 2 and 3 print equivalent
def write(*args):
    # py2 won't allow optional keyword arg on end, so work around it
    dest=sys.stdout
    if args[-1]==sys.stderr:
        dest=args[-1]
        args=args[:-1]
    dest.write(" ".join(args)+"\n")
    dest.flush()

py3=sys.version_info>=(3,0)

# ensure files are closed
def read_whole_file(name, mode):
    if sys.version_info<(2,4):
        if "r" in mode and "U" in mode:
            # python 2.3 returns file not found if "U" present!
            mode="".join([m for m in mode if m!="U"])
    f=open(name, mode)
    try:
        return f.read()
    finally:
        f.close()

def write_whole_file(name, mode, data):
    f=open(name, mode)
    try:
        f.write(data)
    finally:
        f.close()

# They keep messing with where files are in URI
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

# Run test suite
class run_tests(Command):

    description="Run test suite"


    # I did originally try using 'verbose' as the option but it turns
    # out that is builtin and defaults to 1 (--quiet is also builtin
    # and forces verbose to 0)
    user_options=[
        ("show-tests", "s", "Show each test being run"),
        ]

    # see if you can find boolean_options documented anywhere
    boolean_options=['show-tests']

    def initialize_options(self):
        self.show_tests=0

    def finalize_options(self):
        pass

    def run(self):
        import unittest
        import tests
        tests.setup()
        suite=unittest.TestLoader().loadTestsFromModule(tests)
        # verbosity of zero doesn't print anything, one prints a dot
        # per test and two prints each test name
        result=unittest.TextTestRunner(verbosity=self.show_tests+1).run(suite)
        if not result.wasSuccessful():
            sys.exit(1)

# A hack we dont't document
class build_test_extension(Command):
    description="Compiles APSW test loadable extension"

    user_options=[]

    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        # On 64 bit windows we have to use MSVC
        if sys.platform=='win32': # yes even on 64 bit
            try:
                import platform
                if platform.architecture()[0]=='64bit':
                    res=os.system("cl /Gd src/testextension.c /I sqlite3 /I . /DDLL /LD /link /export:sqlite3_extension_init /export:alternate_sqlite3_extension_init /out:testextension.sqlext")
                    if res!=0:
                        raise RuntimeError("Building test extension failed")
                    return
            except ImportError:
                pass
        shared="shared"
        if sys.platform.startswith("darwin"):
            shared="bundle"
        res=os.system("gcc -fPIC -%s -o testextension.sqlext -Isqlite3 -I. src/testextension.c" % (shared,))
        if res!=0:
            raise RuntimeError("Building test extension failed")

# Another hack.  Visual Studio 2008 & 2010 ship with 64
# compilers, headers and the Windows SDK but claims it doesn't and
# distutils can't find it.  The separate Windows SDK can't find this
# and gets very confused not to mention being one of the buggiest cmd
# scripts I have ever seen.  This hack just sets some environment
# variables directly since all the "proper" ways are very broken.
class win64hackvars(Command):
    description="Set env vars for Visual Studio 2008/2010 Express 64 bit"

    user_options=[]
    def initialize_options(self): pass
    def finalize_options(self): pass
    def run(self):
        vcver=9
        if sys.version_info>=(3,3):
            vcver=10
        sdkdir=r"C:\Program Files\Microsoft SDKs\Windows\v6.0A"
        vsdir=r"C:\Program Files (x86)\Microsoft Visual Studio %d.0\VC" % vcver
        assert os.path.isdir(sdkdir), "Expected sdk dir "+sdkdir
        assert os.path.isdir(vsdir), "Expected visual studio dir "+vsdir
        os.environ["PATH"]=r"%s\bin\amd64;%s\bin" % (vsdir, sdkdir)
        os.environ["INCLUDE"]=r"%s\include;%s\include" % (vsdir, sdkdir)
        os.environ["LIB"]=r"%s\lib\amd64;%s\lib\x64" % (vsdir, sdkdir)
        os.environ["DISTUTILS_USE_SDK"]="1"
        os.environ["MSSdk"]=sdkdir

# deal with various python version compatibility issues with how
# to treat returned web data as lines of text
def fixupcode(code):
    if sys.version_info<(2,5):
        if type(code)!=str:
            code=code.read()

    if sys.version_info>=(3,0):
        if type(code)!=bytes:
            code=code.read()
        if type(code)==bytes:
            code=code.decode("iso8859-1")

    if type(code)==str:
        return [l+"\n" for l in code.split("\n")]

    return code

fetch_parts=[]

class fetch(Command):
    description="Automatically downloads SQLite and components"
    user_options=[
        ("version=", None, "Which version of SQLite/components to get (default current)"),
        ("missing-checksum-ok", None, "Continue on a missing checksum (default abort)"),
        ("sqlite", None, "Download SQLite amalgamation"),
        ("all", None, "Download all downloadable components"),
        ]
    fetch_options=['sqlite']
    boolean_options=fetch_options+['all', 'missing-checksum-ok']

    def initialize_options(self):
        self.version=None
        self.sqlite=False
        self.all=False
        self.missing_checksum_ok=False

    def finalize_options(self):
        # If all is selected then turn on all components
        global fetch_parts
        if self.all:
            for i in self.fetch_options:
                    setattr(self, i, True)
        for i in self.fetch_options:
            fetch_parts.append(i)

    def run(self):
        # work out the version
        if self.version is None:
            write("  Getting download page to work out current SQLite version")
            page=self.download("https://sqlite.org/download.html", text=True, checksum=False)
            match=re.search(r'sqlite-amalgamation-3([0-9][0-9])([0-9][0-9])([0-9][0-9])\.zip', page)
            if match:
                self.version="3.%d.%d.%d" % tuple([int(match.group(n)) for n in range(1,4)])
                if self.version.endswith(".0"):
                    self.version=self.version[:-len(".0")]
            else:
                write("Unable to determine current SQLite version.  Use --version=VERSION", sys.stderr)
                write("to set version - eg setup.py fetch --version=3.6.18", sys.stderr)
                sys.exit(17)
            write("    Version is "+self.version)
        # now get each selected component
        downloaded=0

        if not self.version.startswith("fossil"):
            v=[int(x) for x in self.version.split(".")]
            if len(v)<4:
                v.append(0)
            self.webversion="%d%02d%02d%02d" % tuple(v)

        ## The amalgamation
        if self.sqlite:
            if self.version.startswith("fossil"):
                write("  Getting code from fossil")
            else:
                write("  Getting the SQLite amalgamation")

            if self.version.startswith("fossil"):
                if self.version=="fossil":
                    uuid="trunk"
                else:
                    showmsg=False
                    if not self.version.startswith("fossil-"):
                        showmsg=True
                    else:
                        uuid=self.version.split("-", 1)[1]
                        if not uuid:
                            showmsg=True
                    if showmsg:
                        write("Use fossil-HASH to identify a partifular commit", sys.stderr)
                        write("eg  fossil-3a82c8e6", sys.stderr)
                        sys.exit(18)

                AURL="https://sqlite.org/src/zip/sqlite3.zip?uuid="+uuid
                checksum=False
            else:
                if sys.platform=="win32":
                    AURL="https://sqlite.org/sqlite-amalgamation-%s.zip" % (self.webversion,)
                else:
                    AURL="https://sqlite.org/sqlite-autoconf-%s.tar.gz" % (self.webversion,)
                checksum=True

            AURL=fixup_download_url(AURL)

            data=self.download(AURL, checksum=checksum)

            if AURL.endswith(".zip"):
                zip=zipfile.ZipFile(data, "r")
                for name in "sqlite3.c", "sqlite3.h", "sqlite3ext.h":
                    write("Extracting", name)
                    f=[n for n in zip.namelist() if n.endswith(name)]
                    if len(f)!=1:
                        raise Exception("Can't find %s in zip.  Candidates are %s" % (name, f))
                    # Work around SQLite 3.7.13 bug where a symbol was
                    # declared SQLITE_API and extern
                    data=zip.read(f[0])
                    if name=="sqlite3.c":
                        data=data.decode("utf8")
                        data=data.replace("SQLITE_API extern", "SQLITE_API")
                        data=data.encode("utf8")
                    open(name, "wb").write(data)
                zip.close()
            else:
                # we need to run configure to get various -DHAVE_foo flags on non-windows platforms
                # delete existing sqlite3 directory if it exists, but save sqlite3config.h if it exists
                sqlite3config_h=None
                if os.path.exists("sqlite3/sqlite3config.h"):
                    sqlite3config_h=read_whole_file("sqlite3/sqlite3config.h", "rb")
                if os.path.exists('sqlite3'):
                    for dirpath, dirnames, filenames in os.walk('sqlite3', topdown=False):
                        for file in filenames:
                            os.remove(os.path.join(dirpath, file))
                        for dir in dirnames:
                            os.rmdir(os.path.join(dirpath, dir))
                    os.rmdir('sqlite3')
                if self.version.startswith("fossil"):
                    zip=zipfile.ZipFile(data, "r")
                    for name in zip.namelist():
                        # extract
                        if name.endswith("/"):
                            os.mkdir(name)
                        else:
                            open(name, "wb").write(zip.read(name))
                    zip.close()
                else:
                    # if you get an exception here it is likely that you don't have the python zlib module
                    import zlib
                    tar=tarfile.open("nonexistentname to keep old python happy", 'r', data)
                    configmember=None
                    for member in tar.getmembers():
                        tar.extract(member)
                        # find first file named configure
                        if not configmember and member.name.endswith("/configure"):
                            configmember=member
                    tar.close()
                    # the directory name has changed a bit with each release so try to work out what it is
                    if not configmember:
                        write("Unable to determine directory it extracted to.", dest=sys.stderr)
                        sys.exit(19)
                    dirname=configmember.name.split('/')[0]
                    os.rename(dirname, 'sqlite3')
                os.chdir('sqlite3')
                if self.version.startswith("fossil"):
                    write("    Building amalgamation from fossil")
                    res=os.system("make TOP=. -f Makefile.linux-gcc sqlite3.c && cp src/sqlite3ext.h .")
                    defs=[]
                    if sqlite3config_h:
                        open("sqlite3config.h", "wb").write(sqlite3config_h)
                else:
                    write("    Running configure to work out SQLite compilation flags")
                    res=os.system("./configure >/dev/null")
                    defline=None
                    for line in read_whole_file("Makefile", "rtU").split("\n"):
                        if line.startswith("DEFS = "):
                            defline=line
                            break
                    if not defline:
                        write("Unable to determine compile flags.  Create sqlite3/sqlite3config.h to manually set.", sys.stderr)
                        sys.exit(18)
                    defs=[]
                    for part in shlex.split(defline):
                        if part.startswith("-DHAVE"):
                            part=part[2:]
                            if '=' in part:
                                part=part.split('=', 1)
                            else:
                                part=(part, )
                            defs.append(part)
                if res!=0:
                    raise ValueError("Command execution failed")
                if defs:
                    op=open("sqlite3config.h", "wt")
                    op.write("""
/* This file was generated by parsing how configure altered the Makefile
   which isn't used when building python extensions.  It is specific to the
   machine and developer components on which it was run. */
   \n""")

                    for define in defs:
                        op.write('#define %s %s\n' % tuple(define))
                    op.close()
                os.chdir("..")
            downloaded+=1

        if not downloaded:
            write("You didn't specify any components to fetch.  Use")
            write("   setup.py fetch --help")
            write("for a list and details")
            raise ValueError("No components downloaded")

    # A function for verifying downloads
    def verifyurl(self, url, data):
        d=["%s" % (len(data),)]
        try:
            import hashlib
            d.append(hashlib.sha1(data).hexdigest())
            d.append(hashlib.md5(data).hexdigest())
        except ImportError:
            import sha
            d.append(sha.new(data).hexdigest())
            import md5
            d.append(md5.new(data).hexdigest())

        write("    Length:", d[0], " SHA1:", d[1], " MD5:", d[2])
        sums=os.path.join(os.path.dirname(__file__), "checksums")
        for line in read_whole_file(sums, "rt").split("\n"):
            line=line.strip()
            if len(line)==0 or line[0]=="#":
                continue
            l=[l.strip() for l in line.split()]
            if len(l)!=4:
                write("Invalid line in checksums file:", line, sys.stderr)
                raise ValueError("Bad checksums file")
            if l[0]==url:
                if l[1:]==d:
                    write("    Checksums verified")
                    return
                if l[1]!=d[0]:
                    write("Length does not match.  Expected", l[1], "download was", d[0])
                if l[2]!=d[1]:
                    write("SHA does not match.  Expected", l[2], "download was", d[1])
                if l[3]!=d[2]:
                    write("MD5 does not match.  Expected", l[3], "download was", d[2])
                write("The download does not match the checksums distributed with APSW.\n"
                      "The download should not have changed since the checksums were\n"
                      "generated.  The cause could be anything from network corruption\n"
                      "to a malicious attack.")
                raise ValueError("Checksums do not match")
        # no matching line
        write("    (Not verified.  No match in checksums file)")
        if not self.missing_checksum_ok:
            raise ValueError("No checksum available.  Use --missing-checksum-ok option to continue")

    # download a url
    def download(self, url, text=False, checksum=True):
        if py3:
            import urllib.request
            urlopen=urllib.request.urlopen
            import io
            bytesio=io.BytesIO
        else:
            import urllib2
            urlopen=urllib2.urlopen
            import cStringIO
            bytesio=cStringIO.StringIO

        write("    Fetching", url)
        count=0
        while True:
            try:
                if count:
                    write("        Try #",str(count+1))
                try:
                    page=urlopen(url).read()
                except:
                    # Degrade to http if https is not supported
                    e=sys.exc_info()[1]
                    if "eof occurred in violation of protocol" in str(e).lower() or e.reason=="unknown url type: https":
                        write("        [Python has https issues - using http instead]")
                        page=urlopen(url.replace("https://", "http://")).read()
                    else:
                        raise
                break
            except:
                write("       Error ", str(sys.exc_info()[1]))
                time.sleep(1.3)
                count+=1
                if count>=5:
                    raise

        if text:
            if py3:
                page=page.decode("iso8859_1")

        if checksum:
            self.verifyurl(url, page)

        if not text:
            page=bytesio(page)

        return page

# We allow enable/omit to be specified to build and then pass them to build_ext
build_enable=None
build_omit=None
build_enable_all_extensions=False

bparent=build.build
class apsw_build(bparent):
    user_options=bparent.user_options+\
                  [ ("enable=", None, "Enable SQLite options (comma seperated list)"),
                    ("omit=", None, "Omit SQLite functionality (comma seperated list)"),
                    ("enable-all-extensions", None, "Enable all SQLite extensions"),
                    ]
    boolean_options=bparent.boolean_options+["enable-all-extensions"]

    def initialize_options(self):
        v=bparent.initialize_options(self)
        self.enable=None
        self.omit=None
        self.enable_all_extensions=build_enable_all_extensions
        return v

    def finalize_options(self):
        global build_enable, build_omit, build_enable_all_extensions
        build_enable=self.enable
        build_omit=self.omit
        build_enable_all_extensions=self.enable_all_extensions
        return bparent.finalize_options(self)

def findamalgamation():
    amalgamation=(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite3.c"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite3", "sqlite3.c")
        )
    for path in amalgamation:
        if os.path.exists(path):
            return path
    return None

def find_in_path(name):
    for loc in os.getenv("PATH").split(os.pathsep):
        f=os.path.abspath(os.path.join(loc, name))
        if os.path.exists(f) or os.path.exists(f.lower()) or os.path.exists(f.lower()+".exe"):
            return f
    return None

beparent=build_ext.build_ext
class apsw_build_ext(beparent):

    user_options=beparent.user_options+\
                  [ ("enable=", None, "Enable SQLite options (comma seperated list)"),
                    ("omit=", None, "Omit SQLite functionality (comma seperated list)"),
                    ("enable-all-extensions", None, "Enable all SQLite extensions"),
                    ]
    boolean_options=beparent.boolean_options+["enable-all-extensions"]


    def initialize_options(self):
        v=beparent.initialize_options(self)
        self.enable=build_enable
        self.omit=build_omit
        self.enable_all_extensions=build_enable_all_extensions
        return v

    def finalize_options(self):
        v=beparent.finalize_options(self)

        if self.enable_all_extensions:
            exts=["fts4", "fts3", "fts3_parenthesis", "rtree", "stat4"]
            if find_in_path("icu-config"):
                exts.append("icu")
            if not self.enable:
                self.enable=",".join(exts)
            else:
                self.enable=self.enable+","+",".join(exts)

        ext=self.extensions[0]

        if not ext.define_macros: ext.define_macros=[]
        if not ext.depends: ext.depends=[]
        if not ext.include_dirs: ext.include_dirs=[]
        if not ext.library_dirs: ext.library_dirs=[]
        if not ext.libraries: ext.libraries=[]

        # Fixup debug setting
        if self.debug:
            # distutils forces NDEBUG even with --debug so overcome that
            ext.define_macros.append( ('APSW_NO_NDEBUG', '1') )    # double negatives are bad
            ext.define_macros.append( ('APSW_TESTFIXTURES', '1') ) # extra test harness code
            ext.define_macros.append( ('SQLITE_DEBUG', '1') )      # also does NDEBUG mangling
        else:
            ext.define_macros.append( ('NDEBUG', '1') )

        # fork checker?
        if hasattr(os, "fork"):
            ext.define_macros.append( ('APSW_FORK_CHECKER', '1') )

        # SQLite 3
        # Look for amalgamation in our directory or in sqlite3 subdirectory

        path=findamalgamation()
        if path:
            if sys.platform=="win32":
                # double quotes get consumed by windows arg processing
                ext.define_macros.append( ('APSW_USE_SQLITE_AMALGAMATION', '\\"'+path+'\\"') )
            else:
                ext.define_macros.append( ('APSW_USE_SQLITE_AMALGAMATION', '"'+path+'"') )
            ext.depends.append(path)
            # we also add the directory to include path since icu tries to use it
            ext.include_dirs.append(os.path.dirname(path))
            write("SQLite: Using amalgamation", path)
            load_extension=True
        else:
            load_extension=False
            d=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite3")
            if os.path.isdir(d):
                write("SQLite: Using include/libraries in sqlite3 subdirectory")
                ext.include_dirs.append(d)
                ext.library_dirs.append(d)
            else:
                write("SQLite: Using system sqlite include/libraries")
            ext.libraries.append('sqlite3')

        s3config=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite3", "sqlite3config.h")
        if os.path.exists(s3config):
            if sys.platform=="win32":
               ext.define_macros.append( ('APSW_USE_SQLITE_CONFIG', '\\"'+s3config+'\\"') )
            else:
                ext.define_macros.append( ('APSW_USE_SQLITE_CONFIG', '"'+s3config+'"') )

        # enables
        addicuinclib=False
        if self.enable:
            for e in self.enable.split(","):
                e=e.strip()
                if e.lower()=="load_extension":
                    load_extension=True
                    continue
                ext.define_macros.append( ("SQLITE_ENABLE_"+e.upper(), 1) )
                if e.upper()=="ICU":
                    addicuinclib=True
                os.putenv("APSW_TEST_"+e.upper(), "1")
                # See issue #55 where I had left off the 3 in fts3.  This code
                # tries to catch misspelling the name of an extension.
                # However the SQLITE_ENABLE prefix is also used by other
                # options - see https://sqlite.org/compile.html but almost
                # all of those have _ in them, so our abbreviated and
                # hopefully future proof test
                if "_" not in e.lower() and \
                       "memsys" not in e.lower() and \
                       e.lower() not in ("fts4", "fts3", "rtree", "icu", "iotrace",
                                         "stat2", "stat3", "stat4", "dbstat_vtab"):
                    write("Unknown enable "+e, sys.stderr)
                    raise ValueError("Bad enable "+e)

        # omits
        if self.omit:
            for e in self.omit.split(","):
                e=e.strip()
                if e.lower()=="load_extension":
                    load_extension=False
                ext.define_macros.append( ("SQLITE_OMIT_"+e.upper(), 1) )

        if not load_extension:
            ext.define_macros.append( ("SQLITE_OMIT_LOAD_EXTENSION", 1) )

        # icu
        if addicuinclib:
            foundicu=False
            kwargs={}
            if sys.version_info>=(2, 6):
                # if posix is true then quotes get stripped such as from -Dfoo="bar"
                kwargs["posix"]=False
            for part in shlex.split(os.popen("icu-config --cppflags", "r").read(), **kwargs):
                if part.startswith("-I"):
                    ext.include_dirs.append(part[2:])
                    foundicu=True
                elif part.startswith("-D"):
                    part=part[2:]
                    if '=' in part:
                        part=tuple(part.split('=', 1))
                    else:
                        part=(part, '1')
                    ext.define_macros.append(part)
                    foundicu=True

            for part in shlex.split(os.popen("icu-config --ldflags", "r").read(), **kwargs):
                if part.startswith("-L"):
                    ext.library_dirs.append(part[2:])
                    foundicu=True
                elif part.startswith("-l"):
                    ext.libraries.append(part[2:])
                    foundicu=True

            if foundicu:
                write("ICU: Added includes, flags and libraries from icu-config")
            else:
                write("ICU: Unable to determine includes/libraries for ICU using icu-config")
                write("ICU: You will need to manually edit setup.py or setup.cfg to set them")

        # shell
        if not os.path.exists("src/shell.c") or \
               os.path.getmtime("src/shell.c")<os.path.getmtime("tools/shell.py") or \
               os.path.getmtime(__file__)>os.path.getmtime("src/shell.c"):
            create_c_file("tools/shell.py", "src/shell.c")

        # done ...
        return v

    def run(self):
        v=beparent.run(self)
        return v

sparent=sdist.sdist
class apsw_sdist(sparent):

    user_options=sparent.user_options+[
        ("add-doc", None, "Includes built documentation from doc/build/html into source"),
        ]

    boolean_options=sparent.boolean_options+["add-doc"]

    def initialize_options(self):
        sparent.initialize_options(self)
        self.add_doc=False
        # Were we made from a source archive?  If so include the help again
        if os.path.isfile("doc/index.html") and os.path.isfile("doc/_sources/pysqlite.txt"):
            self.add_doc=True
        self.use_defaults=False # they are useless

        # Make sure the manifest is regenerated
        self.force_manifest=True

        # Now do some chicanery.  If a source distribution is requested and
        # fetch --sqlite was requested then make sure the sqlite amalgamation
        # ends up as part of the source distribution.
        if fetch_parts:
            # Use a temporary file for the manifest
            tmpmanifest="MANIFEST.in.tmp"
            self.template=tmpmanifest
            try:
                os.remove(tmpmanifest)
            except:
                pass
            min=open("MANIFEST.in", "rU")
            mout=open(tmpmanifest, "wt")
            for line in min:
                mout.write(line)
            min.close()
            # os.path.relpath emulation
            if "sqlite" in fetch_parts:
                amalgamationpath=findamalgamation()
                amalrelpath=amalgamationpath[len(os.path.dirname(os.path.abspath(__file__)))+1:]
                mout.write("include "+amalrelpath+"\n")
                # also include headers and extension headers
                mout.write("include "+amalrelpath.replace("sqlite3.c", "sqlite3.h")+"\n")
                mout.write("include "+amalrelpath.replace("sqlite3.c", "sqlite3ext.h")+"\n")
                if os.path.exists("sqlite3/sqlite3config.h"):
                    mout.write("include sqlite3/sqlite3config.h\n")

            mout.close()

    def run(self):
        v=sparent.run(self)
        if self.add_doc:
            if len(list(help_walker('')))==0:
                raise Exception("The help is not built")
            for archive in self.get_archive_files():
                add_doc(archive, self.distribution.get_fullname())
        return v

def help_walker(arcdir):
    # Provides a list of (archive name, disk name) for all the help files
    if os.path.isfile("doc/index.html") and os.path.isfile("doc/_sources/pysqlite.txt"):
        topdir="doc/"
    else:
        topdir="doc/build/html/"
    for dirpath, _, filenames in os.walk(topdir):
        prefix=dirpath[len(topdir):]
        for f in filenames:
            yield os.path.join(arcdir, "doc", prefix, f), os.path.join(dirpath, f)

def add_doc(archive, topdir):
    write("Add help files to",archive)
    if archive.endswith(".tar") or ".tar." in archive:
        if archive.endswith(".Z"):
            raise Exception("tarfile module doesn't support old school compress so we can't add doc "+archive)
        fmt=""
        if archive.endswith(".gz") or archive.endswith(".tgz"):
            fmt=":gz"
        elif archive.endswith(".bz2") or archive.endswith(".tbz2"):
            fmt=":bz2"
        oldarchive=tarfile.open(archive)
        newarchive=tarfile.open(archive+"-", mode="w"+fmt)
        for mem in oldarchive.getmembers():
            newarchive.addfile(mem, oldarchive.extractfile(mem))
        oldarchive.close()
        for arcname, fname in help_walker(topdir):
            newarchive.add(fname, arcname)
        newarchive.close()
        os.rename(archive+"-", archive)
    elif archive.endswith(".zip"):
        ofile=zipfile.ZipFile(archive, "a", zipfile.ZIP_DEFLATED)
        for arcname, fname in help_walker(topdir):
            ofile.write(fname, arcname)
        ofile.close()
    else:
        raise Exception("Don't know what to do with "+archive)

def create_c_file(src, dest):
    # Transforms Python src into C dest as a sequence of strings.
    # Because of the pathetic microsoft compiler we have to break it
    # up into small chunks
    out=["/* Automatically generated by setup.py from "+src+" */", ""]
    percents=1
    size=0
    for line in read_whole_file(src, "rt").split("\n"):
        if "if__name__=='__main__':" in line.replace(" ",""):
            break
        if line.strip().startswith('#'): # full line comment
            continue
        if line.strip()=="import apsw":
            continue
        size=size+len(line)
        comma=size>32000
        if comma:
            size=0
            percents+=1
        line=line.replace("\\", "\\\\").\
              replace('"', '\\"')
        out.append('  "'+line.rstrip()+'\\n"')
        if comma:
            out[-1]=out[-1]+","
    if out[-1].endswith(","):
        out[-1]=out[-1][:-1]
    out[1]='"%s",' % ("%s" * percents,)
    write_whole_file(dest, "wt", "\n".join(out))

# We depend on every .[ch] file in src
depends=[f for f in glob.glob("src/*.[ch]") if f!="src/apsw.c"]
for f in (findamalgamation(), ):
    if f:
        depends.append(f)
# we produce a .c file from this
depends.append("tools/shell.py")

# work out version number
version=read_whole_file(os.path.join("src", "apswversion.h"), "rt").split()[2].strip('"')

# msi can't use normal version numbers because distutils is retarded,
# so mangle ours to suit it
if "bdist_msi" in sys.argv:
    if version.endswith("-r1"):
        version=version[:-len("-r1")]
    else:
        assert False, "MSI version needs help"
    version=[int(v) for v in re.split(r"[^\d]+", version)]
    # easy pad to 3 items long
    while len(version)<3:
        version.append(0)
    # 4 is our normal length (eg 3.7.3-r1) but sometimes it is more eg
    # 3.7.16.1-r1 so combine last elements if longer than 4
    while len(version)>4:
        version[-2]=10*version[-2]+version-1
        del version[-1]
    # combine first two elements
    if len(version)>3:
        version[0]=100*version[0]+version[1]
        del version[1]

    version=".".join([str(v) for v in version])

setup(name="apsw",
      version=version,
      description="Another Python SQLite Wrapper",
      long_description=\
"""A Python wrapper for the SQLite embedded relational database engine.
In contrast to other wrappers such as pysqlite it focuses on being
a minimal layer over SQLite attempting just to translate the
complete SQLite API into Python.""",
      author="Roger Binns",
      author_email="rogerb@rogerbinns.com",
      url="https://github.com/rogerbinns/apsw/",
      classifiers=[
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved",
    "Operating System :: OS Independent",
    "Programming Language :: C",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Database :: Front-Ends",
    ],
      keywords=["database", "sqlite"],
      license="OSI Approved ::",

      ext_modules=[Extension("apsw",
                             ["src/apsw.c"],
                             include_dirs=include_dirs,
                             library_dirs=library_dirs,
                             libraries=libraries,
                             define_macros=define_macros,
                             depends=depends)],


      cmdclass={'test': run_tests,
                'build_test_extension': build_test_extension,
                'fetch': fetch,
                'build_ext': apsw_build_ext,
                'build': apsw_build,
                'sdist': apsw_sdist,
                'win64hackvars': win64hackvars}
      )
