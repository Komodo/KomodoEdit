from ctypes import *

BYTE = c_byte
WORD = c_ushort
DWORD = c_ulong

_ole32 = oledll.ole32

_StringFromCLSID = _ole32.StringFromCLSID
_CoTaskMemFree = _ole32.CoTaskMemFree
_ProgIDFromCLSID = _ole32.ProgIDFromCLSID
_CLSIDFromString = _ole32.CLSIDFromString
_CLSIDFromProgID = _ole32.CLSIDFromProgID
_CoCreateGuid = _ole32.CoCreateGuid

# Note: Comparing GUID instances by comparing their buffers
# is slightly faster than using ole32.IsEqualGUID.

class GUID(Structure):
    _fields_ = [("Data1", DWORD),
                ("Data2", WORD),
                ("Data3", WORD),
                ("Data4", BYTE * 8)]

    def __init__(self, name=None):
        if name is not None:
            _CLSIDFromString(unicode(name), byref(self))

    def __repr__(self):
        return u'GUID("%s")' % unicode(self)

    def __unicode__(self):
        p = c_wchar_p()
        _StringFromCLSID(byref(self), byref(p))
        result = p.value
        _CoTaskMemFree(p)
        return result
    __str__ = __unicode__

    def __cmp__(self, other):
        if isinstance(other, GUID):
            return cmp(buffer(self), buffer(other))
        return -1

    def __nonzero__(self):
        return str(buffer(self)) != "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"

    def __eq__(self, other):
        return isinstance(other, GUID) and \
               buffer(self) == buffer(other)

    def __hash__(self):
        # We make GUID instances hashable, although they are mutable.
        return hash(buffer(self))

    def copy(self):
        return GUID(unicode(self))

    def from_progid(cls, progid):
        """Get guid from progid, ...
        """
        if hasattr(progid, "_reg_clsid_"):
            progid = progid._reg_clsid_
        if isinstance(progid, cls):
            return progid
        elif isinstance(progid, basestring):
            if progid.startswith("{"):
                return cls(progid)
            inst = cls()
            _CLSIDFromProgID(unicode(progid), byref(inst))
            return inst
        else:
            raise TypeError("Cannot construct guid from %r" % progid)
    from_progid = classmethod(from_progid)

    def as_progid(self):
        "Convert a GUID into a progid"
        progid = c_wchar_p()
        _ProgIDFromCLSID(byref(self), byref(progid))
        result = progid.value
        _CoTaskMemFree(progid)
        return result

    def create_new(cls):
        "Create a brand new guid"
        guid = cls()
        _CoCreateGuid(byref(guid))
        return guid
    create_new = classmethod(create_new)

__all__ = ["GUID"]
