

from wnd.controls.windowclass import (WindowClass,  
																		SZ_WINDOW_CLASS)
from wnd.controls.base import window 
from wnd.controls.base.methods import WindowMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class Styles: pass

Styles.__dict__.update(window.window_styles.__dict__)
#Styles.prefix += []

class Msgs: pass	
Msgs.__dict__.update(window.window_msgs.__dict__)


class Window(window.BaseWindow, WindowMethods):
	
	
	def __init__(self, classname, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
					
		# preregister a class 
		clss = WindowClass()
		clss.SetClassName(SZ_WINDOW_CLASS % classname)
		clss.SetBackground('window')
		clss.SetCursor()
		
		# init the base window
		window.BaseWindow.__init__(self, clss, title, x, y, w, h, *styles)
		
	
	## overwrite the global message handler
	## and grab the messages 	
	def onMSG(self, hwnd, message, wparam, lparam):
		if message==16:	# WM_CLOSE
			self.Close()
		



#************************************************************

#w = Window('test', 'test', 10, 10, 200, 200, 'sysmenu')
#WM_MOUSEMOVE        = 512		
#w.handleMessage(WM_MOUSEMOVE)
#w.setDebug(True)

#w.run()
#wnd.setStyle(self.BT1, ...)