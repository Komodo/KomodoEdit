"""
Note
This GUI is not optimised for any other then 1200*1024 screen resolution

"""

import wnd
from wnd import gdi
from wnd.wintypes import RGB
from wnd.controls.button import Button
from wnd.controls.listview import Listview
from wnd.controls.imagelist import Imagelist
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# TODO redraw LV items when the user drags the header 

class window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'DrawEdge-', 'DrawEge', None, None, None, None, 'sysmenu', 'sizebox')
		#self.SetStyle('-caption')

		self.bk_color=0x00ff9d9d
		self.tableHeaderText='edge/border'
		self.cellH=80
					
		self.imgl = Imagelist(1, self.cellH, 1, 1)
		self.imgl.AddIcons(gdi.IconFromBytes('', '', 1, 1, 1)) 
		rc=self.GetClientRect()

		self.lv=Listview(self, 0, 0, 0, 0, 'report', 'gridlines', 'customdraw', 'border')
		self.lv.onMSG=self.on_lv
		self.lv.SetImagelistSmall(self.imgl)
		self.lv.SetBkColor(self.bk_color)		
		
		
		self.edges=('raisedinner', 'sunkeninner', 'raisedouter', 'sunkenouter', 'bump', 'etched', 'raised', 'sunken')
		self.borders=('None', 'flat', 'mono', 'soft')
				
		# get max string length and set items
		self.cellH=max(self.lv.GetStringWidth(*self.borders)+10, self.cellH)
		n=self.lv.GetStringWidth(*((self.edges)+ (self.tableHeaderText, )))
		
		self.lv.Column(self.tableHeaderText, n+10)
		self.lv.Item(self.tableHeaderText)
		for i in self.edges:
			self.lv.Item(i, self.cellH)
		for i in self.borders:
			self.lv.Column(i)
				
		rc=self.lv.GetItemRect(len(self.lv)-1, 0)
		self.lv.OffsetWindowSize(rc.right, rc.bottom)
		
		rc=self.lv.GetWindowRect()
		rc2=self.GetClientRect()
		
		self.OffsetWindowSize(rc.right-rc.left-rc2.right, rc.bottom-rc.top-rc2.bottom)
				
		
		
	def on_lv(self, hwnd, msg, wp, lp):
		if msg=="customdraw":
			if lp.drawStage==lp.PREPAINT:
				return lp.NOTIFYITEMDRAW
			
			elif lp.drawStage==lp.ITEMPREPAINT:
				return lp.NOTIFYSUBITEMDRAW

			else:
				if lp.iItem==0 and lp.iSubItem >0:
					dc=gdi.DCFromHandle(lp.hdc)
					font= dc.GetFont()
					rc=self.lv.GetItemRect(lp.iItem, lp.iSubItem)
					rc.Inflate(-2, -2)
					text='\n'.join(self.borders[lp.iSubItem-1].split(','))
					font.DrawText(dc, rc, text)
					dc.Close()
					font.Close()
					return lp.SKIPDEFAULT
			
				elif lp.iItem >0 and lp.iSubItem >0:
					#if lp.iSubItem>1: return 0
					border=self.borders[lp.iSubItem-1].split(',')+['rect', ]
					if border[0]=='None': border.pop(0)
					dc=gdi.DCFromHandle(lp.hdc)
					rc=self.lv.GetItemRect(lp.iItem, lp.iSubItem)
					rc.Inflate(-10, -10)
					dc.DrawEdge(rc, 
										self.edges[lp.iItem-1], 
										*border)
					dc.Close()
					return lp.SKIPDEFAULT
	
				
	
	def onMSG(self, hwnd, msg, wp, lp):
		if msg=="create": pass
		elif msg=="destroy": pass
				
w = window()
w.Run()

