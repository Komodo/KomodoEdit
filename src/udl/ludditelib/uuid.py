"""UUID (universally unique identifiers) as specified in RFC 4122.

This module provides the UUID class and the functions uuid1(), uuid3(),
uuid4(), uuid5() for generating version 1, 3, 4, and 5 UUIDs respectively.

This module works with Python 2.3 or higher."""

__author__ = 'Ka-Ping Yee <ping@zesty.ca>'
__date__ = '$Date: 2005/11/30 11:51:58 $'.split()[1].replace('/', '-')
__version__ = '$Revision: 1.10 $'

RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE = [
    'reserved for NCS compatibility', 'specified in RFC 4122',
    'reserved for Microsoft compatibility', 'reserved for future definition']

class UUID(object):
    """Instances of the UUID class represent UUIDs as specified in RFC 4122.
    Converting a UUID to a string using str() produces a string in the form
    "{12345678-1234-1234-1234-123456789abc}".  The UUID constructor accepts
    a similar string (braces and hyphens optional), or six integer arguments
    (with 32-bit, 16-bit, 16-bit, 8-bit, 8-bit, and 48-bit values
    respectively).  UUID objects have the following attributes:

        bytes       gets or sets the UUID as a 16-byte string

        urn         gets the UUID as a URN as specified in RFC 4122

        variant     gets or sets the UUID variant as one of the constants
                    RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE

        version     gets or sets the UUID version number (1 through 5)
    """

    def __init__(self, *args):
        """Create a UUID either from a string representation in hexadecimal
        or from six integers (32-bit time_low, 16-bit time_mid, 16-bit
        time_hi_ver, 8-bit clock_hi_res, 8-bit clock_low, 48-bit node)."""
        if len(args) == 1:
            digits = args[0].replace('urn:', '').replace('uuid:', '')
            digits = digits.replace('{', '').replace('}', '').replace('-', '')
            assert len(digits) == 32, ValueError('badly formed UUID string')
            time_low = int(digits[:8], 16)
            time_mid = int(digits[8:12], 16)
            time_hi_ver = int(digits[12:16], 16)
            clock_hi_res = int(digits[16:18], 16)
            clock_low = int(digits[18:20], 16)
            node = int(digits[20:32], 16)
        else:
            (time_low, time_mid, time_hi_ver,
             clock_hi_res, clock_low, node) = args
        assert 0 <= time_low < 0x100000000, ValueError('time_low out of range')
        assert 0 <= time_mid < 1<<16, ValueError('time_mid out of range')
        assert 0 <= time_hi_ver < 1<<16, ValueError('time_hi_ver out of range')
        assert 0 <= clock_hi_res < 1<<8, ValueError('clock_hi_res out of range')
        assert 0 <= clock_low < 1<<8, ValueError('clock_low out of range')
        assert 0 <= node < 0x1000000000000, ValueError('node out of range')
        self.time_low = time_low
        self.time_mid = time_mid
        self.time_hi_ver = time_hi_ver
        self.clock_hi_res = clock_hi_res
        self.clock_low = clock_low
        self.node = node

    def __cmp__(self, other):
        return cmp(self.bytes, getattr(other, 'bytes', other))

    def __str__(self):
        return '{%08x-%04x-%04x-%02x%02x-%012x}' % (
            self.time_low, self.time_mid, self.time_hi_ver,
            self.clock_hi_res, self.clock_low, self.node)

    def __repr__(self):
        return 'UUID(%r)' % str(self)

    def get_bytes(self):
        def byte(n):
            return chr(n & 0xff)

        return (byte(self.time_low >> 24) + byte(self.time_low >> 16) +
                byte(self.time_low >> 8) + byte(self.time_low) +
                byte(self.time_mid >> 8) + byte(self.time_mid) +
                byte(self.time_hi_ver >> 8) + byte(self.time_hi_ver) +
                byte(self.clock_hi_res) + byte(self.clock_low) +
                byte(self.node >> 40) + byte(self.node >> 32) +
                byte(self.node >> 24) + byte(self.node >> 16) +
                byte(self.node >> 8) + byte(self.node))

    def set_bytes(self, bytes):
        values = map(ord, bytes)
        self.time_low = ((values[0] << 24) + (values[1] << 16) +
                         (values[2] << 8) + values[3])
        self.time_mid = (values[4] << 8) + values[5]
        self.time_hi_ver = (values[6] << 8) + values[7]
        self.clock_hi_res = values[8]
        self.clock_low = values[9]
        self.node = ((values[10] << 40) + (values[11] << 32) +
                     (values[12] << 24) + (values[13] << 16) +
                     (values[14] << 8) + values[15])

    bytes = property(get_bytes, set_bytes)

    def get_urn(self):
        return 'urn:uuid:%08x-%04x-%04x-%02x%02x-%012x' % (
            self.time_low, self.time_mid, self.time_hi_ver,
            self.clock_hi_res, self.clock_low, self.node)

    urn = property(get_urn)

    def get_variant(self):
        if not self.clock_hi_res & 0x80:
            return RESERVED_NCS
        elif not self.clock_hi_res & 0x40:
            return RFC_4122
        elif not self.clock_hi_res & 0x20:
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE

    def set_variant(self, variant):
        if variant == RESERVED_NCS:
            self.clock_hi_res &= 0x7f
        elif variant == RFC_4122:
            self.clock_hi_res &= 0x3f
            self.clock_hi_res |= 0x80
        elif variant == RESERVED_MICROSOFT:
            self.clock_hi_res &= 0x1f
            self.clock_hi_res |= 0xc0
        elif variant == RESERVED_FUTURE:
            self.clock_hi_res &= 0x1f
            self.clock_hi_res |= 0xe0
        else:
            raise ValueError('illegal variant identifier')

    variant = property(get_variant, set_variant)

    def get_version(self):
        return self.time_hi_ver >> 12

    def set_version(self, version):
        assert 1 <= version <= 5, ValueError('illegal version number')
        self.time_hi_ver &= 0x0fff
        self.time_hi_ver |= (version << 12)

    version = property(get_version, set_version)

def unixgetaddr(program):
    """Get the hardware address on a Unix machine."""
    from os import popen
    for line in popen(program):
        words = line.lower().split()
        if 'hwaddr' in words:
            addr = words[words.index('hwaddr') + 1]
            return int(addr.replace(':', ''), 16)
        if 'ether' in words:
            addr = words[words.index('ether') + 1]
            return int(addr.replace(':', ''), 16)

def wingetaddr(program):
    """Get the hardware address on a Windows machine."""
    from os import popen
    for line in popen(program + ' /all'):
        if line.strip().lower().startswith('physical address'):
            addr = line.split(':')[-1].strip()
            return int(addr.replace('-', ''), 16)

def getaddr():
    """Get the hardware address as a 48-bit integer."""
    from os.path import join, isfile
    for dir in ['/sbin', '/usr/sbin', r'c:\windows',
                r'c:\windows\system', r'c:\windows\system32']:
        if isfile(join(dir, 'ifconfig')):
            return unixgetaddr(join(dir, 'ifconfig'))
        if isfile(join(dir, 'ipconfig.exe')):
            return wingetaddr(join(dir, 'ipconfig.exe'))

def uuid1():
    """Generate a UUID based on the time and hardware address."""
    from time import time
    from random import randrange
    nanoseconds = int(time() * 1e9)
    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = int(nanoseconds/100) + 0x01b21dd213814000
    clock = randrange(1<<16) # don't use stable storage
    time_low = timestamp & (0x100000000 - 1)
    time_mid = (timestamp >> 32) & 0xffff
    time_hi_ver = (timestamp >> 48) & 0x0fff
    clock_low = clock & 0xff
    clock_hi_res = (clock >> 8) & 0x3f
    node = getaddr()
    uuid = UUID(time_low, time_mid, time_hi_ver, clock_low, clock_hi_res, node)
    uuid.variant = RFC_4122
    uuid.version = 1
    return uuid

def uuid3(namespace, name):
    """Generate a UUID from the MD5 hash of a namespace UUID and a name."""
    from md5 import md5
    uuid = UUID(0, 0, 0, 0, 0, 0)
    uuid.bytes = md5(namespace.bytes + name).digest()[:16]
    uuid.variant = RFC_4122
    uuid.version = 3
    return uuid

def uuid4():
    """Generate a random UUID."""
    try:
        from os import urandom
    except:
        from random import randrange
        uuid = UUID(randrange(1<<32), randrange(1<<16), randrange(1<<16),
                    randrange(1<<8), randrange(1<<8), randrange(1<<48))
    else:
        uuid = UUID(0, 0, 0, 0, 0, 0)
        uuid.bytes = urandom(16)
    uuid.variant = RFC_4122
    uuid.version = 4
    return uuid

def uuid5(namespace, name):
    """Generate a UUID from the SHA-1 hash of a namespace UUID and a name."""
    from sha import sha
    uuid = UUID(0, 0, 0, 0, 0, 0)
    uuid.bytes = sha(namespace.bytes + name).digest()[:16]
    uuid.variant = RFC_4122
    uuid.version = 5
    return uuid

NAMESPACE_DNS = UUID('{6ba7b810-9dad-11d1-80b4-00c04fd430c8}')
NAMESPACE_URL = UUID('{6ba7b811-9dad-11d1-80b4-00c04fd430c8}')
NAMESPACE_OID = UUID('{6ba7b812-9dad-11d1-80b4-00c04fd430c8}')
NAMESPACE_X500 = UUID('{6ba7b814-9dad-11d1-80b4-00c04fd430c8}')
