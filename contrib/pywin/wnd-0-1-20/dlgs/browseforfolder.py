
from wnd.wintypes import pointer, user32
from wnd.api.shell.wintypes import *
from wnd.controls.base.dialog import BaseCommonDialog
from wnd.controls.base.methods import DialogMethods
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class BrowseForFolder(BaseCommonDialog, DialogMethods):
		
	def __init__(self, *flags):
		
		BaseCommonDialog.__init__(self, 'modal', *flags)
		
		self.Hwnd = 0
		self._dlgs_pBffCallBack=BFFCALLBACK(self._BffCallBack)
		self._dlgs_pOldProc = 0
		self._dlgs_fHook = False
		self._dlgs_lastImageIndex= None
		

	# BrowseForFolder message handlers ----------------------------------------------
	
	def _BffCallBack(self, hwnd, msg, wp, lp):
		
		if msg==BFFM_INITIALIZED:
			self.Hwnd = hwnd
			if self._dlgs_fHook:
				self._dlgs_pOldProc = user32.SetWindowLongA(hwnd, -4, self.GetDlgProc())
			self.onINIT(hwnd, msg, wp, lp)
					
		elif msg==BFFM_SELCHANGED:
			pIdl= pointer(ITEMIDLIST.from_address(wp))	## passes IDL in wp
			try:
				self.onMSG(hwnd, "bff_selchanged", pIdl, 0)
			finally:
				Malloc.Free(pIdl)
		
		elif msg==BFFM_VALIDATEFAILEDA:
			result=self.onMSG(hwnd, "bff_validatefailed", c_char_p(wp).value, 0)
			if result==False: return 1
			return 0
		return 0
	
			
	## have to overwrite base proc here
	## and enshure default processing
	def _base_WndProc(self, hwnd, msg, wp, lp):
		BaseCommonDialog. _base_WndProc(self, hwnd, msg, wp, lp)
		return user32.CallWindowProcA(self._dlgs_pOldProc, hwnd, msg, wp, lp)

	
	
	def onINIT(self, hwnd, msg, wp, lp):
		"""Overwrite in derrived classes"""
		pass
	
	
	def onMSG(self, hwnd, msg, wp, lp):
		"""Overwrite in derrived classes"""
		pass
	


	# BrowseForFolder methods ----------------------------------------------
	
	def Run(self, hwnd, *flags, **kwargs):
		
		self._dlgs_lastImageIndex = None
		self._dlgs_fHook = False
		
		shb=BROWSEINFO()
		for i in flags:
			if i=='hook':
				self._dlgs_fHook = True
			try: shb.ulFlags |= BF_FLAGS[i]
			except: raise "invalid flag: %s" % i
					
		shb.hwndOwner=hwnd and hwnd or 0
		shb.lpszTitle = kwargs.get('title', '')
		shb.pidlRoot=  kwargs.get('root', PIDL())
		shb.lpfn=self._dlgs_pBffCallBack
		
		## not very usefull. Holds the displayname of the
		## folder selected on return
		p = create_string_buffer(260)	 # MAX_PATH
		shb.pszDisplayName = addressof(p)
						
		result=shell32.SHBrowseForFolder(byref(shb))
		self.Hwnd=0
		if result:	
			self._dlgs_lastImageIndex = shb.iImage
			pIdl=pointer(ITEMIDLIST.from_address(result))
			return pIdl
		return None	
	
	
	def GetLastImageIndex(self):
		return self._dlgs_lastImageIndex
	
	def SetStatusText(self, text):
		"""Sets the status text."""
		if not self.Hwnd: raise "dialog box is not running"
		p=create_string_buffer(text)
		user32.SendMessageA(self.Hwnd, BFFM_SETSTATUSTEXTA, 0, p)
	
	def DisableOK(self):
		"""Disables the OK button"""
		if not self.Hwnd: raise "dialog box is not running"
		user32.SendMessageA(self.Hwnd, BFFM_ENABLEOK , 0, 0)
	
	def EnableOK(self):
		"""Enables the OK button"""
		if not self.Hwnd: raise "dialog box is not running"
		user32.SendMessageA(self.Hwnd, BFFM_ENABLEOK , 0, 1)
	
	def SetSelection(self, pIdlOrPath):
		if not self.Hwnd: raise "dialog box is not running"
		if isinstance(pIdlOrPath, (str, unicode)):	
			p=create_string_buffer(pIdlOrPath)
			flag=1
		else: 
			p=byref(pIdlOrPath)
			flag=0
		user32.SendMessageA(self.Hwnd, BFFM_SETSELECTIONA , flag, p)
				

#**********************************************************************************
#**********************************************************************************

BFFCALLBACK=WINFUNCTYPE(c_int, HWND, c_uint, LPARAM, LPARAM)
class BROWSEINFO(Structure):
	_fields_ = [("hwndOwner", HWND),
					("pidlRoot", PIDL),
					("pszDisplayName", c_ulong),	# address of return 
																# buffer	
					("lpszTitle", LPCSTR),
					("ulFlags", UINT),
					("lpfn", BFFCALLBACK),
					("lParam", LPARAM),
					("iImage", INT)]


BIF_RETURNONLYFSDIRS =  0x0001  # For finding a folder to start document searching
BIF_DONTGOBELOWDOMAIN = 0x0002  # For starting the Find Computer
BIF_STATUSTEXT      =   0x0004
BIF_RETURNFSANCESTORS = 0x0008
BIF_EDITBOX       =     0x0010
BIF_VALIDATE    =       0x0020   # insist on valid result (or CANCEL)
BIF_BROWSEFORCOMPUTER = 0x1000  # Browsing for Computers.
BIF_BROWSEFORPRINTER =  0x2000  # Browsing for Printers
BIF_BROWSEINCLUDEFILES =0x4000   # Browsing for Everything

BF_FLAGS={'fsancestorssonly':BIF_RETURNFSANCESTORS,
				'donotgobbledomain':BIF_DONTGOBELOWDOMAIN,
				'statustext':BIF_STATUSTEXT,
				'fsdirsonly':BIF_RETURNONLYFSDIRS,
				'editbox':BIF_EDITBOX,
				'validate':BIF_VALIDATE,
				'browseforcomputer':BIF_BROWSEFORCOMPUTER,
				'browseforprinter':BIF_BROWSEFORPRINTER, 
				'includefiles':BIF_BROWSEINCLUDEFILES,
				'hook': 0	 # user defined
				}


# messages send by the dialog
BFFM_INITIALIZED      =  1
BFFM_SELCHANGED    =     2
BFFM_VALIDATEFAILEDA  =  3   # lParam:szPath ret:1(cont),0(EndDialog)

# messages you can send to the dialog
WM_USER = 1024
BFFM_SETSTATUSTEXTA   =  WM_USER + 100
BFFM_ENABLEOK        =   WM_USER + 101
BFFM_SETSELECTIONA   =   WM_USER + 102



#**********************************************************************************
#**********************************************************************************

if __name__=='__main__':
	from wnd.api import shell
	
	def br_oninit(hwnd, msg, wp, lp):
		br.SetSelection('c:\\')
		#br.SetStatusText('Selected Folder: ' )

	def on_br(hwnd, msg, wp, lp):
		if msg=='debug': print lp
		
		if msg=='bff_selchanged':
			try:
				sh.SetCwd(shell.PidlCopy(wp))	# don't forgett to copy :-)
				br.SetStatusText('Selected Folder: %s' % sh.GetParseName())
			except: pass
		
	sh= shell.ShellNamespace()
	
	br= BrowseForFolder()
	br.onMSG= on_br
	br.onINIT= br_oninit
	
	pIdl = br.Run(0, 'editbox', 'validate', 'statustext', 'hook')
	if pIdl:
		sh.SetCwd(pIdl)
		print 'folder selected: "%s"' % sh.GetParseName()
					
	sh.Close()


