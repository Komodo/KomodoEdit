"""
LAST VISITED
	18.03.05

NOT IMPLEMENTED
	
	EM_FMTLINES
	EM_GETHANDLE
	EM_GETIMESTATUS
	EM_SETHANDLE
	EM_SETIMESTATUS
	EM_SETTABSTOPS
	EM_SETWORDBREAKPROC


	# not intersting, sned only when the user hits the thumb,
	# and not when the it's dragged
	# to handle this use custom scrollbars for the editbox
	EN_VSCROLL
	EN_HSCROLL


TODO
	 EM_GETTHUMB allways returns 0	??
	 EM_SCROLLCARET does not seem to have an effect, hints anyone ??

"""


from wnd.wintypes import (user32,
													byref,
													POINT,
													LOWORD, 
													HIWORD,
													MAKELONG,
													DWORD,
													RECT,
													create_string_buffer)

from wnd.controls.textin import TextinMethods 
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
import sre
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
_newline_pat = sre.compile(r'(?<! \r)\n', sre.M)
LINESEP = lambda strng: _newline_pat.subn('\r\n', strng)[0]	


class EditboxMethods(TextinMethods):
	#-----------------------------------------------------------------	
	# message handler 	
	# ...currently taken from TextinMethods
		
	
	#--------------------------------------------------------------
	# methods

	def SetText(self, text):
		if not user32.SetWindowTextA(self.Hwnd, LINESEP(text)):
			raise RuntimeError("could not set text")
	
	def Append(self, text):
		n = self.GetTextLen()
		self.Select(n, n)
		self.ReplaceSelected(LINESEP(text))	

	#-------------------------------------------------------------------
	# lines

	def GetLineCount(self):
		return self.SendMessage(self.Hwnd, self.Msg.EM_GETLINECOUNT, 0, 0)
	
	def GetLineText(self, n):
		if n< 0 or n >= self.GetLineCount():
			raise IndexError("line index out of range': %s" % n)
		length = self.GetLineLen(n) +1 
		p = create_string_buffer(str(length), length)
		self.SendMessage(self.Hwnd, self.Msg.EM_GETLINE, n, p)
		return p.value
		
	def GetLineLen(self, n):
		if n< 0 or n >= self.GetLineCount():
			raise ndexError("line index out of range': %s" % n)
		start = self.SendMessage(self.Hwnd, self.Msg.EM_LINEINDEX, n, 0)
		return self.SendMessage(self.Hwnd, self.Msg.EM_LINELENGTH, start, 0)

	def GetLineIndex(self, n):
		if n < 0 or n >= self.GetLineCount():
			raise ndexError("line index out of range': %s" % n)
		return self.SendMessage(self.Hwnd, self.Msg.EM_LINEINDEX, n, 0)

	def GetFirstVisibleLine(self):
		return self.SendMessage(self.Hwnd, self.Msg.EM_GETFIRSTVISIBLELINE, 0, 0)
	
	def IterLines(self):
		for i in range(self.GetLineCount()):
			yield i
	
	#----------------------------------------------------------------------
	# selecting

	def SelectLines(self, start, stop=None):
		n= self.GetLineCount()
		if start < 0:
			start = n  + start
			if start <0: start=0
		elif start >=n: start=n -1
		if stop==None: stop=start
		elif stop < 0:
			stop = n  + stop
			if stop <0: stop=0
		elif stop >=n: stop=n -1
		if start > stop: 
			start, stop=stop, start
		start=self.GetLineIndex(start)
		stop=self.GetLineIndex(stop) + self.GetLineLen(stop) + 2
		self.Select(start, stop)
		return start, stop
			
	def Scroll(self, hScroll=0, vScroll=0):
		self.SendMessage(self.Hwnd, self.Msg.EM_LINESCROLL, hScroll, vScroll)

	def GetFormatingRect(self):
		rc = RECT()
		self.SendMessage(self.Hwnd, self.Msg.EM_GETRECT, 0, byref(rc))
		return rc
	
	def SetFormatingRect(self, Rect):
		self.SendMessage(self.Hwnd, self.Msg.EM_SETRECT, 0, byref(Rect))

	def Linedown(self):
		#SB_LINEDOWN      = 1
		return LOWORD(self.SendMessage(self.Hwnd, self.Msg.EM_SCROLL, 1, 0))
		
	def Lineup(self):
		#SB_LINEUP      = 0
		return LOWORD(self.SendMessage(self.Hwnd, self.Msg.EM_SCROLL, 0, 0))
		
	def Pagedown(self):
		#SB_LINEDOWN= 3
		return LOWORD(self.SendMessage(self.Hwnd, self.Msg.EM_SCROLL, 3, 0))
		
	def Pageup(self):
		#SB_PAGEUP        = 2
		return LOWORD(self.SendMessage(self.Hwnd, self.Msg.EM_SCROLL, 2, 0))

	#def GetThumbPos(self):
	#	return self.SendMessage(self.Hwnd, self.Msg.EM_GETTHUMB, 0, 0)
	
	#def EnshureVisible(self):
	#	self.SendMessage(self.Hwnd, self.Msg.EM_SCROLLCARET, 0, 0)
		
	

#***********************************************************************************
#***********************************************

class Styles:
	ES_LEFT        = 0
	ES_CENTER      = 1
	ES_RIGHT       = 2
	ES_MULTILINE   = 4
	ES_UPPERCASE   = 8
	ES_LOWERCASE   = 16
	ES_PASSWORD    = 32
	ES_AUTOVSCROLL = 64	 #
	ES_AUTOHSCROLL = 128	#
	ES_NOHIDESEL   = 256	#
	ES_OEMCONVERT  = 1024		# ??
	ES_READONLY    = 2048
	ES_WANTRETURN  = 4096
	ES_NUMBER      = 8192
	

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['ES_', ]
	

class Msgs: 
	EN_SETFOCUS  = 256
	EN_KILLFOCUS = 512
	EN_CHANGE    = 768
	EN_UPDATE    = 1024
	EN_ERRSPACE  = 1280
	EN_MAXTEXT   = 1281
	EN_HSCROLL   = 1537
	EN_VSCROLL   = 1538
	
	WM_CUT              = 768
	WM_COPY             = 769
	WM_PASTE            = 770
	WM_CLEAR            = 771
	
	EM_GETSEL              = 176
	EM_SETSEL              = 177
	EM_SCROLL              = 181
	EM_SCROLLCARET         = 183
	EM_GETMODIFY           = 184
	EM_SETMODIFY           = 185
	EM_GETLINECOUNT        = 186
	EM_LINEINDEX           = 187
	EM_GETRECT             = 178
	EM_SETRECT             = 179
	EM_SETRECTNP           = 180
	EM_LINESCROLL          = 182
	EM_GETMODIFY           = 184
	EM_SETMODIFY           = 185
	EM_GETTHUMB            = 190
	EM_LINELENGTH          = 193
	EM_REPLACESEL          = 194
	EM_GETLINE             = 196
	EM_LIMITTEXT           = 197
	EM_CANUNDO             = 198
	EM_UNDO                = 199
	EM_LINEFROMCHAR        = 201
	EM_EMPTYUNDOBUFFER     = 205
	EM_GETFIRSTVISIBLELINE = 206
	EM_SETREADONLY         = 207
	EM_GETLIMITTEXT        = 213
	EM_POSFROMCHAR         = 214
	EM_CHARFROMPOS         = 215
	
Msgs.__dict__.update(control.control_msgs.__dict__)	

	




class Editbox(EditboxMethods ,control.BaseControl, ControlMethods):
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		

		styles += 'subclass', 'multiline'
		control.BaseControl.__init__(self, parent, "Edit",  LINESEP(title),
		x, y, w, h, *styles)						
		

class EditboxFromHandle(EditboxMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		


