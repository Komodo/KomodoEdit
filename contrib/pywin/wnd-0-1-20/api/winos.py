
"""

LAST VISITED
	15.04.05

TODO
	

"""

import sys
from ctypes import (WinError, GetLastError, sizeof, windll,  byref, create_string_buffer, c_ulong, c_ulonglong, c_longlong)
if sys.getwindowsversion()[3]==2:
	from wnd.api import privleges		## not tested, may or may not work
																## for Shutdown (...)
	
kernel32=windll.kernel32
user32=windll.user32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def IsWIN31(): 
	return bool(sys.getwindowsversion()[3]==0)	 # VER_PLATFORM_WIN32s

def IsWIN98(): 
	return bool(sys.getwindowsversion()[3]==1) # VER_PLATFORM_WIN32_WINDOWS

def IsNT():
	return bool(sys.getwindowsversion()[3]==2) # VER_PLATFORM_WIN32_NT

def Name():
	ver= sys.getwindowsversion()
	name =  "unknown"
	if ver[3] == 0:				# VER_PLATFORM_WIN32s
		name = "win3.1"
	elif ver[3] == 1:			# VER_PLATFORM_WIN32_WINDOWS
		if ver[1]  == 0: name = "win95"
		else: name = "win98"
	elif ver[3] == 2:			# VER_PLATFORM_WIN32_NT
		if ver[0]==3: name = "NT"
		elif ver[0]==4: name = "NT4"
		elif ver[0]==5:
			if ver[1]== 0: name = "windows2000"
			else: name = "XP"
		return name

#print IsWIN31()
#print IsWIN98()
#print IsNT()

#----------------------------------------------------------------------------

def GetDriveList():
	p = create_string_buffer(128)
	n=kernel32.GetLogicalDriveStringsA(sizeof(p), p)
	if not n: raise WinError(GetLastError())
	if n > sizeof(p):
		p= create_string_buffer(n+1)
		if not kernel32.GetLogicalDriveStringsA(sizeof(p), p):
			raise  WinError(GetLastError())
	return p.raw[:n-1].split('\0')

#print GetDriveList()
#----------------------------------------------------------------------------
def GetDriveInfo(drive):
	return ['unknown', 'no_root_dir', 'removable', 
				'fixed', 'remote', 	'cdrom','ramdisk'
							][kernel32.GetDriveTypeA(drive)]
		
#print GetDriveInfo('a:')

#----------------------------------------------------------------------------

def GetVolumeInfo(drive):
	drive = drive.replace('/', '\\')
	if not drive.endswith('\\'):
		drive = '%s\\' % drive
	
	pName = create_string_buffer(1024)	
	SerialNo = c_ulong()
	MaxFileName = c_ulong()
	FileSystemFlags = c_ulong()
	pFSName = create_string_buffer(1024)
	if not kernel32.GetVolumeInformationA(
					drive,
					pName,
					sizeof(pName),
					byref(SerialNo),			
					byref(MaxFileName),
					byref(FileSystemFlags),
					pFSName,
					sizeof(pFSName)
					):
		raise WinError(GetLastError())
	return [pName.value, SerialNo.value, MaxFileName.value, FileSystemFlags.value, pFSName.value]
	
	
#print GetVolumeInfo('c:\\')


#-------------------------------------------------------------------------------
def translate_vi_flags(flags):
	result = []
	FLAGS = {1 : 'case_sensitive', 2 : 'case_preserved', 4 : 'unicode_stored_on_disk', 8 : 'persistant_acls', 16 : 'supports_compression', 32768 : 'compressed', }
	for item in FLAGS.items():
		if flags & item[0]:
			result.append(item)
	return result

#flags = GetVolumeInfo('c:\\').filesystemflags

#-------------------------------------------------------------------------

def GetFreeSpace(drive=None):
	AvailableBytes = c_ulonglong()
	TotalBytes = c_ulonglong()
	FreeBytes = c_ulonglong()
	a=kernel32.GetDiskFreeSpaceExA(drive, 
								byref(AvailableBytes), 
								byref(TotalBytes), 
								byref(FreeBytes))
	return (AvailableBytes.value,
					TotalBytes.value,
					FreeBytes.value)
	
#print GetFreeSpace()
#------------------------------------------------------------------------

def Logoff(force=False): 
	flags = 0	# EWX_LOGOFF
	if force:	flags |= 4	# EWX_FORCE
	user32.ExitWindowsEx(flags, 0)
#Logoff(0)


def Shutdown(force=False):
	flags = 1	# EWX_SHUTDOWN
	if force:	flags |= 4 | 8
	if IsNT(): privleges.EnablePrivleges('SeShutdownPrivilege')
	user32.ExitWindowsEx(flags, 0)

#Shutdown(1)

def Reboot(force=False):
	flags = 2	# EWX_RBOOT
	if force:	flags |= 4
	if IsNT(): privleges.EnablePrivleges('SeShutdownPrivilege')
	user32.ExitWindowsEx(flags, 0)

#Reboot(1)

def Poweroff(force=False):
	flags = 8	# EWX_POWEROFF
	if force:	flags |= 4
	if IsNT(): privleges.EnablePrivleges('SeShutdownPrivilege')
	user32.ExitWindowsEx(flags, 0)

#Poweroff(1)



		
	