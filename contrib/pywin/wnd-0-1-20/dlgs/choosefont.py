
from wnd.wintypes import *
from wnd.controls.base.dialog import BaseCommonDialog
from wnd.controls.base.methods import DialogMethods
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#************************************************************************************
#************************************************************************************
class ChooseFont(BaseCommonDialog, DialogMethods):
	def __init__(self, *flags):
				
		BaseCommonDialog.__init__(self, 'modal', *flags)
		
		self._dlgs_logfont        =  None
		self._dlgs_hInstance   =  None
		self._dlgs_templatename  = None
		self._dlgs_colorref      =  0
					
		
	# ChooseFont message handlers -------------------------------
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		pass
	
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		return self.onINIT(hwnd, msg, wp, lp)
	
	def onINIT(self, hwnd, msg, wp, lp): pass		# overwrite
	def onMSG(self, hwnd, msg, wp, lp): pass	# overwrite

	
	# ChooseFont methods -------------------------------
	
	def GetLastColor(self): 
		return self._dlgs_colorref
	
	
	def Run(self, hwnd, *flags, **kwargs):
		
		cf= CHOOSEFONT()
		
		if flags:
			for i in flags:
				try: cf.Flags |=choosefont_flags[i]
				except: raise "invalid flag: %s" % i
		else: cf.Flags |= CF_SCREENFONTS
		
		cf.hWndOwner = hwnd and hwnd or 0
		cf.hDC                = kwargs.get('hdc', 0)
		limitsize             = kwargs.get('limitsize')
		if limitsize:
			cf.Flags |= CF_LIMITSIZE 
			cf.SizeMin, cf.nSizeMax = limitsize
		
		## have to keep the pointer to logfont alive throughout
		## the livetime of the dialog
		logfont     = kwargs.get('logfont')
		if logfont:
			cf.Flags |= CF_INITTOLOGFONTSTRUCT
			self._dlgs_logfont = logfont
		else: 
			self._dlgs_logfont = LOGFONT()
		cf.lpLogFont = pointer(self._dlgs_logfont)
				
		## check for template
		if self._dlgs_hInstance:
			if self._dlgs_templatename:
				cf.Flags |=CF_ENABLETEMPLATE
				cf.hInstance= self._dlgs_hInstance
				cf.lpTemplateName= self._dlgs_templatename
			else:
				cf.Flags |=CF_ENABLETEMPLATEHANDLE 
				cf.hInstance= addressof(self._dlgs_hInstance)
		if limitsize:
			cf.nSizeMin, cf.nSizeMax= limitsize
			cf.Flags |=CF_LIMITSIZE 
				
		## hook the dialog
		if cf.Flags & CF_ENABLEHOOK:
			cf.lpfnHook= self.GetDlgProc()
							
		## run it
		if not comdlg32.ChooseFontA(byref(cf)):
			errno = comdlg32.CommDlgExtendedError()
			if errno:
				from wnd.dlgs.error import ComdlgError
				raise ComdlgError(errno)
			return None
		self._dlgs_colorref= cf.rgbColors
		return self._dlgs_logfont



#************************************************************************************
#************************************************************************************
class ChooseFontFromTemplate(ChooseFont):
	def __init__(self, template, *flags):
		ChooseFont.__init__(self, *flags)
		self._dlgs_hInstance= create_string_buffer(template)
		

#************************************************************************************		
#************************************************************************************
class ChooseFontFromInstance(ChooseFont):
	def __init__(self, instance, templatename, *flags):
		ChooseFont.__init__(self, *flags)
		if isinstance(instance, (int, long)):
			self._dlgs_hInstance= instance
		else: self._dlgs_hInstance= instance._handle
		self.self._dlgs_templatename= emplatename
		

#************************************************************************************		
#************************************************************************************

CF_SCREENFONTS                 = 0x00000001
CF_PRINTERFONTS                = 0x00000002
CF_BOTH                        = CF_SCREENFONTS 
CF_SHOWHELP                    = 0x00000004
CF_ENABLEHOOK                  = 0x00000008
CF_ENABLETEMPLATE              = 0x00000010
CF_ENABLETEMPLATEHANDLE        = 0x00000020
CF_INITTOLOGFONTSTRUCT         = 0x00000040
CF_USESTYLE                    = 0x00000080
CF_EFFECTS                     = 0x00000100
CF_APPLY                       = 0x00000200
CF_ANSIONLY                    = 0x00000400
CF_SCRIPTSONLY                 = CF_ANSIONLY
CF_NOVECTORFONTS               = 0x00000800
CF_NOOEMFONTS                 = CF_NOVECTORFONTS
CF_NOSIMULATIONS               = 0x00001000
CF_LIMITSIZE                   = 0x00002000
CF_FIXEDPITCHONLY              = 0x00004000
CF_WYSIWYG                     = 0x00008000 
CF_FORCEFONTEXIST              = 0x00010000
CF_SCALABLEONLY                = 0x00020000
CF_TTONLY                      = 0x00040000
CF_NOFACESEL                   = 0x00080000
CF_NOSTYLESEL                  = 0x00100000
CF_NOSIZESEL                   = 0x00200000
CF_SELECTSCRIPT                = 0x00400000
CF_NOSCRIPTSEL                 = 0x00800000
CF_NOVERTFONTS                 = 0x01000000

class LOGFONT(Structure):  
	_fields_=[("lfHeight", LONG), 
						("lfWidth", LONG), 
						("lfEscapement", LONG), 
						("lfOrientation", LONG), 
						("lfWeight", LONG), 
						("lfItalic", BYTE), 
						("lfUnderline", BYTE),
						("lfStrikeOut", BYTE), 
						("lfCharSet", BYTE), 
						("lfOutPrecission", BYTE), 
						("lfClipPrecision", BYTE), 
						("lfQuality", BYTE),
						("lfPitchAndFamily", BYTE), 
						("lfFaceName", CHAR *32)]		

class CHOOSEFONT(Structure):  
	_fields_=[("lStructSize", DWORD), 
						("hWndOwner", HWND),
						("hDC", HDC), 
						("lpLogFont", POINTER(LOGFONT)), 
						("iPointSize", INT), 
						("Flags", DWORD), 
						("rgbColors", DWORD), 
						("lCustData", LPARAM),
						("lpfnHook", DIALOGPROC), 
						("lpTemplateName", LPCTSTR), 
						("hInstance", HINSTANCE),
						("lpszStyle", LPTSTR),
						("nFontType", WORD), 
						("Alignment", WORD), 
						("nSizeMin", INT),
						("nSizeMax", INT)]
	def __init__(self): self.lStructSize= sizeof(self)

choosefont_flags={
			'both' : 1,
			'screenfonts' : 1,
			'printerfonts' : 2,
			'showhelp' : 4,
			'hook' : 8,
			#'enabletemplate' : 16,
			#'enabletemplatehandle' : 32,
			#'inittologfontstruct' : 64,
			'usestyle' : 128,
			'effects' : 256,
			'apply' : 512,
			'ansionly' : 1024,
			'scriptsonly' : 1024,
			#'nooemfonts' : 2048,
			'novectorfonts' : 2048,
			'nosimulations' : 4096,
			'limitsize' : 8192,
			'fixedpitchonly' : 16384,
			'wysiwyg' : 32768,
			'forcefontexist' : 65536,
			'scalableonly' : 131072,
			'ttonly' : 262144,
			'nofacesel' : 524288,
			'nostylesel' : 1048576,
			'nosizesel' : 2097152,
			'selectscript' : 4194304,
			'noscriptsel' : 8388608,
			'novertfonts' : 16777216}
