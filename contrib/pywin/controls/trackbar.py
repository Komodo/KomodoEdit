

from wnd.wintypes import (byref,
												InitCommonControlsEx,
												UINT_MAX,
												NMHDR,
												Structure,
												DWORD,
												HANDLE,
												RECT,
												UINT,
												LPARAM
												)

from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_BAR_CLASSES        = 4
InitCommonControlsEx(ICC_BAR_CLASSES)

#***************************************************
# NOT implemented
#
# NM_CUSTOMDRAW
# TBM_SETUNICODEFORMAT
# TBM_GETUNICODEFORMAT
# 


 # NOT working
 #
 # TBS_AUTOTICKS
 #


class TrackbarMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				
				
				
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm = NMHDR.from_address(msgr.lParam)
					if nm.code ==self.Msg.NM_CUSTOMDRAW:
						cd =  NMCUSTOMDRAW.from_address(msgr.lParam)
						result= self.onMSG(hwnd, "customdraw", 0, cd)
						if result !=None: return result
						return 0

					
					if nm.code ==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasedcapture", 0, 0)
						return 0
			return 0		## 
		elif msg==self.Msg.WM_DESTROY: self.onMSG(hwnd, "destroy", 0, 0)
					
				
	#-------------------------------------------------------------------------
	# methods
	
	def ClearSelected(self):
		self.SendMessage(self.Hwnd, self.Msg.TBM_CLEARSEL, 1, 0)
	
	def Clear(self):
		self.SendMessage(self.Hwnd, self.Msg.TBM_CLEARTICS, 1, 0)
	
	def GetLeftBuddy(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETBUDDY, 1, 0)
		if result: return result
	
	def GetTopBuddy(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETBUDDY, 1, 0)
		if result: return result

	def GetRightBuddy(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETBUDDY, 0, 0)
		if result: return result
	
	def GetBottomBuddy(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETBUDDY, 0, 0)
		if result: return result

	def GetChannelRect(self):
		rc=RECT()
		self.SendMessage(self.Hwnd, self.Msg.TBM_GETCHANNELRECT, 0, byref(rc))
		return rc

	def GetLineSize(self):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_GETLINESIZE, 0, 0)

	def GetTicks(self):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_GETNUMTICS, 0, 0)

	def GetPageSize(self):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_GETPAGESIZE, 0, 0)

	def GetPos(self):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_GETPOS, 0, 0)

	def GetTickList(self):
		n=self.GetTicks() - 2
		if n:
			addr=self.SendMessage(self.Hwnd, self.Msg.TBM_GETPTICS, 0, 0)
			arrDw=(DWORD*n).from_address(addr)
			return map(None, arrDw)
		return []

	def GetRange(self):
		return (self.SendMessage(self.Hwnd, self.Msg.TBM_GETRANGEMIN, 0, 0),
						self.SendMessage(self.Hwnd, self.Msg.TBM_GETRANGEMAX, 0, 0))
	
	def GetSelected():
		return (self.SendMessage(self.Hwnd, self.Msg.TBM_GETSELSTART, 0, 0),
						self.SendMessage(self.Hwnd, self.Msg.TBM_GETSELEND, 0, 0))

	def GetThumbSize(self):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_GETTHUMBLENGTH , 0, 0)

	def GetThumbRect(self):
		rc=RECT()
		self.SendMessage(self.Hwnd, self.Msg.TBM_GETTHUMBRECT, 0, byref(rc))
		return rc

	def GetTick(self, i):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETTIC , i, 0)
		if result <0: raise "no tick found"
		return result

	def GetTickPos(self, n):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETTICPOS , i, 0)
		if result <0: raise "no tick found"
		return result
	
	def GetTooltips(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_GETTOOLTIPS , 0, 0)
		if result: return result

	def SetLeftBuddy(self, Control):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETBUDDY , 1, Control.Hwnd)
		if result: return result
	
	def SetTopBuddy(self, Control):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETBUDDY , 1, Control.Hwnd)
		if result: return result

	def SetRightBuddy(self, Control):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETBUDDY , 0, Control.Hwnd)
		if result: return result

	def SetBottomBuddy(self, Control):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETBUDDY , 0, Control.Hwnd)
		if result: return result

	def SetLineSize(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_SETLINESIZE , 0, 0)

	def SetPageSize(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_SETPAGESIZE , 0, 0)

	def SetPos(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.TBM_SETPOS , 1, n)

	def SetRange(self, nMin, nMax):
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETRANGEMIN , 0, nMin)
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETRANGEMAX , 1, nMax)

	def SetSelected(self, iMin, iMax):
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETSELSTART , 0, iMin)
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETSELSTART , 1, iMax)
	
	def SetThumbSize(self, n):
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETTHUMBLENGTH , n, 0)
	
	def SetTick(self, i):
		if not self.SendMessage(self.Hwnd, self.Msg.TBM_SETTIC , 0, i):
			raise "could not set tick" 
		
	def SetTickStep(self, i):
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETTICFREQ , i, 0)

	def SetTooltipsLeft(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETTIPSIDE , TBTS_LEFT, 0)
		if result==TBS_LEFT: return "left"
		elif result==TBS_TOP: return "top"
		elif result==TBS_RIGHT: return "right"
		elif result==TBS_BOTTOM: return "bottom"

	def SetTooltipsTop(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETTIPSIDE , TBTS_Top, 0)
		if result==TBS_LEFT: return "left"
		elif result==TBS_TOP: return "top"
		elif result==TBS_RIGHT: return "right"
		elif result==TBS_BOTTOM: return "bottom"

	def SetTooltipsRight(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETTIPSIDE , TBTS_RIGHT, 0)
		if result==TBS_LEFT: return "left"
		elif result==TBS_TOP: return "top"
		elif result==TBS_RIGHT: return "right"
		elif result==TBS_BOTTOM: return "bottom"

	def SetTooltipsBottom(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TBM_SETTIPSIDE , TBTS_BOTTOM, 0)
		if result==TBS_LEFT: return "left"
		elif result==TBS_TOP: return "top"
		elif result==TBS_RIGHT: return "right"
		elif result==TBS_BOTTOM: return "bottom"

	def SetTooltips(self, Tooltip):
		self.SendMessage(self.Hwnd, self.Msg.TBM_SETTOOLTIPS,  Tooltip.Hwnd, 0)



#***********************************************
WM_USER   = 1024
NM_FIRST = UINT_MAX
#***********************************************

class Styles:
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
	TBS_REVERSED       = 512  # Accessibility hint: the smaller number (usually the min value) means "high" and the larger number (usually the max value) means "low"
	TBS_DOWNISLEFT     = 1024  # Down=Left and Up=Right (default is Down=Right and Up=Left)



Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['TBS_', ]



class Msgs: 
	TBM_GETPOS             = WM_USER
	TBM_GETRANGEMIN        = WM_USER + 1
	TBM_GETRANGEMAX        = WM_USER + 2
	TBM_GETTIC             = WM_USER + 3
	TBM_SETTIC             = WM_USER + 4
	TBM_SETPOS             = WM_USER + 5
	TBM_SETRANGE           = WM_USER + 6
	TBM_SETRANGEMIN        = WM_USER + 7
	TBM_SETRANGEMAX        = WM_USER + 8
	TBM_CLEARTICS          = WM_USER + 9
	TBM_SETSEL             = WM_USER + 10
	TBM_SETSELSTART        = WM_USER + 11
	TBM_SETSELEND          = WM_USER + 12
	TBM_GETPTICS           = WM_USER + 14
	TBM_GETTICPOS          = WM_USER + 15
	TBM_GETNUMTICS         = WM_USER + 16
	TBM_GETSELSTART        = WM_USER + 17
	TBM_GETSELEND          = WM_USER + 18
	TBM_CLEARSEL           = WM_USER + 19
	TBM_SETTICFREQ         = WM_USER + 20
	TBM_SETPAGESIZE        = WM_USER + 21
	TBM_GETPAGESIZE        = WM_USER + 22
	TBM_SETLINESIZE        = WM_USER + 23
	TBM_GETLINESIZE        = WM_USER + 24
	TBM_GETTHUMBRECT       = WM_USER + 25
	TBM_GETCHANNELRECT     = WM_USER + 26
	TBM_SETTHUMBLENGTH     = WM_USER + 27
	TBM_GETTHUMBLENGTH     = WM_USER + 28
	TBM_SETTOOLTIPS        = WM_USER + 29
	TBM_GETTOOLTIPS        = WM_USER + 30
	TBM_SETTIPSIDE         = WM_USER + 31

	TBM_SETBUDDY           = WM_USER + 32 # wparam = BOOL fLeft; (or right)
	TBM_GETBUDDY           = WM_USER + 33 # wparam = BOOL fLeft; (or right)


	#TBM_SETUNICODEFORMAT   = CCM_SETUNICODEFORMAT
	#TBM_GETUNICODEFORMAT   = CCM_GETUNICODEFORMAT

	NM_RELEASEDCAPTURE = NM_FIRST - 16
	NM_CUSTOMDRAW      = NM_FIRST - 12
Msgs.__dict__.update(control.control_msgs.__dict__)


#*******************************************************************************
#*******************************************************************************

class Trackbar(TrackbarMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x,y,w,h,*styles):
		self.Style= Styles
		self.Msg= Msgs 


		styles += 'subclass',
		control.BaseControl.__init__(self, parent,  "msctls_trackbar32", "", x, y, w, h, *styles)	
		
						
class TrackbarFromHandle(TrackbarMethods, control.ControlFromHandle, ControlMethods):
	def __init__(self, phwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)	
		
		

#**********************************************************************************

# TrackBar Tip Side flags
TBTS_TOP               = 0
TBTS_LEFT              = 1
TBTS_BOTTOM            = 2
TBTS_RIGHT             = 3


TB_LINEUP              = 0
TB_LINEDOWN            = 1
TB_PAGEUP              = 2
TB_PAGEDOWN            = 3
TB_THUMBPOSITION       = 4
TB_THUMBTRACK          = 5
TB_TOP                 = 6
TB_BOTTOM              = 7
TB_ENDTRACK            = 8

class NMCUSTOMDRAW(Structure):
	PREPAINT           = 1
	POSTPAINT          = 2
	
	# customdraw return flags
	DODEFAULT          = 0
	NEWFONT            = 2
	SKIPDEFAULT        = 4
	NOTIFYPOSTPAINT    = 16
	NOTIFYITEMDRAW	= 32
			
	TICS    =    1
	THUMB  = 2
	CHANNEL = 3
	
	
	_fields_ = [("hdr" , NMHDR),
					("drawStage" , DWORD),
					("hdc" , HANDLE),
					("rc" , RECT),
					("itemSpec" , DWORD)]