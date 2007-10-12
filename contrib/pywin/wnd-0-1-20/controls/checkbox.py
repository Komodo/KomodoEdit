"""
LAST VISITED: 20.02.05


TODO
'ownerdraw' focus rect. See 'wnd.controls.button'



NOTES
 'ownerdraw' checkboxes do not trigger
 WM_DRAWITEM on WM_LBUTTONDBLCLK
"""


from wnd import fwtypes as fw
from wnd.wintypes import DRAWITEMSTRUCT
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class CheckboxMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				
				if msgr.msg==self.Msg.WM_DRAWITEM:
					di=DRAWITEMSTRUCT.from_address(msgr.lParam)
					if self._client_odState[2]:
						# preprocess selection state changes
						if di.itemAction==di.SELECTCHANGE and not di.itemState & di.SELECTED:
							self._client_odState[0] +=1
							if self._client_odState[0] >= self._client_odState[1]:
								self._client_odState[0]=0
					self.onMSG(hwnd, "drawitem", 0, di)
					return 1
				return 0
				
				elif msgr.msg==self.Msg.WM_COMMAND:
					if self.IsChecked():
						self.onMSG(hwnd, "checked", 0, 0)
					elif self.IsGraychecked():
						self.onMSG(hwnd, "graychecked", 0, 0)
					else:
						self.onMSG(hwnd, "unchecked", 0, 0)
			return 0
	
		elif msg==self.Msg.WM_LBUTTONDBLCLK:
			# required to trigger ownerdraw messages 
			pass
			if self._client_IsOwnerdraw():
				self.DefWindowProc(self.Hwnd, self.Msg.WM_LBUTTONDOWN, wp, lp)
				return 0
		elif msg==self.Msg.WM_SETFOCUS: self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS: self.onMSG(hwnd, "killfocus", wp, lp)
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# checkbox methods
		
	def _client_IsOwnerdraw(self):
		return bool(self.GetStyleL('style') & 11==11)	 #  BS_OWNERDRAW
			
	def IsChecked(self):
		if self._client_IsOwnerdraw():
			return bool(self._client_odState[0]==BST_CHECKED)
		else:
			return bool(self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0) & BST_CHECKED)
			
	def IsGraychecked(self):
		BST_INDETERMINATE = 2
		if self._client_IsOwnerdraw():
			return bool(self._client_odState[0]==BST_INDETERMINATE)
		else:
			return bool(self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0) & BST_INDETERMINATE)
			
	def IsUnchecked(self):
		if not self.IsChecked():
			if not self.IsGraychecked():
				return True
		return False
	
	def Check(self):
		if self.IsChecked(): return False
		BST_CHECKED       = 1
		self.SendMessage(self.Hwnd, self.Msg.BM_SETCHECK, BST_CHECKED, 0)
		self._client_odState[0]=1
		return True
	
	def Graycheck(self):
		if self.IsGraychecked(): return False
		BST_INDETERMINATE = 2
		self.SendMessage(self.Hwnd, self.Msg.BM_SETCHECK, BST_INDETERMINATE, 0)
		if self._client_odState[1]==2:
			self._client_odState[0]=1
		else: 
			self._client_odState[0]=2
		return True
	
	def Uncheck(self):
		if self.IsUnchecked(): return False
		BST_UNCHECKED     = 0
		self.SendMessage(self.Hwnd, self.Msg.BM_SETCHECK, BST_UNCHECKED, 0)
		self._client_odState[0]=0
		return True
	
	def Click(self):
		self.SendMessage(self.Hwnd, self.Msg.BM_CLICK, 0, 0)
	
	#------------------------------------------------------------------
	# overwritten methods
	#
	# GetStyle/SetStyle needs some additional handling
	
	def GetStyle(self):
		"""Returns the style for the checkbox."""
		result = ControlMethods.GetStyle(self)
		if isinstance(result, list):
			if 'auto3state' in result:
				result.remove('checkbox')
			elif 'autocheckbox' in result:
				result.remove('checkbox')
		return result
	
	def SetStyle(self, *styles):
		"""Sets the style for the checkbox.
		Same as the SetStyle method for other controls, except  
		The styles 'checkbox','autocheckbox','3state','auto3state'
		are mutually exclusive. You can not use the flags '-' and
		'~' on them.
		"""
		out = []
		st=('checkbox','autocheckbox','3state','auto3state')
		for i in styles:
			if i in st:
				if i=='checkbox': style = 2
				elif i=='autocheckbox': style = 3
				elif i=='3state': style = 5
				elif i=='auto3state': style = 6
				self.SendMessage(self.Hwnd, self.Msg.BM_SETSTYLE, style, 1)
			else:
				out.append(i)
			if out:
				ControlMethods.SetStyle(self, *out)

	# special method for ownerdraw chexkboxes
	def ODSetStyle(self, nStates, fAutocheck):
		if nStates not in (2, 3): raise ValueError("invalid num states: %s" % nStates)
		self._client_odState[1]=nStates
		self._client_odState[2]=fAutocheck


#********************************************************

class Styles:
	
	BS_OWNERDRAW       = 11
	
	#BS_TEXT            = 0
	BS_CHECKBOX        = 2
	BS_AUTOCHECKBOX    = 3
	BS_3STATE          = 5
	BS_AUTO3STATE      = 6
					
	BS_LEFTTEXT        = 32
	BS_ICON            = 64
	BS_BITMAP          = 128
	BS_LEFT            = 256
	BS_RIGHT           = 512
	BS_CENTER          = 768
	BS_TOP             = 1024
	BS_BOTTOM          = 2048
	BS_VCENTER         = 3072
	BS_PUSHLIKE        = 4096
	BS_MULTILINE       = 8192
	BS_NOTIFY          = 16384
	BS_FLAT            = 32768
	BS_RIGHTBUTTON     = BS_LEFTTEXT


Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['BS_', ]


class Msgs: 
	
	BM_GETCHECK = 240
	BM_SETCHECK = 241
	BM_GETSTATE = 242
	BM_SETSTATE = 243
	BM_SETSTYLE = 244
	BM_CLICK    = 245
	BM_GETIMAGE = 246
	BM_SETIMAGE = 247

Msgs.__dict__.update(control.control_msgs.__dict__)


class Checkbox(CheckboxMethods, control.BaseControl, ControlMethods):
		
	
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		


		# make shure one of the BS_* styles is set
		flag = False
		if 'checkbox' in styles: flag=True
		elif 'autocheckbox' in styles: flag=True
		elif '3state' in styles: flag=True
		elif 'auto3state' in styles: flag=True
		if flag: styles += 'subclass',
		else: styles += 'autocheckbox', 'subclass'
		
		control.BaseControl.__init__(self, parent, 'Button', title, x, y, w, h, *styles)
		
		# ownerdrawn checkboxes do not seem 
		# to provide any state information ??
		self._client_odState=[0, 2, True]	# state / nStstates / fAutocheck
				
	
	
class CheckboxFromHandle(CheckboxMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self._client_odState=[0, 2, True]	# state / nStstates / fAutocheck
						
#***********************************************
