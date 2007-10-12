

from wnd.gdip.wintypes import *

#****************************************************
#
#		Image Classes
#
#****************************************************


class ImageEncoder(object):
	Encoder            = 1
	Decoder            = 2
	SupportBitmap      = 4
	SupportVector      = 8
	SeekableEncode     = 16
	BlockingDecode     = 32
	Builtin            = 65536
	
	def __init__(self):
		num = c_uint()
		size = c_uint()
		result = gdip.GdipGetImageEncodersSize(byref(num), byref(size))
		if result: raise GdiPlusError(result)
		self._pMem= (c_ubyte*size.value)()
		result = gdip.GdipGetImageEncoders(num.value, size.value, byref(self._pMem))
		if result: raise GdiPlusError(result)
		self.arrCodecInfo = (ImageCodecInfo*num.value).from_address(addressof(self._pMem))
		
	def __iter__(self): 
		for i in self.arrCodecInfo: yield i
	
	def GetCodecSignature(self, Encoder):
		size = Encoder.SigSize
		pattern=(c_ubyte*size).from_address(
						addressof(Encoder.SigPattern[0]))
		mask=(c_ubyte*size).from_address(
						addressof(Encoder.SigMask[0]))
		return pattern, mask 


class ImageDecoder(object):
	Encoder            = 1
	Decoder            = 2
	SupportBitmap      = 4
	SupportVector      = 8
	SeekableEncode     = 16
	BlockingDecode     = 32
	Builtin            = 65536
	
	def __init__(self):
		num = c_uint()
		size = c_uint()
		result = gdip.GdipGetImageDecodersSize(byref(num), byref(size))
		if result: raise GdiPlusError(result)
		self._pMem= (c_ubyte*size.value)()
		result = gdip.GdipGetImageDecoders(num.value, size.value, byref(self._pMem))
		if result: raise GdiPlusError(result)
		self.arrCodecInfo = (ImageCodecInfo*num.value).from_address(addressof(self._pMem))
		
	def __iter__(self): 
		for i in self.arrCodecInfo: yield i
	
	def GetCodecSignature(self, Encoder):
		size = Encoder.SigSize
		pattern=(c_ubyte*size).from_address(
						addressof(Encoder.SigPattern[0]))
		mask=(c_ubyte*size).from_address(
						addressof(Encoder.SigMask[0]))
		return pattern, mask 


codec = ImageDecoder()



#****************************************************
class ImageFromPointer(object):
	def __init__(self, ptr):
		self.ptr = ptr		# pointer to the C instance

	def GetThumbnail(self, width=0, height=0):
		ptr = pointer(c_ulong())
		result = gdip.GdipGetImageThumbnail(self.ptr, width, height, byref(ptr), None, None)
		if result: raise GdiPlusError(result)
		return ImageFromPointer(ptr)

		
	def GetDimension(self):
		width = c_float()
		height = c_float()
		result = gdip.GdipGetImageDimension(self.ptr, byref(width), byref(height))
		if result: raise GdiPlusError(result)
		return width.value, height.value
		
	
	def GetBounds(self):
		rc = rectF()
		unit = c_ulong()
		result=gdip.GdipGetImageBounds(self.ptr, byref(rc), byref(unit))
		if result: raise GdiPlusError(result)
		return rc, unit.value
		
	
	def SaveToFile(self, path, Encoder, overwrite=False):
		path = unicode(path)
		result=gdip.GdipSaveImageToFile(self.ptr, path, byref(Encoder.Clsid), None)
		if result: raise GdiPlusError(result)
		
	
	def Close(self):
		result=gdip.GdipDisposeImage(self.ptr)
		if result: raise GdiPlusError(result)
		self.ptr = None
		

#***************************************************
class Image(ImageFromPointer):
	def __init__(self, path):
		path = unicode(path)
		self.ptr = pointer(c_ulong())
		result=gdip.GdipLoadImageFromFile(path, byref(self.ptr))
		if result: raise GdiPlusError(result)

#*************************************************************************
