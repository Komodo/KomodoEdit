# very thin safearray support
from ctypes import *
from comtypes.typeinfo import SAFEARRAYBOUND
from comtypes.automation import VARIANT, VARTYPE, BSTR
from comtypes.automation import VT_VARIANT, VT_R4, VT_R8, VT_I1, VT_I2, VT_I4, VT_INT, VT_UI1, VT_UI2, VT_UI4, VT_UINT, VT_BSTR

class SAFEARRAY(Structure):
    _fields_ = [("cDims", c_ushort),
                ("fFeatures", c_ushort),
                ("cbElements", c_ulong),
                ("cLocks", c_ulong),
                ("pvData", c_void_p),
                ("rgsabound", SAFEARRAYBOUND * 1)]

    def dump(self):
        print "cDims", self.cDims
        print "fFeatures 0x%x" % self.fFeatures
        print "cLocks", self.cLocks
        print "cbElements", self.cbElements


    def __getitem__(self, index):
        ix = c_int(index)
        data = c_double()
        res = SafeArrayGetElement(byref(self), byref(ix), byref(data))
        if res:
            raise WinError(res)
        return data.value

    def __iter__(self):
        ix = c_int()
        data = c_double()
        get = SafeArrayGetElement
        while 1:
            if get(byref(self), byref(ix), byref(data)):
                raise StopIteration
            yield data.value
            ix.value += 1

# XXX
# Seems to work, but not tested enough.
##@ classmethod
##def from_param(cls, arg):
##    if not isinstance(arg, cls._type_):
##        arg = SafeArray_FromSequence(arg)
##    return byref(arg)
##POINTER(POINTER(SAFEARRAY)).from_param = from_param

# XXX For whatever reason, oleaut32.SafeArrayCreateVector does not seem to work correctly
# on the Win2k system I have.  The result cannot be passed successfully to SafeArrayGetVartype,
# the call fails with E_INVALIDARG because FADF_HAVEVARTYPE is not set.
# SafeArrayCreateEx DOES work, as it seems.
# BTW: A C program has the same behaviour.

SafeArrayCreateVectorEx = windll.oleaut32.SafeArrayCreateVectorEx
SafeArrayCreateVectorEx.restype = POINTER(SAFEARRAY)

SafeArrayPutElement = oledll.oleaut32.SafeArrayPutElement
SafeArrayPutElement.argtypes = (c_void_p, POINTER(c_long), c_void_p)

SafeArrayGetElement = oledll.oleaut32.SafeArrayGetElement
SafeArrayGetElement.argtypes = (c_void_p, POINTER(c_long), c_void_p)

SafeArrayAccessData = oledll.oleaut32.SafeArrayAccessData
SafeArrayAccessData.argtypes = (c_void_p, POINTER(c_void_p))

SafeArrayUnaccessData = oledll.oleaut32.SafeArrayUnaccessData
SafeArrayUnaccessData.argtypes = (c_void_p,)

SafeArrayGetVartype = oledll.oleaut32.SafeArrayGetVartype
SafeArrayGetVartype.argtypes = (c_void_p, POINTER(VARTYPE))

SafeArrayCreate = windll.oleaut32.SafeArrayCreate
SafeArrayCreate.argtypes = (VARTYPE, c_uint, POINTER(SAFEARRAYBOUND))
SafeArrayCreate.restype = POINTER(SAFEARRAY)

SafeArrayGetUBound = oledll.oleaut32.SafeArrayGetUBound
SafeArrayGetUBound.argtypes = (c_void_p, c_uint, POINTER(c_long))

SafeArrayGetLBound = oledll.oleaut32.SafeArrayGetLBound
SafeArrayGetLBound.argtypes = (c_void_p, c_uint, POINTER(c_long))

SafeArrayGetDim = oledll.oleaut32.SafeArrayGetDim
SafeArrayGetDim.restype = c_uint

################################################################

def SafeArray_FromSequence(seq):
    """Create a one dimensional safearray of type VT_VARIANT from a
    sequence of Python objects
    """
    psa = SafeArrayCreateVectorEx(VT_VARIANT, 0, len(seq), None)
    for index, elem in enumerate(seq):
        SafeArrayPutElement(psa, byref(c_long(index)), byref(VARIANT(elem)))
    return psa

def SafeArray_FromArray(arr):
    """Create a one dimensional safearray of a numeric type from an
    array instance"""
    TYPECODE = {
        "d": VT_R8,
        "f": VT_R4,
        "l": VT_I4,
        "i": VT_INT,
        "h": VT_I2,
        "b": VT_I1,
        "I": VT_UINT,
        "L": VT_UI4,
        "H": VT_UI2,
        "B": VT_UI1,
        }
    vt = TYPECODE[arr.typecode]
    psa = SafeArrayCreateVectorEx(vt, 0, len(arr), None)
    ptr = c_void_p()
    SafeArrayAccessData(psa, byref(ptr))
    memmove(ptr, arr.buffer_info()[0], len(arr) * arr.itemsize)
    SafeArrayUnaccessData(psa)
    return vt, psa

################################################################

def _get_row(ctype, psa, dim, indices, lowerbounds, upperbounds):
    # loop over the index of dimension 'dim'
    # we have to restore the index of the dimension we're looping over
    restore = indices[dim]

    result = []
    if dim+1 == len(indices):
        for i in range(indices[dim], upperbounds[dim]+1):
            indices[dim] = i
            SafeArrayGetElement(psa, indices, byref(ctype))
            result.append(ctype.value)
    else:
        for i in range(indices[dim], upperbounds[dim]+1):
            indices[dim] = i
            result.append(_get_row(ctype, psa, dim+1, indices, lowerbounds, upperbounds))
    indices[dim] = restore
    return tuple(result) # for compatibility with pywin32.

_VT2CTYPE = {
    VT_BSTR: BSTR,
    VT_I1: c_byte,
    VT_I2: c_short,
    VT_I4: c_long,
    VT_INT: c_int,
    VT_R4: c_float,
    VT_R8: c_double,
    VT_UI1: c_ubyte,
    VT_UI2: c_ushort,
    VT_UI4: c_ulong,
    VT_UINT: c_uint,
    VT_VARIANT: VARIANT,
    }

def _get_datatype(psa):
    # Return the ctypes data type corresponding to the SAFEARRAY's typecode.
    vt = VARTYPE()
    SafeArrayGetVartype(psa, byref(vt))
    return _VT2CTYPE[vt.value]

def _get_ubound(psa, dim):
    # Return the upper bound of a dimension in a safearray
    ubound = c_long()
    SafeArrayGetUBound(psa, dim+1, byref(ubound))
    return ubound.value

def _get_lbound(psa, dim):
    # Return the lower bound of a dimension in a safearray
    lb = c_long()
    SafeArrayGetLBound(psa, dim+1, byref(lb))
    return lb.value

def UnpackSafeArray(psa):
    """Unpack a SAFEARRAY into a Python tuple."""
    dim = SafeArrayGetDim(psa)
    lowerbounds = [_get_lbound(psa, d) for d in range(dim)]
    indexes = (c_long * dim)(*lowerbounds)
    upperbounds = [_get_ubound(psa, d) for d in range(dim)]
    return _get_row(_get_datatype(psa)(), psa, 0, indexes, lowerbounds, upperbounds)

################################################################

if __name__ == "__main__":
    for dim in range(1, 4):

        if dim == 2:
            rgsa = (SAFEARRAYBOUND * 2)()
            rgsa[0].lLbound = 3
            rgsa[0].cElements = 9
            rgsa[1].lLbound = 7
            rgsa[1].cElements = 6

        elif dim == 1:
            rgsa = (SAFEARRAYBOUND * 1)()
            rgsa[0].lLbound = 3
            rgsa[0].cElements = 9

        elif dim == 3:

            rgsa = (SAFEARRAYBOUND * 3)()
            rgsa[0].lLbound = 1
            rgsa[0].cElements = 6
            rgsa[1].lLbound = 2
            rgsa[1].cElements = 5
            rgsa[2].lLbound = 3
            rgsa[2].cElements = 4
        else:
            raise ValueError("dim %d not supported" % dim)
        psa = SafeArrayCreate(VT_BSTR, len(rgsa), rgsa)

        n = 1
        for b in rgsa:
            n *= b.cElements
        print "%d total elements" % n

##        ptr = POINTER(BSTR)()

##        SafeArrayAccessData(psa, byref(ptr))
##        array = (BSTR * n)(*map(str, range(n)))
##        memmove(ptr, array, sizeof(array))
##        SafeArrayUnaccessData(psa)

##        import pprint
##        pprint.pprint(UnpackSafeArray(psa))

##    v = VARIANT()
##    v.value = [("1",), (2, 3, None)]
##    print v.value
