"""Wintypes and some othe commonly used stuff"""


import traceback
from ctypes.wintypes import *
from ctypes import *

user32 = windll.user32
gdi32 = windll.gdi32
comctl32 = windll.comctl32
kernel32 = windll.kernel32
shell32 = windll.shell32
comdlg32=windll.comdlg32

#*************************************************************************************

DLGCODES={'wantarrows':1,
						'wanttabs':2,
						'wantallkeys':4,
						'hassetsel':8, 
						'defpushbutton':16, 
						'undefpushbutton':32, 
						'radiobutton':64,
						'wantchars':128,
						'static':256,
						'button':8192}

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
UINT_MAX  =  1 << 32
INT_MIN   =  -2147483647 - 1 
INT_MAX  =     2147483647

NM_FIRST = 0


BYTE = c_ubyte

CHAR = c_char
COLORREF = c_ulong
CLIPFORMAT = c_ushort

HBRUSH = HANDLE
HBITMAP = HANDLE
HCURSOR = HANDLE
HICON = HANDLE
HIMAGELIST = HANDLE
HMODULE = HANDLE
HMONITOR = HANDLE

INT = c_int

LPTSTR = c_char_p
LPCTSTR = c_char_p
LPVOID = c_void_p

SHORT = c_short
TCHAR = c_char

UINT = c_uint
ULONG = DWORD

WCHAR = c_wchar


def LOWORD(dword): return dword & 0x0000ffff
def HIWORD(dword): return dword >> 16
def LOBYTE(dword): return dword & 0x000000ff
def HIBYTE(dword): return dword >> 8				
def MAKEWORD(byte1, byte2): return byte1 | (byte2 << 8)
def MAKELONG(word1, word2): return word1 | (word2 << 16)
def RGB(r, g, b): return r | (g<<8) | (b<<16)
def GETRGB(colorref): return colorref & 255,colorref >> 8 & 255,colorref >> 16 & 255


WNDPROC = WINFUNCTYPE(c_int, HANDLE, c_uint, WPARAM, LPARAM)
DIALOGPROC = WINFUNCTYPE(BOOL, HWND, c_uint, WPARAM, LPARAM)
#PROPENUMPROC = WINFUNCTYPE(BOOL, HWND, LPCTSTR, HANDLE)

class NMHDR(Structure):
	_fields_=[("hwndFrom", HWND),
						("idFrom", UINT),
						("code", UINT)]



#******************************************************************************
class RECT(RECT):
		
	def byref(self): return byref(self)	
	
	def OffsetSize(self, offsetW, offsetH):
		self.right += offsetW 
		self.bottom += offsetH
		if self.right < 0:	self.right = 0
		if self.bottom < 0:	self.bottom = 0

	def Offset(self, offsetX, offsetY):
		if not user32.OffsetRect(byref(self), offsetX, offsetY):
			raise "could not offset rect"

	def Inflate(self, offsW, offsH):
		if not user32.InflateRect(byref(self), offsW, offsH):
			raise "could not inflate rect"

	def Intersect(self, Rect):
		rc = self.__class__()
		user32.IntersectRect(byref(rc), byref(self), byref(Rect))
		return rc

	def Union(self, Rect):
		rc = self.__class__()
		if not user32.UnionRect(byref(rc), byref(self), byref(Rect)):
			raise "could not union rect"
		return rc
			
	def Subtract(self, Rect):
		rc = self.__class__()
		if not user32.SubtractRect(byref(rc), byref(self), byref(Rect)):
			pass
			#raise "could not substract rect"
		return rc

	def Copy(self):
		return self.__class__(self.left, self.top, self.right, self.bottom)
			
	def IsEqual(self, Rect):
		if user32.EqualRect(byref(self), byref(Rect)): return True
		return False

	def IsEmpty(self):
		if user32.IsRectEmpty(byref(self)): return True
		return False

	def ToTuple(self): return self.left, self.top, self.right, self.bottom
	
	def ToSize(self): return self.left, self.top, self.right-self.left, self.bottom-self.top
	
	def ScreenToClient(self, hwnd):
		pt1 = POINT(self.left, self.top)
		pt2 = POINT(self.right, self.bottom)
		pt1.ScreenToClient(hwnd)
		pt2.ScreenToClient(hwnd)
		self.left, self.top, self.right, self.bottom = pt1.x, pt1.y, pt2.x, pt2.y
						
	def ClientToScreen(self, hwnd):
		pt1 = POINT(self.left, self.top)
		pt2 = POINT(self.right, self.bottom)
		pt1.ClientToScreen(hwnd)
		pt2.ClientToScreen(hwnd)
		self.left, self.top, self.right, self.bottom = pt1.x, pt1.y, pt2.x, pt2.y
				

	def InRect(self, Rect):
		if self.left >= Rect.left:
			if self.right <= Rect.right:
				if self.top >= Rect.top:
					if self.bottom <= Rect.bottom: 
						return True
		return False
			

#************************************************
class POINT(POINT):
	def byref(self): return byref(self)
	def ToTuple(self): return self.x, self.y
	def InRect(self, Rect):
		if user32.PtInRect(byref(Rect), self.x, self.y): return True
		return False
	def ClientToScreen(self, hwnd):
		if not user32.ClientToScreen(hwnd, byref(self)):
			raise "could not convert coordinates"
	def ScreenToClient(self, hwnd):
		if not user32.ScreenToClient(hwnd, byref(self)):
			raise "could not convert coordinates"


#*************************************************************************************

class COPYDATASTRUCT(Structure):
	_fields_ = [("dwData", c_ulong),
						("cbData", c_ulong),
						("lpData", c_void_p)]

class MEASUREITEMSTRUCT(Structure):
	_fields_ = [("CtlType", UINT),
					("CtlID", UINT),
					("itemID", UINT),
					("itemWidth", UINT),
					("itemHeight", UINT),
					("itemData", DWORD)]

class DRAWITEMSTRUCT(Structure):
	DRAWENTIRE = 1
	SELECTCHANGE     = 2
	FOCUSCHANGE      = 4
	
	SELECTED     = 1
	GRAYED       = 2
	DISABLED     = 4
	CHECKED      = 8
	FOCUS        = 16
	DEFAULT      = 32
	COMBOBOXEDIT = 4096
	HOTLIGHT     = 64
	INACTIVE     = 128
	NOACCEL      = 256
	NOFOCUSRECT  = 512
	
	_fields_ = [("CtlType", UINT),
					("CtlID", UINT),
					("itemID", UINT),
					("itemAction", UINT),
					("itemState", UINT),
					("hwndItem", HWND),
					("hDC", HDC),
					("rcItem", RECT),
					("itemData", DWORD)]

class WINDOWPOS(Structure):
	_fields_ = [("hwnd", HWND), 
					("hwndInsertAfter", HWND),
					("x", INT), 
					("y", INT), 
					("cx", INT), 
					("cy", INT), 
					("flags", UINT)]

class MINMAXINFO(Structure):
	_fields_ = [("ptReserved", POINT),
					("ptMaxSize", POINT),
					("ptMaxPosition", POINT),
					("ptMinTrackSize", POINT),
					("ptMaxTrackSize", POINT)]

class PAINTSTRUCT(Structure):
	_fields_ = [("hdc", HANDLE),
					("fErase", BOOL),
					("rcPaint", RECT),
					("fRestore", BOOL),
					("fIncUpdate", BOOL),
					("rgbReserved", BYTE*32)]

class SYSTEMTIME(Structure):
	_fields_ = [("wYear", WORD),
					("wMonth", WORD),
					("wDayOfWeek", WORD),
					("wDay", WORD),
					("wHour", WORD),
					("wMinute", WORD),
					("wSecond", WORD),
					("wMilliseconds", WORD)]

class SHFILEINFO(Structure):
	_fields_ = [("hIcon", HICON),
					("iIcon", INT),
					("dwAttributes", DWORD),
					("szDisplayName", CHAR*260),
					("szTypeName", CHAR*80)]


class FLASHWINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("hwnd", HWND),
					("dwFlags", DWORD),
					("uCount", UINT),
					("dwTimeout", DWORD)]
	def __init__(self): self.cbSize=sizeof(self)


##
def InitCommonControlsEx(ICC_CLASSES):
	"""Init common control classes."""
	if not comctl32.InitCommonControlsEx(
			byref((c_ulong*2)(8, ICC_CLASSES))):
		raise "could not init common control class"	

#******************************************************
class DLLVERSIONINFO(Structure):
	DLLVER_PLATFORM_WINDOWS  =  1      # Windows 95
	DLLVER_PLATFORM_NT = 2 
	_fields_ = [("cbSize", DWORD),
					("dwMajorVersion", DWORD),
					("dwMinorVersion", DWORD),
					("dwBuildNumber", DWORD),
					("dwPlatformID", DWORD)]



## 
def DllGetVersion(dll):
	"""Shell32.dll, Comctl32.dll, Shdocvw.dll, and Shlwapi.dll
	and some more provide this info."""
	DLLGETVERSIONPROC = WINFUNCTYPE(c_ulong, POINTER(DLLVERSIONINFO))
	GetProcAddress=kernel32.GetProcAddress
	GetProcAddress.restype=DLLGETVERSIONPROC
	DllGetVersion=kernel32.GetProcAddress(dll._handle, 'DllGetVersion')
	if not DllGetVersion: raise "no version info available"
	dvi = DLLVERSIONINFO()
	dvi.cbSize = sizeof(DLLVERSIONINFO)
	if DllGetVersion(byref(dvi)): raise "could not  retrieve version info"
	return dvi


# ...and the test if it works
result = DllGetVersion(comctl32)
VER_COMCTL = result.dwMajorVersion, result.dwMinorVersion
if VER_COMCTL < (4, 71):
	from wnd.api.msgbox import Msg
	msg= '''Sorry
				At least comctl32.dll ver 4.71 is required
				Found ver %s.%s on your system'''.replace('\t', '')
	Msg(0, msg % VER_COMCTL, 'wnd-module', 'ok', 'systemmodal')

#OS_NAME = winos.Name()
