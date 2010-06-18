from wnd.consts import dlgs
from wnd.tools.dlgeditor.dlgeditor import DlgEditor
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

p= DlgEditor()

p.BeginTemplate(None, 'Find', 36, 44, 230, 94, ('arial', 8, 0, 0), 'modalframe', 'popup', 'caption', 'sysmenu', 'border', '3dlook', 'contexthelp')

# find editvox
p.Item('static', 0xFFFFFFFF, 'Fi&nd what:', 4, 9, 48, 8, 'left', 'visible')
p.Item('edit', dlgs.edt1, '', 54, 7, 114, 12, 'group', 'tabstop', 'autohscroll', 'visible', 'clientedge')

# replace editbox
p.Item('static', 0xFFFFFFFF, 'Fi&nd what:', 4, 26, 48, 8, 'left', 'visible')
p.Item('edit', dlgs.edt2, '', 54, 24, 114, 12, 'group', 'tabstop', 'autohscroll', 'visible', 'clientedge')

# whole word and match case checkbox
p.Item('button', dlgs.chx1, 'Match &whole word only', 5, 46, 104, 12, 'group','autocheckbox', 'visible', 'tabstop')
p.Item('button', dlgs.chx2, 'Match &case', 5, 62, 59, 12, 'autocheckbox', 'visible')    

# default buttons
p.Item('button', dlgs.IDOK, '&Find Next', 174, 4, 50, 14, 'group', 'visible', 'tabstop')
p.Item('button', dlgs.psh1, '&Find Next', 174, 21, 50, 14, 'visible')
p.Item('button', dlgs.psh2, '&Find Next', 174, 38, 50, 14, 'visible')
p.Item('button', dlgs.IDCANCEL, 'Cancel', 174, 55, 50, 14, 'visible')
p.Item('button', dlgs.pshHelp, '&Help', 174, 75, 50, 14, 'visible')

	
#***********************************************************************
#***********************************************************************

if __name__=='__main__':
	import wnd
	from wnd.dlgs import replacetext
	
	class Window(wnd.Window):
		def __init__(self):
			wnd.Window.__init__(self, 'findtext_test', 'findtext_test', None, None, None, None, 'sysmenu', 'sizebox', 'dialoglike')

			self.fr = replacetext.ReplaceTextFromTemplate(p.ToBuffer())
			self.fr.onMSG = self.on_fr
			
		def on_fr(self, hwnd, msg, wp, lp):
			if msg.startswith('fr_'):
				print hwnd, msg, wp, lp
				
		def onMSG(self, hwnd, msg, wp, lp):
			if msg == 'open':
				self.fr.Run(self.Hwnd, 'foo', '', 'hook', 'showhelp')


	w= Window()
	w.Run()
	
	
	
		


   