
from ctypes.com import IUnknown, GUID, STDMETHOD, HRESULT
from wnd.api.ole.wintypes import (STATDATA,
																POINTER,
																c_ulong)
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class IEnumSTATDATA(IUnknown):
    _iid_ = GUID("{00000105-0000-0000-C000-000000000046}")
  
IEnumSTATDATA. _methods_ = IUnknown._methods_ + [

	STDMETHOD(HRESULT, "Next", c_ulong, POINTER(STATDATA), POINTER(c_ulong)),
	STDMETHOD(HRESULT, "Skip", c_ulong),
	STDMETHOD(HRESULT, "Reset"),
	STDMETHOD(HRESULT, "Clone", POINTER(POINTER(IEnumSTATDATA))),
	]