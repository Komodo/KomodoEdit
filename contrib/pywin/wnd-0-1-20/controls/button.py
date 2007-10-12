

"""
LAST VISITED 19.02.05



TODO
 'ownerdraw' focus rect. 
		Sample: a Button sizing an ownerdrawn Button on click and then setting focus to it. This will currently mess up any focus rect drawing.



NOTES
 'ownerdraw' buttons do not trigger
 WM_DRAWITEM on WM_LBUTTONDBLCLK

"""




from wnd import fwtypes as fw
from wnd.wintypes import DRAWITEMSTRUCT
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class ButtonMethods:
	#-----------------------------------------------------------------	
	# message handler	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_DRAWITEM:
					di=DRAWITEMSTRUCT.from_address(msgr.lParam)
					self.onMSG(hwnd, "drawitem", 0, di)
					return 1
				elif msgr.msg==self.Msg.WM_COMMAND:
					self.onMSG(hwnd, "command", 0, 0)
			return 0
		
		elif msg==self.Msg.WM_LBUTTONDBLCLK:
			# required to trigger ownerdraw messages 
			if self.GetStyleL('style') & self.Style.BS_OWNERDRAW:
				self.DefWindowProc(self.Hwnd, self.Msg.WM_LBUTTONDOWN, wp, lp)
				return 0
		elif msg==self.Msg.WM_SETFOCUS: self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS: self.onMSG(hwnd, "killfocus", wp, lp)
		elif msg==self.Msg.WM_DESTROY: self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# button methods
		
	def Click(self):	self.SendMessage(self.Hwnd, self.Msg.BM_CLICK, 0, 0)
	
	def IsPushed(self):
		BST_PUSHED        = 4
		state= self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0)
		return bool(state & BST_PUSHED)
		
	def Push(self):
		BST_PUSHED        = 4
		state= self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0)
		if state & BST_PUSHED: return False
		self.SendMessage(self.Hwnd, self.Msg.BM_SETSTATE, state|BST_PUSHED, 0)
		return True

	def Release(self):
		BST_PUSHED        = 4
		state= self.SendMessage(self.Hwnd, self.Msg.BM_GETSTATE, 0, 0)
		if not state & BST_PUSHED: return False
		self.SendMessage(self.Hwnd, self.Msg.BM_SETSTATE, 0 , 0)
		return True
	
	def SetIcon(self, Icon):
		if not Icon:
			result= self.SendMessage(self.Hwnd, self.Msg.BM_SETIMAGE, IMAGE_ICON, 0)
		else:
			result= self.SendMessage(self.Hwnd, self.Msg.BM_SETIMAGE, IMAGE_ICON, Icon.handle)
		if result: return result

	def GetIcon(self):
		result= self.SendMessage(self.Hwnd, self.Msg.BM_GETIMAGE, IMAGE_ICON, 0)
		if result: return result

	def SetBitmap(self, Bitmap):
		if Bitmap:
			result= self.SendMessage(self.Hwnd, self.Msg.BM_SETIMAGE, IMAGE_BITMAP, Bitmap.handle)
		else:
			result= self.SendMessage(self.Hwnd, self.Msg.BM_SETIMAGE, IMAGE_BITMAP, 0)
		if result: return result

	def GetBitmap(self):
		result= self.SendMessage(self.Hwnd, self.Msg.BM_GETIMAGE, IMAGE_BITMAP, 0)
		if result: return result

	
#******************************************************

class Styles:
	BS_PUSHBUTTON      = 0
	BS_DEFPUSHBUTTON   = 1
					
	BS_OWNERDRAW       = 11
	BS_ICON            = 64
	BS_BITMAP          = 128
	BS_LEFT            = 256
	BS_RIGHT           = 512
	BS_CENTER          = 768
	BS_TOP             = 1024
	BS_BOTTOM          = 2048
	BS_VCENTER         = 3072
	BS_MULTILINE       = 8192
	BS_NOTIFY          = 16384
	BS_FLAT            = 32768

	#BS_PUSHLIKE        = 4096

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['BS_', ]

class Msgs: 
	BM_CLICK    = 245
	BM_GETSTATE = 242
	BM_SETSTATE = 243
	BM_SETSTYLE = 244
	BM_GETIMAGE = 246
	BM_SETIMAGE = 247
Msgs.__dict__.update(control.control_msgs.__dict__)



class Button(ButtonMethods, control.BaseControl, ControlMethods):
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "Button", title, x, y, w, h, *styles)
		

class ButtonFromHandle(ButtonMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd,*styles)	


	
		
#***********************************************

IMAGE_BITMAP      = 0
IMAGE_ICON        = 1
