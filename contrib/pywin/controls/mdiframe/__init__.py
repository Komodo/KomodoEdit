

"""
MDI-Frame

For testing purposes only

Main problem here is how to close the mdi-childwindows.



"""

from wnd.wintypes import (user32,
													byref,
													MSG,
													HIWORD,
													LOWORD)
from wnd import fwtypes as fw
from wnd.controls.windowclass import (WindowClass,  
																		SZ_WINDOW_CLASS)
from wnd.controls.base import window
from wnd.controls.base.methods import WindowMethods

from wnd.controls.menu import Menu


from wnd.controls.mdiframe.mdiclient import MDIClient
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Styles: pass
Styles.__dict__.update(window.window_styles.__dict__)

class Msgs:
	WM_MDICREATE        = 544
	WM_MDIDESTROY       = 545
	WM_MDIACTIVATE      = 546
	WM_MDIRESTORE       = 547
	WM_MDINEXT          = 548
	WM_MDIMAXIMIZE      = 549
	WM_MDITILE          = 550
	WM_MDICASCADE       = 551
	WM_MDIICONARRANGE   = 552
	WM_MDIGETACTIVE     = 553
	WM_MDISETMENU       = 560

Msgs.__dict__.update(window.window_msgs.__dict__)


#****************************************************************************
# MDI frame
#***************************************************************************

class MDIFrame(window.BaseWindow, WindowMethods):
	
	MIN_MENU_ID= fw.WND_ID_MDICHILD_MAX + 1
	
	
	def __init__(self, title, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 

		
		self._client_MDIClient= None
				
		# preregister a class 
		clss = WindowClass()
		clss.SetClassName(SZ_WINDOW_CLASS % "MdiFrame")
		clss.SetBackground('window')
		clss.SetCursor()
				
		# init the base window
		window.BaseWindow.__init__(self, clss, title, x, y, w, h, *styles)

					
	#-----------------------------------------------------------------
	# methods

	def MDIClient(self, x, y, w, h, *styles, **kwargs):
		if self. _client_MDIClient: raise "mdi-client already created"
		self. _client_MDIClient= MDIClient(self.Hwnd, 
		kwargs.get('hMenu', 0), x,y,w,h, *styles)
		return self. _client_MDIClient
	
	def HasClient(self):
		return not self. _client_MDIClient ==None
			
	#-----------------------------------------------------------------------------------
	# message handler
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
						
		if msg==5:		# WM_SIZE
			## overwrite to make resizing work
			if self._base_fIsopen:
					self.onMSG(hwnd, "size", 0, [0, 0, LOWORD(lp), HIWORD(lp)])
			return user32.DefWindowProcA(hwnd, msg, wp, lp)
		
		
	
	#----------------------------------------------------------------------------------
	# some adjustements for MDIFrame WindowProc
	#	 - instead of DefWindowProc an MDIFrame returns DefFrameProc
	#	- in the message loop TranslateMDISysAccel has to intercept messages first
	def DefWindowProc(self, hwnd, msg, wp, lp):
		if self. _client_MDIClient:
			return user32.DefFrameProcA(hwnd, self. _client_MDIClient.Hwnd, msg, wp, lp)
		return user32.DefWindowProcA(hwnd, msg, wp, lp)
	
	
	def Run(self, show='normal'):
		
		try:
			show=['hidden','normal', 'minimized','maximized'].index(show)
		except:
			try: range(4)[show]
			except:	raise "invalid flag: %s" % show			
		
		# run the messageloop
		self._base_fIsopen= True
		self.onMSG(self.Hwnd, "create", 0, 0)
		user32.ShowWindow(self.Hwnd, show)
		user32.UpdateWindow(self.Hwnd)
		GM, TM, DM, TACC, TMDIA=(user32.GetMessageA,
									user32.TranslateMessage,
									user32.DispatchMessageA,
									user32.TranslateAcceleratorA,
									user32.TranslateMDISysAccel) 
		msg = MSG()
		pMsg = byref(msg)
		if self.GetStyleL('basestyle') & self.Style.WS_BASE_DIALOGLIKE:
			IsDialogMessage=user32.IsDialogMessageA
			self.onMSG(self.Hwnd, "open", 0, 0)
			window._exit.Unregister(self.Hwnd)
			#ExitHandler._UnregisterGuiExitFunc()
			while GM(pMsg, 0, 0, 0) > 0:
				
				if self. _client_MDIClient:
					if not TMDIA(self. _client_MDIClient.Hwnd, pMsg):
						if not IsDialogMessage(self.Hwnd, pMsg):
							if self._base_hAccelerator:
								if not TACC(self.Hwnd, self._base_hAccelerator, pMsg):
									TM(pMsg)
									DM(pMsg)
									continue
				TM(pMsg)
				DM(pMsg)
				
							
		else:
			self.onMSG(self.Hwnd, "open", 0, 0)
			window._exit.Unregister(self.Hwnd)
			#ExitHandler._UnregisterGuiExitFunc()
			while GM(pMsg, 0, 0, 0) > 0:
				
				if self. _client_MDIClient:
					if not TMDIA(self. _client_MDIClient.Hwnd, pMsg):
						if self._base_hAccelerator:
							if not TACC(self.Hwnd, self._base_hAccelerator, pMsg):
								TM(pMsg)
								DM(pMsg)
								continue
				TM(pMsg)
				DM(pMsg)
		

#************************************************************

