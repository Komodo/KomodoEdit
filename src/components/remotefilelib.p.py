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

# An implementation of remote file objects
#
# Contributors:
# * Shane Caraveo
# * Todd Whiteman

import os
import sys
import time
import stat
import threading
import logging
import socket   # For catching underlying socket errors
import select

from xpcom import components, ServerException, nsError

log = logging.getLogger('remotefilelib.p.py')
#log.setLevel(logging.DEBUG)

# Known protocols and their default ports
koRFProtocolDefaultPort = {
    'ftp': 21,
    'ftps': 21,
    'sftp': 22,
    'scp': 22,
}


def addslash(path):
    if len(path) < 1: return "/"
    if path[len(path)-1] != "/": path += "/"
    return path

# This is quite ugly. You will not be able to open a filename that contains
# a backslash in the name (in unix you can have this type of filename).
def normalizePath(path):
    path = os.path.normpath(path) #normalize the path
    if sys.platform == "win32":
        path = path.replace("\\","/") # os.normpath changes slashes on win
    if path[0] != "/" and path != '~':
        if path[:2] != '~/':
            path = "/"+path
    elif path[:2] == '/~':
        path = path[1:]
    return path


class koRFConnection:
    def __init__(self):
        self._connection = None
        self.alias = ""
        self.protocol = ""
        self.server = ""
        self.port = 0
        self.username = ""
        self.password = ""
        self.passive = True
        self.privatekey = ""
        self.homedirectory = None
        self._lasterror = ""
        self._last_verified_time = 0
        self._cache_key = None  # Used for caching files
        self._directoryCache = {}
        self._lock = threading.RLock()
        # can only read/write one file at a time
        self._globalPrefs = \
            components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                            .getService(components.interfaces.koILastErrorService)
        self._rfConnectionService = components.classes["@activestate.com/koRemoteConnectionService;1"]\
                            .getService(components.interfaces.koIRemoteConnectionService)
        self._encodingSvc = components.classes['@activestate.com/koEncodingServices;1'].\
                                getService(components.interfaces.koIEncodingServices)
        # How long the socket waits until it times out when trying to connect
        # or read/recv. The value is in seconds.
        self._socket_timeout = self._globalPrefs.getLongPref('remotefiles_defaultConnectionTimeout')


    # Note: The do_* functions must be implemented by the actual
    # connection that is handling this protocol type. Thus these local
    # do_* functions should never get called unless the protocol does
    # not implement the function
    def do_authenticateWithPassword(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_authenticateWithPrivateKey(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_authenticateWithAgent(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_openSocket(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_verifyConnected(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_getPathInfo(self, path): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_getDirectoryList(self, path, dir_rfinfo): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_rename(self, oldName, newName): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_removeFile(self, name): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_changeDirectory(self, path): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_currentDirectory(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_getHomeDirectory(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_getParentPath(self, path): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_removeDirectory(self, name): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_createDirectory(self, name, permissions): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_createFile(self, name, permissions): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_close(self): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_chmod(self, filepath, permissions): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_readFile(self, filename): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def do_writeFile(self, filename, data): raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    #
    # Internal methods
    #
    #
    def _setLastError(self, error_message):
        # Turn wierd python messages into human readable format
        if sys.platform == "win32":
            if error_message == "getaddrinfo failed":
                error_message = "Unknown hostname: '%s'" % (self.server)
        elif sys.platform == "darwin":
            if error_message == "No address associated with nodename":
                error_message = "Unknown hostname: '%s'" % (self.server)
        elif sys.platform.startswith("linux"):
            if error_message == "Name or service not known":
                error_message = "Unknown hostname: '%s'" % (self.server)

        self._lasterror = error_message
        self.lastErrorSvc.setLastError(0, self._lasterror)

    def _raiseServerException(self, error_message, log_message=None):
        self._setLastError(error_message)
        if log_message:
            self.log.error("%s %s ERROR: %s", self.protocol.upper(), log_message, self._lasterror)
        else:
            from_where = ''
            try:
                i = 1
                # Work out the function name the error occured in
                while not from_where:
                    func_name = sys._getframe(i).f_code.co_name
                    #if func_name and func_name[0] not in "_":
                    #    from_where = func_name
                    if func_name not in ('_raiseTimeoutException',
                                         '_raiseWithException'):
                        from_where = func_name
                    i += 1
            except ValueError:
                pass
            self.log.error("%s %s ERROR: %s", self.protocol.upper(), from_where, self._lasterror)
        raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

    def _raiseTimeoutException(self):
        # Clear this connection from the connection cache.
        self._rfConnectionService.removeConnectionFromCache(self)
        self._raiseServerException("Connection timed out")

    def _raiseWithException(self, e):
        if isinstance(e, socket.timeout):
            self._raiseTimeoutException()
        else:
            if len(e.args) > 0:
                error = e.args[-1]
            else:
                error = str(e)
            self._raiseServerException(error)

    def _removeFromCache(self, path, removeChildNodes=0):
        self._rfConnectionService.removeCachedRFInfo(self._cache_key, path, removeChildNodes)

    @components.ProxyToMainThread
    def promptForUsernameAndPassword(self, path):
        dialogproxy = components.classes['@activestate.com/asDialogProxy;1'].\
                    getService(components.interfaces.asIDialogProxy)
        title = "Authentication"
        if path:
            if len(path) > 40:
                path = "..." + path[-40:]
            title += ", opening file: "+path
        if self._lasterror:
            title += ". Failed, try again..."
        prompt = "Please enter the username and password"
        # Change to new style authentication dialog
        authinfo = dialogproxy.authenticate(title, self.server, prompt,
                                            self.username, 1, 0)
        if authinfo:
            self.username, self.password = authinfo.split(":", 1)
            self.log.debug("authinfo: got back '%s:%s'", self.username,
                           '*' * len(self.password))
        else:
            # Do not log as error, this was intended by the user
            self._setLastError("Login cancelled by user.")
            self.log.info("%s: %s", self.protocol.upper(), self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

    # Shared code for FTP and SCP
    # XXX - This could/should also be a common function for sftp
    def _fixPath(self, path):
        """Hack because:
        1 - ftp/scp does not work well with tilde directory names
        2 - need to remove any trailing forward slashes
        """
        if not path:
            return "/"
        else:
            newPath = None
            if path == '~' or path[:2] == '~/':
                newPath = path[1:]
            elif path[:2] == '/~':
                newPath = path[2:]
            if newPath is not None:
                # Remove any trailing forward slash
                if len(newPath) > 1 and newPath[-1] == "/":
                    newPath = newPath[:-1]
                # Fix up the directory forward slashes
                if newPath[:1] == '/':
                    newPath = newPath[1:]
                if not newPath:
                    newPath = self.do_getHomeDirectory()
                else:
                    newPath = addslash(self.do_getHomeDirectory()) + newPath
                self.log.debug("_fixPath: %s -> %s", path, newPath)
                return newPath
            elif len(path) > 1 and path[-1] == "/":
                # Remove any trailing forward slash
                newPath = path[:-1]
                self.log.debug("_fixPath: %s -> %s", path, newPath)
                return newPath
        return path

    # Shared code for FTP and SCP
    basicModeForBaseDir = stat.S_IFDIR | stat.S_IREAD | stat.S_IWRITE
    def _createBaseDirectory(self, dirname):
        rf = components.classes['@activestate.com/koRemoteFileInfo;1'].\
                    createInstance(components.interfaces.koIRemoteFileInfo)
        rf.initFromStats(dirname, dirname, '0', '', '', self.basicModeForBaseDir, 0)
        return rf

    # Shared code for FTP and SCP
    def _createRFInfoFromListing(self, dirname, fileinfo):
        rf = components.classes['@activestate.com/koRemoteFileInfo;1'].\
                    createInstance(components.interfaces.koIRemoteFileInfo)
        # XXX - We can translate the encoding, but how do we send it back once
        #       it's been traslated? Possibly remembering through the rf object?
        try:
            result = rf.initFromDirectoryListing(dirname, fileinfo)
        except UnicodeDecodeError:
            # Try encoding it with komodo's unicode encoding service
            try:
                fileinfo, rf.encoding, bom = self._encodingSvc.getUnicodeEncodedString(fileinfo)
                self.log.debug("Had to decode filelisting(%s): %s" % (rf.encoding, fileinfo))
                result = rf.initFromDirectoryListing(dirname, fileinfo)
            except Exception, e:
                # No go, we assume it was not found in this string
                self.log.debug("Error '%s' decoding filelisting: '%s'" % (e, fileinfo))
                return None
        if not result:
            del rf
            return None
        return rf

    # Shared code for FTP and SCP
    def _createRFInfo(self, path, fileinfo=None):
        if fileinfo:
            rf_info = self._createRFInfoFromListing(path, fileinfo)
        else:
            rf_info = self._createRFInfoFromPath(path)

        if rf_info:
            rf_info = self._followSymlink(rf_info)
        return rf_info

    # Shared code for FTP and SCP
    def _followSymlink(self, rfinfo):
        loop_count = 0
        # Keep following symlinks until we get the real destination
        while rfinfo.isSymlink():
            loop_count += 1
            if loop_count > 20:
                self.log.error("Can not follow more than 20 symlinks deep: '%s'" % (rfinfo.getFilepath()))
                return None
            # Find out the link target and populate the target info
            # into this file
            link_target = rfinfo.getLinkTarget()
            self.log.debug("_followSymlink: Symlink info for '%s' -> '%s'", rfinfo.getFilepath(), link_target)
            ## We now know where the link goes, but not what the link is
            ## find out what it is
            info = []
            rf_link = self._createRFInfoFromPath(link_target)
            if not rf_link:
                return None
            rfinfo.initFromStats(rfinfo.getDirname(), rfinfo.getFilename(), rf_link.size,
                             rf_link.uid, rf_link.gid, rf_link.mode, 
                             rf_link.mtime)
            if rfinfo.isSymlink():
                rfinfo.setLinkTarget(rf_link.getLinkTarget())
            else:
                rfinfo.setLinkTarget(rf_link.getFilepath())
            self.log.debug("_followSymlink: File now: %s", rfinfo)
        rfinfo.originalIsSymlink = True
        return rfinfo

    # As we are getting filenames from the remote system, the encoding could
    # be anything. We don't know what it is until we do a list() on the path
    # and work out the encoding details. This function ensures the filepath
    # passed between Komodo and the remote server is always in the remote
    # server's encoding.
    # http://bugs.activestate.com/show_bug.cgi?id=47738
    def _getEncodedFilepath(self, filepath):
        rf_info = self.list(filepath, False)
        # We get rf_info to convert the filename back to a local encoding
        self.log.debug("_getEncodedFilepath:: filepath: %r, rfinfo: %r",
                       filepath, rf_info)
        if not rf_info:
            # Could be because it's a decoded path that has not been listed yet
            # I.e. if Komodo has just started and reopening files
            # Try the parent then, ideally we should keep working up the parent
            # chain until we find a match and then work down from there, but
            # we'll try just the immediate parent lookup for now.
            parent_path = self.do_getParentPath(filepath)
            self.log.debug("_getEncodedFilepath:: No rfinfo, trying parent rf_info: %r",
                           parent_path, )
            parentrf_info = self.list(parent_path, True)
            if parentrf_info:
                rf_info = self.list(filepath, False)
                self.log.debug("_getEncodedFilepath:: Found parent rfinfo, trying filepath again: %r",
                               rf_info, )
        if rf_info:
            encoding = rf_info.getEncoding()
            if encoding:
                filepath = filepath.encode(encoding)
        return filepath

    # Open socket functionality taken from connect() method in ftplib.py
    def _get_and_open_socket(self):
        s = None
        msg = "getaddrinfo returns an empty list"
        # Try unspecified protocol type, then try falling back in IPv4 (AF_INET)
        # http://bugs.activestate.com/show_bug.cgi?id=76602
        for af_type in (socket.AF_UNSPEC, socket.AF_INET):
            try:
                address_info = socket.getaddrinfo(self.server, self.port, af_type, socket.SOCK_STREAM)
            except socket.error, msg:
                self.log.warn("socket.getaddrinfo raised exception: %r", msg)
                continue
            for res in address_info:
                af, socktype, proto, canonname, sa = res
                try:
                    s = socket.socket(af, socktype, proto)
                    s.settimeout(self._socket_timeout)
                    s.connect(sa)
                except socket.error, msg:
                    if s:
                        s.close()
                    s = None
                    continue
                break
            if s is not None:
                break
        if not s:
            raise socket.error, msg
        return s

    #
    # XPcom methods, available through koIRemoteConnection interface
    #
    # Note: path is only used for displaying on the username/password dialog
    def open(self, server, port, username, password, path, passive=True,
             privatekey=""):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.server = server
            self.username = username
            self.password = password
            if port > 0: self.port = port
            else: self.port = koRFProtocolDefaultPort[self.protocol]
            self.passive = passive
            self.privatekey = privatekey
    
            self.authAttempt = 0
            while self.authAttempt < 3:
                self.authAttempt += 1
                self.log.debug("open: s:%s p:%s u:%s", self.server, self.port,self.username)

                if not self.username or self.authAttempt > 1:
                    # Need at least a username, or the last login attempt
                    # failed, prompt for username and password now.
                    _username = self.username
                    self.promptForUsernameAndPassword(path)
                    if self.authAttempt > 1 and _username != self.username and \
                       self.protocol in ("sftp", "scp"):
                        # Need to reconnect, see:
                        # http://bugs.activestate.com/show_bug.cgi?id=68773
                        self.do_close()
                        self.log.debug("open: username changed, reopening the "
                                       "connection")
                        self.do_openSocket()

                if self.authAttempt == 1:
                    # Make the inital socket connection.
                    self.do_openSocket()

                if self.do_authenticateWithAgent():
                    self.log.debug("Agent authentication successful.")
                    break

                # Sometimes the above agent authentication will close the SSH
                # transport, so if that happended we re-open it now.
                if self.protocol in ("sftp", "scp") and not self._connection.active:
                    self.do_close()
                    self.log.debug("open: connection closed by agent auth, reopening it")
                    self.do_openSocket()

                # We only try the privatekey once, as it will do it's own
                # re-prompting if necessary.
                if privatekey and self.authAttempt == 1:
                    if self.do_authenticateWithPrivateKey():
                        self.log.debug("Private key authentication successful.")
                        break
                if self.do_authenticateWithPassword():
                    self.log.debug("Password authentication successful.")
                    break
                # else we had an invalid username/password, let's go round again
            else:
                self._raiseServerException("Authentication failed.")

            self.log.info("%s connection opened on %s:%s for user %s", self.protocol,self.server,self.port,self.username)
            # Set the caching key now we have the connection open
            self._cache_key = "%s:%s" % (self.server, self.username)
        finally:
            self._lock.release()
        return 1

    # Note: We add all files and folders that are found to the cache. The
    # sub-directories that get added will not initially have contents, to find
    # the contents, a check is done when the directory gets selected.
    # We return a list of everything found in the directory, including sub
    # directories.
    def list(self, path, refresh):
        self.log.debug("list: (refresh:%r) path: '%s'", refresh, path)

        if not path:
            path = '/'
            self.log.debug("list: No path given, using: '/'")
        #elif path[:2] in ('/~', '/.'):
        elif path[:2] == '/~':
            # Fix up path due to the URI having a leading slash
            path = path[1:]
            self.log.debug("list: Removed leading slash from path: '%s'", path)
        elif len(path) > 1 and path[-1] == '/':
            # Fix up path due to the URI having a trailing slash
            path = path[:-1]
            self.log.debug("list: Removed trailing slash from path: '%s'", path)

        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self._lasterror = ""
            updateCache = False
            # Return the cached copy if not asking for a refresh
            cached_info = self._rfConnectionService.getCachedRFInfo(self._cache_key, path)
    
            # If told to refresh or the file path is not known (not cached)
            if refresh or not cached_info:
                updateCache = True
                if not cached_info:
                    self.log.debug("list: path is not cached, getting info")
                self.do_verifyConnected()
                cached_info = self.do_getPathInfo(path)
                if not cached_info:
                    return None
                self.log.debug("list: Returned new rf_info for: '%s'", path)
            #else:
            #    self.log.debug("Using cached rf_info for: '%s'",path)
    
            if refresh and cached_info.isDirectory():
                updateCache = True
                self.log.debug("list: Creating new listing for directory: '%s'", path)
                # we have a directory that has needs refresh
                # or has not had a directory listing yet
                dirlist = self.do_getDirectoryList(path, cached_info)
                cached_info.setChildren(dirlist)
    
            if updateCache:
                # cache the info (no need to do this if nothing has been updated)
                self._rfConnectionService.setCachedRFInfo(self._cache_key, path, cached_info)
            return cached_info
        finally:
            self._lock.release()

    def rename(self, oldName, newName):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            encoded_oldName = self._getEncodedFilepath(oldName)
            self.log.debug("rename %s to %s" ,encoded_oldName, newName)
            result = self.do_rename(encoded_oldName, newName)
            # Remove decoded oldName, not the encoded one
            self._removeFromCache(oldName, removeChildNodes=1)
            return result
        finally:
            self._lock.release()

    def removeFile(self, name):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            encoded_name = self._getEncodedFilepath(name)
            self.log.debug("remove file %s",encoded_name)
            result = self.do_removeFile(encoded_name)
            # Remove decoded name, not the encoded one
            self._removeFromCache(name, removeChildNodes=0)
            return result
        finally:
            self._lock.release()

    def changeDirectory(self, path):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            path = self._getEncodedFilepath(path)
            self.log.debug("changeDirectory cwd %s",path)
            return self.do_changeDirectory(path)
        finally:
            self._lock.release()

    def currentDirectory(self):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            return self.do_currentDirectory()
        finally:
            self._lock.release()

    def getHomeDirectory(self):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            """Return the cached information if we have it"""
            if self.homedirectory is None:
                self.do_verifyConnected()
                self.homedirectory = self.do_getHomeDirectory()
            return self.homedirectory
        finally:
            self._lock.release()

    def getParentPath(self, path):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            path = self._getEncodedFilepath(path)
            return self.do_getParentPath(path)
        finally:
            self._lock.release()

    def removeDirectory(self, name):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            encoded_name = self._getEncodedFilepath(name)
            self.log.debug("remove directory %s",encoded_name)
            result = self.do_removeDirectory(encoded_name)
            # Remove decoded oldName, not the encoded one
            self._removeFromCache(name, removeChildNodes=1)
            return result
        finally:
            self._lock.release()

    def _removeDirectoryRecursively(self, path):
        directory_rfinfo = self.list(path, 1)
        if directory_rfinfo is None:
            log.debug("removeRecursively: Path does not exist: %r!", path)
            return
        dirEntries = directory_rfinfo.getChildren()
        # Note: dirEntries is a list of koIRemoteFileInfo objects
        if dirEntries:
            log.debug("removeRecursively: Removing sub contents (%d entries)",
                      len(dirEntries))
            for file_rfinfo in dirEntries:
                if file_rfinfo.isDirectory():
                    self._removeDirectoryRecursively(file_rfinfo.getFilepath())
                else:
                    self.removeFile(file_rfinfo.getFilepath())
        self.removeDirectory(path)

    def removeDirectoryRecursively(self, path):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            encoded_path = self._getEncodedFilepath(path)
            self.log.debug("remove directory recursively %s", path)
            self._removeDirectoryRecursively(encoded_path)
        finally:
            self._lock.release()

    def createDirectory(self, name, permissions):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            self.log.debug("createDirectory %s, %r" ,name, permissions)
            return self.do_createDirectory(name, permissions)
        finally:
            self._lock.release()

    def createDirectories(self, path, permissions):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            self.log.debug("createDirectories %s, %r", path, permissions)
            orig_path = path
            make_dir_paths = []
            last_path = None
            rfinfo = self.list(path)
            while rfinfo is None:
                if not path or path == last_path:
                    self._raiseServerException("Could not find any parent directory for %r", orig_path)
                make_dir_paths.append(path)
                path = self.do_getParentPath(path)
                rfinfo = self.list(path)
                last_path = path
            for path in make_dir_paths:
                self.do_createDirectory(name, permissions)
        finally:
            self._lock.release()

    def createFile(self, name, permissions):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            self.log.debug("createFile %s, %r" ,name, permissions)
            return self.do_createFile(name, permissions)
        finally:
            self._lock.release()

    def close(self):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.log.debug("closing connection")
            return self.do_close()
        finally:
            self._lock.release()

    def chmod(self, filepath, permissions):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.log.debug("chmod %s, %r", filepath, permissions)
            return self.do_chmod(filepath, permissions)
        finally:
            self._lock.release()

    def readFile(self, filename):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            filename = self._getEncodedFilepath(filename)
            self.log.debug("reading file: %s", filename)
            return self.do_readFile(filename)
        finally:
            self._lock.release()

    def writeFile(self, filename, data):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self.do_verifyConnected()
            filename = self._getEncodedFilepath(filename)
            self.log.debug("writing file: %s (%d chars)", filename, len(data))
            return self.do_writeFile(filename, data)
        finally:
            self._lock.release()

    def invalidatePath(self, path, invalidateChildren):
        if not self._lock.acquire(blocking=False):
            self._raiseServerException("Could not acquire remote connection lock. Multi-threaded access detected!")
        try:
            self._removeFromCache(path, removeChildNodes=invalidateChildren)
        finally:
            self._lock.release()

    #
    # These XPcom methods should NOT be implemented/overwritten in child classes
    #
    #def refresh(self, path):
    #    self.log.debug("refreshing: '%s'", path)
    #    self.do_verifyConnected()
    #    # remove path and all children from cache
    #    cached_info = self._rfConnectionService.getCachedRFInfo(self._cache_key, path)
    #    if cached_info:
    #        self._removeFromCache(path, removeChildNodes=1)
    #    self.list(path, 1)
    #
    # These are the readonly interface attributes used through pyXPcom
    def get_protocolType(self):
        return self.protocol

    def get_server(self):
        return self.server

    def get_port(self):
        return self.port

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def get_lastError(self):
        return self._lasterror


# SSH support using paramiko, http://www.lag.net/paramiko/
import paramiko

MAX_BLOCK_SIZE = 8192

# Dictionary of loaded keys, the file path is the dictionary key and the value
# is a paramiko private key (PKey).
loaded_private_keys = {}

class InvalidPrivateKeyException(Exception):
    """
    Exception raised when Komodo is unable to load a private key file.
    """
    pass

def load_private_key(privatekey, password=None):
    for key_class in (paramiko.DSSKey, paramiko.RSAKey):
        try:
            return key_class.from_private_key_file(privatekey)
            break
        except paramiko.PasswordRequiredException:
            password_attempts = 0
            prompt = "Passphrase for '%s':" % (privatekey, )
            promptSvc = components.classes["@mozilla.org/embedcomp/prompt-service;1"].\
                            getService(components.interfaces.nsIPromptService)
            while password_attempts < 3:
                password_attempts += 1
                checkstate = False
                if password_attempts >= 2:
                    prompt = "Passphrase incorrect, try again:"
                success, password, checkstate = promptSvc.promptPassword(None, "Private Key Authentication", prompt, "", "", checkstate)
                if not success:
                    return None
                try:
                    return key_class.from_private_key_file(privatekey, password)
                except paramiko.SSHException:
                    # Either the password was invalid or the key is invalid.
                    pass
        except paramiko.SSHException:
            # Invalid key file.
            pass
    raise InvalidPrivateKeyException("Unrecognized private key format")

# Implement common functions for SSH protocols
class koRemoteSSH(koRFConnection):
    def __init__(self):
        koRFConnection.__init__(self)
        self._use_time_delay = 0

    def __del__(self):
        # Ensure we are closed properly
        self.do_close()
        if self._connection:
            del self._connection
        self.log.debug("koSSH object deleted")

    def do_authenticateWithAgent(self):
        """Authenticate with a SSH agent"""
        # Currently paramiko supports the openSSH key-agent and Komodo
        # adds putty/pageant support for windows
        try:
            agent = paramiko.Agent()
            agent_keys = agent.get_keys()
            if len(agent_keys) > 0:
                for key in agent_keys:
                    self.log.debug('Trying ssh-agent key %s', paramiko.util.hexify(key.get_fingerprint()))
                    try:
                        self._connection.auth_publickey(self.username, key)
                        #self._connection.auth_publickey(self.username, key, event)
                    except paramiko.SSHException, e:
                        # the authentication failed (raised when no event passed in)
                        pass
                    if self._connection.is_authenticated():
                        self.log.debug('Agent authentication was successful!')
                        return 1
        except paramiko.BadAuthenticationType, e:
            # Likely if public-key authentication isn't allowed by the server
            self._lasterror = e.args[-1]
            self.log.error("SSH AGENT AUTH ERROR: %s", self._lasterror)
            #self.log.exception(e)
        return 0

    def do_authenticateWithPrivateKey(self):
        """Authenticate using a SSH private key"""
        # Currently paramiko supports the openSSH key-agent and Komodo
        # adds putty/pageant support for windows
        try:
            privatekey = self.privatekey
            if privatekey in loaded_private_keys:
                key = loaded_private_keys[privatekey]
                self.log.debug('Private key already loaded %r', privatekey)
            else:
                self.log.debug('Loading the private key %r', privatekey)
                key = load_private_key(privatekey)
                if not key:
                    # User cancelled or unable to load the private key file.
                    return 0
                loaded_private_keys[privatekey] = key

            self.log.debug('Trying private key %r', privatekey)
            try:
                self._connection.auth_publickey(self.username, key)
                #self._connection.auth_publickey(self.username, key, event)
            except paramiko.SSHException, e:
                # the authentication failed (raised when no event passed in)
                pass
            if self._connection.is_authenticated():
                self.log.debug('Private key authentication was successful!')
                return 1
        except (IOError, InvalidPrivateKeyException), e:
            self._lasterror = e.args[-1]
            self._raiseServerException("Private key authentication error.\nKey file: '%s'\nReason: %s" % (privatekey, self._lasterror))
        except paramiko.BadAuthenticationType, e:
            # Likely if public-key authentication isn't allowed by the server
            self._lasterror = e.args[-1]
            self.log.error("SSH AGENT AUTH ERROR: %s", self._lasterror)
            #self.log.exception(e)
        return 0

    # Authenicate to the remote SSH server using the supplied username/password
    # Return 1 on successful authentication
    # Return 0 when username/password is incorrect
    # Raise exception otherwise
    def do_authenticateWithPassword(self):
        try:
            # open the connection, an exception is always thrown if login fails
            self._connection.auth_password(username=self.username, password=self.password)
            # Transport layer is okay, lets set up the sftp connection object
            self.log.debug("SSH login: Successful")
            if self._use_time_delay:
                time.sleep(0.1)
            return 1
        except paramiko.BadAuthenticationType, e:
            # Likely if this type of authentication isn't allowed by the server
            # or it was just a bad username/password
            e = self._connection.get_exception() or e
            self.log.warn("do_authenticateWithPassword::paramiko.BadAuthenticationType: %s", e)
            for auth_type in e.allowed_types:
                self.log.debug("SSH server allows authorizaton using: %s", auth_type)
            if 'keyboard-interactive' not in e.allowed_types and \
               'password' not in e.allowed_types:
                # Password authentication not allowed on this server
                self._raiseServerException("Remote SSH server does not allow password authentication. Allowed types are: %r" % (", ".join(e.allowed_types)))
            # else, bad username/password
        except paramiko.SSHException, e:
            # Username/Password failed
            e = self._connection.get_exception() or e
            self.log.warn("do_authenticateWithPassword:: SSHException: %s", e)
            # If it's problem reading the SSH protocol banner, it's likely
            # because the user has specified the wrong details:
            # http://bugs.activestate.com/show_bug.cgi?id=47047
            if e.args[-1] == "Error reading SSH protocol banner":
                error_message = "%s:%d is not a recognized SSH server. " \
                                "Please recheck your %s server and port " \
                                "configuration." % (self.server, self.port,
                                                    self.protocol.upper())
                self._raiseServerException(error_message)
            # else, problem logging in
        self.log.warn("SSH error: Invalid username/password")
        return 0

    def do_openSocket(self):
        """Open the SSH connection to the remote site."""
        self._lasterror = ""
        try:
            # open the connection
            s = self._get_and_open_socket()
            self._connection = paramiko.Transport(s)

            # We want to ensure the paramiko logger is turned off
            logger_name = self._connection.get_log_channel()
            logger = paramiko.util.get_logger(logger_name)
            logger.setLevel(logging.CRITICAL)

            if self._globalPrefs.getBoolean('remotefiles_sftp_compression_enabled', True):
                # Turn on compression (if supported by the server) - bug 98376.
                self._connection.use_compression()

            # Start the SSH negotiation
            event = threading.Event()
            self._connection.start_client(event)
            event.wait(self._socket_timeout)
            if not event.isSet():
                self._raiseTimeoutException()
        except (paramiko.SSHException, socket.error), e:
            self._raiseServerException(e.args[-1])

    def do_close(self):
        """Close the SSH connection"""
        try:
            self.log.debug("Closing SSH connection")
            if self._connection and self._connection.is_active:
                self._connection.close()
        except paramiko.SSHException, e:
            self._lasterror = e.args[-1]
            self.log.error("SSH CLOSE ERROR: %s", self._lasterror)
            # XXX - Raise an exception... ??
            pass

    def do_verifyConnected(self):
        """Verify that we are connected to the remote server"""
        try:
            if not self._connection or not self._connection.is_active():
                self.open(self.server, self.port, self.username, self.password,
                          "", self.passive, self.privatekey)
            else:
                # Periodically check that the connection is still alive, bug
                # 85050.
                current_time = time.time()
                if (current_time - self._last_verified_time) >= 30:
                    self.log.debug("Checking that the SSH connection is alive")
                    self.do_getPathInfo("/")
                    self._last_verified_time = current_time
        except Exception, e:
            if isinstance(e, socket.timeout):
                self._raiseWithException(e)
            else:
                # Connection lost, reconnect if possible (bug 85050).
                self.log.info("Re-opening the SSH connection because it was closed")
                self.open(self.server, self.port, self.username, self.password,
                          "", self.passive)

    def runCommand(self, command, combineStdoutAndStderr):
        channel = self._connection.open_session()
        channel.settimeout(self._socket_timeout)
        channel.set_combine_stderr(combineStdoutAndStderr)
        status = -1
        stdout_segments = []
        stderr_segments = []
        try:
            try:
                # This was causing problems on different platforms, so just grab the
                # response to the command.
                channel.exec_command(command)
                channels = [channel]
                while 1:
                    # XXX - Paramiko needs to support stderr select
                    i, o, e = select.select(channels, [], channels, None)
                    if e:
                        break
                    data = ''
                    if channel.recv_ready():
                        data = channel.recv(8192)
                        if not data:
                            break
                        stdout_segments.append(data)
                    #if channel.recv_stderr_ready():
                    #    data = channel.recv_stderr(8192)
                    #    if not data:
                    #        break
                    #    stderr_segments.append(data)
                    if not data:
                        break
                status = channel.recv_exit_status()
            finally:
                channel.close()
        except Exception, e:
            self.log.exception(e)
        stdout = ''.join(stdout_segments)
        stderr = ''.join(stderr_segments)
        #print "runCommand: status: %r" % (status, )
        #if stdout:
        #    print "runCommand: stdout\n%s" % (stdout, )
        #if stderr:
        #    print "runCommand: stderr\n%s" % (stderr, )
        return status, stdout, stderr
    
    def runCommandAsync(self, command, callbackStdout, callbackStderr):
        import threading
        t = threading.Thread(target=self._runCommandAsync,
                             args=(command, callbackStdout, callbackStderr),
                             name="runRemoteAsync")
        t.setDaemon(True)
        t.start()
        
    def _runCommandAsync(self, command, cbStdo, cbStde):
        channel = self._connection.open_session()
        channel.settimeout(self._socket_timeout)
        status = -1
        try:
            try:
                # This was causing problems on different platforms, so just grab the
                # response to the command.
                channel.exec_command(command)
                channels = [channel]
                while 1:
                    # XXX - Paramiko needs to support stderr select
                    i, o, e = select.select(channels, [], channels, None)
                    if e:
                        break
                    data = ''
                    if channel.recv_ready():
                        data = channel.recv(8192)
                        if not data:
                            break
                        self._runCmdCb(cbStdo, data)
                    if channel.recv_stderr_ready():
                        data = channel.recv_stderr(8192)
                        if not data:
                            break
                        self._runCmdCb(cbStde, data)
                    if not data:
                        break
                status = channel.recv_exit_status()
            finally:
                channel.close()
        except Exception, e:
            self.log.exception(e)

    @components.ProxyToMainThreadAsync
    def _runCmdCb(self, callback, result):
        callback.callback(0, result)

# Debug the directory cache
def debug_dirCache(log, cache):
    if log.level == logging.DEBUG:
        log.debug("*" * 40)
        log.debug("Directory cache:")
        for ckey in cache.keys():
            value = cache[ckey]
            if isinstance(value, list):
                s = ["%s:" % ckey]
                for dkey in value:
                    s.append("    %s" % dkey)
                log.debug('\n'.join(s))
            else:
                log.debug("%s: %s", ckey, value)
        log.debug("*" * 40)

def _test():
    pass

if __name__ == '__main__':
    _test()
