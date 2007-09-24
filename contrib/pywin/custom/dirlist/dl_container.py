"""container window for the dirlist"""


from wnd.controls import blank
from wnd.controls.windowclass import WindowClass, SZ_WINDOW_CLASS 
from wnd.wintypes import HIWORD, LOWORD, RECT

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
N_DIRLISTS= 0


class Container(blank.Blank):
	def __init__(self, mainframe, parent, x, y, w, h, *styles):
		
		self.Mainframe= mainframe
		
		global N_DIRLISTS
		N_DIRLISTS += 1
		c= SZ_WINDOW_CLASS % 'dl_container-%s' % N_DIRLISTS
		wc= WindowClass()
		wc.SetCursor()
		wc.SetClassName(c)
		#wc.SetBackground('activecaption')
		self.Hwnd= 0
		blank.Blank.__init__(self, parent, wc, x, y, w, h, *styles)

		

						
	def onMESSAGE(self, hwnd, msg, wp, lp):
					
		if hwnd==self.Hwnd:
			
			## size controls
			if msg==5:		# WM_SIZE
				
								
				w, h= LOWORD(lp), HIWORD(lp)
						
				if self.Mainframe.Header.IsVisible():
					rc= RECT(0, 0, w, h)
				
					hdH= self.Mainframe.Header.GetLayout(rc).ToSize()[3]
									
					self.DeferWindows(
					(self.Mainframe.Header, 0, 0, w, hdH),
					(self.Mainframe.Listview, 0, hdH, w, h-hdH),
					)
					
					self.Mainframe.Header.SetItemWidth(0, w)
					self.Mainframe.Listview.DL_AdjustColumnWidth(w)

				else:
					self.DeferWindows(
					(self.Mainframe.Listview, 0, 0, w, h),
					)
					
					self.Mainframe.Listview.DL_AdjustColumnWidth(w)

			elif msg==self.Msg.WM_SETFOCUS:
				self.Mainframe.Listview.SetFocus()
				
						
			
			


