#!python
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

# The implementation of the Komodo LastError service.

import socket
import threading
import logging
import types
import urllib

from xpcom import components, ServerException, COMException, nsError
from xpcom.client import WeakReference

import URIlib
import remotefilelib

log = logging.getLogger('koRemoteConnectionService')
#log.setLevel(logging.DEBUG)

class BadServerInfoException(Exception):
    pass

#---- PyXPCOM component implementation

class koServerInfo:
    _com_interfaces_ = [components.interfaces.koIServerInfo]
    _reg_desc_ = "Server Information"
    _reg_clsid_ = "{71db5411-9a71-4961-a700-b348b8ef0f75}"
    _reg_contractid_ = "@activestate.com/koServerInfo;1"

    def __init__(self):
        self.raw_hostdata = ''
        self.protocol = ''
        self.alias = ''
        self.hostname = ''
        self.port = -1
        self.username = ''
        self.password = ''
        self.path = ''
        self.passive = 1

    def init(self, protocol, alias, hostname, port, username, password, path,
             passive, raw_hostdata=None):
        self.protocol = protocol
        self.alias = alias
        self.hostname = hostname
        try:
            self.port = int(port)
        except ValueError:
            self.port = -1
        self.username = username
        self.password = password
        self.path = path
        try:
            self.passive = int(passive)
        except ValueError:
            self.passive = 1
        if raw_hostdata is None:
            # Generate the host data
            fields = map(urllib.quote, [protocol, alias, hostname, str(port),
                                        path, str(passive)])
            self.raw_hostdata = ":".join(fields)
        else:
            # Use the existing host data
            self.raw_hostdata = raw_hostdata

    def initFromLoginInfo(self, logininfo):
        # logininfo is a nsILoginInfo xpcom object.
        host_split = logininfo.hostname.split(':')
        # Only use Komodo style server info, ignore others:
        #   nspassword.host example for Komodo:
        #        FTP:the foobar server:foobar.com:21::1
        #   nspassword.host example for Firefox:
        #        ftp://twhiteman@foobar.com:21
        if len(host_split) < 5:
            raise BadServerInfoException()
        if len(host_split) == 5:
            # Upgrade - add the passive setting.
            host_split.append("1")
        # Unquote the elements.
        host_split = map(urllib.unquote, host_split)
        self.init(host_split[0], host_split[1], host_split[2], host_split[3],
                  logininfo.username, logininfo.password, host_split[4],
                  host_split[5],
                  raw_hostdata=logininfo.hostname)

    def generateLoginInfo(self):
        loginInfo = components.classes["@mozilla.org/login-manager/loginInfo;1"]\
                            .createInstance(components.interfaces.nsILoginInfo)
        loginInfo.init(self.raw_hostdata, None, self.alias,
                       self.username, self.password, "", "")
        return loginInfo
        

# The underscore names are private, and should only be used internally
# All underscore names require locking, which should happen through the
# the use of the exposed (non-underscore) functions.
class koRemoteConnectionService:
    _com_interfaces_ = [components.interfaces.koIRemoteConnectionService]
    _reg_desc_ = "Remote Connection Service"
    _reg_clsid_ = "{c12f592b-11a2-4172-85c2-02d87ac56887}"
    _reg_contractid_ = "@activestate.com/koRemoteConnectionService;1"

    EMPTY_PASSWORD_SENTINEL = '\vKOMODO_EMPTY_PASSWORD\v'

    def __init__(self):
        # _connections is a dictionary of python connection objects. The key
        # is a combination of the connection attributes:
        #   conn_key = "%s:%s:%s:%s" % (protocol, server, port, username)
        self._connections = {}
        # _sessionData is a dictionary of known connection information
        #   sessionkey = "%s:%s:%s" % (server, port, username)
        #   Note: Protocol is not used as different protocols should use
        #         the same settings (XXX - WebDAV ?) (XXX - port ?)
        self._sessionData = {}
        # _cachedFiles contains a sub-dictionary for every connection made.
        # The keys for _cachedFiles are the same as used for _connections.
        #   conn_key = "%s:%s:%s:%s" % (protocol, server, port, username)
        # The sub-dictionary will contain filepaths as the keys, whilst
        # the value will be a rf_info object containing the file information.
        self._cachedFiles = {}
        # Global lock for the Remote Connection service
        self._lock = threading.Lock()

    ## Private, internal functions
    ## The lock has been acquired, just do the internal work

    # We have the lock already
    def _getConnection(self, protocol, server, port, username, password, path,
                       passive=True):
        if password:
            log.debug("getConnection: %s %s:%s@%s:%r '%s'", 
                           protocol, username, '*' * len(password), server, port, path)
        else:
            log.debug("getConnection: %s %s@%s:%r '%s'",
                           protocol, username, server, port, path)

        if not protocol or protocol.lower() not in URIlib.RemoteURISchemeTypes:
            self._lasterror = "Unhandled protocol type: %s" % (protocol)
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        protocol = protocol.lower()
        if port < 0:
            port = remotefilelib.koRFProtocolDefaultPort[protocol]
        conn_key = "%s:%s:%s:%s"%(protocol,server,port,username)
        if conn_key in self._connections and \
            self._connections[conn_key]():
            log.debug("getConnection, found cached connection")
            return self._connections[conn_key]()
        log.debug("getConnection, no cached connection found")

        sessionkey = "%s:%s:%s" % (server, port, username)
        if username and not password:
            # See if we have opened this connection before, use same username/password again
            sess = self._getSessionInfo(sessionkey)
            if sess:
                username, password = sess[:2]

        c = components.classes['@activestate.com/ko%sConnection;1' % (protocol.upper())].\
            createInstance(components.interfaces.koIRemoteConnection)
        log.debug("getConnection: Opening %s %s@%s:%r", protocol, username, server, port)
        try:
            c.open(server, port, username, password, path, passive)
            self._connections[conn_key] = WeakReference(c)
            # Update sessionkey to contain any changes to the username, which
            # can happen if/when prompted for a username/password. Fix for bug:
            # http://bugs.activestate.com/show_bug.cgi?id=65529
            sessionkey = "%s:%s:%s" % (server, port, c.username)
            self._saveSessionInfo(sessionkey, [c.username, c.password])
            return c
        except COMException, ex:
            # koIRemoteConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))

    # Return the server prefs for the given server alias
    # We have the lock already
    def _getServerPrefSettings(self, server_alias):
        serverInfo = self.getServerInfoForAlias(server_alias)
        if serverInfo:
            # we found our server, return the info
            return [serverInfo.protocol,
                    serverInfo.alias,
                    serverInfo.hostname,
                    serverInfo.port,
                    serverInfo.username,
                    serverInfo.password,
                    serverInfo.path,
                    serverInfo.passive]
        return None

    def _getServerDetailsFromUri(self, uri):
        server_alias = ''
        protocol = ''
        hostname = ''
        port = -1
        username = ''
        password = ''
        path = ''
        passive = 1

        uriparse = URIlib.URIParser(uri)
        if uriparse.scheme not in URIlib.RemoteURISchemeTypes:
            self._lasterror = "Unhandled protocol type: %s" % (protocol)
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)
        protocol = uriparse.scheme

        if not uriparse.server:
            self._lasterror = "No server information for uri: %s" % (uri)
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        # Check if the given server is actually a server alias (in prefs).
        server_prefs = self._getServerPrefSettings(uriparse.server)
        if server_prefs:
            server_alias = uriparse.server
            # get the connection info from prefs
            log.debug("prefs info: %s", server_prefs)
            protocol = server_prefs[0]
            aliasname = server_prefs[1]
            hostname = server_prefs[2]
            port     = server_prefs[3]
            username = server_prefs[4]
            password = server_prefs[5]
            path     = server_prefs[6]
            passive  = server_prefs[7]
        else:
            log.debug("uri host info: %s", uriparse.server)
            serveruri = URIlib.URIServerParser(uriparse.server)
            if serveruri.username:  username   = serveruri.username
            if serveruri.password:  password   = serveruri.password
            if serveruri.hostname:  hostname   = serveruri.hostname
            if serveruri.port:      port       = serveruri.port

        # Use the URI path if one was supplied
        if uriparse.path:
            path = uriparse.path

        return [ protocol, server_alias, hostname, str(port), username,
                 password, path, str(passive) ]

    # We have the lock already
    def _getConnectionUsingUri(self, uri):
        protocol, server_alias, hostname, port, username, password, \
                    path, passive = self._getServerDetailsFromUri(uri)
        # We want the port as an integer
        try:
            if not port: port = -1
            elif type(port) != types.IntType: port = int(port)
        except ValueError:
            log.debug("Invalid port number: %s", port)
            port = -1

        # We want the passive as an integer
        try:
            if not passive: passive = 1
            elif type(passive) != types.IntType: passive = int(passive)
        except ValueError:
            log.debug("Invalid passive value: %s", passive)
            passive = 1

        # Now we have all the info, lets go make the connection
        connection = self._getConnection(protocol, hostname, port, username,
                                         password, path, passive);
        if connection:
            # Set the alias used to get the connection (if there was one)
            connection.alias = server_alias;
        return connection

    # We have the lock already
    def _saveSessionInfo(self, key, data):
        self._sessionData[key] = data

    # We have the lock already
    def _getSessionInfo(self, key):
        if key in self._sessionData:
            return self._sessionData[key]
        return []

    # We have the lock already
    def _setCachedRFInfo(self, cache_key, path, rfinfo):
        log.debug("_setCachedRFInfo: Adding rfinfo to cache: '%s'", path)
        if not self._cachedFiles.has_key(cache_key):
            self._cachedFiles[cache_key] = {}
        cache = self._cachedFiles[cache_key]
        # Add the rfinfo to the cache
        cache[path] = rfinfo

        # Add all the child rfinfo's to the cache
        children = rfinfo.getChildren()
        for i in range(len(children)):
            childRFInfo = children[i]
            child_path = remotefilelib.addslash(path) + childRFInfo.getFilename()
            if cache.has_key(child_path):
                # It's already cached, update the child to be the cached object
                log.debug("_setCachedRFInfo: Adding new child rfinfo to cache: '%s'", child_path)
                children[i] = cache[child_path]
            else:
                # It's not cached, add it to the cache then
                log.debug("_setCachedRFInfo: Adding new child rfinfo to cache: '%s'", child_path)
                cache[child_path] = childRFInfo

    # We have the lock already
    def _getCachedRFInfo(self, cache_key, path):
        if not self._cachedFiles.has_key(cache_key):
            self._cachedFiles[cache_key] = {}
        cache = self._cachedFiles[cache_key]
        if cache.has_key(path):
            return cache[path]
        return None

    # We have the lock already
    def _removeCachedRFInfo(self, cache_key, path, removeChildPaths):
        if self._cachedFiles.has_key(cache_key):
            cache = self._cachedFiles[cache_key]
            if cache.has_key(path):
                del cache[path]
            if removeChildPaths:
                # Remove all cached paths that are under this directory
                dirPath = remotefilelib.addslash(path)
                for keypath in cache.keys():
                    if keypath.startswith(dirPath):
                        del cache[keypath]


    ## Public, exposed functions from IDL
    ## Acquire the lock and call the private methods


    # Returns True if the url is supported by the remote connection service.
    def isSupportedRemoteUrl(self, url):
        u = URIlib.URIParser(url)
        return u.scheme in URIlib.RemoteURISchemeTypes

    # Returns the list of supported protocols
    def getSupportedProtocolNames(self):
        return URIlib.RemoteURISchemeTypes

    # Return url for given connection and koRemoteFileInfo object
    def getUriForConnectionAndRfInfo(self, connection, rfInfo):
        server = connection.alias
        protocol = connection.protocol
        path = rfInfo.getFilepath()
        if not server:
            # Build one up from the connection details, don't include password
            server = "%s@%s" % (urllib.quote(connection.username),
                                urllib.quote(connection.server))
            port = connection.port
            if port != remotefilelib.koRFProtocolDefaultPort[protocol]:
                server += ":%d" % (port)
        # Remove base slash, it's added when we make the uri
        if path and path[0] == "/":
            path = path[1:]

        # Note: would have liked to use the existing URIParser class here, but
        #       using the set_path() method using an absolute path will create
        #       a "file:///" URI even if it was originally "sftp://". Bah!
        try:
            return "%s://%s/%s" % (protocol, server, urllib.quote(path))
        except KeyError, e:
            # Quoting can fail on unicode chars, just leave as is then.
            return "%s://%s/%s" % (protocol, server, path)

    # Return a connection object for the given parameters
    def getConnection(self, protocol, server, port, username, password, path,
                      passive=True):
        # XXX - Requires ActivePython to support ssl
        # http://bugs.activestate.com/show_bug.cgi?id=50207
        if protocol == "ftps" and not hasattr(socket, 'ssl'):
            self._lasterror = "SSL is not supported in Komodo's internal python"
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        self._lock.acquire()
        try:
            return self._getConnection(protocol, server, port, username, password, path, passive)
        finally:
            self._lock.release()

    # getConnection2 is the same as getConnection, except it also offers to set
    # the passive ftp mode.
    getConnection2 = getConnection

    # Return the server prefs for the given server alias
    def getServerPrefSettings(self, server_alias):
        return self._getServerPrefSettings(server_alias)

    # Return the server details for the given URI
    def getServerDetailsFromUri(self, uri):
        return self._getServerDetailsFromUri(uri)

    # Return the connection object for the given URI, all the connection
    # details should be included in the URI
    #   URI ex: ftp://test:tesuser@somesite.com:22/web/info.php
    #   URI ex: ftp://my_test_site/web/info.php
    def getConnectionUsingUri(self, uri):
        self._lock.acquire()
        try:
            return self._getConnectionUsingUri(uri)
        finally:
            self._lock.release()

    # Return the connection object for the given server alias.
    def getConnectionUsingServerAlias(self, server_alias):
        self._lock.acquire()
        try:
            server_prefs = self._getServerPrefSettings(server_alias)
            if server_prefs:
                protocol = server_prefs[0]
                #aliasname = server_prefs[1]
                hostname = server_prefs[2]
                port     = server_prefs[3]
                username = server_prefs[4]
                password = server_prefs[5]
                path     = server_prefs[6]
                passive  = server_prefs[7]
                connection =  self._getConnection(protocol, hostname, port,
                                                  username, password, path,
                                                  passive)
                if connection:
                    # Remember the alias used to get the connection.
                    connection.alias = server_alias;
                return connection
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                  "No server found for alias: %r" % (
                                        server_alias))
        finally:
            self._lock.release()

    # Set the session information for this key
    def saveSessionInfo(self, key, data):
        self._lock.acquire()
        try:
            return self._saveSessionInfo(key, data)
        finally:
            self._lock.release()

    # Return the session information for this key
    def getSessionInfo(self, key):
        self._lock.acquire()
        try:
            return self._getSessionInfo(key)
        finally:
            self._lock.release()

    # Cache the remote file information for this connection
    def setCachedRFInfo(self, cache_key, path, rfinfo):
        self._lock.acquire()
        try:
            self._setCachedRFInfo(cache_key, path, rfinfo)
        finally:
            self._lock.release()

    # Cache the remote file information for this connection
    def getCachedRFInfo(self, cache_key, path):
        self._lock.acquire()
        try:
            return self._getCachedRFInfo(cache_key, path)
        finally:
            self._lock.release()

    # Remove the cached information for this connection
    def removeCachedRFInfo(self, cache_key, path, removeChildPaths):
        self._lock.acquire()
        try:
            self._removeCachedRFInfo(cache_key, path, removeChildPaths)
        finally:
            self._lock.release()

    # Return the sorted list of servers, in koIServerInfo objects.
    def getServerInfoList(self):
        serverinfo_list = []
        loginmanager = components.classes["@mozilla.org/login-manager;1"].\
                            getService(components.interfaces.nsILoginManager)
        logins = loginmanager.getAllLogins() # array of nsILoginInfo
        #print "getServerInfoList:: logins: %r" % (logins, )
        if logins:
            for logininfo in logins:
                logininfo.QueryInterface(components.interfaces.nsILoginInfo)
                serverinfo = koServerInfo()
                try:
                    if logininfo.password == self.EMPTY_PASSWORD_SENTINEL:
                        logininfo.password = ''
                    serverinfo.initFromLoginInfo(logininfo)
                    serverinfo_list.append(serverinfo)
                except BadServerInfoException:
                    # Ignore non Komodo server entries.
                    pass
            serverinfo_list.sort(lambda a,b: cmp(a.alias.lower(), b.alias.lower()))
        return serverinfo_list

    def getServerInfoForAlias(self, server_alias):
        servers = self.getServerInfoList()
        for serverInfo in servers:
            if server_alias == serverInfo.alias:
                return serverInfo
        return None

    def saveServerInfoList(self, serverinfo_list):
        loginmanager = components.classes["@mozilla.org/login-manager;1"].\
                            getService(components.interfaces.nsILoginManager)
        logins = loginmanager.getAllLogins() # array of nsILoginInfo
        # remove all old servers
        if logins:
            for logininfo in logins:
                logininfo.QueryInterface(components.interfaces.nsILoginInfo)
                serverinfo = koServerInfo()
                try:
                    serverinfo.initFromLoginInfo(logininfo)
                    loginmanager.removeLogin(logininfo)
                except BadServerInfoException:
                    # Ignore non Komodo server entries.
                    pass
        # and now add all the new servers
        for serverinfo in serverinfo_list:
            # Transform the serverinfo into a logininfo object.
            logininfo = serverinfo.generateLoginInfo()
            if not logininfo.password:
                # Hack to workaround the login manager not accepting empty
                # passwords.
                logininfo.password = self.EMPTY_PASSWORD_SENTINEL
            loginmanager.addLogin(logininfo)
