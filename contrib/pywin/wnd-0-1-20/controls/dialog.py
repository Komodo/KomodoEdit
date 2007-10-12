
from wnd.controls.base import dialog as _dialog
from wnd.controls.base.methods import DialogMethods 
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#class Styles: pass
#class Msgs: pass


class Dialog(_dialog.BaseDialog, DialogMethods):
	
	def __init__(self, title, x, y, w, h, *styles):
		styles += 'visible',
		_dialog.BaseDialog.__init__(self, title, x, y, w, h, *styles)

			
		
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		self.onINIT(hwnd, msg, wp, lp)
	
		
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==self.Msg.WM_CLOSE:
			self.Close()
		


class DialogFromTemplate(Dialog, _dialog.BaseDialogFromTemplate):
		
	def __init__(self, template, *styles):
		_dialog.BaseDialogFromTemplate.__init__(self, template, *styles)
	




#******************************************************************

