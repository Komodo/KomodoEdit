
"""
Bit premature and hardly tested


TODO:
	- keyboard for modeless sheet (PSM_ISDIALOGMESSAGE)

NOT IMPLEMENTED

	PSN_GETOBJECT
	PSM_ISDIALOGMESSAGE


"""

from wnd.wintypes import (DIALOGPROC,
													Structure,
													Union,
													sizeof,
													byref,
													POINTER,
													pointer,
													WINFUNCTYPE,
													addressof,
													DIALOGPROC,
													user32,
													comctl32,
													create_string_buffer,
													c_char,
													c_void_p,
													NMHDR,
													INT,
													LPARAM,
													DWORD,
													WORD,
													SHORT,
													LPSTR,
													HANDLE,
													UINT,
													HWND,
													LPARAM,
													UINT_MAX
													)
from wnd import fwtypes as fw


##::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class PropertySheet(object):
	
	
	def __init__(self, title, parent, *flags, **kwargs):
		
		self.Hwnd= 0
		self._client_pages= []
		self._client_mode= 'modal'
		self._client_fReboot= None
				
		self._client_pCallback= PROPSHEETPROC(self._client_Callback)
		#self._client_pChildCallback= PROPSHEETPAGEPROC(self._client_ChildCallback)
		self._client_pDlgProc= DIALOGPROC(self._client_DlgProc)
		self._client_pOldDlgProc= 0
				
		
		self._client_p= PROPSHEETHEADER()
		self._client_p.dwFlags= PSH_PROPSHEETPAGE | PSH_USECALLBACK
		self._client_p.pfnCallback= self._client_pCallback
		self._client_p.pszCaption= title
		
		if parent != None: self._client_p.hwndParent= parent.Hwnd
		
		if flags:
			for i in flags:
				try: 
					self._client_p.dwFlags |= FLAGS_PROPHEADER[i]
					if i=='modeless':
						self._client_mode= i
				except: raise ValueError, "invalid flag: %s" % i
		
		icon = kwargs.get('icon', None)
		if icon:
			self._client_p.dwFlags |= PSH_USEHICON
			self._client_p.u1.hIcon= icon.handle
		
		self._client_p.u2.nStartPage= kwargs.get('startPage', 0)

		## wizard only
		bmpHeader = kwargs.get('bmpHeader', None)
		if bmpHeader:
				self._client_p.dwFlags |= PSH_USEHBMHEADER|PSH_HEADER
				self._client_p.u5.hbmHeader= bmpHeader.handle
		bmpWatermark = kwargs.get('bmpWatermark', None)
		if bmpWatermark:
				self._client_p.dwFlags |= PSH_USEHBMWATERMARK|PSH_WATERMARK
				self._client_p.u4.hbmWatermark= bmpWatermark.handle


				
	
	# message handlers ------------------------------------------------------------
	
	def _client_Callback(self, hwnd, msg, lp):
		if msg== PSCB_INITIALIZED:
			self.Hwnd= hwnd
			# subclass the propsheet
			self._client_pOldDlgProc= user32.SetWindowLongA(hwnd, -4, self._client_pDlgProc)
			self.onMSG(hwnd, "initialized", lp, 0)
		#	elif msg==PSCB_PRECREATE:
		#		self.onMSG(hwnd, "precreate", lp, 0)
	
	
	#def _ChildCallback(self, hwnd, msg, lp):
	#
	#	if msg==PSPCB_CREATE:
	#		self.onMSG(hwnd, "createpage", lp, 0)
	#	elif msg==PSPCB_RELEASE :
	#		self.onMSG(hwnd, "destroypage", lp, 0)	
		
	
	def _client_DlgProc(self, hwnd, msg, wp, lp):
		
		if msg==2:		## WM_DESTROY
			## reset
			try:
				self.onMSG(hwnd,"destroy", 0, 0)
			finally: 
				self.Hwnd= 0
				self._client_fReboot= None
			
				
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= 1
	
				if msgr.msg==WM_NOTIFY:
					nm=NMHDR.from_address(msgr.lParam)
					
					if nm.code==PSN_APPLY:
						result= self.onMSG(hwnd,"apply", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and PSNRET_INVALID_NOCHANGEPAGE  or PSNRET_NOERROR)
						if result != False:
							if self._client_mode=='modeless':
								user32.DestroyWindow(self.Hwnd)
				
					elif nm.code==PSN_HELP:
						self.onMSG(hwnd,"help", msgr.hwndFrom, 0)
					
					elif nm.code==PSN_KILLACTIVE:
						result= self.onMSG(hwnd,"killactive", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and 1 or 0)
					
					elif nm.code==PSN_QUERYCANCEL:
						result= self.onMSG(hwnd,"querycancel", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and 1 or 0)
						if result != False:
							if self._client_mode=='modeless':
								user32.DestroyWindow(self.Hwnd)
					
					elif nm.code==PSN_RESET:
						psn= PSHNOTIFY.from_address(lp)
						result= self.onMSG(hwnd,"reset", msgr.hwndFrom, psn.lParam and 'cancel' or 'close')
										
					elif nm.code==PSN_SETACTIVE:
						self.onMSG(hwnd, "setactive", msgr.hwndFrom, 0)

					elif nm.code==PSN_WIZBACK:
						result= self.onMSG(hwnd,"wizback", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and -1 or 0)
				
					elif nm.code==PSN_WIZNEXT:
						result= self.onMSG(hwnd,"wiznext", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and -1 or 0)

					elif nm.code==PSN_WIZFINISH:
						result= self.onMSG(hwnd,"wizfinish", msgr.hwndFrom, 0)
						user32.SetWindowLongA(hwnd, DWL_MSGRESULT, result==False and 1 or 0)
						if result != False:
							if self._client_mode=='modeless':
								user32.DestroyWindow(self.Hwnd)
						
					return 1
			return 0
								
		return user32.CallWindowProcA(self._client_pOldDlgProc, hwnd, msg, wp, lp)
	
	
		
	def onMSG(self, hwnd, msg, wp, lp):
		print hwnd, msg, wp, lp
		pass
	
	
	# property sheet methods----------------------------------------------------------------
	
	def Page(self, dlg, *flags, **kwargs):
		
				
		if len(self._client_pages) +1 >= MAXPROPPAGES:
			raise RuntimeError, "maximum number of pages exceeded"
		
		
		p= PROPSHEETPAGE()
		p.dwFlags= PSP_DLGINDIRECT 
		#| PSP_USECALLBACK
		#p.pfnCallback= self._client_pChildCallback
		if flags:
			for i in flags:
				try: self._client_p.dwFlags |= FLAGS_PROPPAGE[i]
				except: raise ValueError, "invalid flag: %s" % i
			
		
		## resource buffer has to be writable, so set the it 
		## as attribute the structure carries along
		tpl= dlg.GetTemplate()
		if tpl==None:
			raise ValueError, "dialog does not contain template"
		p._pWritable= create_string_buffer(tpl)
		p.u1.pResource= addressof(p._pWritable)
		
		p.pfnDlgProc= dlg.GetDlgProc()

		icon = kwargs.get('icon', None)
		if icon:
			p.dwFlags |= PSP_USEHICON
			p.u3.hIcon= icon.handle

		title = kwargs.get('title', None)	## overwrites dlgbox title
		if title:
			p.dwFlags |= PSP_USETITLE
			p.pszTitle= title
		
		lParam= kwargs.get('lp', 0)
		
		## wizard only
		headerTitle = kwargs.get('headerTitle', None)
		if headerTitle:
			p.dwFlags |= PSP_USEHEADERTITLE
			p.pszHeaderTitle= headerTitle
		headerSubTitle = kwargs.get('headerSubTitle', None)
		if headerTitle:
			p.dwFlags |= PSP_USEHEADERSUBTITLE
			p.pszHeaderSubTitle= headerSubTitle

		self._client_pages.append(p)

	
	def Run(self):
		
		if self.Hwnd:
			raise RuntimeError, "property sheet is alreaddy created"
		
		if not self._client_pages:
			raise RuntimeError, "property sheet must have at least one page"
		
		self._client_p.nPages = len(self._client_pages)
		arr= (PROPSHEETPAGE*self._client_p.nPages)(*self._client_pages)
		self._client_p.u3.ppsp= pointer(arr[0])
		result= comctl32.PropertySheetA(byref(self._client_p))
		if self._client_mode=='modeless': 
			if result==ID_PSRESTARTWINDOWS:
				return 'restart'
			elif result==ID_PSREBOOTSYSTEM:
				return 'reboot'
			elif result: 
				return 'ok'
			return 'cancel'
			
		else:
			if result:	return result
		
	
	def AddPage(self, dlg, *flags, **kwargs):
		## the propsheet takes care about the handle of the page
		
		if self.Hwnd:
			self._client_page(dlg, *flags, **kwargs)
			hPage= comctl32.CreatePropertySheetPage(byref(self._client_pages[-1]))
			if hPage:
				user32.SendMessageA(self.Hwnd, PSM_ADDPAGE, 0, hPage)
				return True
		return False
	
	def RemovePage(self, i):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_REMOVEPAGE, i, 0)
			try:
				del self._client_pages[i]
			except: raise ValueError, "no such page: %s" % i
	
	def PageChanged(self, hwnd):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_CHANGED, hwnd, 0)
		
	def PageUnchanged(self, hwnd):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_UNCHANGED, hwnd, 0)
	
	def CancelToClose(self):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_CANCELTOCLOSE , 0, 0)
	
	def PressButton(self, button):
		if self.Hwnd:
			try: iButton= PROP_BUTTONS.index(button)
			except: raise ValueError, "invalid burron: %s" % button
			user32.SendMessageA(self.Hwnd, PSM_PRESSBUTTON, iButton, 0)
			
	def SetTitle(self, title, proptitle=False):
		#PSH_PROPTITLE   =        0x00000001
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_SETTITLE, proptitle and 1 or 0, title)
	
	
	def GetReboot(self):
		return self._client_fReboot
	
	def Reboot(self):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_REBOOTSYSTEM , 0, 0)
			self._client_fReboot= 'reboot'
	
	def Restart(self):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_RESTARTWINDOWS, 0, 0)
			self._client_fReboot= 'restart'
	
	def SetFinishText(self, text):
		if self.Hwnd:
			user32.SendMessageA(self.Hwnd, PSM_SETFINISHTEXT , 0, text)
	
	def SetWizardButtons(self, *buttons):
		if self.Hwnd:
			btns= {'back': 1, 'next':2, 'finish':4, 'disablefinish':8}
			flag= 0
			for i in buttons:
				try: flag |= btns[i]
				except: raise ValueError, "invalid button: %s" % i
			## docs claim PostMessage is the right choice here
			user32.PostMessageA(self.Hwnd, PSM_SETWIZBUTTONS , 0, flag)

	def Select(self, i):
		 if self.Hwnd:
			return bool(user32.SendMessageA(self.Hwnd, PSM_SETCURSEL, i, 0))
	
	def SelectHwnd(self, hwnd):
		 if self.Hwnd:
			return bool(user32.SendMessageA(self.Hwnd, PSM_SETCURSEL, 0, hwnd))
	
	def GetCurrentPage(self):
		if self.Hwnd:
			return user32.SendMessageA(self.Hwnd, PSM_GETCURRENTPAGEHWND, 0, 0)
		
	def GetTabControl(self):
		if self.Hwnd:
			result= user32.SendMessageA(self.Hwnd, PSM_GETTABCONTROL, 0, 0)
			if result:
				from wnd.controls import tab
				t= tab.TabFromHandle(result)
				fw.SetFlagMsgReflect(t, False)
				return t
		
	def QuerySiblings(self, param1, param2):
		result= user32.SendMessageA(self.Hwnd, PSM_QUERYSIBLINGS , param1, param2)
		
		
#***********************************************************************************
#***********************************************************************************

class PSHNOTIFY(Structure):
	_fields_ = [("hdr", NMHDR),
						("lParam", LPARAM)]

## some real beauties

class u1(Union):
	_fields_ = [("pszTemplate", LPSTR),
						("pResource", DWORD)]	## LPDLGTEMPLATE 
	
class u2(Union):
	_fields_ = [("hIcon", HANDLE),
						("pszIcon", LPSTR)]

class PROPSHEETPAGE(Structure):
	def __init__(self):
		self.dwSize= sizeof(self)

PROPSHEETPAGEPROC= WINFUNCTYPE(UINT, HWND, UINT, POINTER(PROPSHEETPAGE))
PROPSHEETPROC= WINFUNCTYPE(INT, HWND, UINT, LPARAM)



PROPSHEETPAGE._fields_= [
	("dwSize", DWORD),
	("dwFlags", DWORD),
	("hInstance", HANDLE),
	("u1", u1),
	("u2", u2),
	("pszTitle", LPSTR),
	("pfnDlgProc", DIALOGPROC),
	("lParam", LPARAM),
	("pfnCallback", PROPSHEETPAGEPROC),
	("pcRefParent", POINTER(UINT)),
	("pszHeaderTitle", LPSTR),
	("pszHeaderSubTitle", LPSTR)]


class PROPSHEETHEADER(Structure):
	def __init__(self):
		self.dwSize= sizeof(self)
	
	class u1(Union):
		 _fields_ = [("hIcon", HANDLE),
							("pszIcon", LPSTR)]
	class u2(Union):
		 _fields_ = [("nStartPage", UINT),
							("pStartPage", LPSTR)]
	
	class u3(Union):
		 _fields_ = [("ppsp", POINTER(PROPSHEETPAGE)),	## array PROPPAGE structs
							("phpage", DWORD)]		## addr array of PROPPAGE handles
	class u4(Union):
		 _fields_ = [("hbmWatermark", HANDLE),
							("pszbmWatermark", LPSTR)]
	class u5(Union):
		 _fields_ = [("hbmHeader", HANDLE),
							("pszbmHeader", LPSTR)]
	
	
	_fields_= [
	("dwSize", DWORD),
	("dwFlags", DWORD),
	("hwndParent", HWND),
	("hInstance", HANDLE),
	("u1", u1),
	("pszCaption", LPSTR),
	("nPages", UINT),
	("u2", u2),
	("u3", u3),
	("pfnCallback", PROPSHEETPROC),
	("u4", u4),
	("hplWatermark", HANDLE),
	("u5", u5)
	]



WM_NOTIFY = 78


DWL_MSGRESULT = 0
MAXPROPPAGES     =       100

PSP_DEFAULT      =          0x00000000
PSP_DLGINDIRECT     =       0x00000001
PSP_USEHICON       =        0x00000002
PSP_USEICONID      =         0x00000004
PSP_USETITLE       =         0x00000008
PSP_RTLREADING    =          0x00000010

PSP_HASHELP      =           0x00000020
PSP_USEREFPARENT    =        0x00000040
PSP_USECALLBACK    =         0x00000080
PSP_PREMATURE      =         0x00000400

#if (_WIN32_IE >= 0x0400)
#----- New flags for wizard97 --------------
PSP_HIDEHEADER    =          0x00000800
PSP_USEHEADERTITLE   =       0x00001000
PSP_USEHEADERSUBTITLE    =   0x00002000


## property sheet notifications
PSN_FIRST      =         UINT_MAX-200
PSN_LAST   =              UINT_MAX-299


PSN_SETACTIVE    =          PSN_FIRST-0
PSN_KILLACTIVE    =         PSN_FIRST-1
# PSN_VALIDATE    =           PSN_FIRST-1
PSN_APPLY       =           PSN_FIRST-2
PSN_RESET     =             PSN_FIRST-3
# PSN_CANCEL   =              PSN_FIRST-3
PSN_HELP       =            PSN_FIRST-5
PSN_WIZBACK     =           PSN_FIRST-6
PSN_WIZNEXT      =          PSN_FIRST-7
PSN_WIZFINISH   =           PSN_FIRST-8
PSN_QUERYCANCEL =           PSN_FIRST-9
#if (_WIN32_IE >= 0x0400)
PSN_GETOBJECT     =         PSN_FIRST-10
#endif // 0x0400


PSH_DEFAULT    =         0x00000000
PSH_PROPTITLE   =        0x00000001
PSH_USEHICON     =       0x00000002
PSH_USEICONID    =       0x00000004
PSH_PROPSHEETPAGE    =   0x00000008
PSH_WIZARDHASFINISH   =  0x00000010
PSH_WIZARD        =      0x00000020
PSH_USEPSTARTPAGE   =    0x00000040
PSH_NOAPPLYNOW    =      0x00000080
PSH_USECALLBACK   =      0x00000100
PSH_HASHELP      =       0x00000200
PSH_MODELESS     =       0x00000400
PSH_RTLREADING    =      0x00000800
PSH_WIZARDCONTEXTHELP =  0x00001000
#if (_WIN32_IE >= 0x0400)
#----- New flags for wizard97 -----------
PSH_WIZARD97    =        0x00002000  
# 0x00004000 was not used by any previous release
PSH_WATERMARK    =       0x00008000
PSH_USEHBMWATERMARK  =   0x00010000  # user pass in a hbmWatermark instead of pszbmWatermark
PSH_USEHPLWATERMARK  =   0x00020000  
PSH_STRETCHWATERMARK  =  0x00040000  # stretchwatermark also applies for the header
PSH_HEADER      =        0x00080000
PSH_USEHBMHEADER  =      0x00100000
PSH_USEPAGELANG   =      0x00200000  # use frame dialog template matched to page


PSPCB_RELEASE     =      1
PSPCB_CREATE      =      2
PSCB_INITIALIZED	 = 1
PSCB_PRECREATE  =  2

WM_USER = 1024
PSM_REMOVEPAGE    =       WM_USER + 102
PSM_ADDPAGE      =        WM_USER + 103

PSM_SETCURSEL     =       WM_USER + 101
PSM_REMOVEPAGE    =       WM_USER + 102
PSM_ADDPAGE      =        WM_USER + 103
PSM_CHANGED    =          WM_USER + 104
PSM_RESTARTWINDOWS  =     WM_USER + 105
PSM_REBOOTSYSTEM     =    WM_USER + 106
PSM_CANCELTOCLOSE =       WM_USER + 107
PSM_QUERYSIBLINGS   =     WM_USER + 108
PSM_UNCHANGED    =        WM_USER + 109
PSM_APPLY      =          WM_USER + 110
PSM_SETTITLEA   =         WM_USER + 111
PSM_SETTITLEW      =      WM_USER + 120
#ifdef UNICODE
#PSM_SETTITLE      =       PSM_SETTITLEW
#else
PSM_SETTITLE     =        PSM_SETTITLEA
#endif
PSM_SETWIZBUTTONS   =     WM_USER + 112
PSM_PRESSBUTTON  =        WM_USER + 113



PSM_SETCURSELID   =      WM_USER + 114
PSM_SETFINISHTEXTA   =   WM_USER + 115
PSM_SETFINISHTEXTW  =    WM_USER + 121

#ifdef UNICODE
#PSM_SETFINISHTEXT       PSM_SETFINISHTEXTW
#else
PSM_SETFINISHTEXT  =     PSM_SETFINISHTEXTA
#endif
PSM_GETTABCONTROL   =    WM_USER + 116
PSM_ISDIALOGMESSAGE  =   WM_USER + 117
PSM_GETCURRENTPAGEHWND  =   WM_USER + 118

ID_PSRESTARTWINDOWS  =   0x2
ID_PSREBOOTSYSTEM    =   ID_PSRESTARTWINDOWS | 0x1

PSNRET_NOERROR     =            0
PSNRET_INVALID       =          1
PSNRET_INVALID_NOCHANGEPAGE  =   2


PROP_BUTTONS= ['back','next','finish','ok','applynow','cancel','help']

FLAGS_PROPHEADER= {
'proptitle': PSH_PROPTITLE,
'hashelp': PSH_HASHELP,
'modeless': PSH_MODELESS ,
'noapplynow': PSH_NOAPPLYNOW,
'rtlreading': PSH_RTLREADING,
'wizard97': PSH_WIZARD97,
'stretchwatermark': PSH_STRETCHWATERMARK, 
}

FLAGS_PROPPAGE= {
'hashelp': PSP_HASHELP,
'premature': PSP_PREMATURE,
'rtlreading': PSP_RTLREADING,
'hideheader': PSP_HIDEHEADER
}

WIZ_CXDLG       =        276
WIZ_CYDLG      =         140

WIZ_CXBMP      =         80

WIZ_BODYX      =         92
WIZ_BODYCX      =        184

PROP_SM_CXDLG    =       212
PROP_SM_CYDLG     =      188

PROP_MED_CXDLG    =      227
PROP_MED_CYDLG   =       215

PROP_LG_CXDLG     =      252
PROP_LG_CYDLG     =      218      


