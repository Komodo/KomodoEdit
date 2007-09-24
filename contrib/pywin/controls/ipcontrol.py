

from wnd.wintypes import (Structure,
												byref,
												DWORD,
												HIWORD,
												LOWORD,
												LOBYTE,
												HIBYTE,
												MAKELONG,
												MAKEWORD,
												UINT_MAX,
												NMHDR,
												INT,
												InitCommonControlsEx)
from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_INTERNET_CLASSES   = 2048
InitCommonControlsEx(ICC_INTERNET_CLASSES)

#***************************************************
# TODO
#
# WM_SETFOCUS/WM_KILLFOCUS do not work as suposed to
#


class IPControlMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		#if msg==self.Msg.WM_SETFOCUS:
		#	self.onMSG(hwnd, "setfocus", wp, lp)
		#elif msg==self.Msg.WM_KILLFOCUS:
		#	self.onMSG(hwnd, "killfocus", wp, lp)
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
		
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm=NMHDR.from_address(msgr.lParam)
					if nm.code==self.Msg.IPN_FIELDCHANGED:
						nmip=NMIPADDRESS.from_address(msgr.lParam)
						result=self.onMSG(hwnd, "fieldchanged", nmip.iField, nmip.iValue)
						if isinstance(result, (int, long)):
							if self._IsUByte(result):
								nmip.iValue=result
							else: raise ValueError("value out of range: %s" % result)
			return 0
		
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			

			
	#-------------------------------------------------------------------------
	# methods

	def SetAddress(self, i0, i1, i2, i3):
		if not self._IsUByte(i0, i1, i2, i3):
			raise ValueError("invalid address: %s" % repr((i0, i1, i2, i3)))
		self.SendMessage(self.Hwnd, self.Msg.IPM_SETADDRESS,
									0, self.AddressToDword(i0, i1, i2, i3))
	
	def GetAddress(self):
		dw=DWORD()
		self.SendMessage(self.Hwnd, self.Msg.IPM_GETADDRESS, 0, byref(dw))
		return self.DwordToAddress(dw.value)
	
	def HasAddress(self):
		return not self.SendMessage(self.Hwnd, self.Msg.IPM_ISBLANK, 0, 0)
			
	def ClearAddress(self):
		self.SendMessage(self.Hwnd, self.Msg.IPM_CLEARADDRESS, 0, 0)
	
	def SelectAddress(self, n):
		self.SendMessage(self.Hwnd, self.Msg.IPM_SETFOCUS, n, 0)

	def SetRange(self, n, nMin, nMax):
		if not self._IsUByte(nMin, nMax):
			raise ValueError("invalid range: %s" % repr((nMin, nMax)))
		if not self.SendMessage(self.Hwnd, self.Msg.IPM_SETRANGE, n, MAKEWORD(nMin, nMax)):
			raise RuntimeError("could not set range")

	def DwordToAddress(self, dw):
		w1, w2= HIWORD(dw), LOWORD(dw)
		return  HIBYTE(w1), LOBYTE(w1), HIBYTE(w2),LOBYTE(w2)
		
	def AddressToDword(self, i0, i1, i2, i3):
		if not self._IsUByte(i0, i1, i2, i3):
			raise ValueError("invalid address: %s" % repr((i0, i1, i2, i3)))
		return MAKELONG(MAKEWORD(i3, i2), MAKEWORD(i1, i0))
		
	def AddressToString(self, addr):
		if isinstance(addr, (int, long)):
			addr=self.SplitAddress(addr)
		if not self._IsUByte(*addr):
			raise ValueError("invalid address: %s" % repr(addr))
		try:
			if len(addr)==4:	return '.'.join(map(str, addr))
			else:	raise ''
		except: raise ValueError("invalid address: %s" % repr(addr))

	def _IsUByte(self, *bytes):
		flag=True
		for i in bytes:
			if i < 0 or i > 255:
				flag=False
		return flag

#**************************************************************************************
#***********************************************
IPN_FIRST               = UINT_MAX-860 
WM_USER = 1024

class Styles:	pass
Styles.__dict__.update(control.control_styles.__dict__)
#Styles.prefix += []


class Msgs: 
	IPN_FIELDCHANGED  = IPN_FIRST
	
	IPM_CLEARADDRESS  = WM_USER + 100 # no parameters
	IPM_SETADDRESS    = WM_USER + 101 # lparam = TCP/IP address
	IPM_GETADDRESS    = WM_USER + 102 # lresult = # of non black fields. lparam = LPDWORD for TCP/IP address
	IPM_SETRANGE      = WM_USER + 103 # wparam = field, lparam = range
	IPM_SETFOCUS      = WM_USER + 104 # wparam = field
	IPM_ISBLANK       = WM_USER + 105 # no parameters

Msgs.__dict__.update(control.control_msgs.__dict__)


class IPControl(IPControlMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysIPAddress32", "", x, y, w, h, *styles)						
		

			
class IPControlFromHandle(IPControlMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		

				
	

class NMIPADDRESS(Structure):
	_fields_ = [("hdr", NMHDR),
					("iField", INT),
					("iValue", INT)]