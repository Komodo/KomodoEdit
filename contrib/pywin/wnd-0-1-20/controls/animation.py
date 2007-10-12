
from wnd.wintypes import MAKELONG, InitCommonControlsEx
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

ICC_ANIMATE_CLASS	      = 128 
InitCommonControlsEx(ICC_ANIMATE_CLASS)
#***************************************************


class AnimationMethods:
	#-----------------------------------------------------------------	
	# message handler
	def onMESSAGE(self, hwnd, msg, wp, lp):
		# Not shure if this is necessary
				
		if msg==self.Msg.WM_DESTROY:	
			try: self.CloseAnim()
			except: pass
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# methods
	def OpenAnim(self, path, hInstance=0):
		#try: self.CloseAnim()
		#except: pass
		if not self.SendMessage(self.Hwnd, self.Msg.ACM_OPEN, hInstance, path):
			raise "could not open animation"
				
	def CloseAnim(self):
		if not self.SendMessage(self.Hwnd, self.Msg.ACM_OPEN, 0, 0):
			raise "could not close animation"
			
	def PlayAnim(self, repeat=-1, start=0, stop=-1):
		if not self.SendMessage(self.Hwnd, self.Msg.ACM_PLAY, repeat, MAKELONG(start, stop)):
			raise "could not play animation"
		
	def StopAnim(self):
		if not self.SendMessage(self.Hwnd, self.Msg.ACM_STOP, 0, 0):
			raise "could not stop animation"
		
	def Close(self): 
		try: self.CloseAnimation()
		except: pass
		ControlMethods.Close(self)
	
#*********************************************************************	

class Styles:
	ACS_CENTER	=     1
	ACS_TRANSPARENT	= 2
	ACS_AUTOPLAY	=   4
	ACS_TIMER	=     8

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['ACS_', ]


class Msgs: 
	WM_USER = 1024
	ACM_OPEN	= WM_USER + 100
	ACM_PLAY	= WM_USER + 101
	ACM_STOP	= WM_USER + 102
	
Msgs.__dict__.update(control.control_msgs.__dict__)


class Animation(AnimationMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysAnimate32", "", x, y, w, h, *styles)
		


class AnimationFromHandle(AnimationMethods, control.ControlFromHandle, ControlMethods):
	Style= Styles
	Msg= Msgs 	
	
	def __init__(self, hwnd, *styles):
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		



#***********************************************
