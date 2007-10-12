
"""IEnumFORMATETC and 
Note: 
don't forgett to call OleInitialize before use.

"""

from wnd.api.ole.wintypes import *
from ctypes.com import (GUID,
											IUnknown,
											STDMETHOD,
											HRESULT,
											COMObject)
#*************************************************
class IEnumFORMATETC(IUnknown):
    _iid_ = GUID("{00000103-0000-0000-C000-000000000046}")

IEnumFORMATETC._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "Next", ULONG, POINTER(FORMATETC), POINTER(ULONG)),
    STDMETHOD(HRESULT, "Skip", ULONG),
    STDMETHOD(HRESULT, "Reset"),
    STDMETHOD(HRESULT, "Clone", POINTER(IEnumFORMATETC))]

## documented for anti-trust-case reasons and exported by ordinal
GPA= kernel32.GetProcAddress
GPA.restype= WINFUNCTYPE(
	HRESULT, 
	c_uint, 
	c_ulong,				## addr FORMATETC*1
	POINTER(POINTER(IEnumFORMATETC)))
#GPA.restype= WINFUNCTYPE(HRESULT, c_uint, FORMATETC*1, POINTER(POINTER(IEnumFORMATETC)))
SHCreateStdEnumFmtEtc= GPA(shell32._handle, 74)

#SHCreateStdEnumFmtEtc (74)
#HRESULT SHCreateStdEnumFmtEtc(      
 #   UINT cfmt,
 #   const FORMATETC afmt[],
#    IEnumFORMATETC **ppenumFormatEtc
#

