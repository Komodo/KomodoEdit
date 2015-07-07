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

# Makefile for codeintel.
#

import os
from os.path import join, dirname, basename, isdir, isfile, abspath,\
                    splitext, exists
import sys
from glob import glob
import logging
import shutil
import stat
import re


sys.path.insert(0, join(dirname(__file__), "support"))
try:
    import make
    from make import makes, dep, default, MakeError
    import eol

    try:
        import config as cfg
    except ImportError, ex:
        raise MakeError("could not import configuration: %s" % ex)
    from config import xpath
finally:
    del sys.path[0]


#---- globals

#XXX fallback for not passing log arg through to _run et al
log = logging.getLogger("make")

EXE = (sys.platform == "win32" and ".exe" or "")
LIB = (sys.platform == "win32" and ".lib" or ".a")
def STATIC_LIB_NAME(name, lib_prefix_on_win=False):
    if sys.platform == "win32":
        if lib_prefix_on_win:
            return "lib"+name+LIB
        else:
            return name+LIB
    else:
        return "lib"+name+LIB
PYD = (sys.platform == "win32" and ".pyd" or ".so")



#---- primary make targets

@default
@dep("silvercity", "udl_lexers", "elementtree", "inflector") 
def make_all(maker, log):
    pass

@dep("distclean_scintilla",
     "distclean_udl_lexers",
     "distclean_pcre",
     "distclean_silvercity",
     #XXX Currently can only handle syck on non-Windows.
     #"distclean_syck",
     "distclean_elementtree",
     "distclean_inflector")
def make_distclean(maker, log):
    pass


#---- secondary and internal targets

@makes("src/scintilla")
def make_src_scintilla(maker, log):
    METHOD = "komodo"
    if METHOD == "source package":
        pattern = "scintilla*.tgz"
        candidates = []
        for src_repo in cfg.src_repositories:
            candidates += glob(join(src_repo, pattern))
        if not candidates:
            raise MakeError("cannot find scintilla source (%s) in source "
                            "repositories: '%s'"
                            % (pattern, "', '".join(cfg.src_repositories)))
        candidates.sort()
        pkg_path = abspath(candidates[-1])
        _run_in_dir("tar xzf %s" % pkg_path, "src", logstream=log.info)
    elif METHOD == "komodo":
        ko_scintilla_dir = join(cfg.komodo_src, "src", "scintilla")
        if not isdir(ko_scintilla_dir):
            raise MakeError("cannot find Komodo scintilla source dir: '%s'"
                            % ko_scintilla_dir)
        assert ' ' not in ko_scintilla_dir
        _cp(ko_scintilla_dir, "src/scintilla", logstream=log.info)

    # Purge all but the following lexer languages.
    langs_to_keep = [
        "Python", "HTML", "Perl", "CSS", "Ruby", "Tcl", "XSLT",
        "UDL", "CoffeeScript",
        "Others",   # to get SCLEX_NULL
        # Hardcoded expectations in SilverCity/LanguageInfo.py
        "CPP", "SQL", "YAML", "PS",
    ]
    scintilla_src_dir = join("src", "scintilla", "src")
    scintilla_lexer_dir = join("src", "scintilla", "lexers")
    available_langs = [
        basename(f)[3:-4]
        for f in glob(join(scintilla_lexer_dir, "Lex*.cxx"))
    ]
    langs_to_purge = [lang for lang in available_langs
                      if lang not in langs_to_keep]
    for lang in langs_to_purge:
        cxx_path = join(scintilla_lexer_dir, "Lex%s.cxx" % lang)
        _rm(cxx_path, log.info)

    # Run the source generators post- changes to the sources.
    _run_in_dir(cfg.python+" LexGen.py", "src/scintilla/scripts",
                logstream=log.info)

    if METHOD == "komodo":
        # Generate the *_gen.h files that have been added to the
        # Scintilla build process by Komodo.
        _run_in_dir(cfg.python+" HFacer.py", "src/scintilla/scripts",
                    logstream=log.info)


def make_distclean_scintilla(maker, log):
    _rm("src/scintilla", logstream=log.info)


@makes("src/SilverCity")
def make_src_silvercity(maker, log):
    METHOD = "komodo" # one of "komodo" or "tarball"
    if METHOD == "komodo":
        ko_silvercity_dir = join(cfg.komodo_src, "src", "silvercity")
        if not isdir(ko_silvercity_dir):
            raise MakeError("cannot find Komodo silvercity source dir: '%s'"
                            % ko_silvercity_dir)
        assert ' ' not in ko_silvercity_dir
        dest = join("src", "SilverCity")
        _cp(ko_silvercity_dir, dest, logstream=log.info)

        if sys.platform == "win32":
            for dirpath, dirnames, filenames in os.walk(dest):
                for filename in filenames:
                    _run("attrib -R %s" % join(dirpath, filename),
                         logstream=log.info)
        else:
            _run("chmod -R ug+w %s" % dest, logstream=log.info)
    elif METHOD == "tarball":
        pattern = "SilverCity-*.tar.gz"
        candidates = []
        for src_repo in cfg.src_repositories:
            candidates += glob(join(src_repo, pattern))
        if not candidates:
            raise MakeError("cannot find SilverCity source (%s) in source "
                            "repositories: '%s'"
                            % (pattern, "', '".join(cfg.src_repositories)))
        candidates.sort()
        pkg_path = abspath(candidates[-1])
        pkg_name = basename(pkg_path)[:-len(".tar.gz")]
        _run_in_dir("tar xzf %s" % pkg_path, "src", logstream=log.info)
        _mv(xpath("src", pkg_name), xpath("src/SilverCity"), logstream=log.info)

        for dirname, dirs, files in os.walk("src/SilverCity"):
            for file in files:
                eol.convert_path_eol(join(dirname, file), eol.NATIVE,
                                     log=log)

        # Patch it.
        #XXX Use my patchtool thing.
        for patchfile in glob("src/patches/silvercity-*.patch"):
            _run_in_dir("patch -p0 < %s" % abspath(patchfile), "src",
                        logstream=log.info)


def make_distclean_udl_lexers(maker, log):
    _rm("lib/codeintel2/lexers", log.info)
    _rm("build")

@makes("lib/codeintel2/lexers")
def make_udl_lexers(maker, log):
    udl_build_dir = join(cfg.komodo_src, "build", cfg.komodo_cfg.buildType,
                         "udl", "build")
    if not exists(udl_build_dir):
        raise MakeError("cannot find UDL lexres files in Komodo build area "
                        "(`%s' does not exist): have you built Komodo?"
                        % udl_build_dir)
    lexres_dst_dir = join("lib", "codeintel2", "lexers")
    if not isdir(lexres_dst_dir):
        os.makedirs(lexres_dst_dir)
    for lexres_path in glob(join(udl_build_dir, "*", "lexers", "*.lexres")):
        _cp(lexres_path, lexres_dst_dir, log.info)


def make_distclean_pcre(maker, log):
    paths = [
        "src/SilverCity/"+STATIC_LIB_NAME("pcre", lib_prefix_on_win=True),
        "src/scintilla/include/pcre.h",
        "src/scintilla/win32/"+STATIC_LIB_NAME("pcre", lib_prefix_on_win=True)
    ]
    for path in paths:
        _rm(path, log.info)
    
@makes("src/SilverCity/"+STATIC_LIB_NAME("pcre", lib_prefix_on_win=True),
       "src/scintilla/include/pcre.h",
       "src/scintilla/win32/"+STATIC_LIB_NAME("pcre", lib_prefix_on_win=True))
def make_pcre(maker, log):
    """Make the PCRE lib (used by LexUDL)

    XXX Cheat for now and just get it from the Komodo build.
    """
    libpcre = STATIC_LIB_NAME("pcre", lib_prefix_on_win=True)
    src = join(cfg.komodo_src, "build", "release", "silvercity", libpcre)
    if not exists(src):
        raise MakeError("couldn't find `%s' in your Komodo build: you need to "
                    "have a local build of Komodo (yes this is a lazy, "
                    "cheating hack): %s" % (libpcre, src))
    for dest_dir in ("src/SilverCity", "src/scintilla/win32"):
        _cp(src, dest_dir, log.info)
        if cfg.platinfo.os == "macosx":
            _run("ranlib %s/%s" % (dest_dir, libpcre), log.info)
    _cp(join(cfg.komodo_src, "build", "release", "scintilla", "include", "pcre.h"),
        "src/scintilla/include", log.info)


@dep("distclean_scintilla")
def make_distclean_silvercity(maker, log):
    _rm("lib/SilverCity", logstream=log.info)
    _rm("src/SilverCity", logstream=log.info)

def make_clean_silvercity(maker, log):
    _rm("lib/SilverCity", logstream=log.info)
    _rm("src/SilverCity/build", logstream=log.info)

@dep("src_scintilla", "src_silvercity", "pcre")
@makes("lib/SilverCity")
def make_silvercity(maker, log):
    src_dir = xpath("src/SilverCity")

    # Regenerate ScintillaConstants.py for new scintilla sources.
    _cp("src/scintilla/scripts/Face.py", src_dir+"/PySilverCity/Src/Face.py")
    _run_in_dir(cfg.python+" PySilverCity/Src/write_scintilla.py ../scintilla/include ../scintilla/include/Scintilla.iface PySilverCity/SilverCity/ScintillaConstants.py",
                src_dir, logstream=log.info)

    # Distutils' --install-data doesn't seem to NOT install default.css
    # to the lib dir without this hack.
    _run_in_dir(cfg.python+" setup.py install --prefix=bitbucket "
                    "--install-data=bitbucket --install-scripts=bitbucket "
                    "--install-lib=%s" % abspath("lib"),
                src_dir, logstream=log.info)


@dep("clean_elementtree")
def make_distclean_elementtree(maker, log):
    _rm("src/elementtree", logstream=log.info)
    _rm("src/cElementTree", logstream=log.info)
    _rm("src/ciElementTree", logstream=log.info)

def make_clean_elementtree(maker, log):
    _rm("lib/elementtree", logstream=log.info)
    _rm("lib/cElementTree"+PYD, logstream=log.info) # clean for transitional period
    _rm("lib/ciElementTree"+PYD, logstream=log.info)

@makes("src/cElementTree")
def make_src_elementtree(maker, log):
    """Make elementtree, cElementTree and (codeintel's custom) ciElementTree
    Python packages and extensions.
    """
    src_dir_from_dst_dir = {
        # Note that currently the sources in
        # "contrib/{elementtree|cElementTree}" are *already* patched with
        # the patches in "contrib/patches/{cElementTree|elementtree}_*".
        "src/elementtree": join(cfg.komodo_src, "contrib", "elementtree"),
        "src/cElementTree": join(cfg.komodo_src, "contrib", "cElementTree"),
        "src/ciElementTree": join(cfg.komodo_src, "contrib", "cElementTree"),
    }
    for dst_dir, src_dir in src_dir_from_dst_dir.items():
        if not isdir(src_dir):
            raise MakeError("cannot find Komodo elementtree source dir: '%s'"
                            % src_dir)
        assert ' ' not in src_dir
        _cp(src_dir, dst_dir, logstream=log.info)
        _rm("src/%s/build" % basename(dst_dir), logstream=log.info)

    # Patch it.
    #XXX Use my patchtool thing.
    for dirpath, dirnames, filenames in os.walk("src/ciElementTree"):
        for filename in filenames:
            path = join(dirpath, filename)
            curr_mode = stat.S_IMODE(os.stat(path).st_mode)
            writeable_mode = curr_mode | 0200 # make writeable
            if curr_mode != writeable_mode:
                os.chmod(path, writeable_mode)
    found_some_patches = False
    for patchfile in sorted(glob("src/patches/ciElementTree-*.patch")):
        found_some_patches = True
        if sys.platform.startswith("win"):
            # on Windows, we need to make sure the patch file has CRLF line
            # endings, because patch.exe is crap
            with open(patchfile, "r") as f:
                data = f.read()
            if not "\r\n" in data:
                sys.stderr.write("Warning: converting \"%s\" to DOS line endings" %
                                 (abspath(patchfile),))
                with open(patchfile, "w") as f:
                    f.write(data)

        _run_in_dir("patch -p0 < %s" % abspath(patchfile), "src",
                    logstream=log.info)
    assert found_some_patches, "something wrong with finding ciElementTree patches"

@dep("src_elementtree")
@makes("lib/ciElementTree"+PYD)
def make_elementtree(maker, log):
    elementtree_dirs = [xpath("src/elementtree"),
                        xpath("src/cElementTree"),
                        xpath("src/ciElementTree")]
    for src_dir in elementtree_dirs:
        # Distutils' --install-data doesn't seem to NOT install default.css
        # to the lib dir without this hack.
        if cfg.komodo_cfg.buildType == "debug":
            debug_flags = "--debug"
        else:
            debug_flags = ""
        if sys.platform == "darwin":
            os.environ["CFLAGS"] = os.environ.get("CFLAGS", "").replace("-fvisibility=hidden", "") + " -arch x86_64"
            os.environ["CXXFLAGS"] = os.environ.get("CXXFLAGS", "").replace("-fvisibility=hidden", "") + " -arch x86_64"
        _run_in_dir(" ".join([cfg.python, "setup.py", "build", debug_flags]),
                    src_dir, logstream=log.info)
        _run_in_dir(cfg.python+" setup.py install --skip-build --prefix=bitbucket "
                        "--install-data=bitbucket --install-scripts=bitbucket "
                        "--install-lib=%s" % abspath("lib"),
                    src_dir, logstream=log.info)



def make_distclean_inflector(maker, log):
    _rm("lib/inflector", logstream=log.info)

@makes("lib/inflector")
def make_inflector(maker, log):
    METHOD = "komodo"
    if METHOD == "komodo":
        ko_inflector_dir = join(cfg.komodo_src, "contrib", "inflector")
        if not isdir(ko_inflector_dir):
            raise MakeError("cannot find Komodo inflector source dir: '%s'"
                            % ko_inflector_dir)
        assert ' ' not in ko_inflector_dir
        dest = join("lib", "inflector")
        _cp(ko_inflector_dir, dest, logstream=log.info)

        if sys.platform == "win32":
            for dirpath, dirnames, filenames in os.walk(dest):
                for filename in filenames:
                    _run("attrib -R %s" % join(dirpath, filename),
                         logstream=log.info)
        else:
            _run("chmod -R ug+w %s" % dest, logstream=log.info)



@makes("src/syck")
def make_src_syck(maker, log):
    pattern = "syck-*.tar.gz"
    candidates = []
    for src_repo in cfg.src_repositories:
        candidates += glob(join(src_repo, pattern))
    if not candidates:
        raise MakeError("cannot find Syck source (%s) in source "
                        "repositories: '%s'"
                        % (pattern, "', '".join(cfg.src_repositories)))
    candidates.sort()
    pkg_path = abspath(candidates[-1])
    pkg_name = basename(pkg_path)[:-len(".tar.gz")]
    _run_in_dir("tar xzf %s" % pkg_path, "src", logstream=log.info)
    _mv(xpath("src", pkg_name), xpath("src/syck"), logstream=log.info)

@dep("distclean_scintilla")
def make_distclean_syck(maker, log):
    for base in ("syck"+PYD, "yaml2xml.py*", "ydump.py*", "ypath.py*"):
        _rm("lib/"+base, logstream=log.info)
    _rm("src/syck", logstream=log.info)

if sys.platform != "win32":
    ##def make_clean_syck(maker, log):
    ##    XXX

    @dep("src_syck")
    @makes("lib/syck"+PYD)
    def make_syck(maker, log):
        src_dir = xpath("src/syck")

        _run_in_dir("./configure", src_dir, logstream=log.info)
        _run_in_dir("make", src_dir, logstream=log.info)
        _run_in_dir(cfg.python+" setup.py install --install-lib=%s"
                        % abspath("lib"),
                    src_dir/"ext/python", logstream=log.info)



#---- internal support stuff

# Recipe: run (0.5.3) in /home/trentm/tm/recipes/cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s' from %s: %r" % (cmd, os.getcwd(), status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)

def _rm(path, logstream=None):
    """My little lame cross-platform 'rm -rf'"""
    assert ' ' not in path,\
        "_rm: can't handle paths in spaces: '%s'" % path
    if sys.platform == "win32":
        path = path.replace("/", "\\")
        assert "*" not in path and "?" not in path,\
            "_rm on win32: can't yet handle wildcards: '%s'" % path
        if not exists(path):
            pass
        elif isdir(path):
            _run("rd /s/q %s" % path, logstream=logstream)
        else:
            if not os.access(path, os.W_OK):
                _run("attrib -R %s" % path, logstream=logstream)
            _run("del /q %s" % path, logstream=logstream)
    else:
        _run("rm -rf %s" % path, logstream=logstream)

def _mv(src, dest, logstream=None):
    """My little lame cross-platform 'mv'"""
    assert ' ' not in src and ' ' not in dest,\
        "_mv: can't handle paths in spaces: src=%r, dest=%r" % (src, dest)
    if sys.platform == "win32":
        _run("move %s %s" % (src, dest), logstream=logstream)
    else:
        _run("mv %s %s" % (src, dest), logstream=logstream)

def _cp(src, dest, logstream=None):
    """My little lame cross-platform 'cp'"""
    assert ' ' not in src and ' ' not in dest,\
        "_cp: can't handle paths in spaces: src=%r, dest=%r" % (src, dest)
    if sys.platform == "win32":
        src = src.replace("/", "\\")
        dest = dest.replace("/", "\\")
        if isdir(src):
            _run("xcopy /e/i/y/q %s %s" % (src, dest), logstream=logstream)
        else:
            _run("copy /y %s %s" % (src, dest), logstream=logstream)
    else:
        if isdir(src):
            _run("cp -R %s %s" % (src, dest), logstream=logstream)
        else:
            _run("cp %s %s" % (src, dest), logstream=logstream)



#---- mainline

if __name__ == "__main__":
    make.main()

