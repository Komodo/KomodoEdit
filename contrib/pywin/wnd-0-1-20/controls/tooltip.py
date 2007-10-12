
"""


NOT IMPLEMENTED

	 TTM_HITTEST
	 TTM_RELAYEVENT 
	 TTM_SETTOOLINFO
	 TTM_WINDOWFROMPOINT


TODO

	# could not tackle this to set lParams at runtime
	# TTM_SETTOOLINFO does something unexpected here (sets the text to '' 
	# ...and calling TTM_UPDATETIPTEXT the text never gets updated) 
	# so currently one can retrieve lParams, but not set them
	def _client_SetToolInfo(self, Control=None, ID=None, lp=0):
		ti = TOOLINFO()
		if Control==None and ID==None: raise "no tool specified"
		if Control !=None: ti.hwnd = Control.Hwnd
		if ID==None: ti.uId  = Control.Hwnd
		else: ti.uId  = ID
		ti.lpszText= addressof(self._client_buffer)
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTEXT, 0, byref(ti))
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTOOLINFO, 0, byref(ti))
		ti.lParam= lp
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTOOLINFO, 0, byref(ti))
		#ti.lpszText= addressof(self._client_buffer)
		self.SendMessage(self.Hwnd, self.Msg.TTM_UPDATETIPTEXT, 0, byref(ti))


# see above TTM_SETTOOLINFO does not work as expected
def TipCenter(self, Control,  fCenter=True):
	ti = TOOLINFO()
	ti.hwnd = Control.Hwnd
	ti.uId  = Control.Hwnd
	if not self.SendMessage(self.Hwnd,
					self.Msg.TTM_GETTOOLINFO, 0, byref(ti)):
		raise "no tooltip found"
		
	if fCenter:
		if ti.uFlags & TTF_CENTERTIP: return False
	else:
		if not ti.uFlags & TTF_CENTERTIP: return False
	ti.uFlags ^= TTF_CENTERTIP
	self.SendMessage(self.Hwnd,
					self.Msg.TTM_SETTOOLINFO, 0, byref(ti))
			
"""

from wnd.wintypes import (user32,
													sizeof, 
													byref,
													Structure,
													addressof,
													UINT,
													HWND,
													RECT,
													HANDLE,
													LPTSTR,
													LPARAM,
													NMHDR,
													c_char,
													DWORD,
													MAKELONG,
													UINT_MAX,
													create_string_buffer,
													InitCommonControlsEx,	)
from wnd import fwtypes as fw
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#*************************************************
ICC_TREEVIEW_CLASSES=2
InitCommonControlsEx(ICC_TREEVIEW_CLASSES)

#*************************************************
#
# TODO
#
# we do not have to trunc text in _client_TruncText
# INFOTIPSIZE is used by other commoncontrols when displaying infotips
#

#*************************************************
class TooltipMethods:
	
	def __init__(self, tabwidth=6):
		self._client_tabwidth=tabwidth
		# buffer is required here, cos there is no way to determine the length of
		# a tooltips text
		self._client_buffer= create_string_buffer(1025)
		
	
	
	#----------------------------------------------------------------
	# message handler

	def onMESSAGE(self, hwnd, msg, wp, lp):
				
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				nm=NMHDR.from_address(msgr.lParam)
				if nm.code==self.Msg.TTN_POP:
					self.onMSG(self.Hwnd, "pop", msgr.hwndFrom, nm.idFrom)
				elif nm.code==self.Msg.TTN_SHOW:
					self.onMSG(self.Hwnd, "show", msgr.hwndFrom, nm.idFrom)
				
				elif nm.code==self.Msg.TTN_GETDISPINFO or nm.code==self.Msg.TTN_GETDISPINFOW:
					nmd=NMTTDISPINFO.from_address(msgr.lParam)
					result=self.onMSG(self.Hwnd, "getdispinfo", msgr.hwndFrom, nm.idFrom)
					if type(result)==type(''): 
						nmd.lpszText = self._client_TruncText(result)
				elif nm.code == self.Msg.NM_CUSTOMDRAW:
					cd =  NMTTCUSTOMDRAW.from_address(msgr.lParam)
					result= self.onMSG(self.Hwnd, "customdraw", 
											(msgr.hwndFrom, cd.hdr.idFrom),
											cd)
					if result==None: return 0		# CDRF_DODEFAULT
					return result
			return 0		
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#------------------------------------------------------------------
	# methods
	
	def SetTextMax(self, n):
		self._client_buffer = create_string_buffer(n+1)
	
	def GetTextMax(self):
		return sizeof(self._client_buffer) -1
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		text= text.replace('\t', " "*self._client_tabwidth)
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text + '\x00'
		return addressof(self._client_buffer)			
	
		
	
	def SetTabWidth(self, n):
		self._client_tabwidth=n
	
	def Redraw(self):
		self.SendMessage(self.Hwnd, self.Msg.TTM_UPDATE, 0, 0) 
	
	def Activate(self):
		self.SendMessage(self.Hwnd, self.Msg.TTM_ACTIVATE, 1, 0)
		
	def Deactivate(self):
		self.SendMessage(self.Hwnd, self.Msg.TTM_ACTIVATE, 0, 0)
	
	def SetBkColor(self, colorref):
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTIPBKCOLOR, colorref, 0)

	def SetTextColor(self, colorref):
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTIPTEXTCOLOR, colorref, 0)

	def SetTitle(self, title):
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTITLE, 0, self._client_TruncText(title))
	
	def GetMargins(self,):
		rc=RECT()
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETMARGIN, 0, byref(rc))
		return rc.left, rc.top, rc.right, rc.bottom

	def SetMargins(self, left=0, top=0, right=0, bottom=0):	
		rc= RECT(left, top, right, bottom)
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETMARGIN, 0, byref(rc))
	
	def __iter__(self):
		ti = TOOLINFO()	
		i = 0
		while True:
			result = self.SendMessage(self.Hwnd, self.Msg.TTM_ENUMTOOLS, i, byref(ti))
			if not result: break
			i += 1
			yield ti.hwnd, ti.uId
	
	def __len__(self):
		return self.SendMessage(self.Hwnd,
					self.Msg.TTM_GETTOOLCOUNT, 0, 0)
	
	def GetInitDelay(self):
		TTDT_INITIAL      = 3
		return self.SendMessage(self.Hwnd,
					self.Msg.TTM_GETDELAYTIME, TTDT_INITIAL, 0)
	
	def SetInitDelay(self, n):
		TTDT_INITIAL      = 3
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETDELAYTIME,
		TTDT_INITIAL, n)
	
	def GetPopupDelay(self):
		TTDT_AUTOPOP      = 2
		return self.SendMessage(self.Hwnd,
					self.Msg.TTM_GETDELAYTIME, TTDT_AUTOPOP, 0)
		
	def SetPopupDelay(self, n):
		TTDT_AUTOPOP      = 2
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETDELAYTIME,
		TTDT_AUTOPOP, n)
	
	def GetReshowDelay(self):
		TTDT_RESHOW       = 1
		return self.SendMessage(self.Hwnd,
					self.Msg.TTM_GETDELAYTIME, TTDT_RESHOW, 0)
		
	def SetReshowDelay(self, n):
		TTDT_RESHOW       = 1
		self.SendMessage(self.Hwnd, self.Msg.TTM_SETDELAYTIME,
		TTDT_RESHOW, n)
	
	def GetMaxTipWidth(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.TTM_GETMAXTIPWIDTH, 0, 0)
		if result >-1: return result
	
	def SetMaxTipWidth(self, n):	
		result= self.SendMessage(self.Hwnd,
				self.Msg.TTM_SETMAXTIPWIDTH, 0, n)
		if result >-1: return result

	def HasCurrentTip(self):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TTM_GETCURRENTTOOL, 0, 0))
			
	def GetCurrentTip(self):
		ti = TOOLINFO()
		if self.SendMessage(self.Hwnd, self.Msg.TTM_GETCURRENTTOOL, 0, byref(ti)):
			return ti.hwnd, ti.uId

	def Clear(self):
		ti = TOOLINFO()
		for i in self:
			ti.hwnd, ti.uId = i
			self.SendMessage(self.Hwnd, self.Msg.TTM_DELTOOL, 0, byref(ti))
	
	#---------------------------------------------------------------------
	# tooltip-methods

	def SetToolTip(self, Control, text, lp=0, center=False):
		ti = TOOLINFO()
		ti.uFlags = TTF_IDISHWND | TTF_SUBCLASS
		if center:
			ti.uFlags |= TTF_CENTERTIP
		ti.hwnd = Control.Hwnd
		ti.uId  = Control.Hwnd
		if text == -1: ti.lpszText = text
		else: ti.lpszText = self._client_TruncText(text)
		ti.lParam= lp
		if not self.SendMessage(self.Hwnd, 
					self.Msg.TTM_ADDTOOL, 0, byref(ti)):
			raise RuntimeError("could not set tooltip")
	
	def SetToolTipText(self, Control, text):
		ti = TOOLINFO()
		ti.uFlags = TTF_IDISHWND | TTF_SUBCLASS
		ti.hwnd = Control.Hwnd
		ti.uId  = Control.Hwnd
		ti.lpszText = self._client_TruncText(text)
		self.SendMessage(self.Hwnd,
						self.Msg.TTM_UPDATETIPTEXT, 0, byref(ti))
	
	def GetToolTipText(self, Control):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = Control.Hwnd
		ti.lpszText= addressof(self._client_buffer)
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTEXT, 0, byref(ti))
		return self._client_buffer.value
	
#	def SetToolTipLparam(self, Control, lp):
#		ti = TOOLINFO()
#		ti.hwnd = Control.Hwnd
#		ti.uId  =  Control.Hwnd
#		ti.lParam= lp
#		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTOOLINFO, 0, byref(ti))

	def GetToolTipLparam(self, Control):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  =  Control.Hwnd
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTOOLINFO, 0, byref(ti))
		return ti.lParam
	
	def RemoveToolTip(self, Control):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = Control.Hwnd
		self.SendMessage(self.Hwnd, self.Msg.TTM_DELTOOL, 0, byref(ti))
	
	
	#---------------------------------------------------------------------
	# areatip-methods
	
	def SetAreaTip(self, Control, ID, text, Rect, lp=0):
		ti = TOOLINFO()
		ti.uFlags = TTF_SUBCLASS 
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		if text == -1: ti.lpszText = text
		else: ti.lpszText = self._client_TruncText(text)
		ti.rect= Rect
		ti.lParam= lp
		if not self.SendMessage(self.Hwnd, self.Msg.TTM_ADDTOOL, 0, byref(ti)):
			raise RuntimeError("could not set areatip")
	
	def SetAreaTipText(self, Control, ID, text):
		ti = TOOLINFO()
		ti.uFlags = TTF_SUBCLASS
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		ti.lpszText = self._client_TruncText(text)
		self.SendMessage(self.Hwnd,
						self.Msg.TTM_UPDATETIPTEXT, 0, byref(ti))
		
	def SetAreaTipPos(self, Control, ID, Rect):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		ti.rect=Rect
		self.SendMessage(self.Hwnd, self.Msg.TTM_NEWTOOLRECT, 0, byref(ti))
	
	def GetAreaTipPos(self, Control, ID):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTOOLINFO, 0, byref(ti))
		return ti.rect

	def GetAreaTipText(self, Control, ID):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		ti.lpszText= addressof(self._client_buffer)
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTEXT, 0, byref(ti))
		return self._client_buffer.value
	
#	def SetAreaTipLparam(self, Control, ID, lp):
#		ti = TOOLINFO()
#		ti.hwnd = Control.Hwnd
#		ti.uId  =  ID
#		ti.lParam= lp
#		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTOOLINFO, 0, byref(ti))
#		return ti.lParam

	def GetAreaTipLparam(self, Control, ID):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  =  ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTOOLINFO, 0, byref(ti))
		return ti.lParam
	
	def RemoveAreaTip(self, Control, ID):
		ti = TOOLINFO()
		ti.hwnd = Control.Hwnd
		ti.uId  = ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_DELTOOL, 0, byref(ti))
		
	#---------------------------------------------------------------------
	# areatip-methods
	
	def SetTrackTip(self, ID, text, lp=0):
		ti = TOOLINFO()
		ti.uFlags = TTF_TRACK | TTF_ABSOLUTE
		ti.uId  = ID
		if text == -1: ti.lpszText = text
		else: ti.lpszText = self._client_TruncText(text)
		ti.lParam= lp
		if not self.SendMessage(self.Hwnd, self.Msg.TTM_ADDTOOL, 0, byref(ti)):
			raise RuntimeError("could not set tracktip")
		
	def ShowTrackTip(self, ID):
		ti = TOOLINFO()
		ti.uId  = ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_TRACKACTIVATE, 1, byref(ti))
		
   	def HideTrackTip(self, ID):
		ti = TOOLINFO()
		ti.uId  = ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_TRACKACTIVATE, 0, byref(ti))
		
	def SetTrackTipPos(self, x, y):
		self.SendMessage(self.Hwnd, self.Msg.TTM_TRACKPOSITION, 0, MAKELONG(x, y))
		
	def SetTrackTipText(self, ID, text):
		ti = TOOLINFO()
		ti.uFlags = TTF_TRACK
		ti.uId  = ID
		ti.lpszText = self._client_TruncText(text)
		self.SendMessage(self.Hwnd, self.Msg.TTM_UPDATETIPTEXT, 0, byref(ti))

	def GetTrackTipText(self, ID):
		ti = TOOLINFO()
		ti.uId  = ID
		ti.lpszText= addressof(self._client_buffer)
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTEXT, 0, byref(ti))
		return self._client_buffer.value
	
#	def SetTrackTipLparam(self, ID, lp):
#		ti = TOOLINFO()
#		ti.uId  =  ID
#		ti.lParam= lp
#		self.SendMessage(self.Hwnd, self.Msg.TTM_SETTOOLINFO, 0, byref(ti))
#		return ti.lParam

	def GetTrackTipLparam(self, ID):
		ti = TOOLINFO()
		ti.uId  =  ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_GETTOOLINFO, 0, byref(ti))
		return ti.lParam
		
	def RemoveTrackTip(self, ID):
		ti = TOOLINFO()
		ti.uId  = ID
		self.SendMessage(self.Hwnd, self.Msg.TTM_DELTOOL, 0, byref(ti))

	


#******************************************************************

class Tooltip(TooltipMethods, control.ControlFromHandle, ControlMethods):
			
	def __init__(self, parent, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		# We have to create the control from scratch here
		# and use control.ControlFromHandle cos tooltips must be 
		# created without ID and without WS_CHILD|WS_VISIBLE style
		hwnd = user32.CreateWindowExA(
							0, "tooltips_class32", 0,
							0, 0, 0, 0, 0, parent.Hwnd, 0,
							0, 0)
		if not hwnd:
			raise RuntimeError("could not create tooltip control")

		
		flags= ['subclass',]
		if 'debug' in styles: flags.append('debug')
		if 'debugall' in styles: flags.append('debugall')
		control.ControlFromHandle.__init__(self, hwnd, *flags)
		TooltipMethods.__init__(self)
		self.SetStyle(*styles)
		
		

class TooltipFromHandle(TooltipMethods, control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		TooltipMethods.__init__(self)
		

#*************************************************
NM_FIRST = UINT_MAX
TTN_FIRST               = UINT_MAX-520 
WM_USER = 1024
#***********************************************
#4294966766
#4294966776L




class Styles:
	
	TTS_ALWAYSTIP = 1
	TTS_NOPREFIX  = 2
	TTS_NOANIMATE = 16
	TTS_NOFADE    = 32
	TTS_BALLOON   = 64
	TTS_CLOSE     = 128
	
	WS_CLIENT_CUSTOMDRAW = 1
		
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += 'TTS_', 
	

class Msgs:
	
	NM_CUSTOMDRAW      = NM_FIRST - 12
	

	# Tool Tip Messages
	TTM_ACTIVATE      = WM_USER +  1				#
	TTM_SETDELAYTIME  = WM_USER +  3			#
	TTM_ADDTOOL       = WM_USER +  4				#
	TTM_DELTOOL       = WM_USER +  5				#
	TTM_NEWTOOLRECT   = WM_USER +  6
	TTM_RELAYEVENT    = WM_USER +  7

	TTM_GETTOOLINFO   = WM_USER +  8
	TTM_SETTOOLINFO   = WM_USER +  9
	
	TTM_HITTEST         = WM_USER + 10
	TTM_GETTEXT         = WM_USER + 11			#
	TTM_UPDATETIPTEXT   = WM_USER + 12		#
	TTM_GETTOOLCOUNT    = WM_USER + 13
	TTM_ENUMTOOLS       = WM_USER + 14			#
	TTM_GETCURRENTTOOL  = WM_USER + 15
	TTM_WINDOWFROMPOINT = WM_USER + 16
	TTM_TRACKACTIVATE   = WM_USER + 17			#
	TTM_TRACKPOSITION   = WM_USER + 18			#
	TTM_SETTIPBKCOLOR   = WM_USER + 19			#
	TTM_SETTIPTEXTCOLOR = WM_USER + 20		#
	TTM_GETDELAYTIME    = WM_USER + 21			#
	TTM_GETTIPBKCOLOR   = WM_USER + 22
	TTM_GETTIPTEXTCOLOR = WM_USER + 23
	TTM_SETMAXTIPWIDTH  = WM_USER + 24
	TTM_GETMAXTIPWIDTH  = WM_USER + 25
	TTM_SETMARGIN       = WM_USER + 26
	TTM_GETMARGIN       = WM_USER + 27
	TTM_POP             = WM_USER + 28
	TTM_UPDATE          = WM_USER + 29				#
	TTM_GETBUBBLESIZE   = WM_USER + 30
	TTM_ADJUSTRECT      = WM_USER + 31
	TTM_SETTITLE        = WM_USER + 32  # wParam = TTI_*, lParam = char* szTitle				########
	TTM_POPUP           = WM_USER + 34
	TTM_GETTITLE        = WM_USER + 35  # wParam = 0, lParam = TTGETTITLE*

	TTM_SETWINDOWTHEME = 8203

	TTN_GETDISPINFO     = TTN_FIRST
	TTN_SHOW            = TTN_FIRST - 1
	TTN_POP             = TTN_FIRST - 2
	TTN_LINKCLICK       = TTN_FIRST - 3

	TTN_GETDISPINFOW    = TTN_FIRST - 10

	
	TTN_NEEDTEXT        = TTN_GETDISPINFO
	TTN_NEEDTEXTW       = TTN_GETDISPINFOW

Msgs.__dict__.update(control.control_msgs.__dict__)


	
		

#*************************************************
#TYPE NMTOOLTIPSCREATED
#	hdr          AS NMHDR
# hwndToolTips AS DWORD
#END TYPE





INFOTIPSIZE = 1024

TTF_IDISHWND      = 1			#
TTF_CENTERTIP     = 2			#
TTF_RTLREADING    = 4			#
TTF_SUBCLASS      = 16			#
TTF_TRACK         = 32			#
TTF_ABSOLUTE      = 128
TTF_TRANSPARENT   = 256
TTF_DI_SETITEM    = 32768  # valid only on the TTN_NEEDTEXT callback

TTDT_AUTOMATIC    = 0


TTI_NONE          = 0
TTI_INFO          = 1
TTI_WARNING       = 2
TTI_ERROR         = 3



class TOOLINFO(Structure):
	TTF_IDISHWND      = 1
	TTF_CENTERTIP     = 2
	TTF_RTLREADING    = 4
	TTF_SUBCLASS      = 16
	TTF_TRACK         = 32
	TTF_ABSOLUTE      = 128
	TTF_TRANSPARENT   = 256
	TTF_DI_SETITEM    = 32768  # valid only on the TTN_NEEDTEXT callback
	
	_fields_ = 	[("cbSize", UINT),
					("uFlags", UINT),
					("hwnd", HWND),
					("uId", UINT), 
					("rect", RECT),
					("hinst", HANDLE),
					("lpszText", DWORD),	# addressof ret buffer
					("lParam", LPARAM)]
	def __init__(self):
		self.cbSize = sizeof(self)
		

class NMTTDISPINFO(Structure):
	_fields_ = [("hdr", NMHDR),
					("lpszText", LPTSTR),
					("szText", c_char*80),
					("hinst", HANDLE),
					("uFlags", UINT),
					("lParam", LPARAM)]

class NMTTCUSTOMDRAW(Structure):
	
	# could not get more to work
	
	# CDDS_*
	PREPAINT           = 1
	POSTPAINT          = 2
	#PREERASE           = 3
	#POSTERASE          = 4
	# CDDS_*
	

	# customdraw return flags
	# CDRF_*
	#DODEFAULT          = 0
	#NEWFONT            = 2
	#SKIPDEFAULT        = 4
	NOTIFYPOSTPAINT    = 16
	#NOTIFYITEMDRAW	= 32
	#NOTIFYSUBITEMDRAW  = 32
	
	_fields_ = [("hdr" , NMHDR),
					("dwDrawStage" , DWORD),
					("hdc" , HANDLE),
					("rc" , RECT),
					("iItem" , DWORD),  
					("itemState" , UINT),
					("lParam" , LPARAM),
					("drawFlags", UINT),]

