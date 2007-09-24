""""

TODO
	- most functions querying attrributes of windows will deadlock if
		the window is hung

"""
from wnd.wintypes import *


ENUMWINDOWSPROC = WINFUNCTYPE(INT, HANDLE, LPARAM)
PROPENUMPROC = WINFUNCTYPE(BOOL, HWND, LPCTSTR, HANDLE)


# import some platformspecific stuff
from wnd.api import winos as _winos
osname = _winos.Name()
if osname== 'NT4':		# note: not implemented currently
	from wnd.api.win_NT4 import platformspecific
	platformclass = platformspecific
else:
	# win98, XP:
	 from wnd.api.win_win98 import platformspecific
	 platformclass = platformspecific


#*************************************************
def ToggleTaskBar():
	result= None
	
	hwnd= user32.FindWindowA('Shell_TrayWnd', 0)
	if hwnd:
		if user32.IsWindowVisible(hwnd):
			user32.ShowWindow(hwnd, 0) #SW_HIDE
			result = False
		else: 
			user32.ShowWindow(hwnd, 5)	# SW_SHOW
			result= True
	return result

def GetText(hwnd):
		n = user32.GetWindowTextLengthA(hwnd)
		if n:		
			p = create_string_buffer(n+ 1)
			caption = user32.GetWindowTextA(hwnd, p, n+1)
			return p.value

def FindWindow(classname='', title=''):
	if not classname: classname = 0
	if not title: title = 0
	hwnd = user32.FindWindowA(classname, title)
	if hwnd:	return hwnd

def SendMessage(hwnd, msg, wp, lp): 
	return user32.SendMessageA(hwnd, msg, wp, lp)

def SendMessageTimeout(hwnd, msg, wp, lp, nTimeout):
	pResult = DWORD()
	SMTO_ABORTIFHUNG        = 2
	user32.SendMessageTimeoutA(hwnd, msg, wp, lp, SMTO_ABORTIFHUNG, nTimeout, byref(pResult))
	return pResult.value

def PostMessage(hwnd, msg, wp, lp):
	if not user32.PostMessageA(hwnd, msg, wp, lp):
		raise 'could not post message'

def GetClassName(hwnd, bufsize=50):
	p = create_string_buffer(bufsize)
	result = user32.GetClassNameA(hwnd, p, bufsize)
	if not result:
		error =  GetLastError()
		if error:
			raise WinError(error)
	return p.value

def GetProcessId(hwnd):
	ProcessId = DWORD()
	user32.GetWindowThreadProcessId(hwnd, byref(ProcessId))
	return ProcessId.value

def GetThreadId(hwnd): return user32.GetWindowThreadProcessId(hwnd, 0)

def GetForegroundWindow(): return user32.GetForegroundWindow()

def SetForegroundWindow(hwnd): user32.SetForegroundWindow(hwnd)

def IsWindow(hwnd):
	if user32.IsWindow(hwnd): return True
	return False

def IsVisible(hwnd):
	if user32.IsWindowVisible(hwnd): return True
	return False

def IsMinimized(hwnd):
	if user32.IsIconic(hwnd): return True
	return False

def IsMaximized(hwnd):
	if user32.IsZoomed(hwnd): return True
	return False

def IsChild(hwnd):
	GWL_STYLE      = -16
	WS_CHILD = 1073741824
	GetWindowLong = user32.GetWindowLongA
	GetWindowLong.restype = DWORD
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_CHILD: return True
	return False

def IsPopup(hwnd):
	GWL_STYLE      = -16
	WS_POPUP           = 2147483648
	GetWindowLong = user32.GetWindowLongA
	#GetWindowLong.restype = DWORD
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_POPUP: return True
	return False

def IsMinable(hwnd):
	GWL_STYLE      = -16
	WS_MINBOX = 131072
	GetWindowLong = user32.GetWindowLongA
	GetWindowLong.restype = DWORD
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_MINBOX: return True
	return False

def IsMaxable(hwnd):
	GWL_STYLE      = -16
	WS_MAXBOX = 65536
	GetWindowLong.restype = DWORD
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_MAXBOX:	return True
	return False

def IsSizeable(hwnd):
	GWL_STYLE      = -16
	WS_SIZEBOX =262144
	GetWindowLong = user32.GetWindowLongA
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_SIZEBOX: return True
	return False

def HasCaption(hwnd):
	GWL_STYLE      = -16
	WS_CAPTION =12582912
	GetWindowLong = user32.GetWindowLongA
	GetWindowLong.restype = DWORD
	style = GetWindowLong(hwnd, GWL_STYLE)
	if style & WS_CAPTION:
		return True
	return False

def GetSize(hwnd):
	rect = RECT()
	user32.GetWindowRect(hwnd, byref(rect))
	return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
	
def Move(hwnd, left, top, width, height):
	user32.MoveWindow(hwnd, left, top, width, height, 1)	

def Maximize(hwnd):
	SC_ZOOM =  61488
	WM_SYSCOMMAND       = 274
	user32.PostMessageA(hwnd, WM_SYSCOMMAND, SC_ZOOM, 0)
	
def Minimize(hwnd):
	SC_ICON = 61472
	WM_SYSCOMMAND       = 274
	user32.PostMessageA(hwnd, WM_SYSCOMMAND, SC_ICON, 0)
	
def Restore(hwnd):
	SC_RESTORE = 61728
	WM_SYSCOMMAND       = 274
	user32.PostMessageA(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
	#SetForegroundWindow(hwnd)

def Close(hwnd):
	SC_CLOSE = 61536
	WM_SYSCOMMAND       = 274
	#user32.PostMessageA(hwnd, WM_SYSCOMMAND, SC_CLOSE, 0)
	pResult = DWORD()
	SMTO_ABORTIFHUNG        = 2
	user32.SendMessageTimeoutA(hwnd, WM_SYSCOMMAND, SC_CLOSE, 0, SMTO_ABORTIFHUNG, 500, byref(pResult))
	

#*************************************************

#*************************************************
class _HandleList(object):
	IsWindowVisible = user32.IsWindowVisible
	ENUM_EXCLUDEHIDDEN = 2
	def __init__(self):
		self._pEnumProc = ENUMWINDOWSPROC(self._EnumProc)
		self._enum_result = []
				
		
	def HandleList(self, flag=None):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		user32.EnumWindows(self._pEnumProc, flag)
		return self._enum_result
	
	def ChildWindows(self, hwnd, flag=None):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		user32.EnumChildWindows(hwnd, self._pEnumProc, flag)
		return self._enum_result
		
	def ThreadWindows(self, hwnd, flag):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		threadId = user32.GetWindowThreadProcessId(hwnd, 0)
		user32.EnumThreadWindows(threadId, self._pEnumProc, flag)
		return self._enum_result
		
	def _EnumProc(self, hwnd, lp):
		if lp== 1:
			if not user32.IsWindowVisible(hwnd): return 1
		elif lp== 2:
			if user32.IsWindowVisible(hwnd): return 1
		self._enum_result.append(hwnd)
		return 1

#h = _HandleList()

#************************************************

#************************************************
class _Properties(object):
	def __init__(self):
		self._pEnumProc = PROPENUMPROC(self.EnumProc)
	
	def EnumProc(self, hwnd, propname, hdata):
		self._enum_result[propname] = hdata
		return 1

	def EnumProps(self, hwnd):
		self._enum_result = {}
		user32.EnumPropsA(hwnd, self._pEnumProc)
		result = self._enum_result
		self.__delattr__('_enum_result')
		return result


#***********************************************
def WaitWindow(caption, timeout=0.5):
	import time
	stop = timeout / 0.05
	flag = False
	i = 0
	while True:
		time.sleep(0.05)
		if handle(caption):
			flag = True
			break
		if i >= stop:
			break
		i += 1
	return flag

#**********************************************		



#************************************************
# init handlelists and properties

_h = _HandleList()
Handles = _h.HandleList
ChildWindows = _h.ChildWindows
ThreadWindows = _h.ThreadWindows

_prop = _Properties()
PropertyList = _prop.EnumProps



#************************************************
# init platformspecific stuff

_p = platformclass()
EnumProcesses = _p.processlist
EnumThreads = _p.threadlist
#EnumThreadWindows = _p.threadwindows
ExeFilePath = _p.exefilepath
ExeFileName = _p.exefilename
Handle = _p.handle


#for i in EnumThreads():
