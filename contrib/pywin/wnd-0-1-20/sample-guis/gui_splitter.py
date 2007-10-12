

import wnd
from wnd import gdi
from wnd.custom.splitter import Splitter
from wnd.controls.editbox import Editbox
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'splitter-test', 'splitter-test', None, None, None, None, 'sysmenu', 'sizebox',  'dialoglike')
						
		# setup some splitters
		self.spW= 30
		x,y,w,h= self.GetClientRect().ToSize()
		
		## 'feedbackbar' will leave some stains behind on sp3
		self.sp1=Splitter(self, w/2-(self.spW/2), 0, self.spW, h, 'clientedge','vert', 'tabstop', 'feedbackbar')
		self.sp2=Splitter(self, 0, h/2-(self.spW/2), w/2-(self.spW/2)-1, self.spW, 'clientedge', 'tabstop', 'feedbackbar')
		self.sp3=Splitter(self, w/2+(self.spW/2)+1, h/2-(self.spW/2), w/2-self.spW/2-1, self.spW, 'clientedge', 'tabstop')
		self.sp1.onMSG= self.sp2.onMSG=self.sp3.onMSG= self.on_splitter

		colorBk= gdi.GetSysColor('msgbox')
		colorHi= gdi.GetSysColor('highlight')
		self.sp1.SetColors(colorBk, colorHi)
		self.sp2.SetColors(colorBk, colorHi)
		self.sp3.SetColors(colorBk, colorHi)

		self.sp3.SetPageSize(100)

		# ++ some controls for demonstration purposes 
		self.ed1=Editbox(self, 'some text here', 0, 0, 0, 0, 'clientedge', 'vscroll', 'hscroll')
		self.ed2=Editbox(self, 'some text here', 0, 0, 0, 0, 'clientedge', 'vscroll', 'hscroll')
		self.ed3=Editbox(self, 'some text here', 0, 0, 0, 0, 'clientedge', 'vscroll', 'hscroll')
		self.ed4=Editbox(self, 'some text here', 0, 0, 0, 0, 'clientedge', 'vscroll', 'hscroll')

			
	def sizecontrols(self):
		# keep all the controls in line
		x,y,w,h= self.GetClientRect().ToSize()
		
		rc1=self.sp1.GetWindowRect()
		rc1.ScreenToClient(self.Hwnd)
		rc2=self.sp2.GetWindowRect()
		rc2.ScreenToClient(self.Hwnd)
		rc3=self.sp3.GetWindowRect()
		rc3.ScreenToClient(self.Hwnd)
		
		self.DeferWindows(
			(self.sp1, rc1.left, rc1.top, self.spW, h),
			(self.sp2, rc2.left, rc2.top, rc1.left-1, self.spW),
			(self.sp3, rc1.right+1, rc3.top, w-rc1.right-1, self.spW),
			
			(self.ed1, 0, 0, rc1.left-1, rc2.top-1),
			(self.ed2, rc1.right+1, 0, w-rc1.right-1, rc3.top-1),		
			(self.ed3, 0, rc2.bottom+1, rc1.left-1, h-rc2.bottom-1),
			(self.ed4, rc1.right+1, rc3.bottom-1, w-rc1.right-1, h-rc3.bottom+1)
			)
		
	
	def on_splitter(self, hwnd, msg, wp, lp):
		if msg=="move": 
			pass
		if msg=="moved": 
			self.sizecontrols()
		
			
	def onMSG(self, hwnd, msg, wp, lp):
		if msg=="size": 
			self.sizecontrols()
		elif msg=="close":
			pass
				
		
	
w = window()
w.Run()



