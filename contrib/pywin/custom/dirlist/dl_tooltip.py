

from wnd.controls import tooltip
from wnd.wintypes import POINT
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class DLTooltip(tooltip.Tooltip):
	
	def __init__(self, mainframe, parent):
		
		self.Mainframe= mainframe
		tooltip.Tooltip.__init__(self, parent, 'alwaystip')
		self.SetTrackTip(1000, '')

		self.HandleMessage(self.Msg.WM_WINDOWPOSCHANGED)


	def ShowTip(self, text, x, y):
		self.SetTrackTipText(1000, text)
		self.SetTrackTipPos(x, y)
		self.ShowTrackTip(1000)

	def HideTip(self):
		self.HideTrackTip(1000)


	#def onMSG(self, hwnd, msg, wp, lp):
	#	if msg=="show":
	#		self.SetWindowPos(33, 33)
		
	#	if msg==self.Msg.WM_WINDOWPOSCHANGED:
		#	self.SetWindowPos(33, 33)
		



class DLTooltip2(tooltip.Tooltip):
	
	def __init__(self, LV):
		
		self.LV= LV
		
		tooltip.Tooltip.__init__(self, self.LV, 'alwaystip')
				
		self.LV.SetTooltips(self)
		self.SetFont(self.LV.GetFont())
		self.SetToolTip(self.LV, 'foo')

		self.tippos= None
		

		self.HandleMessage(self.Msg.WM_WINDOWPOSCHANGED)

	
	def onMSG(self, hwnd, msg, wp, lp):
		
		if msg=='show':
			
			x, y=self.GetCursorPos()
			result= self.LV.ItemHittest(x, y)
			if result:
				nItem= result[0]
				nSubItem= 0
				rc=self.LV.GetItemLabelRect(nItem, nSubItem)
				
				text= self.LV.GetItemText(nItem, nSubItem)
				self.SetToolTipText(self.LV, text)
				
				w, h= self.GetTextExtend(text)
				self.SetWindowSize(w, rc.bottom-rc.top)
				
				#pt= POINT(x, y)
				rc.ClientToScreen(self.LV.Hwnd)
				
				self.tippos= rc.left, rc.top
				print 'show'
			else:
				self.tippos= None

			
		if msg==self.Msg.WM_WINDOWPOSCHANGED:
			if self.tippos:
				self.SetWindowPos(*self.tippos)		