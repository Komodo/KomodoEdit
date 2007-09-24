
from wnd.wintypes import (RECT, 
													Structure,
													byref,
													LONG,
													LOWORD,
													HIWORD,
													MAKELONG,
													InitCommonControlsEx)
from wnd import gdi
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#*************************************************
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_PROGRESS_CLASS     = 32
InitCommonControlsEx(ICC_PROGRESS_CLASS)


class ProgressbarMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		# paint the progressbar from scratch to display text
		if msg==self.Msg.WM_PAINT:
			if not self._client_text: return
			
			hDC, ps=self.BeginPaint()
			dc=gdi.DCFromHandle(hDC)
			dc.SetBkMode('transparent')
			pos, stop=self.GetPosition(), self.GetRange()[1]
			rc=self.GetClientRect()
						
			# paint left/bottom side of the bar
			if self.GetStyleL('style') & self.Style.PBS_VERTICAL:
				rcBar=RECT(0, rc.bottom-rc.top -(pos*rc.bottom/stop), rc.right, rc.bottom)
			else:
				rcBar=RECT(0, 0, pos*rc.right/stop, rc.bottom)
			if not rcBar.IsEmpty():
				rg=gdi.RectRegion(rcBar)
				dc.SetClipRegion(rg)		
				brFg=gdi.SolidBrush(self._client_clrBar)
				brFg.FillRegion(dc, rg)
				brFg.Close()
				dc.SetTextColor(self._client_clrTextHi)
				font= dc.GetFont()
				font.DrawText(dc, rc, self._client_text, 'center', 'vcenter', 'singleline')
				dc.SetClipRegion(None)
				font.Close()
				rg.Close()
				
			# paint right/top side of the bar
			if self.GetStyleL('style') & self.Style.PBS_VERTICAL:
				rcBar.top=rc.top
				rcBar.bottom= rc.bottom-rc.top -(pos*rc.bottom/stop)-1
			else:
				rcBar.left=pos*rc.right/stop+1
				rcBar.right=rc.right
			if not rcBar.IsEmpty():
				rg=gdi.RectRegion(rcBar)
				brBk=gdi.SolidBrush(self._client_clrBk)
				brBk.FillRegion(dc, rg)
				brBk.Close()
				dc.SetClipRegion(rg)
				dc.SetTextColor(self._client_clrText)
				font= dc.GetFont()
				font.DrawText(dc, rc, self._client_text, 'center', 'vcenter', 'singleline')
				dc.SetClipRegion(None)
				rg.Close()
											
			dc.Close()
			self.EndPaint(ps)
			return 0
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# progressbar methods
		
	def SetText(self, text): self._client_text=text or None
	def GetText(self): return self._client_text
	
	def SetRange(self, low=0, high=100): 
		result = self.SendMessage(self.Hwnd, self.Msg.PBM_SETRANGE, 0, MAKELONG(low, high))
		return (LOWORD(result),
					HIWORD(result))
		# PBM_SETRANGE32 will not work here
		#result = self.SendMessage(self.Hwnd, self.Msg.PBM_SETRANGE32, low, high)
		#return (LOWORD(result),
		#			HIWORD(result))
	
	def GetRange(self): 
		pbr = PBRANGE()
		self.SendMessage(self.Hwnd, self.Msg.PBM_GETRANGE, 0, byref(pbr))
		return (pbr.iLow, pbr.iHigh)

	def SetPosition(self, n): 
		return self.SendMessage(self.Hwnd, self.Msg.PBM_SETPOS, n, 0)
	
	def GetPosition(self): 
		return self.SendMessage(self.Hwnd, self.Msg.PBM_GETPOS, 0, 0)
		
	def SetStep(self, n): 
		return self.SendMessage(self.Hwnd, self.Msg.PBM_SETSTEP, n, 0)
		
	def OffsetPosition(self, n): 
		return self.SendMessage(self.Hwnd, self.Msg.PBM_DELTAPOS, n, 0)
	
	def Step(self): 
		return self.SendMessage(self.Hwnd, self.Msg.PBM_STEPIT, 0, 0)
			
	def SetBarColor(self, colorref):
		CLR_DEFAULT = 0x4278190080
		if colorref==None: 
			colorref=CLR_DEFAULT
			self._client_clrBar=gdi.GetSysColor('highlight')
		else:	self._client_clrBar=colorref
		return self.SendMessage(self.Hwnd, self.Msg. PBM_SETBARCOLOR, 0, colorref)
			
	def SetBkColor(self, colorref):
		CLR_DEFAULT = 0x4278190080
		if colorref==None: 
			colorref=CLR_DEFAULT
			self._client_clrBk=gdi.GetSysColor('btnface')
		else: self._client_clrBk=colorref
		return self.SendMessage(self.Hwnd, self.Msg. PBM_SETBKCOLOR, 0, colorref)
		
	def SetTextColor(self, colorref):
		prevcolor=self._client_clrText
		if colorref==None:
			self._client_clrText=gdi.GetSysColor('btntext')
		else: self._client_clrText=colorref
		return prevcolor
		
	def SetTextHilightColor(self, colorref):
		prevcolor=self._client_clrTextHi
		if colorref==None:
			self._client_clrTextHi=gdi.GetSysColor('highlighttext')
		else: self._client_clrTextHi=colorref
		return prevcolor


#*********************************************************************
WM_USER = 1024

class Styles:
	PBS_SMOOTH     = 1
	PBS_VERTICAL   = 4
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['PBS_', ]


class Msgs: 
	PBM_SETRANGE    = WM_USER + 1
	PBM_SETPOS      = WM_USER + 2
	PBM_DELTAPOS    = WM_USER + 3
	PBM_SETSTEP     = WM_USER + 4
	PBM_STEPIT      = WM_USER + 5
	
	PBM_GETRANGE    = WM_USER + 7     # wParam = return (TRUE ? low : high). lParam = PPBRANGE or NULL
	PBM_GETPOS      = WM_USER + 8
	PBM_SETBKCOLOR  = 8193  # lParam = bkColor
	PBM_SETBARCOLOR = WM_USER + 9     # lParam = bar color
	
	# -> Requires commctrl v 4.70.
	PBM_SETRANGE32  = WM_USER + 6  # lParam = high, wParam = low

Msgs.__dict__.update(control.control_msgs.__dict__)	



class Progressbar(ProgressbarMethods, control.BaseControl, ControlMethods):
	
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		

		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "msctls_progress32", '', x, y, w, h, *styles)
		self._client_clrBar=gdi.GetSysColor('highlight')
		self._client_clrBk=gdi.GetSysColor('btnface')
		self._client_clrText=gdi.GetSysColor('btntext')
		self._client_clrTextHi=gdi.GetSysColor('highlighttext')
		self._client_text=title or None

		
class ProgressbarFromHandle(ProgressbarMethods, control.ControlFromHandle, ControlMethods):
		
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self._client_clrBar=gdi.GetSysColor('highlight')
		self._client_clrBk=gdi.GetSysColor('btnface')
		self._client_clrText=gdi.GetSysColor('btntext')
		self._client_clrTextHi=gdi.GetSysColor('highlighttext')
		self._client_text=title or None


#***********************************************

class PBRANGE(Structure):
	_fields_ = [("iLow", LONG),
					("iHigh", LONG)]