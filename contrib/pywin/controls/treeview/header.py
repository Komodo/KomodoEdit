


from wnd.wintypes import (user32,
												Structure,
												WINFUNCTYPE,
												sizeof,
												byref,
												addressof,
												c_char_p,
												UINT_MAX,
												HANDLE, 
												RECT, 
												POINT,
												DWORD,
												UINT,
												LPARAM,
												COLORREF,
												NMHDR,
												INT, 
												WORD,
												create_string_buffer,
												InitCommonControlsEx)
from wnd import fwtypes as fw
from wnd.controls.textin import TextinFromHandle
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control

#******************************************************************************************

LPSTR_TEXTCALLBACK     = -1
I_IMAGECALLBACK = -1
I_CHILDRENCALLBACK  = -1



TVSIL_NORMAL           = 0
TVSIL_STATE            = 2
	
TVNRET_DEFAULT = 0
TVNRET_SKIPOLD = 1
TVNRET_SKIPNEW = 2

TVSI_NOSINGLEEXPAND    = 32768 # Should not conflict with TVGN flags.

TVCDRF_NOIMAGES        = 65536

TVIF_DI_SETITEM        = 4096

TVC_UNKNOWN            = 0
TVC_BYMOUSE            = 1
TVC_BYKEYBOARD         = 2

TVGN_ROOT              = 0
TVGN_NEXT              = 1
TVGN_PREVIOUS          = 2
TVGN_PARENT            = 3
TVGN_CHILD             = 4
TVGN_FIRSTVISIBLE      = 5
TVGN_NEXTVISIBLE       = 6
TVGN_PREVIOUSVISIBLE   = 7
TVGN_DROPHILITE        = 8
TVGN_CARET             = 9
TVGN_LASTVISIBLE       = 10


TVHT_NOWHERE           = 1
TVHT_ONITEMICON        = 2
TVHT_ONITEMLABEL       = 4
TVHT_ONITEMINDENT      = 8
TVHT_ONITEMBUTTON      = 16
TVHT_ONITEMRIGHT       = 32
TVHT_ONITEMSTATEICON   = 64
TVHT_ABOVE             = 256
TVHT_BELOW             = 512
TVHT_TORIGHT           = 1024
TVHT_TOLEFT            = 2048
TVHT_ONITEM            = TVHT_ONITEMICON | TVHT_ONITEMLABEL | TVHT_ONITEMSTATEICON	


	
# tvitem
TVIF_TEXT           = 1
TVIF_IMAGE          = 2
TVIF_PARAM          = 4
TVIF_STATE          = 8
TVIF_HANDLE         = 16
TVIF_SELECTEDIMAGE  = 32
TVIF_CHILDREN       = 64
TVIF_INTEGRAL       = 128
	
# item states
TVIS_SELECTED       = 2
TVIS_CUT            = 4
TVIS_DROPHILITED    = 8
TVIS_BOLD           = 16
TVIS_EXPANDED       = 32
TVIS_EXPANDEDONCE   = 64
TVIS_EXPANDPARTIAL  = 128
TVIS_OVERLAYMASK    = 3840
TVIS_STATEIMAGEMASK = 61440
TVIS_USERMASK       = 61440

# 

TVI_ROOT   = 4294901760
TVI_FIRST  = 4294901761
TVI_LAST   = 4294901762
TVI_SORT   = 4294901763

def INDEXTOOVERLAYMASK(i): return i << 8
def INDEXTOSTATEIMAGEMASK(i): return i << 12

TVE_COLLAPSE           = 1
TVE_EXPAND             = 2
TVE_TOGGLE             = 3
TVE_EXPANDPARTIAL      = 16384
TVE_COLLAPSERESET      = 32768


#***********************************************
TV_FIRST               = 4352      
NM_FIRST = UINT_MAX
TVN_FIRST = (UINT_MAX) - 400

#************************************************

class Styles:
	TVS_HASBUTTONS      = 1
	TVS_HASLINES        = 2
	TVS_LINESATROOT     = 4
	TVS_EDITLABELS      = 8
	TVS_DISABLEDRAGDROP = 16
	TVS_SHOWSELALWAYS   = 32
	TVS_RTLREADING      = 64
	TVS_NOTOOLTIPS      = 128
	TVS_CHECKBOXES      = 256
	TVS_TRACKSELECT     = 512
	TVS_SINGLEEXPAND    = 1024
	TVS_INFOTIP         = 2048
	TVS_FULLROWSELECT   = 4096
	TVS_NOSCROLL        = 8192
	TVS_NONEVENHEIGHT   = 16384
	TVS_NOHSCROLL       = 32768  # TVS_NOSCROLL overrides this
	
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['TVS_', ]



class Msgs: 
	TVM_INSERTITEM         = TV_FIRST
	TVM_DELETEITEM         = TV_FIRST + 1
	TVM_EXPAND             = TV_FIRST + 2
	TVM_GETITEMRECT        = TV_FIRST + 4
	TVM_GETCOUNT           = TV_FIRST + 5
	TVM_GETINDENT          = TV_FIRST + 6
	TVM_SETINDENT          = TV_FIRST + 7
	TVM_GETIMAGELIST       = TV_FIRST + 8
	TVM_SETIMAGELIST       = TV_FIRST + 9
	TVM_GETNEXTITEM        = TV_FIRST + 10
	TVM_SELECTITEM         = TV_FIRST + 11
	TVM_GETITEM            = TV_FIRST + 12
	TVM_SETITEM            = TV_FIRST + 13
	TVM_EDITLABEL          = TV_FIRST + 14
	TVM_GETEDITCONTROL     = TV_FIRST + 15
	TVM_GETVISIBLECOUNT    = TV_FIRST + 16
	TVM_HITTEST            = TV_FIRST + 17
	TVM_CREATEDRAGIMAGE    = TV_FIRST + 18
	TVM_SORTCHILDREN       = TV_FIRST + 19
	TVM_ENSUREVISIBLE      = TV_FIRST + 20
	TVM_SORTCHILDRENCB     = TV_FIRST + 21
	TVM_ENDEDITLABELNOW    = TV_FIRST + 22
	TVM_GETISEARCHSTRING   = TV_FIRST + 23
	TVM_SETTOOLTIPS        = TV_FIRST + 24
	TVM_GETTOOLTIPS        = TV_FIRST + 25
	TVM_SETINSERTMARK      = TV_FIRST + 26
	TVM_SETITEMHEIGHT      = TV_FIRST + 27
	TVM_GETITEMHEIGHT      = TV_FIRST + 28
	TVM_SETBKCOLOR         = TV_FIRST + 29
	TVM_SETTEXTCOLOR       = TV_FIRST + 30
	TVM_GETBKCOLOR         = TV_FIRST + 31
	TVM_GETTEXTCOLOR       = TV_FIRST + 32
	TVM_SETSCROLLTIME      = TV_FIRST + 33
	TVM_GETSCROLLTIME      = TV_FIRST + 34
	TVM_SETINSERTMARKCOLOR = TV_FIRST + 37
	TVM_GETINSERTMARKCOLOR = TV_FIRST + 38
	TVM_GETITEMSTATE = TV_FIRST + 39
	TVM_SETLINECOLOR = TV_FIRST + 40
	TVM_GETLINECOLOR = TV_FIRST + 41

	TVN_SELCHANGING        = TVN_FIRST - 1
	TVN_SELCHANGED         = TVN_FIRST - 2
	TVN_GETDISPINFO        = TVN_FIRST - 3
	TVN_SETDISPINFO        = TVN_FIRST - 4
	TVN_ITEMEXPANDING      = TVN_FIRST - 5
	TVN_ITEMEXPANDED       = TVN_FIRST - 6
	TVN_BEGINDRAG          = TVN_FIRST - 7
	TVN_BEGINRDRAG         = TVN_FIRST - 8
	TVN_DELETEITEM         = TVN_FIRST - 9
	TVN_BEGINLABELEDIT     = TVN_FIRST - 10
	TVN_ENDLABELEDIT       = TVN_FIRST - 11
	TVN_KEYDOWN            = TVN_FIRST - 12
	TVN_GETINFOTIP         = TVN_FIRST - 13
	TVN_SINGLEEXPAND       = TVN_FIRST - 15

	TVN_SELCHANGINGW       = TVN_FIRST - 50
	TVN_SELCHANGEDW        = TVN_FIRST - 51
	TVN_GETDISPINFOW       = TVN_FIRST - 52
	TVN_SETDISPINFOW       = TVN_FIRST - 53
	TVN_BEGINLABELEDITW    = TVN_FIRST - 59
	TVN_ENDLABELEDITW      = TVN_FIRST - 60

	
	NM_CLICK           = NM_FIRST - 2  # uses NMCLICK type
	NM_DBLCLK          = NM_FIRST - 3
	NM_RETURN          = NM_FIRST - 4
	NM_RCLICK          = NM_FIRST - 5  # uses NMCLICK type
	
	NM_RDBLCLK         = NM_FIRST - 6
	NM_SETFOCUS        = NM_FIRST - 7
	NM_KILLFOCUS       = NM_FIRST - 8
	NM_CUSTOMDRAW      = NM_FIRST - 12
	NM_HOVER           = NM_FIRST - 13
	NM_NCHITTEST       = NM_FIRST - 14 # uses NMMOUSE type
	NM_KEYDOWN         = NM_FIRST - 15 # uses NMKEY type
	NM_RELEASEDCAPTURE = NM_FIRST - 16
	NM_SETCURSOR       = NM_FIRST - 17 # uses NMMOUSE type
	NM_CHAR            = NM_FIRST - 18 # uses NMCHAR type
	NM_TOOLTIPSCREATED = NM_FIRST - 19 # notify of when the tooltips window is create
	NM_LDOWN           = NM_FIRST - 20
	NM_RDOWN           = NM_FIRST - 21
	NM_THEMECHANGED    = NM_FIRST - 22
	
Msgs.__dict__.update(control.control_msgs.__dict__)


class TVITEM(Structure):
	_fields_ = [("mask", UINT),
					("hItem", HANDLE),
					("state", UINT),
					("stateMask", UINT),
					("pszText", DWORD),
					("cchTextMax", INT),
					("iImage", INT),
					("iSelectedImage", INT),
					("cChildren", INT),
					("lParam", LPARAM),]
#	
class TVITEMEX(Structure):
	_fields_ = [("mask", UINT),
					("hItem", HANDLE),
					("state", UINT),
					("stateMask", UINT),
					("pszText", DWORD),
					("cchTextMax", INT),
					("iImage", INT),
					("iSelectedImage", INT),
					("cChildren", INT),
					("lParam", LPARAM),
					("iIntegral", INT)]
	

class TVINSERTSTRUCT(Structure):
	_fields_ = [("hParent", HANDLE),
					("hInsertAfter", HANDLE),
					("item", TVITEMEX)]
	
class NMTREEVIEW(Structure):
	_fields_ = [("hdr", NMHDR),
					("action", UINT),
					("itemOld", TVITEM),		# not TVITEMEX
					("itemNew", TVITEM),		# not TVITEMEX
					("ptDrag", POINT)]

class NMTVKEYDOWN(Structure):
	_fields_ = [("hdr", NMHDR),
					("wVKey", WORD),
					("flags", UINT)]

class NMTVDISPINFO(Structure):
	_fields_ = [("hdr", NMHDR),
					("item", TVITEM)]

class TVHITTESTINFO(Structure):
	_fields_ = [("pt", POINT),
					("flags", UINT),
					("hItem", HANDLE)]

TVCOMPAREFUNC = WINFUNCTYPE(INT, LPARAM, LPARAM, LPARAM)
class TVSORTCB(Structure):
	_fields_ = [("hParent", HANDLE),
					("lpfnCompare", TVCOMPAREFUNC),
					("lParam", LPARAM)]

class NMCUSTOMDRAW(Structure):
	_fields_ = [("hdr", NMHDR),
					("dwDrawStage", DWORD),
					("hdc", HANDLE),
					("rc", RECT),
					("dwItemSpec", DWORD),
					("uItemState", UINT),
					("lItemlParam", LPARAM)]


class NMTVCUSTOMDRAW(Structure):
	PREPAINT           = 1
	ITEM               = 65536
	ITEMPREPAINT       = (ITEM | PREPAINT)
	
	# customdraw return flags
	# CDRF_*
	DODEFAULT          = 0
	NEWFONT            = 2
	SKIPDEFAULT        = 4
	NOTIFYPOSTPAINT    = 16
	NOTIFYITEMDRAW	= 32
	
		
	#TVCDRF_NOIMAGES # ??
	
	_fields_ = [("hdr", NMHDR),
						("drawStage", DWORD),
						("hdc", HANDLE),
						("rc", RECT),
						("hItem", DWORD),
						("state", UINT),
						("itemlParam", LPARAM),
						("clrText", COLORREF),
						("clrTextBk", COLORREF),
				#if (_WIN32_IE >= 0x0400)"
						("level", INT),]


