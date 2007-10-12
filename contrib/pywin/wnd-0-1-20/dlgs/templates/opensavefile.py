"""default template for OpenSaveFile dialog using dlgeditor"""

from wnd.consts import dlgs
from wnd.tools.dlgeditor.dlgeditor import DlgEditor
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
"""
NOTES
	- the toolbar used by the dialog is not documented 
 - the dialog ignores all attempts to change the font
 - the listview used to display the files is created at runtime
		as a child of a parent window 'SHELLDLL_DefView'
"""


p= DlgEditor()

p.BeginTemplate(None, 'Open', 0, 0, 280, 164, ('Ms Sans Serif', 8, 0, 0), 'modalframe', 'popup', 'caption', 'contexthelp', '3dlook', 'sysmenu', 'clipchildren')

# dir combo
p.Item('static', dlgs.stc4, 'Look &in:', 7, 6, 27, 8, 'left', 'notify', 'visible')
p.Item('combobox', dlgs.cmb2, '', 36, 3, 138, 300, 'dropdownlist', 'ownerdrawfixed', 'hasstrings', 'vscroll','tabstop', 'visible')

# some listbox
p.Item('static', dlgs.stc1, '', 172, 2, 102, 17)	 # not visiblre
p.Item('listbox', dlgs.lst1, '', 4, 20, 272, 85, 'sort', 'nointegralheight', 'multicolumn', 'hscroll') # not visible
        
# filename editbox
p.Item('static', dlgs.stc3, 'File &name:', 5, 112, 48, 8, 'notify', 'left', 'visible')
p.Item('edit', dlgs.edt1, '', 54, 111, 155, 12, 'autohscroll', 'visible')     
	
# filter combobox
p.Item('static', dlgs.stc2, 'Files of &type:', 5, 131, 48, 8, 'notify', 'left', 'visible')	
p.Item('combobox', dlgs.cmb1, '', 54, 129, 155, 100, 'dropdownlist', 'vscroll','tabstop', 'visible')

# redonly checkbox
p.Item('button', dlgs.chx1, 'Open as &read-only', 54, 148, 74, 10, 'autocheckbox', 'tabstop', 'visible')	

# buttons
p.Item('button', dlgs.IDOK, '&Open', 222, 110, 50, 14, 'defpushbutton', 'visible', 'tabstop')	
p.Item('button', dlgs.IDCANCEL, 'Cancel', 222, 128, 50, 14, 'visible')
p.Item('button', dlgs.pshHelp, '&Help', 222, 145, 50, 14, 'visible')
   


#*********************************************************************************
#*********************************************************************************

if __name__=='__main__':
	from wnd.dlgs import opensavefile
	
	def callback(hwnd, msg, wp, lp):
			pass
			#if msg=="debug": print lp
					
	o=opensavefile.OpenSaveFileFromTemplate(p.ToBuffer(), 'debug')
	
	o.onMSG= callback
	r= o.RunOpenFile(0, 'createprompt', 'hook', 'report', defaultfilter=0, initialdir='c:\\')
	#r= o.RunSaveFile(0, 'createprompt', 'overwriteprompt', 'hook', 'hidereadonly', defaultfilter=0, initialdir='c:\\')
	print r


