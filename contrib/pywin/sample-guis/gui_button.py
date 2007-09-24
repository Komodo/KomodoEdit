"""Sample GUI, ownerdrawing buttons"""


import wnd
from wnd import gdi
from wnd.controls.button import Button
from wnd.controls.checkbox import Checkbox
from wnd.controls.imagelist import Imagelist
from wnd.wintypes import *

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class MyODButton(Button):
	def __init__(self, parent, title, x, y, w, h):
		Button.__init__(self, parent, title, x, y, w, h, 'ownerdraw')
		
	def onMSG(self, hwnd, msg, wp, lp):
		if hwnd==self.Hwnd:
			
			if msg=="drawitem":
				dc=gdi.DCFromHandle(lp.hDC)
				font= dc.GetFont()
				dc.SetBkMode('transparent')
								
				# draw the border
				if lp.itemState & lp.SELECTED:
					dc.DrawBorder(lp.rcItem, 'clientedge', 'pushed')
				else:
					dc.DrawBorder(lp.rcItem, 'clientedge')
				
				# draw background and text
				if lp.itemState & lp.DISABLED:
					font.DrawStateEx(dc, lp.rcItem, self.GetText(),  'singleline', 'vcenter', 'center', 'disabled', 'end_ellipsis')
				else:
					if lp.itemState & lp.SELECTED:
						brush=gdi.SolidBrush(RGB(0, 100, 100))
					elif lp.itemState & lp.FOCUS:
						brush=gdi.SolidBrush(RGB(0, 150, 150))
					else:
						brush=gdi.SolidBrush(RGB(0, 150, 150))
					brush.FillRect(dc, lp.rcItem)
					brush.Close()
					font.DrawText(dc, lp.rcItem, self.GetText() , 'singleline', 'vcenter', 'center', 'end_ellipsis')
				
				font.Close()
				dc.Close()
				return 0
			else:
				return self.onMyODButton(hwnd, msg, wp, lp)
	
	def onMyODButton(self, hwnd, msg, wp, lp):
		# new message handler, overwrite
		pass

#**********************************************************************************************
#**********************************************************************************************
class MyODCheckbox(Checkbox):
	def __init__(self, parent, title, x, y, w, h, imagelist):
		Checkbox.__init__(self, parent, title, x, y, w, h, 'ownerdraw')
		self.imgl=imagelist
			
		
	def onMSG(self, hwnd, msg, wp, lp):
		if msg=="drawitem":
			# draw a flat checkbox from scratch
			
			dc=gdi.DCFromHandle(lp.hDC)
			font= dc.GetFont()
			rc=self.GetClientRect()
			
			# frame the checkbox
			# ...DrawEdge does not inflate our rect, so 
			# we have to guess the border size
			dc.DrawEdge(rc, 'raisedouter', 'mono', 'rect')
			rc.Inflate(-1, -1)
					
			# calculate the bitmaps rect
			x=rc.left
			BmW, BmH=self.imgl.GetIconSize()
			y=((rc.bottom-rc.top)/2)-(BmH/2)
			rcBmp=RECT(x, y, x+BmW, y+BmH)
			
			# draw a flat border around the bitmap
			# ...DrawBorder inflates the rect for us
			dc.DrawBorder(rcBmp, 'flat')
			
			# exclude the clientedge border of the bitmap from drawing
			rgn=gdi.RectRegion(rcBmp)
			dc.SetClipRegion(rgn)
			rgn.Close()
			
			# prepair the checkboxes rect for drawing the text
			rc.left+=BmW+(BmW/2)
			
			# now draw this thing
			if lp.itemState & lp.DISABLED:
				if self.IsChecked(): 
					self.imgl.Draw(dc, 4, x, y)
				else: 
					self.imgl.Draw(dc, 2, x, y)
				dc.SetClipRegion(None)
				font.DrawStateEx(dc, rc, self.GetText(), 'singleline', 'vcenter', 'disabled')
			else:
				if lp.itemState & lp.SELECTED:
					if self.IsChecked(): 
						self.imgl.Draw(dc, 3, x, y)
					else: 
						self.imgl.Draw(dc, 2, x, y)
				else:
					if self.IsChecked(): 
						self.imgl.Draw(dc, 1, x, y)
					else: 
						self.imgl.Draw(dc, 0, x, y)
					dc.SetClipRegion(None)
					font.DrawText(dc, rc, self.GetText(), 'singleline', 'vcenter')
			
			font.Close()
			dc.Close()
		else:
			return self.onMyODCheckbox(hwnd, msg, wp, lp)
	
	def onMyODCheckbox(self, hwnd, msg, wp, lp):
		# new message handler, overwrite
		pass



#**********************************************************************************************
#**********************************************************************************************
class window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'buttonn-test', 'button-test', 10, 10, 400, 300, 'sysmenu')
		
		self.bt1=Button(self, 'simple button', 5, 5, 160, 80, 'center', 'vcenter', 'clientedge')
		self.bt1.onMSG=self.on_bt
		self.bt2=MyODButton(self, 'ownerdrawn button', 170, 5, 160, 80)
		self.bt2.onMyODButton=self.on_bt
				
		self.ck=Checkbox(self, 'simple checkbox', 5, 90, 160, 40, 'border', 'flat')
		self.ck.Check()
				
		bm=gdi.SystemBitmap('checkboxes')
		w, h= bm.GetSize()
		bmW, bmH = w/4, h/3
		self.imgl=Imagelist(bmW, bmH, 5, 5)
		self.imgl.AddBitmap(bm.Extract(None, 0, 0, bmW, bmH))
		self.imgl.AddBitmap(bm.Extract(None, bmW, 0, bmW, bmH))
		self.imgl.AddBitmap(bm.Extract(None, bmW*2, 0, bmW, bmH))
		self.imgl.AddBitmap(bm.Extract(None, 0, bmW*3, bmW, bmH))
		self.imgl.AddBitmap(bm.Extract(None, bmW*3, bmH*2, bmW, bmH))
		bm.Close()
							
		self.ck2=MyODCheckbox(self, 'ownerdraw checkbox', 175, 90, 155, 40,self.imgl)
		self.ck2.onMyODCheckbox=self.on_ck
		self.ck2.Check()
		
			
	def on_debug(self, hwnd, msg, wp, lp):
		pass
	
	def on_ck(self, hwnd, msg, wp, lp):
		pass
						
	def on_bt(self, hwnd, msg, wp, lp):
		if hwnd==self.bt1.Hwnd:
			if msg=="command":
				pass
				
		elif hwnd==self.bt2.Hwnd:
			if msg=="command":
				pass
			
	
	def onMSG(self, hwnd, msg, wp, lp):
		if msg=="open":
			pass
		
		elif msg=="destroyed":
			pass
		

w = window()
w.Run()





