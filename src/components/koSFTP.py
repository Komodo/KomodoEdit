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

# An implementation of a secure ftp file object for Komodo
#
# This uses "paramiko", a pure python implementation of the 
# SSH2 protocol, of which, we are using the SFTP component.
# http://www.lag.net/paramiko/
#
# Contributors:
# * Todd Whiteman

import os
import socket
import logging

from xpcom import components, ServerException, nsError

# remote file library
import remotefilelib
# needed for SFTP
import paramiko


log = logging.getLogger('koSFTPConnection')
#log.setLevel(logging.DEBUG)


# URI handler
class SFTPURI:
    _com_interfaces_ = components.interfaces.nsIProtocolHandler
    _reg_contractid_ = '@mozilla.org/network/protocol;1?name=sftp'
    _reg_clsid_ = '{b7b16573-c158-4546-91be-f4324de9dcfb}'
    _reg_desc_ = "SFTP handler"

    scheme = "sftp"
    defaultPort = 22
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


# Connection handler
class koSFTPConnection(remotefilelib.koRemoteSSH):
    _com_interfaces_ = [components.interfaces.koISSHConnection]
    _reg_desc_ = "Komodo SFTP Connection"
    _reg_contractid_ = "@activestate.com/koSFTPConnection;1"
    _reg_clsid_ = "{0a29b026-b0cb-4316-a0ea-23f890c7e8be}"

    # SFTP Exceptions caught and handled
    _SFTPExceptions = (paramiko.SFTPError, IOError, socket.timeout)

    def __init__(self):
        remotefilelib.koRemoteSSH.__init__(self)
        self.log = log
        self.log.debug('__init__()')
        self.protocol = 'sftp'
        self.port = remotefilelib.koRFProtocolDefaultPort[self.protocol]
        self._sftp = None
        # Private, set to the first directory where we log into
        # This is because sftp does not support "~" names.
        self._homedirectory = None

    def __del__(self):
        # Ensure we are closed properly
        self.do_close()
        if self._sftp:
            del self._sftp
        if self._connection:
            del self._connection
        self.log.debug("__del__: koSFTP object deleted")
        del self.log

    def _fixPath(self, path):
        """Hack for SFTP because
        1 - sftp does not understand tilde directory names
        2 - sometimes the tilde pathname is preceeded with a /
        3 - need to remove any trailing forward slashes
        """
        newPath = None
        if not path or path == "~":
            newPath = "./"
        elif path[:2] == "/~":
            newPath = "." + path[2:]
        elif path[0] == "~":
            if path[:2] == '~/':
                newPath = "." + path[1:]
            else:
                newPath = "./" + path[1:]
        if newPath:
            # Remove any trailing forward slash
            if len(newPath) > 1 and newPath[-1] == "/":
                newPath = newPath[:-1]
            self.log.debug("_fixPath: '%s' -> '%s'", path, newPath)
            return newPath
        elif len(path) > 1 and path[-1] == "/":
            # Remove any trailing forward slash
            newPath = path[:-1]
            self.log.debug("_fixPath: %s -> %s", path, newPath)
            return newPath
        return path

    def _setupClientSFTP(self):
        """Get the client SFTP object for access to the remote site."""
        try:
            self._sftp = paramiko.SFTP.from_transport(self._connection)
            # _sftp.sock in this case is actually a paramiko.Channel object
            self._sftp.sock.settimeout(self._socket_timeout)
            self._homedirectory = self.do_currentDirectory()
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    # Authenicate to the remote SSH server using the supplied username/password
    # Return 1 on successful authentication
    # Return 0 when agent fails to authorize
    # Raise exception on error
    def do_authenticateWithAgent(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithAgent(self) == 1:
            self._setupClientSFTP()
            return 1
        return 0

    # Authenicate to the remote SSH server using the supplied private key file.
    # Return 1 on successful authentication
    # Return 0 when agent fails to authorize
    # Raise exception on error
    def do_authenticateWithPrivateKey(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPrivateKey(self) == 1:
            self._setupClientSFTP()
            return 1
        return 0

    # Authenicate to the remote SSH server using the supplied private key file.
    # Return 1 on successful authentication
    # Return 0 when agent fails to authorize
    # Raise exception on error
    def do_authenticateWithPrivateKey(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPrivateKey(self) == 1:
            self._setupClientSFTP()
            return 1
        return 0

    # Authenicate to the remote SSH server using the supplied private key file.
    # Return 1 on successful authentication
    # Return 0 when agent fails to authorize
    # Raise exception on error
    def do_authenticateWithPrivateKey(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPrivateKey(self) == 1:
            self._setupClientSFTP()
            return 1
        return 0

    # Return 1 on successful authentication
    # Return 0 when username/password is incorrect
    # Raise exception on error
    def do_authenticateWithPassword(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPassword(self) == 1:
            self._setupClientSFTP()
            return 1
        return 0

    # remotefilelib.koRemoteSSH handles these methods.
    #def do_openSocket(self):
    #def do_close(self):
    #def do_verifyConnected(self):

    def _createRFInfoFromStat(self, dirname, filename, fileinfo):
        """Create a koRemoteFileInfo class object given the path and paramiko stats"""
        rf = components.classes['@activestate.com/koRemoteFileInfo;1'].\
                    createInstance(components.interfaces.koIRemoteFileInfo)
        try:
            rf.initFromStats(dirname, filename, str(fileinfo.st_size),
                             str(fileinfo.st_uid), str(fileinfo.st_gid),
                             fileinfo.st_mode, fileinfo.st_mtime)
        except UnicodeDecodeError:
            # Need to encode the filename then
            try:
                filename, rf.encoding, bom = self._encodingSvc.getUnicodeEncodedString(filename)
                self.log.debug("Had to decode filename(%s): %s" % (rf.encoding, filename))
                rf.initFromStats(dirname, filename, str(fileinfo.st_size),
                                 str(fileinfo.st_uid), str(fileinfo.st_gid),
                                 fileinfo.st_mode, fileinfo.st_mtime)
            except Exception, e:
                # No go, we assume it was not found in this string
                self.log.debug("Error '%s' decoding filename: '%s'" % (e, filename))
                del rf
                return None
        if rf.isSymlink():
            # Find out the link target and populate the target info
            # into this file
            link_target = self._sftp.normalize(self._fixPath(rf.getFilepath()))
            self.log.debug("_createRFInfoFromStat: Symlink info for '%s' -> '%s'", rf.getFilepath(), link_target)
            ## We now know where the link goes, but not what the link is,
            ## we need to find out what it is
            linkstat = self._sftp.lstat(link_target)
            # Copy the target information into our current rf object
            # Do not change the name, we want to keep the original symlink path
            rf.initFromStats(rf.getDirname(), rf.getFilename(), str(linkstat.st_size),
                            str(linkstat.st_uid), str(linkstat.st_gid),
                            linkstat.st_mode, linkstat.st_mtime)
            self.log.debug("_createRFInfoFromStat: File now: %s", rf)
        return rf

    def do_getPathInfo(self, path):
        """Get information about the file/directory for the given path"""
        try:
            self.log.debug("do_getPathInfo: Getting path info for: %s", path)
            info = self._sftp.lstat(self._fixPath(path))
            parentPath = self.do_getParentPath(path)
            #if path == '~': 
            #    parentPath = path
            #else:
            #    parentPath = os.path.dirname(path)
            if path == "/":
                return self._createRFInfoFromStat(parentPath, path, info)
            return self._createRFInfoFromStat(parentPath, os.path.basename(path), info)
        except IOError, e:
            # Likely this path does not exist then, else it needs to be encoded
            self.log.debug("do_getPathInfo: error: %s on path '%s'", e.args[-1], path)
            return None
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_getDirectoryList(self, path, dir_rfinfo):
        """Retrieve directory entries for the given path"""
        dirinfo = []
        try:
            orig_path = path
            # Fix up path for home directory
            path = self._fixPath(path)
            info = self._sftp.listdir_attr(path)
            for fileinfo in info:
                try:
                    rf_fileinfo = self._createRFInfoFromStat(orig_path, fileinfo.filename, fileinfo)
                    if rf_fileinfo is not None:
                        dirinfo.append(rf_fileinfo)
                except Exception, e:
                    self.log.error("Unable to create a listing element for: %s", fileinfo.filename)
                    self.log.debug("Error: %s: %s", e, e.args)
        except self._SFTPExceptions, e:
            self._raiseWithException(e)
        return dirinfo

    def do_rename(self, oldName, newName):
        try:
            self._sftp.rename(self._fixPath(oldName), self._fixPath(newName))
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_changeDirectory(self, path):
        try:
            self._sftp.chdir(self._fixPath(path))
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_currentDirectory(self):
        try:
            return self._sftp.normalize(".")
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_getHomeDirectory(self):
        # Home directory is set when we initially log in
        return self._homedirectory

    def do_getParentPath(self, path):
        try:
            parent_path = os.path.dirname(self._fixPath(path))
            norm_path = self._sftp.normalize(parent_path)
            if not parent_path:
                parent_path = "/"
            self.log.debug("do_getParentPath: '%s' -> '%s'", path, parent_path)
            return parent_path
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_removeFile(self, name):
        try:
            self._sftp.remove(self._fixPath(name))
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_removeDirectory(self, name):
        try:
            return self._sftp.rmdir(self._fixPath(name))
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_createDirectory(self, name, permissions):
        try:
            # Treat permissions as an octet value, we need to convert to integer
            # I.e. 755 as octet, the integer value of this is 493
            # permissions = int(str(permissions), 8)
            return self._sftp.mkdir(self._fixPath(name), permissions)
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_createFile(self, name, permissions):
        try:
            # Treat permissions as an octet value, we need to convert to integer
            # I.e. 755 as octet, the integer value of this is 493
            # permissions = int(str(permissions), 8)
            filename = self._fixPath(name)
            self.log.debug("do_createFile: Creating file though sftp: '%s'", filename)
            # Open and then close the file to create it
            self._sftp.open(filename, 'wb').close()
            self._sftp.chmod(filename, permissions)
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_chmod(self, filepath, permissions):
        try:
            self._sftp.chmod(self._fixPath(filepath), permissions)
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_readFile(self, filename):
        try:
            # Fix up path for home directory
            filename = self._fixPath(filename)
            self.log.debug("do_readFile: Reading sftp file: %s", filename)
            data = self._sftp.open(filename, 'rb').read()
            self.log.debug("do_readFile: Read in %d characters", len(data))
            return data
        except self._SFTPExceptions, e:
            self._raiseWithException(e)

    def do_writeFile(self, filename, data):
        try:
            # Fix up path for home directory
            filename = self._fixPath(filename)
            self.log.debug("do_writeFile: Writing sftp file: %s", filename)
            self._sftp.open(filename, 'wb').write(data)
            self.log.debug("do_writeFile: Wrote %s characters", len(data))
        except self._SFTPExceptions, e:
            self._raiseWithException(e)


# Test function
def _test():
    pass

# When run from command line
if __name__ == '__main__':
    _test()

