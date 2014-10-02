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
#
# TODO:
# * File permissions are not used/preserved.
# * Add/use the timeout value in server preferences.
# * Standalone testing, could use paramiko ssh server components.

import os
import logging
import time
import socket
import re

from xpcom import components, ServerException, nsError

# remote file library
import remotefilelib
# needed for SSH
import paramiko


log = logging.getLogger('koSCPConnection')
#log.setLevel(logging.DEBUG)

MAX_BLOCK_SIZE = 8192


# URI handler
class SCPURI:
    _com_interfaces_ = components.interfaces.nsIProtocolHandler
    _reg_contractid_ = '@mozilla.org/network/protocol;1?name=scp'
    _reg_clsid_ = '{40843031-307c-4fb1-8557-ebb0a72d0441}'
    _reg_desc_ = "SCP handler"

    scheme = "scp"
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
class koSCPConnection(remotefilelib.koRemoteSSH):
    _com_interfaces_ = [components.interfaces.koISSHConnection]
    _reg_desc_ = "Komodo Remote SCP"
    _reg_contractid_ = "@activestate.com/koSCPConnection;1"
    _reg_clsid_ = "{73836747-2f55-405e-a96b-fcb212403cd4}"

    ConnectionException = paramiko.SSHException
    # SCP Exceptions caught and handled
    _SCPExceptions = (paramiko.SSHException, socket.timeout)

    def __init__(self):
        remotefilelib.koRemoteSSH.__init__(self)
        #self.log.setLevel(logging.DEBUG)
        self.log = log
        self.log.debug('__init__()')
        self.protocol = 'scp'
        self.port = remotefilelib.koRFProtocolDefaultPort[self.protocol]
        # Private, set to the first directory where we log into
        # This is because sftp does not support "~" names.
        self._homedirectory = None
        self._use_ls_lad = 1
        self._use_time_delay = 0
        #self._use_time_delay = 1

    def _setHomeDirectory(self):
        # Note: We only just return the last line, as there may be junk output
        #       from the login shell, i.e. from .bashrc, .profile
        try:
            pwd = self._runScpCommand("pwd", splitlines=True)
            if len(pwd) >= 1:
                self._homedirectory = pwd[-1]
            else:
                self._homedirectory = '/'
                self.log.error("Could not determine the remote home directory. 'pwd' failed")
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    # remotefilelib.koRemoteSSH handles the opening and authentication methods.
    def do_authenticateWithPrivateKey(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPrivateKey(self) == 1:
            self._setHomeDirectory()
            return 1
        return 0

    def do_authenticateWithPassword(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPassword(self) == 1:
            self._setHomeDirectory()
            return 1
        return 0

    def do_authenticateWithPassword(self):
        if remotefilelib.koRemoteSSH.do_authenticateWithPassword(self) == 1:
            self._setHomeDirectory()
            return 1
        return 0

    # remotefilelib.koRemoteSSH handles these methods.
    #def do_openSocket(self):
    #def do_close(self):
    #def do_verifyConnected(self):

    #def _fixPath(self, path):
        # Now in parent class, remotefilelib.py

    _escape_chars = ('\\', ' ', "'", '"', ';')
    def _escapePath(self, path):
        """Escape the path
        Escape spaces, backslashes, quotes etc...
        """
        # XXX: Quoting... this could cause problems with certain shells?
        #for char in self._escape_chars:
        #    path = path.replace(char, "\\" + char)
        path = '"%s"' % (self._fixPath(path).replace('"', r'\"'))
        return path

    def _readFromChannel(self, channel, timeout=None, readlength=None):
        """Read data from the channel. This will perform one read action, that
        is, even if more data is available return with just what it first read.

        Returns string of data received.
        Raises socket.error if a timeout occurs."""

        oldtimeout = channel.gettimeout()
        if not timeout:
            timeout = self._socket_timeout
        channel.settimeout(timeout)
        received_so_far = 0
        result = []
        try:
            while 1:
                data = channel.recv(MAX_BLOCK_SIZE)
                received_so_far += len(data)
                if readlength and received_so_far >= readlength:
                    result.append(data[:len(data) - (received_so_far - readlength)])
                    break
                result.append(data)
                if not readlength or len(data) != MAX_BLOCK_SIZE:
                    break
            return ''.join(result)
        finally:
            channel.settimeout(oldtimeout)

    # Run a command through the SSH connection
    # Return the data from the command
    # Raise an exception when the command fails
    def _runScpCommand(self, command, splitlines=False):
        #print "_runScpCommand: running: '%s'" % command
        self.log.debug("_runScpCommand: running: '%s'", command)
        channel = self._connection.open_session()
        if self._use_time_delay:
            # XXX - openSSH hack to stop remote commands from hanging
            time.sleep(0.1)
        try:
            # This was causing problems on different platforms, so just grab the
            # response to the command.
            # XXX: This will not give a message if a command fails though... ???
            channel.exec_command(command)
            data_segments = []
            while 1:
                #data = channel.recv(MAX_BLOCK_SIZE)
                data = self._readFromChannel(channel)
                if not data:
                    break
                data_segments.append(data)
        finally:
            channel.close()
        data = ''.join(data_segments)

        self.log.debug("_runScpCommand: result\n%s", data)
        if splitlines:
            return data.splitlines(0)
        return data


    #def _createBaseDirectory(self, dirname):
        # Now in parent class, remotefilelib.py

    #def __createRFInfoFromListing(self, dirname, fileinfo):
        # Now in parent class, remotefilelib.py

    #def _createRFInfo(self, path, fileinfo=None):
        # Now in parent class, remotefilelib.py

    #def _followSymlink(self, rfinfo):
        # Now in parent class, remotefilelib.py

    def _createRFInfoFromPath(self, path):
        info = []
        path = self._fixPath(path)
        dirname = self.do_getParentPath(path)
        basename = os.path.basename(path)
        self.log.debug("_createRFInfoFromPath for: '%s'", path)
        # We have two ways of doing this
        # 1 - Using LIST -lad, which just displays the directory
        #     Note: Some servers may not use this option (I.e. windows)
        #     Note: Also, some quoted paths may not work with this
        if self._use_ls_lad:
            try:
                info = self._runScpCommand("ls -lad %s" % (self._escapePath(path)), splitlines=True)
                self.log.debug("_createRFInfoFromPath: %s", info)
                info.reverse()  # Start from the last line (skip any shell garbage)
                for line in info:
                    rf_pathinfo = self._createRFInfoFromListing(dirname, line)
                    if rf_pathinfo and (path[0] == '~' or rf_pathinfo.getFilename() == basename):
                        return rf_pathinfo
            except self.ConnectionException, e:
                self._use_ls_lad = 0
                self.log.info("ls -lad failed: %s", e)
                self.log.debug("_createRFInfoFromPath: Not using 'ls -lad' any further")
                pass

        # 2 - Do a ls -la of the parent directory and find the child in the list
        info = []
        info = self._runScpCommand("ls -la %s" % (self._escapePath(dirname)), splitlines=True)
        for filelisting in info:
            if filelisting.find(basename) > 0:
                rf_pathinfo = self._createRFInfoFromListing(dirname, filelisting)
                if rf_pathinfo and rf_pathinfo.getFilename() == basename:
                    return rf_pathinfo
        return None

    def do_getPathInfo(self, path):
        try:
            # Get the remote file details
            try:
                rf_info = self._createRFInfo(path)
            except self._SCPExceptions, e:
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

            # Does not exist
            self.log.debug("do_getPathInfo: Path does not exist '%s'", path)
            return None
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_getDirectoryList(self, path, dir_rfinfo):
        """Retrieve directory entries for the given path"""
        # Use this rf_info path, as it's symlink ready
        if dir_rfinfo.getLinkTarget():
            path = dir_rfinfo.getLinkTarget()

        dirinfo = []
        try:
            orig_path = path
            # Fix up path for home directory
            path = self._fixPath(path)
            #info = self._sftp.listdir_attr(path)
            #for fileinfo in info:
            #    rf_fileinfo = self._createRFInfoFromStat(orig_path, fileinfo.filename, fileinfo)
            #    dirinfo.append(rf_fileinfo)
            info = self._runScpCommand("ls -la %s" % (self._escapePath(path)), splitlines=True)
            # Alternative on unix boxes (L means to show links as real items)
            #info = self._runScpCommand("ls -laL %s" % (self._escapePath(path)), splitlines=True)
            for fileinfo in info:
                self.log.debug("do_getDirectoryList: raw list item: %s", fileinfo)
                try:
                    rf_fileinfo = self._createRFInfo(path, fileinfo)
                    if rf_fileinfo and rf_fileinfo.getFilename() not in (".", ".."):
                        dirinfo.append(rf_fileinfo)
                except self._SCPExceptions, e:
                    self._raiseWithException(e)
                except Exception, e:
                    self.log.error("Unable to create a listing element for: %s", fileinfo)
                    self.log.debug("Error: %s: %s", e, e.args)
        except self._SCPExceptions, e:
            self._raiseWithException(e)
        return dirinfo

    def do_rename(self, oldName, newName):
        try:
            self._runScpCommand("mv %s %s" % (self._escapePath(oldName), self._escapePath(newName)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_changeDirectory(self, path):
        # Not needed
        pass

    def do_currentDirectory(self):
        try:
            return self._runScpCommand("pwd")
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_getHomeDirectory(self):
        # Home directory is set when we initially log in
        if self._homedirectory is None:
            self._setHomeDirectory()
        return self._homedirectory

    def do_getParentPath(self, path):
        try:
            norm_path = self._fixPath(path)
            parent_path = os.path.dirname(norm_path)
            if not parent_path:
                parent_path = "/"
            self.log.debug("do_getParentPath: '%s' -> '%s'", path, parent_path)
            return parent_path
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_removeFile(self, name):
        try:
            self._runScpCommand("rm %s" % (self._escapePath(name)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_removeDirectory(self, name):
        try:
            self._runScpCommand("rmdir %s" % (self._escapePath(name)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_createDirectory(self, name, permissions):
        try:
            # Treat permissions as an octet value, we need to convert to integer
            # I.e. 755 as octet, the integer value of this is 493
            # permissions = int(str(permissions), 8)
            self._runScpCommand("mkdir %s" % (self._escapePath(name)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_createFile(self, name, permissions):
        try:
            # Treat permissions as an octet value, we need to convert to integer
            # I.e. 755 as octet, the integer value of this is 493
            # permissions = int(str(permissions), 8)
            self._runScpCommand("touch %s" % (self._escapePath(name)))
            #self._runScpCommand("chmod %s %s" % (permissions, self._escapePath(name)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def do_chmod(self, filepath, permissions):
        try:
            self._runScpCommand("chmod %s %s" % (oct(permissions),
                                                 self._escapePath(filepath)))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    class _scp_transfer_response:
        def __init__(self, mode, length, filename):
            self.mode = int(mode, 8)    # Octet format, convert to int
            self.length = long(length)
            self.filename = filename
        def __str__(self):
            return "filename: %s, length: %s, mode: %s" % (self.filename,
                                                           self.length,
                                                           oct(self.mode))

    # The scp response format is the following:
    # C<mode> <length> <filename>
    #   mode:       an octal value, i.e. 0644
    #   length:     length of the file that will be sent
    #   filename:   remote name of the file being sent
    _scp_regex = re.compile(r'^C(?P<mode>\d+)\s+(?P<length>\d+)\s+(?P<filename>.*)$')

    def _scpGetFileTransferResponse(self, channel):
        try:
            #total_data_read = []
            left_over_read_data = ''
            while 1:
                scp_response = self._readFromChannel(channel)
                if not scp_response:
                    raise self.ConnectionException("No SCP response was received.")
                self.log.debug("_scpGetFileTransferResponse: data read from channel: '%s'", scp_response)
                if left_over_read_data:
                    scp_response = left_over_read_data + scp_response
                    left_over_read_data = ''

                regex_groups = None
                linesplits = scp_response.splitlines(1)
                for line in linesplits:
                    regexdata = self._scp_regex.match(line)
                    if regexdata:
                        # We have a match
                        regex_groups = regexdata.groupdict()
                        break
                else:
                    if linesplits[-1] and linesplits[-1][-1] not in '\r\n':
                        left_over_read_data = linesplits[-1]
                if regex_groups:
                    scp_info = self._scp_transfer_response(regex_groups['mode'],
                                                           regex_groups['length'],
                                                           regex_groups['filename'])
                    log.info("_scpGetFileTransferResponse: scp_info: %s", (scp_info))
                    return scp_info
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def _scpReadFile(self, filename):
        channel = self._connection.open_session()
        if self._use_time_delay:
            # XXX - openSSH hack to stop remote commands from hanging
            time.sleep(0.1)
        try:
            channel.exec_command('scp -f %s' % (self._escapePath(filename)))
            # Read information generated from a login shell, see:
            # http://bugs.activestate.com/show_bug.cgi?id=45395
            try:
                self._readFromChannel(channel, timeout=0.1)
            except socket.error:    # Timeout occured
                pass   # That's okay if there is nothing to read yet

            # Prompt for file info by sending a null byte
            channel.send('\0')
            scp_info = self._scpGetFileTransferResponse(channel)
            if not scp_info:
                raise self.ConnectionException("Unable to perform remote scp fetch file operation")

            # Prompt for the file data now
            channel.send('\0')

            # Read all the file data
            length_data_left_to_read = scp_info.length
            data_segments = []
            # Need to keep reading until we get all the data, bug 61428
            while length_data_left_to_read > 0:
                data = self._readFromChannel(channel, readlength=length_data_left_to_read)
                if not data:
                    break
                data_segments.append(data)
                length_data_left_to_read -= len(data)
            data = "".join(data_segments)
            #import binascii
            #self.log.debug("_scpReadFile: File data\n%s", binascii.hexlify(''.join(fileparts)))
            if len(data) > scp_info.length:
                return data[:scp_info.length]
            elif len(data) == scp_info.length:
                return data
            else:
                self.log.error("_scpReadFile: Read '%d' bytes, but required length was: %d",
                               len(data), scp_info.length)
            # Else, we couldn't read all the information
            raise self.ConnectionException("Unable to perform remote scp fetch file operation")

        finally:
            channel.close()

    def do_readFile(self, filename):
        try:
            # Fix up path for home directory
            return self._scpReadFile(self._fixPath(filename))
        except self._SCPExceptions, e:
            self._raiseWithException(e)

    def _getAcknowledgement(self, channel):
        scp_response = self._readFromChannel(channel)
        if not scp_response:
            raise self.ConnectionException("No SCP response was received")
        status_code = scp_response[0]
        if status_code == '\0':
            # All is good.
            return
        # Else, it's an error, see if we can format the error a little...
        error_message = scp_response[1:]
        error_split = error_message.split(":", 1)
        if len(error_split) > 1:
            error_message = error_split[1]
        raise self.ConnectionException(error_message.strip())

    def _scpWriteFile(self, filename, permissions, data):
        channel = self._connection.open_session()
        if self._use_time_delay:
            # XXX - openSSH hack to stop remote commands from hanging
            time.sleep(0.1)
        try:
            channel.exec_command('scp -t %s' % (self._escapePath(filename)))
            # Wait for the acknowledgement
            self._getAcknowledgement(channel)

            # Send the file information now
            filedata = "C%s %d %s\n" % (permissions, len(data), os.path.basename(filename))
            channel.send(filedata)

            # Remote scp will send an ack when they have received file info and
            # it is ready to receive the file data.
            self._getAcknowledgement(channel)

            # Send all the file data now
            channel.sendall(data)
        finally:
            channel.close()

    def do_writeFile(self, filename, data):
        try:
            # XXX - Fix permissions!
            filemode = "0644"
            # Fix up path for home directory
            return self._scpWriteFile(self._fixPath(filename), filemode, data)
        except self._SCPExceptions, e:
            self._raiseWithException(e)


# Test function
def _test():
    pass

# When run from command line
if __name__ == '__main__':
    _test()

