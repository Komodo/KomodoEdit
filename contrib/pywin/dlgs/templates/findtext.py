"""default template for FindText dialog using dlgeditor"""

from wnd.consts import dlgs
from wnd.tools.dlgeditor.dlgeditor import DlgEditor
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
p= DlgEditor()

p.BeginTemplate(None, 'Find', 30, 73, 236, 62, ('Ms Sans Serif', 8, 0, 0), 'modalframe', 'popup', 'caption', 'sysmenu', 'border', '3dlook', 'contexthelp')

# find editvox
p.Item('static', 0xFFFFFFFF, 'Fi&nd what:', 4, 8, 42, 8, 'left', 'visible')
p.Item('edit', dlgs.edt1, '', 47, 7, 128, 12, 'group', 'tabstop', 'autohscroll', 'visible', 'clientedge')

# whole word and match case checkbox
p.Item('button', dlgs.chx1, 'Match &whole word only', 4, 26, 100, 12, 'group','autocheckbox', 'visible', 'tabstop')
p.Item('button', dlgs.chx2, 'Match &case', 4, 42, 64, 12, 'autocheckbox', 'visible')    
	
# direcion radiobox
p.Item('button', dlgs.grp1, 'Direction', 107, 26, 68, 28, 'groupbox', 'group', 'visible')  
p.Item('button', dlgs.rad1, '&Up', 111, 38, 25, 12, 'group','autoradiobutton', 'visible')
p.Item('button', dlgs.rad2, '&Down', 138, 38, 35, 12, 'autoradiobutton', 'visible')

# default buttons
p.Item('button', dlgs.IDOK, '&Find Next', 182, 5, 50, 14, 'group', 'visible', 'tabstop')
p.Item('button', dlgs.IDCANCEL, 'Cancel', 182, 23, 50, 14, 'visible')
p.Item('button', dlgs.pshHelp, '&Help', 182, 45, 50, 14, 'visible')

	
#***********************************************************************
#***********************************************************************

if __name__=='__main__':
	import wnd
	from wnd.dlgs import findtext
	
	class Window(wnd.Window):
		def __init__(self):
			wnd.Window.__init__(self, 'findtext_test', 'findtext_test', None, None, None, None, 'sysmenu', 'sizebox', 'dialoglike')

			self.fr = findtext.FindTextFromTemplate(p.ToBuffer())
			self.fr.onMSG = self.on_fr
			
		def on_fr(self, hwnd, msg, wp, lp):
			if msg.startswith('fr_'):
				print hwnd, msg, wp, lp
				
		def onMSG(self, hwnd, msg, wp, lp):
			if msg == 'open':
				self.fr.Run(self.Hwnd, 'foo', 'hook', 'showhelp')


	w= Window()
	w.Run()
	
	
	
		


   