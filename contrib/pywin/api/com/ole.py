"""Some missing ole interfaces
		
		IOleCommandTarget
		IDocHostUIHandler
		 IDataObject
		 IEnumFORMATETC
		 IDropSource
		 IDropTarget
"""

from ctypes.com import IUnknown, GUID, STDMETHOD, ole32
from ctypes.com.automation import VARIANT, IDispatch  
from ctypes.com.ole import (	IOleInPlaceActiveObject,
													IOleInPlaceFrame, 
													IOleInPlaceUIWindow,
													IAdviseSink,
													FORMATETC, 
													STGMEDIUM)

from ctypes.com.oleobject import IEnumSTATDATA
# IEnumSTATDATA is defined as fake IUnknown in ctypes.com.oleobject
# we'll se if we need IOleObject.EnumAdvise
#class IEnumSTATDATA(IUnknown):
#   _iid_ = GUID("{00000105-0000-0000-C000-000000000046}")

from ctypes.wintypes import *
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# creates an embeded ole object
# coclass= the object class to create
# IClientSide= interface for the class object to communicate with the container 
#								(usually IOleObject). May be None
# IStorage= IStorage pointer of an IStorage implementation (required)
# renderCap= one of the ole render capabilities flags (OLERENDER_*)
# formatetc= FORMATETC structure may be None depending on the renderCap flag
#
#	return value
#		the pointer to the requested interface to communicate with the class object
def OleCreate(object, coclass, IClientSite, IStorage, renderCap=0, formatetc=None):
	if IClientSite: IClientSite= byref(IClientSite)
	else: IClientSite= None
	if formatetc: formatetc= byref(formatetc)
	else: formatetc= None
	p= POINTER(coclass)()
	ole32.OleCreate(
			byref(GUID(object._reg_clsid_)),
			byref(coclass._iid_),
			renderCap,
			formatetc,
			IClientSite,
			byref(IStorage),
			byref(p))
	return p


#*******************************************************************************************

class IEnumFORMATETC(IUnknown):
    _iid_ = GUID("{00000103-0000-0000-C000-000000000046}")

IEnumFORMATETC._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "Next", ULONG, POINTER(FORMATETC), POINTER(ULONG)),
    STDMETHOD(HRESULT, "Skip", ULONG),
    STDMETHOD(HRESULT, "Reset"),
    STDMETHOD(HRESULT, "Clone", POINTER(IEnumFORMATETC))]

class IDataObject(IUnknown):
    _iid_ = GUID("{0000010E-0000-0000-C000-000000000046}")

IDataObject._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "GetData", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "GetDataHere", POINTER(FORMATETC), POINTER(STGMEDIUM)),
    STDMETHOD(HRESULT, "QueryGetData", POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "GetCanonicalFormatEtc", POINTER(FORMATETC), POINTER(FORMATETC)),
    STDMETHOD(HRESULT, "SetData", POINTER(FORMATETC), POINTER(STGMEDIUM), BOOL),
    STDMETHOD(HRESULT, "EnumFormatEtc", DWORD, POINTER(POINTER(IEnumFORMATETC))),
    STDMETHOD(HRESULT, "DAdvise", POINTER(FORMATETC), DWORD, POINTER(IAdviseSink), POINTER(DWORD)),
    STDMETHOD(HRESULT, "DUnadvise", DWORD),
    STDMETHOD(HRESULT, "EnumDAdvise", POINTER(POINTER(IEnumSTATDATA)))]


#***********************************************************************************
DROPEFFECT_NONE   = 0 
DROPEFFECT_COPY   = 1 
DROPEFFECT_MOVE   = 2 
DROPEFFECT_LINK   = 4 
DROPEFFECT_SCROLL = -2147483648

class IDropSource(IUnknown):
    _iid_ = GUID("{00000121-0000-0000-C000-000000000046}")

IDropSource._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "QueryContinueDrag", BOOL, DWORD),
    STDMETHOD(HRESULT, "GiveFeedback", DWORD)]


class IDropTarget(IUnknown):
    _iid_ = GUID("{00000122-0000-0000-C000-000000000046}")

IDropTarget._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "DragEnter", POINTER(IDataObject), DWORD, POINTL, POINTER(DWORD)),
    STDMETHOD(HRESULT, "DragOver", DWORD, POINTL, POINTER(DWORD)),
    STDMETHOD(HRESULT, "DragLeave"),
    STDMETHOD(HRESULT, "Drop", POINTER(IDataObject), DWORD, POINTL, POINTER(DWORD))]		## Note: POINTER(DWORD)
														# not DWORD as in venster

#***********************************************************************************
# IOleCommandTarget consts
CONTEXT_MENU_DEFAULT= 0  
CONTEXT_MENU_IMAGE =1  
CONTEXT_MENU_CONTROL = 2  
CONTEXT_MENU_TABLE = 3  
CONTEXT_MENU_DEBUG = 4  
CONTEXT_MENU_1DSELECT = 5  
CONTEXT_MENU_ANCHOR = 6  
CONTEXT_MENU_IMGDYNSRC = 7  

OLECMDTEXTF_NONE   =  0, 
OLECMDTEXTF_NAME   =  1, 
OLECMDTEXTF_STATUS =  2 

OLECMDF_SUPPORTED   =  1, 
OLECMDF_ENABLED     =  2, 
OLECMDF_LATCHED     =  4, 
OLECMDF_NINCHED     =  8

OLECMDID_OPEN               =  1, 
OLECMDID_NEW                =  2, 
OLECMDID_SAVE               =  3, 
OLECMDID_SAVEAS             =  4, 
OLECMDID_SAVECOPYAS         =  5, 
OLECMDID_PRINT              =  6, 
OLECMDID_PRINTPREVIEW       =  7, 
OLECMDID_PAGESETUP          =  8, 
OLECMDID_SPELL              =  9, 
OLECMDID_PROPERTIES         = 10, 
OLECMDID_CUT                = 11, 
OLECMDID_COPY               = 12, 
OLECMDID_PASTE              = 13, 
OLECMDID_PASTESPECIAL       = 14, 
OLECMDID_UNDO               = 15, 
OLECMDID_REDO               = 16, 
OLECMDID_SELECTALL          = 17, 
OLECMDID_CLEARSELECTION     = 18, 
OLECMDID_ZOOM               = 19, 
OLECMDID_GETZOOMRANGE       = 20  
OLECMDID_UPDATECOMMANDS     = 21  
OLECMDID_REFRESH            = 22  
OLECMDID_STOP               = 23  
OLECMDID_HIDETOOLBARS       = 24  
OLECMDID_SETPROGRESSMAX     = 25  
OLECMDID_SETPROGRESSPOS     = 26  
OLECMDID_SETPROGRESSTEXT    = 27  
OLECMDID_SETTITLE           = 28  
OLECMDID_SETDOWNLOADSTATE   = 29  
OLECMDID_STOPDOWNLOAD       = 30  
OLECMDID_ONTOOLBARACTIVATED = 31,
OLECMDID_FIND               = 32,
OLECMDID_DELETE             = 33,
OLECMDID_HTTPEQUIV          = 34,
OLECMDID_HTTPEQUIV_DONE     = 35,
OLECMDID_ENABLE_INTERACTION = 36,
OLECMDID_ONUNLOAD           = 37


class OLECMD(Structure):
	_fields_ = [("cmdID", ULONG),
					("cmdf", DWORD)]

class OLECMDTEXT(Structure):
	_fields_ = [("cmdtextf", DWORD),
					("cwActual", ULONG),
					("cwBuf", ULONG),
					("rgwz", c_wchar*1)]

class IOleCommandTarget(IUnknown):
    _iid_ = GUID("{b722bccb-4e68-101b-a2bc-00aa00404770}")
    _methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "QueryStatus", POINTER(GUID), c_ulong,
	POINTER(OLECMD), # variable length array 
	POINTER(OLECMDTEXT)),
	STDMETHOD(HRESULT, "Exec", POINTER(GUID), DWORD, DWORD, POINTER(VARIANT), POINTER(VARIANT))]


#******************************************************************************
DOCHOSTUIDBLCLK_DEFAULT         = 0,
DOCHOSTUIDBLCLK_SHOWPROPERTIES  = 1,
DOCHOSTUIDBLCLK_SHOWCODE        = 2,

DOCHOSTUIFLAG_DIALOG            = 1
DOCHOSTUIFLAG_DISABLE_HELP_MENU = 2
DOCHOSTUIFLAG_NO3DBORDER        = 4
DOCHOSTUIFLAG_SCROLL_NO         = 8
DOCHOSTUIFLAG_DISABLE_SCRIPT_INACTIVE = 16
DOCHOSTUIFLAG_OPENNEWWIN        = 32
DOCHOSTUIFLAG_DISABLE_OFFSCREEN = 64
DOCHOSTUIFLAG_FLAT_SCROLLBAR = 128
DOCHOSTUIFLAG_DIV_BLOCKDEFAULT = 256
DOCHOSTUIFLAG_ACTIVATE_CLIENTHIT_ONLY = 512
DOCHOSTUIFLAG_DISABLE_COOKIE = 1024


class DOCHOSTUIINFO(Structure):
	_fields_ = [("cbSize", c_ulong),
					("dwFlags", DWORD),
					("dwDoubleClick", DWORD)]

class IDocHostUIHandler(IUnknown):
	_iid_ = GUID("{bd3f23c0-d43e-11cf-893b-00aa00bdce1a}")
	_methods_ = IUnknown._methods_ + [
	STDMETHOD(HRESULT, "ShowContextMenu", DWORD, POINTER(POINT), POINTER(IUnknown), POINTER(IDispatch)),
	STDMETHOD(HRESULT, "GetHostInfo", POINTER(DOCHOSTUIINFO)),
	STDMETHOD(HRESULT, "ShowUI", DWORD, POINTER(IOleInPlaceActiveObject),
	POINTER(IOleCommandTarget), POINTER(IOleInPlaceFrame), POINTER(IOleInPlaceUIWindow)),
	STDMETHOD(HRESULT, "HideUI"),
	STDMETHOD(HRESULT, "UpdateUI"),
	STDMETHOD(HRESULT, "EnableModeless", BOOL),
	STDMETHOD(HRESULT, "OnDocWindowActivate", BOOL),
	STDMETHOD(HRESULT, "OnFrameWindowActivate", BOOL),
	STDMETHOD(HRESULT, "ResizeBorder", POINTER(RECT), POINTER(IOleInPlaceUIWindow), BOOL),
	STDMETHOD(HRESULT, "TranslateAccelerator", POINTER(MSG), POINTER(GUID), DWORD),
	STDMETHOD(HRESULT, "GetOptionKeyPath", LPOLESTR, DWORD),
	STDMETHOD(HRESULT, "GetDropTarget", POINTER(IDropTarget), POINTER(POINTER(IDropTarget))),
	STDMETHOD(HRESULT, "GetExternal", POINTER(POINTER(IDispatch))),
	STDMETHOD(HRESULT, "TranslateUrl", DWORD, LPOLESTR, POINTER(LPOLESTR)),
	STDMETHOD(HRESULT, "FilterDataObject", POINTER(IDataObject), POINTER(POINTER(IDataObject)))]
	

