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

import time
import socket
import threading
import logging
import types
import urllib

from xpcom import components, ServerException, COMException, nsError

import URIlib

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
        self.guid = ''
        self.raw_hostdata = ''
        self.protocol = ''
        self.alias = ''
        self.hostname = ''
        self.port = -1
        self.username = ''
        self.password = ''
        self.path = ''
        self.passive = 1
        self.privatekey = ''

    def init(self, guid, protocol, alias, hostname, port, username, password,
             path, passive, privatekey='', raw_hostdata=None):
        self.guid = guid
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
        self.privatekey = privatekey
        if raw_hostdata is None:
            # Generate the host data
            fields = map(urllib.quote, [protocol, alias, hostname, str(port),
                                        path, str(passive), privatekey])
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
        if len(host_split) == 6:
            # Upgrade - add the privatekey setting.
            host_split.append("")
        # Unquote the elements.
        host_split = map(urllib.unquote, host_split)
        guid = logininfo.QueryInterface(components.interfaces.\
                                        nsILoginMetaInfo).guid
        self.init(guid, host_split[0], host_split[1], host_split[2],
                  host_split[3], logininfo.username, logininfo.password,
                  host_split[4], host_split[5], host_split[6],
                  raw_hostdata=logininfo.hostname)

    def generateLoginInfo(self):
        loginInfo = components.classes["@mozilla.org/login-manager/loginInfo;1"]\
                            .createInstance(components.interfaces.nsILoginInfo)
        loginInfo.init(self.raw_hostdata, None, self.alias,
                       self.username, self.password, "", "")
        loginInfo.QueryInterface(components.interfaces.nsILoginMetaInfo).\
                    guid = self.guid
        return loginInfo
        

class RemoteConnectionCache(object):
    def __init__(self):
        self._cache = {}
        self._timer = None
        self._lock = threading.Lock()

        globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                        getService(components.interfaces.koIPrefService).prefs
        self.EXPIRY_SECONDS = globalPrefs.getLongPref('remotefiles_inactiveConnectionExpirySeconds')

    def _timer_callback(self):
        # Periodically, clear old connections from the cache.
        log.debug("RemoteConnectionCache:: Got the timer callback")
        self._lock.acquire()
        try:
            self._timer = None
            for cache_key, cache_item in self._cache.items():
                connection, cache_time = cache_item
                if (time.time() - cache_time) > self.EXPIRY_SECONDS:
                    log.debug("RemoteConnectionCache:: expired the cached "
                              "connection for: %r", cache_key)
                    self._cache.pop(cache_key, None)
                    try:
                        connection.close()
                    except Exception, ex:
                        # We don't care if there was any exception here.
                        log.debug("RemoteConnectionCache:: exception when closing connection: %r", ex)
            if len(self._cache) == 0:
                # Nothing in the cache, no point in keeping the timer active.
                log.debug("RemoteConnectionCache:: cancelled the timer, "
                          "nothing left in the cache.")
            else:
                self._ensureTimerActivated()
        finally:
            self._lock.release()

    def _ensureTimerActivated(self):
        if not self._timer:
            self._timer = threading.Timer(60, self._timer_callback)   # Every minute.
            self._timer.setDaemon(True)
            self._timer.start()
            log.debug("RemoteConnectionCache:: started a new timer")

    ##
    # Add a connection to cache.
    # @param cache_key {str}  The connection cache key.
    # @param connection {koIRemoteConnection}  The connection to cache.
    #
    def addConnection(self, cache_key, connection):
        self._lock.acquire()
        try:
            self._cache[cache_key] = (connection, time.time())
            log.debug("RemoteConnectionCache:: cached connection for: %r", cache_key)
            self._ensureTimerActivated()
        finally:
            self._lock.release()

    ##
    # Add a connection to cache.
    # @param cache_key {str}  The connection cache key.
    # @returns {koIRemoteConnection}  The cached connection.
    #
    def getConnection(self, cache_key):
        self._lock.acquire()
        try:
            cache_item = self._cache.get(cache_key)
            if cache_item is not None:
                # There is a cached item, check if it's still alive.
                connection, cache_time = cache_item
                # Update the last cached time.
                self._cache[cache_key] = (connection, time.time())
                return connection
            return None
        finally:
            self._lock.release()

    ##
    # Remove a connection from the cache.
    # @param cache_key {str}  The connection cache key.
    #
    def removeConnectionWithKey(self, cache_key):
        self._lock.acquire()
        try:
            cache_item = self._cache.get(cache_key)
            if cache_item is not None:
                log.debug("RemoteConnectionCache: connection removed: %r",
                          cache_key)
                self._cache.pop(cache_key, None)
        finally:
            self._lock.release()

    ##
    # Remove all connections from the cache and stop any timers.
    #
    def clearAll(self):
        self._lock.acquire()
        try:
            self._cache = {}
            if self._timer is not None:
                self._timer.cancel()
        finally:
            self._lock.release()


# The underscore names are private, and should only be used internally.
class koRemoteConnectionService:
    _com_interfaces_ = [components.interfaces.koIRemoteConnectionService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Remote Connection Service"
    _reg_clsid_ = "{c12f592b-11a2-4172-85c2-02d87ac56887}"
    _reg_contractid_ = "@activestate.com/koRemoteConnectionService;1"

    EMPTY_PASSWORD_SENTINEL = '\vKOMODO_EMPTY_PASSWORD\v'

    # List of server login info - cached data, gets updated when the server
    # prefs are modified.
    __serverinfo_list = None

    def __init__(self):
        # _connections is a dictionary of python connection objects. The key
        # is a combination of the connection attributes:
        #   conn_key = "%s:%s:%s:%s" % (protocol, server, port, username)
        # and the value is a tuple (connection, last_used_time)
        self._connection_cache = RemoteConnectionCache()
        # _sessionData is a dictionary of known connection information
        #   sessionkey = "%s:%s:%s" % (server, port, username)
        #   Note: Protocol is not used as different protocols should use
        #         the same settings (XXX - WebDAV ?) (XXX - port ?)
        self._sessionData = {}
        # _cachedFiles contains a sub-dictionary for every connection made.
        # The keys for _cachedFiles are the same as used for _connections.
        #   conn_key = "%s:%s:%s:%s" % (thread_id, protocol, server, port,
        #                               username)
        # The sub-dictionary will contain filepaths as the keys, whilst
        # the value will be a rf_info object containing the file information.
        self._cachedFiles = {}
        # Global lock for the Remote Connection service - used to maintain
        # control over the _sessionData and _cachedFiles.
        self._lock = threading.Lock()

        # Listen for network status changes.
        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                      getService(components.interfaces.nsIObserverService)
        obsSvc.addObserver(self, "network:offline-status-changed", False)
        obsSvc.addObserver(self, "xpcom-shutdown", False)

    ## Private, internal functions

    def _generateCachekey(self, protocol, server, port, username):
        """Generate a key to be used for caching the connection object.
        
        The currentThread() call is used to ensure each thread gets their own
        unqiue connection.
        """
        conn_key = "%s:%s:%s:%s:%s" % (threading.currentThread(),
                                       protocol, server, port, username)
        return conn_key

    def _getConnection(self, protocol, server, port, username, password, path,
                       passive=True, privatekey='', useConnectionCache=True):
        if password:
            log.debug("getConnection: %s %s:%s@%s:%r '%s'", 
                           protocol, username, '*' * len(password), server, port, path)
        else:
            log.debug("getConnection: %s %s@%s:%r '%s'",
                           protocol, username, server, port, path)
        if privatekey:
            log.debug("getConnection: auth using private key: %r", privatekey)

        if not protocol or protocol.lower() not in URIlib.RemoteURISchemeTypes:
            self._lasterror = "Unhandled protocol type: %s" % (protocol)
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        protocol = protocol.lower()
        if port < 0:
            from remotefilelib import koRFProtocolDefaultPort
            port = koRFProtocolDefaultPort[protocol]
        if useConnectionCache:
            conn_key = self._generateCachekey(protocol, server, port, username)
            c = self._connection_cache.getConnection(conn_key)
            if c is not None:
                log.debug("getConnection, found cached connection")
                return c
            log.debug("getConnection, no cached connection found: %r", conn_key)

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
            c.open(server, port, username, password, path, passive, privatekey)
            if useConnectionCache:
                self._connection_cache.addConnection(conn_key, c)
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
                    serverInfo.passive,
                    serverInfo.privatekey]
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
        privatekey = ''

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
            privatekey = server_prefs[8]
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
                 password, path, str(passive), privatekey ]

    def _getConnectionUsingUri(self, uri, useConnectionCache=True):
        protocol, server_alias, hostname, port, username, password, \
                    path, passive, privatekey = self._getServerDetailsFromUri(uri)
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
                                         password, path, passive,
                                         privatekey=privatekey,
                                         useConnectionCache=useConnectionCache)

        if connection:
            # Set the alias used to get the connection (if there was one)
            connection.alias = server_alias;
        return connection

    # Return the sorted list of servers, in koIServerInfo objects.
    # Note: The "_lock" must *not* be acquired by the thread making this call,
    #       otherwise Komodo can become deadlocked - bug 92273.
    @components.ProxyToMainThread
    def _getServerInfoList(self):
        serverinfo_list = []
        try:
            loginmanager = components.classes["@mozilla.org/login-manager;1"].\
                                getService(components.interfaces.nsILoginManager)
            logins = loginmanager.getAllLogins() # array of nsILoginInfo
        except COMException, ex:
            # TODO: Check if this is a testing environment, if it's not then
            #       this should be an exception.
            log.warn("Could not obtain logins from the nsILoginManager")
            logins = []
        #print "_getServerInfoList:: logins: %r" % (logins, )
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
        from remotefilelib import addslash
        log.debug("_setCachedRFInfo: Adding rfinfo, cache_key %r, path %r",
                  cache_key, path)
        cache = self._cachedFiles.get(cache_key)
        if cache is None:
            self._cachedFiles[cache_key] = cache = {}
        # Add the rfinfo to the cache
        cache[path] = rfinfo
        # Add all the child rfinfo's to the cache
        children = rfinfo.getChildren()
        for i in range(len(children)):
            childRFInfo = children[i]
            child_path = addslash(path) + childRFInfo.getFilename()
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
        log.debug("_getCachedRFInfo: cache_key %r, path %r",
                  cache_key, path)
        if not self._cachedFiles.has_key(cache_key):
            self._cachedFiles[cache_key] = {}
        cache = self._cachedFiles[cache_key]
        if cache.has_key(path):
            return cache[path]
        return None

    # We have the lock already
    def _removeCachedRFInfo(self, cache_key, path, removeChildPaths):
        log.debug("_removeCachedRFInfo: cache_key %r, path %r",
                  cache_key, path)
        if self._cachedFiles.has_key(cache_key):
            cache = self._cachedFiles[cache_key]
            if cache.has_key(path):
                del cache[path]
            if removeChildPaths:
                # Remove all cached paths that are under this directory
                from remotefilelib import addslash
                dirPath = addslash(path)
                for keypath in cache.keys():
                    if keypath.startswith(dirPath):
                        del cache[keypath]


    ## Public, exposed functions from IDL

    def observe(self, subject, topic, data):
        # https://developer.mozilla.org/en/Observer_Notifications
        if topic == "network:offline-status-changed":
            if data == "offline":
                self.clearConnectionCache()
        elif topic == "xpcom-shutdown":
            self._connection_cache.clearAll()

    def clearConnectionCache(self):
        # Gone offline, clear the connection cache.
        self._connection_cache.clearAll()

    def removeConnectionFromCache(self, conn):
        conn_key = self._generateCachekey(conn.protocol, conn.server,
                                          conn.port, conn.username)
        self._connection_cache.removeConnectionWithKey(conn_key)

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
            from remotefilelib import koRFProtocolDefaultPort
            server = "%s@%s" % (urllib.quote(connection.username),
                                urllib.quote(connection.server))
            port = connection.port
            if port != koRFProtocolDefaultPort[protocol]:
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
                      passive=True, privatekey=''):
        # XXX - Requires ActivePython to support ssl
        # http://bugs.activestate.com/show_bug.cgi?id=50207
        if protocol == "ftps" and not hasattr(socket, 'ssl'):
            self._lasterror = "SSL is not supported in Komodo's internal python"
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        return self._getConnection(protocol, server, port, username, password,
                                   path, passive, privatekey=privatekey)

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
        return self._getConnectionUsingUri(uri)

    # Return the connection object for the given URI, all the connection
    # details should be included in the URI. Will not cache the connection or
    # re-use any existing cached connection.
    def getConnectionUsingUriNoCache(self, uri):
        return self._getConnectionUsingUri(uri, useConnectionCache=False)

    def getConnectionUsingServerAlias(self, server_alias):
        return self._getConnectionUsingServerAlias(server_alias)
    
    # Return the connection object for the given server alias.
    def _getConnectionUsingServerAlias(self, server_alias, callback=False):
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
            privatekey = server_prefs[8]
            connection =  self._getConnection(protocol, hostname, port,
                                              username, password, path,
                                              passive, privatekey=privatekey)
            if connection:
                # Remember the alias used to get the connection.
                connection.alias = server_alias;
            
            if callback:
                return self.asyncCallback(callback, connection)
            else:
                return connection
        
        if callback:
            self.asyncCallback(callback, False)
        else:
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                "No server found for alias: %r" % (
                                        server_alias))
    
    def getConnByAliasAsync(self, server_alias, callback):
        import threading
        t = threading.Thread(target=self._getConnectionUsingServerAlias,
                             args=(server_alias, callback),
                             name="getConnAsync")
        t.setDaemon(True)
        t.start()
        
    @components.ProxyToMainThreadAsync
    def asyncCallback(self, callback, result):
        callback.callback(0, result)

    # Return the connection object for the given serverInfo.
    def getConnectionUsingServerInfo(self, serverInfo):
        self._lock.acquire()
        try:
            connection =  self._getConnection(serverInfo.protocol,
                                              serverInfo.hostname,
                                              serverInfo.port,
                                              serverInfo.username,
                                              serverInfo.password,
                                              serverInfo.path,
                                              serverInfo.passive,
                                              serverInfo.privatekey)
            if connection:
                # Remember the alias used to get the connection.
                connection.alias = serverInfo.alias;
            return connection
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
        if self.__serverinfo_list is None:
            self.__serverinfo_list = self._getServerInfoList()
        return self.__serverinfo_list
    
    def clearServerInfoListCache(self):
        # When Sync creates new logins using the loginManager it has to clear the cache
        self.__serverinfo_list = None

    def getServerInfoForAlias(self, server_alias):
        servers = self.getServerInfoList()
        for serverInfo in servers:
            if server_alias == serverInfo.alias:
                return serverInfo
        return None

    def saveServerInfoList(self, serverinfo_list):
        # Ensure the cache is cleared, as it must get reloaded by
        # getServerInfoList later on, otherwise we may get 'Login exists'
        # errors, see - bug 89685.
        self.clearServerInfoListCache()

        loginmanager = components.classes["@mozilla.org/login-manager;1"].\
                            getService(components.interfaces.nsILoginManager)
        old_logins = {}
        
        all_logins = loginmanager.getAllLogins()
        # Note: all_logins can be None - bug 88772.
        if all_logins:
            for old_login in all_logins:
                old_login.QueryInterface(components.interfaces.nsILoginInfo)
                serverinfo = koServerInfo()
                try:
                    serverinfo.initFromLoginInfo(old_login)
                except BadServerInfoException:
                    # Ignore non Komodo server entries.
                    continue
                guid = old_login.QueryInterface(components.interfaces.\
                                                nsILoginMetaInfo).guid
                old_logins[guid] = old_login
        for serverinfo in serverinfo_list:
            new_login = serverinfo.generateLoginInfo()
            if not new_login.password:
                # Hack to workaround the login manager not accepting empty
                # passwords.
                new_login.password = self.EMPTY_PASSWORD_SENTINEL
            guid = serverinfo.guid
            if not guid in old_logins:
                loginmanager.addLogin(new_login)
            else:
                old_login = old_logins.pop(guid)
                if not old_login.equals(new_login):
                    loginmanager.modifyLogin(old_login, new_login)
                    
        for old_login in old_logins.itervalues():
            loginmanager.removeLogin(old_login)
            
        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                      getService(components.interfaces.nsIObserverService)
        obsSvc.notifyObservers(None, "server-preferences-changed", "")

