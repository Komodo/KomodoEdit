"""

Sorry, the SDK docs are a mess, so here is a probbably more usable one

class MENUEX_TEMPLATE_HEADER(Structure):
	_fields_ = [("wVersion", WORD),		# must be 1
					("wOffset", WORD),			# offset to the first
																	# MENUEX_TEMPLATE_ITEM (usually 4)
					("dwHelpId", DWORD)]		# helpID for the menu

class MENUEX_TEMPLATE_ITEM(Structure):
	_fields_ = [("dwType", DWORD),		# one or more of the MFT_* flags
					("dwState", DWORD),			# one or more of the MFS_* flags
					("uId", UINT),						# the items ID
					("bResInfo", WORD),			# 0x80, 0x01 or 0
					("szText", WCHAR*1),		# variable length title array
					("dwHelpId", DWORD)		# only included for items starting a \
																	# submenu


A menu template consuists of one MENUEX_TEMPLATE_HEADER, followed
by any number of MENUEX_TEMPLATE_ITEM structures. 
Each MENUEX_TEMPLATE_ITEM must be DWORD aligned. If an item
starts a submenu bResInfo must be 0x80 and dwHelpId is included,
following emidiately the other members wich should be DWORD aligned
BEFORE (!!) appending dwHelpId
To end a menu or submenu bResInfo must be 0x01.
The menu must be treminated appending one MENUEX_TEMPLATE_ITEM
with bResInfo set to 0x01.

"""
 


from wnd.tools.dlgeditor.wintypes import (user32, 
																			create_string_buffer,
																			WM_INITDIALOG,
																			WORD_TOBYTES,
																			DWORD_TOBYTES,
																			SZ_TOWBYTES,
																			)

from wnd.tools.dlgeditor.dlgeditor import DlgEditor 
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

__all__= ['MFT_STRING', 'MFT_BITMAP', 'MFT_MENUBARBREAK',
'MFT_MENUBREAK', 'MFT_OWNERDRAW', 'MFT_RADIOCHECK', 'MFT_SEPARATOR', 'MFT_RIGHTORDER', 'MFT_RIGHTJUSTIFY', 'MFS_NORMAL', 'MFS_DISABLED', 'MFS_CHECKED', 'MFS_HILITE', 'MFS_DEFAULT', 'MF_BEGIN', 'MF_END', 'MF_NONE', 'Dlg', 'MnuTemplate']


MFT_STRING         = 0
MFT_BITMAP         = 4
MFT_MENUBARBREAK   = 32
MFT_MENUBREAK      = 64
MFT_OWNERDRAW      = 256
MFT_RADIOCHECK     = 512
MFT_SEPARATOR      = 2048
MFT_RIGHTORDER     = 8192
MFT_RIGHTJUSTIFY   = 16384

MFS_NORMAL= 0
MFS_DISABLED  =  3
MFS_CHECKED   = 8
MFS_HILITE    = 128
MFS_DEFAULT   = 4096

MF_NONE          =  0
MF_BEGIN             = 1
MF_END             = 128


class _Dlg(DlgEditor):
	def __init__(self):
		DlgEditor.BeginTemplate(self, None, 'menu template', 0,0,200,25, None, 'sysmenu')
	def RunModal(self, hwnd, hMenu): DlgEditor.RunModal(self, hwnd, hMenu)
	def RunModeless(self, hwnd, hMenu): DlgEditor.RunModeless(self, hwnd, hMenu)
	def onMSG(self, hwnd, msg, wp, lp):
		if msg== WM_INITDIALOG:
			if lp: 
				if not user32.SetMenu(hwnd, lp):
					raise "could not set menu"
Dlg = _Dlg()		# overwrite onMSG for further processing, like hosting it


def GetMenuFlags(*flags):
	out= {'type':{},'state':{},'flag':{}}
	for name, value in globals().items():
		flag= False
		if name.startswith('MFT_'): flag= 'type'
		elif name.startswith('MFS_'): flag= 'state'
		elif name.startswith('MF_'): flag= 'flag'
		if flag:	
			if 'noprefix' in flags:
				name= name[3:]
			if 'lowercase' in flags:
				name= name.lower()
			out[flag][name]=value
	return out	

#r= GetMenuFlags('lowercase', 'noprefix')

#*********************************************

class Template(object):
	
	def __init__(self): pass
		
	def BeginTemplate(self):
		p= []
		p+= WORD_TOBYTES(1)						# version
		p+= WORD_TOBYTES(4)						# offset
		p+= DWORD_TOBYTES(0)					# helpId	# ignore ??
		self._p= p
	
	def Item(self, ID, title, itemType, itemState, menuFlag):
		p= []
		p+= DWORD_TOBYTES(itemType)		# type
		p+= DWORD_TOBYTES(itemState)		# state
		p+= DWORD_TOBYTES(ID)					# ID
		p+= WORD_TOBYTES(menuFlag)		# resinfo
		p+= SZ_TOWBYTES(title)						# title
		# dword align item	
		if len(p) % 4: p += (0, 0)
		if menuFlag== MF_BEGIN:
			p+= DWORD_TOBYTES(0)				# helpId	# ignore
		self._p += p

	def ToBuffer(self):
		# terminate this thing
		self._p +=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128, 0, 0, 0)
		#self.Item(0, '', 0, 0, MF_END) ## do not use
		return create_string_buffer(''.join(map(chr, self._p)))



#**********************

class MnuTemplate(Template):
	
	def __init__(self):
		Template.__init__(self)

	def __nonzero__(self):
		if hasattr(self, 'level'): return True
		return False
	
	def BeginTemplate(self):
		self.level= 0
		Template.BeginTemplate(self)
	
	def ToBuffer(self):
		if not self: raise "no template started"
		return buffer(Template.ToBuffer(self))[:]
				
	def RunModeless(self, hwnd=0):
		if not self: raise "no template started"
		self._template =  self.ToBuffer()
		hMenu= user32.LoadMenuIndirectA(self._template)
		if hMenu:
			Dlg.RunModeless(hMenu)
		else: raise"could not create menu"
	
	def RunModal(self, hwnd=0):
		if not self: raise "no template started"
		self._template =  self.ToBuffer()
		hMenu= user32.LoadMenuIndirectA(self._template)
		if hMenu:
			Dlg.RunModal(hwnd, hMenu)
		else: raise"could not create menu"
				
	def Item(self, ID, title, itemType, itemState=0, menuFlag=0):
		if not self: raise "no template started"
		if self.level==0 and menuFlag != MF_BEGIN:
			raise "item without menu"
		if menuFlag== MF_BEGIN: 
			self.level += 1
		if menuFlag== MF_END: 
			self.level -= 1
		if self.level <0: raise "end without begin"
		Template.Item(self, ID, title, itemType, itemState, menuFlag)
		


	




def test():
	m= MnuTemplate()
	m.BeginTemplate()
	
	
	m.Item(100, 'faaaXag', MFT_STRING, 0, MF_BEGIN)
	
	m.Item(101, 'bbbX', MFT_STRING, 0)
	
	m.Item(100, 'faaaXag', MFT_RADIOCHECK, MFS_DISABLED, MF_BEGIN)
	m.Item(102, 'cc', MFT_STRING, 0, MF_END)
	
	m.Item(102, 'cc', MFT_STRING, 0, MF_END)

	m.Item(100, 'faaaXag', MFT_STRING, 0, MF_BEGIN)
	m.Item(101, '', MFT_SEPARATOR)
	m.Item(101, 'bbbX', MFT_STRING, 4096)
	m.Item(102, 'cc', MFT_STRING, 0, MF_END)
	
	
	m.RunModal()



#test()

