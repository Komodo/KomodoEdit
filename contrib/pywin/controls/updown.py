

from wnd.wintypes import (Structure, 
													byref, 
													UINT_MAX,
													INT_MAX,
													INT_MIN,
													c_int,
													HIWORD,
													LOWORD,
													DWORD,
													NMHDR,
													InitCommonControlsEx)
from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_UPDOWN_CLASS       = 16
InitCommonControlsEx(ICC_UPDOWN_CLASS)

#***************************************************
UD_MAXVAL            = 32767
UD_MINVAL            = - UD_MAXVAL



class UpdownMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm=NMHDR.from_address(msgr.lParam)
					if nm.code==self.Msg.UDN_DELTAPOS:
						nmud=NMUPDOWN.from_address(msgr.lParam)
						if self.onMSG(hwnd, "setpos", nmud.iPos,		\
							nmud.iDelta)==False: return 1
						return 0
					
					if nm.code==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasedcapture", 0, 0)
			return 0
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
		
			
				
	#-------------------------------------------------------------------------
	# ethods

	def GetBuddy(self):
		result = self.SendMessage(self.Hwnd, self.Msg.UDM_GETBUDDY , 0, 0)
		if result: return result

	def SetBuddy(self, Window):
		result = self.SendMessage(self.Hwnd, self.Msg.UDM_SETBUDDY , Window.Hwnd, 0)
		if result: return result

	def GetRange(self):
		start=c_int()
		stop=c_int()
		self.SendMessage(self.Hwnd, self.Msg.UDM_GETRANGE32, byref(start), byref(stop))
		return start.value, stop.value

	def SetRange(self, start, stop):
		if self.GetBase()==16:
			if start <0 or stop <0:
				raise ValueError("only unsigned hex values allowed")
		if start > INT_MAX or stop > INT_MAX:
			raise ValueError("INT_MAX exceeded")
		if start < INT_MIN or stop < INT_MIN:
			raise ValueError("INT_MIN exceeded")
		self.SendMessage(self.Hwnd, self.Msg.UDM_SETRANGE32, start,  stop)

	def GetBase(self):
		return self.SendMessage(self.Hwnd, self.Msg.UDM_GETBASE , 0, 0)

	def SetBase(self, base):
		if base not in (10, 16):
			raise ValueError("base must be 10 or 16")
		if base==16:
			start, stop=self.GetRange()
			if start <0 or stop <0:
				raise ValueError("invalid range for hex display")
		result = self.SendMessage(self.Hwnd, self.Msg.UDM_SETBASE , base, 0)
		if not result: raise RuntimeError("could not set base")
		return result

	def SetAcceleration(self, *accelerations):
		n=len(accelerations)
		arrAcc= (UDACCEL*n)(*accelerations)
		if not self.SendMessage(self.Hwnd, self.Msg.UDM_SETACCEL, n,  byref(arrAcc)):
			raise RuntimeError("could not set acceleration")
		
	def GetAcceleration(self):
		n=self.SendMessage(self.Hwnd, self.Msg.UDM_GETACCEL, 0,  0)
		if n:
			arrAcc= (UDACCEL*n)()
			self.SendMessage(self.Hwnd, self.Msg.UDM_GETACCEL, n,  byref(arrAcc))
			out=[]
			for i in arrAcc: out.append((i.nSec, i.nInc))
			return out
		
	def GetPos(self):
		result=self.SendMessage(self.Hwnd, self.Msg.UDM_GETPOS, 0,  0)
		if HIWORD(result):
			raise RuntimeError("could not retrieve position")
		return LOWORD(result)
	
	def SetPos(self, n):
		 return self.SendMessage(self.Hwnd, self.Msg.UDM_SETPOS, 0,  n)


#***********************************************************************
NM_FIRST = UINT_MAX
UDN_FIRST               = UINT_MAX-721       # updown
WM_USER = 1024

class Styles:
	UDS_WRAP             = 1
	UDS_SETBUDDYINT      = 2
	UDS_ALIGNRIGHT       = 4
	UDS_ALIGNLEFT        = 8
	UDS_AUTOBUDDY        = 16
	UDS_ARROWKEYS        = 32
	UDS_HORZ             = 64
	UDS_NOTHOUSANDS      = 128
	UDS_HOTTRACK         = 256
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['UDS_', ]


class Msgs: 
	NM_RELEASEDCAPTURE = NM_FIRST - 16
	
	UDN_DELTAPOS = UDN_FIRST - 1

	
	UDM_SETRANGE         = WM_USER + 101
	UDM_GETRANGE         = WM_USER + 102
	UDM_SETPOS           = WM_USER + 103
	UDM_GETPOS           = WM_USER + 104
	UDM_SETBUDDY         = WM_USER + 105
	UDM_GETBUDDY         = WM_USER + 106
	UDM_SETACCEL         = WM_USER + 107
	UDM_GETACCEL         = WM_USER + 108
	UDM_SETBASE          = WM_USER + 109
	UDM_GETBASE          = WM_USER + 110
	UDM_SETRANGE32       = WM_USER + 111
	UDM_GETRANGE32       = WM_USER + 112 # wParam & lParam are LPINT
	
	UDM_SETPOS32         = WM_USER + 113
	UDM_GETPOS32         = WM_USER + 114

Msgs.__dict__.update(control.control_msgs.__dict__)


class Updown(UpdownMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "msctls_updown32", "", x, y, w, h, *styles)						
		

class UpdownFromHandle(UpdownMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)		

# NOT implemented
# 
# 

#***********************************************



class UDACCEL(Structure):
	_fields_=[("nSec", DWORD), 
					("nInc", DWORD)]

class NMUPDOWN(Structure):
	_fields_ = [("hdr", NMHDR),
					("iPos", c_int),
					("iDelta", c_int)]