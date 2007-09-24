

from ctypes.wintypes import *
from ctypes.com import GUID
from wnd import WND_LIBPATH
gdip = windll.LoadLibrary('%s\\gdiplus.dll' % WND_LIBPATH)

COLORREF= c_ulong
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class _GdipInit(object):
	"""Helper class. Init and shutdown gdiplus."""
	def __init__(self):
		class GdiplusStartupInput(Structure):
			_fields_= [("GdiplusVersion", c_uint),
						("SuppressBackgroundThread", BOOL),
						("SuppressExternalCodecs", BOOL)]
		self.token = pointer(c_ulong())
		result = gdip.GdiplusStartup(byref(self.token),
									byref(GdiplusStartupInput(1, 0, 0)), 
									None)
		if result: raise GdiPlusError(result)
		self.closefunc = gdip.GdiplusShutdown
	def Close(self):
		self.closefunc(self.token)


class GdiPlusError(Exception):
	def __init__(self, value):
		try:
			self.value = {0:'Ok',1:'GenericError',	2:'InvalidParameter',
				3:'OutOfMemory',4:'ObjectBusy',5:'InsufficientBuffer',
				6:'NotImplemented',7:'Win32Error',8:'WrongState',
				9:'Aborted',10:'FileNotFound',11:'ValueOverflow',
				12:'AccessDenied',13:'UnknownImageFormat',
				14:'FontFamilyNotFound',15:'FontStyleNotFound',
				16:'NotTrueTypeFont',17:'UnsupportedGdiplusVersion',
				18:'GdiplusNotInitialized',19:'PropertyNotFound',
				20:'PropertyNotSupported'}[value]
		except:
			self.value = 'Unknown Error'
		
	def __str__(self):
		return repr(self.value)

#*******************************************************************************
class ImageCodecInfo(Structure):
	_fields_=[("Clsid", GUID),
				("FormatID", GUID),
				("CodecName", c_wchar_p),
				("DllName", c_wchar_p),
				("FormatDescription", c_wchar_p),
				("FilenameExtension", c_wchar_p),
				("MimeType", c_wchar_p),
				("Flags", DWORD),
				("Version", DWORD),
				("SigCount", DWORD),
				("SigSize", DWORD),
				("SigPattern", POINTER(c_ubyte*1)),
				("SigMask", POINTER(c_ubyte*1))]

class rectF(Structure):
	_fields_=[("x", c_float),
				("y", c_float),
				("width", c_float),
				("height", c_float)]

class sizeF(Structure):
	_fields_=[("height", c_float),
					("width", c_float)]
