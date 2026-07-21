# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

"""
DSS keys.
"""

import os
from hashlib import sha1

from Crypto.PublicKey import DSA

from paramiko import util
from paramiko.common import zero_byte
from paramiko.py3compat import long
from paramiko.ssh_exception import SSHException
from paramiko.message import Message
from paramiko.ber import BER, BERException
from paramiko.pkey import PKey


class DSSKey (PKey):
    """
    Representation of a DSS key which can be used to sign an verify SSH2
    data.
    """

    def __init__(self, msg=None, data=None, filename=None, password=None, vals=None, file_obj=None):
        self.p = None
        self.q = None
        self.g = None
        self.y = None
        self.x = None
        if file_obj is not None:
            self._from_private_key(file_obj, password)
            return
        if filename is not None:
            self._from_private_key_file(filename, password)
            return
        if (msg is None) and (data is not None):
            msg = Message(data)
        if vals is not None:
            self.p, self.q, self.g, self.y = vals
        else:
            if msg is None:
                raise SSHException('Key object may not be empty')
            if msg.get_text() != 'ssh-dss':
                raise SSHException('Invalid key')
            self.p = msg.get_mpint()
            self.q = msg.get_mpint()
            self.g = msg.get_mpint()
            self.y = msg.get_mpint()
        self.size = util.bit_length(self.p)

    def asbytes(self):
        m = Message()
        m.add_string('ssh-dss')
        m.add_mpint(self.p)
        m.add_mpint(self.q)
        m.add_mpint(self.g)
        m.add_mpint(self.y)
        return m.asbytes()

    def __str__(self):
        return self.asbytes()

    def __hash__(self):
        h = hash(self.get_name())
        h = h * 37 + hash(self.p)
        h = h * 37 + hash(self.q)
        h = h * 37 + hash(self.g)
        h = h * 37 + hash(self.y)
        # h might be a long by now...
        return hash(h)

    def get_name(self):
        return 'ssh-dss'

    def get_bits(self):
        return self.size

    def can_sign(self):
        return self.x is not None

    def sign_ssh_data(self, data):
        digest = sha1(data).digest()
        # generate a suitable k
        qsize = len(util.deflate_long(self.q, 0))
        while True:
            k = util.inflate_long(os.urandom(qsize), 1)
            if (k > 2) and (k < self.q):
                break
        # pycryptodome's DsaKey no longer exposes raw sign()/verify()
        # ("Use module Crypto.Signature.DSS instead") -- but that module
        # generates its own k internally (deliberately, to avoid the
        # well-known k-reuse/k-leakage class of DSA vulnerabilities) and
        # has no way to accept the caller-supplied k paramiko generates
        # above. Do the same raw DSA sign math pycrypto's dss.sign()
        # did internally instead, using paramiko's own existing
        # util.mod_inverse() (already used elsewhere in this codebase for
        # private key encoding).
        M = util.inflate_long(digest, 1)
        r = pow(self.g, k, self.p) % self.q
        s = (util.mod_inverse(k, self.q) * (M + self.x * r)) % self.q
        m = Message()
        m.add_string('ssh-dss')
        # apparently, in rare cases, r or s may be shorter than 20 bytes!
        rstr = util.deflate_long(r, 0)
        sstr = util.deflate_long(s, 0)
        if len(rstr) < 20:
            rstr = zero_byte * (20 - len(rstr)) + rstr
        if len(sstr) < 20:
            sstr = zero_byte * (20 - len(sstr)) + sstr
        m.add_string(rstr + sstr)
        return m

    def verify_ssh_sig(self, data, msg):
        if len(msg.asbytes()) == 40:
            # spies.com bug: signature has no header
            sig = msg.asbytes()
        else:
            kind = msg.get_text()
            if kind != 'ssh-dss':
                return 0
            sig = msg.get_binary()

        # pull out (r, s) which are NOT encoded as mpints
        sigR = util.inflate_long(sig[:20], 1)
        sigS = util.inflate_long(sig[20:], 1)
        sigM = util.inflate_long(sha1(data).digest(), 1)

        # See sign_ssh_data() above for why this is raw modular arithmetic
        # rather than dss.verify() (removed in pycryptodome).
        if not (0 < sigR < self.q) or not (0 < sigS < self.q):
            return False
        w = util.mod_inverse(sigS, self.q)
        u1 = (sigM * w) % self.q
        u2 = (sigR * w) % self.q
        v = ((pow(self.g, u1, self.p) * pow(self.y, u2, self.p)) % self.p) % self.q
        return v == sigR

    def _encode_key(self):
        if self.x is None:
            raise SSHException('Not enough key information')
        keylist = [0, self.p, self.q, self.g, self.y, self.x]
        try:
            b = BER()
            b.encode(keylist)
        except BERException:
            raise SSHException('Unable to create ber encoding of key')
        return b.asbytes()

    def write_private_key_file(self, filename, password=None):
        self._write_private_key_file('DSA', filename, self._encode_key(), password)

    def write_private_key(self, file_obj, password=None):
        self._write_private_key('DSA', file_obj, self._encode_key(), password)

    @staticmethod
    def generate(bits=1024, progress_func=None):
        """
        Generate a new private DSS key.  This factory function can be used to
        generate a new host key or authentication key.

        :param int bits: number of bits the generated key should be.
        :param function progress_func:
            unused -- accepted only for backwards API compatibility. pycrypto's
            DSA.generate() took a progress callback as its 3rd positional arg;
            pycryptodome's DSA.generate(bits, randfunc=None, domain=None) does
            not (that 3rd slot is now domain parameters), so there is nothing
            to forward it to any more.
        :return: new `.DSSKey` private key
        """
        dsa = DSA.generate(bits, os.urandom)
        key = DSSKey(vals=(dsa.p, dsa.q, dsa.g, dsa.y))
        key.x = dsa.x
        return key

    ###  internals...

    def _from_private_key_file(self, filename, password):
        data = self._read_private_key_file('DSA', filename, password)
        self._decode_key(data)

    def _from_private_key(self, file_obj, password):
        data = self._read_private_key('DSA', file_obj, password)
        self._decode_key(data)

    def _decode_key(self, data):
        # private key file contains:
        # DSAPrivateKey = { version = 0, p, q, g, y, x }
        try:
            keylist = BER(data).decode()
        except BERException as e:
            raise SSHException('Unable to parse key file: ' + str(e))
        if (type(keylist) is not list) or (len(keylist) < 6) or (keylist[0] != 0):
            raise SSHException('not a valid DSA private key file (bad ber encoding)')
        self.p = keylist[1]
        self.q = keylist[2]
        self.g = keylist[3]
        self.y = keylist[4]
        self.x = keylist[5]
        self.size = util.bit_length(self.p)
