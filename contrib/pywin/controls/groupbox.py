

from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		

class Styles:
	BS_GROUPBOX        = 7
	
	BS_LEFT            = 256
	BS_RIGHT           = 512
	BS_CENTER          = 768
	BS_FLAT            = 32768
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['BS_', ]

class  Msgs: 	pass

Msgs.__dict__.update(control.control_msgs.__dict__)


class Groupbox(control.BaseControl, ControlMethods):
	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		

		styles +='groupbox'	, # 'subclass',
		control.BaseControl.__init__(self, parent, "Button", title, x, y, w, h, *styles)						
		
			
class GroupboxFromHandle(control.ControlFromHandle, ControlMethods):
		
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		



#***********************************************

	
