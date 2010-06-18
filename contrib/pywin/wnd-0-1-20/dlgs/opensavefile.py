
from wnd.wintypes import *
from wnd.controls.base.dialog import BaseCommonDialog
from wnd.controls.base.methods import DialogMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#*****************************************************************************
#*****************************************************************************
"""
 TODO
	- custom filter ++ OFN_EXTENSIONDIFFERENT

NOTES
	
	- the dialog created is actually a child of the 'real' dialogbox.
		All messages must be send to the parent window of the 
		dialogbox

"""

class OpenSaveFile(BaseCommonDialog, DialogMethods):
	def __init__(self, *flags):
		
		BaseCommonDialog.__init__(self, 'modal', *flags)
				
		self._dlgs_flags          =   0
		self._dlgs_hInstance    =   None		## template
		self._dlgs_templatename   =   None
		self._dlgs_bufferErr    =     0
		self._dlgs_initView    =    None


	# OpenSaveFile message handlers ------------------------------------------------------------------------
		
	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==WM_NOTIFY:
			nm= NMHDR.from_address(lp)
			
			if nm.code==CDN_INITDONE:
				## SHELLDLL_DefView" is not yet created. Wild guess here that this is
				## done in response to this message. Otherwise we would have to
				## wait threaded...
				if self._dlgs_initView:
					user32.PostMessageA(hwnd, WND_WM_SETVIEW, 0, 0)
					
		elif msg==WND_WM_SETVIEW:
			if self._dlgs_initView:
				self.SetView(self._dlgs_initView)
				self._dlgs_initView= None
			
	
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		return self.onINIT(hwnd, msg, wp, lp)
	
	def onINIT(self, hwnd, msg, wp, lp): pass		# overwrite
	def onMSG(self, hwnd, msg, wp, lp): pass	# overwrite

				
	# OpenSaveFile methods---------------------------------------------------------------------	
	
	def _dlgs_InitOPENFILENAME(self, hwnd, *flags, **kwargs):
		## helper method. Fills in the OPENFILENAME struct and returns 
		## tuple(ofn, ret-buffer)	
		
		self._dlgs_bufferErr= 0
		
		ofn=OPENFILENAME()
		ofn.lStructSize=sizeof(OPENFILENAME)
		
		ofn.Flags   = OFN_EXPLORER
		for i in flags:
			if i in OFN_VIEWFLAGS:
				self._dlgs_initView= i
			else:
				try:
					ofn.Flags|= OFN_FLAGS[i]
				except: raise ValueError, "invalid flag: %s" % i
				
		ofn.hWndOwner      =   hwnd and hwnd or 0
		ofn.lpstrFilter           =   kwargs.get('filters', 'All Files (*.*)\x00*.*\x00\x00')
		ofn.nFilterIndex       =   kwargs.get('deffilter', 0)
		ofn.lpstrDefExt        =   kwargs.get('defext', '')[:3]
		ofn.nFileExtension =   len(ofn.lpstrDefExt)
		ofn.lpstrInitialDir     =  kwargs.get('initialdir', '')
		ofn.lpstrTitle            =   kwargs.get('title', '')
				
		## setup return buffer
		## make shure required buffer size (on error) can be placed in the buffer
		p= create_string_buffer(max(kwargs.get('buffersize', OFN_FILEBUFFERSIZE+2), 4))
		p.value             =   kwargs.get('deffile', '')
		ofn.lpstrFile    =   addressof(p)
		ofn.nMaxFile   =   sizeof(p) -2	## SaveFile checks for '\x00\x00'
						
		## hook the dialog
		if ofn.Flags & OFN_ENABLEHOOK:
			ofn.Flags |= OFN_ENABLESIZING	# req. to make resizing workwhen hooked
			ofn.lpfnHook = self.GetDlgProc()
		else:
			self._dlgs_initView = None		# reset
		
		## check for template
		if self._dlgs_hInstance:
			if self._dlgs_templatename:
				ofn.Flags      |=  OFN_ENABLETEMPLATE
				ofn.hInstance  =  self._dlgs_hInstance
				ofn.lpTemplateName   =   self._dlgs_templatename
			else:
				ofn.Flags |=   OFN_ENABLETEMPLATEHANDLE 
				ofn.hInstance   =   addressof(self._dlgs_hInstance)
					
		return ofn, p		
	
	
	def RunSaveFile(self, hwnd, *flags, **kwargs):
		ofn, p= self._dlgs_InitOPENFILENAME(hwnd, *flags, **kwargs)
		
		if not comdlg32.GetSaveFileNameA(byref(ofn)):
			errno = comdlg32.CommDlgExtendedError()
			if errno:
				if errno== 12291:	## FNERR_BUFFERTOOSMALL
					self._dlgs_bufferErr= c_ushort.from_address(addressof(p)).value
				from wnd.dlgs.error import ComdlgError
				raise ComdlgError(errno)
			return None
		
		self._dlgs_flags= ofn.Flags					
		return p.value

		
	def RunOpenFile(self, hwnd, *flags, **kwargs):
		ofn, p= self._dlgs_InitOPENFILENAME(hwnd, *flags, **kwargs)
		
		if not comdlg32.GetOpenFileNameA(byref(ofn)):
			errno = comdlg32.CommDlgExtendedError()
			if errno:
				if errno== 12291:	## FNERR_BUFFERTOOSMALL
					self._dlgs_bufferErr= c_ushort.from_address(addressof(p)).value
				from wnd.dlgs.error import ComdlgError
				raise ComdlgError(errno)
			return None
							
		self._dlgs_flags= ofn.Flags
		
		# get files for multiplesel an normalsel
		n= p.raw.index('\x00\x00')
		if ofn.Flags &  OFN_ALLOWMULTISELECT:
			files= p[:n].split('\x00')
		else:
			files= p[:n]
		return files
	
				
	def IsReadOnlyChecked(self):
		return bool(self._dlgs_flags & OFN_READONLY)
	
	def GetBufferError(self):
		return self._dlgs_bufferErr
	
	def SetView(self, view):
		## have to send the message to the parent dialogs "SHELLDLL_DefView"
		## window as WM_COMMAND message
		if self.Hwnd:
			try: view= OFN_VIEWFLAGS[view]
			except: raise "invalid view flag: %s" % view
			h= user32.FindWindowExA(user32.GetParent(self.Hwnd), None, "SHELLDLL_DefView", None)
			if h:
				user32.SendMessageA(h, WM_COMMAND, view, 0)
				return True
		return False
		

#************************************************************************************
#************************************************************************************
class OpenSaveFileFromTemplate(OpenSaveFile):
	def __init__(self, template, *flags):
		OpenSaveFile.__init__(self, *flags)
		self.hInstance= create_string_buffer(template)


#************************************************************************************		
#************************************************************************************
class OpenSaveFileFromInstance(OpenSaveFile):
	def __init__(self, instance, templatename, *flags):
		OpenFile.__init__(self, *flags)
		if isinstance(instance, (int, long)):
			self._dlgs_hInstance= instance
		else: self._dlgs_hInstance= instance._handle
		self.self._dlgs_templatename= emplatename


#************************************************************************************		
#************************************************************************************
OFN_READONLY             = 0x00000001
OFN_OVERWRITEPROMPT      = 0x00000002
OFN_HIDEREADONLY         = 0x00000004
OFN_NOCHANGEDIR          = 0x00000008
OFN_SHOWHELP             = 0x00000010
OFN_ENABLEHOOK           = 0x00000020
OFN_ENABLETEMPLATE       = 0x00000040
OFN_ENABLETEMPLATEHANDLE = 0x00000080
OFN_NOVALIDATE           = 0x00000100
OFN_ALLOWMULTISELECT     = 0x00000200
OFN_EXTENSIONDIFFERENT   = 0x00000400
OFN_PATHMUSTEXIST        = 0x00000800
OFN_FILEMUSTEXIST        = 0x00001000
OFN_CREATEPROMPT         = 0x00002000
OFN_SHAREAWARE           = 0x00004000
OFN_NOREADONLYRETURN     = 0x00008000
OFN_NOTESTFILECREATE     = 0x00010000
OFN_NONETWORKBUTTON      = 0x00020000
OFN_NOLONGNAMES          = 0x00040000 # force no long names for 4.x modules
OFN_EXPLORER             = 0x00080000 # new look commdlg
OFN_NODEREFERENCELINKS   = 0x00100000
OFN_LONGNAMES            = 0x00200000 # force long names for 3.x modules
OFN_ENABLEINCLUDENOTIFY  = 0x00400000 # send include message to callback
OFN_ENABLESIZING         = 0x00800000
OFN_DONTADDTORECENT      = 0x02000000
OFN_FORCESHOWHIDDEN      = 0x10000000 # Show All files including System and hidden files

OFN_EX_NOPLACESBAR       = 0x00000001

OFN_SHAREFALLTHROUGH     = 2
OFN_SHARENOWARN          = 1
OFN_SHAREWARN            = 0

OFN_FILEBUFFERSIZE = 8192



# some -semi official- constants
#OFN_VIEW_LARGEICON=  0x7029
#OFN_VIEW_LIST= 0x702B
#OFN_VIEW_REPORT=  0x702C
#OFN_VIEW_SMALLICON=  0x702A
#OFN_VIEW_THUMBNAILS=  0x702D

OFN_VIEWFLAGS= {
'largeicon': 0x7029,
'list': 0x702B,
'report': 0x702C,
'smallicon': 0x702A,
'thumbnails': 0x702D
}


# notifications
CDN_FIRST  =  0xFFFFFDA7 
CDN_INITDONE  = CDN_FIRST - 0 
CDN_SELCHANGE  = CDN_FIRST - 1 
CDN_FOLDERCHANGE  = CDN_FIRST - 2 
CDN_SHAREVIOLATION  = CDN_FIRST - 3 
CDN_HELP  = CDN_FIRST - 4 
CDN_FILEOK  = CDN_FIRST - 5 
CDN_TYPECHANGE  = CDN_FIRST - 6 
CDN_INCLUDEITEM  = CDN_FIRST - 7 


WM_NOTIFY= 78
WM_COMMAND= 273
WM_APP = 32768

WND_WM_SETVIEW= WM_APP + 1

#-----------------------------------------------------------
class OPENFILENAME(Structure):  
	_fields_=[("lStructSize", DWORD), 
						("hWndOwner", HWND), 
						("hInstance", HINSTANCE), 
						("lpstrFilter", LPCTSTR), 
						("lpstrCustomFilter", DWORD),	## addr of ret buffer 
						("nCustFilter", DWORD), 
						("nFilterIndex", DWORD), 
						("lpstrFile", DWORD),		## addr of ret buffer 
						("nMaxFile", DWORD), 
						("lpstrFileTitle", LPTSTR), 
						("nMaxFileTitle", DWORD), 
						("lpstrInitialDir", LPCTSTR), 
						("lpstrTitle", LPCTSTR), 
						("Flags", DWORD), 
						("nFileOffset", WORD), 
						("nFileExtension", WORD),
						("lpstrDefExt", LPCTSTR), 
						("lCustData", DWORD), 
						("lpfnHook", DIALOGPROC),
						("lpTemplateName", LPCTSTR)] 

#OFNHOOKPROC=WINFUNCTYPE(INT, HWND, UINT, WPARAM, LPARAM)
#-----------------------------------------------------------

OFN_FLAGS={
			'sharewarn' : 0,
			#'ex_noplacesbar' : 1,	## XP ??
			'readonly' : 1,
			#'sharenowarn' : 1,	# ??
			#'sharefallthrough' : 2,	# ??
			'overwriteprompt': 2,
			'hidereadonly' : 4,
			'nochangedir' : 8,
			'showhelp' : 16,
			'hook': 32,
			'novalidate' : 256,
			'allowmultiselect' : 512,
			'pathmustexist' : 2048,
			'filemustexist' : 4096,
			'createprompt' : 8192,
			'shareaware' : 16384,
			'noreadonlyreturn' : 32768,
			'nonetworkbutton' : 131072,
			'nodereferencelinks' : 1048576,
			#'enableincludenotify' : 4194304,
			'dontaddtorecent' : 33554432,
			'forceshowhidden' : 268435456}
