"""Bit (bit !) more sophisticated dialog DlgTemplate editor.
Styles may be specified as strings here.
WS_VISIBLE becomes 'visible', WS_EX_CLIENTEGE 'clientedge'

LAST VISITED
	16.03.05


NOTES
	



Init a new DialogDlgTemplate by specifying 
classname (can be None), title,  x, y, w, h, font and styles for the main frame.
font is optional and can be Noner. If not None it should be a 4-tuple:
		(name, size, weight, italic).
		where:
			'name' is the font name
			'size' is the font size
			'weight' is any value range 0 through 1000
						supposed to work in steps 100 +
						err.. not working for me so far..
			'italic'  is 0 or 1

For each control to add to the DlgTemplate call the Item method
specifying classname, ID,  title, x, y, w, h, and styles.
You have to pass 'visible' along with the styles to create the control 
in visible state, otherwise it will be hidden.
WS_CHILD is set by default.

When done with the DlgTemplate either call the Run method to run the
dialog and see if it works or call the ToBuffer method to get
a ctypes string buffer in return containing the bytes of the DlgTemplate.
This string buffer you can pass to any api acepting a buffer
containing a dialog DlgTemplate - usually DialogBoxIndirect e.a-,
or save it to file or whatever. 
The bytes forming the DlgTemplate you will find in stringbuffer.raw


WARNING:
The windows API definitely does not like invalid DlgTemplates.
Creating a dialog upon an invalid DlgTemplate may dadlock
everything around or cause an empire of evil to arise.
No check is done to make shure you are not doing any
harm to your system. Use at your own risk.

NOTES
	
	- if you use common control classes in the dialog
		you have to call comctl32.InitCommonControls
		to make them work
	
	- Remember to kep a reference to the dialogDlgTemplate, when
		creating a dilalog from it. Otherwise it might get garbage
		collected while running the dialog.
		
	-Take care about your sources in case you want to rework
		or extend a dialog DlgTemplate ;)

	
TODO

"""

from wnd.tools.dlgeditor.dlgtemplate import DlgTemplate

from wnd.consts import styles as _styles
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def GetStyle(classname, *styles):
	style, exstyle= 0, 0
	if styles:
		styles= [i.upper() for i in styles]
		d= _styles.GetStyles(classname)
		if d==None: raise "class not supported: %s" % classnane
		for name, value in d.items():
			name= name.split('_', 2)
			if len(name) == 3:
				if name[1]=='EX':
					if name[2] in styles: 
						exstyle |= value
						styles.remove(name[2])
			elif len(name)==2:
				if name[1] in styles: 
					style |= value
					styles.remove(name[-1])
			if not styles: break
		if styles: raise "invalid style: %s" % styles[0].lower()

	return style, exstyle	
	
#************************************************************************************
#************************************************************************************

class DlgEditor(DlgTemplate):
		
	def __init__(self): pass
	
		
	def BeginTemplate(self, classname, title, x, y, w, h, font, *styles):	
		style, exstyle= GetStyle('dialog', *styles)
		DlgTemplate.BeginTemplate(self, classname, title, style, exstyle, x, y, w, h, font)
				
	def Item(self, classname, ID, title, x, y, w, h, *styles):
		style, exstyle= GetStyle(classname, *styles)
		DlgTemplate.Item(self, classname, ID, title, style, exstyle, x, y, w, h)
		
	def ToBuffer(self): return DlgTemplate.ToBuffer(self)
	def RunModal(self, hwnd=0, lp=0): 
		return DlgTemplate.RunModal(self, hwnd, lp)
	def RunModeless(self, hwnd=0, lp=0): return DlgTemplate.RunModeless(self, hwnd, lp)
	#def DlgProc(self, hwnd, msg, wp, lp):
	#	return DlgTemplate.DlgProc(self, hwnd, msg, wp, lp)
	
#*****************************************************************************************
#*****************************************************************************************

def test():
	IDOK       = 1
	IDCANCEL   = 2
	font=('arial', 12, 100, 1)
	tpl = DlgEditor() 
	tpl.BeginTemplate(None, 'test dialog', 0, 10, 80, 85, font, 'sysmenu')
	tpl.Item('button', IDOK, 'OK', 8, 50, 25, 12, 'visible')
	tpl.Item('button', IDCANCEL, 'cancel', 45, 50, 25, 12, 'visible')
	#print repr(tpl.ToBuffer())
	print tpl.RunModal()
	import os
	fp= open(os.path.join(os.getcwd(), 'res_dlg.py'), 'wb')
	try:
		p= tpl.ToBuffer()
		fp.write('DLG_RES= %s'% repr(p))

	finally: fp.close()

	
#test()

