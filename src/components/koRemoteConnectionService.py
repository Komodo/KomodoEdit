#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# The implementation of the Komodo LastError service.

import socket
import threading
from xpcom import components, ServerException, COMException, nsError
from xpcom.client import WeakReference
import logging, types
import URIlib
import remotefilelib

log = logging.getLogger('koRemoteConnectionService')
#log.setLevel(logging.DEBUG)

#---- PyXPCOM component implementation

# The underscore names are private, and should only be used internally
# All underscore names require locking, which should happen through the
# the use of the exposed (non-underscore) functions.
class koRemoteConnectionService:
    _com_interfaces_ = [components.interfaces.koIRemoteConnectionService]
    _reg_desc_ = "Remote Connection Service"
    _reg_clsid_ = "{c12f592b-11a2-4172-85c2-02d87ac56887}"
    _reg_contractid_ = "@activestate.com/koRemoteConnectionService;1"

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
    def _getConnection(self, protocol, server, port, username, password, path):
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
        if not port:
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
            createInstance(components.interfaces.koIFTPConnection)
        log.debug("getConnection: Opening %s %s@%s:%r", protocol, username, server, port)
        try:
            c.open(server, port, username, password, path)
            self._connections[conn_key] = WeakReference(c)
            # Update sessionkey to contain any changes to the username, which
            # can happen if/when prompted for a username/password. Fix for bug:
            # http://bugs.activestate.com/show_bug.cgi?id=65529
            sessionkey = "%s:%s:%s" % (server, port, c.username)
            self._saveSessionInfo(sessionkey, [c.username, c.password])
            return c
        except COMException, ex:
            # koIFTPConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))

    # We have the lock already
    def _getConnectionUsingUri(self, uri):
        server_alias = ''
        protocol = ''
        hostname = ''
        port = 0
        username = ''
        password = ''
        path = ''

        uriparse = URIlib.URIParser(uri)
        if uriparse.scheme not in URIlib.RemoteURISchemeTypes:
            self._lasterror = "Unhandled protocol type: %s" % (protocol)
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, self._lasterror)
            raise ServerException(nsError.NS_ERROR_FAILURE, self._lasterror)

        if uriparse.server:
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
                path     = server_prefs[4]
                username = server_prefs[5]
                password = server_prefs[6]
            else:
                log.debug("uri host info: %s", uriparse.server)
                serveruri = URIlib.URIServerParser(uriparse.server)
                if serveruri.username:  username   = serveruri.username
                if serveruri.password:  password   = serveruri.password
                if serveruri.hostname:  hostname   = serveruri.hostname
                if serveruri.port:      port       = serveruri.port

        protocol = uriparse.scheme
        # We want the port as an integer
        try:
            if not port: port = 0
            elif type(port) != types.IntType: port = int(port)
        except ValueError:
            log.debug("Invalid port number: %s", port)
            port = 0

        # Use the URI path
        if uriparse.path:
            path = uriparse.path

        # Now we have all the info, lets go make the connection
        connection = self._getConnection(protocol, hostname, port, username,
                                         password, path);
        if connection:
            # Set the alias used to get the connection (if there was one)
            connection.alias = server_alias;
        return connection

    # Return the server prefs for the given server alias
    # We have the lock already
    def _getServerPrefSettings(self, server_alias):
        passwordmanager = components.classes["@mozilla.org/passwordmanager;1"].getService(components.interfaces.nsIPasswordManager);
        e = passwordmanager.enumerator
        while e.hasMoreElements():
            # server is nsIPassword, which has host, user and password members
            server = e.getNext().QueryInterface(components.interfaces.nsIPassword)
            #print "    %s [%s,%s] " % (server.host, server.user, server.password)
            info = server.host.split(':')
            if server_alias == info[1]:
                # we found our server, return the info
                return info + [server.user, server.password]
        return None

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
            server = "%s@%s" % (connection.username, connection.server)
            port = connection.port
            if port != remotefilelib.koRFProtocolDefaultPort[protocol]:
                server += ":%d" % (port)
        # Remove base slash, it's added when we make the uri
        if path and path[0] == "/":
            path = path[1:]

        return "%s://%s/%s" % (protocol, server, path)

    # Return a connection object for the given parameters
    def getConnection(self, protocol, server, port, username, password, path):
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
            return self._getConnection(protocol, server, port, username, password, path)
        finally:
            self._lock.release()

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

    # Return the server prefs for the given server alias
    def getServerPrefSettings(self, server_alias):
        self._lock.acquire()
        try:
            return self._getServerPrefSettings(server_alias)
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
