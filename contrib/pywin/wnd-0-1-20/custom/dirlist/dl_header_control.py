"""header control for the dirlist"""

from wnd import gdi
from wnd.api import winpath
from wnd.controls import header
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class HeaderControl(header.Header):
	def __init__(self, mainframe, parent, *styles):
		
		self.Mainframe= mainframe
		
		
		header.Header.__init__(self, parent, 0, 0, 0, 0, *styles)
		self.fDL_HilightHeader= False
		self.Item('')

		
	#----------------------------------------------------------------------
	# message handler
	
	def onMSG(self, hwnd, msg, wp, lp):
		
		if msg=='customdraw':
			
			if lp.drawStage== lp.PREPAINT:
				return lp.NOTIFYITEMDRAW
			
			elif lp.drawStage== lp.ITEMPREPAINT:
				dc= gdi.DCFromHandle(lp.hdc)
				dc.SetBkMode('transparent')
				
				if self.fDL_HilightHeader:
					brush= gdi.SysColorBrush('highlight')
					dc.SetTextColor(gdi.GetSysColor('highlighttext'))
				else:
					brush= gdi.SysColorBrush('btnface')
					dc.SetTextColor(gdi.GetSysColor('btntext'))
				
				if 'border' in self.Mainframe.styles:
					dc.DrawEdge(lp.rc, 'sunkeninner', 'rect')
					lp.rc.Inflate(-1, -1)
					dc.DrawEdge(lp.rc, 'raisedouter', 'rect', 'soft')
					lp.rc.Inflate(-1, -1)
				elif 'clientedge' in self.Mainframe.styles:
					dc.DrawEdge(lp.rc, 'sunken', 'rect', 'soft')
					lp.rc.Inflate(-2, -2)
					lp.rc.bottom += 1
				
				
				brush.FillRect(dc, lp.rc)
				brush.Close()
				path= winpath.Compact(dc.handle, 
															None, 
															self.GetItemText(0), 
															lp.rc.right-lp.rc.left)
				font= dc.GetFont()
				font.DrawText(dc, lp.rc, path)
				
				font.Close()
				dc.Close()
				return lp.SKIPDEFAULT
				
			
		elif msg=='lmbdouble':
			self.Mainframe.Listview.DL_DirUp()
		elif msg=='mouseactivate':
			self.DL_HilightHeader(hilight=True, focus=True)
		
		elif msg=='rmbup':
			self.Mainframe.MsgHandler(hwnd, "header", "rmbup", 0)
		
		
	#------------------------------------------------------------------------
			
	def DL_HilightHeader(self, hilight=True, focus=True):
		self.fDL_HilightHeader= hilight
		self.RedrawClientArea()
		if focus:
			self.Mainframe.Listview.SetFocus()
	
	def DL_HasDir(self):
		return bool(self.GetItemText(0))


	def DL_Hide(self):
		self.Disable()
		return self.Hide()

	def DL_Show(self):
		self.Enable()
		return self.Show()
		