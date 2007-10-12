
from wnd.wintypes import (Structure, 
												sizeof,
												byref,
												addressof,
												create_string_buffer,
												MAKELONG,
												LOWORD,
												HIWORD,
												NMHDR,
												LPSTR,
												c_char,
												c_char_p,
												HANDLE,
												UINT,
												LPARAM,
												INT,
												BYTE,
												DWORD,
												WORD,
												COLORREF,
												POINT,
												RECT,
												SIZE,
												UINT_MAX,
												memmove,
												InitCommonControlsEx)
from wnd.controls.base import control

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class NMTTDISPINFO(Structure):
	_fields_ = [("hdr", NMHDR),
					("lpszText", LPSTR),
					("szText", c_char*80),
					("hinst", HANDLE),
					("uFlags", UINT),
					#if (_WIN32_IE >= 0x0300)
					("lParam", LPARAM)]

class TBBUTTON(Structure):
	_fields_ = [("iBitmap", INT),
					("idCommand", INT),
					("fsState", BYTE),
					("fsStyle", BYTE),
					("dwData", DWORD),
					("iString", INT)]

class TBSAVEPARAMS(Structure):
	_fields_ = [("hkr", HANDLE),
					("pszSubKey", LPSTR),
					("pszValueName", LPSTR)]



SNAP_COOKIE= "TBS"

def ReadSnapshot(data):
	"""extracts TBBUTTON and string array from the passed data."""
		
	error = True
	data= create_string_buffer(data)
	
	if len(data) > (len(SNAP_COOKIE)+12):
		# test for cookie
		if data[:3]==SNAP_COOKIE:
			n= len(SNAP_COOKIE)+1
			
			# version and sizeof 
			ver= UINT.from_address(addressof(data)+n)
			n += 4
			szeof= UINT.from_address(addressof(data)+n)
			n += 4
			
			# get button array
			nButtons= UINT.from_address(addressof(data)+n)
			n += 4
			szeofBt= nButtons.value*sizeof(TBBUTTON)
			if len(data) > szeofBt+n:
				arrBt= (TBBUTTON*nButtons.value)()
				memmove(addressof(arrBt), addressof(data)+n, szeofBt)
				n+= szeofBt
				
				# get text array
				cchText= UINT.from_address(int(addressof(data)+n))
				n+= 4
				if len(data)== n + cchText.value+1:
					text= data[n:n+cchText.value]
					error= False
	
	if error: raise ValueError("invalid data")
	return arrBt, text


	


def SetupSnapshot(buttons):
	"""Helps to create a snapshot of a Toolbar.

	Call with the array of TBBUTTON structures of the Toolbar,
	write all the strings to the returned TBSNAPSHOT instance,
	then write the resulting data.

	Return value is a TBSNAPSHOT class, preinitialized
	to the contents of the passed array.

	The returned TBSNAPSHOT instance has two methods:

	AddText(i, text) to add a text string to its internal buffer.
		Use this to record the text strings for the buttons.
		'i' is the index of the string as given in the TBBUTTON structure
		(index of -1 is ignored) 'text' the actual text.

	Write()
		Returns a string containing all data necessary to restore
		a Toolbar.
	
	Sample use:

	# assert you have collected this button data from a Toolbar
	arr= (TBBUTTON*3)(
		TBBUTTON(1,2,3, 0, 0, -1),
		TBBUTTON(4,5,6, 0, 0, 0),
		TBBUTTON(7,8,9, 0, 0, 1),
		)

		s= SetupSnapshot(arr)
		for i in arr:
			s.AddText(i.iString, MyToolbar.GetItemText(i.idCommand))
		p= s.Write()

		# now a call to ReadSnapshot should restore the button and string array
		arr, string= ReadSnapshot(p)
	
	"""

	class TBSNAPSHOT(Structure):
		_pack_=2
		_fields_= [("type", c_char*len(SNAP_COOKIE)),
					("version", UINT),
					("cbSize", UINT),
					("nButtons", UINT),
					("arrButtons", TBBUTTON*len(buttons)),
					#("cbOrderArray", UINT),
					#()
					("cchText", UINT),]
		
		def __init__(self, cookie, buttons): 
			self.cbSize= sizeof(self)
			self.type= cookie
			self.nButtons= len(self.arrButtons)
			self.arrButtons= buttons
			self.textBuffer= [None, ]*self.nButtons
		
		def AddText(self, i, text):
			if i > -1: 
				self.textBuffer[i]= text
		
		def Write(self):
			text= [i for i in self.textBuffer  if i != None]
			text= '%s\x00\x00' % '\x00'.join(text)
			self.cchText= len(text)
			p= buffer(self)[:] + buffer(text)[:]
			return p
	
	return TBSNAPSHOT(SNAP_COOKIE, buttons)


def test():
	
	arr= (TBBUTTON*3)(
	TBBUTTON(1,2,3, 0, 0, -1),
	TBBUTTON(4,5,6, 0, 0, 0),
	TBBUTTON(7,8,9, 0, 0, 1),
	)

	s= SetupSnapshot(arr)

	s.AddText(1, 'fo')
	s.AddText(0, 'xx')
	p= s.Write()
	arr, sz= ReadSnapshot(p[:])
	


class NMTOOLBAR(Structure):
	_fields_ = [("hdr", NMHDR),
					("iItem", INT),
					("tbButton", TBBUTTON),
					("cchText", INT),
					("pszText", LPSTR)]	# addr of buffer

class TBBUTTONINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("dwMask", DWORD),
					("idCommand", INT),
					("iImage", INT),
					("fsState", BYTE),
					("fsStyle", BYTE),
					("cx", WORD),
					("lParam", DWORD),
					("pszText", LPSTR),	# addr ret buffer not required here
					("cchText", INT)]
	def __init__(self): self.cbSize=sizeof(self)
			
class TBADDBITMAP(Structure):
	_fields_ = [("hInst", HANDLE),
					("nID", UINT)]


class COLORSCHEME(Structure):
	_fields_ = [("dwSize", DWORD),
					("clrBtnHighlight", COLORREF),
					("clrBtnShadow", COLORREF)]

class NMMOUSE(Structure):
	_fields_ = [("hdr", NMHDR),
					("dwItemSpec", DWORD),
					("dwItemData", DWORD),
					("pt", POINT)]

class NMTBHOTITEM(Structure):
	_fields_ = [("hdr", NMHDR),
					("idOld", INT),
					("idNew", INT),
					("dwFlags", DWORD)]


TBSTATE_CHECKED        = 1
TBSTATE_PRESSED        = 2
TBSTATE_ENABLED        = 4
TBSTATE_HIDDEN         = 8
TBSTATE_INDETERMINATE  = 16
TBSTATE_WRAP           = 32
#TBSTATE_ELLIPSES       = 64	# ??
TBSTATE_MARKED         = 128


TBSTYLE_BUTTON         = 0
TBSTYLE_SEP            = 1
TBSTYLE_CHECK          = 2
TBSTYLE_GROUP          = 4
TBSTYLE_CHECKGROUP     = TBSTYLE_GROUP | TBSTYLE_CHECK
TBSTYLE_DROPDOWN       = 8
TBSTYLE_AUTOSIZE       = 16 # automatically calculate the cx of the button
TBSTYLE_NOPREFIX       = 32 # if this button should not have accel prefix


BTNS_BUTTON     = TBSTYLE_BUTTON      # 0
BTNS_SEP        = TBSTYLE_SEP         # 1
BTNS_CHECK      = TBSTYLE_CHECK       # 2
BTNS_GROUP      = TBSTYLE_GROUP       # 4
BTNS_CHECKGROUP = TBSTYLE_CHECKGROUP  # (TBSTYLE_GROUP OR TBSTYLE_CHECK)
BTNS_DROPDOWN   = TBSTYLE_DROPDOWN    # 8
BTNS_AUTOSIZE   = TBSTYLE_AUTOSIZE    # 16; automatically calculate the cx of the button
BTNS_NOPREFIX   = TBSTYLE_NOPREFIX    # 32; this button should not have accel prefix
BTNS_SHOWTEXT   = 64              # ignored unless TBSTYLE_EX_MIXEDBUTTONS is set
BTNS_WHOLEDROPDOWN  = 128          # draw drop-down arrow, but without split arrow section

TBIF_IMAGE   = 1
TBIF_TEXT    = 2
TBIF_STATE   = 4
TBIF_STYLE   = 8
TBIF_LPARAM  = 16
TBIF_COMMAND = 32
TBIF_SIZE    = 64
TBIF_ALL= 1|4|8|16|32|64	# felt free to define this (all except TBIF_TEXT)


TBI_NOTEXT = -1		# felt free to define this

#***********************************************
TBN_FIRST               = UINT_MAX-700  
NM_FIRST = UINT_MAX
WM_USER = 1024

CCM_FIRST              = 8192
CCM_SETCOLORSCHEME     = CCM_FIRST + 2
CCM_GETCOLORSCHEME     = CCM_FIRST + 3
CCM_SETWINDOWTHEME     = CCM_FIRST + 11


class Styles:
	CCS_TOP           = 1
	CCS_NOMOVEY       = 2
	CCS_BOTTOM        = 3
	CCS_NORESIZE      = 4
	CCS_NOPARENTALIGN = 8
	CCS_ADJUSTABLE    = 32
	CCS_NODIVIDER     = 64
	CCS_VERT          = 128
	CCS_LEFT          = CCS_VERT | CCS_TOP
	CCS_RIGHT         = CCS_VERT | CCS_BOTTOM
	CCS_NOMOVEX       = CCS_VERT | CCS_NOMOVEY

	
	
	CCS_NOPARENTALIGN = 8
	
	CCS_ADJUSTABLE    = 32
	CCS_NODIVIDER     = 64
	
	#TBSTYLE_TOOLTIPS        = 256
	TBSTYLE_WRAPABLE        = 512
	TBSTYLE_ALTDRAG         = 1024
	TBSTYLE_FLAT            = 2048
	TBSTYLE_LIST            = 4096
	TBSTYLE_CUSTOMERASE     = 8192
	TBSTYLE_REGISTERDROP    = 16384
	TBSTYLE_TRANSPARENT     = 32768
	
	TBSTYLE_EX_DRAWDDARROWS = 1
	TBSTYLE_EX_MIXEDBUTTONS       = 8
	TBSTYLE_EX_HIDECLIPPEDBUTTONS = 16 # don#t show partially obscured buttons

	TBSTYLE_EX_DOUBLEBUFFER       = 128 # Double Buffer the toolbar

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['CCS_', 'TBSTYLE_', 'TBSTYLE_EX_']

WM_USER = 1024

class Msgs:
	MSG_SETEXSTYLE= WM_USER + 84 # TB_SETEXTENDEDSTYLE
	MSG_GETEXSTYLE= WM_USER +85 # TB_GETEXTENDEDSTYLE
		
	
	TB_ENABLEBUTTON             = WM_USER + 1
	TB_CHECKBUTTON              = WM_USER + 2
	TB_PRESSBUTTON              = WM_USER + 3
	TB_HIDEBUTTON               = WM_USER + 4
	TB_INDETERMINATE            = WM_USER + 5
	TB_MARKBUTTON               = WM_USER + 6
	TB_ISBUTTONENABLED          = WM_USER + 9
	TB_ISBUTTONCHECKED          = WM_USER + 10
	TB_ISBUTTONPRESSED          = WM_USER + 11
	TB_ISBUTTONHIDDEN           = WM_USER + 12
	TB_ISBUTTONINDETERMINATE    = WM_USER + 13
	TB_ISBUTTONHIGHLIGHTED      = WM_USER + 14
	TB_SETSTATE                 = WM_USER + 17
	TB_GETSTATE                 = WM_USER + 18
	TB_ADDBITMAP                = WM_USER + 19
	TB_ADDBUTTONS       = WM_USER + 20
	TB_INSERTBUTTON     = WM_USER + 21
	TB_DELETEBUTTON     = WM_USER + 22
	TB_GETBUTTON        = WM_USER + 23
	TB_BUTTONCOUNT      = WM_USER + 24
	TB_COMMANDTOINDEX   = WM_USER + 25
	TB_SAVERESTORE           = WM_USER + 26
	#TB_SAVERESTOREW          = WM_USER + 76
	TB_CUSTOMIZE             = WM_USER + 27
	TB_ADDSTRING             = WM_USER + 28
	TB_ADDSTRINGW            = WM_USER + 77
	TB_GETITEMRECT           = WM_USER + 29
	TB_BUTTONSTRUCTSIZE      = WM_USER + 30
	TB_SETBUTTONSIZE         = WM_USER + 31
	TB_SETBITMAPSIZE         = WM_USER + 32
	TB_AUTOSIZE              = WM_USER + 33
	TB_GETTOOLTIPS           = WM_USER + 35
	TB_SETTOOLTIPS           = WM_USER + 36
	TB_SETPARENT             = WM_USER + 37
	TB_SETROWS               = WM_USER + 39
	TB_GETROWS               = WM_USER + 40
	TB_SETCMDID              = WM_USER + 42
	TB_CHANGEBITMAP          = WM_USER + 43
	TB_GETBITMAP             = WM_USER + 44
	TB_GETBUTTONTEXT         = WM_USER + 45
	TB_GETBUTTONTEXTW        = WM_USER + 75
	TB_REPLACEBITMAP         = WM_USER + 46
	TB_SETINDENT             = WM_USER + 47
	TB_SETIMAGELIST          = WM_USER + 48
	TB_GETIMAGELIST          = WM_USER + 49
	TB_LOADIMAGES            = WM_USER + 50
	TB_GETRECT               = WM_USER + 51  # wParam is the Cmd instead of index
	TB_SETHOTIMAGELIST       = WM_USER + 52
	TB_GETHOTIMAGELIST       = WM_USER + 53
	TB_SETDISABLEDIMAGELIST  = WM_USER + 54
	TB_GETDISABLEDIMAGELIST  = WM_USER + 55
	TB_SETSTYLE              = WM_USER + 56
	TB_GETSTYLE              = WM_USER + 57
	TB_GETBUTTONSIZE         = WM_USER + 58
	TB_SETBUTTONWIDTH        = WM_USER + 59
	TB_SETMAXTEXTROWS        = WM_USER + 60
	TB_GETTEXTROWS           = WM_USER + 61

	TB_GETOBJECT             = WM_USER + 62  # wParam == IID, lParam void **ppv
	TB_GETHOTITEM            = WM_USER + 71
	TB_SETHOTITEM            = WM_USER + 72  # wParam == iHotItem
	TB_SETANCHORHIGHLIGHT    = WM_USER + 73  # wParam == TRUE/FALSE
	TB_GETANCHORHIGHLIGHT    = WM_USER + 74
	TB_MAPACCELERATOR        = WM_USER + 78  # wParam == ch, lParam int * pidBtn
	TB_GETINSERTMARK        = WM_USER + 79  # lParam == LPTBINSERTMARK
	TB_SETINSERTMARK        = WM_USER + 80  # lParam == LPTBINSERTMARK
	TB_INSERTMARKHITTEST    = WM_USER + 81  # wParam == LPPOINT lParam == LPTBINSERTMARK
	TB_MOVEBUTTON           = WM_USER + 82
	TB_GETMAXSIZE           = WM_USER + 83  # lParam == LPSIZE
	TB_SETEXTENDEDSTYLE     = WM_USER + 84  # For TBSTYLE_EX_*
	TB_GETEXTENDEDSTYLE     = WM_USER + 85  # For TBSTYLE_EX_*
	TB_GETPADDING           = WM_USER + 86
	TB_SETPADDING           = WM_USER + 87
	TB_SETINSERTMARKCOLOR   = WM_USER + 88
	TB_GETINSERTMARKCOLOR   = WM_USER + 89

	TB_SETCOLORSCHEME       = CCM_SETCOLORSCHEME  # lParam is color scheme
	TB_GETCOLORSCHEME       = CCM_GETCOLORSCHEME  # fills in COLORSCHEME pointed to by lParam

	#TB_SETUNICODEFORMAT     = CCM_SETUNICODEFORMAT
	#TB_GETUNICODEFORMAT     = CCM_GETUNICODEFORMAT

	TB_MAPACCELERATORW      = WM_USER + 90  # wParam == ch, lParam int * pidBtn


	TB_GETBITMAPFLAGS       = WM_USER + 41
	TB_GETBUTTONINFO         = WM_USER + 65
	TB_SETBUTTONINFO         = WM_USER + 66

	TB_HITTEST              = WM_USER + 69

	TB_SETDRAWTEXTFLAGS     = WM_USER + 70  # wParam == mask lParam == bit values

	TB_GETSTRINGW           = WM_USER + 91
	TB_GETSTRING            = WM_USER + 92
	TB_GETMETRICS      = WM_USER + 101
	TB_SETMETRICS      = WM_USER + 102
	TB_SETWINDOWTHEME  = CCM_SETWINDOWTHEME

	
	
	NM_RCLICK          = NM_FIRST - 5
	NM_RDBLCLK         = NM_FIRST - 6
	NM_RELEASEDCAPTURE = NM_FIRST - 16
	



	TBN_GETBUTTONINFO  = TBN_FIRST - 0
	TBN_BEGINDRAG      = TBN_FIRST - 1
	TBN_ENDDRAG        = TBN_FIRST - 2
	TBN_BEGINADJUST    = TBN_FIRST - 3
	TBN_ENDADJUST      = TBN_FIRST - 4
	TBN_RESET          = TBN_FIRST - 5
	TBN_QUERYINSERT    = TBN_FIRST - 6
	TBN_QUERYDELETE    = TBN_FIRST - 7
	TBN_TOOLBARCHANGE  = TBN_FIRST - 8
	TBN_CUSTHELP       = TBN_FIRST - 9
	TBN_DROPDOWN       = TBN_FIRST - 10
	TBN_GETOBJECT      = TBN_FIRST - 12
	TBN_HOTITEMCHANGE   = TBN_FIRST - 13
	TBN_DRAGOUT         = TBN_FIRST - 14 # this is sent when the user clicks down on a button then drags off the button
	TBN_DELETINGBUTTON  = TBN_FIRST - 15 # uses TBNOTIFY
	TBN_GETDISPINFO     = TBN_FIRST - 16 # This is sent when the toolbar needs some display information
	
	TBN_GETDISPINFOW    = TBN_FIRST - 17 # This is sent when the toolbar needs some display information
	TBN_GETINFOTIP      = TBN_FIRST - 18
	TBN_GETINFOTIPW     = TBN_FIRST - 19
	TBN_GETBUTTONINFOW  = TBN_FIRST - 20
	TBN_RESTORE         = TBN_FIRST - 21
	TBN_SAVE            = TBN_FIRST - 22
	TBN_INITCUSTOMIZE   = TBN_FIRST - 23

Msgs.__dict__.update(control.control_msgs.__dict__)
