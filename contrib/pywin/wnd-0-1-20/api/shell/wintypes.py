#
from wnd.wintypes import *
from ctypes.com import IUnknown, STDMETHOD, HRESULT, GUID, ole32, REFIID
from ctypes.com.mallocspy import IMalloc, MallocSpy
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
import locale
LOCALE= locale.getdefaultlocale()[1]

#********************************************************************************


Malloc=POINTER(IMalloc)()
shell32.SHGetMalloc(byref(Malloc))

GetProcAddress = kernel32.GetProcAddress

HRESULT_CODE = lambda HRESULT: HRESULT & 0xFFFF

class SHITEMID(Structure):
	_fields_ = [("cb", c_ushort),
				("abID", c_ubyte * 1)] # variable length, in reality

class ITEMIDLIST(Structure):
	_fields_ = [("mkid", SHITEMID)]
PIDL = POINTER(ITEMIDLIST)


class SHFILEINFO(Structure):
	_fields_ = [("hIcon", HICON),
					("iIcon", INT),
					("dwAttributes", DWORD),
					("szDisplayName", CHAR*260),
					("szTypeName", CHAR*80)]


class CMINVOKECOMMANDINFO(Structure):
	_fields_ = [("cbSize", DWORD),
					("fMask", DWORD),
					("hwnd", HWND),
					("lpVerb", DWORD),	#  LPSTR in reality
															# but we have to place a
															# cmdOffset or a string in there
					("lpParameters", LPCSTR),
					("lpDirectory", LPCSTR),
					("nShow", INT),
					("dwHotKey", DWORD),
					("hIcon", HANDLE)]

	def __init__(self): self.cbSize= sizeof(self)


class CMINVOKECOMMANDINFOEX(Structure):
	_fields_ = [("cbSize", DWORD),
					("fMask", DWORD),
					("hwnd", HWND),
					("lpVerb", DWORD),
					("lpParameters", LPCSTR),
					("lpDirectory", LPCSTR),
					("nShow", INT),
					("dwHotKey", DWORD),
					("hIcon", HANDLE),
					("lpTitle", LPCSTR),
					("lpVerbW", LPCWSTR),
					("lpParametersW", LPCWSTR),
					("lpDirectoryW", LPCWSTR),
					("lpTitleW", LPCWSTR),
					("ptInvoke", POINT)]
	def __init__(self): self.cbSize= sizeof(self)

#****************************************************************************
# shell folder stuff


class STRRET(Structure):
	class U(Union):
		_fields_ = [("pOleStr", LPWSTR), 
						("pStr", LPSTR),
						("uOffset", c_uint),
						("cStr", c_char * 260)]
	_fields_ = [("uType", c_uint),
					("_", U)] 

try:
	# check if we can get StrRetToBuf api, introduced with IE5
	StrRetToBuf=  windll.shlwapi.StrRetToBufA
	NAME_BUFFER= create_string_buffer(MAX_PATH +1)
except:
	pass
	

class IEnumIDList(IUnknown):
	_iid_ = GUID("{000214F2-0000-0000-C000-000000000046}")
IEnumIDList._methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "Next", c_ulong,POINTER(POINTER(ITEMIDLIST)),
                      POINTER(c_ulong)),
	STDMETHOD(HRESULT, "Skip", c_ulong),
	STDMETHOD(HRESULT, "Reset"),
	STDMETHOD(HRESULT, "Clone", POINTER(POINTER(IEnumIDList)))]

class IShellFolder(IUnknown):
	_iid_ = GUID("{000214E6-0000-0000-C000-000000000046}")
IShellFolder._methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "ParseDisplayName", HWND,
    c_void_p, LPOLESTR, POINTER(c_ulong), POINTER(PIDL), POINTER(c_ulong)),
	STDMETHOD(HRESULT, "EnumObjects", HWND, DWORD, POINTER(POINTER(IEnumIDList))),
	STDMETHOD(HRESULT, "BindToObject", PIDL , c_void_p, REFIID, POINTER(POINTER(IUnknown))),
	STDMETHOD(HRESULT, "BindToStorage", POINTER(ITEMIDLIST), c_void_p, REFIID, POINTER(POINTER(IUnknown))),
	STDMETHOD(HRESULT, "CompareIDs", LPARAM,PIDL, PIDL),
	STDMETHOD(HRESULT, "CreateViewObject", HWND, REFIID, POINTER(POINTER(IUnknown))),
	STDMETHOD(HRESULT, "GetAttributesOf", c_uint, POINTER(POINTER(ITEMIDLIST)),	# idl array in reality
	POINTER(c_ulong)),
	STDMETHOD(HRESULT, "GetUIObjectOf", HWND, c_uint, POINTER(POINTER(ITEMIDLIST)),		#  idl array in reality
	REFIID, POINTER(c_uint),
	POINTER(POINTER(IUnknown))),
	STDMETHOD(HRESULT, "GetDisplayNameOf", POINTER(ITEMIDLIST), DWORD, POINTER(STRRET)),
	STDMETHOD(HRESULT, "SetNameOf", HWND, POINTER(ITEMIDLIST),  OLESTR, DWORD,
                                 POINTER(PIDL))]

SHCONTF_FOLDERS = 32
SHCONTF_NONFOLDERS = 64
SHCONTF_INCLUDEHIDDEN = 128

STRRET_WSTR  =   0x0000          # Use STRRET.pOleStr
STRRET_OFFSET =  0x0001          # Use STRRET.uOffset to Ansi
STRRET_CSTR =    0x0002          # Use STRRET.cStr

SHGDN_FORPARSING = 0x8000	
SHGDN_FORADDRESSBAR = 0x4000


#*************************************************
# context menu stuff

class IContextMenu(IUnknown):
	_iid_ =  GUID("{000214E4-0000-0000-C000-000000000046}")

IContextMenu._methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "QueryContextMenu", c_ulong, c_uint, c_uint, c_uint, c_uint),
	STDMETHOD(HRESULT, "InvokeCommand", POINTER(CMINVOKECOMMANDINFOEX)),                           
	STDMETHOD(HRESULT, "GetCommandString",  c_uint, c_uint, c_uint, c_ulong,	# addressof buffer
	c_uint)]

class IContextMenu2(IUnknown):
	_iid_ =  GUID("{000214F4-0000-0000-C000-000000000046}")
IContextMenu2._methods_ = IContextMenu._methods_ + [
    STDMETHOD(HRESULT, "HandleMenuMsg", c_uint, WPARAM, LPARAM)] 

class IContextMenu3(IUnknown):
	_iid_ =  GUID("{BCFCE0A0-EC17-11D0-8D10-00A0C90F2719}")
IContextMenu3._methods_ = IContextMenu._methods_ + [
    STDMETHOD(HRESULT, "HandleMenuMsg2", c_uint, WPARAM, LPARAM, POINTER(c_long))]




##  exported by ordinal: shell32 (77)    
# int SHMapPIDLToSystemImageListIndex(		
#    IShellFolder *psf,
#    LPCITEMIDLIST pidl,
#    int *piIndex
#);
## pIndex will receive the open icon if available. It will be  set to -1 if not available.
## retval is the index of the icon in the system imagelist or -1.
GPA= kernel32.GetProcAddress
GPA.restype= WINFUNCTYPE(INT, POINTER(IShellFolder), PIDL, POINTER(INT))
SHMapPIDLToSystemImageListIndex= GPA(shell32._handle, 77)

