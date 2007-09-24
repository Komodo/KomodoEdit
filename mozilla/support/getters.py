#!/usr/bin/env python

r"""
    A class hierarchy for retrieving files and packages from various
    places (e.g. Mozilla source tarball, mozilla-devel builds from
    \\americano, Mozilla source from CVS, etc.).

    Usage:
        TODO
"""
# TODO:
#   - everything, this is currently just a copy of the ActivePython 2.1
#     code
#

import os
import sys
import re

import logger



#---- exceptions

class GetterError(Exception):
    pass



#---- globals

log = logger.Logger("getters", logger.Logger.INFO)



#---- public interface

#XXX Can get the latest mozilla-source.tar.gz from
#    http://archive.progeny.com/mozilla/nightly/latest/

class Getter:
    """The Getter interface:

    get(self, <destination>)
        Get files from the repository that this getter represents and put it
        in the destination folder.  It returns a list of tuple (one per file
        gotten) of the form:
            (<relative-file-path>, <file-meta-data>)
        The type of <file-meta-data> is not specified. This may describe file
        attributes, or whatever. For example, Perforce or CVS filetype
        information.
    """
    def get(self, dest):
        raise NotImplementedError,\
              "This is virtual function, you must subclass it."


class RelCandiGetter(Getter):
    """Get the latest build of the relevant package(s) ('package') matching
    all the specified arguments. The valid values of 'package' are:
        'archppm': PyPPM modules package for one architecture
    For example to get the latest ActivePython 2.1.2 windows installer:
        RelCandiGetter("windows", product="ActivePython", version="2.1.2")
    To get the latest PythonDirect 213 linux packages:
        RelCandiGetter("linux", product="PythonDirect", buildnum="213")
    """
    def __init__(self, package, product, version=None, arch=None,
                 buildnum=None, cfg=''):
        self.package = package
        self.product = product
        self.version = version
        self.arch = arch
        self.buildnum = buildnum
        # Configuration suffix string, e.g. '-ssl', default config == ''
        self.cfg = cfg
        if sys.platform[:3] == "win":
            self.relcandi = r"\\crimper\apps\ActivePython\RelCandi"
        elif sys.platform[:5] == "linux":
            self.relcandi = r"/nfs/crimper/home/apps/ActivePython/RelCandi"
        else:
            self.relcandi = r"/mnt/crimper/home/apps/ActivePython/RelCandi"

    def get(self, dest):
        query = {
            'product': self.product or '\w+',
            'version': self.version or '\d+\.\d+\.\d+',
            'buildnum': self.buildnum or '\d+',
            'arch': self.arch or '\w+-\w+',
            'cfg': self.cfg,
        }
        pattern = "%(product)s-%(version)s-%(buildnum)s-%(arch)s%(cfg)s"\
                  % query
        msg = "Populate '%s' with latest %s package(s) for '%s'."\
              % (dest, self.package, pattern)
        print msg

        getter = getattr(self, '_get_' + self.package)
        getter(query, dest)

    def _get_archppm(self, query, dest):
        base = self.relcandi
        pattern = re.compile("^%(product)s-%(version)s-%(buildnum)s-%(arch)s"\
                             "\.zip$" % query)
        files = self._find_packages(base, [pattern])
        # Unzip documentation package into 'dest'.
        unzip = os.path.join(gPlat2BinDir[sys.platform], "unzip")
        oldDir = os.getcwd()
        try:
            os.chdir(dest)
            for file in files:
                cmd = '%s %s' % (unzip, file)
                print "extract '%s' to '%s'" % (file, dest)
                retval = os.system(cmd)
                if retval:
                    raise BuildError("Error running '%s': retval=%d"\
                                     % (cmd, retval))
        finally:
            os.chdir(oldDir)

    def _find_packages(self, base, patterns):
        builds = os.listdir(base)
        builds.sort()
        builds.reverse()
        #print "patterns", patterns
        #print "builds:", builds
        for build in builds:
            files = []
            for pattern in patterns:
                matches = []
                for f in os.listdir(os.path.join(base, build)):
                    if pattern.match(f):
                        matches.append(os.path.join(base, build, f))
                if not matches:
                    break
                else:
                    files = file + matches
            else:
                break
        else:
            pats = []
            for p in patterns:
                pats.append(p.pattern)
            raise BuildError("Could not find a build of the following "\
                             "patterns in '%s': %s" % (base, pats))
        return files 


