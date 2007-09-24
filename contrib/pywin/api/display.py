
from wnd.wintypes import *
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::

#
# TODO
#
# ?? the monitor methods sem not to be usable along with the WM_DISPLAYCHANGE
# message. The results of the calls are pretty weird (functions succeed but throw errors) 
#


ENUMMONITORPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

CCHDEVICENAME = 32
CCHFORMNAME = 32

MONITORINFOF_PRIMARY = 1

ENUM_CURRENT_SETTINGS  = 4294967295
ENUM_REGISTRY_SETTINGS = 4294967294

DM_GRAYSCALE            = 1
DM_INTERLACED           = 2



class MONITORINFOEX(Structure):
	_fields_ = [("cbSize", DWORD),
						("rcMonitor", RECT),
						("rcWork", RECT),
						("dwFlags", DWORD),
						("szDevice", c_char*CCHDEVICENAME)]
	def __init__(self): self.cbSize=sizeof(self)

class DISPLAY_DEVICE(Structure):
	_fields_ = [("cb", DWORD),
						("DeviceName", c_char * 32),
						("DeviceString", c_char * 128),
						("StateFlags", DWORD)]
	def __init__(self): self.cb=sizeof(self)


# welcome to the DEVMODE struct
class S(Structure):
		_fields_ = [("dmOrientation", c_ushort),
						("dmPaperSize", c_ushort),
						("dmPaperLength", c_ushort),
						("dmPaperWidth", c_ushort)]
class U(Union):
	_fields_ = [("S", S),
						("dmPosition", POINT)]

class DEVMODE(Structure):
	_fields_ = [("dmDeviceName", CHAR * CCHDEVICENAME ),
						("dmSpecVersion", WORD),
						("dmDriverVersion", WORD),
						("dmSize", WORD),
						("dmDriverExtra", WORD),
						("dmFields", DWORD),
						("U", U),
						("dmScale", c_ushort),
						("dmCopies", c_ushort),
						("dmDefaultSource", c_ushort),
						("dmPrintQuality", c_ushort),
						("dmColor", c_ushort),
						("dmDuplex", c_ushort),
						("dmYResolution", c_ushort),
						("dmTTOption", c_ushort),
						("dmCollate", c_ushort),
						("dmFormName", CHAR * CCHFORMNAME),
						("dmLogPixels", WORD),
						("dmBitsPerPel", DWORD),
						("dmPelsWidth", DWORD),
						("dmPelsHeight", DWORD),
						("dmDisplayFlags", DWORD),
						("dmDisplayFrequency", DWORD),
						("dmICMMethod", DWORD),
						("dmICMIntent", DWORD),
						("dmMediaType", DWORD),
						("dmDitherType", DWORD),
						("dmReserved1", DWORD),
						("dmReserved2", DWORD),
						("dmPanningWidth", DWORD),
						("dmPanningHeight", DWORD)]
	def __init__(self): self.dmSize=sizeof(self)

#------------------------------------------------------------------------------
def GetMonitorCount():
	#SM_CMONITORS           = 80
	return user32.GetSystemMetrics(80)



#---------------------------------------------------------------------------
def IsSameDisplayFormat():
	#SM_SAMEDISPLAYFORMAT   = 81
	if user32.GetSystemMetrics(81): return True
	return False


#----------------------------------------------------------------------------
def GetVirtualScreenSize():
	GSM = user32.GetSystemMetrics
	return (user32.GetSystemMetrics(76),		# SM_XVIRTUALSCREEN
				user32.GetSystemMetrics(77),		# SM_YVIRTUALSCREEN
				user32.GetSystemMetrics(78),		# SM_CXVIRTUALSCREEN
				user32.GetSystemMetrics(79))		# SM_CYVIRTUALSCREEN

#----------------------------------------------------------------------------
def IterDisplayNames():
	dd = DISPLAY_DEVICE()
	i = 0
	while True:
		result = user32.EnumDisplayDevicesA(0, i, byref(dd), 0)
		if not result:	break
		i += 1
		yield dd.DeviceName



def IterDisplayDeviceNames():
	dd = DISPLAY_DEVICE()
	i = 0
	while True:
		result = user32.EnumDisplayDevicesA(0, i, byref(dd), 0)
		if not result:	break
		i += 1
		yield dd.DeviceString
	
#------------------------------------------------------------------------

class EnumMonitors(object):
	def __init__(self):
		self._p_EnumProc = ENUMMONITORPROC(self.EnumMonitorProc)
		self.out=[]
		self.mi = MONITORINFOEX()
		self.devm=DEVMODE()

	def EnumMonitorProc(self, hMonitor, hDC, pRect, lp):
		if lp==1:
			if not user32.GetMonitorInfoA(hMonitor, byref(self.mi)):
				raise "could not retrieve monitor info"
			self.out.append((self.mi.szDevice,
											self.mi.dwFlags and True or False, 
											RECT(self.mi.rcMonitor.left,
														self.mi.rcMonitor.right,
														self.mi.rcMonitor.top,
														self.mi.rcMonitor.bottom), 
											RECT(self.mi.rcWork.left, 
														self.mi.rcWork.right, 
														self.mi.rcWork.top,
														self.mi.rcWork.bottom)))
		else:
			self.out.append(RECT(pRect[0].left,
													pRect[0].top,
													pRect[0].right,
													pRect[0].bottom))
		user32.ReleaseDC(hDC)
		kernel32.CloseHandle(hMonitor)
		return 1

	def IterDisplayRect(self):
		self.out = []
		if not user32.EnumDisplayMonitors(0, 0, self._p_EnumProc, 0):
			raise "could not enum monitors"
		return iter(self.out)

	def IterDisplayInfo(self):
		self.out = []
		if not user32.EnumDisplayMonitors(0, 0, self._p_EnumProc, 1):
			raise "could not enum monitors"
		return iter(self.out)


_e=EnumMonitors()
IterDisplayRect=_e.IterDisplayRect
IterDisplayInfo=_e.IterDisplayInfo



#--------------------------------------------------------------------

def IterDisplaySettings(current=True):
	dm=DEVMODE()
	if current: flag= ENUM_CURRENT_SETTINGS
	else: flag=ENUM_REGISTRY_SETTINGS
	for i in IterDisplayNames():
		result= user32.EnumDisplaySettingsA(i, flag,byref(dm)) 
		if result:
			if dm.dmDisplayFlags==DM_GRAYSCALE:
				flag='grayscale'
			elif dm.dmDisplayFlags==DM_INTERLACED:
				flag='interlaced'
			else: flag='color'
			yield (i, 
						dm.dmBitsPerPel,
						dm.dmPelsWidth,
						dm.dmPelsHeight,
						flag,
						dm.dmDisplayFrequency)
		



#**********************************************************************************
def GetMonitorXY(x, y, flag='nearest'):
	if flag=='primary': flag=1			# MONITOR_DEFAULTTOPRIMARY
	elif flag=='nearest': flag=2		# MONITOR_DEFAULTTONEAREST
	elif not flag: flag=0					# MONITOR_DEFAULTTONULL
	hMonitor= user32.MonitorFromPoint(POINT(x, y), flag)
	if hMonitor:
		mi= MONITORINFOEX()
		result= user32.GetMonitorInfoA(hMonitor, byref(mi))
		kernel32.CloseHandle(hMonitor)
		if not result:	raise "could not retrieve monitor info"
		return mi.szDevice, mi.dwFlags and True or False, mi.rcMonitor, mi.rcWork

											
def GetMonitorFromWindow(hwnd, flag='nearest'):
	if flag=='primary': flag=1			# MONITOR_DEFAULTTOPRIMARY
	elif flag=='nearest': flag=2		# MONITOR_DEFAULTTONEAREST
	elif not flag: flag=0					# MONITOR_DEFAULTTONULL
	hMonitor= user32.MonitorFromWindow(hwnd, flag)
	if hMonitor:
		mi= MONITORINFOEX()
		result= user32.GetMonitorInfoA(hMonitor, byref(mi))
		kernel32.CloseHandle(hMonitor)
		if not result:	raise "could not retrieve monitor info"
		return mi.szDevice, mi.dwFlags and True or False, mi.rcMonitor, mi.rcWork

																	
	

#r=GetMonitorXY(0, 0)


#def MonitorRectFromWindow(hwnd, flag='nearest'):
#	MONITOR_DEFAULTTONULL    = 0
#MONITOR_DEFAULTTOPRIMARY = 1
#MONITOR_DEFAULTTONEAREST = 2
#
#MonitorFromWindow(
 # HWND hwnd,       // handle to a window 
#  DWORD dwFlags    // flags if no monitor intersects the window 
#);



#---------------------------------------------------------------------------------------------

DM_POSITION         = 32
DM_BITSPERPEL       = 262144
DM_PELSWIDTH        = 524288
DM_PELSHEIGHT       = 1048576
DM_DISPLAYFLAGS     = 2097152
DM_DISPLAYFREQUENCY = 4194304

CDS_UPDATEREGISTRY  = 1
CDS_TEST            = 2
CDS_FULLSCREEN      = 4
CDS_GLOBAL          = 8
CDS_SET_PRIMARY     = 16
CDS_RESET           = 1073741824
CDS_NORESET         = 268435456

DISP_CHANGE_SUCCESSFUL  =  0
DISP_CHANGE_RESTART     =  1
DISP_CHANGE_FAILED      = -1
DISP_CHANGE_BADMODE     = -2
DISP_CHANGE_NOTUPDATED  = -3
DISP_CHANGE_BADFLAGS    = -4
DISP_CHANGE_BADPARAM    = -5
DISP_CHANGE_BADDUALVIEW = -6



# TODO
#
# 'set_primary' flag
# DM_POSITION
#

def ChangeDisplaySettings(displayname, flag, nBits=False, nWidth=False, nHeight=False, nMode=False, nFreq=False, nPos=False):
	try: 
		if flag in ('global', 'noreset'):	uFlag = CDS_UPDATEREGISTRY
		else: uFlag = 0
		uFlag |={'updateregistry': 1,'test':2,'fullscreen':4,
					'global':8,'set_primary':16,'reset':1073741824,
					'noreset':268435456}[flag]
	except: return (-1, "invalid flag: %s" % flag)
	
	dm=DEVMODE()
	if not user32.EnumDisplaySettingsA(name, ENUM_CURRENT_SETTINGS,byref(dm)):
		return (-1, "invalid display-name: %s" % displayname)
	if nBits:
		dm.dmFields |= DM_BITSPERPEL 
		dm.dmBitsPerPel = nBits
	if nWidth and nHeight:
		dm.dmFields |= DM_PELSWIDTH | DM_PELSHEIGHT
		dm.dmPelsWidth = nWidth
		dm.dmPelsHeight = nHeight
	if nMode:
		dm.dmFields |= DM_DISPLAYFLAGS
		dm.dmDisplayFlags = nMode
	if nFreq:
		dm.dmFields |= DM_DISPLAYFREQUENCY
		dm.dmDisplayFrequency=nFreq
	if nPos:
		return (-1, "not yet implemented")
		# relative position here
		dm.dmFields |= DM_POSITION
		dm.U.dmPosition.x=0
		dm.U.dmPosition.y=0

	dm.dmDeviceName = displayname
	result= user32.ChangeDisplaySettingsA(byref(dm), uFlag)
	if result:
		try:
			return (0, {0:'sucess',1:'restart',-1:'failed',-2:'badmode',
							-3:'notupdated',-4:'badflags',
						-5:'badparam',-6:'baddualview'}[result])
		except: return (0, 'unknown')
	return (0, True)


#***************************************************************************************************************
def SetDisplayBitsPerPel(displayname, nBits, flag):
	result=ChangeDisplaySettings(displayname, flag, nBits=nBits)
	if result[0]: raise result[1]
	return result[1]


#name=IterDisplayNames().next()
#r=SetDisplayBitsPerPel(name, 16, 'fullscreen')


#******************************************************************************************************

def SetDisplaySize(displayname, nWidth, nHeight, flag):
	result=ChangeDisplaySettings(displayname, flag, nWidth=nWidth, nHeight=nHeight)
	if result[0]: raise result[1]
	return result[1]

#name=IterDisplayNames().next()
#r=SetDisplaySize(name, 800, 600, 'reset')

#******************************************************************************************************

def SetDisplayMode(displayname, mode, flag):
	try:	mode={'color':0,'grayscale':1,'interlaced':2}[mode]
	except: raise "invalid mode: %s" % mode
	result=ChangeDisplaySettings(displayname, flag, nMode=mode)
	if result[0]: raise result[1]
	return result[1]

#name=IterDisplayNames().next()
#r=SetDisplayMode(name, 'grayscale', 'fullscreen')

	

#*****************************************************************************************************
def SetDisplayFrequency(displayname, nFreq, flag):
	result=ChangeDisplaySettings(displayname, flag, nFreq=nFreq)
	if result[0]: raise result[1]
	return result[1]

#name=IterDisplayNames().next()
#r=SetDisplayFrequency(name, 85, 'fullscreen')


	
#********************************************************************************************************
# NOT yet implemented
#def SetDisplayPosition():
#	pass