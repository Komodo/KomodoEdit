"""

LAST VISITED 


TODO
	- system imagelist (small, large)

"""

from wnd import gdi
from wnd.wintypes import (comctl32, 
													kernel32,
													shell32,
													c_int,
													byref,
													sizeof,
													WINFUNCTYPE,
													POINTER,
													memmove,
													POINT,
													BOOL,
													HANDLE,
													INT,
													SHFILEINFO,
													create_string_buffer)
from wnd.fwtypes import TrackHandler
from ctypes.com import COMObject
from ctypes.com.storage import IStream
from wnd.api import winos


comctl32.InitCommonControls()
#**************************************************
S_OK = 0
S_FALSE = 1
STG_E_ACCESSDENIED = -2147287035 
STG_E_CANTSAVE  =   0x80030103L
STG_E_MEDIUMFULL = 2147680368L                 
E_NOTIMPL    = -2147467263

#**************************************************

class Factory(object):
    def LockServer(self, arg, arg2):
		pass

#**************************************************
# IStream implementation used to write and read imagelists
class IStreamImpl(COMObject):
	_com_interfaces_ = [IStream]
	_factory = Factory()

	def __init__(self, data=None):
		COMObject.__init__(self)
		self.IStream = self._com_pointers_[0][1]
		if data: self.data=data
		else: self.data = ''
			
	def Read(self, this, pv, cb, pRead):
		try:
			bytes = self.data[:cb]
			self.data = self.data[cb:]
			memmove(pv, bytes, cb)
			return S_OK
		except: return S_FALSE
	
	def Write(self, this, pv, cb, pWritten):
		try:
			p = create_string_buffer(cb)
			memmove(p, pv, cb)
			self.data = self.data + p.raw
			# imagelists don't seem to care
			#try: pWritten[0]	# NULL pointer test
			#except: pass
			return S_OK
		except: return STG_E_CANTSAVE

	def Seek(self, this, move, origin, pNewPos):return E_NOTIMPL
	def SetSize(self, this, newsize):	return STG_E_MEDIUMFULL
	def CopyTo(self, this, pDest, cb, pRead, pWritten):	return E_NOTIMPL
	def Commit(self, this, flags):	return E_NOTIMPL
	def Revert(self, this): return E_NOTIMPL
	def LockRegion(self, this, start, length, locktype):return E_NOTIMPL
	def UnlockRegion(self, this,  start, length, locktype): return E_NOTIMPL
	def Stat(self, this, pStats, flags): return E_NOTIMPL
	def Clone(self, this, pIStream): return E_NOTIMPL


#----------------------------------------------------------

def INDEXTOOVERLAYMASK(i): return i << 8

IMGL_CREATEFLAGS = {"mask" : 1,"color" : 0,"colordb" : 254,
"color4" : 4,"color8" :  8,"color16" : 16,"color24" : 24,
"color32" : 32}

IMGL_DRAWFLAGS={"normal" : 0,"transparent" : 1,"blend25" : 2,
"focus" : 2,"blend" : 4,"blend50" : 4,"selected" : 4,
"mask" : 16,"image" : 32,"rop" : 64,"overlaymask" : 3840}

FILEINFO_FLAGS={'linkoverlay' : 32768,
									'selected' : 65536,
									'largeicon' : 0,
									'smallicon' : 1,
									'openicon' : 2,
									'shelliconsize' : 4}		#'sysiconindex' : 4096
	

#***********************************************
class ImagelistFromHandle(object):
	"""Baseclass for imagelist apis"""

	def __init__(self, handle):
		self.handle = handle
		
		
	def Write(self):
		self.stream = IStreamImpl()
		result =comctl32.ImageList_Write(self.handle, byref(self.stream.IStream))
		del self.stream.IStream
		if not result: raise RuntimeError("could not write imagelist")
		#self.stream = None
		return self.stream.data
			
	def Copy(self):
		handle = comctl32.ImageList_Duplicate(self.handle)
		if not handle:	raise RuntimeError("could not copy imagelist")
		return ImageListFromHandle(handle)
	
	#----------------------------------------------------------------------
	# icons
	def AddIcons(self, *Icons):
		for n, i in enumerate(Icons):
			result = comctl32.ImageList_ReplaceIcon(self.handle, -1, i.handle)
			i.Close()
			if result < 0: raise RuntimeError("could not add icon: (%s)" % n)
		return result - n

	def ReplaceIcon(self, i, Icon):
		result = comctl32.ImageList_ReplaceIcon(self.handle, i, Icon.handle)
		Icon.Close()
		if result < 0: raise RuntimeError("could not replace icon")
		return result
		
	
	def AddIconFromFile(self, path):
		IMAGE_ICON        = 1
		LR_LOADFROMFILE      = 16
		w, h = self.GetIconSize()
		handle = user32.LoadImageA(0, path, IMAGE_ICON, w, h, LR_LOADFROMFILE)
		if not handle:	raise RuntimeError("could not load icon")
		result = comctl32.ImageList_ReplaceIcon(self.handle, -1, handle)
		if not user32.DestroyIcon(handle): raise RuntimeError("could not close icon")
		if result < 0: raise RuntimeError("could not add icon")
		return result
		
	def GetIcon(self, i, *flags):
		flag = 0
		for n in flags:
			if isinstance(n, int):
				flag |= INDEXTOOVERLAYMASK(n)
			else:
				try: flag |=  IMGL_DRAWFLAGS[n]
				except: raise ValueError("invalid style: %s" % n)
		handle = comctl32.ImageList_GetIcon(self.handle, i, flag)
		if not handle:
			raise RuntimeError("could not retrieve icon")
		return gdi.icon.IconFromHandle(handle)
	
	def SetIconSize(self, w, h):
		if not comctl32.ImageList_SetIconSize(self.handle, w, h):
			raise RuntimeError("could not set size")
	
	def GetIconSize(self):
		w = c_int()
		h = c_int()
		if not comctl32.ImageList_GetIconSize(self.handle, byref(w), byref(h)):
			raise RuntimeError("could not retrieve icon size")
		return w.value, h.value
		
	#-------------------------------------------------------------------------
	# bitmaps
		
	
	def AddBitmap(self, Bitmap, Mask=0):
		if Mask: handle = Mask.handle
		else: handle = 0
		result = comctl32.ImageList_Add(self.handle, Bitmap.handle, handle)
		Bitmap.Close()
		if Mask: Mask.Close()
		if result < 0: raise RuntimeError("could not add bitmap")
		return result

	def AddMaskedBitmap(self, Bitmap, colorref):
		result = comctl32.ImageList_AddMasked(self.handle, Bitmap.handle, colorref)
		Bitmap.Close()
		if result < 0: raise RuntimeError("could not add bitmap")
		return result
	
	def ReplaceBitmap(self, i, Bitmap,  Mask=0):
		mask=Mask
		if Mask: mask = Mask.handle
		result = comctl32.ImageList_Replace(self.handle, i, Bitmap.handle, mask)
		Bitmap.Close()
		if Mask: Mask.Close()
		if not result: raise RuntimeError("could not replace bitmap")
		return result
		
	#--------------------------------------------------------------------
	# 
	def SetOverlayImage(self, i, n):
		if not comctl32.ImageList_SetOverlayImage(self.handle, i, n):
			raise RuntimeError("could not set overlay mage")
	
	def CopyImage(self, sourceindex, destindex, flag='copy'):
		if flag=='copy': flag = 0	# ILCF_MOVE
		elif flag=='swap': flag = 1		# ILCF_SWAP
		else:	raise 'invalid flag'
		if not comctl32.ImageList_Copy(
					self.handle,
					sourceindex,
					self.handle,
					destindex,
					flag): raise RuntimeError("could not copy image")
		
	def RemoveImage(self, i):
		if not comctl32.ImageList_Remove(self.handle, i):
			raise RuntimeError("could not remove image")
	
	def Clear(self):
		result = comctl32.ImageList_Remove(self.handle, -1)
		if result < 0: raise RuntimeError("could not clear imagelist")
		
	def Draw(self, DC, i, x, y, *flags):
		flag = 0
		for n in flags:
			if isinstance(n, (int, long)):	flag |= INDEXTOOVERLAYMASK(n)
			else:
				try: flag |= IMGL_DRAWFLAGS[n]
				except: raise ValueError("invalid draw flag: %s" % n)
		result = comctl32.ImageList_Draw(self.handle, i, DC.handle, x, y, flag)
		if not result: raise RuntimeError("could not draw image")

	def DrawEx(self, DC, i, x, y, w, h, colorBk, colorFg, *flags):
		CLR_NONE    = 4294967295
		CLR_DEFAULT = 4278190080
		if not colorBk:	colorBk = CLR_NONE
		elif colorBk=='default': colorBk = CLR_DEFAULT
		else: colorBk = RGB(*colorBk)
		if not colorFg: colorFg = CLR_NONE
		elif colorFg=='default': colorFg = CLR_DEFAULT
		else: colorFg = colorBk
		flag = 0
		for n in flags:
			if isinstance(n, int):	flag |= INDEXTOOVERLAYMASK(n)
			else:
				try: flag |= IMGL_DRAWFLAGS[n]
				except: raise ValueError("invalid draw flag: %s" % n)
		result = comctl32.ImageList_DrawEx(self.handle, i, DC.handle, x, y, w, h, colorBk, colorFg, flag)
		if not result: raise RuntimeError("could not draw image")

	def SetBkColor(self, colorref):
		CLR_NONE    = 4294967295
		if colorref==None:
			colorref = CLR_NONE
		result = comctl32.ImageList_SetBkColor(self.handle, colorref)
		if result == CLR_NONE:
			raise RuntimeError("could not set background color")
		return result

	def HasTransparentBk(self):
		return bool(comctl32.ImageList_GetBkColor(self.handle)==-1)
		
	def GetBkColor(self):
		result= comctl32.ImageList_GetBkColor(self.handle)
		if result >-1: return result

	def __iter__(self):
		for i in range(comctl32.ImageList_GetImageCount(self.handle)):
			yield i
		
	def __len__(self): return comctl32.ImageList_GetImageCount(self.handle)

	
	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("imagelist is closed")


#**************************************************
#**************************************************
class DisposableImagelist(ImagelistFromHandle):
	
	def __init__(self, handle):
		self.handle= handle
		TrackHandler.Register('imagelists', self.handle)

	def Close(self):
		if self.handle:
			TrackHandler.Unregister('imagelists', self.handle)
			if not comctl32.ImageList_Destroy(self.handle):
				raise RuntimeError("could not destroy imagelist")
			self.handle = 0	


#**************************************************
#**************************************************
class Imagelist(DisposableImagelist):		
	
	def __init__(self, w, h, size, maxsize, *flags):
		flag = 0
		for i in flags:
			try: flag |= IMGL_CREATEFLAGS[i]
			except:	raise ValueError("invalid flag")
		handle = comctl32.ImageList_Create(w, h, flag, size, maxsize)
		if not handle:
			raise RuntimeError("could not create imagelist")
		DisposableImagelist.__init__(self, handle)
				
#**************************************************
#**************************************************
class ImagelistFromBytes(DisposableImagelist):
		
	def __init__(self, bytes):
		self.stream = IStreamImpl(bytes)
		handle = comctl32.ImageList_Read(byref(self.stream.IStream))
		if not handle: raise RuntimeError("could not create imagelist from bytes")
		DisposableImagelist.__init__(self, handle)
		del self.stream.IStream
		del self.stream

#****************************************************
class ImagelistFromFile(DisposableImagelist):
	
	def __init__(self, path, w):
		LR_LOADFROMFILE      = 16
		IMAGE_BITMAP      = 0
		CLR_DEFAULT = 4278190080
		handle = comctl32.ImageList_LoadImage(
				0,
				path,
				w,
				0,
				CLR_DEFAULT,
				IMAGE_BITMAP,
				LR_LOADFROMFILE 
				)	
		if not handle:
			raise RuntimeError("could not load imagelist from file")
		DisposableImagelist.__init__(self, handle)


#**************************************************
#**************************************************
class SystemImagelist(object):
		
	def __init__(self, size='small'):
	
		GPA = kernel32.GetProcAddress
		isNT= winos.IsNT()
		if isNT:
			## ?? check what happens on successive inits
			## should be the same handle returned, at least I hope so
			GPA.restype = WINFUNCTYPE(BOOL, BOOL) 
			try:
				IconInit = GPA(shell32._handle, 660)
				IconInit(1)
			except:
				raise RuntimeError, "could not retrieve IconInit api"
			
		GPA.restype = WINFUNCTYPE(INT, POINTER(HANDLE), POINTER(HANDLE))
		try:
			SH_GetImageLists = GPA(shell32._handle, 71) 
		except:
			raise RuntimeError, "could not retrieve shell_GetImageLists api"
		
			
		small = HANDLE()
		large = HANDLE()
		if not SH_GetImageLists(byref(large), byref(small)):
			raise RuntimeError, "could not retrieve system imagelist"
		
		if not (large.value and small.value):
			raise RuntimeError, "could not retrieve system imagelist"
		
		if size=='small':
			self.handle= small.value
		else:
			self.handle= large.value
							
	
	def AddIcons(self, *Icons):
		for n, i in enumerate(Icons):
			result = comctl32.ImageList_ReplaceIcon(self.handle, -1, i.handle)
			i.Close()
			if result < 0: raise RuntimeError("could not add icon: (%s)" % n)
		return result - n
	
	
	def SetBkColor(self, colorref):
		CLR_NONE    = 4294967295
		if colorref==None:
			colorref = CLR_NONE
		result = comctl32.ImageList_SetBkColor(self.handle, colorref)
		if result == CLR_NONE:
			raise RuntimeError("could not set background color")
		return result
	
	def GetIconIndex(self, path, *flags):
		flag = 16384  # SHGFI_SYSICONINDEX
		for i in flags:
			try: flag |= FILEINFO_FLAGS[i]
			except: raise ValueError("invalid flag: %s" % i)
					
		fileattributes = 0
		if path[0]=='*':
			fileattributes = 128	# FILE_ATTRIBUTE_NORMAL
			flag |= 16					# SHGFI_USEFILEATTRIBUTES 
		
		if path=='directory':
			fileattributes = 16	# FILE_ATTRIBUTE_DIRECTORY
			flag |= 16				# SHGFI_USEFILEATTRIBUTES 
		
		fi = SHFILEINFO()
		if not shell32.SHGetFileInfoA(path, fileattributes, byref(fi), sizeof(SHFILEINFO), flag):
			raise RuntimeError("could not retrieve icon")
		return fi.iIcon
		
	
	def Draw(self, DC, i, x, y, *flags):
		flag = 0
		for n in flags:
			if isinstance(n, (int, long)):	flag |= INDEXTOOVERLAYMASK(n)
			else:
				try: flag |= IMGL_DRAWFLAGS[n]
				except: raise ValueError("invalid draw flag: %s" % n)
		if not comctl32.ImageList_Draw(self.handle, i, DC.handle, x, y, flag):
			raise RuntimeError("could not draw image")

	def DrawEx(self, DC, i, x, y, w, h, colorBk, colorFg, *flags):
		CLR_NONE    = 4294967295
		CLR_DEFAULT = 4278190080
		if not colorBk:	colorBk = CLR_NONE
		elif colorBk=='default': colorBk = CLR_DEFAULT
		else: colorBk = RGB(*colorBk)
		if not colorFg: colorFg = CLR_NONE
		elif colorFg=='default': colorFg = CLR_DEFAULT
		else: colorFg = colorBk
		flag = 0
		for n in flags:
			if isinstance(n, int): flag |= INDEXTOOVERLAYMASK(n)
			else:
				try: flag |= IMGL_DRAWFLAGS[n]
				except: raise ValueError("invalid draw flag: %s" % n)
		result = comctl32.ImageList_DrawEx(self.handle, i, DC.handle, x, y, w, h, colorBk, colorFg, flag)
		if not result: raise RuntimeError("could not draw image")	
			
	def GetIconSize(self):
		w = c_int()
		h = c_int()
		if not comctl32.ImageList_GetIconSize(self.handle, byref(w), byref(h)):
			raise RuntimeError("could not retrieve icon size")
		return w.value, h.value
		
	
	def Close(self):
		pass

#**************************************************
#**************************************************
class DragImage:
	def __init__(self, imagelist):
			self.handle = imagelist.handle
	
	def BeginDrag(self, i, x, y):
		"""Begins dragging an image. x and y specifies the hotspot
		of the image."""
		if not ImageList_BeginDrag(self.handle, i, x, y):
			raise RuntimeError("could not begin drag")

		def DragEnter(self, hwnd, x, y):
			"""Locks updates to the specified window during a drag operation and displays the drag image at the specified position within the window. """
			if not comctl32.ImageList_DragEnter(hwnd, x, y):
				raise RuntimeError("drag enter failed")
		
		def DragMove(self, x, y):
			"""Moves the image to the specified position, mostly
			this should be a task for WM_MOUSEMOVE."""
			if not comctl32.ImageList_DragMove(x, y):
				raise RuntimeError("drag move failed")
		
		def DragLeave(self, hwnd):
			"""Unlocks the window"""
			if not comctl32.ImageList_DragLeave(hwnd):
				raise RuntimeError("drag leave failed")
				
		def EndDrag(self):
			"""Ends a drag operation"""
			if not comctl32.ImageList_EndDrag():
				raise RuntimeError("could not end drag")

		def ShowDragImage(self):
			"""Shows the image being dragged."""
			comctl32.ImageList_DragShowNolock(1)
		
		def HideDragImage(self):
			"""Hides the image being dragged."""
			comctl32.ImageList_DragShowNolock(0)
		
		def SetCursorImage(self, i, x, y, Imagelist=None):
			"""Creates a new drag image by combining the specified
			image i with the current drag image. x and y are the
			coordinates of the hotspot.	You can specify an imagelist
			from wich the image is to be taken. To make a long story
			short, you would like to have a dragcursor attatched to the
			image being dragged, this is how its done."""
			if Imagelist: handle = Imagelist.handle
			else: handle = self.handle
			if not comctl32.ImageList_SetDragCursorImage(handle, i, x, y):
				raise RuntimeError("could not set cursorimage")

		def GetDragPos(self):
			"""Retrieves the current drag position as tuple (x, y)."""
			pt = POINT()
			if not comctl32.ImageList_GetDragImage(byref(pt), 0):
				raise RuntimeError("could not retrieve drag position")
			return point.x, point.y	
				
		def GetHotSpot(self):
			"""Retrieves the current hotspot position as tuple (x, y)."""
			point = POINT()
			if not comctl32.ImageList_GetDragImage(0, byref(pt)):
				raise RuntimeError("could not retrieve drag position")
			return point.x, point.y	
		
#-----------------------------------------------------------------------------
	# not implemented
	
	# write or read imagelist from stream
	#ImageList_ReadEx = windll.comctl32.ImageList_ReadEx
	#ImageList_WriteEx = windll.comctl32.ImageList_WriteEx
	#ILP_NORMAL    = 0 # Writes or reads the stream using new sematics for this version of comctl32
	#ILP_DOWNLEVEL = 1 # Write or reads the stream using downlevel sematics
		
	# ?? could not find these
	#ILS_NORMAL   = 0
	#ILS_GLOW     = 1
	#ILS_SHADOW   = 2
	#ILS_SATURATE = 4
	#ILS_ALPHA    = 8
	
	#def merge(self):
	#	"""Not yet implemented."""
	#		comctl32.ImageList_Merge 
	
	#def getimageinfo(self):
	#	"""Not yet implemented."""
	#	comctl32.ImageList_GetImageInfo
	
	#def expand(self, n):
	#	comctl32.ImageList_SetImageCount(self.handle, n)


#class IMAGELISTDRAWPARAMS(Structure):
#	_fields_=[("cbSize", DWORD),
#						("himl", HIMAGELIST),
#						("i", INT),
#						("hdcDst", HDC),
#						("x", INT),
#						("y", INT),
#						("cx", INT),
#						("cy", INT),
#						("xBitmap", INT),	# x offest from the upperleft
#						("yBitmap", INT),	# y offest from the upperleft of bitmap
#						("rgbBk", COLORREF),
#						("rgbFg", COLORREF),
#						("fStyle", UINT),
#						("dwRop", DWORD)]


#class IMAGEINFO(Structure):
#	_fields_=[("hbmImage", HBITMAP),
#						("hbmMask", HBITMAP),
#						("Unused1", INT),
#						("Unused2", INT),
#						("rcImage", RECT)]


