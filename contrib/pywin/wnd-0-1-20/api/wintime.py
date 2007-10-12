
"""Time and time converting functions and classes.
The win API uses a time with the epoch starting at
the first milisecond of 1.1.1601. 

- sytemtime is the universal time
- localtime is time taking into consideration daylight-saving-time
aspects

The module contains some data one might be interested in:
'days' 
	a list of days 'Sun', 'Mon', (...) 
'months'	
	list of months	'Jan', 'Feb', (...)
'epoch'
	when micros~1 started counting 
	as string: 'Mon Jan 1 0:0:0 1601'
"""


from wnd.wintypes import *
#import time 
#--------------------------------------------------------------------------
#TODO:
#	- converting between t_time and UNC time
#		see -> d:/_docs_/time
#
#DONE:
#	- GetTimeZoneInformation
#
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oc', 'Nov', 'Dec']

EPOCH = 'Mon Jan 1 0:0:0 1601'
#*********************************************
TIME_ZONE_ID_INVALID  = 4294967295
TIME_ZONE_ID_UNKNOWN  = 0
TIME_ZONE_ID_STANDARD = 1
TIME_ZONE_ID_DAYLIGHT = 2

#************************************************
class TIME_ZONE_INFORMATION(Structure): 
	_fields_ = [("Bias", LONG),
					("StandardName", WCHAR*32),
					("StandardDate", SYSTEMTIME),
					("StandardBias", LONG),
					("DaylightName", WCHAR*32),
					("DaylightDate", SYSTEMTIME),
					("DaylightBias", LONG)]
	

#************************************************
def SystemtimeToFiletime(systemtime):
	ft = FILETIME()
	if not kernel32.SystemTimeToFileTime(byref(systemtime), byref(ft)):
		raise "could not convert systemtime to filetime"
	return ft

#************************************************
def FiletimeToLocalFiletime(filetime):
	ft  = FILETIME()
	if not kernel32.FileTimeToLocalFileTime(byref(filetime), byref(ft)):
			raise "could not convert filetime to local filetime"
	return ft

def LocalFiletimeToFiletime(filetime):
	ft = FILETIME()
	if not kernel32.LocalFileTimeToFileTime(byref(filetime), byref(ft)):
			raise "could not convert local filetime to filetime"
	return ft

def FiletimeToSystemtime(filetime):
	st=SYSTEMTIME()
	if not kernel32.FileTimeToSystemTime(byref(filetime), byref(st)):
			raise "could not convert filetime to systemtime"
	return st

#***************************************************
def GetLocalTime():
	st = SYSTEMTIME()
	if not kernel32.GetLocalTime(byref(st)):
		raise "could not retrieve local time"
	return st
	
  #***************************************************
def GetSystemTime():
	st = SYSTEMTIME()
	if not kernel32.GetSystemTime(byref(st)):
		raise "could not retrieve system time"
	return st

def GetSystemFiletime():
	ft = FILETIME()
	if not kernel32.GetSystemTimeAsFileTime(byref(ft)):
		raise "could not retrieve system filetime"
	return ft
	


#***************************************************
def CompareFiletime(filetime1, filetime2):       
	return kernel32.CompareFileTime(byref(filetime1), byref(filetime2))

#**************************************************
#TODO: test
def GetFiletime(hFile, ctime=None, atime=None, mtime=None):
	if not kernel32.GetFileTime(hFile, byref(ftc), byref(fta), byref(ftm)):
		raise WinError()
	return ftc, fta, ftmj
	
#**************************************************
def SetFiletime(hFile, ctime=None, atime=None, mtime=None):
	if ctime: ftc = FILETIME()
	if atime: fta = FILETIME()
	if mtime: ftm = FILETIME()
	if not kernel32.SetFileTime(hFile, ftc, fta, ftm):
		raise WinError()
	
#*************************************************

# needs rework or kick it out
def FormatTime(systemtime):
	"""Formats a systemtime struct as a as a string using same
	semantics as PYTHON time.asctime i.e:
	'Sun Jun 20 23:21:05 1993'	"""
	return '%s %s %s %s:%s:%s %s' % (
										days[systemtime.wDayOfWeak],
										months[systemtime.wMonth-1],
										systemtime.wMonth,
										systemtime.wHour,
										systemtime.wMinute,
										systemtime.wSecond,
										systemtime.wYear)

def IsEpoch(FtOrSt):
	if FtOrSt.__class__.__name__ == 'FILETIME':
		if FtOrSt.dwLowDateTime==0 and FtOrSt.dwHighDateTime==0:
			return True
	elif FtOrSt.__class__.__name__ == 'SYSTEMTIME':
		if FtOrSt.wYear==1601:
			if FtOrSt.wMonth==1:
				if FtOrSt.wDayOfWeak==1:
					if FtOrSt.wDay==1:
						if FtOrSt.wHour==0:
							if FtOrSt.wMinute==0:
								if FtOrSt.wSecond==0:
									return True
	else:
		raise "invalid structure type"
	return False

#*************************************************	
def GetTimezoneInfo():
	tzi = TIME_ZONE_INFORMATION()
	result = kernel32.GetTimeZoneInformation(tzi.byref())
	if result == TIME_ZONE_ID_INVALID:
		raise WinError()
	return result, tzi



#ft = getsystemtime(True)
#ft = ft.tolocalfiletime()
#st = ft.tolocaltime()


#st = getlocaltime()


#tzi = gettimezoneinfo()


