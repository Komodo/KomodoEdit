
from wnd.api.shell.wintypes import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# stuff for icon extraction
#


class IExtractIcon(IUnknown):
	_iid_ = GUID("{000214EB-0000-0000-C000-000000000046}")
IExtractIcon._methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "GetIconLocation", (c_uint, 
                                               c_ulong,
                                               # addressof return buffer
                                               c_uint,
                                               POINTER(c_int),	# sizeof return buffer
                                               POINTER(c_uint))),
	STDMETHOD(HRESULT, "Extract", (LPSTR, c_uint, POINTER(c_ulong),
                                       POINTER(c_ulong), c_uint))]

class IShellIcon(IUnknown):
	_iid_ = GUID("{000214E5-0000-0000-C000-000000000046}")
IShellIcon._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "GetIconOf", (PIDL, c_uint, POINTER(c_int)))]

## some imports by ord
GetProcAddress.restype = WINFUNCTYPE(c_int, LPSTR, c_uint, BOOL)
SHGetCachedImageIndex = GetProcAddress(shell32._handle, 72)

