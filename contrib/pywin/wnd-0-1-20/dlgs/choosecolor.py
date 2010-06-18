
from wnd.wintypes import *
from wnd.controls.base.dialog import BaseCommonDialog
from wnd.controls.base.methods import DialogMethods
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#****************************************************************************
#****************************************************************************

class ChooseColor(BaseCommonDialog, DialogMethods):
	def __init__(self, *flags):
		
		BaseCommonDialog.__init__(self, 'modal', *flags)
				
		self._dlgs_hInstance   =  None
		self._dlgs_templatename  = None

		self._dlgs_colors= COLORREF16()
			
			
	# message handlers -----------------------------------------------------------------
	
	# dialog hook
	def onMESSAGE(self, hwnd, msg, wp, lp):
		pass
		## do not return here

	
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		self.onINIT(hwnd, msg, wp, lp)
		return 1
	
	def onINIT(self, hwnd, msg, wp, lp): pass		# overwrite
	def onMSG(self, hwnd, msg, wp, lp): pass	# overwrite


	# methods -------------------------------------------------------------------------
	
	def Run(self, hwnd, *flags, **kwargs):
		
			cc= CHOOSECOLOR()
			cc.lStructSize = sizeof(CHOOSECOLOR)
			cc.hWndOwner = hwnd and hwnd or 0
			
			if flags:
				for i in flags:
					try: cc.Flags |=CC_FLAGS[i]
					except: raise ValueError, "invalid flag: %s" % i
						
			customcolors= kwargs.get('customcolors')
			if customcolors: 	
				for i, x in enumerate(customcolors):
					self._dlgs_colors[i]= x
			cc.lpCustColors=pointer(self._dlgs_colors)
			
			initcolor= kwargs.get('initcolor')			
			if initcolor != None:
				cc.Flags |= CC_RGBINIT
				cc.rgbResult = initcolor
											
			
			## hook the dialog
			if cc.Flags & CC_ENABLEHOOK:
				cc.lpfnHook = self.GetDlgProc()
		
		
			## check for template
			if self._dlgs_hInstance:
				if self._dlgs_templatename:
					cc.Flags      |=  CC_ENABLETEMPLATE
					cc.hInstance  =  self._dlgs_hInstance
					cc.lpTemplateName   =   self._dlgs_templatename
				else:
					cc.Flags |=   CC_ENABLETEMPLATEHANDLE 
					cc.hInstance   =   addressof(self._dlgs_hInstance)
					
			
			
			
			if not comdlg32.ChooseColorA(byref(cc)):
				errno = comdlg32.CommDlgExtendedError()
				if errno:
					from wnd.dlgs.error import ComdlgError
					raise ComdlgError(errno)
				return None
			return cc.rgbResult
	
	
	def __setitem__(self, i, value):
		if isinstance(i, slice):
			start, stop, step= i.indices(16)
			self._dlgs_colors[start:stop]= value
		else: self._dlgs_colors[i]= value

	
	def __getitem__(self, i):
		if isinstance(i, slice):
			start, stop, step= i.indices(16)
			return self._dlgs_colors[start:stop]
		else: return self._dlgs_colors[i]
	
	
#********************************************************************************
#********************************************************************************

class ChooseColorFromTemplate(ChooseColor):
	def __init__(self, template, *flags):
		ChooseColor.__init__(self, *flags)
		self._dlgs_hInstance= create_string_buffer(template)
		
		
#************************************************************************************		
#************************************************************************************

class ChooseColorFromInstance(ChooseColor):
	def __init__(self, instance, templatename, *flags):
		ChooseColor.__init__(self, *flags)
		if isinstance(instance, (int, long)):
			self._dlgs_hInstance= instance
		else: self._dlgs_hInstance= instance._handle
		self.self._dlgs_templatename= emplatename


		
#************************************************************************************		
#************************************************************************************
CC_RGBINIT                     = 0x00000001 # ???
CC_FULLOPEN                 = 0x00000002 # ???
CC_PREVENTFULLOPEN    = 0x00000004 # ???
CC_SHOWHELP                = 0x00000008 # ???
CC_ENABLEHOOK                  = 0x00000010 # ???
CC_ENABLETEMPLATE              = 0x00000020 # ???
CC_ENABLETEMPLATEHANDLE   = 0x00000040 # ???
CC_SOLIDCOLOR                  = 0x00000080 # ???
CC_ANYCOLOR                    = 0x00000100 # ???

CC_FLAGS={'fullopen':CC_FULLOPEN,
'preventfulopen':CC_PREVENTFULLOPEN,
'showhelp':CC_SHOWHELP, 
'solidcolor':CC_SOLIDCOLOR,
'anycolor':CC_ANYCOLOR,
'hook':CC_ENABLEHOOK,
}

COLORREF16= COLORREF *16 # array custom colors 

class CHOOSECOLOR(Structure):
	_fields_=[("lStructSize", DWORD),
						("hWndOwner", DWORD),
						("hInstance", DWORD),
						("rgbResult", DWORD),
						("lpCustColors", POINTER(COLORREF16)), 
						("Flags", DWORD),
						("lCustData", LONG),
						("lpfnHook", DIALOGPROC),
						("lpTemplateName",  LPCTSTR)]



