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

# Putty/Pageant ssh authentication for win32
#
# This uses "paramiko", a pure python implementation of the 
# SSH2 protocol, of which, we are using the SFTP component.
# http://www.lag.net/paramiko/
#
# Contributors:
# * Todd Whiteman

import os, time, array, struct, mmap
import logging, tempfile
# Paramiko sftp imports
import paramiko
from paramiko.agent import SSH2_AGENTC_REQUEST_IDENTITIES, \
                           SSH2_AGENT_IDENTITIES_ANSWER, \
                           SSH2_AGENTC_SIGN_REQUEST, \
                           SSH2_AGENT_SIGN_RESPONSE

# Note: These WM_* values are pulled from win32con, as a workaround
# so we do not need to import this huge library.
WM_COPYDATA                     = 74
WM_NULL                         = 0

# Pageant and SSH defines
AGENT_MAX_MSGLEN                = 8192
AGENT_COPYDATA_ID               = 0x804e50ba
SSH2_AGENTC_REQUEST_KEYS        = 1
PAGEANT_REQUEST_KEY_DATA        = "\0\0\0" + \
                                  chr(SSH2_AGENTC_REQUEST_KEYS) + \
                                  chr(paramiko.agent.SSH2_AGENTC_REQUEST_IDENTITIES)
# Phew... thats getting ugly

class PageantException(paramiko.SSHException):
    pass

# Convert a 4 byte string into an integer value
# Returns the integer value
# Exceptions: can raise PageantException
def covert_to_int(data):
    try:
        if len(data) != 4:
            raise PageantException("covert_to_int: Data length is not 4, it is: %d" % (len(data)))
        # Note: Pageant uses big-endian format, thus use ">" with unpack()
        return struct.unpack(">L", data)[0]
    except struct.error:
        raise PageantException("covert_to_int: Could not unpack data: 0x%s" % (''.join( [ '%02x' % (ord(c)) for c in data ] )))

# Read an integer value from file/mmap object f
# Returns the integer value
# Exceptions: covert_to_int() may raise PageantException
def file_read_int(f):
    # Parse up 4 bytes into an integer/long value
    data = f.read(4)
    return covert_to_int(data)

# Send a request to pageant and get back the response data
# Returns the data response that pageant receives
# Returns None if pageant is not running
def pageant_request(pageant_data):
    # Win32 import moved here to stop initial component registration problems
    import win32gui

    # Make sure Pageant is running, otherwise this is pointless
    try:
        hwnd = win32gui.FindWindowEx(0, 0, "Pageant", "Pageant")
        if not hwnd:
            return None
    except win32gui.error, e:
        # Pageant window could not be found
        return None

    # Write our pageant request string into the file, pageant will read this to
    # determine what it needs to do.
    (fd, filename) = tempfile.mkstemp('.pag')
    map_filename = os.path.basename(filename)

    f = os.fdopen(fd, 'w+b')
    try:
        f.seek(0)
        f.write(pageant_data)
        f.write('\0' * (AGENT_MAX_MSGLEN - len(pageant_data)))
    
        # Create the shared file map that pageant will use to read
        pymap = mmap.mmap(f.fileno(), AGENT_MAX_MSGLEN, tagname=map_filename, access=mmap.ACCESS_WRITE)

        char_buffer = array.array("c", map_filename + '\0')
        char_buffer_address, char_buffer_size = char_buffer.buffer_info()
        cds = struct.pack("LLP", AGENT_COPYDATA_ID, char_buffer_size, char_buffer_address)

        succ = win32gui.SendMessage(hwnd, WM_COPYDATA, WM_NULL, cds)

        if not succ:
            raise "Pageant SendMessage failed."

        #print "SendMessage result:", succ
        pymap.flush()
        pymap.seek(0)
        data_len = file_read_int(pymap)
        #log.debug("Length of pageant data: %d", data_len)
        data = pymap.read(data_len)
        pymap.close()
        return data
    finally:
        f.close()
        os.unlink(filename)

# Wrapper around paramiko's agent for supporting Putty's Pageant
class PageantKey(paramiko.AgentKey):
    """
    Private key held in pageant.  This type of key can be used for
    authenticating to a remote server (signing).
    """
    def __init__(self, agent, keyblob, keycomment):
        paramiko.AgentKey.__init__(self, agent, keyblob)
        self.comment = keycomment

    def sign_ssh_data(self, randpool, data):
        """Get pageant to sign the data
        Can raise a paramiko.SSHException if pageant cannot sign the data.
        """
        #print "Paramiko wants me to sign"
        request_data = chr(SSH2_AGENTC_SIGN_REQUEST)
        # Add public key blob
        request_data += struct.pack(">L", len(self.blob))
        request_data += self.blob
        # Add public sign data
        request_data += struct.pack(">L", len(data))
        request_data += data
        # Put whole length + data in request_data
        request_data = struct.pack(">L", len(request_data)) + request_data

        # Make the request to pageant
        pagdata = pageant_request(request_data)
        if not pagdata:
            raise paramiko.SSHException('Pageant is no longer running')
        # first byte should be the pageant answer code
        if pagdata[0] != chr(SSH2_AGENT_SIGN_RESPONSE):
            raise paramiko.SSHException('key cannot be used for signing')
        return pagdata[5:]


class KomodoAgent(paramiko.Agent):
    """
    Client interface for using private keys from an SSH agent running on the
    local machine.  If an SSH agent is running, this class can be used to
    connect to it and retreive PKey objects which can be used when
    attempting to authenticate to remote SSH servers.
    
    The SSH agent protocol uses environment variables and unix-domain
    sockets on Linux and MacOS X, as well as Pageant (Putty) for Windows.
    """
    
    def __init__(self):
        """
        Open a session with the local machine's SSH agent, if one is running.
        If no agent is running, initialization will succeed, but get_keys
        will return an empty tuple.
        
        @raise SSHException: if an SSH agent is found, but speaks an
            incompatible protocol
        """
        # Initialise keys known through paramiko (Linux, Mac side)
        import socket
        try:
            paramiko.Agent.__init__(self)
        except socket.error, e:
            # if SSH_AUTH_SOCK is set, but the socket file actually does
            # not exist, we will get an exception raised.  We want to ignore
            # the exception so that the KomodoAgent initalizes correctly,
            # which is the expected behaviour. bug 60897
            pass
        self.log = logging.getLogger('KomodoAgent')
        #self.log.setLevel(logging.DEBUG)
        self.log.debug('koSFTPConnection __init__()')

        # Initialise keys known through pageant (Windows side)
        pagdata = pageant_request(PAGEANT_REQUEST_KEY_DATA)
        if not pagdata:
            # Pageant was not able to be used
            return

        # first byte should be the pageant answer code
        if pagdata[0] == chr(SSH2_AGENT_IDENTITIES_ANSWER):
            pageant_keys = []
            # okay, find out how many keys were returned
            num_keys = covert_to_int(pagdata[1:5])
            self.log.debug("%d keys returned", num_keys)
            data_pos = 5
            # Parse up the keys from the pageant data revieced
            for key_num in range(1, num_keys+1):
                key = ['', '']  # [ data, comment ]
                for key_part in range(len(key)):
                    # Read key info
                    key_data_length     = covert_to_int(pagdata[data_pos:data_pos+4])
                    key[key_part]       = pagdata[data_pos+4:data_pos+4+key_data_length]
                    data_pos            += 4 + key_data_length
                # Add to list of public keys
                pageant_keys.append(PageantKey(self, key[0], key[1]))
            # Add this to the known paramiko keys
            self.keys = tuple(list(self.keys) + pageant_keys)


def _test():
    ka = KomodoAgent()

if __name__ == '__main__':
    _test()
