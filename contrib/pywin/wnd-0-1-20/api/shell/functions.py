

from wnd.api.shell.wintypes import *

__all__=["FileOperation","MoveFiles","CopyFiles","DeleteFiles",
			"RenameFiles","GetPathFromPidl","PidlCopy",
			"PidlDidAlloc","PidlEnum","PidlFree","PidlGetParent",
			"PidlGetSize","PidlJoin","PidlPrint",	"PidlSplit", "PidlRemoveLast",
			"PidlFromPath", "PidlGetNext", "PidlGetLast", "PidlCopyFirst",
			"PidlGetChild", "PidlAppend", "PidlIsEqual", "PidlIsParent",
			"ILIsZero", "GetSpecialFolderPath", "CLSIDL_FromPidl"]

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class SHFILEOPSTRUCT(Structure):
	_fields_ = [("hwnd", HWND),
					("wFunc", UINT),
					("pFrom", LPCSTR),
					("pTo", LPCSTR),
					("fFlags", c_ulong),
					("fAnyOperationsAborted", BOOL),
					("hNameMappings", LPVOID),
					("lpszProgressTitle", LPCSTR)]


FO_MOVE    = 1
FO_COPY     = 2
FO_DELETE      = 3
FO_RENAME    = 4

FOF_MULTIDESTFILES    =     1
#FOF_CONFIRMMOUSE     =     2
FOF_SILENT             =    4  # don't create progress/report
FOF_RENAMEONCOLLISION  =  8
FOF_NOCONFIRMATION     =   16  # Don't prompt the user.
FOF_WANTMAPPINGHANDLE   =   32  # Fill in SHFILEOPSTRUCT.hNameMappings
                                      # Must be freed using SHFreeNameMappings
FOF_ALLOWUNDO      =        64
FOF_FILESONLY           =   128  # on *.*, do only files
FOF_SIMPLEPROGRESS    =     256  # means don't show names of files
FOF_NOCONFIRMMKDIR   =      512  # don't confirm making any needed dirs
FOF_NOERRORUI       =       1024  # don't put up error UI
FOF_NOCOPYSECURITYATTRIBS= 2048  # dont copy NT file Security Attributes

FILEOPERATIONS={'move':FO_MOVE, 'copy':FO_COPY, 'delete':FO_DELETE,'rename':FO_RENAME}
FO_FLAGS={'silent': FOF_SILENT,
		'renameoncollision':FOF_RENAMEONCOLLISION,
		'noconfirm':FOF_NOCONFIRMATION,
		'noconfirmmkdir':FOF_NOCONFIRMMKDIR,
		'allowundo':FOF_ALLOWUNDO,
		'filesonly':FOF_FILESONLY,
		'simpleprogress': FOF_SIMPLEPROGRESS,
		'noerrorui':FOF_NOERRORUI, 
		'nosecurityattrs':FOF_NOCOPYSECURITYATTRIBS,}


def FileOperation(fileaction, From, To,  *flags, **kwargs):
	
	if fileaction not in FILEOPERATIONS:
		raise "invalid file action: %s" % fileaction
	if not From: raise "no source files specified"
	
	sho=SHFILEOPSTRUCT()
	try:
		sho.wFunc= FILEOPERATIONS[fileaction]
	except: raise ValueError, "invalid file action: %s" % fileaction
	
	for i in flags:
		try: sho.fFlags=FO_FLAGS[i]
		except: raise "invalid flag: %s" % i
	sho.hwnd=kwargs.get('title', 0)
		
	if fileaction != 'delete':
		if not To: raise "no destination specified"
		if isinstance(To, (list, tuple)):
			sho.fFlags |= FOF_MULTIDESTFILES
			sho.pTo= '%s\x00' % '\x00'.join(To)
		else: sho.pTo= To
	if isinstance(From, (list, tuple)):
		sho.pFrom='%s\x00' % '\x00'.join(From)
	else: sho.pFrom=From
	sho.lpszProgressTitle=kwargs.get('title', '')
		
	if shell32.SHFileOperation(byref(sho)): 
		return False
	if sho.fAnyOperationsAborted: 
		return False
	return True

def MoveFiles(From, To, title='', hwnd=0, *flags, **kwargs):
	return FileOperation('move', From, To, *flags, **kwargs)	

def CopyFiles(From, To, title='', hwnd=0, *flags):
	return FileOperation('copy', From, To, flags, kwargs)	

def DeleteFiles(From, To, title='', hwnd=0, *flags, **kwargs):
	return FileOperation('delete', From, To, flags, kwargs)	
	
def RenameFiles(From, To, title='', hwnd=0, *flags, **kwargs):
	return FileOperation('rename', From, To, *flags, **kwargs)	

#**********************************************************
# pIdl functions 
#**********************************************************

GPA= kernel32.GetProcAddress

GPA.restype= WINFUNCTYPE(c_void_p, PIDL)
PidlFree= GPA(shell32._handle, 155)	

GPA.restype= WINFUNCTYPE(BOOL, PIDL)
PidlRemoveLast= GPA(shell32._handle, 17)

GPA.restype= WINFUNCTYPE(PIDL, LPSTR)
PidlFromPath= GPA(shell32._handle, 157)

GPA.restype= WINFUNCTYPE(PIDL, PIDL)
PidlGetNext= GPA(shell32._handle, 153)
PidlGetLast=  GPA(shell32._handle, 16)
PidlCopy=  GPA(shell32._handle, 18)
PidlCopyFirst=  GPA(shell32._handle, 19)

GPA.restype= WINFUNCTYPE(PIDL, PIDL, PIDL)
PidlGetChild=  GPA(shell32._handle, 24)
PidlJoin=  GPA(shell32._handle, 25)

GPA.restype= WINFUNCTYPE(PIDL, PIDL, PIDL, BOOL)
PidlAppend=  GPA(shell32._handle, 154)

GPA.restype= WINFUNCTYPE(BOOL, PIDL, PIDL)
PidlIsEqual= GPA(shell32._handle, 21)

GPA.restype= WINFUNCTYPE(BOOL, PIDL, PIDL, BOOL)
PidlIsParent= GPA(shell32._handle, 23)

GPA.restype= WINFUNCTYPE(c_uint, PIDL)
PidlGetSize= GPA(shell32._handle, 152)

def ILIsZero(pIdl):
	if pIdl:
		if pIdl[0].mkid.cb > 0:
			return False
	return True

def PidlEnum(pIdl):
	while True:
		pIdl= PidlGetNext(pIdl)
		if not pIdl: break
		if pIdl[0].mkid.cb==0: break
		yield pIdl

def PidlSplit(pIdl):
	pIdlChild= PidlGetLast(pIdl)
	if pIdlChild:
		pIdlChild= PidlCopy(pIdlChild)
		if PidlRemoveLast(pIdl):
			return pIdlChild
		PidlFree(pIdlChild)

def GetPathFromPidl(pIdl):
	p = create_string_buffer(260 +1)	# MAX_PATH
	if not shell32.SHGetPathFromIDListA(pIdl, p):
		raise RuntimeError, "could not extract path from identifier list"
	return p.value
		
def PidlGetParent(pIdl):
	return PidlRemoveLast(pIdl)

def PidlDidAlloc(pIdl):
	if Malloc.DidAlloc(pIdl): 
		return True
	return False
	
def PidlPrint(pIdl):
	p= create_string_buffer(PidlGetSize(pIdl))
	memmove(p, pIdl, sizeof(p))
	print repr(p.raw)
	
	
NAME_BUFFER= create_string_buffer(260)
ret= STRRET()


def GetIShellFolder(pIdl):
	Folder = POINTER(IShellFolder)()
	shell32.SHGetDesktopFolder(byref(Folder))
	tmp_pIdl= pIdl
	
	
	while not ILIsZero(tmp_pIdl):
		pIdlChild= PidlCopyFirst(tmp_pIdl)
		try:
			FolderNew = POINTER(IShellFolder)()
			Folder.BindToObject(pIdlChild, None, byref(IShellFolder._iid_), byref(FolderNew))
			del Folder
			Folder= FolderNew
		finally:
			PidlFree(pIdlChild)
		tmp_pIdl= PidlGetNext(tmp_pIdl)
	return Folder

#****************************************************************************
#****************************************************************************
def GetSpecialFolderPath(clsidl):
	p= create_string_buffer(261)
	shell32.SHGetSpecialFolderPathA(0, p, clsidl, 0)
	if p.value: return p.value



def CLSIDL_FromPidl(pIdl):
	CLSIDLS= [('desktop' , 0),('internet' , 1),('programs' , 2),('controls' , 3),
						('printers' , 4),('personal' , 5),('favorites' , 6),('startup' , 7),
						('recent' , 8),(	'sendto' , 9),('bitbucket' , 10),('startmenu' , 11),
						('desktopdirectory' , 16),('drives' , 17),('network' , 18),
						('nethood' , 19),('fonts' , 20),('templates' , 21),
						('common_startmenu' , 22),('common_programs' , 23),
						('common_startup' , 24),('common_desktopdirectory' , 25),
						('appdata' , 26),('printhood' , 27),(	'altstartup' , 29),
						('common_altstartup' , 30),('common_favorites' , 31),
						('internet_cache' , 32),('cookies' , 33),('history' , 34)]
	
	for name, value in CLSIDLS:
				
		pIdl_tmp = PIDL(ITEMIDLIST()) 
		shell32.SHGetSpecialFolderLocation(0, value, byref(pIdl_tmp))
		try:
			if PidlIsEqual(pIdl, pIdl_tmp):
				PidlFree(pIdl_tmp)
				return value, name
		except: pass
		PidlFree(pIdl_tmp)
	

