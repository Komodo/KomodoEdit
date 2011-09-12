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

# An implementation of a ftp file objects
#
# Contributors:
# * Shane Caraveo
# * Todd Whiteman

import os
import socket
import ssl
import time
import ftplib
import logging
from cStringIO import StringIO

# XPCOM imports
from xpcom import components, COMException, ServerException, nsError

# Komodo imports
import URIlib
import remotefilelib


# logging objects
log_koFTP = logging.getLogger('koFTPConnection')
#log_koFTP.setLevel(logging.DEBUG)
log_koFTPS = logging.getLogger('koFTPSConnection')
#log_koFTPS.setLevel(logging.DEBUG)

log_FTPFile = logging.getLogger('FTPFile')
#log_FTPFile.setLevel(logging.DEBUG)


# Connection handler
class koFTP(ftplib.FTP):

    #
    # We are using the code from ftplib.py, but adding an optional timeout
    # parameter, which is passed in through the connect() method.
    #
    # We need to do this as there is no way to timeout the socket connect
    # method below using the python ftplib.FTP module. See bug:
    # http://bugs.activestate.com/show_bug.cgi?id=47047
    #
    # Drawbacks: If ftplib.FTP changes it's implementation, we need to update
    # the connect() method below to correstpond.
    #
    def connect(self, host='', port=0, timeout=None):
        '''Connect to host.  Arguments are:
        - host: hostname to connect to (string, default previous host)
        - port: port to connect to (integer, default previous port)
        - timeout: socket timeout in seconds (float)'''
        if host: self.host = host
        if port: self.port = port
        msg = "getaddrinfo returns an empty list"
        af = None
        for af_type in (socket.AF_UNSPEC, socket.AF_INET):
            try:
                address_info = socket.getaddrinfo(self.host, self.port, af_type, socket.SOCK_STREAM)
            except socket.error, msg:
                log_koFTP.warn("socket.getaddrinfo raised exception: %r", msg)
                continue
            for res in address_info:
                af, socktype, proto, canonname, sa = res
                try:
                    self.sock = socket.socket(af, socktype, proto)
                    # Start: added for Komodo socket timeouts
                    if timeout is not None:
                        self.sock.settimeout(timeout)
                    # End
                    self.sock.connect(sa)
                except socket.error, msg:
                    if self.sock:
                        self.sock.close()
                    self.sock = None
                    continue
                break
            if self.sock:
                break
        if not self.sock:
            raise socket.error, msg
        self.af = af
        self.file = self.sock.makefile('rb')
        self.welcome = self.getresp()
        return self.welcome


class koFTPConnection(remotefilelib.koRFConnection):
    _com_interfaces_ = [components.interfaces.koIRemoteConnection]
    _reg_desc_ = "Komodo FTP Connection"
    _reg_contractid_ = "@activestate.com/koFTPConnection;1"
    _reg_clsid_ = "{76A0956E-044C-45fc-BD9B-07BC5C659E4A}"

    _FTPExceptions = ftplib.all_errors

    def __init__(self):
        remotefilelib.koRFConnection.__init__(self)
        self.log = log_koFTP
        self.port = remotefilelib.koRFProtocolDefaultPort['ftp']
        self.protocol = 'ftp'
        self._connection = None
        self._currentDirectory = ""
        self._use_ls_lad = 1
        self._homedirectory = None

    def __del__(self):
        try:
            self.log.debug("__del__: koFTP deleted")
            if self._connection and self._connection.sock:
                self._connection.quit()
        except self._FTPExceptions, e:
            #self.log.error("FTP CLOSE ERROR: %s", e)
            pass

    #def _fixPath(self, path):
        # Now in parent class, remotefilelib.py

    def _setConnectionMode(self):
        # Most servers accept passive mode, so we'll try that first
        # Note: passive is enabled by default in Python 2.1 and above
        info = []
        try:
            if self.passive:
                self._connection.makepasv()
        except self._FTPExceptions, e:
            # Note: Sometimes e.args is an empty tuple, thus we use the "and/or"
            msg = e.args and e.args[-1] or "Setting passive mode failed"
            self.log.info("_setConnectionMode: Unable to set passive mode, exception: %s", msg)
            error_code = msg[:3]
            if error_code == "550":
                self.log.info("_setConnectionMode: Trying active mode")
                self._connection.set_pasv(False)

    def do_openSocket(self):
        """Open the FTP connection socket to the remote site."""
        self._setLastError("")
        # open the connection
        try:
            self._connection = koFTP()
            self._connection.set_pasv(self.passive)
            self._connection.connect(self.server, self.port,
                                     self._socket_timeout)
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_authenticateWithAgent(self):
        """Not used for ftp"""
        return 0

    # Authenicate to the remote FTP server using the supplied username/password
    # Return 1 on successful authentication
    # Return 0 when username/password is incorrect
    # Raise exception otherwise
    def do_authenticateWithPassword(self):
        # attempt authentication
        try:
            self._connection.login(self.username, self.password)
            self._setConnectionMode()
            self.log.debug("do_authenticateWithPassword: login successful")
            return 1
        except self._FTPExceptions, e:
            self._lasterror = e.args and e.args[-1] or "Login failed"
            if self._lasterror[:3] == "530":
                # username/password error, unset password so we can prompt again
                self.log.debug("do_authenticateWithPassword: Invalid username/password")
            else:
                self._raiseWithException(e)
        return 0

    def _NOOP(self):
        try:
            self.log.debug("Sending NOOP");
            self._connection.voidcmd('NOOP')
        except self._FTPExceptions, e:
            # Note: Sometimes e.args is an empty tuple, thus we do this
            self._lasterror = e.args and e.args[-1] or ""
            self.log.info("FTP NOOP ERROR: %s", self._lasterror)
            raise

    def do_verifyConnected(self):
        """Verify that we are connected to the remote server"""
        try:
            if not self._connection:
                self.open(self.server, self.port, self.username, self.password, "", self.passive)
            else:
                # Periodically check that the connection is still alive, bug
                # 85050.
                current_time = time.time()
                if (current_time - self._last_verified_time) >= 30:
                    self.log.debug("Checking that the ftp connection is alive")
                    self._NOOP()
                    self._last_verified_time = current_time
        except Exception, e:
            if isinstance(e, socket.timeout):
                self._raiseWithException(e)
            else:
                if not isinstance(e, self._FTPExceptions):
                    self.log.exception(e, "Unexpected FTP exception")
                # connection lost, reconnect if possible
                self.log.info("Re-opening the ftp connection because it was closed")
                self.open(self.server, self.port, self.username, self.password, "", self.passive)

    def do_close(self):
        """Close the FTP connection"""
        self._setLastError("")
        try:
            self.log.debug("do_close: Closing FTP connection")
            if self._connection:
                self._connection.quit()
        except Exception, e:
            self._setLastError(e.args and e.args[-1] or "Connection close failed")
            self.log.error("FTP CLOSE ERROR: %s", self._lasterror)
            pass
        self._connection = None

    #def _createBaseDirectory(self, dirname):
        # Now in parent class, remotefilelib.py

    #def __createRFInfoFromListing(self, dirname, fileinfo):
        # Now in parent class, remotefilelib.py

    #def _createRFInfo(self, path, fileinfo=None):
        # Now in parent class, remotefilelib.py

    #def _followSymlink(self, rfinfo):
        # Now in parent class, remotefilelib.py

    def _createRFInfoFromPath(self, path):
        pwd = None
        try:
            info = []
            #dirname = os.path.dirname(path)
            dirname = self.do_getParentPath(path)
            basename = os.path.basename(path)
            self.log.debug("_createRFInfoFromPath: '%s'", path)
            # We have two ways of doing this
            # 1 - Using LIST -lad, which just displays the directory
            # 1 - Note: Some servers may not use this option (I.e. windows)
            # 1 - Note: Also, some quoted paths may not work with this
            if self._use_ls_lad:
                try:
                    self._connection.retrlines("LIST -lad %s" % path, info.append)
                    if len(info) == 1:
                        rf_pathinfo = self._createRFInfoFromListing(dirname, info[0])
                        if rf_pathinfo and rf_pathinfo.getFilename() == basename:
                            return rf_pathinfo
                except self._FTPExceptions, e:
                    if isinstance(e, socket.timeout):
                        raise
                    msg = e.args and e.args[-1] or "Retrieval of listing failed"
                    if msg[:3] == "550":
                        # This path does not exist then
                        # XXX - Note: This could be an encoding error.
                        self.log.debug("_createRFInfoFromPath: error: %s on path '%s'", msg, path)
                        return None
                    self._use_ls_lad = 0
                    self.log.info("LIST -lad failed: %s", msg)
                    self.log.debug("_createRFInfoFromPath: Not using 'LIST -lad' any further")
    
            # 2 - Do a LIST -al of the parent directory and find the child in the list
            pwd = self._currentDirectory
            if not self.do_changeDirectory(dirname, doRaiseException=False):
                return None
            info = []
            self._connection.retrlines("LIST -la", info.append)
            for filelisting in info:
                foundPos = -1
                encoding = ''
                try:
                    foundPos = filelisting.find(basename)
                except UnicodeDecodeError:
                    # Try encoding it with komodo's unicode encoding service
                    try:
                        filelisting, encoding, bom = self._encodingSvc.getUnicodeEncodedString(filelisting)
                        foundPos = filelisting.find(basename)
                        self.log.debug("Had to decode filelisting(%s): %s" % (encoding, filelisting))
                    except Exception, e:
                        # No go, we assume it was not found in this string
                        self.log.debug("Error decoding filelisting: %s" % (e))
                        self.log.debug("filelisting is: %s" % (filelisting))
                if foundPos > 0:
                    rf_pathinfo = self._createRFInfoFromListing(dirname, filelisting)
                    if rf_pathinfo and rf_pathinfo.getFilename() == basename:
                        if encoding:
                            rf_pathinfo.encoding = encoding
                        return rf_pathinfo
        finally:
            if pwd:
                self.do_changeDirectory(pwd)
        return None

    def do_getPathInfo(self, path):
        try:
            # Get the remote file details
            try:
                rf_info = self._createRFInfo(path)
            except socket.timeout, e:
                self._raiseWithException(e)
            except Exception, e:
                self.log.error("Unable to get path info for: %s", path)
                self.log.debug("Error: %s: %s", e, e.args)
                return None
            if rf_info:
                return rf_info

            # Last chance, might be a basedir
            if path in ('/', '~', '~/'):
                self.log.debug("do_getPathInfo: Creating basedir for '%s'", path)
                return self._createBaseDirectory(path)

            # It may exist, but is somehow hidden (like a virtual folder on
            # Microsoft's IIS FTP server), see bug:
            # http://bugs.activestate.com/show_bug.cgi?id=69434
            # So, we try to change to the directory anyway and if that works,
            # then the path must be valid.
            pwd = self._currentDirectory
            if self.do_changeDirectory(path, doRaiseException=False):
                self.log.debug("do_getPathInfo: Found hidden directory: %r", path)
                # change back to where we came from
                self.do_changeDirectory(pwd, doRaiseException=False)
                # Create the remote file information for this hidden directory
                rf = components.classes['@activestate.com/koRemoteFileInfo;1'].\
                            createInstance(components.interfaces.koIRemoteFileInfo)
                dirname, name = os.path.split(path)
                if not name:
                    name = dirname
                rf.initFromStats(dirname, name, '0', '', '',
                                 self.basicModeForBaseDir, 0)
                return rf

            # Does not exist
            self.log.debug("do_getPathInfo: Path does not exist '%s'", path)
            return None
        except self._FTPExceptions, e:
            self._lasterror = e.args and e.args[-1] or "Retrieval of listing failed"
            if self._lasterror[:3] == "550":
                # This path does not exist then
                self.log.debug("do_getPathInfo: error: %s on path '%s'", self._lasterror, path)
                return None
            else:
                self._raiseWithException(e)

    def do_getDirectoryList(self, path, dir_rfinfo):
        dirinfo = []
        pwd = None
        try:
            try:
                info = []
                pwd = self._currentDirectory
                if not self.do_changeDirectory(path, doRaiseException=False):
                    return None
                self._connection.dir("-la", info.append)
                for fileinfo in info:
                    self.log.debug("do_getDirectoryList: raw list item: %s", fileinfo)
                    try:
                        rf_fileinfo = self._createRFInfo(path, fileinfo)
                        if rf_fileinfo and rf_fileinfo.getFilename() not in (".", ".."):
                            dirinfo.append(rf_fileinfo)
                    except socket.timeout, e:
                        self._raiseWithException(e)
                    except Exception, e:
                        self.log.error("Unable to create a listing element for: %s", fileinfo)
                        self.log.debug("Error: %s: %s", e, e.args)
            except self._FTPExceptions, e:
                self._lasterror = e.args and e.args[-1] or "Directory listing failed"
                if self._lasterror[:3] == "550":
                    # This path does not exist then
                    self.log.debug("do_getDirectoryList: error: %s on path '%s'", self._lasterror, path)
                    return None
                else:
                    self._raiseWithException(e)
        finally:
            if pwd:
                self.do_changeDirectory(pwd)
        return dirinfo

    def do_rename(self, oldName, newName):
        try:
            self._connection.rename(self._fixPath(oldName), self._fixPath(newName))
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_removeFile(self, name):
        try:
            self._connection.delete(self._fixPath(name))
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_changeDirectory(self, path, doRaiseException=True):
        try:
            self._connection.cwd(path)
            self._currentDirectory = path
            return 1
        except self._FTPExceptions, e:
            if doRaiseException:
                self._raiseWithException(e)
            else:
                return 0

    def do_currentDirectory(self):
        try:
            path = self._connection.pwd()
            self.log.debug("do_currentDirectory: pwd '%s'",path)
            return path
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_getHomeDirectory(self):
        pwd = None
        try:
            try:
                if self._homedirectory is None:
                    pwd = self._currentDirectory
                    # Some ftp servers do not support tilde as home directories,
                    # so we don't raise an exception if the changeDir fails.
                    self.do_changeDirectory("~", doRaiseException=False)
                    self._homedirectory = self._connection.pwd()
                    self.log.debug("do_getHomeDirectory: path '%s'", self._homedirectory)
                return self._homedirectory
            except self._FTPExceptions, e:
                self._setLastError(e.args and e.args[-1] or "Setting home directory failed")
                self.log.warn("FTP HOMEDIR ERROR: %s", self._lasterror)
        finally:
            if pwd:
                self.do_changeDirectory(pwd)
        return "/"

    def do_getParentPath(self, path):
        try:
            norm_path = self._fixPath(path)
            parent_path = os.path.dirname(norm_path)
            if not parent_path:
                parent_path = "/"
            self.log.debug("do_getParentPath: '%s' -> '%s'", path, parent_path)
            return parent_path
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_removeDirectory(self, name):
        try:
            self._connection.rmd(self._fixPath(name))
        except self._FTPExceptions, e:
            self._raiseServerException(e.args and e.args[-1] or "Directory removal failed")

    def do_createDirectory(self, name, permissions):
        try:
            self._connection.mkd(self._fixPath(name))
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_createFile(self, name, permissions):
        try:
            # Treat permissions as an octet value, we need to convert to integer
            # I.e. 755 as octet, the integer value of this is 493
            # permissions = int(str(permissions), 8)
            name = self._fixPath(name)
            self.log.debug("do_createFile: Creating file though ftp: '%s'", name)
            self.do_writeFile(name, '')
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def do_chmod(self, filepath, permissions):
        try:
            chmod_cmd = "SITE CHMOD %s %s" % (oct(permissions),
                                              self._fixPath(filepath))
            self._connection.sendcmd(chmod_cmd)
        except self._FTPExceptions, e:
            self._raiseWithException(e)

    def _read_cb(self, block):
        #print "read %r bytes"  % (len(block))
        self._filedata.write(block)

    def do_readFile(self, filename):
        self._filedata = StringIO()
        try:
            # We want binary
            self._connection.sendcmd('TYPE I')
            if self._filedata.tell() == 0:
                # retreive the file
                self._connection.retrbinary("RETR "+self._fixPath(filename), self._read_cb)
                self._filedata.seek(0,0)
            data = self._filedata.getvalue()
            # reset _filedata
        except self._FTPExceptions, e:
            self._filedata.close()
            del self._filedata
            self._raiseWithException(e)
        self._filedata.close()
        del self._filedata
        return data

    def do_writeFile(self, filename, data):
        filedata = StringIO()
        filedata.write(data)
        filedata.seek(0,0)
        self._setLastError("")
        try:
            self._connection.storbinary("STOR "+self._fixPath(filename), filedata)
        except self._FTPExceptions, e:
            filedata.close()
            self._raiseWithException(e)
        filedata.close()

#############################################################################
#                               FTPS support                                #
#############################################################################
#
# Example using M2Crypto, not used, as we can do the same without M2Crypto
# (see below)
#
#from M2Crypto.ftpslib import FTP_TLS
#class koFTP_TLS(FTP_TLS):
#    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
#        """Retrieve data in binary mode.
#
#        `cmd' is a RETR command.  `callback' is a callback function is
#        called for each block.  No more than `blocksize' number of
#        bytes will be read from the socket.  Optional `rest' is passed
#        to transfercmd().
#
#        A new port is created for you.  Return the response code.
#        """
#        self.voidcmd('TYPE I')
#        conn, size = self.ntransfercmd(cmd, rest)
#        print "size: %r" % (size)
#        while size > 0:
#            readsize = min(blocksize, size)
#            data = conn.recv(readsize)
#            if not data:
#                break
#            callback(data)
#            size -= len(data)
#        del conn
#        #conn.close()
#        print "Closed conn"
#        return self.voidresp()
#
#    def storbinary(self, cmd, fp, blocksize=8192):
#        '''Store a file in binary mode.'''
#        self.voidcmd('TYPE I')
#        conn, size = self.ntransfercmd(cmd)
#        print "size: %r" % (size)
#        while 1:
#            buf = fp.read(blocksize)
#            print "Read in buf (%d) bytes" % (len(buf))
#            if not buf: break
#            conn.sendall(buf)
#            print "sendall buf"
#        del conn
#        #conn.close()
#        print "Closed conn"
#        #result = self.voidcmd('NOOP')
#        result = self.voidresp()
#        print "Voidresp: %r" % (result)
#        return result


# URI handler
class FTPSURI:
    _com_interfaces_ = components.interfaces.nsIProtocolHandler
    _reg_contractid_ = '@mozilla.org/network/protocol;1?name=ftps'
    _reg_clsid_ = '{64f2ef13-5873-40dc-bcd2-b29978ed32df}'
    _reg_desc_ = "FTPS handler"

    scheme = "ftps"
    defaultPort = 21
    protocolFlags = components.interfaces.nsIProtocolHandler.URI_STD

    def __init__(self):
        pass

    def newURI(self, aSpec, aOriginCharset, aBaseURI):
        url = components.classes["@mozilla.org/network/standard-url;1"].\
                 createInstance(components.interfaces.nsIStandardURL)
        url.init(components.interfaces.nsIStandardURL.URLTYPE_AUTHORITY,
                 self.defaultPort, aSpec, aOriginCharset, aBaseURI)
        return url.QueryInterface(components.interfaces.nsIURI)

    def newChannel(self, aURI):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    def allowPort(self, port, scheme):
        return True


#
# Komodo FTPS class
# Requires ActivePython build with ssl support (which it now does)
# http://bugs.activestate.com/show_bug.cgi?id=50207
#
class koFTPS(koFTP):
    def __init__(self, host=''):
        """Initialise the client."""
        koFTP.__init__(self)
        self.prot = 0
        self.auth_mode = None

    #
    # There are a number of ways to perform ftp over ssl, we only cover one of
    # the three possible ways as described in (the other two are deprecated):
    # http://www.ford-hutchinson.com/~fh-1-pfh/ftps-ext.html
    #
    # This is:
    #   1. "AUTH TLS", where the connection is made and then an AUTH TLS
    #      request is sent, upon success the client can then choose if it
    #      then wants the data to be also sent over ssl (prot_p), or wants
    #      the data sent in clear text (prot_c).
    #

    def auth_tls(self):
        """Secure the control connection per AUTH TLS, aka AUTH TLS-C."""
        self.voidcmd('AUTH TLS')
        self.sock = ssl.wrap_socket(self.sock)
        self.file = self.sock.makefile('rb')
        self.auth_mode = "TLS"

    def prot_p(self):
        """Set up secure data connection."""
        self.voidcmd('PBSZ 0')
        self.voidcmd('PROT P')
        self.prot = 1

    def prot_c(self):
        """Set up data connection in the clear."""
        self.voidcmd('PROT C')
        self.prot = 0

    def ntransfercmd(self, cmd, rest=None):
        """Initiate a data transfer."""
        conn, size = koFTP.ntransfercmd(self, cmd, rest)
        if self.prot:
            conn = ssl.wrap_socket(conn)
        return conn, size

    def _readUnknownDataSize(self, conn, callback, blocksize=8192):
        """Read data until no more data arrives or the connection is closed."""
        try:
            while 1:
                data = conn.recv(blocksize)
                #print "  received: %r" % (data, )
                if not data:
                    break
                callback(data)
        except ftplib.all_errors:
            # Ignore this error, this should be the connection being closed.
            pass

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        """Retrieve data in binary mode.

        `cmd' is a RETR command.  `callback' is a callback function is
        called for each block.  No more than `blocksize' number of
        bytes will be read from the socket.  Optional `rest' is passed
        to transfercmd().

        A new port is created for you.  Return the response code.
        """
        self.voidcmd('TYPE I')
        #print "retrbinary:: cmd: %r, rest: %r" % (cmd, rest)
        conn, size = self.ntransfercmd(cmd, rest)
        if size is None:
            # The ntransfercmd() call can return a size of None when the
            # size is undetermined. Fixes bug:
            #   http://bugs.activestate.com/show_bug.cgi?id=72068
            self._readUnknownDataSize(conn, callback, blocksize)
        else:
            #print "  size: %r" % (size)
            while size > 0:
                readsize = min(blocksize, size)
                data = conn.recv(readsize)
                #print "  received: %r" % (data, )
                if not data:
                    break
                callback(data)
                size -= len(data)
        #-- Hack start
        # Expected usage
        #conn.close()
        # Hack for python ssl, see bug:
        # http://bugs.activestate.com/show_bug.cgi?id=50217
        conn._sock.shutdown(2)
        del conn
        #-- Hack end
        #print "Closed conn"
        return self.voidresp()

    def retrlines(self, cmd, callback = None):
        '''Retrieve data in line mode.
        The argument is a RETR or LIST command.
        The callback function (2nd argument) is called for each line,
        with trailing CRLF stripped.  This creates a new port for you.
        print_line() is the default callback.'''
        if callback is None: callback = print_line
        resp = self.sendcmd('TYPE A')
        conn = self.transfercmd(cmd)
        fp = conn.makefile('rb')
        while 1:
            line = fp.readline()
            if self.debugging > 2: print '*retr*', repr(line)
            if not line:
                break
            if line[-2:] == ftplib.CRLF:
                line = line[:-2]
            elif line[-1:] == '\n':
                line = line[:-1]
            callback(line)
        fp.close()
        #-- Hack start
        # Expected usage
        #conn.close()
        # Hack for python ssl, see bug:
        # http://bugs.activestate.com/show_bug.cgi?id=50217
        conn._sock.shutdown(2)
        del conn
        #-- Hack end
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192):
        '''Store a file in binary mode.'''
        self.voidcmd('TYPE I')
        conn, size = self.ntransfercmd(cmd)
        #print "size: %r" % (size)
        while 1:
            buf = fp.read(blocksize)
            #print "Read in buf (%d) bytes" % (len(buf))
            if not buf: break
            conn.sendall(buf)
            #print "sendall buf"
        #-- Hack start
        # Expected usage
        #conn.close()
        # Hack for python ssl, see bug:
        # http://bugs.activestate.com/show_bug.cgi?id=50217
        conn._sock.shutdown(2)
        del conn
        #-- Hack end
        #print "Closed conn"
        return self.voidresp()


class koFTPSConnection(koFTPConnection):
    _com_interfaces_ = [components.interfaces.koIRemoteConnection]
    _reg_desc_ = "Komodo FTPS Connection"
    _reg_contractid_ = "@activestate.com/koFTPSConnection;1"
    _reg_clsid_ = "{1835146c-5b54-4519-94a0-8a02a7262691}"

    def __init__(self):
        koFTPConnection.__init__(self)
        self.log = log_koFTPS
        self.port = remotefilelib.koRFProtocolDefaultPort['ftps']
        self.protocol = 'ftps'

    def do_openSocket(self):
        """Open the FTP connection socket to the remote site."""
        # open the connection
        self._setLastError("")
        try:
            #self._connection = koFTP_TLS()     # Using M2Crypto
            self._connection = koFTPS()        # Using python ssl
            self._connection.connect(self.server, self.port,
                                     self._socket_timeout)
        except self._FTPExceptions, e:
            self._raiseServerException(e.args and e.args[-1] or "Connection failed")

        # Now try to request for authorization over SSL.
        try:
            # auth_tls throws exception when tls authentication not supported
            self._connection.auth_tls()
        except self._FTPExceptions, e:
            self._raiseServerException(e.args and e.args[-1] or "Connection failed")

    def _setConnectionMode(self):
        koFTPConnection._setConnectionMode(self)
        try:
            # Try and force encryption of all data transfers
            self._connection.prot_p()
            self.log.debug("TLS data encryption setting was successful.")
        except self._FTPExceptions, e:
            self.log.warn("TLS data encryption failed, data will be sent and received in clear text.")
            # Fall back to clear text transfer of data
            self._connection.prot_c()


# FTP File support
class FTPFile:
    _com_interfaces_ = [components.interfaces.koIFTPFile]
    _reg_desc_ = "Komodo FTP File"
    _reg_contractid_ = "@activestate.com/koFTPFile;1"
    _reg_clsid_ = "{010656B6-E830-45ae-B7D9-F22C1E4AFDEC}"

    def __init__(self):
        import warnings
        warnings.warn("'koIFTPFile' is deprecated, use koIFileEx instead.",
                      DeprecationWarning)
        self.log = log_FTPFile
        #self.filename = ""
        #self.ftpfile = None
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                            .getService(components.interfaces.koILastErrorService)
        self.rfinfo = None
        self.log.debug("__init__")

    def _getRemoteConnection(self):
        self.log.debug("_getRemoteConnection()")
        RFService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
                    getService(components.interfaces.koIRemoteConnectionService)
        return RFService.getConnectionUsingUri(self._fulluri)
            
    def init(self, url, mode="r"):
        self.log.debug("init: uri: '%s'", url)
        self.mode = mode
        self._fulluri = url
        self._uriparse = URIlib.URIParser(url)

        # make the connection to the remote site
        try:
            conn = self._getRemoteConnection()
        except COMException, ex:
            # koIRemoteConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))
        
        # Check that the file exists
        self.rfinfo = conn.list(self._uriparse.path, 0)

    def refreshStats(self):
        self.log.debug("refreshStats: Refreshing rfinfo for '%s'", self._uriparse.path)
        try:
            conn = self._getRemoteConnection()
            self.rfinfo = conn.list(self._uriparse.path, 1)
        except COMException, ex:
            # koIRemoteConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))

    def read(self, n = -1):
        self.log.debug("read: size %d", n)
        try:
            conn = self._getRemoteConnection()
            return conn.readFile(self._uriparse.path)
        except COMException, ex:
            # koIRemoteConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))

    def write(self, data):
        self.log.debug("write: size %d", len(data))
        try:
            conn = self._getRemoteConnection()
            conn.writeFile(self._uriparse.path, data)
        except COMException, ex:
            # koIRemoteConnection will already setLastError on failure so don't
            # need to do it again. The only reason we catch it to just
            # re-raise it is because PyXPCOM complains on stderr if a
            # COMException passes out of the Python run-time.
            raise ServerException(ex.errno, str(ex))

    def close(self):
        pass

    def get_isReadable(self):
        #if self.ftpfile:
        #    return self.ftpfile.isReadable()
        #self.log.warn("no ftpfile available for reading!")
        #return 0
        return 1

    def get_isWritable(self):
        #if self.ftpfile:
        #    return self.ftpfile.isWritable()
        #self.log.warn("no ftpfile was available for writing!")
        #return 0
        return 1
