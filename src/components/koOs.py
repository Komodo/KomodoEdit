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

"""
Exposes some of Python's os module to other languages.
"""

import os
import stat
import sys
import koUnicodeEncoding
from xpcom import components, nsError, ServerException, COMException

lastErrorSvc = None #XXX should be gLastErrorSvc

### Internal functions

def _unique(s):
    """Return a list of the elements in s, in arbitrary order, but without
    duplicates. (_Part_ of the Python Cookbook recipe.)
    """
    # get the special case of an empty s out of the way, very rapidly
    n = len(s)
    if n == 0:
        return []

    # Try using a dict first, as that's the fastest and will usually work.
    u = {}
    try:
        for x in s:
            u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return u.keys()

def _splitall(path):
    """Split the given path into all its directory parts and return the list
    of those parts (see Python Cookbook recipe for test suite.
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def _commonprefix(paths):
    """An os.path.commonprefix() more suited to actual paths.
    
    It returns the common path prefix of the given paths or None, if there
    is no such common prefix.
    """
    if not paths:
        return None
    splitpaths = [_splitall(path) for path in paths]
    commonprefix = []
    for set in zip(*splitpaths):
        # This path element is part of the common prefix if it is the same
        # for every give path.
        elem = set[0]
        if sys.platform.startswith("win"):
            # Case-insensitive comparison on Windows.
            set = [p.lower() for p in set]
        if len(_unique(set)) == 1:
            commonprefix.append(elem)
        else:
            break
    if commonprefix:
        retval = os.path.join(*commonprefix)
    else:
        retval = None
    #print "_commonprefix(%r) == %r" % (paths, retval)
    return retval

def _relpath(path, relTo=None):
    """Return a relative path of the given path.

    "relTo" indicates a directory to which to make "path" relative.
        It default to the cwd if not specified.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if relTo is None:
        relTo = os.getcwd()
    else:
        relTo = os.path.abspath(relTo)

    pathDrive, pathRemainder = os.path.splitdrive(path)
    if not pathDrive:
        pathDrive = os.path.splitdrive(os.getcwd())[0]
    relToDrive, relToRemainder = os.path.splitdrive(relTo)
    if pathDrive != relToDrive:
        raise OSError("Cannot make '%s' relative to '%s'. They are on "\
                      "different drives." % (path, relTo))

    pathParts = _splitall(pathRemainder)[1:] # drop the leading root dir
    relToParts = _splitall(relToRemainder)[1:] # drop the leading root dir
    #print "_relpath: pathPaths=%s" % pathParts
    #print "_relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if pathPart == relToPart: # drop leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "_relpath: pathParts=%s" % pathParts
    #print "_relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relTo" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "_relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath

class koOsPath:
    _com_interfaces_ = [components.interfaces.koIOsPath]
    _reg_clsid_ = "{5f25f8f1-c0aa-4d2f-9519-e2832cedd296}"
    _reg_contractid_ = "@activestate.com/koOsPath;1"
    _reg_desc_ = "Makes os.path available outside of Python"

    def basename(self, path):
        return os.path.basename(path)

    def dirname(self, path):
        return os.path.dirname(path)

    def join(self, path1, path2):
        return os.path.join(path1, path2)

    def joinlist(self, paths):
        return os.path.join(*paths)

    def withoutExtension(self, path):
        return os.path.splitext(path)[0]
    
    def getExtension(self, path):
        return os.path.splitext(path)[1]

    def exists(self, path):
        return os.path.exists(path)
    
    def isfile(self, path):
        return os.path.isfile(path)
    
    def isdir(self, path):
        return os.path.isdir(path)
    
    def isabs(self, path):
        return os.path.isabs(path)
    
    def normpath(self, path):
        return os.path.normpath(path)

    def realpath(self, path):
        return os.path.realpath(path)
    
    def expanduser(self, path):
        return os.path.expanduser(path)
    
    def commonprefix(self, path1, path2):
        return _commonprefix([path1, path2])
    
    def commonprefixlist(self, paths):
        return _commonprefix(paths)
    
    def relpath(self, path, relativeTo):
        return _relpath(path, relativeTo)
    
    def abspath(self, path):
        return os.path.abspath(path)
    
    def lstrippath(self, path, n):
        parts = _splitall(path)
        # '' for first arg is to prevent TypeError if n > len(parts).
        return os.path.join('', *parts[n:])
    
    def samepath(self, path1, path2):
        from os.path import normcase, abspath
        return normcase(abspath(path1)) == normcase(abspath(path2))


class koOs(object):
    _com_interfaces_ = [components.interfaces.koIOs]
    _reg_clsid_ = "{3348b94f-f27e-4819-a689-74978024d106}"
    _reg_contractid_ = "@activestate.com/koOs;1"
    _reg_desc_ = "Makes os available outside of Python"

    _path = None

    def __init__(self):
        global lastErrorSvc
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
               .getService(components.interfaces.koILastErrorService)

        # open() flags
        self.O_RDONLY = os.O_RDONLY
        self.O_WRONLY = os.O_WRONLY
        self.O_RDWR = os.O_RDWR
        self.O_APPEND = os.O_APPEND
        self.O_CREAT = os.O_CREAT
        self.O_EXCL = os.O_EXCL
        self.O_TRUNC = os.O_TRUNC

        self.name = os.name

    def get_sep(self):
        return os.sep

    def get_pathsep(self):
        return os.pathsep

    def get_path(self):
        if self._path is None:
            self._path = components.classes["@activestate.com/koOsPath;1"] \
                         .getService()
        return self._path

    def getenv(self, env):
        return os.getenv(env,'')
    
    def chdir(self, path):
        os.chdir(path)

    def chmod(self, path, mode):
        try:
            os.chmod(path, mode)
        except EnvironmentError, ex:
            lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise

    def getcwd(self):
        return os.getcwd()

    def system(self, command):
        return os.system(command)

    def startfile(self, command):
        os.startfile(command)

    def readfile(self, path):
        try:
            _globalPrefSvc = components.classes["@activestate.com/koPrefService;1"].\
                                getService(components.interfaces.koIPrefService)
            prefs = _globalPrefSvc.prefs
            defaultEncoding = prefs.getStringPref('encodingDefault')
            f = open(path, 'rb')
            buffer = f.read()
            unicode_buffer, encoding, bom = koUnicodeEncoding.autoDetectEncoding(buffer,
                   tryXMLDecl=1,
                   tryHTMLMeta=1,
                   tryModeline=1,
                   wantEncoding=None,
                   defaultEncoding=defaultEncoding)
            return unicode_buffer
        except Exception, ex:
            lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise

    def writefile(self, path, data):
        return open(path, 'wb').write(data)

    def mkdir(self, path):
        try:
            os.mkdir(path)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise

    def rename(self, fn_from, fn_to):
        try:
            os.rename(fn_from, fn_to)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise

    def renames(self, fn_from, fn_to):
        try:
            os.renames(fn_from, fn_to)
        except Exception, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise

    def stat(self, filename):
        try:
            # See http://bugs.activestate.com/show_bug.cgi?id=21252.
            # """stat'ing C:\core\http\clicknames\htdocs\top.phtml returned
            # -1 for the m_time. This from Python's os.stat which uses
            # Windows' _stati64, which makes no mention of error cases
            # for m_time.
            #
            # Proposed workaround: Catch this in koOs::stat method -- if
            # m_time and/or c_time is -1 then consider this an error and
            # default it to a_time. If *a_time* is also -1 then raise an
            # exception (i.e. we will really have to figure out what is
            # going on.) """
            retval = list( os.stat(filename)[:10] )
            if retval[stat.ST_ATIME] == -1:
                raise OSError("stat() returned -1 access time for '%s'"\
                              % filename)
            if retval[stat.ST_MTIME] == -1:
                retval[stat.ST_MTIME] = retval[stat.ST_ATIME]
            if retval[stat.ST_CTIME] == -1:
                retval[stat.ST_CTIME] = retval[stat.ST_ATIME]
            return retval
        except OSError, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise

    def access(self, path, mode):
        return os.access(path, mode)

    def saneAccess(self, path, mode):
        if sys.platform.startswith('win'):
            return 1
        return os.access(path, mode)

    def saneAccessParent(self, path, mode):
        if sys.platform.startswith('win'):
            return 1
        while not os.path.exists(path):
            path = os.path.dirname(path)
        return self.saneAccess(path, mode)

    def getmod(self, path): # return the chmod-relevant part of the mode as returned by stat
        return stat.S_IMODE(os.stat(path).st_mode)

    def setWriteability(self, path, writeable):
        if not os.path.exists(path):
            lastErrorSvc.setLastError(0, "File does not exist")
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "File does not exist")

        try:
            mode = self.getmod(path)
            if writeable:
                desired_mode = mode | stat.S_IWUSR
            else:
                desired_mode = mode & ~stat.S_IWUSR
            os.chmod(path, desired_mode)
            obtained_mode = self.getmod(path)
        except EnvironmentError, ex:
            lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise
    
    def listdir(self, path):
        try:
            return os.listdir(path)
        except OSError, ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise

    def open(self, path, flags):
        try:
            return os.open(path, flags)
        except OSError, ex:
            lastErrorSvc.setLastError(ex.errno, str(ex))
            raise

    def unsetenv(self, varname):
        try:
            return os.unsetenv(varname)
        except OSError, ex:
            lastErrorSvc.setLastError(ex.errno, str(ex))
            raise

