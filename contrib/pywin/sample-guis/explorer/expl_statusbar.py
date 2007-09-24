

from wnd.controls.statusbar import Statusbar 
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class ExplStatusbar(Statusbar):
	
	def __init__(self, mainframe):
		
		self.Main= mainframe

		Statusbar.__init__(self, mainframe)
		


	def Expl_SetItemsSelected(self, n, size=''):
		
		if len(self) > 1:
			if not n:
				self.SetText('' , 1)
			elif n==1:
				self.SetText(' 1 Item Selected   %s bytes total' % size, 1)
			else:
				self.SetText(' %s Items Selected   %s bytes total' % (n, size), 1)