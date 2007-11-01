# comtypes.automation module
from ctypes import *
from _ctypes import CopyComPointer
from comtypes import IUnknown, GUID, IID, STDMETHOD, BSTR, COMMETHOD, COMError
from comtypes.hresult import *
from comtypes.partial import partial

import datetime # for VT_DATE, standard in Python 2.3 and up
import array
try:
    import decimal # standard in Python 2.4 and up
except ImportError:
    decimal = None
    
from ctypes.wintypes import VARIANT_BOOL
from ctypes.wintypes import WORD
from ctypes.wintypes import UINT
from ctypes.wintypes import DWORD
from ctypes.wintypes import LONG

from ctypes.wintypes import WCHAR

LCID = DWORD
DISPID = LONG
SCODE = LONG

VARTYPE = c_ushort

DISPATCH_METHOD = 1
DISPATCH_PROPERTYGET = 2
DISPATCH_PROPERTYPUT = 4
DISPATCH_PROPERTYPUTREF = 8

tagINVOKEKIND = c_int
INVOKE_FUNC = DISPATCH_METHOD
INVOKE_PROPERTYGET = DISPATCH_PROPERTYGET
INVOKE_PROPERTYPUT = DISPATCH_PROPERTYPUT
INVOKE_PROPERTYPUTREF = DISPATCH_PROPERTYPUTREF
INVOKEKIND = tagINVOKEKIND


################################
# helpers
IID_NULL = GUID()
riid_null = byref(IID_NULL)
_VariantClear = oledll.oleaut32.VariantClear
_SysAllocStringLen = oledll.oleaut32.SysAllocStringLen
_VariantCopyInd = oledll.oleaut32.VariantCopyInd

# 30. December 1899, midnight.  For VT_DATE.
_com_null_date = datetime.datetime(1899, 12, 30, 0, 0, 0)

################################################################
# VARIANT, in all it's glory.
VARENUM = c_int # enum
VT_EMPTY = 0
VT_NULL = 1
VT_I2 = 2
VT_I4 = 3
VT_R4 = 4
VT_R8 = 5
VT_CY = 6
VT_DATE = 7
VT_BSTR = 8
VT_DISPATCH = 9
VT_ERROR = 10
VT_BOOL = 11
VT_VARIANT = 12
VT_UNKNOWN = 13
VT_DECIMAL = 14
VT_I1 = 16
VT_UI1 = 17
VT_UI2 = 18
VT_UI4 = 19
VT_I8 = 20
VT_UI8 = 21
VT_INT = 22
VT_UINT = 23
VT_VOID = 24
VT_HRESULT = 25
VT_PTR = 26
VT_SAFEARRAY = 27
VT_CARRAY = 28
VT_USERDEFINED = 29
VT_LPSTR = 30
VT_LPWSTR = 31
VT_RECORD = 36
VT_INT_PTR = 37
VT_UINT_PTR = 38
VT_FILETIME = 64
VT_BLOB = 65
VT_STREAM = 66
VT_STORAGE = 67
VT_STREAMED_OBJECT = 68
VT_STORED_OBJECT = 69
VT_BLOB_OBJECT = 70
VT_CF = 71
VT_CLSID = 72
VT_VERSIONED_STREAM = 73
VT_BSTR_BLOB = 4095
VT_VECTOR = 4096
VT_ARRAY = 8192
VT_BYREF = 16384
VT_RESERVED = 32768
VT_ILLEGAL = 65535
VT_ILLEGALMASKED = 4095
VT_TYPEMASK = 4095

class tagCY(Structure):
    _fields_ = [("int64", c_longlong)]
CY = tagCY
CURRENCY = CY

# The VARIANT structure is a good candidate for implementation in a C
# helper extension.  At least the get/set methods.
class tagVARIANT(Structure):
    # The C Header file defn of VARIANT is much more complicated, but
    # this is the ctypes version - functional as well.
    class U_VARIANT(Union):
        _fields_ = [
            ("VT_BOOL", VARIANT_BOOL),
            ("VT_I1", c_byte),
            ("VT_I2", c_short),
            ("VT_I4", c_long),
            ("VT_INT", c_int),
            ("VT_UI1", c_ubyte),
            ("VT_UI2", c_ushort),
            ("VT_UI4", c_ulong),
            ("VT_UINT", c_uint),
            ("VT_R4", c_float),
            ("VT_R8", c_double),
            ("VT_CY", c_longlong),
            ("c_wchar_p", c_wchar_p),
            ("c_void_p", c_void_p),

            ("bstrVal", BSTR),
            # placeholder only, for the correct size:
            #struct  __tagBRECORD
            #    {
            #        PVOID pvRecord;
            #        IRecordInfo __RPC_FAR *pRecInfo;
            #    }__VARIANT_NAME_4;
            ("__tagBRECORD", c_void_p * 2),
            ]
    _fields_ = [("vt", VARTYPE),
                ("wReserved1", c_ushort),
                ("wReserved2", c_ushort),
                ("wReserved3", c_ushort),
                ("_", U_VARIANT)
    ]

    def __init__(self, *args):
        if args:
            self.value = args[0]

    def __del__(self):
        if self._b_needsfree_:
            # XXX This does not work.  _b_needsfree_ is never
            # set because the buffer is internal to the object.
            _VariantClear(byref(self))

    def __repr__(self):
        return "VARIANT(%r)" % (self.value,)

    def from_param(cls, value):
        if isinstance(value, cls):
            return value
        return cls(value)
    from_param = classmethod(from_param)

    # see also c:/sf/pywin32/com/win32com/src/oleargs.cpp 54
    def _set_value(self, value):
        _VariantClear(byref(self))
        if value is None:
            self.vt = VT_NULL
        # since bool is a subclass of int, this check must come before
        # the check for int
        elif isinstance(value, bool):
            self.vt = VT_BOOL
            self._.VT_BOOL = value
        elif isinstance(value, int):
            self.vt = VT_I4
            self._.VT_I4 = value
        elif isinstance(value, long):
            u = self._
            # try VT_I4 first.
            u.VT_I4 = value
            if u.VT_I4 == value:
                # it did work.
                self.vt = VT_I4
                return
            # try VT_UI4 next.
            if value >= 0:
                u.VT_UI4 = value
                if u.VT_UI4 == value:
                    # did work.
                    self.vt = VT_UI4
                    return
            # VT_R8 is last resort.
            self.vt = VT_R8
            u.VT_R8 = float(value)
        elif isinstance(value, float):
            self.vt = VT_R8
            self._.VT_R8 = value
        elif isinstance(value, (str, unicode)):
            self.vt = VT_BSTR
            # do the c_wchar_p auto unicode conversion
            self._.c_void_p = _SysAllocStringLen(c_wchar_p.from_param(value), len(value))
        elif isinstance(value, datetime.datetime):
            delta = value - _com_null_date
            # a day has 24 * 60 * 60 = 86400 seconds
            com_days = delta.days + (delta.seconds + delta.microseconds * 1e-6) / 86400.
            self.vt = VT_DATE
            self._.VT_R8 = com_days
        elif decimal is not None and isinstance(value, decimal.Decimal):
            self._.VT_CY = int(round(value * 10000))
        elif isinstance(value, POINTER(IDispatch)):
            CopyComPointer(value, byref(self._))
            self.vt = VT_DISPATCH
        elif isinstance(value, POINTER(IUnknown)):
            CopyComPointer(value, byref(self._))
            self.vt = VT_UNKNOWN
        elif isinstance(value, (list, tuple)):
            from comtypes.safearray import SafeArray_FromSequence
            self._.c_void_p = cast(SafeArray_FromSequence(value), c_void_p)
            self.vt = VT_ARRAY | VT_VARIANT
        elif isinstance(value, array.array):
            from comtypes.safearray import SafeArray_FromArray
            typecode, psa = SafeArray_FromArray(value)
            self._.c_void_p = cast(psa, c_void_p)
            self.vt = VT_ARRAY | typecode
        else:
            raise "VARIANT _set_value, NYI", value
        # buffer ->  SAFEARRAY of VT_UI1 ?

    # c:/sf/pywin32/com/win32com/src/oleargs.cpp 197
    def _get_value(self):
        vt = self.vt
        if vt in (VT_EMPTY, VT_NULL):
            return None
        elif vt == VT_I1:
            return self._.VT_I1
        elif vt == VT_I2:
            return self._.VT_I2
        elif vt == VT_I4:
            return self._.VT_I4
        elif vt == VT_INT:
            return self._.VT_INT
        elif vt == VT_UI1:
            return self._.VT_UI1
        elif vt == VT_UI2:
            return self._.VT_UI2
        elif vt == VT_UI4:
            return self._.VT_UI4
        elif vt == VT_UINT:
            return self._.VT_UINT
        elif vt == VT_R4:
            return self._.VT_R4
        elif vt == VT_R8:
            return self._.VT_R8
        elif vt == VT_BOOL:
            return self._.VT_BOOL
        elif vt == VT_BSTR:
            return self._.bstrVal
        elif vt == VT_DATE:
            days = self._.VT_R8
            return datetime.timedelta(days=days) + _com_null_date
        elif vt == VT_CY:
            if decimal is not None:
                return self._.VT_CY / decimal.Decimal("10000")
            else:
                return self._.VT_CY / 10000.
        elif vt == VT_UNKNOWN:
            val = self._.c_void_p
            if not val:
                # We should/could return a NULL COM pointer.
                # But the code generation must be able to construct one
                # from the __repr__ of it.
                return None # XXX?
            ptr = cast(val, POINTER(IUnknown))
            # cast doesn't call AddRef (it should, imo!)
            ptr.AddRef()
            return ptr.__ctypes_from_outparam__()
        elif vt == VT_DISPATCH:
            val = self._.c_void_p
            if not val:
                # See above.
                return None # XXX?
            ptr = cast(val, POINTER(IDispatch))
            # cast doesn't call AddRef (it should, imo!)
            ptr.AddRef()
            return ptr.__ctypes_from_outparam__()
        # see also c:/sf/pywin32/com/win32com/src/oleargs.cpp
        elif vt == VT_BYREF|VT_VARIANT:
            # apparently VariantCopyInd doesn't work with
            # VT_BREF|VT_VARIANT, so do it manually.
            v = cast(self._.c_void_p, POINTER(VARIANT))[0]
            return v.value
        elif self.vt & VT_BYREF:
            v = VARIANT()
            _VariantCopyInd(byref(v), byref(self))
            return v.value
        elif self.vt & VT_ARRAY:
            from comtypes.safearray import UnpackSafeArray
            return UnpackSafeArray(self._.c_void_p)
        else:
            raise NotImplementedError("typecode %d = 0x%x)" % (vt, vt))

# these are missing:
##    getter[VT_ERROR]
##    getter[VT_ARRAY]
##    getter[VT_BYREF|VT_UI1]
##    getter[VT_BYREF|VT_I2]
##    getter[VT_BYREF|VT_I4]
##    getter[VT_BYREF|VT_R4]
##    getter[VT_BYREF|VT_R8]
##    getter[VT_BYREF|VT_BOOL]
##    getter[VT_BYREF|VT_ERROR]
##    getter[VT_BYREF|VT_CY]
##    getter[VT_BYREF|VT_DATE]
##    getter[VT_BYREF|VT_BSTR]
##    getter[VT_BYREF|VT_UNKNOWN]
##    getter[VT_BYREF|VT_DISPATCH]
##    getter[VT_BYREF|VT_ARRAY]
##    getter[VT_BYREF|VT_VARIANT]
##    getter[VT_BYREF]
##    getter[VT_BYREF|VT_DECIMAL]
##    getter[VT_BYREF|VT_I1]
##    getter[VT_BYREF|VT_UI2]
##    getter[VT_BYREF|VT_UI4]
##    getter[VT_BYREF|VT_INT]
##    getter[VT_BYREF|VT_UINT]

    value = property(_get_value, _set_value)

    def __ctypes_from_outparam__(self):
        # XXX Manual resource management, because of the VARIANT bug:
        result = self.value
        self.value = None
        return result

    def ChangeType(self, typecode):
        oledll.oleaut32.VariantChangeType(byref(self),
                                          byref(self),
                                          0,
                                          typecode)

VARIANT = tagVARIANT
VARIANTARG = VARIANT

# some commonly used VARIANT instances
VARIANT.empty = VARIANT(None)
VARIANT.null = VARIANT()
VARIANT.missing = v = VARIANT()
v.vt = VT_ERROR
v._.VT_I4 = 0x80020004L
del v

# Hack alert.  Make the VARIANT type available in the comtypes module,
# once comtypes.automation has been imported.  See comment in
# comtypes\__init__.py.
import comtypes
comtypes._VARIANT_type_hack = VARIANT

_carg_obj = type(byref(c_int()))
from _ctypes import Array as _CArrayType

class _(partial, POINTER(VARIANT)):
    # Override the default .from_param classmethod of POINTER(VARIANT).
    # This allows to pass values which can be stored in VARIANTs as
    # function parameters declared as POINTER(VARIANT).  See
    # InternetExplorer's Navigate2() method, or Word's Close() method, for
    # examples.
    def from_param(self, arg):
        # accept POINTER(VARIANT) instance
        if isinstance(arg, POINTER(VARIANT)):
            return arg
        # accept byref(VARIANT) instance
        if isinstance(arg, _carg_obj) and isinstance(arg._obj, VARIANT):
            return arg
        # accept VARIANT instance
        if isinstance(arg, VARIANT):
            return byref(arg)
        if isinstance(arg, _CArrayType) and arg._type_ is VARIANT:
            # accept array of VARIANTs
            return arg
        # anything else which can be converted to a VARIANT.
        return byref(VARIANT(arg))
    from_param = classmethod(from_param)

    def __setitem__(self, index, value):
        self[index].value = value

################################################################

class IEnumVARIANT(IUnknown):
    _iid_ = GUID('{00020404-0000-0000-C000-000000000046}')
    _idlflags_ = ['hidden']
    def __iter__(self):
        return self

    def next(self):
        item, fetched = self.Next(1)
        if fetched:
            return item
        raise StopIteration

    def __getitem__(self, index):
        self.Reset()
        # Does not yet work.
##        if isinstance(index, slice):
##            self.Skip(index.start or 0)
##            return self.Next(index.stop or sys.maxint)
        self.Skip(index)
        item, fetched = self.Next(1)
        if fetched:
            return item
        raise IndexError

    def Next(self, celt):
        if celt == 1:
            return self._Next(1)
        fetched = c_ulong()
        array = (VARIANT * celt)()
        self.__com_Next(celt, array, fetched)
        return [v.value for v in array[:fetched.value]]

IEnumVARIANT._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
              ( ['in'], c_ulong, 'celt' ),
              ( ['out'], POINTER(VARIANT), 'rgvar' ),
              ( ['out'], POINTER(c_ulong), 'pceltFetched' )),
    COMMETHOD([], HRESULT, 'Skip',
              ( ['in'], c_ulong, 'celt' )),
    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone',
              ( ['out'], POINTER(POINTER(IEnumVARIANT)), 'ppenum' )),
]


##from _ctypes import VARIANT_set
##import new
##VARIANT.value = property(VARIANT._get_value, new.instancemethod(VARIANT_set, None, VARIANT))


class tagEXCEPINFO(Structure):
    def __repr__(self):
        return "<EXCEPINFO %s>" % \
               ((self.wCode, self.bstrSource, self.bstrDescription, self.bstrHelpFile, self.dwHelpContext,
                self.pfnDeferredFillIn, self.scode),)
tagEXCEPINFO._fields_ = [
    ('wCode', WORD),
    ('wReserved', WORD),
    ('bstrSource', BSTR),
    ('bstrDescription', BSTR),
    ('bstrHelpFile', BSTR),
    ('dwHelpContext', DWORD),
    ('pvReserved', c_void_p),
##    ('pfnDeferredFillIn', WINFUNCTYPE(HRESULT, POINTER(tagEXCEPINFO))),
    ('pfnDeferredFillIn', c_void_p),
    ('scode', SCODE),
]
EXCEPINFO = tagEXCEPINFO

class tagDISPPARAMS(Structure):
    _fields_ = [
        # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 696
        ('rgvarg', POINTER(VARIANTARG)),
        ('rgdispidNamedArgs', POINTER(DISPID)),
        ('cArgs', UINT),
        ('cNamedArgs', UINT),
    ]
    def __del__(self):
        if self._b_needsfree_:
            for i in range(self.cArgs):
                self.rgvarg[i].value = None
DISPPARAMS = tagDISPPARAMS

DISPID_VALUE = 0
DISPID_UNKNOWN = -1
DISPID_PROPERTYPUT = -3
DISPID_NEWENUM = -4
DISPID_EVALUATE = -5
DISPID_CONSTRUCTOR = -6
DISPID_DESTRUCTOR = -7
DISPID_COLLECT = -8

class IDispatch(IUnknown):
    _iid_ = GUID("{00020400-0000-0000-C000-000000000046}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetTypeInfoCount',
                  (['out'], POINTER(UINT) ) ),
        COMMETHOD([], HRESULT, 'GetTypeInfo',
                  (['in'], UINT, 'index'),
                  (['in'], LCID, 'lcid', 0),
## Normally, we would declare this parameter in this way:
##                  (['out'], POINTER(POINTER(ITypeInfo)) ) ),
## but we cannot import comtypes.typeinfo at the top level (recursive imports!).
                  (['out'], POINTER(POINTER(IUnknown)) ) ),
        STDMETHOD(HRESULT, 'GetIDsOfNames', [POINTER(IID), POINTER(c_wchar_p),
                                             UINT, LCID, POINTER(DISPID)]),
        STDMETHOD(HRESULT, 'Invoke', [DISPID, POINTER(IID), LCID, WORD,
                                      POINTER(DISPPARAMS), POINTER(VARIANT),
                                      POINTER(EXCEPINFO), POINTER(UINT)]),
    ]

    def GetTypeInfo(self, index, lcid=0):
        """Return type information.  Index 0 specifies typeinfo for IDispatch"""
        import comtypes.typeinfo
        # we could also use cast instead of QueryInterface.  Does it matter?
        result = self._GetTypeInfo(index, lcid)
        return result.QueryInterface(comtypes.typeinfo.ITypeInfo)

    def GetIDsOfNames(self, *names, **kw):
        """Map string names to integer ids."""
        lcid = kw.pop("lcid", 0)
        assert not kw
        arr = (c_wchar_p * len(names))(*names)
        ids = (DISPID * len(names))()
        self.__com_GetIDsOfNames(riid_null, arr, len(names), lcid, ids)
        return [i for i in ids]

    def Invoke(self, dispid, *args, **kw):
        """Invoke a method or property."""

        # Memory management in Dispatch::Invoke calls:
        # http://msdn.microsoft.com/library/en-us/automat/htm/chap5_4x2q.asp
        # Quote:
        #     The *CALLING* code is responsible for releasing all strings and
        #     objects referred to by rgvarg[ ] or placed in *pVarResult.
        #
        # For comtypes this is handled in DISPPARAMS.__del__ and VARIANT.__del__.
        _invkind = kw.pop("_invkind", 1) # DISPATCH_METHOD
        _lcid = kw.pop("_lcid", 0) 
        if kw:
            raise ValueError, "named parameters not yet implemented"

        result = VARIANT()
        excepinfo = EXCEPINFO()
        argerr = c_uint()

        if _invkind == DISPATCH_PROPERTYPUT: # propput
            assert len(args) == 1
            dp = DISPPARAMS()
            dp.cArgs = 1
            dp.cNamedArgs = 1
            dp.rgvarg = pointer(VARIANT(args[0]))
            dp.rgdispidNamedArgs = pointer(DISPID(DISPID_PROPERTYPUT))
        else:
            array = (VARIANT * len(args))()

            for i, a in enumerate(args[::-1]):
                array[i].value = a

            dp = DISPPARAMS()
            dp.cArgs = len(args)
            dp.cNamedArgs = 0
            dp.rgvarg = array

        try:
            self.__com_Invoke(dispid, riid_null, _lcid, _invkind, byref(dp),
                              byref(result), byref(excepinfo), byref(argerr))
        except COMError, (hresult, text, details):
            if hresult == DISP_E_EXCEPTION:
                details = (excepinfo.bstrDescription, excepinfo.bstrSource,
                           excepinfo.bstrHelpFile, excepinfo.dwHelpContext,
                           excepinfo.scode)
                raise COMError(hresult, text, details)
            elif hresult == DISP_E_PARAMNOTFOUND:
                # MSDN says: You get the error DISP_E_PARAMNOTFOUND
                # when you try to set a property and you have not
                # initialized the cNamedArgs and rgdispidNamedArgs
                # elements of your DISPPARAMS structure.
                #
                # So, this looks like a bug.
                raise COMError(hresult, text, argerr.value)
            elif hresult == DISP_E_TYPEMISMATCH:
                # MSDN: One or more of the arguments could not be
                # coerced.
                #
                # Hm, should we raise TypeError, or COMError?
                raise COMError(hresult, text,
                               ("TypeError: Parameter %s" % (argerr.value + 1),
                                args))
            raise
        return result.value

    # XXX Would separate methods for _METHOD, _PROPERTYGET and _PROPERTYPUT be better?


VT2CTYPE = {
    VT_R4: c_float,
    VT_R8: c_double,
    VT_I4: c_long,
    VT_INT: c_int,
    VT_UI4: c_ulong,
    VT_VOID: None,
    VT_BSTR: BSTR,
    VT_DISPATCH: POINTER(IDispatch),
    VT_HRESULT: HRESULT,
    VT_VARIANT: VARIANT,
    VT_BOOL: VARIANT_BOOL,
    }

def _midlSAFEARRAY(aType):
    from comtypes.safearray import SAFEARRAY
    return POINTER(SAFEARRAY)
