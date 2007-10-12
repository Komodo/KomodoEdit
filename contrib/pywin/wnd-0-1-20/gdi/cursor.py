
from wnd.gdi.wintypes import *
from wnd.gdi.trackhandles import TrackHandler
from wnd.gdi.bitmap import DisposableBitmap
#*************************************************
#
#							Cursor classes
#
#*************************************************
__all__= ("SYSTEM_CURSORS", "CursorFromHandle", "DisposableCursor", "SystemCursor", "CursorFromFile", "CursorFromInstance", "CursorFromBytes")		

SYSTEM_CURSORS= {
				'arrow' : 32512,
				'ibeam' : 32513,
				'wait' : 32514,
				'cross' : 32515,
				'uparrow' : 32516,
				'size' : 32640,
				'icon' : 32641,
				'sizenwse' : 32642,
				'sizenesw' : 32643,
				'sizewe' : 32644,
				'sizens' : 32645,
				'sizeall' : 32646,
				'no' : 32648,
				'hand' : 32649,
				'appstarting' : 32650,
				'help' : 32651}

class CursorMethods(object):
	"""cursor class."""
	
	
	

	def SaveToFile(self, path, bits=32):
		#
		# TODO
		# check bit-depth for the color bitmap. Currently its allways 8-bit
		# 
		# an icon file consists of an ICONDIR structure specifying
		# the number of icons in the file.  
		# Next is an ICONDIERENTRY for each icon with the data for each icon,
		# (where to locate the icons data, how many bytes in it and so on).
		# Finally ICONIMAGE structures containing the actual data for each
		# icon.
		info= self.GetCursorInfo()
				
		# get bytes and info for the two bitmaps used for the icon
		if info.hbmColor:
			# color cursor
			bmColor= DisposableBitmap(info.hbmColor)
			biColor= bmColor.GetBitmapInfo(bits=bits)	# ?? 16-bits dono work
			bytesColor= bmColor.GetDibBits(biColor)
			bmColor.Close()
			bmMask= DisposableBitmap(info.hbmMask)
			biMask= bmMask.GetBitmapInfo(bits=1)	# allways 1-bit
			bytesMask= bmMask.GetDibBits(biMask)
			bmMask.Close()
			ICONIMAGE = setupICONIMAGE(len(biColor.bmiColors),
																			sizeof(bytesColor),
																			sizeof(bytesMask))
		else:
			# monochrome cursor (--no color bitmap here--)
			bmColor= DisposableBitmap(info.hbmMask)
			biColor= bmColor.GetBitmapInfo(bits=1)
			bytesColor= bmColor.GetDibBits(biColor)
			bmColor.Close()
			bmMask=None
			ICONIMAGE = setupICONIMAGE(len(biColor.bmiColors),
																		sizeof(bytesColor),
																		0)
			
		ii = ICONIMAGE()
		ii.icHeader = biColor.bmiHeader
		if bmMask:
			ii.icHeader.biHeight *= 2					# mask + color
			ii.icHeader.biSizeImage += biMask.bmiHeader.biSizeImage
		ii.icHeader.biCompression = 0			# allways zero
		ii.icHeader.biXPelsPerMeter = 0		# allways zero
		ii.icHeader.biYPelsPerMeter = 0		# allways zero
		ii.icHeader.biClrUsed = 0					# allways zero
		ii.icHeader.biClrImportant = 0			# allways zero
		ii.icColors = biColor.bmiColors
		ii.icXOR = bytesColor
		if bmMask:
			ii.icAND = bytesMask
					
		# setup ICONDIERENTRY for the cursor
		ide = ICONDIRENTRY()
		ide.bWidth =  biColor.bmiHeader.biWidth
		ide.bHeight = biColor.bmiHeader.biHeight
		ide.wPlanes = biColor.bmiHeader.biPlanes
		ide.wBitCount = biColor.bmiHeader.biBitCount
		if (ide.wPlanes * ide.wBitCount) >= 8:
			ide.bColorCount = 0
		else:
			ide.bColorCount = 1 << (ide.wPlanes * ide.wBitCount)
		ide.dwBytesInRes = sizeof(ii)
		ide.dwImageOffset = sizeof(ICONDIR) + sizeof(ide)		##
	
		# setup ICONDIR for the icon
		idir = ICONDIR()
		idir.idType = 2		# 2 for cursors
		idir.idCount = 1
			
		# dump all the structures to file
		# ...bit messy in ctypes currently
		fp=open(path, 'wb')
		try:
			p= create_string_buffer(sizeof(idir))
			memmove(p, addressof(idir), sizeof(idir))
			fp.write(p.raw)
			p= create_string_buffer(sizeof(ide))
			memmove(p, addressof(ide), sizeof(ide))
			fp.write(p.raw)
			p= create_string_buffer(sizeof(ii))
			r=memmove(p, byref(ii), sizeof(ICONIMAGE))
			fp.write(p.raw)
		finally: fp.close()
		
		
	
	
	def GetDibBits(self, cursotinfo, bits=8):
		#
		# TODO
		# test with color cursors
		#
		
		if cursotinfo.hbmColor:
			bmColor= DisposableBitmap(cursotinfo.hbmColor)
			try:
				bi= bmColor.GetBitmapInfo(bits=bits)
				bytesColor= bmColor.GetDibBits(bi)
			finally: bmColor.Close()
			bmMask= DisposableBitmap(cursotinfo.hbmMask)
			try:
				bi= bmMask.GetBitmapInfo(bits=1)
				bytesMask= bmMask.GetDibBits(bi)
			finally: bmMask.Close()
			return bytesMask, bytesColor
			
		
		bm= DisposableBitmap(cursotinfo.hbmMask)
		try:
			bi= bm.GetBitmapInfo(bits=bits)
			bytes= bm.GetDibBits(bi)
		finally:
			bm.Close()
		
		n= len(bytes)/2
		AND = (c_ubyte*n)()
		XOR = (c_ubyte*n)()
		memmove(XOR, bytes, sizeof(XOR))
		memmove(AND, addressof(bytes)+sizeof(XOR), sizeof(AND))
		return AND, XOR
	
	
	def GetCursorInfo(self):
		ii = ICONINFO()
		if not user32.GetIconInfo(self.handle, byref(ii)):
			raise RuntimeError("could not retrieve icon info")
		return ii

	def ReleaseCursorInfo(self, cursorinfo):
		if gdi32.GetObjectType(cursorinfo.hbmMask):
			gdi32.DeleteObject(cursorinfo.hbmMask)
		if gdi32.GetObjectType(cursorinfo.hbmColor):
			gdi32.DeleteObject(cursorinfo.hbmColor)
	

	#---------------------------------------------------------------
	
	
	
	def __init__(self): 
		"""Simple cursor class bundling some cursor functions.
		set() should do nothing cos this class doesn't keep an 
		actuall cursor. Use cursorfromfile or systemcursor instead."""
		
		self.handle = 0
	
	def GetPosition(self):
		"""Returns a point containing the current cursor position in 
		screen coordinates."""
		pt = POINT()
		if not user32.GetCursorPos(pt.byref(pt)):
			raise RuntimeError("could not retrieve cursor position")
		return pt

	def SetPos(self, x, y):
		"""Sets the cursor to the new position (screen coordinates)."""
		if not user32.SetCursorPos(x, y):
			raise RuntimeError("could not set cursor position")

	def SetClipRect(self, Rect=0):
		"""Makes the cursor stay within a given screen rectangle.
		If rect parameter is 0, the cursor may go anywhere on the 
		screen."""
		if Rect:
			if not user32.ClipCursor(byref(Rect)):
				raise RuntimeError("could not set cliprect")
		else:
			if not user32.ClipCursor(0):
				raise RuntimeError("could not set cliprect for")

	def GetClipRect(self):
		"""Returns a rect with the current clip coordinates for cursors."""
		rc = RECT()
		if not user32.GetClipCursor(byref(rc)):
			raise RuntimeError("could not retrieve cliprect")
		return rc
		
	def Show(self):
		"""Shows the cursor."""
		user32.ShowCursor(1)

	def Hide(self):
		"""Hides the cursor."""
		user32.ShowCursor(0)

	def Set(self):
		"""Actually sets the cursor.
		
		Todo: 
			
			ref says: "If your application must set the cursor while it is in a window, make sure the class cursor for the specified window's class is set to NULL. If the class cursor is not NULL, the system restores the class cursor each time the mouse is moved." well(???) 
			
			"""
		user32.SetCursor(self.handle)

	def Copy(self, w=None, h=None):
		flag = 0
		if w == None or h == None:
			flag = LR_COPYRETURNORG     = 4
			w = h = 0
		IMAGE_CURSOR      = 2
		handle = user32.CopyImage(self.handle, IMAGE_CURSOR, w, h, flag)
		if not handle: raise RuntimeError("could not copy icon")
		return DisposableIcon(handle)
		

	

#***************************************************

class CursorFromHandle(CursorMethods):
	def __init__(self, handle):
		self.handle= handle
	
	def Release(self):
		self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("cursor is closed")

#*********************************************************************
class DisposableCursor(CursorMethods):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('cursors', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('cursors', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("cursor is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('cursors', self.handle)
			result= user32.DestroyCursor(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete cursor")
		else:
			raise RuntimeError("cursor is closed")

#***************************************************

class SystemCursor(CursorFromHandle):
		
	def __init__(self, cursorname):
		try: cursor =  SYSTEM_CURSORS[cursorname]
		except:	raise ValueError("invalid cursor: %s" % cursorname)
		handle = user32.LoadCursorA(0, cursor)
		if not handle: raise RuntimeError("could not load cursor")
		CursorFromHandle.__init__(self, handle)
	
#************************************************
class CursorFromFile(DisposableCursor):
	def __init__(self, path):
		IMAGE_CURSOR      = 2
		LR_LOADFROMFILE      = 16
		handle = user32.LoadImageA(0, path, IMAGE_CURSOR, 0, 0, LR_LOADFROMFILE)
		if not handle: raise RuntimeError("could not load cursor: %s" % path)
		DisposableCursor.__init__(self, handle)
	
					
#************************************************
class CursorFromInstance(DisposableCursor):
		
	def __init__(self, instance, resname):
		#if not resname.startswith('#'): 
		#	raise "resourcensames should be prefixed with: '#'"
		IMAGE_CURSOR      = 2
		if isinstance(instance, (int, long)): hInstance= instance
		else: hInstance= instance._handle
		handle = user32.LoadImageA(hInstance, resname, IMAGE_CURSOR, 0, 0, 0)
		if not handle: raise RuntimeError("could not load cursor")
		DisposableCursor.__init__(self, handle)
		
			
#***************************************************
class CursorFromBytes(DisposableCursor):
	
	def __init__(self, hotspotX, hotspotY, bytesAND, bytesXOR):
		handle= user32.CreateCursor(0, 
														hotspotX,  
														hotspotY, 
														user32.GetSystemMetrics(13),	# SM_CXCURSOR
														user32.GetSystemMetrics(14),	# SM_CYCURSOR
														bytesAND,
														bytesXOR)
		if not handle: raise RuntimeError("could not create cursor")
		DisposableCursor.__init__(self, handle)

	





