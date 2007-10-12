"""
LAST VISITED
	18.03.05

"""



from wnd.wintypes import (user32,
													byref,
													POINT,
													LOWORD, 
													HIWORD,
													MAKELONG,
													DWORD,)
from wnd import fwtypes as fw
from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods

#***********************************************
class TextinMethods:
	
		#--------------------------------------------------------------------
	# message handlers
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_COMMAND:
					notify = HIWORD(msgr.wParam)
					if notify == self.Msg.EN_CHANGE:
						self.onMSG(hwnd, "change", 0, 0)
					elif notify == self.Msg.EN_UPDATE:
						self.onMSG(hwnd, "update", 0, 0)
					elif notify == self.Msg.EN_MAXTEXT:
						self.onMSG(hwnd, "maxtext", 0, 0)
					elif notify == self.Msg.EN_ERRSPACE:
						self.onMSG(hwnd, "errspace", 0, 0)
				return 0		
				
		elif msg==self.Msg.WM_CHAR:
			if wp==VK_RETURN:
				self.onMSG(hwnd, "return", 0, 0)
				if not self.GetStyleL('style') & 4096:	# ES_WANTRETURN
					return 0
		elif msg==self.Msg.WM_CONTEXTMENU:
			
			if self.onMSG(hwnd, "contextmenu", wp, 0): return 0
		elif msg==self.Msg.WM_LBUTTONDBLCLK:
			self.onMSG(hwnd, "lmbdouble", wp, (LOWORD(lp), HIWORD(lp)))
		elif msg==self.Msg.WM_LBUTTONUP:
			self.onMSG(hwnd, "lmbup", wp, (LOWORD(lp), HIWORD(lp)))
		elif msg==self.Msg.WM_RBUTTONUP:
			result=self.onMSG(hwnd, "rmbup", wp, (LOWORD(lp), HIWORD(lp)))
			if result==False: return 0
		elif msg==self.Msg.WM_SETFOCUS:
			self.DefWindowProc(hwnd, msg, wp, lp)
			self.onMSG(hwnd, "setfocus", wp, 0)
			return 0
		elif msg==self.Msg.WM_KILLFOCUS:
			self.DefWindowProc(hwnd, msg, wp, lp)
			self.onMSG(hwnd, "killfocus", wp, 0)
			return 0
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			

	
	#**************************************************************************************	
	
	def __len__(self): 
		return self.SendMessage(self.Hwnd, self.Msg.EM_LINELENGTH, 0, 0)
			
	def __iter__(self):
		for i in self.GetText():
			yield i
	
	def SetTextMax(self, n):
		self.SendMessage(self.Hwnd, self.Msg.EM_LIMITTEXT, n, 0)

	def GetTextMax(self):
		return self.SendMessage(self.Hwnd, self.Msg.EM_GETLIMITTEXT, 0, 0)

	def SetPasswordChar(self, char):
		# changes are not reflected correctly so.. gettext/settext
		text = self.GetText()
		self.SendMessage(self.Hwnd, self.Msg.EM_SETPASSWORDCHAR, ord(char), 0)
		self.SetText(text)
		
	def GetPasswordChar(self):
		result = self.SendMessage(self.Hwnd, self.Msg.EM_GETPASSWORDCHAR, 0, 0)
		if result: return chr(result)
		
	def GetSelectedText(self):
		start, stop=self.GetSelectedIndex()
		if start != stop:
			return  self.GetText()[start : stop]
		
	def GetSelectedIndex(self):
		start = DWORD()
		stop = DWORD()
		self.SendMessage(self.Hwnd, self.Msg.EM_GETSEL, byref(start), byref(stop))
		return start.value, stop.value
	
	def ReplaceSelected(self, text, canundo=True):
		if canundo:  canundo= 1
		else:  canundo= 0
		self.SendMessage(self.Hwnd, self.Msg.EM_REPLACESEL, canundo, text)

	def Select(self, start=0, stop= -1):
		#Todo: rewrite to python slices. ??
		self.SendMessage(self.Hwnd, self.Msg.EM_SETSEL, start, stop)
		
	def Deselect(self):
		self.SendMessage(self.Hwnd, self.Msg.EM_SETSEL, -1, 0)

		
	def PosFromChar(self, i):
		result= self.SendMessage(self.Hwnd, self.Msg.EM_POSFROMCHAR, i,0)
		return LOWORD(result), HIWORD(result)
	
	def CharFromPos(self, x, y):
		result = self.SendMessage(self.Hwnd, self.Msg.EM_CHARFROMPOS, 0, MAKELONG(x, y))
		return LOWORD(result)


	def Copy(self):
		self.SendMessage(self.Hwnd, self.Msg.WM_COPY, 0, 0)
	
	def Cut(self):
		self.SendMessage(self.Hwnd, self.Msg.WM_CUT, 0, 0)
	
	def Clear(self):
		self.SendMessage(self.Hwnd, self.Msg.WM_CLEAR, 0, 0)
	11
	def Paste(self):
		self.SendMessage(self.Hwnd, self.Msg.WM_PASTE, 0, 0)
	
	def CanUndo(self):
		return bool(self.SendMessage(self.Hwnd, self.Msg.EM_CANUNDO, 0, 0))
		
	
	def ClearUndo(self):
		if self.CanUndo():
			self.SendMessage(self.Hwnd, self.Msg.EM_EMPTYUNDOBUFFER, 0, 0)
			return True
		return False
		
	def Undo(self):
		if self.CanUndo():
			self.SendMessage(self.Hwnd, self.Msg.EM_UNDO, 0, 0)
			return True
		return False

	def IsDirty(self):
		if self.SendMessage(self.Hwnd, self.Msg.EM_GETMODIFY, 0, 0):
			return True
		return False

	def SetDirty(self):
		self.SendMessage(self.Hwnd, self.Msg.EM_SETMODIFY, 1, 0)
	
	def SetClean(self):
		self.SendMessage(self.Hwnd, self.Msg.EM_SETMODIFY, 0, 0)
	
	#**********************************************************************************	
	
	def SetStyleL(self, offset, style):
		if offset=='style':
			ES_READONLY = 2048
			fReadonly = style & ES_READONLY
			if self.GetStyleL('style') & ES_READONLY != fReadonly:
				flag=0
				if fReadonly: flag=1
				self.SendMessage(self.Hwnd, self.Msg.EM_SETREADONLY, flag, 0)
					
	def SetStyle(self, *styles):
		out = []
		fReadonly=None
		for i in styles:
			if 'readonly' in i: fReadonly = i
			else:	out.append(i)
		if fReadonly:
			flag=1
			if fReadonly[0]=='-': flag=0
			if fReadonly[0]=='~':
				ES_READONLY = 2048
				if self.GetStyleL('style') & ES_READONLY:
					flag=0
			self.SendMessage(self.Hwnd, self.Msg.EM_SETREADONLY, flag, 0)
		if out:
			ControlMethods.SetStyle(self, *out)
				


#**************************************************************************				

class Textin(TextinMethods, control.BaseControl, ControlMethods):
	
	
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, 'Edit', title, x, y, w, h, *styles)				


class TextinFromHandle(TextinMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
				
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		


#***************************************************

class Styles:
	ES_LEFT        = 0
	ES_CENTER      = 1
	ES_RIGHT       = 2
	ES_UPPERCASE   = 8
	ES_LOWERCASE   = 16
	ES_PASSWORD    = 32
	ES_AUTOHSCROLL = 128
	ES_NOHIDESEL   = 256
	ES_OEMCONVERT  = 1024
	ES_READONLY    = 2048
	ES_NUMBER      = 8192
			
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['ES_', ]


class Msgs: 
	WM_CUT              = 768
	WM_COPY             = 769
	WM_PASTE            = 770
	WM_CLEAR            = 771
	
	EM_GETSEL              = 176
	EM_SETSEL              = 177
	EM_SCROLLCARET         = 183
	EM_GETMODIFY           = 184
	EM_SETMODIFY           = 185
	EM_LINELENGTH          = 193
	EM_REPLACESEL          = 194
	EM_LIMITTEXT           = 197
	EM_CANUNDO             = 198
	EM_UNDO                = 199
	EM_SETPASSWORDCHAR     = 204	 # singleline only
	EM_EMPTYUNDOBUFFER     = 205
	EM_GETFIRSTVISIBLELINE = 206
	EM_SETREADONLY         = 207
	EM_GETPASSWORDCHAR     = 210	 # singleline only
	EM_GETLIMITTEXT        = 213
	EM_POSFROMCHAR         = 214
	EM_CHARFROMPOS         = 215
	
	
	EN_SETFOCUS  = 256
	EN_KILLFOCUS = 512
	EN_CHANGE    = 768
	EN_UPDATE    = 1024
	EN_ERRSPACE  = 1280
	EN_MAXTEXT   = 1281
	EN_HSCROLL   = 1537
	EN_VSCROLL   = 1538

			
Msgs.__dict__.update(control.control_msgs.__dict__)



		

#************************************************

VK_RETURN   = 13
VK_SPACE    = 32
VK_TAB      = 9

		
#***********************************************
