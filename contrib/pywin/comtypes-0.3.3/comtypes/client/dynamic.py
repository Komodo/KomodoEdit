import ctypes
import comtypes.automation
import comtypes.typeinfo
import comtypes.client

from comtypes import COMError
import comtypes.hresult as hres

# These errors generally mean the property or method exists,
# but can't be used in this context - eg, property instead of a method, etc.
# Used to determine if we have a real error or not.
ERRORS_BAD_CONTEXT = [
    hres.DISP_E_MEMBERNOTFOUND,
    hres.DISP_E_BADPARAMCOUNT,
    hres.DISP_E_PARAMNOTOPTIONAL,
    hres.DISP_E_TYPEMISMATCH,
    hres.E_INVALIDARG,
]

def Dispatch(obj):
    # Wrap an object in a Dispatch instance, exposing methods and properties
    # via fully dynamic dispatch
    if isinstance(obj, _Dispatch):
        return obj
    if isinstance(obj, ctypes.POINTER(comtypes.automation.IDispatch)):
        return _Dispatch(obj)
    return obj

class MethodCaller:
    kw = dict(_invkind=comtypes.automation.DISPATCH_METHOD)
    
    def __init__(self, _id, _obj):
        self._id = _id
        self._obj = _obj
        
    def __call__(self, *args):
        return self._obj._comobj.Invoke(self._id, *args, **self.kw)

class _Dispatch(object):
    # Expose methods and properties via fully dynamic dispatch
    def __init__(self, comobj):
        self._comobj = comobj
        self._ids = {} # Tiny optimization: trying not to use GetIDsOfNames more than once

    def __enum(self):
        e = self._comobj.Invoke(-4) # DISPID_NEWENUM
        return e.QueryInterface(comtypes.automation.IEnumVARIANT)

    def __getitem__(self, index):
        enum = self.__enum()
        if index > 0:
            if 0 != enum.Skip(index):
                raise IndexError, "index out of range"
        item, fetched = enum.Next(1)
        if not fetched:
            raise IndexError, "index out of range"
        return item

    def QueryInterface(self, *args):
        "QueryInterface is forwarded to the real com object."
        return self._comobj.QueryInterface(*args)

    def __getattr__(self, name):
##        tc = self._comobj.GetTypeInfo(0).QueryInterface(comtypes.typeinfo.ITypeComp)
##        dispid = tc.Bind(name)[1].memid
        dispid = self._ids.get(name)
        if not dispid:
            dispid = self._comobj.GetIDsOfNames(name)[0]
            self._ids[name] = dispid
        
        flags = comtypes.automation.DISPATCH_PROPERTYGET
        try:
            result = self._comobj.Invoke(dispid, _invkind=flags)
        except COMError, (hresult, text, details):
            if hresult in ERRORS_BAD_CONTEXT:
                result = MethodCaller(dispid, self)
                setattr(self, name, result)
            else: raise
        except: raise
        
        return result

    def __iter__(self):
        return _Collection(self.__enum())

##    def __setitem__(self, index, value):
##        self._comobj.Invoke(-3, index, value,
##                            _invkind=comtypes.automation.DISPATCH_PROPERTYPUT|comtypes.automation.DISPATCH_PROPERTYPUTREF)

class _Collection(object):
    def __init__(self, enum):
        self.enum = enum

    def next(self):
        item, fetched = self.enum.Next(1)
        if fetched:
            return item
        raise StopIteration

    def __iter__(self):
        return self

__all__ = ["Dispatch"]
