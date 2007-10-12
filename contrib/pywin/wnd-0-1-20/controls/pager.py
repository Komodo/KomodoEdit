
from wnd.wintypes import (user32,
													Structure,
													NMHDR,
													DWORD,
													c_int,
													BOOL, 
													RECT,
													UINT_MAX,
													InitCommonControlsEx,)


from wnd import fwtypes as fw
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_PAGESCROLLER_CLASS = 4096
InitCommonControlsEx(ICC_PAGESCROLLER_CLASS)

#***************************************************
# NOT implemented
#
# PGM_GETDROPTARGET
# 
# 
# 
# 
# 

class PagerMethods: 
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm = NMHDR.from_address(msgr.lParam)
					if nm.code ==self.Msg.PGN_CALCSIZE:
						nmc=NMPGCALCSIZE.from_address(msgr.lParam)
						if nmc.dwFlag==PGF_CALCHEIGHT:
							result=self.onMSG(hwnd, "calcsize", "height", 0)
							if isinstance(result, (int, long)):
								nmc.iHeight=result
						elif nmc.dwFlag==PGF_CALCWIDTH:
							result=self.onMSG(hwnd, "calcsize", "width", 0)
							if isinstance(result, (int, long)):
								nmc.iWidth=result
					elif nm.code ==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasedcapture", 0, 0)
			return 0
			
			
			# Not working
			#elif nm.code ==self.Msg.PGN_SCROLL:
			#	nmps=NMPGSCROLL.from_address(lp)
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
			
		
	#-------------------------------------------------------------------------
	# methods
	
	def SetChild(self, Control):
		user32.SetParent(Control.Hwnd, self.Hwnd)
		self.SendMessage(self.Hwnd, self.Msg.PGM_SETCHILD, 0, Control.Hwnd)
	
	def GetButtonSize(self):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSIZE, 0, 0)
	
	def SetButtonSize(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_SETBUTTONSIZE, 0, n)

	def SetBorderSize(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_SETBORDER, 0, n)
	
	def GetBorderSize(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_GETBORDER, 0, 0)
	
	def SetBkColor(self, colorref):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_SETBKCOLOR, 0, colorref)
	
	def GetPos(self):
		return self.SendMessage(self.Hwnd, self.Msg.PGM_GETPOS, 0, 0)
	
	def SetPos(self, n):
		self.SendMessage(self.Hwnd, self.Msg.PGM_SETPOS, 0, n)
	
	def CalcSize(self):
		self.SendMessage(self.Hwnd, self.Msg.PGM_CALCSIZE, 0, 0)
	
		
	#------------------------------------------------------------------------------------
	# all the has- and is-methods

	def IsLeftButtonVisible(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_TOPORLEFT)
		return bool(state & PGF_INVISIBLE)
				
	def IsRightButtonVisible(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_BOTTOMORRIGHT)
		return bool(state & PGF_INVISIBLE)
			
	def IsTopButtonVisible(self): return self.IsLeftButtonVisible()
	def IsBottomButtonVisible(self): return self.IsRightButtonVisible()
		
	def IsLeftButtonGrayed(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_TOPORLEFT)
		return bool(state & state & PGF_GRAYED)
				
	def IsRightButtonGrayed(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_BOTTOMORRIGHT)
		return bool(state & state & PGF_GRAYED)
	
	def IsTopButtonGrayed(self): return self.IsLeftButtonGrayed()
	def IsBottomButtonGrayed(self): return self.IsRightButtonGrayed()
		
	def IsLeftButtonPressed(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_TOPORLEFT)
		return bool(state & state & PGF_PRESSED)
				
	def IsRightButtonPressed(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_BOTTOMORRIGHT)
		return bool(state & state & PGF_PRESSED)
			
	def IsTopButtonPressed(self): return self.IsLeftButtonPressed()
	def IsBottomButtonPressed(self): return self.IsRightButtonPressed()
		
	def IsLeftButtonHilighted(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_TOPORLEFT)
		return bool(state & state & PGF_HOT)
		
		
	def IsRightButtonHilighted(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_BOTTOMORRIGHT)
		return bool(state & state & PGF_HOT)
			
	def IsTopButtonHilighted(self): return self.IsLeftButtonHilighted()
	def IsBottomButtonHilighted(self): return self.IsRightButtonHilighted()
		
	def IsLeftButtonNormal(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_TOPORLEFT)
		return bool(state & state & PGF_NORMAL)
				
	def IsRightButtonNormal(self):
		state= self.SendMessage(self.Hwnd, self.Msg.PGM_GETBUTTONSTATE, 0, PGB_BOTTOMORRIGHT)
		return bool(state & state & PGF_NORMAL)
			
	def IsTopButtonNormal(self): return self.IsLeftButtonNormal()
	def IsBottomButtonNormal(self): return self.IsRightButtonNormal()


#******************************************************************+
#***********************************************
PGN_FIRST               = UINT_MAX-900
PGM_FIRST              = 5120

CCM_FIRST              = 8192
NM_FIRST = UINT_MAX
#***********************************************
CCM_GETDROPTARGET      = CCM_FIRST + 4

class Styles:
	PGS_VERT                = 0
	PGS_HORZ                = 1
	PGS_AUTOSCROLL          = 2
	PGS_DRAGNDROP           = 4
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['PGS_', ]


class Msgs: 
	NM_RELEASEDCAPTURE = NM_FIRST - 16
	PGN_SCROLL      = PGN_FIRST - 1	
	PGN_CALCSIZE    = PGN_FIRST - 2
	
	
	NM_CLICK           = NM_FIRST - 2  # uses NMCLICK type
	NM_DBLCLK          = NM_FIRST - 3
	NM_RETURN          = NM_FIRST - 4
	NM_RCLICK          = NM_FIRST - 5  # uses NMCLICK type
	
	NM_RDBLCLK         = NM_FIRST - 6
	
		
	PGM_SETCHILD            = PGM_FIRST + 1
	PGM_RECALCSIZE          = PGM_FIRST + 2
	PGM_FORWARDMOUSE        = PGM_FIRST + 3
	PGM_SETBKCOLOR          = PGM_FIRST + 4
	PGM_GETBKCOLOR          = PGM_FIRST + 5
	PGM_SETBORDER          = PGM_FIRST + 6
	PGM_GETBORDER          = PGM_FIRST + 7
	PGM_SETPOS              = PGM_FIRST + 8
	PGM_GETPOS              = PGM_FIRST + 9
	PGM_SETBUTTONSIZE       = PGM_FIRST + 10
	PGM_GETBUTTONSIZE       = PGM_FIRST + 11
	PGM_GETBUTTONSTATE      = PGM_FIRST + 12
	PGM_GETDROPTARGET       = CCM_GETDROPTARGET

Msgs.__dict__.update(control.control_msgs.__dict__)



class Pager(PagerMethods, control.BaseControl, ControlMethods):
	
	
	def __init__(self, parent, x,y,w,h,*styles):
		self.Style= Styles
		self.Msg= Msgs 
		


		styles += 'subclass',
		control.BaseControl.__init__(self, parent,  "SysPager", "", x, y, w, h, *styles)	
		
						
class PagerFromHandle(PagerMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		
	

			
#***********************************************
PGF_CALCWIDTH   = 1
PGF_CALCHEIGHT  = 2


PGF_SCROLLUP    = 1
PGF_SCROLLDOWN  = 2
PGF_SCROLLLEFT  = 4
PGF_SCROLLRIGHT = 8


#Keys down
PGK_SHIFT       = 1
PGK_CONTROL     = 2
PGK_MENU        = 4

#The scroll can be in one of the following control State
PGF_INVISIBLE       = 0      # Scroll button is not visible
PGF_NORMAL          = 1      # Scroll button is in normal state
PGF_GRAYED          = 2      # Scroll button is in grayed state
PGF_DEPRESSED       = 4      # Scroll button is in depressed state
PGF_HOT             = 8      # Scroll button is in hot state


# The following identifiers specifies the button control
PGB_TOPORLEFT       = 0
PGB_BOTTOMORRIGHT   = 1

class NMPGCALCSIZE(Structure):
	_fields_ = [("hdr", NMHDR),
					("dwFlag", DWORD),
					("iWidth", c_int),
					("iHeight", c_int)]

class NMPGSCROLL(Structure):
	_fields_ = [("hdr", NMHDR),
					("fwKeys", BOOL),
					("rcParent", RECT),
					("iDir", c_int),
					("iXpos", c_int),
					("iYpos", c_int),
					("iScroll", c_int)]


