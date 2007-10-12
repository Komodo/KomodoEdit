

from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
from wnd.controls.windowclass import WindowClass, SZ_CONTROL_CLASS
#****************************************************
class Styles: pass

Styles.__dict__.update(control.control_styles.__dict__)
#Styles.prefix += 'ACS_', 

class Msgs: pass

Msgs.__dict__.update(control.control_msgs.__dict__)



class Blank(control.BaseControl, ControlMethods):
	"""Minimal featureless control"""
	
	def __init__(self, parent, ClassOrName, x, y, w, h, *styles):	
		self.Style= Styles
		self.Msg= Msgs 
		
		
		if isinstance(ClassOrName, basestring):
			wc = WindowClass()
			wc.SetClassName(SZ_CONTROL_CLASS % ClassOrName)
			wc.SetCursor()
			wc.SetBackground('window')
		else:
			wc= ClassOrName
			wc.lpszClassName = SZ_CONTROL_CLASS % wc.lpszClassName
			
		
		title=""
		control.BaseControl.__init__(self, parent, wc, title,x, y, w, h, *styles)

	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
					
						
		
	def onMSG(self, hwnd, msg, wp, lp):
		pass


#*****************************************************	


