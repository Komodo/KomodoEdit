"""win98 specific process enumeration and functions based upon."""


#from name.api.wintypes import *
from ctypes import Structure, c_ulong as DWORD, c_long as LONG, \
c_char as CHAR, c_int as INT, windll as windll, c_buffer as BUFFER, \
WINFUNCTYPE, sizeof, byref


HANDLE = DWORD
LPARAM = LONG

_kernel32 = windll.kernel32
_user32 = windll.user32

#**************************************************

#**************************************************
class PROCESSENTRY32(Structure):
	_fields_ = [("dwSize", DWORD),
					("cntUsage", DWORD),
					("th32ProcessID", DWORD),
					("th32DefaultHeapID", DWORD),
					("th32ModuleID", DWORD),
					("cntThreads", DWORD),
					("th32ParentProcessID", DWORD),
					("pcPriClassBase", LONG),
					("dwFlags", DWORD),
					("szexeFile", CHAR * 260)] #MAX_PATH
	def __init__(self):
		Structure.__init__(self)
		self.dwSize = sizeof(self)
	def byref(self): return byref(self)

 
class THREADENTRY32(Structure):
	_fields_ = [("dwSize", DWORD),
							("cntUsage", DWORD),
							("th32ThreadID", DWORD),
							("th32OwnerProcessID", DWORD),
							("tpBasePri", LONG),
							("TpDeltaPri", LONG),
							("dwFlags", DWORD)]
	def __init__(self):
		Structure.__init__(self)
		self.dwSize = sizeof(self)
	def byref(self): return byref(self)

ENUMWINDOWSPROC = WINFUNCTYPE(INT, HANDLE, LPARAM)
#*************************************************

#*************************************************
class ThSnapShot(object):
	"""Wrapper around Toolhelp32Snapshot handle, to get it 
	closed in a generator loop."""
	def __init__(self, flag):
		self.handle = _kernel32.CreateToolhelp32Snapshot(flag, 0)
		if not self.handle:
			raise 'could not create snapshot'
	def __del__(self): self.close()
	def close(self): 
		
		if not _kernel32.CloseHandle(self.handle):
			raise 'could not close handle'
		
#***************************************************

#***************************************************
class platformspecific(object):
	IsWindowVisible = _user32.IsWindowVisible
	GetWindowText=windll.user32.GetWindowTextA
	GetWindowTextLength=windll.user32.GetWindowTextLengthA
	
	GETFILENAME = lambda self, path: path[path.rfind('\\')+1: path.rfind('.') > 0 and path.rfind('.') or None]
	
	
	ENUM_FINDFIRST = 1
	ENUM_EXCLUDEHIDDEN = 2
	
	WLDCRD_NONE = 0
	WLDCRD_LEFT = 32
	WLDCRD_RIGHT = 64
	WLDCRD_BOTH = 128
	
	def __init__(self):
		self._p_enum_threadwindows = ENUMWINDOWSPROC(self._threadwindowsproc)
		self._p_enum_wildcards = ENUMWINDOWSPROC(self.__wildcardsproc)
		
	
	def processlist(self):
		"""Yields 'processId', 'exefilepath' of currently running
		processes. """
		
		pe = PROCESSENTRY32()
  		snapshot = ThSnapShot(2)	 # TH32CS_SNAPPROCESS
  		result = _kernel32.Process32First(snapshot.handle, pe.byref())
		PE32_NEXT = _kernel32.Process32Next
		while result:
			yield pe.th32ProcessID, pe.szexeFile
			result = PE32_NEXT(snapshot.handle, pe.byref())
			
		
	def threadlist(self):
		"""Yields 'threadId', 'ownerProcessId' of currently running
		threads."""
		result = []
		te = THREADENTRY32()
		snapshot = ThSnapShot(4) # TH32CS_SNAPTHREAD
  		result = _kernel32.Thread32First(snapshot.handle, te.byref())
		TE32_NEXT = _kernel32.Thread32Next
		while result:
			yield te.th32ThreadID, te.th32OwnerProcessID
			result = TE32_NEXT(snapshot.handle, te.byref())
		
		
	def threadwindows(self, hwnd, *flags):
		"""Returns a list of handles of threadwindows
		of the window with the given hwnd. You can specify a set
		of flags to alter the behaviour of 'threadwindows'.
		Valid flags are:
				
		'threadId' 
			indicates that the hwnd parameter points to a thread id
			instead of a hwnd
		'excludehidden' 
			returns WS_VISIBLE style windows only
		'findfirst'
			emidiately returns with the first window found 
		"""
		
		tw_flags = {
		'threadId' : 0,
		'hwnd' : 0,
		'findfirst' : self.ENUM_FINDFIRST,
		'excludehidden' : self.ENUM_EXCLUDEHIDDEN,
		}
		flag = 0
		for i in flags:
			try: flag |= tw_flags[i]
			except:	raise '"%s" invalid flag' % i
				
		threadId = hwnd
		if not 'threadId' in flags:
			threadId = _user32.GetWindowThreadProcessId(hwnd, 0)
			
		self._enum_result = []
		_user32.EnumThreadWindows(threadId, self._p_enum_threadwindows, flag)
		result = self._enum_result
		self.__delattr__('_enum_result')
		return result
	
	
	def _threadwindowsproc(self, hwnd, lparam):
		if lparam & self.ENUM_EXCLUDEHIDDEN:
			if self.IsWindowVisible(hwnd): 
				self._enum_result.append(hwnd)
				if lparam & self.ENUM_FINDFIRST:
					return 0
			return 1
		else:
			self._enum_result.append(hwnd)
			if lparam & self.ENUM_FINDFIRST:
				return 0
			return 1
	
	
	def exefilepath(self, hwnd):
		"""Returns the path to the executable, that created 
		the window with the given hwnd."""
		out = None
		processId = DWORD()
		_user32.GetWindowThreadProcessId(hwnd, byref(processId))
		processId = processId.value
		for pId, exepath in self.processlist():
			if pId == processId:
				out = exepath
				break
		return out
		
	def exefilename(self, hwnd):
		"""Same as exefilepath but returning the filename only."""
		path = self.exefilepath(hwnd)
		if path:
			return self.GETFILENAME(path)
	
	
	def handle(self, caption):
		"""Returns the handle of the first visible window matching
		caption. Left/right wildcards supported. Use '=exename' to
		find the first visible window created by the executable
		'exename'. """
		caption = caption.lower()
				
		if caption[0]=='*' and caption[-1]=='*':
			return self.__matchwildcard(
				caption[1:-1], self.WLDCRD_BOTH
				)
		
		elif caption[0]=='*' and caption[-1] !='*': 
			return self.__matchwildcard(
				caption[1: ], self.WLDCRD_LEFT
				)
		
		elif caption[0] not in '*=' and caption[-1] == '*': 
			return self.__matchwildcard(
				caption[ :-1], self.WLDCRD_RIGHT
				)
			
		elif caption[0] == '=':
			caption = caption[1:]
			for processId, path in self.processlist():
				if self.GETFILENAME(path).lower() == caption:
					for threadId, pId in self.threadlist():
						if processId == pId:
							return self.threadwindows(threadId, 'threadId', 'findfirst', 'excludehidden')[0]
					break
		else:
			return self.__matchwildcard(caption, self.WLDCRD_NONE)
				
		
	def __matchwildcard(self, caption, param):
		self._temp_caption = caption
		self._enum_result = None
		_user32.EnumWindows(self._p_enum_wildcards, param)
		result = self._enum_result
		self.__delattr__('_temp_caption')
		self.__delattr__('_enum_result')
		return result

	
	def __wildcardsproc(self, hwnd, lparam):
		if not self.IsWindowVisible(hwnd): 
			return 1
		length=self.GetWindowTextLength(hwnd) +1
		p = BUFFER(length)
		self.GetWindowText(hwnd, p, length)
		caption = p.value.lower()
		if lparam== self.WLDCRD_NONE:
			if caption == self._temp_caption:
				self._enum_result = hwnd
				return 0
		if lparam== self.WLDCRD_BOTH:
			if  self._temp_caption in caption:
				self._enum_result = hwnd
				return 0
		elif lparam== self.WLDCRD_LEFT:
			if caption.endswith(self._temp_caption):
				self._enum_result = hwnd	
				return 0
		elif lparam==self.WLDCRD_RIGHT:
			if caption.startswith(self._temp_caption):
				self._enum_result = hwnd
				return 0


#**************************************************
#w = platformspecific()
#hwnd = w.handle('*g4cdebug*')


