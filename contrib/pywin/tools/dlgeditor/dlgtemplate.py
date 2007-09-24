"""Bare bones dialog template editor.

LAST VISITED
	16.03.05


NOTES
	To make this editor usable from the framework all control
	classes must be extended to support initializing from
	ID o or hwnd.
	Quite some way to go yet.





Init a new DialogTemplate by specifying 
classname (can be None), title,  style, exstyle, x, y, w, h, font for the main frame.
font is optional and can be Noner. If not None it should be a 4-tuple:
		(name, size, weight, italic).
		where:
			'name' is the font name
			'size' is the font size
			'weight' is any value range 0 through 1000
						supposed to work in steps 100 +
						err.. not working for me so far..
			'italic'  is 0 or 1

For each control to add to the template call the Item method
specifying classname, ID,  title, style, exstyle, x, y, w, h.
You have to pass WS_VISIBLE along with the styles to create the control 
in visible state, otherwise it will be hidden.
WS_CHILD is set by default.

When done with the template either call the Run method to run the
dialog and see if it works or call the ToBuffer method to get
a ctypes string buffer in return containing the bytes of the template.
This string buffer you can pass to any api acepting a buffer
containing a dialog template - usually DialogBoxIndirect e.a-,
or save it to file or whatever. 
The bytes forming the template you will find in stringbuffer.raw


WARNING:
The windows API definitely does not like invalid templates.
Creating a dialog upon an invalid template may dadlock
everything around or cause an empire of evil to arise.
No check is done to make shure you are not doing any
harm to your system. Use at your own risk.

NOTES
	
	- if you use common control classes in the dialog
		you have to call comctl32.InitCommonControls
		to make them work
	
	- Remember to kep a reference to the dialogtemplate, when
		creating a dilalog from it. Otherwise it might get garbage
		collected while running the dialog.
		
	-Take care about your sources in case you want to rework
		or extend a dialog template ;)

	
TODO

"""

from wnd.tools.dlgeditor.wintypes import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


#************************************************************************
# based on DLGTEMPLATEEX ++ DLGITEMTEMPLATEEX
#************************************************************************

class DlgTemplate(object):
		
	def __init__(self): pass
	
	def __nonzero__(self):
			if hasattr(self, '_p'): return True
			return False
	
	def BeginTemplate(self, classname, title, style, exstyle, x, y, w, h, font):
		style |= WS_VISIBLE
		if font: style |= DS_SETFONT
		p= []
		p += WORD_TOBYTES(1)					#  dlgversion
		p += WORD_TOBYTES(0xFFFF)		#  signature
		p += DWORD_TOBYTES(0)				#  helpId		# ignore
		p += DWORD_TOBYTES(exstyle)		# exstyle
		p += DWORD_TOBYTES(style)			# style
		p += WORD_TOBYTES(0)					# nItems bit 16/17
		p += WORD_TOBYTES(x)					# x
		p += WORD_TOBYTES(y)					# y
		p += WORD_TOBYTES(w)					# w
		p += WORD_TOBYTES(h)					# h
		p += [0, 0]												# menu	# not yet
		if classname: p += SZ_TOWBYTES(classname)
		else: p += [0, 0]	
		p += SZ_TOWBYTES(title)
		if font:
			p += WORD_TOBYTES(font[1])	# size
			p += WORD_TOBYTES(font[2])	# weight
			p += WORD_TOBYTES(font[3])	# italic
			p += SZ_TOWBYTES(font[0])		# face name
		# align
		if len(p) % 4:	p += (0, 0)
		self._p = p
		self._nItems = 0
		
	def Item(self, classname, ID, title, style, exstyle, x, y, w, h):
		if not self: raise "no template started"
		self._nItems += 1
		style  |= WS_CHILD
		p= []
		p += DWORD_TOBYTES(0)				# helpId	# ignore
		p += DWORD_TOBYTES(exstyle)		#  extended style
		p += DWORD_TOBYTES(style)			# style  
		p += WORD_TOBYTES(x)					# x
		p += WORD_TOBYTES(y)					# y
		p += WORD_TOBYTES(w)					# w
		p += WORD_TOBYTES(h)					# h
		p += DWORD_TOBYTES(ID)				# ID
		p += SZ_TOWBYTES(classname)
		p += SZ_TOWBYTES(title)
		# dword align		
		if len(p) % 4: p += (0, 0)
		else: p += (0, 0, 0, 0)
		self._p += p
		
	
	def RunModal(self, hwnd=0, lp=0):
		if not self: raise "no template started"
		self._template =  self.ToBuffer()
		#self._template =  self.ToString()
		self._pDlgProc = DIALOGPROC(self.DlgProc)
		result = user32.DialogBoxIndirectParamA(
			0, self._template, hwnd, self._pDlgProc, lp)
		return result

	def RunModeless(self, hwnd=0, lp=0):
		if not self: raise "no template started"
		self._template =  self.ToBuffer()
		self._pDlgProc = DIALOGPROC(self.DlgProc)
		user32.CreateDialogIndirectParamA(
			0, self._template, hwnd, self._pDlgProc, lp)
		
	def DlgProc(self, hwnd, msg, wp, lp):
		self.onMSG(hwnd, msg, wp, lp)
		if msg==WM_CLOSE:
			user32.EndDialog(hwnd, 1)
		elif msg == WM_INITDIALOG:
			return 1
		return 0
		
	def ToBuffer(self):
		if not self: raise "no template started"
		#return buffer(self.ToBuffer())[:]
		self._p[16], self._p[17]= WORD_TOBYTES(self._nItems)
		return buffer(''.join(map(chr, self._p)))[:]
		
	def onMSG(self,  hwnd, msg, wp, lp):
		# overwrite
		pass
	
#************************************************
#************************************************

def test():
	WS_VISIBLE = 268435456
	WS_SYSMENU         = 524288		
	IDOK       = 1
	IDCANCEL   = 2
	font=('arial', 12, 100, 1)
	tpl = DlgTemplate() 
	tpl.BeginTemplate(None, 'test dialog', WS_SYSMENU, 0, 0, 10, 80, 85, font)
	tpl.Item('button', IDOK, 'OK', WS_VISIBLE, 0, 8, 50, 25, 12)
	tpl.Item('button', IDCANCEL, 'cancel', WS_VISIBLE, 0, 45, 50, 25, 12)
	print repr(tpl.ToBuffer())
	print tpl.RunModal()

	import os
	fp= open('%s\\test.dlg' % os.path.split(__file__)[0], 'w')
	try:
		fp.write(repr(tpl.ToBuffer()))
	finally: fp.close()
	
#test()


"""
#********************************************************************************
# based on DLGTEMPLATE ++ DLGITEMTEMPLATE
#********************************************************************************

#class DlgTemplateSimple(DlgTemplate):
		
	def __init__(self):
		DlgTemplate.__init__(self)
	
		
	def BeginTemplate(self, classname, title, style, exstyle, x, y, w, h, font):
						
		style |= WS_VISIBLE
		if font: style |= DS_SETFONT
		p= []
		p += DWORD_TOBYTES(style)			# style
		p += DWORD_TOBYTES(exstyle)		# exstyle
		p += WORD_TOBYTES(0)					# nItems bit 8/19
		p += WORD_TOBYTES(x)					# x
		p += WORD_TOBYTES(y)					# y
		p += WORD_TOBYTES(w)					# w
		p += WORD_TOBYTES(h)					# h
		p += [0, 0]												# menu	# not yet
		if classname: p += SZ_TOWBYTES(classname)
		else: p += [0, 0]	
		p += SZ_TOWBYTES(title)
		if font:
			## does not support weight and italic
			p += WORD_TOBYTES(font[1])	# size
			p += SZ_TOWBYTES(font[0])		# face name
		# align
		if len(p) % 4:	p += (0, 0)
		self._p = p
		self._nItems = 0
		
	def Item(self, classname, ID, title, style, exstyle, x, y, w, h):
		if not self: raise "no template started"
		self._nItems += 1
		style  |= WS_CHILD
		p= []
		p += DWORD_TOBYTES(style)			# style  
		p += DWORD_TOBYTES(exstyle)		#  extended style
		p += WORD_TOBYTES(x)					# x
		p += WORD_TOBYTES(y)					# y
		p += WORD_TOBYTES(w)					# w
		p += WORD_TOBYTES(h)					# h
		p += WORD_TOBYTES(ID)					# ID (WORD in DLGTEMOPLATE)
		p += SZ_TOWBYTES(classname)
		p += SZ_TOWBYTES(title)
		# dword align		
		if len(p) % 4: p += (0, 0)
		else: p += (0, 0, 0, 0)
		self._p += p
		
	
	def ToBuffer(self):
		if not self: raise "no template started"
		self._p[8], self._p[9]= WORD_TOBYTES(self._nItems)
		return buffer(''.join(map(chr, self._p)))[:]
		


def test():
	WS_VISIBLE = 268435456
	WS_SYSMENU         = 524288		
	WS_SIZEBOX      = 262144
	IDOK       = 1
	IDCANCEL   = 2
	font=('arial', 12, 100)
	tpl = DlgTemplateSimple() 
	tpl.BeginTemplate(None, 'test dialog', WS_SYSMENU|WS_SIZEBOX, 0, 0, 100, 80, 185, font)
	tpl.Item('button', IDOK, 'OK', WS_VISIBLE, 0, 8, 50, 25, 12)
	tpl.Item('button', IDCANCEL, 'cancel', WS_VISIBLE, 0, 45, 50, 25, 12)
	#print repr(tpl.ToBuffer())
	tpl.RunModal()

	import os
	fp= open('%s\\test.dlg' % os.path.split(__file__)[0], 'w')
	try:
		fp.write(repr(tpl.ToBuffer()))
	finally: fp.close()
	
#test()


"""
		
#************************************************

#************************************************





