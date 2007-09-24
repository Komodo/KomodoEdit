
from wnd.wintypes import (user32, 
												Structure, 
												sizeof,
												byref, 
												UINT,
												INT, 
												LOWORD, 
												HIWORD)		
from wnd import fwtypes as fw
from wnd.consts import vk
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#***************************************************
# TODO:
#
# ScrollWindowEx
# ScrollDC

def HasScrollbar(Window):
	style=Window.GetStyleL('style')
	if style & WS_VSCROLL or style & WS_HSCROLL:
		return True
	return False
	
# ShowScrollBar should not be called when processing
# a scrollbar message

def ShowHorzScrollbar(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_HORZ, 1):
		raise RuntimeError("could not show horz scrollbar")
	
def HideHorzScrollbar(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_HORZ, 0):
		raise RuntimeError("could not show horz scrollbar")
	
def ShowVertScrollbar(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_VERT, 1):
		raise RuntimeError("could not show vert scrollbar")
	
def HideHorzScrollbar(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_VERT, 0):
		raise RuntimeError("could not show vert scrollbar")
	
def ShowScrollbars(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_BOTH, 1):
		raise RuntimeError("could not show scrollbars")	

def HideScrollbars(Window):
	if not user32.ShowScrollBar(Window.Hwnd, SB_BOTH, 0):
		raise RuntimeError("could not show scrollbars")	

def GetHorzScrollInfo(Window):
	sci=SCROLLINFO()
	sci.fMask=SIF_ALL
	if not user32.GetScrollInfo(Window.Hwnd, 
				SB_HORZ, byref(sci)):
			raise RuntimeError("could not retrieve horz scrollinfo")	
	return sci.nMin, sci.nMax, sci.nPage, sci.nPos, sci.nTrackPos 
	
def GetVertScrollInfo(Window):
	sci=SCROLLINFO()
	sci.fMask=SIF_ALL
	if not user32.GetScrollInfo(Window.Hwnd, 
				SB_VERT, byref(sci)):
			raise RuntimeError("could not retrieve vert scrollinfo")	
	return sci.nMin, sci.nMax, sci.nPage, sci.nPos, sci.nTrackPos 

def SetHorzScrollInfo(Window, nMin, nMax, nPage, nPos, hide=True):
	sci=SCROLLINFO()
	sci.fMask=SIF_ALL
	if not hide: sci.fMask |=SIF_DISABLENOSCROLL
	sci.nMin = nMin
	sci.nMax = nMax
	sci.nPage = nPage
	sci.nPos = nPos
	if not user32.SetScrollInfo(Window.Hwnd, 
				SB_HORZ, byref(sci), 1):
			raise RuntimeError("could not set horz scrollinfo")	
	
def SetVertScrollInfo(Window, nMin, nMax, nPage, nPos, hide=True):
	sci=SCROLLINFO()
	sci.fMask=SIF_ALL
	if not hide: sci.fMask |=SIF_DISABLENOSCROLL
	sci.nMin = nMin
	sci.nMax = nMax
	sci.nPage = nPage
	sci.nPos = nPos
	if not user32.SetScrollInfo(Window.Hwnd, 
				SB_VERT, byref(sci), 1):
			raise RuntimeError("could not set vert scrollinfo")
	
def EnableLeftArrow(Window):
	user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_ENABLE_BOTH)
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DISABLE_RIGHT):
		raise RuntimeError("could not enable left arrow")

def EnableRightArrow(Window):
	user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_ENABLE_BOTH)
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DISABLE_LEFT):
		raise RuntimeError("could not enable right arrow")

def EnableHorzArrows(Window):
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_ENABLE_BOTH):
		raise RuntimeError("could not enable arrows")

def DisableHorzArrows(Window):
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DIABLE_BOTH):
		raise RuntimeError("could not disable arrows")

def EnableUpArrow(Window):
	user32.EnableScrollBar(Window.Hwnd, 
									SB_VERT, ESB_ENABLE_BOTH)
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DISABLE_DOWN):
		raise RuntimeError("could not enable left arrow")

def EnableDownArrow(Window):
	user32.EnableScrollBar(Window.Hwnd, 
									SB_VERT, ESB_ENABLE_BOTH)
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DISABLE_UP):
		raise RuntimeError("could not enable right arrow")

def EnableVertArrows(Window):
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_VERT, ESB_ENABLE_BOTH):
		raise RuntimeError("could not enable arrows")

def DisableVertArrows(Window):
	if not user32.EnableScrollBar(Window.Hwnd, 
									SB_HORZ, ESB_DIABLE_BOTH):
		raise RuntimeError("could not disable arrows")

#***************************************************


class ScrollbarMethods:
	#-----------------------------------------------------------------	
	# message handlers	

	def onMESSAGE(self, hwnd, msg, wp, lp):
				
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_HSCROLL:
					return self._base_HandleScroll(hwnd, msgr.msg, msgr.wParam, msgr.lParam)
				elif msgr.msg==self.Msg.WM_VSCROLL:
					return self._base_HandleScroll(hwnd, msgr.msg, msgr.wParam, msgr.lParam)
			return 0
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			

	def ForwardKeyMessage(self, hwnd, msg, wp, lp):
		# hwnd is not passed along
		
		if msg==self.Msg.WM_KEYDOWN:
			code=None
			if wp==vk.VK_UP: code=SB_LINEUP
			elif wp==vk.VK_PRIOR: code=SB_PAGEUP
			elif wp==vk.VK_NEXT: code=SB_PAGEDOWN
			elif wp==vk.VK_DOWN: code=SB_LINEDOWN
			elif wp==vk.VK_HOME: code=SB_TOP
			elif wp==vk.VK_END: code=SB_BOTTOM
			if code !=None:
				if self.GetStyleL('style') & self.Style.SBS_VERT:
					self._base_HandleScroll(self.Hwnd, self.Msg.WM_VSCROLL, code, 0)
				else:
					self._base_HandleScroll(self.Hwnd, self.Msg.WM_HSCROLL, code, 0)
				return True
		return False

	def _base_HandleScroll(self, hwnd, msg, wp, lp):
		oldPos=self.GetPos()
		code, newPos=LOWORD(wp), HIWORD(wp)
		nMin, nMax = self.GetRange()
		if code==SB_ENDSCROLL: 
			newPos, oldPos= oldPos, 0
			code='endscroll'
		elif code==SB_LEFT: 
			newPos=nMin
			code= msg== self.Msg.WM_VSCROLL and 'up' or 'left'
		elif code==SB_RIGHT: 
			newPos=nMax
			code= msg== self.Msg.WM_VSCROLL and 'down' or 'right'
		elif code==SB_LINELEFT:
			newPos=oldPos - 1
			code= msg== self.Msg.WM_VSCROLL and 'lineup' or 'lineleft'
		elif code==SB_LINERIGHT: 
			newPos=oldPos + 1
			code= msg== self.Msg.WM_VSCROLL and 'linedown' or 'lineright'
		elif code==SB_PAGELEFT: 
			newPos=oldPos - self.GetPageSize()
			code= msg== self.Msg.WM_VSCROLL and 'pageup' or 'pageleft'
		elif code==SB_PAGERIGHT: 
			newPos=oldPos + self.GetPageSize()
			code= msg== self.Msg.WM_VSCROLL and 'pagedown' or 'pageright'
		elif code==SB_THUMBPOSITION: 
			newPos=self.GetTrackPos()	
			code='thumbpos'
		elif code==SB_THUMBTRACK: 
			newPos=self.GetTrackPos()				
			code='thumbtrack'
		if newPos < nMin: newPos=nMin
		if newPos > nMax: newPos=nMax
		msg= self.Msg.WM_VSCROLL and 'vscroll' or 'hscroll'
		self.onMSG(hwnd, msg, code, (oldPos, newPos))
		return 0

	#-------------------------------------------------------------------------
	# methods
	
	def Show(self): return bool(user32.ShowScrollBar(self.Hwnd, SB_CTL, 1))
	def Hide(self): return bool(user32.ShowScrollBar(self.Hwnd, SB_CTL, 0))
	def Enable(self): return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_ENABLE_BOTH))
	def Disable(self):	return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_DISABLE_BOTH))
		
	
	def DisableRightArrow(self):
		if self.GetStyleL('style') & self.Style.SBS_VERT:
			raise RuntimeError("invalid method for vertical scrollbar")
		return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_DISABLE_LEFT))
			
	def DisableLeftArrow(self):
		if self.GetStyleL('style') & self.Style.SBS_VERT:
			raise RuntimeError("invalid method for vertical scrollbar")
		return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_DISABLE_RIGHT))
				
	def DisableUpArrow(self):
		if not self.GetStyleL('style') & self.Style.SBS_VERT:
			raise RuntimeError("invalid method for horizontal scrollbar")
		return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_DISABLE_DOWN))
			
	def DisableDownArrow(self):
		if not self.GetStyleL('style') & self.Style.SBS_VERT:
			raise RuntimeError("invalid method for horizontal scrollbar")
		return bool(user32.EnableScrollBar(self.Hwnd, SB_CTL, ESB_DISABLE_UP))
			
	def SetPageSize(self, n):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_PAGE
		sbi.nPage=n
		self.SendMessage(self.Hwnd,
				self.Msg.SBM_SETSCROLLINFO, 1, byref(sbi))
			
	def GetPageSize(self):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_PAGE
		if not self.SendMessage(self.Hwnd, self.Msg. SBM_GETSCROLLINFO, 0, byref(sbi)):
			raise RuntimeError("could not retrieve page size")
		return sbi.nPage

	def GetPos(self):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_POS
		if not self.SendMessage(self.Hwnd, self.Msg.SBM_GETSCROLLINFO, 0, byref(sbi)):
			raise RuntimeError("could not retrieve position")
		return sbi.nPos
	
	def SetPos(self, n):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_POS
		sbi.nPos=n
		return self.SendMessage(self.Hwnd, self.Msg.SBM_SETSCROLLINFO, 1, byref(sbi))
					
	def SetRange(self, nMin, nMax):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_RANGE
		sbi.nMin=nMin
		sbi.nMax=nMax
		return self.SendMessage(self.Hwnd, self.Msg. SBM_SETSCROLLINFO, 1, byref(sbi))
		
	def GetRange(self):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_RANGE
		if not self.SendMessage(self.Hwnd, self.Msg. SBM_GETSCROLLINFO, 0, byref(sbi)):
			raise RuntimeError("could not retrieve range")
		return sbi.nMin, sbi.nMax

	def GetTrackPos(self):
		sbi=SCROLLINFO()
		sbi.fMask=SIF_TRACKPOS
		if not self.SendMessage(self.Hwnd, self.Msg. SBM_GETSCROLLINFO, 0, byref(sbi)):
			raise RuntimeError("could not retrieve trackpos")
		return sbi.nTrackPos

	def StepUp(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_UP, 0)

	def StepDown(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_DOWN, 0)
	
	def StepPrior(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_PRIOR, 0)

	def StepNext(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_NEXT, 0)
	
	def StepHome(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_HOME, 0)

	def StepEnd(self):
		self.ForwardKeyMessage(0, self.Msg.WM_KEYDOWN, vk.VK_END, 0)

	

#**************************************************************************

class Styles:
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
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['SBS_', ]


class Msgs: 
	SBM_SETPOS           = 224 
	SBM_GETPOS           = 225
	SBM_SETRANGE         = 226 
	SBM_SETRANGEREDRAW   = 230 
	SBM_GETRANGE         = 227 
	SBM_ENABLE_ARROWS    = 228
	SBM_SETSCROLLINFO    = 233
	SBM_GETSCROLLINFO    = 234
	SBM_GETSCROLLBARINFO = 235

Msgs.__dict__.update(control.control_msgs.__dict__)



class Scrollbar(ScrollbarMethods, control.BaseControl, ControlMethods):
	
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		

		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "Scrollbar", "", x, y, w, h, *styles)						
		

class ScrollbarFromHandle(ScrollbarMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		


# SIF_DISABLENOSCROLL

#***********************************************

class SCROLLINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("fMask", UINT),
					("nMin", INT),
					("nMax", INT),
					("nPage", UINT),
					("nPos", INT),
					("nTrackPos", INT)]
	def __init__(self): self.cbSize=sizeof(self)


SIF_RANGE           = 1
SIF_PAGE            = 2
SIF_POS             = 4
SIF_DISABLENOSCROLL = 8
SIF_TRACKPOS        = 16
SIF_ALL = SIF_RANGE | SIF_PAGE | SIF_POS | SIF_TRACKPOS

SB_HORZ = 0
SB_VERT = 1
SB_CTL  = 2
SB_BOTH = 3

ESB_ENABLE_BOTH   = 0
ESB_DISABLE_BOTH  = 3

ESB_DISABLE_LEFT  = 1
ESB_DISABLE_RIGHT = 2

ESB_DISABLE_UP    = 1
ESB_DISABLE_DOWN  = 2

WS_VSCROLL         = 2097152
WS_HSCROLL         = 1048576

SB_LINEUP        = 0
SB_LINELEFT      = 0
SB_LINEDOWN      = 1
SB_LINERIGHT     = 1
SB_PAGEUP        = 2
SB_PAGELEFT      = 2
SB_PAGEDOWN      = 3
SB_PAGERIGHT     = 3
SB_THUMBPOSITION = 4
SB_THUMBTRACK    = 5
SB_TOP           = 6
SB_LEFT          = 6
SB_BOTTOM        = 7
SB_RIGHT         = 7
SB_ENDSCROLL     = 8


