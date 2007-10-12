

from wnd.wintypes import (user32,
												Structure, 
												byref,
												addressof,
												sizeof,
												WINFUNCTYPE,
												c_char_p,
												UINT_MAX,
												UINT,
												INT,
												DWORD,
												LPARAM,
												NMHDR,
												WORD,
												HANDLE,
												RECT,
												LONG,
												POINT,
												LPCTSTR,
												MAKELONG,
												LOWORD,
												HIWORD,)
from wnd import fwtypes as fw
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


COMPAREFUNC = WINFUNCTYPE(INT, LPARAM, LPARAM, LPARAM)
def INDEXTOSTATEIMAGEMASK(i): return i << 12 
def  INDEXTOOVERLAYMASK(i): return i << 8

#***********************************************
NM_FIRST = UINT_MAX
LVN_FIRST = (UINT_MAX) - 100
LVM_FIRST = 4096

class Styles:
	
	LVS_ICON            = 0			#
	LVS_REPORT          = 1
	LVS_SMALLICON       = 2		#
	LVS_LIST            = 3
	LVS_OWNERDATA       = 4096
	
		
	LVS_TYPEMASK        = 3
	LVS_SINGLESEL       = 4
	LVS_SHOWSELALWAYS   = 8
	LVS_SORTASCENDING   = 16
	LVS_SORTDESCENDING  = 32
	LVS_SHAREIMAGELISTS = 64
	LVS_NOLABELWRAP     = 128
	LVS_AUTOARRANGE     = 256
	LVS_EDITLABELS      = 512
	LVS_NOSCROLL        = 8192
	LVS_NOCOLUMNHEADER = 16384
	LVS_NOSORTHEADER = 32768
	LVS_TYPESTYLEMASK = 64512
		
	LVS_EX_GRIDLINES        = 1
	LVS_EX_SUBITEMIMAGES    = 2
	LVS_EX_CHECKBOXES       = 4
	LVS_EX_TRACKSELECT      = 8
	LVS_EX_HEADERDRAGDROP   = 16
	LVS_EX_FULLROWSELECT    = 32 
	LVS_EX_ONECLICKACTIVATE = 64
	LVS_EX_TWOCLICKACTIVATE = 128
	LVS_EX_FLATSB           = 256
	LVS_EX_REGIONAL         = 512
	LVS_EX_INFOTIP          = 1024 
	LVS_EX_UNDERLINEHOT     = 2048
	LVS_EX_UNDERLINECOLD    = 4096
	LVS_EX_MULTIWORKAREAS   = 8192
	LVS_EX_LABELTIP         = 16384 
	LVS_EX_BORDERSELECT     = 32768 
	LVS_EX_DOUBLEBUFFER     = 65536
	LVS_EX_HIDELABELS       = 131072
	LVS_EX_SINGLEROW        = 262144
	LVS_EX_SNAPTOGRID       = 524288 
	LVS_EX_SIMPLESELECT     = 1048576 

	WS_CLIENT_CUSTOMDRAW = 1
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += 'LVS_EX_', 'LVS_'



class Msgs: 
	
	MSG_SETEXSTYLE= LVM_FIRST + 54 # LVM_SETEXTENDEDLISTVIEWSTYLE
	MSG_GETEXSTYLE= LVM_FIRST +55 # LVM_GETEXTENDEDLISTVIEWSTYLE
	
	WM_WINDOWPOSCHANGING = 70
	WM_WINDOWPOSCHANGED = 71
	WM_VSCROLL = 277
	WM_HSCROLL = 276
	
	LVM_GETBKCOLOR         = LVM_FIRST + 0
	LVM_SETBKCOLOR         = LVM_FIRST + 1		
	LVM_GETIMAGELIST       = LVM_FIRST + 2
	LVM_SETIMAGELIST       = LVM_FIRST + 3
	LVM_GETITEMCOUNT  =  LVM_FIRST + 4
	LVM_GETITEM            = LVM_FIRST + 5
	LVM_SETITEM = LVM_FIRST + 6
	LVM_INSERTITEM = LVM_FIRST + 7
	LVM_DELETEITEM         = LVM_FIRST + 8
	LVM_DELETEALLITEMS =  LVM_FIRST + 9
	LVM_GETCALLBACKMASK    = LVM_FIRST + 10
	LVM_SETCALLBACKMASK    = LVM_FIRST + 11
	LVM_GETNEXTITEM        = LVM_FIRST + 12
	LVM_FINDITEM           = LVM_FIRST + 13
	LVM_GETITEMRECT        = LVM_FIRST + 14
	LVM_GETITEMPOSITION    = LVM_FIRST + 16
	LVM_GETSTRINGWIDTH     = LVM_FIRST + 17
	LVM_ENSUREVISIBLE      = LVM_FIRST + 19
	LVM_SCROLL             = LVM_FIRST + 20
	LVM_REDRAWITEMS        = LVM_FIRST + 21
	LVM_ARRANGE            = LVM_FIRST + 22
	LVM_EDITLABEL          = LVM_FIRST + 23
	LVM_GETEDITCONTROL     = LVM_FIRST + 24
	LVM_GETCOLUMN          = LVM_FIRST + 25
	LVM_SETCOLUMN          = LVM_FIRST + 26
	LVM_INSERTCOLUMN      = LVM_FIRST + 27
	LVM_DELETECOLUMN       = LVM_FIRST + 28
	LVM_SETCOLUMNWIDTH         = LVM_FIRST + 30
	LVM_GETHEADER       =        LVM_FIRST + 31
	LVM_CREATEDRAGIMAGE    = LVM_FIRST + 33
	LVM_GETVIEWRECT        = LVM_FIRST + 34
	LVM_GETTEXTCOLOR       = LVM_FIRST + 35
	LVM_SETTEXTCOLOR       = LVM_FIRST + 36
	LVM_GETTEXTBKCOLOR     = LVM_FIRST + 37
	LVM_SETTEXTBKCOLOR     = LVM_FIRST + 38
	LVM_GETTOPINDEX        = LVM_FIRST + 39
	LVM_GETCOUNTPERPAGE    = LVM_FIRST + 40
	LVM_GETORIGIN          = LVM_FIRST + 41
	LVM_UPDATE             = LVM_FIRST + 42
	LVM_SETITEMSTATE  =  LVM_FIRST + 43
	LVM_GETITEMSTATE       = LVM_FIRST + 44
	LVM_SETITEMCOUNT       = LVM_FIRST + 47
	LVM_SORTITEMS          = LVM_FIRST + 48
	LVM_SETITEMPOSITION32  = LVM_FIRST + 49
	LVM_GETSELECTEDCOUNT   = LVM_FIRST + 50
	LVM_GETITEMSPACING     = LVM_FIRST + 51
	LVM_SETICONSPACING     = LVM_FIRST + 53
	LVM_GETISEARCHSTRING   = LVM_FIRST + 52
	LVM_GETSUBITEMRECT      = LVM_FIRST + 56
	LVM_SUBITEMHITTEST      = LVM_FIRST + 57
	LVM_SETCOLUMNORDERARRAY = LVM_FIRST + 58
	LVM_GETCOLUMNORDERARRAY = LVM_FIRST + 59
	LVM_GETHOTITEM  = LVM_FIRST + 61
	LVM_SETHOTCURSOR  = LVM_FIRST + 62
	LVM_GETHOTCURSOR  = LVM_FIRST + 63
	LVM_APPROXIMATEVIEWRECT = LVM_FIRST + 64
	LVM_SETWORKAREAS         = LVM_FIRST + 65
	LVM_GETSELECTIONMARK    = LVM_FIRST + 66
	LVM_SETSELECTIONMARK    = LVM_FIRST + 67
	LVM_GETWORKAREAS        = LVM_FIRST + 70
	LVM_SETHOVERTIME        = LVM_FIRST + 71
	LVM_GETHOVERTIME        = LVM_FIRST + 72
	LVM_GETNUMBEROFWORKAREAS  = LVM_FIRST + 73
	LVM_SETTOOLTIPS       = LVM_FIRST + 74
	LVM_GETTOOLTIPS       = LVM_FIRST + 78


	LVN_ITEMCHANGING    = LVN_FIRST
	LVN_ITEMCHANGED     = LVN_FIRST - 1
	LVN_INSERTITEM      = LVN_FIRST - 2
	LVN_DELETEITEM      = LVN_FIRST - 3
	LVN_DELETEALLITEMS  = LVN_FIRST - 4
	LVN_BEGINLABELEDIT  = LVN_FIRST - 5
	LVN_ENDLABELEDIT    = LVN_FIRST - 6
	LVN_COLUMNCLICK     = LVN_FIRST - 8
	LVN_BEGINDRAG       = LVN_FIRST - 9
	LVN_BEGINRDRAG      = LVN_FIRST - 11
	LVN_ODCACHEHINT     = LVN_FIRST - 13
	LVN_ODFINDITEM      = LVN_FIRST - 52
	LVN_ITEMACTIVATE    = LVN_FIRST - 14
	LVN_ODSTATECHANGED  = LVN_FIRST - 15
	LVN_HOTTRACK        = LVN_FIRST - 21
	LVN_GETDISPINFO     = LVN_FIRST - 50
	LVN_SETDISPINFO     = LVN_FIRST - 51
	LVN_KEYDOWN          = LVN_FIRST - 55
	
	LVN_BEGINLABELEDITW = LVN_FIRST - 75
	LVN_ENDLABELEDITW   = LVN_FIRST - 76
	LVN_ODFINDITEMW     = LVN_FIRST - 79
	LVN_GETDISPINFOW    = LVN_FIRST - 77
	LVN_SETDISPINFOW    = LVN_FIRST - 78

	
	
	NM_OUTOFMEMORY     = NM_FIRST - 1
	
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


	
class LV_COLUMN(Structure):
	"""Extended LV_COLUMN structure."""
	LVCF_FMT               = 1
	LVCF_WIDTH             = 2
	LVCF_TEXT              = 4
	LVCF_SUBITEM           = 8
	LVCF_IMAGE             = 16
	LVCF_ORDER             = 32
	LVCF_ORDER             = 32
	_fields_ = [("mask", UINT),
						("fmt", INT),
						("cx", INT),
						("pszText", DWORD),	# address of buffer
						("cchTextMax", INT),
						("iSubItem", INT),
						("iImage", INT),
						("iOrder", INT)]	

class LV_ITEM(Structure):
	LVIF_TEXT              = 1
	LVIF_IMAGE             = 2
	LVIF_PARAM             = 4
	LVIF_STATE             = 8
	LVIF_INDENT            = 16
	LVIF_NORECOMPUTE       = 2048
	LVIS_FOCUSED         =   1
	LVIS_SELECTED        =   2
	_fields_ = [("mask", UINT),
						("iItem", INT),
						("iSubItem", INT),
						("state", UINT),
						("stateMask", UINT),
						("pszText", DWORD),	# addressof buffer
						("cchTextMax", INT),
						("iImage", INT),
						("lParam", LPARAM),
						("iIndent", INT)]



class STYLESTRUCT(Structure):
	_fields_ = [("styleOld", DWORD), 
					("styleNew", DWORD)]

class NMKEY(Structure):
	_fields_ = [("hdr", NMHDR),
					("nVKey", WORD),
					("uFlags", UINT)]

class NMCUSTOMDRAW(Structure):
	CDDS_PREPAINT           = 1
	CDDS_ITEM               = 65536
	CDDS_ITEMPREPAINT       = (CDDS_ITEM | CDDS_PREPAINT)
	CDDS_SUBITEM            = 131072

	# customdraw return flags
	CDRF_DODEFAULT          = 0
	CDRF_NEWFONT            = 2
	CDRF_SKIPDEFAULT        = 4
	CDRF_NOTIFYPOSTPAINT    = 16
	CDRF_NOTIFYITEMDRAW	= 32
	CDRF_NOTIFYSUBITEMDRAW  = 32
	
	_fields_ = [("hdr" , NMHDR),
					("dwDrawStage" , DWORD),
					("hdc" , HANDLE),
					("rc" , RECT),
					("dwItemSpec" , DWORD),  
					("uItemState" , UINT),
					("lItemlParam" , LPARAM)]


class NMLVCUSTOMDRAW(Structure):
	# CDDS_*
	ITEM               = 65536
	SUBITEM            = 131072
	
	PREPAINT           = 1
	POSTPAINT          = 2
	
	ITEMPREPAINT       = (ITEM | PREPAINT)
	SUBITEMPREPAINT       = (ITEM | SUBITEM | PREPAINT)
	ITEMPOSTPAINT      = (ITEM | POSTPAINT)
	#print ITEM | SUBITEM| PREPAINT
	
	
	# customdraw return flags
	# CDRF_*
	DODEFAULT          = 0
	NEWFONT            = 2
	SKIPDEFAULT        = 4
	NOTIFYPOSTPAINT    = 16
	NOTIFYITEMDRAW	= 32
	NOTIFYSUBITEMDRAW  = 32
	
	
	# item states CDIS_*
	SELECTED         = 1
	GRAYED           = 2
	DISABLED         = 4
	CHECKED          = 8
	FOCUS            = 16
	DEFAULT          = 32
	HOT              = 64
	MARKED           = 128
	INDETERMINATE    = 256
	SHOWKEYBOARDCUES = 512
	
	_fields_ = [("hdr" , NMHDR),
						("drawStage" , DWORD),
						("hdc" , HANDLE),
						("rc" , RECT),
						("iItem" , DWORD),  
						("itemState" , UINT),
						("itemlParam" , LPARAM),	# from NMCUSTOMDRAW
						("clrText",     DWORD),
						("clrTextBk",  DWORD),
						("iSubItem",   LONG),]
							#("dwItemType",  DWORD),
							# Item custom draw
							#("clrFace",     DWORD),
							#("iIconEffect", LONG),
							#("iIconPhase",  LONG),
							#("iPartId",     LONG),
							#("iStateId",    LONG),
							# Group Custom Draw
							#("rcText",      RECT),
							#("uAlign",      DWORD)] # Alignment. Use LVGA_HEADER_CENTER, LVGA_HEADER_RIGHT, LVGA_HEADER_LEFT



class NMLVDISPINFO(Structure):
	_fields_ = [("hdr", NMHDR),
					("item", LV_ITEM)]

class NMLVCACHEHINT(Structure):
	_fields_ = [("hdr", NMHDR),
					("iFrom", INT),
					("iTo", INT)]

class NMLISTVIEW(Structure):
	LVIS_FOCUSED         =   1
	LVIS_SELECTED        =   2
	_fields_ = [("hdr", NMHDR),
					("iItem", INT),
					("iSubItem", INT),
					("uNewState", UINT),
					("uOldState", UINT),
					("uChanged", UINT),
					("ptAction", POINT),
					("lParam", LPARAM)]



class LVFINDINFO(Structure):
	LVFI_PARAM             = 1
	LVFI_STRING            = 2
	LVFI_PARTIAL           = 8
	LVFI_WRAP              = 32
	LVFI_NEARESTXY         = 64
	_fields_ = [("flags", UINT),
					("psz", LPCTSTR),
					("lParam", LPARAM),
					("pt", POINT),
					("vkDirection", UINT)]

class LVHITTESTINFO(Structure):
	_fields_ = [("pt", POINT),
					("flags", UINT),
					("iItem", INT),
					("iSubItem", INT)]


