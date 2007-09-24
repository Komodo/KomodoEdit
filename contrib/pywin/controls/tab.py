

"""
LAST VISITED		24.03.05


NOT IMPLEMENTED
	
	TCM_SETITEMEXTRA
	TCM_SETTOOLTIPS
	TCM_SETUNICODEFORMAT
	TCM_GETTOOLTIPS
		
	TCN_GETOBJECT

	+ ownerdraw

"""



from wnd.wintypes import (InitCommonControlsEx,
													user32,
													byref,
													NMHDR,
													MAKELONG,
													LOWORD,
													HIWORD,
													RECT,
													POINT,
													Structure,
													c_int,
													c_uint,
													WORD,
													DWORD,
													LPARAM,
													addressof,
													sizeof,
													UINT_MAX,
													create_string_buffer,)

from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_TAB_CLASSES        = 8
InitCommonControlsEx(ICC_TAB_CLASSES)




class TabMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm = NMHDR.from_address(msgr.lParam)
					if nm.code == self.Msg.TCN_SELCHANGING:
						if self.onMSG(hwnd, "selchanging", self.GetSelected(), 0)==False:
							return 1
					elif nm.code == self.Msg.TCN_SELCHANGE:
						self.onMSG(hwnd, "selchanged", self.GetSelected(), 0)
					elif nm.code==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasedcapture", 0, 0)
					elif nm.code==self.Msg.NM_CLICK:
						self.onMSG(hwnd, "click", 0, 0)
					elif nm.code==self.Msg.NM_RCLICK:
						self.onMSG(hwnd, "rclick", 0, 0)
					elif nm.code==self.Msg.TCN_KEYDOWN:
						nmk= NMTCKEYDOWN.from_address(lp)
						self.onMSG(hwnd, "keydown", 0, (nmk.wVKey, nmk.flags))
					elif nm.code==self.Msg.TCN_FOCUSCHANGE:
						self.onMSG(hwnd, "focuschange", 0, 0)
			return 0
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#--------------------------------------------------------------------
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text + '\x00'
		return addressof(self._client_buffer)					
	#-------------------------------------------------------------------------
	# tab methods
		
	def __len__(self):
		return  self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEMCOUNT, 0, 0)
	
	def __iter__(self):
		for i in range(self.__len__()): yield i
	
	
	def FindLparam(self, lp):
		for i in self:
			if self.GetItemLparam(i)== lp:
				return i
			
	
	def Clear(self):
		"""Removes all items from the tab control."""
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_DELETEALLITEMS, 0, 0):
			raise RuntimeError("could not clear items")
		
	def Item(self, text, iImage=0, lp=0):
		return self.InsertItem(self.__len__(), text, iImage, lp)
	
	def InsertItem(self, i, text, iImage=0, lp=0):
		tci = TCITEM()
		tci.mask = tci.TCIF_TEXT|tci.TCIF_PARAM|tci.TCIF_IMAGE 
		tci.lParam= lp
		tci.iImage= iImage
		tci.pszText = self._client_TruncText(text)
		result = self.SendMessage(self.Hwnd, self.Msg.TCM_INSERTITEM, i, byref(tci))
		if result < 0: raise RuntimeError("could not add tab")
		return result
	
	def RemoveItem(self, i):
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_DELETEITEM, i, 0):
			raise RuntimeError("could not remove item")
			
	def SetItemText(self, i, text):
		tci = TCITEM()
		tci.mask = tci.TCIF_TEXT
		tci.pszText = self._client_TruncText(text)
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could set text")
		
	def GetItemText(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_TEXT
		tci.pszText = addressof(self._client_buffer)
		tci.cchTextMax = sizeof(self._client_buffer)
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEM, i, byref(tci)):
			raise RuntimeError("could not retrive text")
		return self._client_buffer.value
		
	def SetItemImage(self, i, iImage):
		tci = TCITEM()
		tci.mask = tci.TCIF_IMAGE
		tci.iImage = iImage
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could not set image")
		
	def GetItemImage(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_IMAGE
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEM, i, byref(tci)):
			raise RuntimeError("could not retrive image")
		return tci.iImage
		
	def SetItemLparam(self, i, lp):
		tci = TCITEM()
		tci.mask = tci.TCIF_PARAM 
		tci.lParam = lp
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could not set lparam")
		
	def GetItemLparam(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_PARAM 
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEM, i, byref(tci)):
			raise RuntimeError("could not retrive lparam")
		return tci.lParam

	def SetItemSize(self, w, h): 
		result=self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEMSIZE , 0, MAKELONG(w, h))
		return LOWORD(result), HIWORD(result)

	def GetItemRect(self, i):
		rc=RECT()
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEMRECT, i, byref(rc)):
			raise RuntimeError("could not retrieve item rect")
		return rc

	def GetFocusItem(self):
		# ?? no error here available (-1) or something
		return self.SendMessage(self.Hwnd, self.Msg.TCM_GETCURFOCUS, 0, 0)
		 
	def SetFocusItem(self, i):
		return self.SendMessage(self.Hwnd, self.Msg.TCM_SETCURFOCUS, i, 0)
	
	def SetMinItemWidth(self, w=-1):
		return self.SendMessage(self.Hwnd, self.Msg.TCM_SETMINTABWIDTH, 0, w)
		
	def SetItemPadding(self, w):
		self.SendMessage(self.Hwnd, self.Msg.TCM_SETPADDING , 0, w)
	
	def ItemHitTest(self, x, y):
		tht=TCHITTESTINFO()
		result=self.SendMessage(self.Hwnd, self.Msg.TCM_HITTEST , 0, byref(tht))
		if result <0: result= None
		if tht.flags & 1: flag='nowhere'
		elif tht.flags & 2 and tht.flags & 4: flag='onitem'
		elif tht.flags & 2:	flag='onicon'
		elif tht.flags & 4: flag='onlabel'
		return result, flag
	
	def Select(self, i): 
		result=self.SendMessage(self.Hwnd, self.Msg.TCM_SETCURSEL, i, 0) 
		if result <0: raise RuntimeError("could not select item") 
		return result

	def GetSelected(self):
		result = self.SendMessage(self.Hwnd, self.Msg.TCM_GETCURSEL, 0, 0)
		if result > -1:	return result
		
	def SetImagelist(self, ImageList):
		return  self.SendMessage(self.Hwnd, self.Msg.TCM_SETIMAGELIST , 0, ImageList.handle)
		
	def  GetImagelist(self):
		return  self.SendMessage(self.Hwnd, self.Msg.TCM_GETIMAGELIST, 0, 0)

	def GetRowCount(self):
		return self.SendMessage(self.Hwnd, self.Msg.TCM_GETROWCOUNT, 0, 0)

	def GetDisplayRect(self):
		rc=self.GetWindowRect()
		self.SendMessage(self.Hwnd, self.Msg.TCM_ADJUSTRECT, 0, byref(rc))
		return rc

	def AdjustDisplayRect(self, Rect):
		self.SendMessage(self.Hwnd, self.Msg.TCM_ADJUSTRECT, 1, byref(Rect))
		
	def ReleaseAllItems(self, keepfocus=False):
		if keepfocus: focus= 1
		else: keepfocus=0
		self.SendMessage(self.Hwnd, self.Msg.TCM_DESELECTALL, keepfocus, 0)
		
	def ReleaseItem(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 1		# TCIS_BUTTONPRESSED
		tci.dwState= 0
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could release item")
		
	def PushItem(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 1		# TCIS_BUTTONPRESSED
		tci.dwState= 1
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could push item")
	
	def IsPushed(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 1		# TCIS_BUTTONPRESSED
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEM, i, byref(tci)):
			raise RuntimeError("could retrieve item info")
		return bool(tci.dwState)
		
	def UnhilightItem(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 2		# TCIS_HIGHLIGHTED
		tci.dwState= 0
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could set text")
			
	def IsHilighted(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 2		# TCIS_HIGHLIGHTED
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_GETITEM, i, byref(tci)):
			raise RuntimeError("could retrieve item info")
		return bool(tci.dwState)
			
	def HilightItem(self, i):
		tci = TCITEM()
		tci.mask = tci.TCIF_STATE
		tci.dwStateMask= 2		# TCIS_HIGHLIGHTED
		tci.dwState= 2
		if not self.SendMessage(self.Hwnd, self.Msg.TCM_SETITEM, i, byref(tci)):
			raise RuntimeError("could set text")
			

#*******************************************************************************


class Tab(TabMethods, control.BaseControl, ControlMethods):

	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysTabControl32", '', x, y, w, h, *styles)	
		self._client_buffer = create_string_buffer(512)
		


class TabFromHandle(TabMethods, control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self._client_buffer = create_string_buffer(512)
		
		



#**************************************************************************
TCM_FIRST              = 4864
c_uint_MAX = (1l << 32)
TCN_FIRST               = c_uint_MAX-550
NM_FIRST= UINT_MAX
#**************************************************

class Styles:
	
	TCS_TABS                = 0
	TCS_RIGHTJUSTIFY        = 0
	TCS_SINGLELINE          = 0
	TCS_SCROLLOPPOSITE      = 1  # assumes multiline tab
	TCS_BOTTOM              = 2
	TCS_RIGHT               = 2
	TCS_MULTISELECT         = 4  # allow multi-select in button mode
	TCS_FLATBUTTONS         = 8
	TCS_FORCEICONLEFT       = 16
	TCS_FORCELABELLEFT      = 32
	TCS_HOTTRACK            = 64
	TCS_VERTICAL            = 128
	TCS_BUTTONS             = 256
	TCS_MULTILINE           = 512
	TCS_FIXEDWIDTH          = 1024
	TCS_RAGGEDRIGHT         = 2048
	TCS_FOCUSONBUTTONDOWN   = 4096
	TCS_OWNERDRAWFIXED      = 8192
	TCS_TOOLTIPS            = 16384
	TCS_FOCUSNEVER          = 32768

	TCS_EX_FLATSEPARATORS   = 1
	TCS_EX_REGISTERDROP     = 2
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['TCS_', 'TCS_EX_']


class Msgs: 
	
	MSG_SETEXSTYLE=  TCM_FIRST + 52	# TCM_SETEXTENDEDSTYLE
	MSG_GETEXSTYLE= TCM_FIRST +53 # TCM_GETEXTENDEDSTYLE
		
	TCM_GETIMAGELIST        = TCM_FIRST + 2
	TCM_SETIMAGELIST        = TCM_FIRST + 3
	TCM_GETITEMCOUNT        = TCM_FIRST + 4

	TCM_GETITEM             = TCM_FIRST + 5
	TCM_GETITEMW            = TCM_FIRST + 60
	TCM_SETITEM            = TCM_FIRST + 6
	TCM_SETITEMW           = TCM_FIRST + 61
	TCM_INSERTITEM         = TCM_FIRST + 7
	TCM_INSERTITEMW        = TCM_FIRST + 62
	TCM_DELETEITEM         = TCM_FIRST + 8
	TCM_DELETEALLITEMS      = TCM_FIRST + 9
	TCM_GETITEMRECT         = TCM_FIRST + 10
	TCM_GETCURSEL           = TCM_FIRST + 11
	TCM_SETCURSEL           = TCM_FIRST + 12

	TCM_HITTEST             = TCM_FIRST + 13
	TCM_SETITEMEXTRA        = TCM_FIRST + 14
	TCM_ADJUSTRECT          = TCM_FIRST + 40
	TCM_SETITEMSIZE         = TCM_FIRST + 41
	TCM_REMOVEIMAGE         = TCM_FIRST + 42
	TCM_SETPADDING          = TCM_FIRST + 43
	TCM_GETROWCOUNT         = TCM_FIRST + 44
	TCM_GETTOOLTIPS         = TCM_FIRST + 45
	TCM_SETTOOLTIPS         = TCM_FIRST + 46
	TCM_GETCURFOCUS         = TCM_FIRST + 47
	TCM_SETCURFOCUS         = TCM_FIRST + 48
	TCM_SETMINTABWIDTH      = TCM_FIRST + 49
	TCM_DESELECTALL         = TCM_FIRST + 50
	TCM_HIGHLIGHTITEM       = TCM_FIRST + 51
	
	TCN_KEYDOWN             = TCN_FIRST - 0
	TCN_SELCHANGE   = TCN_FIRST - 1
	TCN_SELCHANGING = TCN_FIRST - 2
	TCN_GETOBJECT   = TCN_FIRST - 3
	TCN_FOCUSCHANGE = TCN_FIRST - 4

	NM_RELEASEDCAPTURE = NM_FIRST - 16
	NM_CLICK           = NM_FIRST - 2  # uses NMCLICK type
	NM_RCLICK          = NM_FIRST - 5  # uses NMCLICK type

Msgs.__dict__.update(control.control_msgs.__dict__)


#*************************************************

class TCITEM(Structure):
	TCIF_TEXT               = 1
	TCIF_IMAGE              = 2
	TCIF_RTLREADING         = 4
	TCIF_PARAM              = 8
	TCIF_STATE              = 16
	_fields_=[("mask", c_uint),
					("dwState",DWORD),	# if IE > 300
					("dwStateMask", DWORD),
					("pszText", DWORD),	# address of buffer
					("cchTextMax", c_int),
					("iImage", c_int),
					("lParam", LPARAM)]
	
class TCHITTESTINFO(Structure):
	_fields_ = [("pt", POINT),
					("flags", c_uint)]

class NMTCKEYDOWN(Structure):
	_fields_ = [("hdr", NMHDR),
					("wVKey", WORD),
					("flags", c_uint)]