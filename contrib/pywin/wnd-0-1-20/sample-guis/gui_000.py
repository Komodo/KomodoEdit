""""featureles gui"""

import wnd
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	
class Window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'test', 'test', None, None, None, None, 'sysmenu', 'sizebox')
		
	def onMSG(self, hwnd, msg, wp, lp):
		pass
			
		
    
                  
w = Window()
w.Run()





