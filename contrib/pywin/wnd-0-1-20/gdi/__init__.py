

""" """
from wnd.gdi.trackhandles import GetOpenHandles
from wnd.gdi.bitmap import *
from wnd.gdi.brush import *
from wnd.gdi.cursor import *
from wnd.gdi.dc import *
from wnd.gdi.font import *
from wnd.gdi.icon import *
from wnd.gdi.pen import *
from wnd.gdi.region import *

from ctypes import windll

user32= windll.user32
gdi32= windll.gdi32
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Color:
	def __init__(self, colorref=0):
		self.color = colorref
	def GetColor(self): return self.color
	def SetRgb(self, r, g, b):
		self.color = r | (g<<8) | (b<<16)
	def GetRgb(self):
		return (self.color >> 0 & 255,
				 self.color >> 8 & 255,
				 self.color >> 16 & 255)
	def GetR(self): return self.color >> 0 & 255
	def GetG(self): return self.color >> 8 & 255
	def getB(self): return self.color >> 16 & 255
	
#c=Color()
#c.SetRgb(255, 255, 255)


#**************************************************
GDI_OBJECTS=('unknown','pen','brush','dc','metadc','pal','font','bitmap','region', 				
								'metafile','memdc','extpen','enhmetadc','enhmetafile')

SYSTEM_COLORS = {
			'scrollbar' : 0,
			'background' : 1,
			'desktop' : 1,
			'activecaption' : 2,
			'inactivecaption' : 3,
			'menu' : 4,
			'msgbox' : 4,
			'window' : 5,
			'windowframe' : 6,
			'menutext' : 7,
			'msgboxtext' : 7,
			'windowtext' : 8,
			'captiontext' : 9,
			'activeborder' : 10,
			'inactiveborder' : 11,
			'appworkspace' : 12,
			'highlight' : 13,
			'highlighttext' : 14,
			'3dface' : 15,
			'btnface' : 15,
			'3dshadow' : 16,
			'btnshadow' : 16,
			'graytext' : 17,
			'btntext' : 18,
			'inactivecaptiontext' : 19,
			'3dhighlight' : 20,
			'3dhilight' : 20,
			'btnhighlight' : 20,
			'btnhilight' : 20,
			'3ddkshadow' : 21,
			'3dlight' : 22,
			'infotext' : 23,
			'infobk' : 24,
			'hotlight' : 26,
			'gradientactivecaption' : 27,
			'gradientinactivecaption' : 28,
			'menuhilight' : 29,
			'menubar' : 30}

SYSTEM_METRICS={
			'cxscreen' : 0,
			'cyscreen' : 1,
			'cxvscroll' : 2,
			'cyhscroll' : 3,
			'cycaption' : 4,
			'cxborder' : 5,
			'cyborder' : 6,
			'cxfixedframe' : 7,
			'cyfixedframe' : 8,
			'cyvthumb' : 9,
			'cxhthumb' : 10,
			'cxicon' : 11,
			'cyicon' : 12,
			'cxcursor' : 13,
			'cycursor' : 14,
			'cymenu' : 15,
			'cxfullscreen' : 16,
			'cyfullscreen' : 17,
			'cykanjiwindow' : 18,
			'mousepresent' : 19,
			'cyvscroll' : 20,
			'cxhscroll' : 21,
			'debug' : 22,
			'swapbutton' : 23,
			'cxmin' : 28,
			'cymin' : 29,
			'cxsize' : 30,
			'cysize' : 31,
			'cxsizeframe' : 32,
			'cysizeframe' : 33,
			'cxmintrack' : 34,
			'cymintrack' : 35,
			'cxdoubleclk' : 36,
			'cydoubleclk' : 37,
			'cxiconspacing' : 38,
			'cyiconspacing' : 39,
			'menudropalignment' : 40,
			'penwindows' : 41,
			'dbcsenabled' : 42,
			'cmousebuttons' : 43,
			'secure' : 44,
			'cxedge' : 45,
			'cyedge' : 46,
			'cxminspacing' : 47,
			'cyminspacing' : 48,
			'cxsmicon' : 49,
			'cysmicon' : 50,
			'cysmcaption' : 51,
			'cxsmsize' : 52,
			'cysmsize' : 53,
			'cxmenusize' : 54,
			'cymenusize' : 55,
			'arrange' : 56,
			'cxminimized' : 57,
			'cyminimized' : 58,
			'cxmaxtrack' : 59,
			'cymaxtrack' : 60,
			'cxmaximized' : 61,
			'cymaximized' : 62,
#			'network' : 63,
			'cleanboot' : 67,
			'cxdrag' : 68,
			'cydrag' : 69,
			'showsounds' : 70,
			'cxmenucheck' : 71,
			'cymenucheck' : 72,
			'slowmachine' : 73,
			'mideastenabled' : 74,
			'mousewheelpresent' : 75,
			'xvirtualscreen' : 76,
			'yvirtualscreen' : 77,
			'cxvirtualscreen' : 78,
			'cyvirtualscreen' : 79,
			'cmonitors' : 80,
			'samedisplayformat' : 81,
#			'immenabled' : 82,
#			'cxfocusborder' : 83,
#			'cyfocusborder' : 84,
#			'tabletpc' : 86,
#			'mediacenter' : 87,
	#		'cmetrics' : 88,
	#		'remotesession' : 4096,
	#		'shuttingdown' : 8192,
	#		'remotecontrol' : 8193
			}

# Not working on win98
#'cxfocusborder'
#'cyfocusborder'


#****************************************************************************************
def GetSysColor(colorname):
	try: color = SYSTEM_COLORS[colorname]
	except: raise ValueError("invalid color name: %s" % colorname)
	return user32.GetSysColor(color) 
	
#--------------------------------------------------------------------------
# NOT documented
# SM_ARRANGE
# SM_CXFOCUSBORDER
# SM_CYFOCUSBORDER
# SM_DBCSENABLED	
# SM_DEBUG
# SM_MIDEASTENABLED
# SM_PENWINDOWS
#SM_MEDIACENTER
#SM_CMETRICS
#SM_REMOTESESSION
#SM_SHUTTINGDOWN
#SM_REMOTECONTROL
#SM_CYKANJIWINDOW

def GetSystemMetric(metricname):
	try: metricname=SYSTEM_METRICS[metricname]
	except: raise ValueError("invalid metric name: %s" % metricname)
	result=user32.GetSystemMetrics(metricname)
	return result
	# docs claim if return value is zero the call failed
	# try 'xvirtualscreen' as proof that this is nonsense
	#if result: return result
	#raise "could not retrieve system color"

def IsNetworkPresent():
	"""True if a network is present False otherwise."""   
	if user32.GetSYSTEM_METRICS(63) & 0x000000ff:		# SM_NETWORK
		return True
	return False


#---------------------------------------------------------------------------------
# the rest of the staff

SM_CYKANJIWINDOW       = 18
SM_DEBUG               = 22
SM_MENUDROPALIGNMENT   = 40
SM_PENWINDOWS          = 41
SM_DBCSENABLED         = 42
SM_SECURE              = 44
SM_ARRANGE             = 56
SM_CLEANBOOT           = 67
SM_SLOWMACHINE         = 73
SM_MIDEASTENABLED      = 74
SM_IMMENABLED          = 82
SM_TABLETPC            = 86
SM_MEDIACENTER         = 87
SM_CMETRICS            = 88   # varies by Windows version
SM_REMOTESESSION       = 4096
SM_SHUTTINGDOWN        = 8192
SM_REMOTECONTROL       = 8193

#************************************************************************************************
def GetScreenDPI():
	LOGPIXELSX     = 88
	hdcScreen = user32.GetDC(None)
	iDPI = -1; # assume failure
	if hdcScreen:
		iDPI = gdi32.GetDeviceCaps(hdcScreen, LOGPIXELSX)
		user32.ReleaseDC(None, hdcScreen)
	if iDPI  <0 : raise RuntimeError("could not retrieve screen dpi")
	return iDPI


#
def GetObjectType(obj):
	try: return GDI_OBJECTS[gdi32.GetObjectType(obj.handle)]
	except: return 'unknown'



