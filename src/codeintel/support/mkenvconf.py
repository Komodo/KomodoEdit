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

r"""Make an 'envconf' shell script for codeintel dev work.

Codeintel development works like this:
1. Get the codeintel source.
        cd .../komodo/src/codeintel
2. Setup build environment:
        bin\setenv.bat          # Windows
        . bin\setenv.sh         # other plats
3. Build, test, commit.

The relevant part here is step #2. Those 'setenv' scripts do this:
- call 'support/mkenvconf.py' to generate 'tmp/envconf.{bat|sh}'
- call the generated envconf script

"""

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, dirname, basename, abspath, exists, normpath
import sys
import re
import pprint
import glob
import traceback
import logging
import optparse

import which



#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("mkenvconf")



#---- main functions

def mkenvconf():
    log.debug("mkenvconf: start")
    
    # This should only be run via the setenv scripts and only from the
    # top-level codeintel dir. Verify the latter, at least.
    landmark = join("lib", "codeintel2", "citadel.py")
    if not exists(landmark):
        raise Error("support/mkenvconf.py should only be run via the "
                    "bin/setenv.{bat|sh} scripts and only from the "
                    "top-level codeintel dir: `%s' landmark does not exist"
                    % landmark)

    envconf = []
    CODEINTEL_SRC = abspath(os.getcwd())
    python = get_config().python

    # Put 'bin' on PATH. Also, if not already first, put the configured
    # python first on PATH.
    paths = []
    if not which.which("python").lower() == python.lower():
        paths.append(dirname(python))
    paths.append(join(CODEINTEL_SRC, "bin"))
    if sys.platform == "win32":
        envconf.append("set PATH=%s;%%PATH%%" % os.pathsep.join(paths))
    else:
        envconf.append("export PATH=%s:$PATH" % os.pathsep.join(paths))
    
    # Put necessary dirs on PYTHONPATH.
    komodo_src_dir = normpath(join(CODEINTEL_SRC, "..", ".."))
    pythonpaths = [
        join(CODEINTEL_SRC, "lib"),
        join(CODEINTEL_SRC, "support"),
        # 'python-sitelib' needed for XML completion support stuff
        # and textinfo/langinfo system
        join(komodo_src_dir, "src", "python-sitelib"),
        # 'find' needed for findlib2.py
        join(komodo_src_dir, "src", "find"),
        # 'util' needed for testlib.py
        join(komodo_src_dir, "util"),
        join(komodo_src_dir, "contrib" ,"zope" ,"cachedescriptors" ,"src"),
    ]

    # Make the zope directory a package.
    if not exists(join(komodo_src_dir, "contrib" ,"zope", "cachedescriptors", "src", "zope", "__init__.py")):
        file(join(komodo_src_dir, "contrib" ,"zope", "cachedescriptors", "src", "zope", "__init__.py"), "w").write("")

    udl_skel_dir = join(komodo_src_dir, "src", "udl", "skel")
    for d in os.listdir(udl_skel_dir):
        pylib_dir = join(udl_skel_dir, d, "pylib")
        if exists(pylib_dir):
            pythonpaths.append(pylib_dir)
    if sys.platform == "win32":
        # Also need the winprocess module on Windows.
        pythonpaths.append(join(komodo_src_dir, "contrib", "smallstuff"))
        envconf.append("set PYTHONPATH=%s;%%PYTHONPATH%%"
                       % os.pathsep.join(pythonpaths))
    else:
        envconf.append("""
if [ -z "$PYTHONPATH" ]; then
    export PYTHONPATH=%s
else
    export PYTHONPATH=%s:$PYTHONPATH
fi
""" % (os.pathsep.join(pythonpaths), os.pathsep.join(pythonpaths)))
    
    # On Windows, determine which compiler is appropriate for the configured
    # Python and call the appropriate setup script for that compiler.
    if sys.platform == "win32":
        msvc_ver = _capture_python_output(python,
            "import distutils.msvccompiler as c; "
            "print c.get_build_version()").strip()
        if msvc_ver == "6":
            msvc_setenv = r"C:\Program Files\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT"
        elif msvc_ver.startswith("7"):
            msvc_setenv = r"C:\Program Files\Microsoft Visual Studio .NET 2003\Vc7\bin\vcvars32.bat"
        elif msvc_ver.startswith("8"):
            msvc_setenv = r"C:\Program Files\Microsoft Visual Studio 8\VC\bin\vcvars32.bat"
        elif msvc_ver.startswith("9"):
            msvc_setenv = r"C:\Program Files\Microsoft Visual Studio 9.0\VC\bin\vcvars32.bat"
        elif msvc_ver.startswith("11"):
            msvc_setenv = r"C:\Program Files\Microsoft Visual Studio 11.0\VC\bin\vcvars32.bat"
        else:
            raise Error("unrecognized MSVC version used to build your "
                        "configured python: '%s' (python='%s')"
                        % (msvc_ver, python))
        if not exists(msvc_setenv):
            # Try the x86 version, on Windows 7 it might be under:
            #   C:\Program Files (x86)\
            alt_msvc_setenv = msvc_setenv.replace("Program Files",
                                                  "Program Files (x86)")
            if exists(alt_msvc_setenv):
                msvc_setenv = alt_msvc_setenv
            else:
                raise Error("environ script for MSVC %s does not exist: '%s'"
                            % (msvc_ver, msvc_setenv))
        envconf.append('call "%s"' % msvc_setenv)

    # Setup some convenience aliases non-Windows.
    if sys.platform != "win32":
        envconf.append("alias ci2='python %s/ci2.py'" % CODEINTEL_SRC)
        envconf.append("alias mk='python Makefile.py'")

    # Write out the envconf to 'tmp/envconf.{bat|sh}'.
    tmp_dir = "tmp"
    if not exists(tmp_dir):
        log.debug("mkdir `%s'", tmp_dir)
        os.makedirs(tmp_dir)
    if sys.platform == "win32":
        envconf_path = join(tmp_dir, "envconf.bat")
    else:
        envconf_path = join(tmp_dir, "envconf.sh")
    if exists(envconf_path):
        log.debug("rm `%s'", envconf_path)
        os.remove(envconf_path)
    log.info("create `%s'", envconf_path)
    fout = open(envconf_path, 'w')
    try:
        fout.write('\n\n'.join(envconf))
    finally:
        fout.close()
    


#---- internal support functions


def get_config():
    return _module_from_path("config.py")

# Recipe: module_from_path (1.0) in C:\trentm\tm\recipes\cookbook
def _module_from_path(path):
    from os.path import dirname, basename, splitext
    import imp
    dir  = dirname(path) or os.curdir
    name = splitext(basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)

def _capture_python_output(python, oneliner):
    assert ' ' not in python
    assert '"' not in oneliner
    cmd = '%s -c "%s"' % (python, oneliner)
    i,o,e = os.popen3(cmd)
    i.close()
    stdout = o.read()
    stderr = e.read()
    o.close()
    retval = e.close()
    if retval:
        raise Error("error running '%s': stdout=%r, stderr=%r, retval=%r"
                    % (cmd, stdout, stderr, retval))
    return stdout
    


#---- mainline


# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


def main(argv):
    usage = "usage: %prog"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="make", usage=usage, version=version,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.set_defaults(log_level=logging.INFO)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    return mkenvconf()


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.isEnabledFor(logging.DEBUG):
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)


