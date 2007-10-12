
"""
Pretty old module here, needs some rework

"""



from ctypes import *
## from wnd.api import win ## importted on the fly in 'Terminate'
from wnd.api import msgbox

kernel32= windll.kernel32
shell32= windll.shell32
#-----------------------------------------------------------
DWORD = c_ulong
WORD = c_ushort
HANDLE = c_ulong
LPTSTR = c_char_p
LPCTSTR = c_char_p
BYTE = c_int
LPVOID = c_void_p

INFINITE = -1
NORMAL_PRIORITY_CLASS = 32
STARTF_USESHOWWINDOW = 1
WAIT_FAILED = -1
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT= 258
WAIT_ABANDONED  = 128

PROCESS_ALL_ACCESS = 2035711

class STARTUPINFO(Structure):
	_fields_=[	("cb", DWORD),
						("lpReserved", LPTSTR), 
						("lpDesktop", LPTSTR), 
						("lpTitle", LPTSTR), 
						("dwX", DWORD), 
						("dwY", DWORD), 
						("dwXSize", DWORD), 
						("dwYSize", DWORD), 
						("dwXCountChars", DWORD), 
						("dwYCountChars", DWORD), 
						("dwFillAttribute", DWORD), 
						("dwFlags", DWORD), 
						("wShowWindow", WORD),
						("cbReserved2", WORD), 
						("lpReserved2", BYTE), 
						("hStdInput", HANDLE), 
						("hStdOutput", HANDLE), 
						("hStdError", HANDLE)] 


class PROCESS_INFORMATION(Structure):
	_fields_=[("hProcess", HANDLE), 
						("hThread", HANDLE), 
						("dwProcessId", DWORD), 
						("dwThreadId", DWORD)] 

	
SHOWSTATES={"hidden" : 0,
						"normal" : 1,
						"minimized" :  2,
						"maximized" : 3}


class ShellError(Exception):
	def __init__(self, value):
		err={
				0: "OUT OF MEMORY",
				2 : "FILE NOT FOUND",
				3 : "PATH NOT FOUND",
				5 : "ACCESSDENIED",
				8 : "OUT_OF_MEMORY",
				11 : "WRONG FILE FORMAT",
				26 : "SHARING_VIOLATION",
				27 : "FILE_ASSOCIATION_ERROR",
				28 : "DDE_TIMEOUT",
				29 : "DDE_FAILURE",
				30 : "DDE_BUSY",
				31 : "NO_FILE_ASSOCIATION_FOUND",
				32: "DLL_NOT_FOUND"}
		try:
			self.value= err[value]
		except: 
			self.value= "UNKNOWN ERROR"
		msgbox.Msg(0, self.value, 'process error', 'systemmodal', 'ok')
	def __str__(self):
		return repr(self.value)


class ProcessError(Exception):
	def __init__(self, value):
		self.value= value
		msgbox.Msg(0, self.value, 'process error', 'systemmodal', 'ok')
	def __str__(self):
		return repr(self.value)

#**************************************************************************
#**************************************************************************

def Create(commandline, show='normal', flag='synchron', timeout=INFINITE, return_handle = False):
		
	si = STARTUPINFO()
	si.cb = sizeof(STARTUPINFO)
	pi = PROCESS_INFORMATION()
		
	if show:
		si.dwFlags = STARTF_USESHOWWINDOW
		try:
			si.wShowWindow = SHOWSTATES[show]
		except: raise ProcessError, "invalid show state: %s" % show
		
	result = kernel32.CreateProcessA(
			0,										# appName
			commandline,				#commandLine 
			0,										#processAttributes
			0,										#threadAttributes 
			0,										#bInheritHandles 
			NORMAL_PRIORITY_CLASS,
			0,										#newEnvironment
			0,										#currentDirectory 
			byref(si),
			byref(pi)
		)
	if not result:
		raise ProcessError, FormatError(GetLastError())
		
	 # wait till process is signaled.
	if flag == 'synchron':
		wait = kernel32.WaitForSingleObject(pi.hProcess, timeout)
		if pi.hProcess: kernel32.CloseHandle(pi.hProcess)
		if pi.hThread: kernel32.CloseHandle(pi.hThread)
				
		# TODO	check return values
		if wait==WAIT_TIMEOUT: return 1
		elif wait==WAIT_OBJECT_0 : 	return 0
		elif wait==WAIT_ABANDONED: 
			return 'WAIT_ABANDONED'				# ??
		elif wait==WAIT_FAILED: 	return -1
	
	 # return emidiately.
	else:
		if return_handle:
			# TODO we could return handle objects.
			# To avoid having to close the handles.
			return (pi.hProcess,
							pi.hThread,
							pi.dwProcessId,
							pi.dwThreadId)
		else: 
			if pi.hProcess: kernel32.CloseHandle(pi.hProcess)
			if pi.hThread: kernel32.CloseHandle(pi.hThread)
			return result
	
#Create(commandline='regedit', flag='synchron')

#***********************************************************
#***********************************************************
def WinExec(commandline, show='normal'):
	try:
		show=SHOWSTATES[show]
	except: raise ProcessError, "invalid show state: %s" % show
	result = kernel32.WinExec(commandline, show)
	if result  < 32:
		raise ShellError(result)
	
#WinExec('notepad.exe')

#***********************************************************
#***********************************************************
def ShellExec(hwnd=0, verb = 'open', file=0,  params=0, directory =0, show = 'normal', return_handle = False):
	
	try:
	 show = SHOWSTATES[show]
	except: raise ProcessError, "invalid show state: %s" % show
	result =	shell32.ShellExecuteA(hwnd,
									verb,
									file,
									params,
									directory,
									show)
	if result <= 32:
		raise ShellError(result)
				
	if not return_handle :
		kernel32.CloseHandle(result)	## TODO check if necessary.
	return bool(result)
	

def _test():
	import sys
	path= '%s\\license.txt' % sys.prefix
	ShellExec(file=path, verb='open')	## as long as verb and file exists
#_test()

#************************************************************
#************************************************************
def Terminate(pid):
	
	if isinstance(pid, basestring):
		from wnd.api import win
		
		hwnd = win.Handle("=%s" % pid)
		if hwnd:
			pid = win.GetProcessId(hwnd)
		else:	
			raise RuntimeError,"no such process: %s" % pid
	
	error= None
	hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, 0, pid)
	if hProcess:
		if not kernel32.TerminateProcess(hProcess, 0):
			error= "could not terminate process"
	else:
		error= "could not open process"
			
	if hProcess:	
		kernel32.CloseHandle(hProcess)
	if error:
		raise RuntimeError, error
	
#Terminate('notepad')



