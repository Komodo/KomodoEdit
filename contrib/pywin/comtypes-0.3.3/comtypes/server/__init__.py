import comtypes, ctypes

################################################################
# Interfaces
class IClassFactory(comtypes.IUnknown):
    _iid_ = comtypes.GUID("{00000001-0000-0000-C000-000000000046}")
    _methods_ = [
        comtypes.STDMETHOD(comtypes.HRESULT, "CreateInstance",
                           [ctypes.c_int, ctypes.POINTER(comtypes.GUID), ctypes.POINTER(ctypes.c_ulong)]),
        comtypes.STDMETHOD(comtypes.HRESULT, "LockServer",
                           [ctypes.c_int])]

##class IExternalConnection(IUnknown):
##    _iid_ = GUID("{00000019-0000-0000-C000-000000000046}")
##    _methods_ = [
##        STDMETHOD(HRESULT, "AddConnection", [c_ulong, c_ulong]),
##        STDMETHOD(HRESULT, "ReleaseConnection", [c_ulong, c_ulong, c_ulong])]
