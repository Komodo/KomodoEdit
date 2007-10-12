

from wnd.wintypes import (user32,
													c_uint,
													HIWORD,
													LOWORD,
													DWORD,
													HANDLE,
													Structure,
													byref,
													sizeof,
													addressof,
													WNDPROC,
													create_string_buffer)
from wnd import fwtypes as fw
from wnd.fwtypes import TrackHandler

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::



class MENUITEMINFO(Structure):
	_fields_=[("cbSize", c_uint),  
					("fMask", c_uint), 
					("fType", c_uint), 
					("fState", c_uint), 
					("wID", c_uint), 
					("hSubMenu", HANDLE),
					("hbmpChecked", HANDLE),
					("hbmpUnChecked", HANDLE), 
					("dwItemData", DWORD), 
					("dwTypeData", DWORD),	# depends on fType 
					("cch", c_uint)] 
	def __init__(self):
		self.cbSize = sizeof(self)


#*************************************************
class Styles: pass

class Msgs:
	WM_ENTERMENULOOP = 529
	WM_INITMENU = 278
	WM_INITMENUPOPUP = 279
	WM_MENUSELECT = 287
	WM_UNINITMENUPOPUP = 293
	WM_NCPAINT = 133
	WM_GETTEXT = 13
	WM_ERASEBKGND = 20
	WM_UNINITMENUPOPUP = 293
	WM_EXITMENULOOP = 530


MIIM_STATE      = 1
MIIM_ID         = 2
MIIM_SUBMENU    = 4
MIIM_CHECKMARKS = 8
MIIM_TYPE       = 16
MIIM_DATA       = 32
MIIM_STRING     = 64
MIIM_BITMAP     = 128
MIIM_FTYPE      = 256

	
MIIM_STATE      = 1
MIIM_ID         = 2
MIIM_SUBMENU    = 4
MIIM_CHECKMARKS = 8
MIIM_TYPE       = 16
MIIM_DATA       = 32
MIIM_STRING     = 64
MIIM_BITMAP     = 128
MIIM_FTYPE      = 256

MFT_STRING         = 0
MFT_BITMAP         = 4
MFT_MENUBARBREAK   = 32
MFT_MENUBREAK      = 64
MFT_OWNERDRAW      = 256
MFT_RADIOCHECK     = 512
MFT_SEPARATOR      = 2048
MFT_RIGHTORDER     = 8192
MFT_RIGHTJUSTIFY   = 16384

MFS_GRAYED    = 3
MFS_DISABLED  = MFS_GRAYED
MFS_CHECKED   = 8
MFS_HILITE    = 128
MFS_ENABLED   = 0
MFS_UNCHECKED = 0
MFS_UNHILITE  = 0
MFS_DEFAULT   = 4096

#MF_DISABLED        = 2
	
# Flags for TrackPopupMenu
TPM_LEFTBUTTON   = 0
TPM_RIGHTBUTTON  = 2
TPM_LEFTALIGN    = 0
TPM_CENTERALIGN  = 4
TPM_RIGHTALIGN   = 8

TPM_TOPALIGN     = 0
TPM_VCENTERALIGN = 16
TPM_BOTTOMALIGN  = 32

TPM_HORIZONTAL   = 0  # Horz alignment matters more
TPM_VERTICAL     = 64  # Vert alignment matters more
TPM_NONOTIFY     = 128  # Don#t send any notification msgs
TPM_RETURNCMD    = 256

MF_UNCHECKED       = 0
MF_CHECKED         = 8

MF_BYCOMMAND      = 0
MF_BYPOSITION      = 1024


