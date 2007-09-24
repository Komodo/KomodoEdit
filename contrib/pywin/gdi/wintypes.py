

from wnd.wintypes import *

#from ctypes.wintypes import (Structure,
#														WORD,
#														DWORD,
#														LONG,
#														c_void_p,
#														c_ubyte,
#														BOOL,
#														HANDLE,
#														BYTE,)
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


def setupBITMAPINFO(nColors=0):
	"""Returns an uninitialized BITMAPINFO struct
	with an array length 'nColors' of RGBQUAD
	structures."""
	#if nColors == 0:
	#	class BITMAPINFO(Structure):
	#		_fields_ = [("bmiHeader", BITMAPINFOHEADER)]
	#else:
	class BITMAPINFO(Structure):
		_fields_ = [("bmiHeader", BITMAPINFOHEADER),
							("bmiColors", RGBQUAD*nColors)]
	return BITMAPINFO

class BITMAPFILEHEADER(Structure):
	_pack_ = 2	 ## (!!)
	_fields_ = [("bfType", WORD),
						("bfSize", DWORD),
						("bfReserved1", WORD),
						("bfReserved2", WORD),
						("bfOffBits", DWORD)]

class BITMAPINFOHEADER(Structure):
	_fields_  = [("biSize", DWORD),
						("biWidth",  LONG),
						("biHeight",  LONG),
						("biPlanes", WORD),
						("biBitCount", WORD),
						("biCompression", DWORD),
						("biSizeImage", DWORD),
						("biXPelsPerMeter", LONG),
						("biYPelsPerMeter", LONG),
						("biClrUsed", DWORD),
						("biClrImportant", DWORD)]	

class BITMAP(Structure):
	_fields_ = [("bmType", LONG),
						("bmWidth", LONG),
						("bmHeight", LONG),
						("bmWidthBytes", LONG),
						("bmPlanes", WORD),
						("bmBitsPixel", WORD),
						("bmBits", c_void_p)]

class RGBQUAD(Structure):
	_fields_ = [("rgbBlue", c_ubyte),
						("rgbGreen", c_ubyte),
						("rgbRed", c_ubyte),
						("rgbReserved", c_ubyte)]



# save icons and cursors to file
class ICONINFO(Structure):
	_fields_ = [("fIcon", BOOL),
						("xHotspot", DWORD),
						("yHotspot", DWORD),
						("hbmMask", HANDLE),
						("hbmColor", HANDLE)]

class ICONDIRENTRY(Structure):
	_pack_= 2
	_fields_ = [("bWidth", BYTE),
						("bHeight", BYTE),
						("bColorCount", BYTE),
						("bReserved", BYTE),
						("wPlanes", WORD),
						("wBitCount", WORD),
						("dwBytesInRes", DWORD),
						("dwImageOffset", DWORD)]

class ICONDIR(Structure):
	_pack_= 2		## (!!)
	_fields_ = [("idReserved", WORD),
						("idType", WORD),
						("idCount", WORD)	]

def setupICONIMAGE(nColors, nXOR, nAND):
	class ICONIMAGE(Structure):
		_pack_= 2
		_fields_ = [("icHeader", BITMAPINFOHEADER),
							("icColors", RGBQUAD*nColors),
							("icXOR", c_ubyte*nXOR),
							("icAND", c_ubyte*nAND)]
	return ICONIMAGE
	

