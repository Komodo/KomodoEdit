"""default template for ChooseFont dialog using dlgeditor"""

from wnd.consts import dlgs
from wnd.tools.dlgeditor.dlgeditor import DlgEditor
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
p= DlgEditor()

p.BeginTemplate(None, 'Font', 13, 54, 263, 196, ('Ms Sans Serif', 8, 0, 0), 'modalframe', 'popup', 'caption', 'contexthelp', '3dlook', 'sysmenu')

# font combos
p.Item('static', dlgs.stc1, '&Font:', 7, 7, 40, 9, 'left', 'visible')
p.Item('combobox', dlgs.cmb1, '', 7, 16, 98, 76, 'simple', 'sort', 'vscroll', 'tabstop', 'disablenoscroll', 'hasstrings', 'ownerdrawfixed', 'visible')

p.Item('static', dlgs.stc2, 'Font st&yle:', 110, 7, 44, 9, 'left', 'visible')
p.Item('combobox', dlgs.cmb2, '', 110, 16, 62, 76, 'simple', 'vscroll', 'disablenoscroll', 'tabstop', 'visible')

p.Item('static', dlgs.stc3, '&Size:',177, 7, 30, 9, 'left', 'visible')
p.Item('combobox', dlgs.cmb3, '', 177, 16, 27, 76, 'simple', 'tabstop', 'sort', 'disablenoscroll', 'hasstrings', 'ownerdrawfixed', 'visible')

# default buttons
p.Item('button', dlgs.IDOK, 'OK', 210, 16, 45, 14, 'pushbutton', 'defpushbutton', 'group',  'visible', 'tabstop')
p.Item('button', dlgs.IDCANCEL, 'Cancel', 210, 32, 45, 14, 'pushbutton', 'visible')
p.Item('button', dlgs.psh3, '&Apply', 210, 48, 45, 14, 'pushbutton', 'defpushbutton', 'visible')
p.Item('button', dlgs.pshHelp, '&Help', 210, 64, 45, 14, 'pushbutton', 'visible')

# effects
p.Item('button', dlgs.grp1, 'Effects', 7, 97, 98, 72, 'groupbox', 'visible')
p.Item('button', dlgs.chx1, 'Stri&keout', 13, 110, 49, 10, 'autocheckbox', 'tabstop',  'visible')
p.Item('button', dlgs.chx2, '&Underline', 13, 123, 51, 10, 'autocheckbox', 'tabstop',  'visible')

# color
p.Item('static', dlgs.stc4, '&Color:', 13, 136, 30, 9, 'left', 'visible')
p.Item('combobox', dlgs.cmb4, '', 13, 146, 82, 100, 'dropdownlist', 'autohscroll', 'border', 'vscroll', 'tabstop',  'hasstrings', 'ownerdrawfixed', 'visible')

# sample
p.Item('button', dlgs.grp2, 'Sample', 110, 97, 94, 43, 'groupbox', 'group',  'visible')
p.Item('static', dlgs.stc5, 'AaBbYyZz', 118, 111, 77, 23, 'noprefix') # not visible
p.Item('static', dlgs.stc6, '', 7, 176, 196, 20, 'left', 'noprefix', 'visible')

# script
p.Item('static', dlgs.stc7, 'Sc&ript:', 110, 147, 30, 9, 'left', 'visible')
p.Item('combobox', dlgs.cmb5, '', 110, 157, 94, 30, 'dropdownlist', 'autohscroll', 'border', 'vscroll', 'tabstop', 'hasstrings', 'ownerdrawfixed', 'visible')


#***********************************************************************
#***********************************************************************

if __name__=='__main__':
	from wnd.dlgs import choosefont
	
	def callback(hwnd, msg, wp, lp):
			pass
			#if msg=="debug": print lp
					
	lf=choosefont.LOGFONT()
	lf.lfFaceName='verdana'
	c=choosefont.ChooseFontFromTemplate(p.ToBuffer(), 'debug')
	c.onMSG= callback
	r=c.Run(None,  'hook', 'screenfonts', 'apply', 'effects', 'showhelp', 'selectscript', logfont=lf) 
	#print r
	
	