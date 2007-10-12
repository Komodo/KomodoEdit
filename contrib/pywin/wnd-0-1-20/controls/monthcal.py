

from wnd.wintypes import (NMHDR, 
													SYSTEMTIME,
													UINT,
													POINT,

													UINT_MAX,
													Structure,
													byref,
													InitCommonControlsEx)

from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_DATE_CLASSES       = 256
InitCommonControlsEx(ICC_DATE_CLASSES)
#************************************************

# NOT implemented
# MCM_SETDAYSTATE
# MCN_GETDAYSTATE
# MCM_SETUNICODEFORMAT
# MCM_GETUNICODEFORMAT

#****************************************************
class MonthcalMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==self.Msg.WM_SETFOCUS:
			self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			self.onMSG(hwnd, "killfocus", wp, lp)
		
		if wp==fw.WND_NM_MSGREFLECT:
			msgr= fw.WND_MSGREFLECT.from_address(lp)
			msgr.fReturn= self._base_fMsgReflect
	
			if msgr.msg==self.Msg.WM_NOTIFY:
				nm=NMHDR.from_address(msgr.lParam)
							
				if nm.code==self.Msg.MCN_SELCHANGE:
					nmsc=NMSELCHANGE.from_address(msgr.lParam)
					st1=nmsc.stSelStart
					st2=nmsc.stSelEnd
					self.onMSG(hwnd, "selchanbge", (st1, st2), 0)
					return 0
				if nm.code==self.Msg.MCN_SELECT:
					nmsc=NMSELCHANGE.from_address(msgr.lParam)
					st1=nmsc.stSelStart
					st2=nmsc.stSelEnd
					self.onMSG(hwnd, "select", (st1, st2), 0)
					return 0
				
				if nm.code==self.Msg.NM_RELEASEDCAPTURE:
					self.onMSG(hwnd, "releasedcapture", 0, 0)
					
				
				return 0	

	
				
	#-------------------------------------------------------------------------
	# methods

	def Selected(self):
		st=SYSTEMTIME()
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETCURSEL, 0, byref(st)):
			raise "could not retrieve selected item"
		return st
		
	def IsLocaleFirstDayOfWeek(self):
		result=self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETFIRSTDAYOFWEEK, 0, 0)
		if HIWORD(result): return False
		return True

	def GetFirstDayOfWeek(self):
		return LOWORD(self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETFIRSTDAYOFWEEK, 0, 0))
		
	def SetFirstDayOfWeek(self, n):
		return LOWORD(self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETFIRSTDAYOFWEEK, 0, n))
		
	def GetMaxSelCount(self):
		return self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMAXSELCOUNT, 0, 0)
		
	def GetMaxTodayWidth(self):
		return self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMAXTODAYWIDTH, 0, 0)
    
	def GetMinRequiredSize(self):
		rc=RECT()
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMINREQRECT, 0, byref(rc)):
			raise "could not retrieve min required size"
			return rc
	
	def GetMonthDelta(self):
		return self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMONTHDELTA, 0, 0)
	
	def GetMonthRange(self, visible=True):
		st1=SYSTEMTIME()
		st2=SYSTEMTIME()
		arrSt=(SYSTEMTIME*2)(st1, st2)
		result=self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMONTHRANGE, GMR_DAYSTATE, byref(arrSt))
		return result, st1, st2
		
	def GetVisibleMonthRange(self):
		st1=SYSTEMTIME()
		st2=SYSTEMTIME()
		arrSt=(SYSTEMTIME*2)(st1, st2)
		result=self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMONTHRANGE, GMR_VISIBLE, byref(arrSt))
		return result, st1, st2
		
	def GetRange(self):
		st1=SYSTEMTIME()
		st2=SYSTEMTIME()
		arrSystime=(SYSTEMTIME*2)(st1, st2)
		result=self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETRANGE, 0, byref(arrSystime))
		out=[None, None]
		if result & GDTR_MIN:
			out[0]=st1
		if result & GDTR_MAX:
			out[1]=st2
		return out
	
	def GetSelectedRange(self):
		st1=SYSTEMTIME()
		st2=SYSTEMTIME()
		arrSt=(SYSTEMTIME*2)(st1, st2)
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETSELRANGE, 0, byref(arrSystime)):
			raise "could not retrieve selected range"
		return st1, st2

	def GetToday(self):
		st=SYSTEMTIME()
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETTODAY, 0, byref(st)):
			raise "could not retrieve today"
		return st
	
	def HitTest(self, x, y):
		ht=MCHITTESTINFO()
		ht.cbSize=sizeof(ht)
		ht.pt.x=x
		ht.pt.y=y
		self.SendMessage(self.Hwnd,
				self.Msg.MCM_HITTEST, 0, byref(ht))
		
		flag=False
		out=[None, ]
		if ht.uHit & MCHT_TITLE: out.append('title')
		if ht.uHit & MCHT_CALENDAR: out.append('calendar')
		if ht.uHit & MCHT_TODAYLINK: out.append('todaylink')
		if ht.uHit & MCHT_NEXT: out.append('next')
		if ht.uHit & MCHT_PREV: out.append('prev')
		if ht.uHit & MCHT_NOWHERE: out.append('nowhere')
		if ht.uHit & MCHT_TITLEBK : out.append('titlebk')
		if ht.uHit & MCHT_TITLEMONTH: out.append('titlemonth')
		if ht.uHit & MCHT_TITLEYEAR: out.append('titleyear')
		if ht.uHit & MCHT_TITLEBTNNEXT: out.append('titlebtnnext')
		if ht.uHit & MCHT_TITLEBTNPREV: out.append('titlebtnprev')
		if ht.uHit & MCHT_CALENDARBK: out.append('calendarbk')
		if ht.uHit & MCHT_CALENDARDATE:
			flag=True
			out.append('calendardate')
		if ht.uHit & MCHT_CALENDARDATENEXT: out.append('calendardatenext')
		if ht.uHit & MCHT_CALENDARDATEPREV: out.append('calendardateprev')
		if ht.uHit & MCHT_CALENDARDAY: 		
			flag=True
			out.append('calendardate')
		if ht.uHit & MCHT_CALENDARWEEKNUM: 
			flag=True
			out.append('calendarweeknum')
		if ht.uHit & MCHT_TITLE: out.append('title')
		if flag: out[0]=ht.st
		return out

	def Select(self):
		st=SYSTEMTIME()
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETCURSEL, 0, byref(st)):
			raise "could not select date"
	
	def SelectRange(self, systemtimeLow, systemtimeHi):
		arrSt=(SYSTEMTIME*2)(systemtimeLow, systemtimeHi)
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETSELRANGE, 0, byref(arrSt)):
			raise "could not select range"
		
	def SetMaxSelCount(self, n):
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMAXSELCOUNT, n, 0):
			raise "could not set max sel count"
	
	def SetMonthDelta(self, n):
		return self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMONTHDELTA, n, 0)

	def SetRange(self, systemtimeMin, systemtimeMax):
		arrSt=(SYSTEMTIME*2)()
		flag=0
		if systemtimeMin:
			arrSt[0]=systemtimeMin
			flag |= GDTR_MIN
		if systemtimeMax:
			arrSt[0]=systemtimeMax
			flag |= GDTR_MAX
		if not self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETRANGE, flag, byref(arrSt)):
					raise "could not set range"
	
	def SetToday(self, systemtime):
		 self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETRANGE, flag, byref(systime))
	
	def GetBkColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMCCOLOR, 0, MCSC_BACKGROUND)
		if result <0:	
			raise "could not retrieve background color"
		return result

	def GetMonthBkColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMCCOLOR, 0, MCSC_MONTHBK)
		if result <0:	
			raise "could not retrieve month background color"
		return result

	def GetTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMCCOLOR, 0, MCSC_TEXT)
		if result <0:	
			raise "could not retrieve text color"
		return result

	def GetTitleTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMCCOLOR, 0, MCSC_TITLETEXT)
		if result <0:	
			raise "could not retrieve title text color"
		return result

	def GetTrailingTextColor(self):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_GETMCCOLOR, 0, MCSC_TRAILINGTEXT)
		if result <0:	
			raise "could not retrieve trailing text color"
		return result

	def SetBkColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMCCOLOR, colorref, MCSC_BACKGROUND)
		if result <0:	
			raise "could not set background color"
		return result

	def SetMonthBkColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMCCOLOR, colorref, MCSC_MONTHBK)
		if result <0:	
			raise "could not set month background color"
		return result

	def SetTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMCCOLOR, colorref, MCSC_TEXT)
		if result <0:	
			raise "could not set text color"
		return result

	def SetTitleTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMCCOLOR, colorref, MCSC_TITLETEXT)
		if result <0:	
			raise "could not set title text color"
		return result

	def SetTrailingTextColor(self, colorref):
		result= self.SendMessage(self.Hwnd,
				self.Msg.MCM_SETMCCOLOR, 0, MCSC_TRAILINGTEXT)
		if result <0:	
			raise "could not set trailing text color"
		return result	
			


#*******************************************************************************
#*******************************************************************************

class Monthcal(MonthcalMethods,control.BaseControl, ControlMethods):
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysMonthCal32", "", x, y, w, h, *styles)								


class MonthcalFromHandle(MonthcalMethods, control.ControlFromHandle,  ControlMethods):
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd,  *styles)
						

#***********************************************
MCM_FIRST = 4096
MCN_FIRST   = UINT_MAX-750
NM_FIRST = UINT_MAX

class Styles:
	MCS_DAYSTATE        = 1
	MCS_MULTISELECT     = 2
	MCS_WEEKNUMBERS     = 4
	MCS_NOTODAYCIRCLE   = 8
	MCS_NOTODAY         = 16

	
	WS_CLIENT_NOTIFYSELCHANGE = 1
	WS_CLIENT_NOTIFYSELECT = 2

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['MCS_', ]

	


class Msgs: 
	MCM_GETCURSEL       = MCM_FIRST + 1
	MCM_SETCURSEL       = MCM_FIRST + 2
	MCM_GETMAXSELCOUNT  = MCM_FIRST + 3
	MCM_SETMAXSELCOUNT  = MCM_FIRST + 4
	MCM_GETSELRANGE     = MCM_FIRST + 5
	MCM_SETSELRANGE     = MCM_FIRST + 6
	MCM_GETMONTHRANGE   = MCM_FIRST + 7
	MCM_SETDAYSTATE     = MCM_FIRST + 8
	MCM_GETMINREQRECT   = MCM_FIRST + 9
	MCM_SETCOLOR            = MCM_FIRST + 10
	MCM_GETCOLOR            = MCM_FIRST + 11
	MCM_SETTODAY    = MCM_FIRST + 12
	MCM_GETTODAY    = MCM_FIRST + 13
	MCM_SETFIRSTDAYOFWEEK = MCM_FIRST + 15
	MCM_GETFIRSTDAYOFWEEK = MCM_FIRST + 16
	MCM_GETRANGE = MCM_FIRST + 17
	MCM_SETRANGE = MCM_FIRST + 18
	MCM_GETMONTHDELTA = MCM_FIRST + 19
	MCM_SETMONTHDELTA = MCM_FIRST + 20
	MCM_GETMAXTODAYWIDTH = MCM_FIRST + 21

	MCN_SELCHANGE       = MCN_FIRST + 1
	MCN_GETDAYSTATE     = MCN_FIRST + 3
	MCN_SELECT          = MCN_FIRST + 4

	NM_RELEASEDCAPTURE     =   NM_FIRST-16

Msgs.__dict__.update(control.control_msgs.__dict__)


MCSC_BACKGROUND   = 0   # the background color (between months)
MCSC_TEXT         = 1   # the dates
MCSC_TITLEBK      = 2   # background of the title
MCSC_TITLETEXT    = 3
MCSC_MONTHBK      = 4   # background within the month cal
MCSC_TRAILINGTEXT = 5   # the text color of header & trailing days

GMR_VISIBLE     = 0       # visible portion of display
GMR_DAYSTATE    = 1       # above plus the grayed out parts of
                           # partially displayed months

GDTR_MIN       = 1
GDTR_MAX       = 2

MCHT_TITLE         = 65536
MCHT_CALENDAR      = 131072
MCHT_TODAYLINK     = 196608

MCHT_NEXT          = 16777216  # these indicate that hitting
MCHT_PREV          = 33554432  # here will go to the next/prev month
MCHT_NOWHERE       = 0

MCHT_TITLEBK            = MCHT_TITLE
MCHT_TITLEMONTH         = MCHT_TITLE | 1
MCHT_TITLEYEAR          = MCHT_TITLE | 2
MCHT_TITLEBTNNEXT       = MCHT_TITLE | MCHT_NEXT | 3
MCHT_TITLEBTNPREV       = MCHT_TITLE | MCHT_PREV | 3

MCHT_CALENDARBK         = MCHT_CALENDAR
MCHT_CALENDARDATE       = MCHT_CALENDAR | 1
MCHT_CALENDARDATENEXT= MCHT_CALENDARDATE | MCHT_NEXT
MCHT_CALENDARDATEPREV   = MCHT_CALENDARDATE | MCHT_PREV
MCHT_CALENDARDAY        = MCHT_CALENDAR | 2
MCHT_CALENDARWEEKNUM    = MCHT_CALENDAR | 3

LOCALE_IFIRSTDAYOFWEEK        = 4108



class MCHITTESTINFO(Structure):
	_fields_ = [("cbSize", UINT),
					("pt", POINT),
					("uHit", UINT),
					("st", SYSTEMTIME)]

class NMSELCHANGE(Structure):
	_fields_ = [("nmhdr", NMHDR),
					("stSelStart", SYSTEMTIME),
					("stSelEnd", SYSTEMTIME)]