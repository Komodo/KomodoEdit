"""
TODO
	- GetMonthcal leaves garbage behind


NOT IMPLEMENTED
 
	DTN_FORMAT
	DTN_FORMATQUERY
	DTN_USERSTRING
	DTN_WMKEYDOWN




"""


from wnd.wintypes import (NMHDR, 
													SYSTEMTIME,
													DWORD,
													UINT_MAX,
													LPSTR,
													Structure,
													byref,
													InitCommonControlsEx)


from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
from wnd.controls.monthcal import MonthcalFromHandle

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_DATE_CLASSES       = 256
InitCommonControlsEx(ICC_DATE_CLASSES)
#***************************************************

GDTR_MIN       = 1
GDTR_MAX       = 2

GDT_ERROR      = -1
GDT_VALID      = 0
GDT_NONE       = 1

MCSC_BACKGROUND   = 0   # the background color (between months)
MCSC_TEXT         = 1   # the dates
MCSC_TITLEBK      = 2   # background of the title
MCSC_TITLETEXT    = 3
MCSC_MONTHBK      = 4   # background within the month cal
MCSC_TRAILINGTEXT = 5   # the text color of header & trailing days

#**************************************************

class DatepickerMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==self.Msg.WM_SETFOCUS:
			self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			self.onMSG(hwnd, "killfocus", wp, lp)
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm=NMHDR.from_address(msgr.lParam)
											
					if nm.code==self.Msg.DTN_CLOSEUP:
						self.onMSG(hwnd, "closemonthcal", 0, 0)
						return 0
					
					elif nm.code==self.Msg.DTN_DROPDOWN:
						self.onMSG(hwnd, "openmonthcal", 0, 0)
						return 0
					
					elif nm.code==self.Msg.DTN_DATETIMECHANGE:
						nmd=NMDATETIMECHANGE.from_address(msgr.lParam)
						if nmd.dwFlags==GDT_VALID:
							flag= 'valid'
						elif nmd.dwFlags==GDT_NONE:
							flag= 'none'
						elif nmd.dwFlags==DWORD(-1).value:
							flag= 'error'
						else:
							flag= 'unknown'
						self.onMSG(hwnd, "datechange", nmd.st, flag)
					
					elif nm.code==self.Msg.DTN_USERSTRING:
						dt= NMDATETIMESTRING.from_address(msgr.lParam)
						result= self.onMSG(hwnd, "userstring", dt.st, dt.pszUserString)
						if result==True:
							dt.dwFlags= GDT_VALID
						elif result== False:
							dt.dwFlags= GDT_NONE
					
					return 0
				
		
			
				
	#-------------------------------------------------------------------------
	# methods
	
	def SetFormat(self, format):
		if not self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETFORMAT, 0, format):
			raise "could not set format"
			
	def GetMonthcal(self):
		hwnd= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMONTHCAL, 0, 0)
		if not hwnd:
			raise "could not retrieve monthcal"
		mth=  MonthcalFromHandle(hwnd)
		fw.SetFlagMsgReflect(mth, False)
		return mth

	def GetMonthcalBkColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCCOLOR, 0, MCSC_BACKGROUND)
		if result <0:	
			raise "could not retrieve background color"
		return result

	def GetMonthcalMonthBkColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCCOLOR, 0, MCSC_MONTHBK)
		if result <0:	
			raise "could not retrieve month background color"
		return result

	def GetMonthcalTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCCOLOR, 0, MCSC_TEXT)
		if result <0:	
			raise "could not retrieve text color"
		return result

	def GetMonthcalTitleTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCCOLOR, 0, MCSC_TITLETEXT)
		if result <0:	
			raise "could not retrieve title text color"
		return result

	def GetMonthcalTrailingTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCCOLOR, 0, MCSC_TRAILINGTEXT)
		if result <0:	
			raise "could not retrieve trailing text color"
		return result

	def SetMonthcalBkColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCCOLOR, colorref, MCSC_BACKGROUND)
		if result <0:	
			raise "could not set background color"
		return result

	def SetMonthcalMonthBkColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCCOLOR, colorref, MCSC_MONTHBK)
		if result <0:	
			raise "could not set month background color"
		return result

	def SetMonthcalTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCCOLOR, colorref, MCSC_TEXT)
		if result <0:	
			raise "could not set text color"
		return result

	def SetMonthcalTitleTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCCOLOR, colorref, MCSC_TITLETEXT)
		if result <0:	
			raise "could not set title text color"
		return result

	def SetMonthcalTrailingTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCCOLOR, 0, MCSC_TRAILINGTEXT)
		if result <0:	
			raise "could not set trailing text color"
		return result

	def GetMonthcalFont(self):
		return self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETMCFONT, 0, 0)

	def SetMonthcalFont(self, Font):
		self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETMCFONT, 1, Font.handle)

	def GetTime(self):
		st=SYSTEMTIME()
		result= self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETSYSTEMTIME, 0, byref(st))
		if result==GDT_ERROR: raise "could not retrive time"
		if result==GDT_VALID:
			return st
	
	
	def SetTime(self, systemtime):
		if not self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETSYSTEMTIME, GDT_VALID, byref(systemtime)):
			raise "could not set time"
		
	
	def GetRange(self):
		st1=SYSTEMTIME()
		st2=SYSTEMTIME()
		arrSystime=(SYSTEMTIME*2)(st1, st2)
		result=self.SendMessage(self.Hwnd,
				self.Msg.DTM_GETRANGE, 0, byref(arrSystime))
		out=[None, None]
		if result & GDTR_MIN:
			out[0]=st1
		if result & GDTR_MAX:
			out[1]=st2
		return out
		
	def SetRange(self, systemtimeMin, systemtimeMax):
		arrSystime=(SYSTEMTIME*2)()
		flag=0
		if systemtimeMin:
			arrSystime[0]=systemtimeMin
			flag |= GDTR_MIN
		if systemtimeMax:
			arrSystime[0]=systemtimeMax
			flag |= GDTR_MAX
		if not self.SendMessage(self.Hwnd,
				self.Msg.DTM_SETRANGE, flag, byref(arrSystime)):
					raise "could not set range"



#************************************************************************************
#************************************************************************************

class Datepicker(DatepickerMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysDateTimePick32", "", x, y, w, h, *styles)						
		

class DatepickerFromHandle(DatepickerMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		ControlFromHandle.__init__(self, hwnd, styles)
		

				
#***********************************************
DTN_FIRST               = UINT_MAX-760
DTM_FIRST        = 4096
WM_USER = 1024

class Styles:
	DTS_UPDOWN          = 1 # use UPDOWN instead of MONTHCAL
	DTS_SHOWNONE        = 2 # allow a NONE selection
	DTS_SHORTDATEFORMAT = 0 # use the short date format (app must forward WM_WININICHANGE messages)
	DTS_LONGDATEFORMAT  = 4 # use the long date format (app must forward WM_WININICHANGE messages)
	DTS_SHORTDATECENTURYFORMAT = 12 # short date format with century (app must forward WM_WININICHANGE messages)
	DTS_TIMEFORMAT      = 9 # use the time format (app must forward WM_WININICHANGE messages)
	DTS_APPCANPARSE     = 16 # allow user entered strings (app MUST respond to DTN_USERSTRING)
	DTS_RIGHTALIGN      = 32 # right-align popup instead of left-align it	
	
		

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['DTS_', ]



class Msgs: 
	DTM_GETSYSTEMTIME   = DTM_FIRST + 1
	DTM_SETSYSTEMTIME   = DTM_FIRST + 2
	DTM_GETRANGE = DTM_FIRST + 3
	DTM_SETRANGE = DTM_FIRST + 4
	DTM_SETFORMAT  = DTM_FIRST + 5
	DTM_SETMCCOLOR    = DTM_FIRST + 6
	DTM_GETMCCOLOR    = DTM_FIRST + 7
	DTM_GETMONTHCAL   = DTM_FIRST + 8
	DTM_SETMCFONT     = DTM_FIRST + 9
	DTM_GETMCFONT     = DTM_FIRST + 10

	DTN_DATETIMECHANGE  = DTN_FIRST + 1 # the systemtime has changed
	DTN_USERSTRING   = DTN_FIRST + 2  # the user has entered a string
	DTN_WMKEYDOWN   = DTN_FIRST + 3  # modify keydown on app format field (X)
	DTN_FORMAT   = DTN_FIRST + 4  # query display for app 	format field (X)
	DTN_FORMATQUERY  = DTN_FIRST + 5  # query formatting info for app format field (X)
	DTN_DROPDOWN   = DTN_FIRST + 6  # MonthCal has dropped down
	DTN_CLOSEUP   =  DTN_FIRST + 7

Msgs.__dict__.update(control.control_msgs.__dict__)



class NMDATETIMECHANGE(Structure):
	_fields_ = [("nmhdr", NMHDR),
					("dwFlags", DWORD),
					("st", SYSTEMTIME)]

class NMDATETIMESTRING(Structure):
	_fields_ = [("nmhdr", NMHDR),
					("pszUserString", LPSTR),
					("st", SYSTEMTIME),
					("dwFlags", DWORD)]