"""
NOTES
	
	- the parfent window has to be created with the 'dialoglike' style set to make
		the keyboard interface work

"""


from future.utils import raise_
from wnd.wintypes import *
from wnd.controls.base.dialog import BaseCommonDialog
from wnd.controls.base.methods import DialogMethods
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#****************************************************************************
#****************************************************************************

class FindText(BaseCommonDialog, DialogMethods):
	def __init__(self, *flags):
		
		BaseCommonDialog.__init__(self, 'modeless', *flags)
				
		self._dlgs_fr= None
		self._dlgs_pParentProc= WNDPROC(self._dlgs_ParentOnMsg)
		self._dlgs_pOldParentProc= 0
		self._dlgs_findbuffer= None

		self._dlgs_hInstance   =  None
		self._dlgs_templatename  = None
		
		
		
	# message handlers -----------------------------------------------------------------
	
	def _dlgs_ParentOnMsg(self, hwnd, msg, wp, lp):
		
		if msg== FR_MSG:
			
			fr = FINDREPLACE.from_address(lp)
			if fr.Flags & FR_FINDNEXT:
				if self._dlgs_CheckReturnBuffer()==False: return
				self.onMSG(self.Hwnd, "fr_findnext", self._dlgs_findbuffer.value, self._dlgs_Get_FR_Flags(fr.Flags))
			
							
			elif fr.Flags & FR_DIALOGTERM:
				## restore parent proc
				user32.SetWindowLongA(hwnd, -4, self._dlgs_pParentProc)
				self._dlgs_pParentProc= 0
				self._dlgs_fr= None
				self._dlgs_findbuffer= None
				self.onMSG(hwnd, "fr_close", 0, 0)
		
		return user32.CallWindowProcA(self._dlgs_pOldParentProc, hwnd, msg, wp, lp)
	
	
	# dialog hook
	def onMESSAGE(self, hwnd, msg, wp, lp):
		pass
		## do not return here

		
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		## check 'down' radiobox (feels more natural)
		self.SetSearchDirection('down')
		self.onINIT(hwnd, msg, wp, lp)
		return 1
	
	def onINIT(self, hwnd, msg, wp, lp): pass		# overwrite
	def onMSG(self, hwnd, msg, wp, lp): pass	# overwrite


	# methods -------------------------------------------------------------------------
	
	def Run(self, hwnd, what, *flags, **kwargs):
		
		self._dlgs_fr= self._dlgs_InitFINDREPLACE(hwnd, what, *flags, **kwargs)
		self.Hwnd = comdlg32.FindTextA(byref(self._dlgs_fr))
		if self.Hwnd:
			## subclass parent
			self._dlgs_pOldParentProc= user32.SetWindowLongA(hwnd, -4, self._dlgs_pParentProc)
		else:
			errno = comdlg32.CommDlgExtendedError()
			if errno:
				from wnd.dlgs.error import ComdlgError
				raise ComdlgError(errno)
		return self.Hwnd		
	
	
	def SetBufferSize(self, n):
		if self.Hwnd:
			self._dlgs_findbuffer = create_string_buffer('', size=n +1)
			self._dlgs_fr.lpstrFindWhat = addressof(self._dlgs_findbuffer)
			self._dlgs_fr.wFindWhatLen = sizeof(self._dlgs_findbuffer)
			hwnd= self.GetDlgItem(edt1)
			if hwnd:
				user32.GetWindowTextA(hwnd, self._dlgs_findbuffer, sizeof(self._dlgs_findbuffer))
				return True
			return False
					
	
	def SetSearchDirection(self, direction):
		hwnd1, hwnd2 = self.GetDlgItem(rad1), self.GetDlgItem(rad2)
		if hwnd1 and hwnd2:
			if direction=='up':
				hwnd1, hwnd2= hwnd2, hwnd1
			self.SendMessage(hwnd1, BM_SETCHECK, 0, 0)
			self.SendMessage(hwnd2, BM_SETCHECK, BST_CHECKED, 0)
		
	def GetSearchDirection(self):
		hwnd = self.GetDlgItem(rad1)
		if hwnd:
			if self.SendMessage(hwnd, BM_GETCHECK, 0, 0) & BST_CHECKED:
				return 'up'
			return 'down'
						
		
	def CheckWholeWord(self):
		hwnd = self.GetDlgItem(chx1)
		if hwnd:
			self.SendMessage(hwnd, BM_SETCHECK, BST_CHECKED, 0)
			return True
		return False
	
	def IsWholeWordChecked(self):
		hwnd = self.GetDlgItem(chx1)
		if hwnd:
			return bool(self.SendMessage(hwnd, BM_GETCHECK, 0, 0) & BST_CHECKED)
	
	def CheckMatchCase(self):
		hwnd = self.GetDlgItem(chx2)
		if hwnd:
			self.SendMessage(hwnd, BM_SETCHECK, BST_CHECKED, 0)
			return True
		return False
	
	def IsMatchCaseChecked(self):
		hwnd = self.GetDlgItem(chx2)
		if hwnd:
			return bool(self.SendMessage(hwnd, BM_GETCHECK, 0, 0) & BST_CHECKED)
	
	
	def Close(self):
		self.PostMessage(self.Hwnd, self.Msg.WM_COMMAND, IDABORT, 0)


	# helper methods ------------------------------------------------------------------------------

	def _dlgs_InitFINDREPLACE(self, hwnd, what, *flags, **kwargs):
		fr = FINDREPLACE()
		fr.lStructSize  = sizeof(FINDREPLACE)
		fr.hwndOwner = hwnd		## required
				
		fr.Flags= 0
		
		if flags:	
			for i in flags:
				try: fr.Flags |= FR_FLAGS[i]
				except:raise_(ValueError, "invalid flag: %s" % i)
				
						
		## check for template
		if self._dlgs_hInstance:
			if self._dlgs_templatename:
				fr.Flags |=FR_ENABLETEMPLATE
				ft.hInstance= self._dlgs_hInstance
				fr.lpTemplateName= self._dlgs_templatename
			else:
				fr.Flags |=FR_ENABLETEMPLATEHANDLE 
				fr.hInstance= addressof(self._dlgs_hInstance)
				
		# hook the dialog		
		if fr.Flags & FR_ENABLEHOOK:
			fr.lpfnHook = self.GetDlgProc()
						
		## setup buffer for find string
		self._dlgs_findbuffer= create_string_buffer(what, size=kwargs.get('buffersize', 1024) +1)
		fr.lpstrFindWhat = addressof(self._dlgs_findbuffer)
		fr.wFindWhatLen = sizeof(self._dlgs_findbuffer)
		
		return fr		## remember to keep reference
	
		
	def _dlgs_Get_FR_Flags(self, fr_flags):
		out= []
		if fr_flags & FR_DOWN: out.append('down')
		else: out.append('up')
		if fr_flags & FR_MATCHCASE: out.append('matchcase')
		if fr_flags & FR_WHOLEWORD: out.append('wholeword')
		return out

	
		
	def _dlgs_CheckReturnBuffer(self):
		hwnd= self.GetDlgItem(edt1)
		if hwnd:
			n = self.SendMessage(hwnd, EM_LINELENGTH, 0, 0)
			if n > len(self._dlgs_findbuffer):
				return self.onMSG(self.Hwnd, "fr_buffererror", 'find', (n, len(self._dlgs_findbuffer) -1))		
	
#********************************************************************************
#********************************************************************************

class FindTextFromTemplate(FindText):
	def __init__(self, template, *flags):
		FindText.__init__(self, *flags)
		self._dlgs_hInstance= create_string_buffer(template)
		
		
#************************************************************************************		
#************************************************************************************

class FindTextFromInstance(FindText):
	def __init__(self, instance, templatename, *flags):
		FindText.__init__(self, *flags)
		if isinstance(instance, (int, long)):
			self._dlgs_hInstance= instance
		else: self._dlgs_hInstance= instance._handle
		self.self._dlgs_templatename= emplatename


		
#************************************************************************************		
#************************************************************************************

class FINDREPLACE(Structure):
	_fields_ = [("lStructSize", DWORD),
						("hwndOwner", HWND),
						("hInstance", HINSTANCE),
						("Flags", DWORD),
						("lpstrFindWhat", DWORD),	# addr ret buffer
						("lpstrReplaceWith", LPTSTR),
						("wFindWhatLen", WORD),
						("wReplaceWithLen", WORD),
						("lCustData", LPARAM),
						("lpfnHook", WNDPROC),
						("lpTemplateName", LPCTSTR)]

FR_DOWN        =                 0x00000001
FR_WHOLEWORD        =            0x00000002
FR_MATCHCASE       =             0x00000004
FR_FINDNEXT         =            0x00000008
FR_REPLACE             =         0x00000010
FR_REPLACEALL      =             0x00000020
FR_DIALOGTERM       =            0x00000040
FR_SHOWHELP            =         0x00000080
FR_ENABLEHOOK       =            0x00000100
FR_ENABLETEMPLATE    =           0x00000200
FR_NOUPDOWN         =            0x00000400
FR_NOMATCHCASE       =           0x00000800
FR_NOWHOLEWORD      =            0x00001000
FR_ENABLETEMPLATEHANDLE   =      0x00002000
FR_HIDEUPDOWN         =          0x00004000
FR_HIDEMATCHCASE     =           0x00008000
FR_HIDEWHOLEWORD     =           0x00010000

FR_FLAGS= {'noupdown':FR_NOUPDOWN,
'nomatchcase':FR_NOMATCHCASE,
'nowholeword':FR_NOWHOLEWORD,
'hideupdown':FR_HIDEUPDOWN,
'hidematchcase':FR_HIDEMATCHCASE,
'hidewholeword':FR_HIDEWHOLEWORD,
'hook': FR_ENABLEHOOK,
'showhelp':FR_SHOWHELP,
}


FINDMSGSTRING = "commdlg_FindReplace"
FR_MSG = user32.RegisterWindowMessageA(FINDMSGSTRING)  

IDABORT    = 3
chx1     =   1040
chx2   =     1041
edt1   =     1152
rad1    =    1056
rad2    =    1057

EM_LINELENGTH          = 193
BM_SETCHECK = 241
BM_GETCHECK = 240

BST_CHECKED       = 1