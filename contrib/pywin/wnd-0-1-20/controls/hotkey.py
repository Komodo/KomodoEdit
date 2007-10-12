

from wnd.wintypes import(HIBYTE, 
												LOBYTE, 
												MAKEWORD,
												InitCommonControlsEx)
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
from wnd.consts import vk
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_HOTKEY_CLASS       = 64
InitCommonControlsEx(ICC_HOTKEY_CLASS)

#***************************************************		

class HotkeyMethods:
			
	def GetHotkey(self):
		result = self.SendMessage(self.Hwnd, self.Msg.HKM_GETHOTKEY, 0, 0)
		if result:
			fMod=HIBYTE(result)
			out=[LOBYTE(result), ]
			for name, value in MODKEYS.items():
				if fMod & value:
					out.append(name)
			return out

	def SetHotkey(self, vk, *modkeys):
		fMod=0
		for i in modkeys:
			try: fMod |= MODKEYS[i]
			except: raise ValueError("invalid modkey flag: %s" % i)
		self.SendMessage(self.Hwnd, self.Msg.HKM_SETHOTKEY, 
		MAKEWORD(vk, fMod), 0)

	def SetInvalidModkeys(self, *modkeys):
		flags={'none':1,'shift':2,'control':4,'alt':8,'shift-control':16,
					'shift-alt':32,'control-alt':64,'shift-control-alt':128, 'all': 254}		
		fInv=0
		for i in modkeys:
			try: fInv |= flags[i]
			except: raise ValueError("invalid inv flag: %s" % i)
		self.SendMessage(self.Hwnd, 
				self.Msg.HKM_SETRULES, fInv, 0)	



#*********************************************

class Styles: pass

Styles.__dict__.update(control.control_styles.__dict__)
#Styles.prefix += []

class Msgs: 
	WM_USER=1024
	
	HKM_SETHOTKEY   = WM_USER + 1
	HKM_GETHOTKEY   = WM_USER + 2
	HKM_SETRULES    = WM_USER + 3

Msgs.__dict__.update(control.control_msgs.__dict__)


class Hotkey(HotkeyMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		#styles += 'subclass',
		control.BaseControl.__init__(self, parent, "msctls_hotkey32", "", x, y, w, h, *styles)
		self._client_modkeyFlags={'shift':1,'control':2,'alt':4,'ext':8}
		

class HotkeyFromHandle(HotkeyMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		

	

#***********************************************
MODKEYS= {'shift':1,'control':2,'alt':4,'ext':8}


