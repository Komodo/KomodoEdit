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

# A better implementation of uri's than urllib stuff

# needed for ftpfile
import urlparse, urllib
import stat, os, sys, copy
from os.path import splitdrive
from hashlib import md5
import types, re

win32 = sys.platform.startswith("win")
from xpcom import components, COMException, ServerException, nsError
from xpcom.server import UnwrapObject
from zope.cachedescriptors.property import LazyClassAttribute

if win32:
    WIN32_DRIVE_REMOTE = 4
    # Import the Win32 GetDriveTypeW API:
    # http://msdn.microsoft.com/en-us/library/aa364939%28VS.85%29.aspx
    from ctypes import windll
    Win32_GetDriveTypeW = windll.kernel32.GetDriveTypeW
    del windll

import logging
log = logging.getLogger('URIlib')
#log.setLevel(logging.DEBUG)

def addSchemeToParser(scheme):
    urlparse.uses_relative.append(scheme)
    urlparse.uses_netloc.append(scheme)
    urlparse.uses_params.append(scheme)
    urlparse.uses_query.append(scheme)
    urlparse.uses_fragment.append(scheme)

addSchemeToParser('macro')
addSchemeToParser('snippet')

# For toolbox2 items in v.6:
addSchemeToParser('macro2')
addSchemeToParser('snippet2')

RemoteURISchemeTypes = [ 'ftp' ]

protocolsWithCrypto = ['ftps', 'sftp', 'scp']
for protocol in protocolsWithCrypto:
    addSchemeToParser(protocol)
    RemoteURISchemeTypes.append(protocol)

class URILibError(Exception):
    pass

# Split up a server field, of the form "me:mypass@servername:portnum"
# into it's components
class URIServerParser(object):
    _serveruri = None
    _username = None
    _password = None
    _hostname = None
    _port     = None

    def __init__(self, serveruri=None):
        if serveruri:
            self.parseServerUri(serveruri)
    
    def dump(self):
        print
        print "serveruri:[%s]"%self._serveruri
        print "username: [%s]"%self._username
        print "password: [%s]"%self._password
        print "hostname: [%s]"%self._hostname
        print "port:     [%s]"%self._port
        print

    # Parse up a serveruri into it's component fields
    # Raises ValueError on failure, because serveruri was not in the correct format.
    def parseServerUri(self, serveruri):
        self._serveruri = serveruri
        u = re.search("^(([^:@]+)(:([^:]+))?@)?([^:@]+)(:(.*))?", self._serveruri)
        if not u:
            raise ValueError, "Regular Expression Failure in %s" % (self._serveruri)
        ug = u.groups()
        self._username, self._password, self._hostname, self._port = ug[1], ug[3], ug[4], ug[6]
        # Unquote the individual pieces from the URL.
        if self._username:
            self._username = urllib.unquote(self._username)
        if self._password:
            self._password = urllib.unquote(self._password)
        if self._hostname:
            self._hostname = urllib.unquote(self._hostname)

    #attribute string ServerURI;
    def get_ServerURI(self):
        return self._serveruri
    # This is the only setter attribute for the class
    def set_ServerURI(self, serveruri):
        self.parseServerUri(serveruri)
    ServerURI = property(get_ServerURI, set_ServerURI)

    def get_username(self):
        return self._username
    username = property(get_username)

    def get_password(self):
        return self._password
    password = property(get_password)

    def get_hostname(self):
        return self._hostname
    hostname = property(get_hostname)

    def get_port(self):
        return self._port
    port = property(get_port)


class URIParser(object):
    fileName = None
    _uri = None
    _path = None
    _server = None
    _baseName = None
    _dirName = None
    _ext = None

    # Lazily loaded class variables.
    @LazyClassAttribute
    def komodoStartupEncoding(self):
        return components.classes['@activestate.com/koInitService;1'].\
                    getService(components.interfaces.koIInitService).\
                    getStartupEncoding()
    @LazyClassAttribute
    def encodingServices(self):
        return components.classes['@activestate.com/koEncodingServices;1'].\
                    getService(components.interfaces.koIEncodingServices);

    def __init__(self, uri=None):
        # _fileParsed contains broken up parts of the URI, indexes are:
        #   0  scheme
        #   1  netloc
        #   2  path      (the path is *always* unquoted)
        #   3  query
        #   4  fragment
        self._fileParsed = ['', '', '', '', '']
        if uri:
            self.set_URI(uri)
    
    def _clear(self):
        self.fileName = None
        self._uri = None
        self._path = None
        self._server = None
        self._baseName = None
        self._dirName = None
        self._ext = None
        self._fileParsed = ['', '', '', '', '']
    
    def dump(self):
        print
        print "_uri:     [%s]"%self._uri
        print "fileName: [%s]"%self.fileName
        print "URI:      [%s]"%self.URI
        print "scheme:   [%s]"%self.scheme
        print "server:   [%s]"%self.server
        print "path:     [%s]"%self.path
        print "leafName: [%s]"%self.leafName
        print "baseName: [%s]"%self.baseName
        print "dirName:  [%s]"%self.dirName
        print "ext:      [%s]"%self.ext
        print
        
    def _parseURI(self, uri, doUnquote=True):
        #print "_parseURI[%s]"%uri
        if win32:
            uri = uri.replace('\\','/')
            # fix the uri if we get the lame pipe in place of colon uri's
            try:
                colon_pos = len("file:///z:") - 1
                if uri[colon_pos] == "|":
                    uri = uri[:colon_pos] + ":" + uri[colon_pos + 1:]
            except IndexError:
                pass # uri too short

        #assert uri.find("://") != -1
        # If we got a Netscape UNC file uri, fix it.
        if uri.startswith("file://///"):
            uri = uri.replace("file://///", "file://", 1)

        parts = list(urlparse.urlsplit(uri,'file',0))

        # prevent /c:/ paths from persisting
        if len(parts[2]) > 2 and parts[2][0]=='/' and \
            (parts[2][2] ==":" > 3 or \
             parts[2].find("://") > 0):
            parts[2] = parts[2][1:]

        # Unquote the path from the URL parts.
        if doUnquote and parts[2].find('%') != -1:
            parts[2] = urllib.unquote(parts[2])

        return parts
    
    def _buildURI(self, parts):
        # XXX we may need to do more about quoting
        # if a windows path, fix it
        uparts = list(parts)
        if win32:
            uparts[2] = uparts[2].replace('\\','/')
            if uparts[0] == "file" and uparts[1] != "":
                # Win32, scheme=file with a non-empty netloc - a UNC path
                # Force the netloc to have 3 extra slashes, so we end up with
                # a Netscape-style five-slash file://///netloc/share/
                uparts[1] = "///" + uparts[1]
        prefix = ""
        if ' ' in uparts[2] or '%' in uparts[2]:
            if uparts[2].find(':') == 1:
                prefix = uparts[2][:2]
                uriPart = uparts[2][2:]
            elif uparts[2].find('://') > 0:
                # XXX a bit of a hack to support koremote
                # which contains a sub-url.  currently the only
                # koremote is our ftp support, which doesn't expect
                # to get quoted url's
                # XXX -- 2008/12/19 - this part seems obsolete,
                #   as nothing in Komodo currently creates koremote URIs
                
                moreparts = self._parseURI(uparts[2])
                if not moreparts:
                    uriPart = uparts[2]
                else:
                    uriPart = None
            else:
                uriPart = uparts[2]
            if uriPart:
                try:
                    uriPartQuoted = urllib.quote(uriPart)
                    if win32:
                        uparts[2] = prefix + uriPartQuoted
                    uparts[2] = prefix + uriPartQuoted
                except KeyError, e:
                    # quote fails on unicode chars - bug 63027, just pass
                    # through and hope for the best.
                    # Toddw: We could fall back to the Mozilla escape handling,
                    #        which does a better job of handling Unicode chars:
                    #          netUtilSvc = components.classes['@mozilla.org/network/util;1']\
                    #                .getService(components.interfaces.nsINetUtil)
                    #          uparts[2] = prefix + netUtilSvc.escapeURL(uriPart, netUtilSvc.ESCAPE_URL_FILEPATH)
                    pass
        return urlparse.urlunsplit(tuple(uparts))

    def _setFileNames(self, fileName, doUnquote=True):
        # Expects a URI where *no* urlunquote has yet been done. Unquoting
        # of the path itself will be done as part of the _parseURI() method
        # if the doUnquote argument is True.
        self._clear()
        if fileName:
            self.fileName = fileName
            self._fileParsed = self._parseURI(fileName, doUnquote)
            self._uri = self._buildURI(self._fileParsed)
            
    def _encodeForFileSystem(self, filename):
        # get a decoded version of uri.path.  This exists to fix reading
        # files with latin-1 or other 8 bit encodings on systems where
        # utf-8 support is incomplete (bug 29040)
        if type(filename) == types.UnicodeType:
            try:
                fn_enc = sys.getfilesystemencoding()
                if not fn_enc:
                    if sys.platform.startswith('win'):
                        fn_enc = 'mbcs'
                    elif sys.platform.startswith('darwin'):
                        fn_enc = 'utf-8'
                    else:
                        fn_enc = self.komodoStartupEncoding
                filename = self.encodingServices.encode(filename, fn_enc, 'strict')
            except COMException, e:
                # happens on occasion, such as when windows system encoding is
                # cp936. see bug #32814. falling back to the regular path allows
                # most files to still work properly. The exception would
                # probably be if the file has characters in it from the system
                # encoding
                pass
        return filename

    def get_encodedURI(self):
        return self._encodeForFileSystem(self._uri)
    encodedURI = property(get_encodedURI)

    #attribute string URI; 
    def get_URI(self):
        return self._uri
    
    def set_URI(self, uri):
        # if the uri is quoted, we need to unquote first, we'll requote once
        # the uri is fully parsed
        if uri is None:
            self._clear()
        elif uri.find('://') == -1:
            self.set_path(uri)
        else:
            self._setFileNames(uri, doUnquote=True)
    URI = property(get_URI,set_URI)

    def get_displayPath(self):
        if self.scheme == 'file':
            return self.get_path() 
        else:
            return self.get_URI()
    
    #attribute string path; 
    def get_path(self):
        if self._path:
            return self._path
        if self._fileParsed[0] != 'file':
            if self._fileParsed[0] not in urlparse.uses_relative:
                self._path = self._uri
                return self._path
            self._path = self._fileParsed[2]
            return self._path
        parts = copy.copy(self._fileParsed)
        # fix the UNC file uri  this assums netloc in a file uri
        # is a machine name, thus this is a UNC
        if win32 and parts[0]=='file' and parts[1]:
            parts[2]='//'+parts[1]+parts[2]
            parts[1]=''
        path = os.path.normpath(parts[2])
        if len(path)==2 and path[1]==":" and self._fileParsed[2][-1] == "/":
            path += "/"
        if win32:
            path = path.replace('/','\\')
        self._path = path
        return path 

    def get_encodedPath(self):
        return self._encodeForFileSystem(self.get_path())
    encodedPath = property(get_encodedPath)

    # Warning, for absolute paths, this method actually resets the scheme
    # to be "file:///", ignoring what the original scheme settings were.
    def set_path(self, path):
        # turn paths into uri's, then set_URI
        if not path: return
        if path.find('://') >= 0:
            self.set_URI(path)
        else:
            # "sortaURI" is url unquoted already, ensure it's not re-unquoted
            # by passing "doUnquote=False" to _setFileNames(), bug 82660.
            if win32:
                path2 = path.replace('\\','/')
                if path2.startswith("//"):  # UNC path
                    sortaURI = "file:///" + path2
                elif path2.find(':') == 1:  # Absolute Windows path
                    sortaURI = "file:///" + path2
                else:
                    sortaURI = path2
            elif path[0] == '/':       # Absolute Unix path
                # Fix double-root paths, by collapsing them - bug 106180.
                path = os.path.normpath(path)
                if path.startswith("//"):
                    path = path[1:]
                sortaURI = "file://" + path
            elif path[1:2] == ':':  # Looks like an absolute Windows path
                # We allow Windows file paths on Unix, for things like mapped
                # URIs - bug 99683.
                sortaURI = "file:///" + path.replace('\\','/')
            else:
                sortaURI = path
            self._setFileNames(sortaURI, doUnquote=False)
    path = property(get_path,set_path)

    @property
    def prePath(self):
        return self.scheme + "://" + self.server

    #attribute string leafName; 
    def get_leafName(self):
        return self.baseName

    def set_leafName(self, leafName):
        self._path = os.path.join(self.dirName,leafName)
    leafName = property(get_leafName,set_leafName)

    #attribute string server; 
    def get_server(self):
        return self._fileParsed[1]

    def set_server(self, server):
        self._fileParsed[1] = server
        self._uri = self._buildURI(self._fileParsed)
    server = property(get_server,set_server)

    #readonly attribute string baseName; 
    def get_baseName(self):
        if not self._baseName:
            if self.path:
                self._baseName = os.path.basename(self.path)
        return self._baseName
    baseName = property(get_baseName)

    #readonly attribute string dirName; 
    def get_dirName(self):
        if not self._dirName:
            if self.path:
                self._dirName = os.path.dirname(self.path)
                if len(self._dirName)==2 and self._dirName[1]==":" and self.path[-1] == "/":
                    self._dirName += "/"
        return self._dirName
    dirName = property(get_dirName)

    #readonly attribute string scheme; 
    def get_scheme(self):
        return self._fileParsed[0]
    scheme = property(get_scheme)

    #readonly attribute string ext;
    def get_ext(self):
        if not self._ext:
            if self.path:
                self._ext = os.path.splitext(self.path)[1]
        return self._ext
    ext = property(get_ext)

    #readonly attribute string md5name; 
    def get_md5name(self):
        return md5(self.get_encodedURI()).hexdigest()
    md5name = property(get_md5name)

    def updateStats(self):
        return 0

    @property
    def hasChanged(self):
        import warnings
        warnings.warn("'hasChanged' is deprecated, use updateStats() instead.",
                      DeprecationWarning)
        return self.updateStats()

    @property
    def hasChangedNoStatUpdate(self):
        import warnings
        warnings.warn("'hasChangedNoStatUpdate' is deprecated.",
                      DeprecationWarning)
        return 0

class FileHandlerBase(object):

    isNetworkFile = False

    @LazyClassAttribute
    def lastErrorSvc(self):
        return components.classes["@activestate.com/koLastErrorService;1"].\
                    getService(components.interfaces.koILastErrorService)

    def __init__(self):
        self.clearstat()
        self._file = None
        self._path = None
        self._mode = 'rb'
        
        # lastAccessedTime is special, in that it can change
        # but we don't care if it does.  It's only used in ko
        # for display purposes.  If we keep this in the stat
        # cache for this file, it makes checking disk changes
        # more difficult, so instead, we store it seperately
        # see get_hasChanged below
        self.lastAccessedTime = 0
        

    def get_stats(self):
        return self._stats
    stats = property(get_stats)

    def clearstat(self):
        self._stats = {}

    def __getattr__(self,name):
        if name in self.stats:
            return self.stats[name]
        if self._file is None or not hasattr(self._file,name):
            raise AttributeError, name
        return getattr(self._file,name)

    def getStatusMap(self):
        status = self.stats.copy()
        keys = map(str, status.keys())
        values = map(str, status.values())
        return keys,values

    def read(self, nBytes):
        try:
            if nBytes >= 0xFFFFFFFF:
                # XXX - Hack around the fact that the read nBytes is
                #           marked as an unsigned int in the IDL, but some
                #           parts of the code use read(-1), which makes a
                #           really large unsigned int, causing exceptions!
                # http://bugs.activestate.com/show_bug.cgi?id=72912
                return self._file.read(-1)
            else:
                return self._file.read(nBytes)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise ServerException(nsError.NS_ERROR_FAILURE, ex.strerror)
        except COMException:
            # Last error should already be set in this case
            raise ServerException(nsError.NS_ERROR_FAILURE)

    def write(self, text):
        try:
            self._file.write(text)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise ServerException(nsError.NS_ERROR_FAILURE, ex.strerror)
        except COMException:
            # Last error should already be set in this case
            raise ServerException(nsError.NS_ERROR_FAILURE)

    def chmod(self, permissions):
        raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE)

class FileHandler(FileHandlerBase):
    isLocal = 1
    isRemoteFile = 0
    _networkFile = None

    def __init__(self,path):
        FileHandlerBase.__init__(self)
        uri = URIParser(path)
        if uri.scheme != 'file':
            raise URILibError("Invalid File Scheme: %s" % uri.scheme)
        self._path = uri.path
        self._decodedPath = uri.encodedPath

    def __del__(self):
        if self._file:
            self.close()

    _network_file_check_enabled = None

    @property
    def isNetworkFile(self):
        """Return true if this file resides on a network share.
        
        Note: For networked file, isLocal is *always* true."""
        if self._networkFile is None:

            # Check if the user allows networked files to be checked - bug 88521.
            network_check_enabled = FileHandler._network_file_check_enabled
            if network_check_enabled is None:
                globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                                    getService(components.interfaces.koIPrefService).prefs
                network_check_enabled = globalPrefs.getBooleanPref("checkNetworkDiskFile")
                FileHandler._network_file_check_enabled = network_check_enabled

            if not network_check_enabled and win32:
                # Determine if file is networked using the Win32 API. The string
                # must be a unicode object - otherwise the call will fail.
                # TODO: Does my path ever change? If so there needs to be an
                #       invalidate method so this call fires again.
                drive = unicode(splitdrive(self._path)[0])
                self._networkFile = Win32_GetDriveTypeW(drive) == WIN32_DRIVE_REMOTE
            else:
                self._networkFile = False
            # TODO: Check if the user has marked this location to be treated as
            #       a network file type (via user preferences).
            #if not self._networkFile:
            #    if self._path.startswith("/home/toddw/tmp"):
            #        self._networkFile = True
        return self._networkFile

    def close(self):
        if not self._file:
            raise URILibError("file not opened: '%s'" % self._path)
        try:
            try:
                self._file.close()
            except EnvironmentError, ex:
                self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
                raise ServerException(nsError.NS_ERROR_FAILURE, ex.strerror)
                return 0
        finally:
            self._file = None
        
    def open(self, mode):
        self._mode = mode
        if self._file is not None:
            raise URILibError("Cannot open a file again without closing it first!")
        if self._stats and self._stats['exists']==0:
            self._stats = None
        try:
            self._file = open(self._decodedPath, self._mode)
        except EnvironmentError, ex:
            try:
                # XXX bug 63027, try the original path
                self._file = open(self._path, self._mode)
            except EnvironmentError, ex:
                log.exception(ex)
                # python exceptions dont follow their own rules
                if ex.errno is None:
                    errno = 0
                else:
                    errno = ex.errno
                if ex.strerror is None:
                    strerror = repr(ex.args)
                else:
                    strerror = ex.strerror
                self.lastErrorSvc.setLastError(errno, strerror)
                raise ServerException(nsError.NS_ERROR_FAILURE, strerror)
                return 0
        return self._file is not None

    def __get_stats(self):
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                    'uid':'','gid':'','fileSize':0,
                    'lastModifiedTime':0,'createdTime':0,'isReadable':0,
                    'isWriteable':0,'isExecutable':0,'isReadOnly':0,
                    'isReadWrite':0,'exists':0,'isDirectory':0,
                    'isFile':0,'isSymlink':0,'isSpecial':0,'permissions':0,
                    'isHidden':0}
        try:
            try:
                lstats = os.lstat(self._decodedPath) # Don't follow symlinks
            except EnvironmentError, ex:
                try:
                    # XXX bug 63027, try the original path
                    lstats = os.lstat(self._path)
                except EnvironmentError, ex:
                    #log.exception(ex)
                    raise
            lmode = lstats[stat.ST_MODE]
            _stats['isSymlink'] = int(stat.S_ISLNK(lmode))
            if not _stats['isSymlink']:
                mode = lmode
                stats = lstats
            else:
                try:
                    stats = os.stat(self._decodedPath)
                except EnvironmentError, ex:
                    try:
                        # XXX bug 63027, try the original path
                        stats = os.stat(self._path)
                    except EnvironmentError, ex:
                        #log.exception(ex)
                        raise
                mode = stats[stat.ST_MODE]
            _stats['mode'] = mode
            _stats['ino'] = stats[stat.ST_INO]
            _stats['dev'] = stats[stat.ST_DEV]
            _stats['nlink'] = stats[stat.ST_NLINK]
            _stats['uid'] = stats[stat.ST_UID]
            _stats['gid'] = stats[stat.ST_GID]
            _stats['fileSize'] = stats[stat.ST_SIZE]
            # see comment on lastAccessedTime above
            self.lastAccessedTime = stats[stat.ST_ATIME]
            _stats['lastModifiedTime'] = stats[stat.ST_MTIME]
            _stats['createdTime'] = stats[stat.ST_CTIME]

            _stats['isReadable'] = int(mode & stat.S_IREAD == stat.S_IREAD)
            _stats['isWriteable'] = int(mode & stat.S_IWRITE == stat.S_IWRITE)
            _stats['isExecutable'] = int(mode & stat.S_IEXEC == stat.S_IEXEC)
            _stats['isDirectory'] = int(stat.S_ISDIR(mode))
            _stats['isFile'] = int(stat.S_ISREG(mode))
            _stats['isSpecial'] = int(stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode))
            _stats['permissions'] = stat.S_IMODE(mode)
            
            _stats['isReadOnly'] = int(_stats['isReadable'] and not _stats['isWriteable'])
            _stats['isReadWrite'] = int(_stats['isReadable'] and _stats['isWriteable'])
            _stats['exists']=1
            #print repr(_stats)
        except OSError,e:
            if e.errno != 2:
                raise
        return _stats

    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)

    def updateStats(self):
        if not self._stats:
            return 0
        tmpstats = self.__get_stats()
        if self._stats != tmpstats:
            self._stats = tmpstats
            return 1
        return 0

    @property
    def hasChangedNoStatUpdate(self):
        import warnings
        warnings.warn("'hasChangedNoStatUpdate' is deprecated.",
                      DeprecationWarning)
        if not self._stats or self._stats == self.__get_stats():
            return 0
        return 1

    def chmod(self, permissions):
        os.chmod(self._decodedPath, permissions)

class URIHandler(FileHandlerBase):
    isLocal = 0
    isRemoteFile = 0
    
    def __init__(self,path):
        FileHandlerBase.__init__(self)
        uri = URIParser(path)
        if uri.scheme == 'file':
            raise URILibError("Invalid File Scheme: %s" % uri.scheme)
        self._path = uri.URI
    
    def __del__(self):
        if self._file:
            self.close()

    def close(self):
        if not self._file:
            raise URILibError("file not opened: '%s'" % self._path)
        self._file.close()
        self._file = None

    def open(self, mode):
        import urllib2
        self._mode = mode
        if self._file is not None:
            raise URILibError("Cannot open a file again without closing it first!")
        if self._stats and self._stats['exists']==0:
            self._stats = None
        httpService = components.classes["@mozilla.org/network/protocol;1?name=http"].\
                              getService(components.interfaces.nsIHttpProtocolHandler)
        req = urllib2.Request(self._path, None, {'User-agent': httpService.userAgent})
        self._file = urllib2.urlopen(req)
        return self._file is not None

    def __get_stats(self):
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                    'uid':'','gid':'','fileSize':0,
                    'lastModifiedTime':0,'createdTime':0,'isReadable':1,
                    'isWriteable':0,'isExecutable':0,'isReadOnly':1,
                    'isReadWrite':0,'exists':1,'isDirectory':0,
                    'isFile':0,'isSymlink':0,'isSpecial':0,'permissions':0,
                    'isHidden':0}
        # XXX need to implement this stuff for ftp/http
        return _stats
    
    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)
    
class QuickstartHandler(FileHandlerBase):
    #XXX Shane, should this inherit from FileHandlerBase, because no chrome
    #    file should use any of SCC status stuff?
        
    isLocal = 0
    isRemoteFile = 0
            
    @LazyClassAttribute
    def displayPath(self):
        """A HACK to override the quickstart view's document.file.displayPath
        """
        bundle = components.classes["@mozilla.org/intl/stringbundle;1"].\
                 getService(components.interfaces.nsIStringBundleService).\
                 createBundle("chrome://komodo/locale/komodo.properties")
        return bundle.GetStringFromName("newTab")
        
    def __init__(self, path):
        FileHandlerBase.__init__(self)
        if path != "chrome://komodo/content/quickstart.xml#view-quickstart":
            raise URILibError("Invalid Quick Start path: %s" % path)
            
    def __del__(self):
        pass
        
    def close(self):
        pass
                
    def open(self, mode):
        return 0
        
    def __get_stats(self):
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                  'uid':'','gid':'','fileSize':0,
                  'lastModifiedTime':0,'createdTime':0,'isReadable':1,
                  'isWriteable':0,'isExecutable':0,'isReadOnly':1,
                  'isReadWrite':0,'exists':1,'isDirectory':0,
                  'isFile':1,'isSymlink':0,'isSpecial':0,'permissions':0,
                  'isHidden':0}
        # XXX need to implement this stuff from nsIFile stuff
        return _stats
            
    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)


class xpURIHandler(FileHandlerBase):
    isLocal = 0
    isRemoteFile = 0
    
    def __init__(self,path):
        FileHandlerBase.__init__(self)
        uri = URIParser(path)
        self._path = path
    
    def open(self, mode):
        if "r" not in mode:
            raise ValueError, "only 'r' mode supported'"
        self._mode = mode

        io_service = components.classes["@mozilla.org/network/io-service;1"] \
                        .getService(components.interfaces.nsIIOService)
        url_ob = io_service.newURI(self._path, None, None)
        # Mozilla asserts and starts saying "NULL POINTER" if this is wrong!
        if not url_ob.scheme:
            raise ValueError, ("The URI '%s' is invalid (no scheme)" 
                                  % (url_ob.spec,))

        if self._stats and self._stats['exists']==0:
            self._stats = None

        try:
            channel = io_service.newChannelFromURI(url_ob)
            self._file = channel.open()
        except Exception, e:
            # Mozilla could not open the file, so it either does not exist
            # or some other error which we unfortunately do not get good info
            # on from mozilla.  One example is a dbgp uri being restored
            # on startup.  We pass here and let the file be non-existent
            self._file = None
            if self._stats:
                self._stats['exists'] = 0
                self._stats['isReadable'] = 0
                self._stats['isReadOnly'] = 0
        return self._file is not None

    def read(self, nBytes):
        bufptr = FileHandlerBase.read(self, nBytes)
        # A bufptr is Mozilla file buffer (array) - we want the contents.
        return ''.join(bufptr)

    def __get_stats(self):
        # exists must be true for an open file attempt to be made
        # we set isSpecial to true here because this class is only used for
        # mozilla based uri's, such as the dbgp:// implementation or chrome
        # uri's.  We do not want these uri's restored when Komodo restarts.
        # this way we can genericaly avoid trying to restore these.
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                    'uid':'','gid':'','fileSize':0,
                    'lastModifiedTime':0,'createdTime':0,'isReadable': 1,
                    'isWriteable':0,'isExecutable':0,'isReadOnly': 1,
                    'isReadWrite':0,'exists': 1,'isDirectory':0,
                    'isFile':0,'isSymlink':0,'isSpecial':1,'permissions':0,
                    'isHidden':0}
        # XXX need to implement this stuff for ftp/http
        return _stats

    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)

class RemoteURIHandler(FileHandlerBase):
    isLocal = 0
    isRemoteFile = 1
    
    @LazyClassAttribute
    def remoteFileSvc(self):
        return components.classes["@activestate.com/koRemoteConnectionService;1"].\
                    getService(components.interfaces.koIRemoteConnectionService)

    def __init__(self,path):
        import re
        FileHandlerBase.__init__(self)
        self._fulluri = path
        self._uri = URIParser(path)
        if self._uri.scheme not in RemoteURISchemeTypes:
            raise URILibError("Invalid File Scheme: %s" % self._uri.scheme)
        self._mode = 'r'
        # Keep the stats hanging around, we don't need to update everytime the 
        # file does an open, we check before we save to be safe (in koDocument).
        self._stats = None

    def close(self):
        pass

    def _getConnection(self):
        return self.remoteFileSvc.getConnectionUsingUri(self._fulluri)
        
    def _getRemotePathInfo(self, refresh=0):
        # Check that the file exists
        conn = self._getConnection()
        return conn.list(self._uri.path, refresh)

    def open(self, mode):
        # Note: We don't actually hold open a remote file object, we just assume
        #       it will be possible - read|write will fail if it's not possible.
        self._mode = mode
        return True

    def read(self, nBytes):
        conn = self._getConnection()
        # XXX: Doesn't support nBytes - reads in everything.
        return conn.readFile(self._uri.path)

    def write(self, text):
        conn = self._getConnection()
        conn.writeFile(self._uri.path, text)
        # We need to update the stats now, as the timestamps will have changed
        self._stats = self.__get_stats(refresh=1)

    def __get_stats(self, refresh=0, rfInfo=None):
        # XXX need to implement this stuff for ftp/http
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                    'uid':'','gid':'','fileSize':0,
                    'lastModifiedTime':0,'createdTime':0,'isReadable':1,
                    'isWriteable':1,'isExecutable':0,'isReadOnly':0,
                    'isReadWrite':0,'exists':1,'isDirectory':0,
                    'isFile':0,'isSymlink':0,'isSpecial':0,'permissions':0,
                    'isHidden':0}
        if refresh:
            rfInfo = self._getRemotePathInfo(refresh=refresh)
        if rfInfo:
            _stats['fileSize']          = rfInfo.getFileSize()
            # Use same values for Modified, Accessed and Created times
            self.lastAccessedTime       = rfInfo.getModifiedTime()
            _stats['lastModifiedTime']  = self.lastAccessedTime
            _stats['createdTime']       = self.lastAccessedTime
            _stats['isReadable']        = rfInfo.isReadable()
            _stats['isWriteable']       = rfInfo.isWriteable()
            _stats['isExecutable']      = rfInfo.isExecutable()
            _stats['isReadOnly']        = _stats['isReadable'] and not _stats['isWriteable']
            _stats['isReadWrite']       = _stats['isReadable'] and _stats['isWriteable']
            _stats['exists']            = 1
            _stats['isDirectory']       = rfInfo.isDirectory()
            _stats['isFile']            = rfInfo.isFile()
            _stats['isSymlink']         = rfInfo.isSymlink()
            _stats['isSpecial']         = 0
            _stats['permissions']       = stat.S_IMODE(rfInfo.mode)
            _stats['isHidden']          = rfInfo.isHidden()
        return _stats
    
    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)

    def updateStats(self):
        if not self._stats:
            return 0
        tmpstats = self.__get_stats(refresh=1)
        if self._stats != tmpstats:
            self._stats = tmpstats
            return 1
        return 0

    @property
    def hasChangedNoStatUpdate(self):
        import warnings
        warnings.warn("'hasChangedNoStatUpdate' is deprecated.",
                      DeprecationWarning)
        if not self._stats or self._stats == self.__get_stats(refresh=1):
            return 0
        return 1

    def chmod(self, permissions):
        connection = self.remoteFileSvc.getConnectionUsingUri(self._fulluri)
        connection.chmod(self._uri.path, permissions)
        self._stats['permissions'] = permissions

class projectURIHandler(FileHandlerBase):
    isLocal = 0
    isRemoteFile = 0

    @LazyClassAttribute
    def partSvc(self):
        return components.classes["@activestate.com/koPartService;1"].\
                    getService(components.interfaces.koIPartService)

    def __init__(self,URI):
        FileHandlerBase.__init__(self)
        self._uri = URI
        self._path = URI.path
        self.part = None
    
    def __del__(self):
        if self._file:
            self.close()

    def close(self):
        if not self._file:
            raise URILibError("file not opened: '%s'" % self._uri.URI)
        try:
            if self.part and self._mode and self._mode[0] == 'w':
                val = self._file.getvalue()
                if val != self.part.value:
                    self.part.value = val
                    if not self.part.project:
                        raise URILibError("unable to save macro: '%s'" % self._uri.URI)
                    self.part.project.isDirty = True
                    # If the part resides in one of the toolboxes, then
                    # automatically save the toolbox as well - bug 82878.
                    if self.part.project in (self.partSvc.toolbox,
                                             self.partSvc.sharedToolbox):
                        self.part.project.save()
        finally:
            try:
                self._file.close()
            except Exception, e:
                log.exception(e)
            self._file = None
        
    def open(self, mode):
        import StringIO
        self._mode = mode
        if self._file is not None:
            raise URILibError("Cannot open a file again without closing it first!")
        if self._stats and self._stats['exists']==0:
            self._stats = None
        try:
            # get the part from the part service, get the value of the part,
            # and insert it into a stringio object
            if not self.part:
                self.part = self.partSvc.getPartById(self._uri.server)
                self._stats = None
            if mode and mode[0] == 'r':
                # bug89131: work with read method, which returns octets
                # file contents should always be utf-8
                self._file = StringIO.StringIO(self.part.value.encode('utf-8'))
            else:
                self._file = StringIO.StringIO()
        except Exception, e:
            # Mozilla could not open the file, so it either does not exist
            # or some other error which we unfortunately do not get good info
            # on from mozilla.  One example is a dbgp uri being restored
            # on startup.  We pass here and let the file be non-existent
            self._file = None
            if self._stats:
                self._stats['exists'] = 0
                self._stats['isReadable'] = 0
                self._stats['isReadOnly'] = 0
        return self._file is not None

    #def read(self, nBytes):
    #    # bug89131: read returns (length, octets), but it mishandles
    #    # returning a string of Unicode characters: it returns
    #    # (# of Unicode characters, sequence of utf-8-encoded octets)
    #    return FileHandlerBase.read(self, nBytes).encode('utf-8')

    def __get_stats(self):
        # exists must be true for an open file attempt to be made
        # we set isSpecial to true here because this class is only used for
        # mozilla based uri's, such as the dbgp:// implementation or chrome
        # uri's.  We do not want these uri's restored when Komodo restarts.
        # this way we can genericaly avoid trying to restore these.
        _stats = {'mode':'','ino':'','dev':'','nlink':'',
                    'uid':'','gid':'','fileSize':0,
                    'lastModifiedTime':0,'createdTime':0,'isReadable': 1,
                    'isWriteable':1,'isExecutable':0,'isReadOnly': 0,
                    'isReadWrite':1,'exists': 1,'isDirectory':0,
                    'isFile':0,'isSymlink':0,'isSpecial':1,'permissions':0,
                    'isHidden':0}
        # XXX need to implement this stuff for ftp/http
        if self.part:
            _stats['fileSize'] = len(self.part.value)
        return _stats
    
    def get_stats(self):
        if not self._stats:
            self._stats = self.__get_stats()
        return self._stats
    stats = property(get_stats)

class projectURI2_Handler(projectURIHandler):

    @LazyClassAttribute
    def toolSvc(self):
        return UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"].\
                               getService(components.interfaces.koIToolbox2ToolManager))

    def __del__(self):
        if self._file:
            self.close()

    def getMacroTool(self):
        # Should get snippets as well...
        return self.toolSvc.getToolById(self._uri.server)

    def close(self):
        if not self._file:
            raise URILibError("file not opened: '%s'" % self._uri.URI)
        try:
            if self.part and self._mode and self._mode[0] == 'w':
                val = self._file.getvalue()
                origVal = self.part.value
                if val != origVal:
                    tool = self.getMacroTool()
                    tool.value = val
                    self.part.value = val
                    try:
                        tool.save() # updates filesystem tool & DB
                    except:
                        tool.value = origVal
                        raise
        finally:
            try:
                self._file.close()
            except Exception, e:
                log.exception(e)
            self._file = None
        
    def open(self, mode):
        import StringIO
        self._mode = mode
        if self._file is not None:
            raise URILibError("Cannot open a file again without closing it first!")
        if self._stats and self._stats['exists']==0:
            self._stats = None
        try:
            # get the part from the part service, get the value of the part,
            # and insert it into a stringio object
            if mode and mode[0] == 'r':
                try:
                    self.part = self.getMacroTool()
                    self._stats = None
                    text = self.part.value
                    if self._uri.scheme == "snippet2":
                        try:
                            text = self._trimPositionInfo(text)
                        except:
                            import traceback
                            traceback.print_exc()
                except AttributeError:
                    log.exception("can't get content off %s", self.part)
                    raise
                # bug89131: work with read method, which returns octets
                # file contents should always be utf-8
                self._file = StringIO.StringIO(text.encode('utf-8'))
            else:
                self._file = StringIO.StringIO()
        except Exception:
            # Mozilla could not open the file, so it either does not exist
            # or some other error which we unfortunately do not get good info
            # on from mozilla.  One example is a dbgp uri being restored
            # on startup.  We pass here and let the file be non-existent
            log.exception("Problems in projectURI2_Handler.open")
            self._file = None
            if self._stats:
                self._stats['exists'] = 0
                self._stats['isReadable'] = 0
                self._stats['isReadOnly'] = 0
        return self._file is not None
    
    def write(self, text):
        if self._uri.scheme == "snippet2":
            # Bogus, but we don't have access to the view selection here.
            text += "!@#_currentPos!@#_anchor"
        # super
        projectURIHandler.write(self, text)

    def _trimPositionInfo(self, text):
        return text.replace("!@#_currentPos", "").replace("!@#_anchor", "")

if __name__=="__main__":
    # simple quick tests, unit tests are in test_URIlib.py
    URI = URIParser()
    #URI.path = r'c:\test\path\to\somefile.txt'
    #URI.path = 'c:\\'
    #URI.URI = "file://netshare/apps/Komodo/Naming Rules for Tarballs.txt"
    #URI.URI = 'ftp://somesite.com/web/info.php'
    URI.URI = r'ftp://somesite.com/web/info.php'
    #URI.URI = r'sftp://test:tesuser@somesite.com:22/web/info.php'
    #URI.URI = r'sftp://test:tesuser@somesite.com:22/web/utils/info.php'
    URI.dump()

    URI.URI = r'ftp://server_alias/tests'
    #URI.URI = r'sftp://server_alias/tests'
    URI.dump()
    handler = RemoteURIHandler(URI.URI)
    #print handler._connection
    #except Exception, ex:
    #    print "*** Exception ***"
    #    print ex
