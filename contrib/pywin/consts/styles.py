"""module containing styles (style and exstyle not commoncontrols
extendedstyles) for window classes.

Use the GetStyles function to get the dictionary of styles supported
by the window class.

use:
	styles= GetStyles('button')
	if styles==None:
			pass

GetStyles will return None if no dict could be found. But check for None
is required, cos the dict may be empty for a window that does not 
define any styles.

You can check if a class is supported by examing the SUPPORTED
tuple

if 'button' in SUPPORTED:
	styles= GetStyles('button')

NOTES

		- classname is handled case insensitive 
		
		- styles for the 'window' clas you can retreve from here. 
			'window' is not really a classname, its more like a placeholder 
			so you can access the styles available for main windows
"""

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
SUPPORTED= (			# must be lowercase
							'window',
							'dialog', 
							'button',
							'combobox'
							'static',
							'edit',
							'listbox',
							'scrollbar',
							'systreeview32',
							'sysanimate32',
							'sysdatetimepick32',
							'sysheader32',
							'msctls_hotkey32',
							'sysipaddress32',
							'syslistview32',
							'sysmonthcal32',
							'syspager',
							'msctls_progress32',
							'rebarwindow32',
							'msctls_statusbar32',
							'systabcontrol32',
							'toolbarwindow32',
							'tooltips_class32',
							'msctls_trackbar32',
							'msctls_updown32'
							)



class window:
	WS_OVERLAPPED      = 0
	WS_MINIMIZE        = 536870912
	WS_VISIBLE         = 268435456
	WS_DISABLED        = 134217728
	WS_CLIPCHILDREN    = 33554432
	WS_MAXIMIZE        = 16777216
	WS_CAPTION         = 12582912 
	WS_BORDER          = 8388608
	WS_DLGFRAME        = 4194304
	WS_VSCROLL         = 2097152
	WS_HSCROLL         = 1048576
	WS_SYSMENU         = 524288
	WS_SIZEBOX           =  262144
	WS_MINIMIZEBOX     = 131072
	WS_MAXIMIZEBOX     = 65536
	WS_EX_DLGMODALFRAME   = 1
	WS_EX_TOPMOST         = 8
	WS_EX_ACCEPTFILES     = 16
	WS_EX_TRANSPARENT     = 32
	WS_EX_TOOLWINDOW      = 128
	WS_EX_SMCAPTION       = 128
	WS_EX_WINDOWEDGE      = 256
	WS_EX_CLIENTEDGE      = 512
	WS_EX_CONTEXTHELP     = 1024
	WS_EX_RIGHT           = 4096
	WS_EX_LEFT            = 0
	WS_EX_RTLREADING      = 8192
	WS_EX_LTRREADING      = 0
	WS_EX_LEFTSCROLLBAR   = 16384
	WS_EX_RIGHTSCROLLBAR  = 0
	WS_EX_STATICEDGE      = 131072
	WS_EX_CONTROLPARENT   = 65536
	WS_EX_APPWINDOW       = 262144
	WS_EX_LAYERED         = 524288
	WS_EX_NOINHERITLAYOUT = 1048576
	WS_EX_LAYOUTRTL       = 4194304
	WS_EX_COMPOSITED      = 33554432
	WS_EX_NOACTIVATE      = 134217728

class dialog:
	WS_POPUP           = 2147483648
	WS_CHILD = 1073741824
	WS_VISIBLE         = 268435456
	WS_OVERLAPPED      = 0
	WS_MINIMIZE        = 536870912
	WS_VISIBLE         = 268435456
	WS_DISABLED        = 134217728
	WS_CLIPSIBLINGS    = 67108864
	WS_CLIPCHILDREN    = 33554432
	WS_MAXIMIZE        = 16777216
	WS_CAPTION         = 12582912 
	WS_BORDER          = 8388608
	WS_DLGFRAME        = 4194304
	WS_VSCROLL         = 2097152
	WS_HSCROLL         = 1048576
	WS_SYSMENU         = 524288
	WS_THICKFRAME      = 262144
	WS_SIZEBOX           = WS_THICKFRAME
	WS_MINIMIZEBOX     = 131072
	WS_MAXIMIZEBOX     = 65536
	DS_3DLOOK        = 4
	DS_ABSALIGN      = 1
	DS_SYSMODAL      = 2
	DS_3DLOOK        = 4
	DS_FIXEDSYS      = 8
	DS_NOFAILCREATE  = 16
	DS_LOCALEDIT     = 32 # Edit items get Local storage.
	DS_SETFONT       = 64 # User specified font for Dlg controls
	DS_MODALFRAME    = 128 # Can be combined with WS_CAPTION
	DS_NOIDLEMSG     = 256 # WM_ENTERIDLE message will not be sent
	DS_SETFOREGROUND = 512 # not in win3.1
	DS_CONTROL       = 1024
	DS_CENTER        = 2048
	DS_CENTERMOUSE   = 4096
	DS_CONTEXTHELP   = 8192
	
class _s:
	WS_POPUP           = 2147483648
	WS_POPUPWINDOW = WS_POPUP|window.WS_BORDER|window.WS_SYSMENU
	WS_GROUP = 131072
	WS_TABSTOP = 65536
	WS_VISIBLE = 268435456
	WS_DISABLED = 134217728
	WS_CHILD = 1073741824
	WS_CLIPCHILDREN    = 33554432
	WS_CLIPSIBLINGS    = 67108864
	WS_HSCROLL = 1048576
	WS_VSCROLL = 2097152
	WS_BORDER          = 8388608
	WS_EX_ACCEPTFILES = 16
	WS_EX_CLIENTEDGE = 512
	WS_EX_MDICHILD = 64
	WS_EX_CONTROLPARENT   = 65536
	
class button:
	BS_TEXT            = 0
	BS_PUSHBUTTON      = 0
	BS_DEFPUSHBUTTON   = 1
	BS_DEFAULT         = BS_DEFPUSHBUTTON
	BS_CHECKBOX        = 2
	BS_AUTOCHECKBOX    = 3
	BS_RADIOBUTTON     = 4
	BS_3STATE          = 5
	BS_AUTO3STATE      = 6
	BS_GROUPBOX        = 7
	BS_USERBUTTON      = 8
	BS_AUTORADIOBUTTON = 9
	BS_OWNERDRAW       = 11
	BS_LEFTTEXT        = 32
	BS_ICON            = 64
	BS_BITMAP          = 128
	BS_LEFT            = 256
	BS_RIGHT           = 512
	BS_CENTER          = 768
	BS_TOP             = 1024
	BS_BOTTOM          = 2048
	BS_VCENTER         = 3072
	BS_PUSHLIKE        = 4096
	BS_MULTILINE       = 8192
	BS_NOTIFY          = 16384
	BS_FLAT            = 32768
	BS_RIGHTBUTTON     = BS_LEFTTEXT
button.__dict__.update(_s.__dict__)


class combobox:
	CBS_SIMPLE            = 1
	CBS_DROPDOWN          = 2
	CBS_DROPDOWNLIST      = 3
	CBS_OWNERDRAWFIXED    = 16
	CBS_OWNERDRAWVARIABLE = 32
	CBS_AUTOHSCROLL       = 64
	CBS_OEMCONVERT        = 128
	CBS_SORT              = 256
	CBS_HASSTRINGS        = 512
	CBS_NOINTEGRALHEIGHT  = 1024
	CBS_DISABLENOSCROLL   = 2048
	CBS_UPPERCASE         = 8192
	CBS_LOWERCASE         = 16384
combobox.__dict__.update(_s.__dict__)

class static:
	SS_LEFT            = 0
	SS_CENTER          = 1
	SS_RIGHT           = 2
	SS_ICON            = 3
	SS_BLACKRECT       = 4
	SS_GRAYRECT        = 5
	SS_WHITERECT       = 6
	SS_BLACKFRAME      = 7
	SS_GRAYFRAME       = 8
	SS_WHITEFRAME      = 9
	SS_USERITEM        = 10
	SS_SIMPLE          = 11
	SS_LEFTNOWORDWRAP  = 12
	SS_NOWORDWRAP      = SS_LEFTNOWORDWRAP
	SS_OWNERDRAW       = 13
	SS_BITMAP          = 14
	SS_ENHMETAFILE     = 15
	SS_ETCHEDHORZ      = 16
	SS_ETCHEDVERT      = 17
	SS_ETCHEDFRAME     = 18
	SS_REALSIZECONTROL = 64
	SS_NOPREFIX        = 128 
	SS_NOTIFY          = 256
	SS_CENTERIMAGE     = 512
	SS_RIGHTJUST       = 1024
	SS_REALSIZEIMAGE   = 2048
	SS_REALSIZE        = SS_REALSIZEIMAGE
	SS_SUNKEN          = 4096
	SS_ENDELLIPSIS     = 16384
	SS_PATHELLIPSIS    = 32768
	SS_WORDELLIPSIS    = 49152
	SS_ELLIPSISMASK    = 49152
static.__dict__.update(_s.__dict__)	


class scrollbar:
	SBS_HORZ                    = 0
	SBS_VERT                    = 1
	SBS_TOPALIGN                = 2
	SBS_LEFTALIGN               = 2
	SBS_BOTTOMALIGN             = 4
	SBS_RIGHTALIGN              = 4
	SBS_SIZEBOXTOPLEFTALIGN     = 2
	SBS_SIZEBOXBOTTOMRIGHTALIGN = 4
	SBS_SIZEBOX                 = 8
	SBS_SIZEGRIP                = 16
scrollbar.__dict__.update(_s.__dict__)	

class edit:
	ES_LEFT        = 0
	ES_CENTER      = 1
	ES_RIGHT       = 2
	ES_MULTILINE   = 4
	ES_UPPERCASE   = 8
	ES_LOWERCASE   = 16
	ES_PASSWORD    = 32
	ES_AUTOVSCROLL = 64
	ES_AUTOHSCROLL = 128
	ES_NOHIDESEL   = 256
	ES_OEMCONVERT  = 1024
	ES_READONLY    = 2048
	ES_WANTRETURN  = 4096
	ES_NUMBER      = 8192
edit.__dict__.update(_s.__dict__)	


class listbox:
	LBS_NOTIFY            = 1
	LBS_SORT              = 2
	LBS_NOREDRAW          = 4
	LBS_MULTIPLESEL       = 8
	LBS_OWNERDRAWFIXED    = 16
	LBS_OWNERDRAWVARIABLE = 32
	LBS_HASSTRINGS        = 64
	LBS_USETABSTOPS       = 128
	LBS_NOINTEGRALHEIGHT  = 256
	LBS_MULTICOLUMN       = 512
	LBS_WANTKEYBOARDINPUT = 1024
	LBS_EXTENDEDSEL       = 2048
	LBS_DISABLENOSCROLL   = 4096
	LBS_NODATA            = 8192
	LBS_NOSEL             = 16384
	LBS_STANDARD= LBS_NOTIFY|LBS_SORT|_s.WS_VSCROLL|_s.WS_BORDER	
listbox.__dict__.update(_s.__dict__)	


# common controls---------------------------------------------------------
###################################################

class _ccs:
	CCS_TOP           = 1
	CCS_NOMOVEY       = 2
	CCS_BOTTOM        = 3
	CCS_NORESIZE      = 4
	CCS_NOPARENTALIGN = 8
	CCS_ADJUSTABLE    = 32
	CCS_NODIVIDER     = 64
	CCS_VERT          = 128
	CCS_LEFT          = CCS_VERT|CCS_TOP
	CCS_RIGHT         = CCS_VERT|CCS_BOTTOM
	CCS_NOMOVEX       = CCS_VERT|CCS_NOMOVEY
_ccs.__dict__.update(_s.__dict__)

class msctls_updown32:
	UDS_WRAP             = 1
	UDS_SETBUDDYINT      = 2
	UDS_ALIGNRIGHT       = 4
	UDS_ALIGNLEFT        = 8
	UDS_AUTOBUDDY        = 16
	UDS_ARROWKEYS        = 32
	UDS_HORZ             = 64
	UDS_NOTHOUSANDS      = 128
	UDS_HOTTRACK         = 256
msctls_updown32.__dict__.update(_ccs.__dict__)

class msctls_trackbar32:
	TBS_AUTOTICKS      = 1
	TBS_VERT           = 2
	TBS_HORZ           = 0
	TBS_TOP            = 4
	TBS_BOTTOM         = 0
	TBS_LEFT           = 4
	TBS_RIGHT          = 0
	TBS_BOTH           = 8
	TBS_NOTICKS        = 16
	TBS_ENABLESELRANGE = 32
	TBS_FIXEDLENGTH    = 64
	TBS_NOTHUMB        = 128
	TBS_TOOLTIPS       = 256
	TBS_REVERSED       = 512  
	TBS_DOWNISLEFT     = 1024  
msctls_trackbar32.__dict__.update(_ccs.__dict__)

class tooltips_class32:
	TTS_ALWAYSTIP = 1
	TTS_NOPREFIX  = 2
	TTS_NOANIMATE = 16
	TTS_NOFADE    = 32
	TTS_BALLOON   = 64
	TTS_CLOSE     = 128
tooltips_class32.__dict__.update(_ccs.__dict__)

class toolbarwindow32:
	TBSTYLE_TOOLTIPS        = 256
	TBSTYLE_WRAPABLE        = 512
	TBSTYLE_ALTDRAG         = 1024
	TBSTYLE_FLAT            = 2048
	TBSTYLE_LIST            = 4096
	TBSTYLE_CUSTOMERASE     = 8192
	TBSTYLE_REGISTERDROP    = 16384
	TBSTYLE_TRANSPARENT     = 32768
	TBSTYLE_EX_DRAWDDARROWS = 1
	TBSTYLE_EX_MIXEDBUTTONS       = 8
	TBSTYLE_EX_HIDECLIPPEDBUTTONS = 16 
	TBSTYLE_EX_DOUBLEBUFFER       = 128
toolbarwindow32.__dict__.update(_ccs.__dict__)

class systabcontrol32:
	TCS_SCROLLOPPOSITE      = 1
	TCS_BOTTOM              = 2
	TCS_RIGHT               = 2
	TCS_MULTISELECT         = 4
	TCS_FLATBUTTONS         = 8
	TCS_FORCEICONLEFT       = 16
	TCS_FORCELABELLEFT      = 32
	TCS_HOTTRACK            = 64
	TCS_VERTICAL            = 128
	TCS_TABS                = 0
	TCS_BUTTONS             = 256
	TCS_SINGLELINE          = 0
	TCS_MULTILINE           = 512
	TCS_RIGHTJUSTIFY        = 0
	TCS_FIXEDWIDTH          = 1024
	TCS_RAGGEDRIGHT         = 2048
	TCS_FOCUSONBUTTONDOWN   = 4096
	TCS_OWNERDRAWFIXED      = 8192
	TCS_TOOLTIPS            = 16384
	TCS_FOCUSNEVER          = 32768
systabcontrol32.__dict__.update(_ccs.__dict__)

class msctls_statusbar32:
	SBARS_SIZEGRIP = 256
	SBARS_TOOLTIPS = 2048
msctls_statusbar32.__dict__.update(_ccs.__dict__)


class rebarwindow32:
	RBS_TOOLTIPS        = 256
	RBS_VARHEIGHT       = 512
	RBS_BANDBORDERS     = 1024
	RBS_FIXEDORDER      = 2048
	RBS_REGISTERDROP    = 4096
	RBS_AUTOSIZE        = 8192
	RBS_VERTICALGRIPPER = 16384 
	RBS_DBLCLKTOGGLE    = 32768
rebarwindow32.__dict__.update(_ccs.__dict__)

class msctls_progress32:
	PBS_SMOOTH     = 1
	PBS_VERTICAL   = 4
msctls_progress32.__dict__.update(_ccs.__dict__)

class syspager:
	PGS_VERT                = 0
	PGS_HORZ                = 1
	PGS_AUTOSCROLL          = 2
	PGS_DRAGNDROP           = 4
syspager.__dict__.update(_ccs.__dict__)

class sysmonthcal32:
	MCS_DAYSTATE        = 1
	MCS_MULTISELECT     = 2
	MCS_WEEKNUMBERS     = 4
	MCS_NOTODAYCIRCLE   = 8
	MCS_NOTODAY         = 16
sysmonthcal32.__dict__.update(_ccs.__dict__)

class syslistview32:
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
syslistview32.__dict__.update(_ccs.__dict__)	

class sysipaddress32: pass
sysipaddress32.__dict__.update(_ccs.__dict__)	

class msctls_hotkey32: pass
msctls_hotkey32.__dict__.update(_ccs.__dict__)	

class sysheader32:
	HDS_HORZ        = 0
	HDS_BUTTONS     = 2
	HDS_HOTTRACK    = 4
	HDS_HIDDEN      = 8
	HDS_DRAGDROP    = 64
	HDS_FULLDRAG    = 128
	HDS_FILTERBAR   = 256
	HDS_FLAT        = 512
sysheader32.__dict__.update(_ccs.__dict__)

class sysdatetimepick32:
	DTS_UPDOWN          = 1 
	DTS_SHOWNONE        = 2 
	DTS_SHORTDATEFORMAT = 0
	DTS_LONGDATEFORMAT  = 4
	DTS_SHORTDATECENTURYFORMAT = 12 
	DTS_TIMEFORMAT      = 9 
	DTS_APPCANPARSE     = 16
	DTS_RIGHTALIGN      = 32 
sysdatetimepick32.__dict__.update(_ccs.__dict__)

class sysanimate32:
	ACS_CENTER	=     1
	ACS_TRANSPARENT	= 2
	ACS_AUTOPLAY	=   4
	ACS_TIMER	=     8
sysanimate32.__dict__.update(_ccs.__dict__)	

class systreeview32:
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
systreeview32.__dict__.update(_ccs.__dict__)	



################################################

def GetStyles(classname):
	try:
		d=globals()[classname.lower()].__dict__.copy()
		del d['__doc__']
		del d['__module__']
		return d
	except: pass


#------------------------------------------------------------------------------------------
def test():
	print GetStyles('button')
		
#test()
