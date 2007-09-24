"""
TODO:
	- test on XP
	- drawitem, measureitem, menuchar 
			(unicode and ansi versions of GCS_VERB and GCS_HELPTEXT)
	- could not get 'NewFolder' verb to work


"""

from wnd.api.shell.wintypes import *
from wnd.api.shell.functions import (GetIShellFolder,
																	PidlSplit,
																	PidlCopy,
																	PidlFree)
from  wnd.api import ole		## have to call OleInitialize to make clipboard
													## work with context menu
import traceback


#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

## not documented
## returns tuple(IContextMenu, version)
def GetContextMenuVersion(Folder, pIdl, version):
	if not version in (None, 1, 2, 3):
			raise ValueError, "invalid version: %s" % version
	
	Menu = POINTER(IContextMenu)()
	if isinstance(pIdl, Array):
		Folder.GetUIObjectOf(0, len(pIdl), byref(pIdl[0]), 
	REFIID(IContextMenu._iid_), byref(c_uint()), byref(Menu))
	else:
		Folder.GetUIObjectOf(0, 1, byref(pIdl), 
		REFIID(IContextMenu._iid_), byref(c_uint()), byref(Menu))
	if version==1:
		return Menu, 1
	
	Menu2 = POINTER(IContextMenu2)()
	try:
		Menu.QueryInterface(byref(IContextMenu2._iid_), byref(Menu2))
	except Exception, d:
		if version==None:
			return Menu, 1
		else:
			raise Exception, d
	del Menu
	if version== 2:
		return Menu2, 2

	Menu3 = POINTER(IContextMenu3)()
	try:
		Menu2.QueryInterface(byref(IContextMenu3._iid_), byref(Menu3))
	except Exception, d:
		if version==None:
			return Menu2, 2
		else:
			raise Exception, d
	del Menu2
	return Menu3, 3

#***************************************************************************
#***************************************************************************

S_OK= 0
E_NOTIMPL    = -2147467263
E_FAIL       = 0x80004005L

VK_SHIFT    = 16
VK_CONTROL  = 17

CMIC_MASK_PTINVOKE    =  0x20000000
CMIC_MASK_SHIFT_DOWN  =   0x10000000
CMIC_MASK_CONTROL_DOWN  =  0x40000000


#define GCS_VERBA        0x00000000     // canonical verb
#define GCS_HELPTEXTA    0x00000001     // help text (for status bar)
#define GCS_VALIDATEA    0x00000002     // validate command exists
#define GCS_VERBW        0x00000004     // canonical verb (unicode)
#define GCS_HELPTEXTW    0x00000005     // help text (unicode version)
#define GCS_VALIDATEW    0x00000006     // validate command exists (unicode)
#define GCS_UNICODE      0x00000004     // for bit testing - Unicode string

GCS_VERB   =     0x00000000
GCS_VERBW = 4

GCS_HELPTEXT = 1		# ansi version ## unicode does not work on win98
GCS_HELPTEXTW  =  0x00000005
GCS_UNICODE    =  0x00000004

MIN_MENU_ID =1				## shell context menu
MAX_MENU_ID =29999	## shell context menu


#CMF_DEFAULTONLY         1		##
#CMF_VERBSONLY    =       2			##
#CMF_EXPLORE       =      4
#CMF_NOVERBS      =       8			##
#CMF_CANRENAME   =        16		##
#CMF_NODEFAULT    =       32
#CMF_INCLUDESTATIC  =     64
#CMF_RESERVED     =       0xffff0000      // View specific
CM_FLAGS= {'defaultonly':1,'verbsonly':2,'explore':4,'noverbs':8,
						'canrename':16,'nodefault':32,'includestatic':64}


#define CMDSTR_NEWFOLDERA   "NewFolder"
#define CMDSTR_VIEWLISTA    "ViewList"
#define CMDSTR_VIEWDETAILSA "ViewDetails"
#define CMDSTR_NEWFOLDERW   L"NewFolder"
#define CMDSTR_VIEWLISTW    L"ViewList"
#define CMDSTR_VIEWDETAILSW L"ViewDetails"

#***************************************************************************
#***************************************************************************

class ShellContextMenu(object):
	
	def __init__(self, minID=MIN_MENU_ID, maxID=MAX_MENU_ID):
						
		self._minID = minID
		self._maxID = maxID
		self._pOldWndProc= 0
		self._pWndproc= WNDPROC(self._MenuProc)
		
		self._version= None
		self._pIContextMenu= None
		self._lastError= None
		
				
	
	def onMSG(self, hwnd, msg, wp, lp):
		# overwrite
		pass
	

	def Reset(self):
		if self._pIContextMenu:
			del self._pIContextMenu
			self._pIContextMenu= None
		self._pOldWndProc= 0
	
	
	def SetLastError(self, exc, value):
		if exc:
			self.lastError= ''.join(traceback.format_exception_only(exc, value))
		else:
			self.lastError= None
			
	def GetLastError(self):
		error= self.lastError
		self.lastError= None
		return error
	
	
	## minimum/maximum allowable for client code
	def GetMinMenuID(self): return self._maxID + 1
	def GetMaxMenuID(self): return self._minID - 1
	
	
	def SubclassParent(self, window):
		if not self._pIContextMenu:
			raise RuntimeError, "no context menu initialised"
		
		if not self._pOldWndProc:
			self._pOldWndProc = user32.SetWindowLongA(window.Hwnd, -4, self._pWndproc)
			if not self._pOldWndProc:
				raise RuntimeError, "could not subclass window"
		else:
			raise RuntimeError, "there is alreaddy a window subclassed"
		
	
	def RestoreParentProc(self, window):
		if not self._pIContextMenu:
			raise RuntimeError, "no context menu initialised"
		
		if self._pOldWndProc:
			user32.SetWindowLongA(window.Hwnd, -4, self._pOldWndProc)
			self._pOldWndProc= 0
		else:
			raise RuntimeError, "no proc found to restore"
	
	
	def QueryContextMenu(self, pIdlParent, pIdl, hMenu, *flags, **kwargs):
		
		flag= 0
		for i in flags:
			try: flag |= CM_FLAGS[i]
			except: raise ValueError, "invalid flag: %s" % i
		
		self.lastError= None
		try:
			Folder= GetIShellFolder(pIdlParent)
			result= GetContextMenuVersion(Folder, pIdl, kwargs.get('version', None))
			self._pIContextMenu, self._version= result
			self._pIContextMenu.QueryContextMenu(
									hMenu, 
									0, 
									self._minID, 
									self._maxID,
									flag)
		except Exception, d:
			self.SetLastError(Exception, d)
		return not self.lastError
		
						
	def _GetCommandString(self, flag, ID, szeof):
		## work around on buggy context menu handlers
		## (see http://blogs.msdn.com/oldnewthing/ "How to host an IContextMenu,
		## part 6 - Displaying menu help")
		# flag should be the GCS_* ansi version

		hr= S_OK
		
		p = create_string_buffer(szeof)
		try:
			self._pIContextMenu.GetCommandString(
				ID - self._minID,  flag, 0, addressof(p),szeof-1)
			hr= S_OK
		except Exception, d: 
			hr= E_NOTIMPL
		if p[0]=='\x00' and hr==S_OK:
			hr= E_NOTIMPL
		else:
			return hr, p.value
				
		if hr:
			## try unicode version
			## very! unelegant mapping to and and from unicode
			p = create_unicode_buffer(unicode(''*(szeof), LOCALE), size=szeof)
			try:
				self._pIContextMenu.GetCommandString(
					ID - self._minID,  flag | GCS_UNICODE, 0, addressof(p),szeof-1)
				hr= S_OK
			except Exception, d: 
				hr= E_NOTIMPL
			if p[0]=='\x00' and hr==S_OK:
				hr= E_NOTIMPL
			else:
				out= []
				for i in p.value:
					out.append(chr(ord(i)))
				return hr, ''.join(out)
		
		return hr, ''
		
	
	
	def GetCommandString(self, ID):
		if not self._pIContextMenu:
			raise RuntimeError, "no context menu initialised"
		
		self.lastError= None
		
		if self.IsMenuID(ID):
			hr, name= self._GetCommandString(GCS_VERB, ID, 41)
			if hr:
				self.SetLastError(WinError(hr), None)
			return name
		return ''	
								
		
	def InvokeCommand(self, ID, point=None):
		if not self._pIContextMenu:
			raise RuntimeError, "no context menu initialised"
		
		self.lastError= None
				
		ici = CMINVOKECOMMANDINFOEX()
		ici.nShow = 1		##SW_SHOWNORMAL
		if point:
			ici.ptInvoke= point
			ici.fMask |= CMIC_MASK_PTINVOKE
		if HIBYTE(user32.GetKeyState(VK_SHIFT)): 
			ici.fMask |= CMIC_MASK_SHIFT_DOWN
		if HIBYTE(user32.GetKeyState(VK_CONTROL)):
			ici.fMask |= CMIC_MASK_CONTROL_DOWN
		
		if isinstance(ID, str):
			## never worked for me
			p= create_string_buffer(ID)
			ici.lpVerb = addressof(p)
		else:
			if self.IsMenuID(ID):
				ici.lpVerb = ID - self._minID
			
		if ici.lpVerb:
			try:									
				self._pIContextMenu.InvokeCommand(byref(ici))
			except Exception, d:
				self.SetLastError(Exception, d)
			else:
				return True
		return False
		
	
	def IsMenuID(self, ID):
		if isinstance(ID, (int, long)):
			return ID <= self._maxID and ID >= self._minID
		return False
	
	
	def _HandleMenuMsg(self, msg, wp, lp):
		if self._version== 2:
			try:
				self._pIContextMenu.HandleMenuMsg(msg, wp, lp)
			except: pass
		elif self._version== 3:
			## always errors here, but processes correctly ?? (4-bytes in excess)
			lResult= c_long()	
			try:
				self._pIContextMenu.HandleMenuMsg2(msg, wp, lp, byref(lResult))
			except: pass
		
		
	
	def _MenuProc(self, hwnd, msg, wp, lp):
		## TODO
		if msg==43:		# WM_DRAWITEM
			self._HandleMenuMsg(msg, wp, lp)
			return 0
		## TODO
		elif msg==44:	# WM_MEASUREITEM
			self._HandleMenuMsg(msg, wp, lp)
			return 0
		
		if msg==287:		# WM_MENUSELECT
			ID, flag= LOWORD(wp), HIWORD(wp)
			if not flag & 16:		# MF_POPUP	## for popups position, not ID is passed
				## try to get help string
				if  self.IsMenuID(ID):
					hr, name= self._GetCommandString(GCS_HELPTEXT, ID, 512)
					self.onMSG(hwnd, "shell_contextmenu", "helpstring", name)
					return hr
						
		elif msg==279:		# WM_INITMENUPOPUP
			self._HandleMenuMsg(msg, wp, lp)
			return 1
									
		else:
			return user32.CallWindowProcA(self._pOldWndProc, hwnd, msg, wp, lp)
			
		
