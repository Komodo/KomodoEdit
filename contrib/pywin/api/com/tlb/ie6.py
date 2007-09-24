# -*- python -*-
# Generated from C:\windows\system32\SHDOCVW.DLL

###############################################################
# NOTE: This is a GENERATED file. Please do not make changes, #
# they will be overwritten next time it is regenerated.       #
###############################################################

from ctypes import *
from ctypes.com import IUnknown, GUID, STDMETHOD, HRESULT
from ctypes.com.automation import IDispatch, BSTR, VARIANT, dispinterface, \
                                  DISPMETHOD, DISPPARAMS, EXCEPINFO


##############################################################################

# The Type Library
class SHDocVw:
    'Microsoft Internet Controls'
    guid = GUID('{EAB22AC0-30C1-11CF-A7EB-0000C05BAE0B}')
    version = (1, 1)
    flags = 0x8
    path = 'C:\\windows\\system32\\SHDOCVW.DLL'

##############################################################################

class CommandStateChangeConstants(c_int):
    """Constants for WebBrowser CommandStateChange"""
    _iid_ = GUID('{34A226E0-DF30-11CF-89A9-00A0C9054129}')
    CSC_UPDATECOMMANDS = -1
    CSC_NAVIGATEFORWARD = 1
    CSC_NAVIGATEBACK = 2


class OLECMDID(c_int):
    OLECMDID_OPEN = 1
    OLECMDID_NEW = 2
    OLECMDID_SAVE = 3
    OLECMDID_SAVEAS = 4
    OLECMDID_SAVECOPYAS = 5
    OLECMDID_PRINT = 6
    OLECMDID_PRINTPREVIEW = 7
    OLECMDID_PAGESETUP = 8
    OLECMDID_SPELL = 9
    OLECMDID_PROPERTIES = 10
    OLECMDID_CUT = 11
    OLECMDID_COPY = 12
    OLECMDID_PASTE = 13
    OLECMDID_PASTESPECIAL = 14
    OLECMDID_UNDO = 15
    OLECMDID_REDO = 16
    OLECMDID_SELECTALL = 17
    OLECMDID_CLEARSELECTION = 18
    OLECMDID_ZOOM = 19
    OLECMDID_GETZOOMRANGE = 20
    OLECMDID_UPDATECOMMANDS = 21
    OLECMDID_REFRESH = 22
    OLECMDID_STOP = 23
    OLECMDID_HIDETOOLBARS = 24
    OLECMDID_SETPROGRESSMAX = 25
    OLECMDID_SETPROGRESSPOS = 26
    OLECMDID_SETPROGRESSTEXT = 27
    OLECMDID_SETTITLE = 28
    OLECMDID_SETDOWNLOADSTATE = 29
    OLECMDID_STOPDOWNLOAD = 30
    OLECMDID_ONTOOLBARACTIVATED = 31
    OLECMDID_FIND = 32
    OLECMDID_DELETE = 33
    OLECMDID_HTTPEQUIV = 34
    OLECMDID_HTTPEQUIV_DONE = 35
    OLECMDID_ENABLE_INTERACTION = 36
    OLECMDID_ONUNLOAD = 37
    OLECMDID_PROPERTYBAG2 = 38
    OLECMDID_PREREFRESH = 39
    OLECMDID_SHOWSCRIPTERROR = 40
    OLECMDID_SHOWMESSAGE = 41
    OLECMDID_SHOWFIND = 42
    OLECMDID_SHOWPAGESETUP = 43
    OLECMDID_SHOWPRINT = 44
    OLECMDID_CLOSE = 45
    OLECMDID_ALLOWUILESSSAVEAS = 46
    OLECMDID_DONTDOWNLOADCSS = 47
    OLECMDID_UPDATEPAGESTATUS = 48
    OLECMDID_PRINT2 = 49
    OLECMDID_PRINTPREVIEW2 = 50
    OLECMDID_SETPRINTTEMPLATE = 51
    OLECMDID_GETPRINTTEMPLATE = 52


class OLECMDF(c_int):
    OLECMDF_SUPPORTED = 1
    OLECMDF_ENABLED = 2
    OLECMDF_LATCHED = 4
    OLECMDF_NINCHED = 8
    OLECMDF_INVISIBLE = 16
    OLECMDF_DEFHIDEONCTXTMENU = 32


class OLECMDEXECOPT(c_int):
    OLECMDEXECOPT_DODEFAULT = 0
    OLECMDEXECOPT_PROMPTUSER = 1
    OLECMDEXECOPT_DONTPROMPTUSER = 2
    OLECMDEXECOPT_SHOWHELP = 3


class tagREADYSTATE(c_int):
    READYSTATE_UNINITIALIZED = 0
    READYSTATE_LOADING = 1
    READYSTATE_LOADED = 2
    READYSTATE_INTERACTIVE = 3
    READYSTATE_COMPLETE = 4


class SecureLockIconConstants(c_int):
    """Constants for WebBrowser security icon notification"""
    _iid_ = GUID('{65507BE0-91A8-11D3-A845-009027220E6D}')
    secureLockIconUnsecure = 0
    secureLockIconMixed = 1
    secureLockIconSecureUnknownBits = 2
    secureLockIconSecure40Bit = 3
    secureLockIconSecure56Bit = 4
    secureLockIconSecureFortezza = 5
    secureLockIconSecure128Bit = 6


class ShellWindowTypeConstants(c_int):
    """Constants for ShellWindows registration"""
    _iid_ = GUID('{F41E6981-28E5-11D0-82B4-00A0C90C29C5}')
    SWC_EXPLORER = 0
    SWC_BROWSER = 1
    SWC_3RDPARTY = 2
    SWC_CALLBACK = 4


class ShellWindowFindWindowOptions(c_int):
    """Options for ShellWindows FindWindow"""
    _iid_ = GUID('{7716A370-38CA-11D0-A48B-00A0C90A8F39}')
    SWFO_NEEDDISPATCH = 1
    SWFO_INCLUDEPENDING = 2
    SWFO_COOKIEPASSED = 4


##############################################################################

class IWebBrowser2(IDispatch):
    """Web Browser Interface for IE4."""
    _iid_ = GUID('{D30C1661-CDAF-11D0-8A3E-00C04FC9E26E}')


class IShellNameSpace(IDispatch):
    """IShellNameSpace Interface"""
    _iid_ = GUID('{E572D3C9-37BE-4AE2-825D-D521763E3108}')


class IShellWindows(IDispatch):
    """Definition of interface IShellWindows"""
    _iid_ = GUID('{85CB6900-4D95-11CF-960C-0080C7F4EE85}')


class IWebBrowser(IDispatch):
    """Web Browser interface"""
    _iid_ = GUID('{EAB22AC1-30C1-11CF-A7EB-0000C05BAE0B}')


class ISearchAssistantOC(IDispatch):
    """ISearchAssistantOC Interface"""
    _iid_ = GUID('{72423E8F-8011-11D2-BE79-00A0C9A83DA1}')


class ISearches(IDispatch):
    """Searches Enum"""
    _iid_ = GUID('{47C922A2-3DD5-11D2-BF8B-00C04FB93661}')


class DShellWindowsEvents(dispinterface):
    """Event interface for IShellWindows"""
    _iid_ = GUID('{FE4106E0-399A-11D0-A48C-00A0C90A8F39}')


class ISearchAssistantOC3(IDispatch):
    """ISearchAssistantOC3 Interface"""
    _iid_ = GUID('{72423E8F-8011-11D2-BE79-00A0C9A83DA3}')


class IWebBrowserApp(IDispatch):
    """Web Browser Application Interface."""
    _iid_ = GUID('{0002DF05-0000-0000-C000-000000000046}')


class DWebBrowserEvents2(dispinterface):
    """Web Browser Control events interface"""
    _iid_ = GUID('{34A715A0-6587-11D0-924A-0020AFC7AC4D}')


class IScriptErrorList(IDispatch):
    """Script Error List Interface"""
    _iid_ = GUID('{F3470F24-15FD-11D2-BB2E-00805FF7EFCA}')


class ISearchAssistantOC2(IDispatch):
    """ISearchAssistantOC2 Interface"""
    _iid_ = GUID('{72423E8F-8011-11D2-BE79-00A0C9A83DA2}')


class ISearch(IDispatch):
    """Enumerated Search"""
    _iid_ = GUID('{BA9239A4-3DD5-11D2-BF8B-00C04FB93661}')


class IShellUIHelper(IDispatch):
    """Shell UI Helper Control Interface"""
    _iid_ = GUID('{729FE2F8-1EA8-11D1-8F85-00C04FC2FBE1}')


class DShellNameSpaceEvents(dispinterface):
    _iid_ = GUID('{55136806-B2DE-11D1-B9F2-00A0C98BC547}')


class DWebBrowserEvents(dispinterface):
    """Web Browser Control Events (old)"""
    _iid_ = GUID('{EAB22AC2-30C1-11CF-A7EB-0000C05BAE0B}')


class _SearchAssistantEvents(dispinterface):
    _iid_ = GUID('{1611FDDA-445B-11D2-85DE-00C04FA35C89}')


class IShellFavoritesNameSpace(IDispatch):
    """IShellFavoritesNameSpace Interface"""
    _iid_ = GUID('{55136804-B2DE-11D1-B9F2-00A0C98BC547}')


IWebBrowser2._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "GoBack"),
    STDMETHOD(HRESULT, "GoForward"),
    STDMETHOD(HRESULT, "GoHome"),
    STDMETHOD(HRESULT, "GoSearch"),
    STDMETHOD(HRESULT, "Navigate", BSTR, POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Refresh"),
    STDMETHOD(HRESULT, "Refresh2", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Stop"),
    STDMETHOD(HRESULT, "_get_Application", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Parent", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Container", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Document", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_TopLevelContainer", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Type", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Left", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Left", c_long),
    STDMETHOD(HRESULT, "_get_Top", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Top", c_long),
    STDMETHOD(HRESULT, "_get_Width", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Width", c_long),
    STDMETHOD(HRESULT, "_get_Height", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Height", c_long),
    STDMETHOD(HRESULT, "_get_LocationName", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_LocationURL", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Busy", POINTER(c_int)),
    STDMETHOD(HRESULT, "Quit"),
    STDMETHOD(HRESULT, "ClientToWindow", POINTER(c_int), POINTER(c_int)),
    STDMETHOD(HRESULT, "PutProperty", BSTR, VARIANT),
    STDMETHOD(HRESULT, "GetProperty", BSTR, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "_get_Name", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_HWND", POINTER(c_long)),
    STDMETHOD(HRESULT, "_get_FullName", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Path", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Visible", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Visible", c_int),
    STDMETHOD(HRESULT, "_get_StatusBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_StatusBar", c_int),
    STDMETHOD(HRESULT, "_get_StatusText", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_StatusText", BSTR),
    STDMETHOD(HRESULT, "_get_ToolBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_ToolBar", c_int),
    STDMETHOD(HRESULT, "_get_MenuBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_MenuBar", c_int),
    STDMETHOD(HRESULT, "_get_FullScreen", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_FullScreen", c_int),
    STDMETHOD(HRESULT, "Navigate2", POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "QueryStatusWB", OLECMDID, POINTER(OLECMDF)),
    STDMETHOD(HRESULT, "ExecWB", OLECMDID, OLECMDEXECOPT, POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "ShowBrowserBar", POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "_get_ReadyState", POINTER(tagREADYSTATE)),
    STDMETHOD(HRESULT, "_get_Offline", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Offline", c_int),
    STDMETHOD(HRESULT, "_get_Silent", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Silent", c_int),
    STDMETHOD(HRESULT, "_get_RegisterAsBrowser", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_RegisterAsBrowser", c_int),
    STDMETHOD(HRESULT, "_get_RegisterAsDropTarget", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_RegisterAsDropTarget", c_int),
    STDMETHOD(HRESULT, "_get_TheaterMode", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_TheaterMode", c_int),
    STDMETHOD(HRESULT, "_get_AddressBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_AddressBar", c_int),
    STDMETHOD(HRESULT, "_get_Resizable", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Resizable", c_int),
]

IShellNameSpace._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "MoveSelectionUp"),
    STDMETHOD(HRESULT, "MoveSelectionDown"),
    STDMETHOD(HRESULT, "ResetSort"),
    STDMETHOD(HRESULT, "NewFolder"),
    STDMETHOD(HRESULT, "Synchronize"),
    STDMETHOD(HRESULT, "Import"),
    STDMETHOD(HRESULT, "Export"),
    STDMETHOD(HRESULT, "InvokeContextMenuCommand", BSTR),
    STDMETHOD(HRESULT, "MoveSelectionTo"),
    STDMETHOD(HRESULT, "_get_SubscriptionsEnabled", POINTER(c_int)),
    STDMETHOD(HRESULT, "CreateSubscriptionForSelection", POINTER(c_int)),
    STDMETHOD(HRESULT, "DeleteSubscriptionForSelection", POINTER(c_int)),
    STDMETHOD(HRESULT, "SetRoot", BSTR),
    STDMETHOD(HRESULT, "_get_EnumOptions", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_EnumOptions", c_long),
    STDMETHOD(HRESULT, "_get_SelectedItem", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_put_SelectedItem", POINTER(IDispatch)),
    STDMETHOD(HRESULT, "_get_Root", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "_put_Root", VARIANT),
    STDMETHOD(HRESULT, "_get_Depth", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Depth", c_int),
    STDMETHOD(HRESULT, "_get_Mode", POINTER(c_uint)),
    STDMETHOD(HRESULT, "_put_Mode", c_uint),
    STDMETHOD(HRESULT, "_get_Flags", POINTER(c_ulong)),
    STDMETHOD(HRESULT, "_put_Flags", c_ulong),
    STDMETHOD(HRESULT, "_put_TVFlags", c_ulong),
    STDMETHOD(HRESULT, "_get_TVFlags", POINTER(c_ulong)),
    STDMETHOD(HRESULT, "_get_Columns", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_Columns", BSTR),
    STDMETHOD(HRESULT, "_get_CountViewTypes", POINTER(c_int)),
    STDMETHOD(HRESULT, "SetViewType", c_int),
    STDMETHOD(HRESULT, "SelectedItems", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "Expand", VARIANT, c_int),
    STDMETHOD(HRESULT, "UnselectAll"),
]

IShellWindows._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "_get_Count", POINTER(c_long)),
    STDMETHOD(HRESULT, "Item", VARIANT, POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_NewEnum", POINTER(POINTER(IUnknown))),
    STDMETHOD(HRESULT, "Register", POINTER(IDispatch), c_long, c_int, POINTER(c_long)),
    STDMETHOD(HRESULT, "RegisterPending", c_long, POINTER(VARIANT), POINTER(VARIANT), c_int, POINTER(c_long)),
    STDMETHOD(HRESULT, "Revoke", c_long),
    STDMETHOD(HRESULT, "OnNavigate", c_long, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "OnActivated", c_long, c_int),
    STDMETHOD(HRESULT, "FindWindowSW", POINTER(VARIANT), POINTER(VARIANT), c_int, POINTER(c_long), c_int, POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "OnCreated", c_long, POINTER(IUnknown)),
    STDMETHOD(HRESULT, "ProcessAttachDetach", c_int),
]

IWebBrowser._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "GoBack"),
    STDMETHOD(HRESULT, "GoForward"),
    STDMETHOD(HRESULT, "GoHome"),
    STDMETHOD(HRESULT, "GoSearch"),
    STDMETHOD(HRESULT, "Navigate", BSTR, POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Refresh"),
    STDMETHOD(HRESULT, "Refresh2", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Stop"),
    STDMETHOD(HRESULT, "_get_Application", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Parent", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Container", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Document", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_TopLevelContainer", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Type", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Left", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Left", c_long),
    STDMETHOD(HRESULT, "_get_Top", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Top", c_long),
    STDMETHOD(HRESULT, "_get_Width", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Width", c_long),
    STDMETHOD(HRESULT, "_get_Height", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Height", c_long),
    STDMETHOD(HRESULT, "_get_LocationName", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_LocationURL", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Busy", POINTER(c_int)),
]

ISearchAssistantOC._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "AddNextMenuItem", BSTR, c_long),
    STDMETHOD(HRESULT, "SetDefaultSearchUrl", BSTR),
    STDMETHOD(HRESULT, "NavigateToDefaultSearch"),
    STDMETHOD(HRESULT, "IsRestricted", BSTR, POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_ShellFeaturesEnabled", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_SearchAssistantDefault", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Searches", POINTER(POINTER(ISearches))),
    STDMETHOD(HRESULT, "_get_InWebFolder", POINTER(c_int)),
    STDMETHOD(HRESULT, "PutProperty", c_int, BSTR, BSTR),
    STDMETHOD(HRESULT, "GetProperty", c_int, BSTR, POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_EventHandled", c_int),
    STDMETHOD(HRESULT, "ResetNextMenu"),
    STDMETHOD(HRESULT, "FindOnWeb"),
    STDMETHOD(HRESULT, "FindFilesOrFolders"),
    STDMETHOD(HRESULT, "FindComputer"),
    STDMETHOD(HRESULT, "FindPrinter"),
    STDMETHOD(HRESULT, "FindPeople"),
    STDMETHOD(HRESULT, "GetSearchAssistantURL", c_int, c_int, POINTER(BSTR)),
    STDMETHOD(HRESULT, "NotifySearchSettingsChanged"),
    STDMETHOD(HRESULT, "_put_ASProvider", BSTR),
    STDMETHOD(HRESULT, "_get_ASProvider", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_ASSetting", c_int),
    STDMETHOD(HRESULT, "_get_ASSetting", POINTER(c_int)),
    STDMETHOD(HRESULT, "NETDetectNextNavigate"),
    STDMETHOD(HRESULT, "PutFindText", BSTR),
    STDMETHOD(HRESULT, "_get_Version", POINTER(c_int)),
    STDMETHOD(HRESULT, "EncodeString", BSTR, BSTR, c_int, POINTER(BSTR)),
]

ISearches._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "_get_Count", POINTER(c_long)),
    STDMETHOD(HRESULT, "_get_Default", POINTER(BSTR)),
    STDMETHOD(HRESULT, "Item", VARIANT, POINTER(POINTER(ISearch))),
    STDMETHOD(HRESULT, "_NewEnum", POINTER(POINTER(IUnknown))),
]

DShellWindowsEvents._dispmethods_ = [
    DISPMETHOD(0xc8L, None, "WindowRegistered", c_long),
    DISPMETHOD(0xc9L, None, "WindowRevoked", c_long),
]

ISearchAssistantOC3._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "AddNextMenuItem", BSTR, c_long),
    STDMETHOD(HRESULT, "SetDefaultSearchUrl", BSTR),
    STDMETHOD(HRESULT, "NavigateToDefaultSearch"),
    STDMETHOD(HRESULT, "IsRestricted", BSTR, POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_ShellFeaturesEnabled", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_SearchAssistantDefault", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Searches", POINTER(POINTER(ISearches))),
    STDMETHOD(HRESULT, "_get_InWebFolder", POINTER(c_int)),
    STDMETHOD(HRESULT, "PutProperty", c_int, BSTR, BSTR),
    STDMETHOD(HRESULT, "GetProperty", c_int, BSTR, POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_EventHandled", c_int),
    STDMETHOD(HRESULT, "ResetNextMenu"),
    STDMETHOD(HRESULT, "FindOnWeb"),
    STDMETHOD(HRESULT, "FindFilesOrFolders"),
    STDMETHOD(HRESULT, "FindComputer"),
    STDMETHOD(HRESULT, "FindPrinter"),
    STDMETHOD(HRESULT, "FindPeople"),
    STDMETHOD(HRESULT, "GetSearchAssistantURL", c_int, c_int, POINTER(BSTR)),
    STDMETHOD(HRESULT, "NotifySearchSettingsChanged"),
    STDMETHOD(HRESULT, "_put_ASProvider", BSTR),
    STDMETHOD(HRESULT, "_get_ASProvider", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_ASSetting", c_int),
    STDMETHOD(HRESULT, "_get_ASSetting", POINTER(c_int)),
    STDMETHOD(HRESULT, "NETDetectNextNavigate"),
    STDMETHOD(HRESULT, "PutFindText", BSTR),
    STDMETHOD(HRESULT, "_get_Version", POINTER(c_int)),
    STDMETHOD(HRESULT, "EncodeString", BSTR, BSTR, c_int, POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_ShowFindPrinter", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_SearchCompanionAvailable", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_UseSearchCompanion", c_int),
    STDMETHOD(HRESULT, "_get_UseSearchCompanion", POINTER(c_int)),
]

IWebBrowserApp._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "GoBack"),
    STDMETHOD(HRESULT, "GoForward"),
    STDMETHOD(HRESULT, "GoHome"),
    STDMETHOD(HRESULT, "GoSearch"),
    STDMETHOD(HRESULT, "Navigate", BSTR, POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Refresh"),
    STDMETHOD(HRESULT, "Refresh2", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "Stop"),
    STDMETHOD(HRESULT, "_get_Application", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Parent", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Container", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_Document", POINTER(POINTER(IDispatch))),
    STDMETHOD(HRESULT, "_get_TopLevelContainer", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Type", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Left", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Left", c_long),
    STDMETHOD(HRESULT, "_get_Top", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Top", c_long),
    STDMETHOD(HRESULT, "_get_Width", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Width", c_long),
    STDMETHOD(HRESULT, "_get_Height", POINTER(c_long)),
    STDMETHOD(HRESULT, "_put_Height", c_long),
    STDMETHOD(HRESULT, "_get_LocationName", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_LocationURL", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Busy", POINTER(c_int)),
    STDMETHOD(HRESULT, "Quit"),
    STDMETHOD(HRESULT, "ClientToWindow", POINTER(c_int), POINTER(c_int)),
    STDMETHOD(HRESULT, "PutProperty", BSTR, VARIANT),
    STDMETHOD(HRESULT, "GetProperty", BSTR, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "_get_Name", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_HWND", POINTER(c_long)),
    STDMETHOD(HRESULT, "_get_FullName", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Path", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Visible", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_Visible", c_int),
    STDMETHOD(HRESULT, "_get_StatusBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_StatusBar", c_int),
    STDMETHOD(HRESULT, "_get_StatusText", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_StatusText", BSTR),
    STDMETHOD(HRESULT, "_get_ToolBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_ToolBar", c_int),
    STDMETHOD(HRESULT, "_get_MenuBar", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_MenuBar", c_int),
    STDMETHOD(HRESULT, "_get_FullScreen", POINTER(c_int)),
    STDMETHOD(HRESULT, "_put_FullScreen", c_int),
]

DWebBrowserEvents2._dispmethods_ = [
    DISPMETHOD(0x66L, None, "StatusTextChange", BSTR),
    DISPMETHOD(0x6cL, None, "ProgressChange", c_long, c_long),
    DISPMETHOD(0x69L, None, "CommandStateChange", c_long, c_int),
    DISPMETHOD(0x6aL, None, "DownloadBegin"),
    DISPMETHOD(0x68L, None, "DownloadComplete"),
    DISPMETHOD(0x71L, None, "TitleChange", BSTR),
    DISPMETHOD(0x70L, None, "PropertyChange", BSTR),
    DISPMETHOD(0xfaL, None, "BeforeNavigate2", POINTER(IDispatch), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(c_int)),
    DISPMETHOD(0xfbL, None, "NewWindow2", POINTER(POINTER(IDispatch)), POINTER(c_int)),
    DISPMETHOD(0xfcL, None, "NavigateComplete2", POINTER(IDispatch), POINTER(VARIANT)),
    DISPMETHOD(0x103L, None, "DocumentComplete", POINTER(IDispatch), POINTER(VARIANT)),
    DISPMETHOD(0xfdL, None, "OnQuit"),
    DISPMETHOD(0xfeL, None, "OnVisible", c_int),
    DISPMETHOD(0xffL, None, "OnToolBar", c_int),
    DISPMETHOD(0x100L, None, "OnMenuBar", c_int),
    DISPMETHOD(0x101L, None, "OnStatusBar", c_int),
    DISPMETHOD(0x102L, None, "OnFullScreen", c_int),
    DISPMETHOD(0x104L, None, "OnTheaterMode", c_int),
    DISPMETHOD(0x106L, None, "WindowSetResizable", c_int),
    DISPMETHOD(0x108L, None, "WindowSetLeft", c_long),
    DISPMETHOD(0x109L, None, "WindowSetTop", c_long),
    DISPMETHOD(0x10aL, None, "WindowSetWidth", c_long),
    DISPMETHOD(0x10bL, None, "WindowSetHeight", c_long),
    DISPMETHOD(0x107L, None, "WindowClosing", c_int, POINTER(c_int)),
    DISPMETHOD(0x10cL, None, "ClientToHostWindow", POINTER(c_long), POINTER(c_long)),
    DISPMETHOD(0x10dL, None, "SetSecureLockIcon", c_long),
    DISPMETHOD(0x10eL, None, "FileDownload", POINTER(c_int)),
    DISPMETHOD(0x10fL, None, "NavigateError", POINTER(IDispatch), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(c_int)),
    DISPMETHOD(0xe1L, None, "PrintTemplateInstantiation", POINTER(IDispatch)),
    DISPMETHOD(0xe2L, None, "PrintTemplateTeardown", POINTER(IDispatch)),
    DISPMETHOD(0xe3L, None, "UpdatePageStatus", POINTER(IDispatch), POINTER(VARIANT), POINTER(VARIANT)),
    DISPMETHOD(0x110L, None, "PrivacyImpactedStateChange", c_int),
]

IScriptErrorList._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "advanceError"),
    STDMETHOD(HRESULT, "retreatError"),
    STDMETHOD(HRESULT, "canAdvanceError", POINTER(c_long)),
    STDMETHOD(HRESULT, "canRetreatError", POINTER(c_long)),
    STDMETHOD(HRESULT, "getErrorLine", POINTER(c_long)),
    STDMETHOD(HRESULT, "getErrorChar", POINTER(c_long)),
    STDMETHOD(HRESULT, "getErrorCode", POINTER(c_long)),
    STDMETHOD(HRESULT, "getErrorMsg", POINTER(BSTR)),
    STDMETHOD(HRESULT, "getErrorUrl", POINTER(BSTR)),
    STDMETHOD(HRESULT, "getAlwaysShowLockState", POINTER(c_long)),
    STDMETHOD(HRESULT, "getDetailsPaneOpen", POINTER(c_long)),
    STDMETHOD(HRESULT, "setDetailsPaneOpen", c_long),
    STDMETHOD(HRESULT, "getPerErrorDisplay", POINTER(c_long)),
    STDMETHOD(HRESULT, "setPerErrorDisplay", c_long),
]

ISearchAssistantOC2._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "AddNextMenuItem", BSTR, c_long),
    STDMETHOD(HRESULT, "SetDefaultSearchUrl", BSTR),
    STDMETHOD(HRESULT, "NavigateToDefaultSearch"),
    STDMETHOD(HRESULT, "IsRestricted", BSTR, POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_ShellFeaturesEnabled", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_SearchAssistantDefault", POINTER(c_int)),
    STDMETHOD(HRESULT, "_get_Searches", POINTER(POINTER(ISearches))),
    STDMETHOD(HRESULT, "_get_InWebFolder", POINTER(c_int)),
    STDMETHOD(HRESULT, "PutProperty", c_int, BSTR, BSTR),
    STDMETHOD(HRESULT, "GetProperty", c_int, BSTR, POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_EventHandled", c_int),
    STDMETHOD(HRESULT, "ResetNextMenu"),
    STDMETHOD(HRESULT, "FindOnWeb"),
    STDMETHOD(HRESULT, "FindFilesOrFolders"),
    STDMETHOD(HRESULT, "FindComputer"),
    STDMETHOD(HRESULT, "FindPrinter"),
    STDMETHOD(HRESULT, "FindPeople"),
    STDMETHOD(HRESULT, "GetSearchAssistantURL", c_int, c_int, POINTER(BSTR)),
    STDMETHOD(HRESULT, "NotifySearchSettingsChanged"),
    STDMETHOD(HRESULT, "_put_ASProvider", BSTR),
    STDMETHOD(HRESULT, "_get_ASProvider", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_put_ASSetting", c_int),
    STDMETHOD(HRESULT, "_get_ASSetting", POINTER(c_int)),
    STDMETHOD(HRESULT, "NETDetectNextNavigate"),
    STDMETHOD(HRESULT, "PutFindText", BSTR),
    STDMETHOD(HRESULT, "_get_Version", POINTER(c_int)),
    STDMETHOD(HRESULT, "EncodeString", BSTR, BSTR, c_int, POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_ShowFindPrinter", POINTER(c_int)),
]

ISearch._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "_get_Title", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_Id", POINTER(BSTR)),
    STDMETHOD(HRESULT, "_get_URL", POINTER(BSTR)),
]

IShellUIHelper._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "ResetFirstBootMode"),
    STDMETHOD(HRESULT, "ResetSafeMode"),
    STDMETHOD(HRESULT, "RefreshOfflineDesktop"),
    STDMETHOD(HRESULT, "AddFavorite", BSTR, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "AddChannel", BSTR),
    STDMETHOD(HRESULT, "AddDesktopComponent", BSTR, BSTR, POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT), POINTER(VARIANT)),
    STDMETHOD(HRESULT, "IsSubscribed", BSTR, POINTER(c_int)),
    STDMETHOD(HRESULT, "NavigateAndFind", BSTR, BSTR, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "ImportExportFavorites", c_int, BSTR),
    STDMETHOD(HRESULT, "AutoCompleteSaveForm", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "AutoScan", BSTR, BSTR, POINTER(VARIANT)),
    STDMETHOD(HRESULT, "AutoCompleteAttach", POINTER(VARIANT)),
    STDMETHOD(HRESULT, "ShowBrowserUI", BSTR, POINTER(VARIANT), POINTER(VARIANT)),
]

DShellNameSpaceEvents._dispmethods_ = [
    DISPMETHOD(0x1L, None, "FavoritesSelectionChange", c_long, c_long, BSTR, BSTR, c_long, BSTR, c_long),
    DISPMETHOD(0x2L, None, "SelectionChange"),
    DISPMETHOD(0x3L, None, "DoubleClick"),
    DISPMETHOD(0x4L, None, "Initialized"),
]

DWebBrowserEvents._dispmethods_ = [
    DISPMETHOD(0x64L, None, "BeforeNavigate", BSTR, c_long, BSTR, POINTER(VARIANT), BSTR, POINTER(c_int)),
    DISPMETHOD(0x65L, None, "NavigateComplete", BSTR),
    DISPMETHOD(0x66L, None, "StatusTextChange", BSTR),
    DISPMETHOD(0x6cL, None, "ProgressChange", c_long, c_long),
    DISPMETHOD(0x68L, None, "DownloadComplete"),
    DISPMETHOD(0x69L, None, "CommandStateChange", c_long, c_int),
    DISPMETHOD(0x6aL, None, "DownloadBegin"),
    DISPMETHOD(0x6bL, None, "NewWindow", BSTR, c_long, BSTR, POINTER(VARIANT), BSTR, POINTER(c_int)),
    DISPMETHOD(0x71L, None, "TitleChange", BSTR),
    DISPMETHOD(0xc8L, None, "FrameBeforeNavigate", BSTR, c_long, BSTR, POINTER(VARIANT), BSTR, POINTER(c_int)),
    DISPMETHOD(0xc9L, None, "FrameNavigateComplete", BSTR),
    DISPMETHOD(0xccL, None, "FrameNewWindow", BSTR, c_long, BSTR, POINTER(VARIANT), BSTR, POINTER(c_int)),
    DISPMETHOD(0x67L, None, "Quit", POINTER(c_int)),
    DISPMETHOD(0x6dL, None, "WindowMove"),
    DISPMETHOD(0x6eL, None, "WindowResize"),
    DISPMETHOD(0x6fL, None, "WindowActivate"),
    DISPMETHOD(0x70L, None, "PropertyChange", BSTR),
]

_SearchAssistantEvents._dispmethods_ = [
    DISPMETHOD(0x1L, None, "OnNextMenuSelect", c_long),
    DISPMETHOD(0x2L, None, "OnNewSearch"),
]

IShellFavoritesNameSpace._methods_ = IDispatch._methods_ + [
    STDMETHOD(HRESULT, "MoveSelectionUp"),
    STDMETHOD(HRESULT, "MoveSelectionDown"),
    STDMETHOD(HRESULT, "ResetSort"),
    STDMETHOD(HRESULT, "NewFolder"),
    STDMETHOD(HRESULT, "Synchronize"),
    STDMETHOD(HRESULT, "Import"),
    STDMETHOD(HRESULT, "Export"),
    STDMETHOD(HRESULT, "InvokeContextMenuCommand", BSTR),
    STDMETHOD(HRESULT, "MoveSelectionTo"),
    STDMETHOD(HRESULT, "_get_SubscriptionsEnabled", POINTER(c_int)),
    STDMETHOD(HRESULT, "CreateSubscriptionForSelection", POINTER(c_int)),
    STDMETHOD(HRESULT, "DeleteSubscriptionForSelection", POINTER(c_int)),
    STDMETHOD(HRESULT, "SetRoot", BSTR),
]

##############################################################################

class ShellNameSpace:
    _reg_clsid_ = '{55136805-B2DE-11D1-B9F2-00A0C98BC547}'
    _com_interfaces_ = [IShellNameSpace]
    _outgoing_interfaces_ = [DShellNameSpaceEvents]


class CScriptErrorList:
    _reg_clsid_ = '{EFD01300-160F-11D2-BB2E-00805FF7EFCA}'
    _com_interfaces_ = [IScriptErrorList]


class WebBrowser_V1:
    """WebBrowser Control"""
    _reg_clsid_ = '{EAB22AC3-30C1-11CF-A7EB-0000C05BAE0B}'
    _com_interfaces_ = [IWebBrowser, IWebBrowser2]
    _outgoing_interfaces_ = [DWebBrowserEvents, DWebBrowserEvents2]


class ShellBrowserWindow:
    """Shell Browser Window."""
    _reg_clsid_ = '{C08AFD90-F2A1-11D1-8455-00A0C91F3880}'
    _com_interfaces_ = [IWebBrowser2, IWebBrowserApp]
    _outgoing_interfaces_ = [DWebBrowserEvents2, DWebBrowserEvents]


class SearchAssistantOC:
    """SearchAssistantOC Class"""
    _reg_clsid_ = '{B45FF030-4447-11D2-85DE-00C04FA35C89}'
    _com_interfaces_ = [ISearchAssistantOC3]
    _outgoing_interfaces_ = [_SearchAssistantEvents]


class ShellWindows:
    """ShellDispatch Load in Shell Context"""
    _reg_clsid_ = '{9BA05972-F6A8-11CF-A442-00A0C90A8F39}'
    _com_interfaces_ = [IShellWindows]
    _outgoing_interfaces_ = [DShellWindowsEvents]


class InternetExplorer:
    """Internet Explorer Application."""
    _reg_clsid_ = '{0002DF01-0000-0000-C000-000000000046}'
    _com_interfaces_ = [IWebBrowser2, IWebBrowserApp]
    _outgoing_interfaces_ = [DWebBrowserEvents2, DWebBrowserEvents]


class WebBrowser:
    """WebBrowser Control"""
    _reg_clsid_ = '{8856F961-340A-11D0-A96B-00C04FD705A2}'
    _com_interfaces_ = [IWebBrowser2, IWebBrowser]
    _outgoing_interfaces_ = [DWebBrowserEvents2, DWebBrowserEvents]


class ShellUIHelper:
    _reg_clsid_ = '{64AB4BB7-111E-11D1-8F79-00C04FC2FBE1}'
    _com_interfaces_ = [IShellUIHelper]

