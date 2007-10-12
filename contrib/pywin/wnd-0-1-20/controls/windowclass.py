

from wnd.wintypes import (user32,
												gdi32,
												WNDPROC, 
												WinError,
												GetLastError,
												Structure,
												c_uint,
												c_int,
												HANDLE,
												LPSTR,
												sizeof,
												byref,	)

from wnd import fwtypes as fw
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# use this to register classnames
SZ_WINDOW_CLASS = "wnd_window(%s)"
SZ_DIALOG_CLASS = "wnd_dialog(%s)"
SZ_CONTROL_CLASS = "wnd_control(%s)"
SZ_POPUP_CLASS = "wnd_popup(%s)"


CS_VREDRAW         = 1
CS_HREDRAW         = 2
CS_KEYCVTWINDOW    = 4
CS_DBLCLKS         = 8
CS_OWNDC           = 32
CS_CLASSDC         = 64
CS_PARENTDC        = 128
CS_NOKEYCVT        = 256
CS_NOCLOSE         = 512
CS_SAVEBITS        = 2048
CS_BYTEALIGNCLIENT = 4096
CS_BYTEALIGNWINDOW = 8192
CS_PUBLICCLASS     = 16384
CS_GLOBALCLASS     = CS_PUBLICCLASS
CS_IME             = 65536
CS_DROPSHADOW      = 131072


BACKGROUNDS= ['scrollbar','background',
				'activecaption','inactivecaption','menu','window',
				'windowframe','menutext','windowtext','captiontext',	'activeborder','inactiveborder','appworkspace',
				'highlight','highlighttext','btnface','btnshadow',
				'graytext','btntext']

CLASSTYLES = {'vredraw':1,'hredraw':2,'dblclks':8,'owndc':32,
		'classdc':64,'parentdc':128,'noclose':512,'savebits':2048, 
			'bytealignclient':4096,'bytealignwindow':8192}

SYSTEM_CURSORS= {
				'arrow' : 32512,
				'ibeam' : 32513,
				'wait' : 32514,
				'cross' : 32515,
				'uparrow' : 32516,
				'size' : 32640,
				'icon' : 32641,
				'sizenwse' : 32642,
				'sizenesw' : 32643,
				'sizewe' : 32644,
				'sizens' : 32645,
				'sizeall' : 32646,
				'no' : 32648,
				'hand' : 32649,
				'appstarting' : 32650,
				'help' : 32651}

#****************************************************
class WindowClass(Structure):
	_fields_ = [("cbSize", c_uint),
					("style", c_uint),
					("lpfnWndProc", WNDPROC),
					("cbClsExtra", c_int),
					("cbWndExtra", c_int),
					("hInstance", HANDLE),
					("hIcon", HANDLE),
					("hCursor", HANDLE),
					("hbrBackground", HANDLE),
					("lpszMenuName", LPSTR),
					("lpszClassName", LPSTR),
					("hIconSm", HANDLE)]
		
	def __init__(self): self.cbSize = sizeof(self)
	
	def SetClassName(self, name):
		if len(name) > fw.WND_MAX_CLASSNAME:
			raise ValueError("classname to long: (%s char(s) exceeded)" % len(name)-fw.WND_MAX_CLASSNAME)
		self.lpszClassName = name
	
	def SetWindowProc(self, pWndproc):
		self.lpfnWndProc = pWndproc
	
	def SetBackground(self, background):
		# see if we have to release brushes, too
		if isinstance(background, basestring):
			try: self.hbrBackground= BACKGROUNDS.index(background)
			except: raise ValueError("invalid background: %s" % background)
		else:	
			try: 
				self.hbrBackground = background.handle
				background.Release()
			except: raise ValueError("invalid background: %s" % background)
				
	def SetStyle(self, *styles):
		for i in styles:
			try: self.style |= CLASSTYLES[i]
			except: raise ValueError("invalid style '%s'" % i)
		
	def SetCursor(self, cursor=None):
		# we have to carefull here cos XP is pretty strict with resources,
		# and in case the cursor it registered by gdi TrackHandler it
		# will be closed twice, hanging the process.
		if isinstance(cursor, basestring):
			try: self.hCursor= user32.LoadCursorA(0, SYSTEM_CURSORS[cursor])
			except: raise ValueError, "invalid cursor: %s" % cursor
		elif  cursor: 
			self.hCursor = cursor.handle
			cursor.Release()
		else: self.hCursor= user32.LoadCursorA(0, 32512) # IDC_ARROW
				
	def SetIcons(self, IconLarge, IconSmall=None):
		# >> see SetCursor
		self.hIcon= IconLarge.handle
		if IconSmall:
			self.hIconSm = IconSmall.handle
		if IconSmall:
			if IconSmall != IconLarge:
					IconSmall.Release()
		IconLarge.Release()
	
	
	def SetExtraBytes(self, classextra=0, windowextra=0):
		self.cbClsExtra = classextra
		self.cbWndExtra = windowextra

	def SetInstance(instance):
		if isinstance(instance, (int, long)):
			self.hInstance= instance
		else:
			try: self.hInstance= instance._handle
			except: raise ValueError("invalid instance: %s" % instance)
	
	def Register(self):
		# pretty useless to return the atom here, cos XP does not accept
		# class atoms in CreateWindowEx, we'll see
		self.atom = user32.RegisterClassExA(byref(self))
		if not self.atom:
			raise WinError(GetLastError())
		return self.atom
		
	def GetClassInfo(self, classname):
		if not user32.GetClassInfoExA(None, classname, byref(self)):
			raise WinError(GetLastError())


#**************************************************



#clss = WindowClass()
#clss.setClassName('test')
#clss.setBackground('window')
#clss.setCursor()
#style = 524288		# WS_SYSMENU
#exstyle = 0
#w = BaseWindow(clss, 'test', style, exstyle, 10, 10, 200, 200)
#b = BaseControl(w, 'Button', 'test', 0, 0, 10, 10, 30, 30, True)
#w.run('normal')	


