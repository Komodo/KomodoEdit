"""
The module defines a list SYSTEM_ICONS with the string 
identifiers all available predefined system icons to be used
with the 'systemicon' class.

"""


from wnd.wintypes import SHFILEINFO
from wnd.gdi.wintypes import *
from wnd.gdi.trackhandles import TrackHandler
from wnd.gdi.bitmap import DisposableBitmap
from ctypes import sizeof, byref, windll

user32= windll.user32
gdi32= windll.gdi32


__all__= ("GetShellIconSize", "GetShellSmallIconSize", "SYSTEM_ICONS", "IconFromHandle", "DisposableIcon", "IconFromFile", "FileIcon", "SystemIcon", "IconFromBytes", "IconFromInstance", "GetSysIconIndex")


SYSTEM_ICONS = {
			'application' : 32512,
			'error' : 32513,
			'hand' : 32513,
			'question' : 32514,
			'exclamation' : 32515,
			'warning' : 32515,
			'asterisk' : 32516,
			'information' : 32516,
			'winlogo' : 32517}

FILEINFO_FLAGS={'linkoverlay' : 32768,
									'selected' : 65536,
									'largeicon' : 0,
									'smallicon' : 1,
									'openicon' : 2,
									'shelliconsize' : 4}		#'sysiconindex' : 4096

DI_FLAGS= {
'mask':1,
'image':2,
'normal':3,
'compat':4,
'defaultsize':8,
'nomirror':16,
} 



#*********************************************
# functions
#*********************************************


def GetShellIconSize():
	SHGFI_SYSICONINDEX      = 16384  
	SHGFI_ICON              = 256
	SHGFI_LARGEICON         = 0  
	SHGFI_OPENICON          = 2  
	SHGFI_SHELLICONSIZE     = 4  
	shfi=SHFILEINFO()
	hImagelist=shell32.SHGetFileInfo('*.*', 0, byref(shfi), sizeof(SHFILEINFO), SHGFI_SYSICONINDEX|SHGFI_ICON|SHGFI_SHELLICONSIZE)
	user32.DestroyIcon(shfi.hIcon)
	w, h = INT(), INT()
	if not windll.comctl32.ImageList_GetIconSize(hImagelist, byref(w), byref(h)):
			raise RuntimeError("could not retrieve shell icon size")
	return w.value, h.value
	

def GetShellSmallIconSize():
	SHGFI_SYSICONINDEX      = 16384  
	SHGFI_ICON              = 256
	SHGFI_SMALLICON         = 1  
	SHGFI_OPENICON          = 2  
	SHGFI_SHELLICONSIZE     = 4  
	shfi=SHFILEINFO()
	hImagelist=shell32.SHGetFileInfo('*.*', 0, byref(shfi), sizeof(SHFILEINFO), SHGFI_SYSICONINDEX|SHGFI_ICON|SHGFI_SHELLICONSIZE|SHGFI_SMALLICON)
	user32.DestroyIcon(shfi.hIcon)
	w, h = INT(), INT()
	if not windll.comctl32.ImageList_GetIconSize(hImagelist, byref(w), byref(h)):
			raise RuntimeError("could not retrieve shell icon size")
	return w.value, h.value

def GetSysIconIndex(path, *flags):
	flag = 256|4096  # SHGFI_ICON|SHGFI_SYSICONINDEX
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
	user32.DestroyIcon(fi.hIcon)
	return fi.iIcon
	


#**************************************************
#
#							Icon classes
#
#**************************************************


class IconFromHandle(object):
	
		
	def __init__(self, handle):
		self.handle = handle
			
	def GetDibBits(self, iconinfo, bits=32):
		# get bytes and info for the two bitmaps used for the icon
		bmColor= DisposableBitmap(iconinfo.hbmColor)
		biColor= bmColor.GetBitmapInfo(bits=bits)	# ?? 16-bits dono work
		bytesColor= bmColor.GetDibBits(biColor)
		bmColor.Close()
		bmMask= DisposableBitmap(iconinfo.hbmMask)
		biMask= bmMask.GetBitmapInfo(bits=1)	# allways 1-bit
		bytesMask= bmMask.GetDibBits(biMask)
		bmMask.Close()
		return bytesMask, bytesColor
		
	
	def SaveToFile(self, path, bits=32):
		#
		# TODO
		# check bit-depth for the color bitmap. Currently 16-bit does not work
		# 
		# an icon file consists of an ICONDIR structure specifying
		# the number of icons in the file.  
		# Next is an ICONDIERENTRY for each icon with the data for each icon,
		# (where to locate the icons data, how many bytes in it and so on).
		# Finally ICONIMAGE structures containing the actual data for each
		# icon.
		info= self.GetIconInfo()
				
		# get bytes and info for the two bitmaps used for the icon
		bmColor= DisposableBitmap(info.hbmColor)
		biColor= bmColor.GetBitmapInfo(bits=bits)	# ?? 16-bits dono work
		bytesColor= bmColor.GetDibBits(biColor)
		bmMask= DisposableBitmap(info.hbmMask)
		biMask= bmMask.GetBitmapInfo(bits=1)	# allways 1-bit
		bytesMask= bmMask.GetDibBits(biMask)
		# no longer needed		
		bmMask.Close()
		bmColor.Close()
		
		#setup ICONIMAGE for the icon
		ICONIMAGE = setupICONIMAGE(len(biColor.bmiColors),
																	sizeof(bytesColor),
																	sizeof(bytesMask))
		ii = ICONIMAGE()
		ii.icHeader = biColor.bmiHeader
		ii.icHeader.biHeight *= 2					# mask + color
		ii.icHeader.biSizeImage += biMask.bmiHeader.biSizeImage
		ii.icHeader.biCompression = 0			# allways zero
		ii.icHeader.biXPelsPerMeter = 0		# allways zero
		ii.icHeader.biYPelsPerMeter = 0		# allways zero
		ii.icHeader.biClrUsed = 0					# allways zero
		ii.icHeader.biClrImportant = 0			# allways zero
		ii.icColors = biColor.bmiColors
		ii.icXOR = bytesColor
		ii.icAND = bytesMask
					
		# setup ICONDIERENTRY for the icon
		ide = ICONDIRENTRY()
		ide.bWidth =  biColor.bmiHeader.biWidth
		ide.bHeight = biColor.bmiHeader.biHeight
		ide.wPlanes = biColor.bmiHeader.biPlanes
		ide.wBitCount = biColor.bmiHeader.biBitCount
		if (ide.wPlanes * ide.wBitCount) > 8:
			ide.bColorCount = 0
		else:
			ide.bColorCount = 1 << (ide.wPlanes * ide.wBitCount)
		ide.dwBytesInRes = sizeof(ii)
		ide.dwImageOffset = sizeof(ICONDIR) + sizeof(ide)		##
	
		# setup ICONDIR for the icon
		idir = ICONDIR()
		idir.idType = 1
		idir.idCount = 1
			
		# dump all the structures to file
		# ...bit messy in ctypes currently
		fp=open(path, 'wb')
		try:
			fp.write(buffer(idir)[:])
			fp.write(buffer(ide)[:])
			fp.write(buffer(ii)[:])
		finally: fp.close()
					
	
	def GetIconInfo(self):
		ii = ICONINFO()
		if not user32.GetIconInfo(self.handle, byref(ii)):
			raise RuntimeError("could not retrieve icon info")
		return ii

	def ReleaseIconInfo(self, iconinfo):
		# make shure gdi not deadlocks when called with invalid handles
		if gdi32.GetObjectType(iconinfo.hbmMask):
			gdi32.DeleteObject(iconinfo.hbmMask)
		if gdi32.GetObjectType(iconinfo.hbmMask):
			gdi32.DeleteObject(iconinfo.hbmColor)
	

	#---------------------------------------------------------------
	
	def GetSize(self):
		ii = ICONINFO()
		if not user32.GetIconInfo(self.handle, byref(ii)):
			raise RuntimeError("could not retrieve icon info")
		bm=BITMAP()
		if not gdi32.GetObjectA(ii.hbmMask, sizeof(BITMAP), byref(bm)):
			raise RuntimeError("could not retrieve bitmap info")
		if ii.hbmMask:
			gdi32.DeleteObject(ii.hbmMask)
		if ii.hbmColor:
			gdi32.DeleteObject(ii.hbmColor)
			return bm.bmWidth, bm.bmHeight
		return bm.bmWidth, bm.bmHeight/2
		
	
	def Copy(self, w=None, h=None):
		flag = 0
		if w == None or h == None:
			flag = LR_COPYRETURNORG     = 4
			w = h = 0
		IMAGE_ICON        = 1
		handle = user32.CopyImage(self.handle, IMAGE_ICON, w, h, flag)
		if not handle: raise RuntimeError("could not copy icon")
		return DisposableIcon(handle)
	
		
	
	def DrawEx(self, dc, x, y, w, h, flag):
		try: flag= DI_FLAGS[flag]
		except: raise ValueError, "invalid flag: %s" % flag 
		if not user32.DrawIconEx(dc.handle, x, y, self.handle, w, h, 0, None, flag):
			raise "could not draw icon"
 	
	
	
	def Draw(self, dc, x, y):
		if not user32.DrawIcon(dc.handle, x, y, self.handle):
			raise RuntimeError("could not draw icon")
	
	def DrawState(self, dc, x, y, Brush, flag):
		nFlag=3	 # DST_ICON
		if Brush: 
			Brush=Brush.handle
			#nFlag |= 128	 # DSS_MONO
		else: Brush=0
		if flag=='disabled': nFlag |= 32		# DSS_DISABLED
		elif flag=='union': nFlag |= 16		# DSS_UNION
		elif flag=='mono': nFlag |= 128		# DSS_MONO
		elif not flag: pass
		else: raise ValueError("invalid flag: %s" % flag)
		if not user32.DrawStateA(dc.handle, Brush, None, self.handle, 0, x, y, 0, 0, nFlag):
			raise RuntimeError("could not draw state")
		
	
	def Release(self):
		self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("icon is closed")

#**************************************************
class DisposableIcon(IconFromHandle):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('icons', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('icons', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("icon is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('icons', self.handle)
			result= user32.DestroyIcon(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete icon")
			
		else:
			raise RuntimeError("icon is closed")

#***********************************************************************

class IconFromFile(DisposableIcon): 

	def __init__(self, path, w=0, h=0):
		IMAGE_ICON        = 1
		LR_LOADFROMFILE      = 16
		handle = user32.LoadImageA(0, path, IMAGE_ICON, w, h, LR_LOADFROMFILE)
		if not handle: raise RuntimeError("could not load icon: %s" % path)
		DisposableIcon.__init__(self, handle)
			

#**************************************************
class IconFromInstance(DisposableIcon): 
	
	def __init__(self, instance, resname, w=0, h=0):
		IMAGE_ICON        = 1
		if isinstance(instance, (int, long)): hInstance= instance
		else: hInstance= instance._handle
		self.handle = user32.LoadImageA(hInstance, resname, IMAGE_ICON, w, h, 0)
		if not self.handle: raise RuntimeError("could not load icon: %s" % path)
		DisposableIcon.__init__(self, self.handle)
	
#**************************************************
# TODO
# shared or not ??
# should be shared, cos its taken fron  the systems imagelist
#
# NOTE: the difference between win98 and NT system imagelist is:
# win98 has one imagelist for all processes, closing it will set your system
# back in an iconless world, while NT systems use one imagelist/process.
# Each time you request an icon via SHGetFileInfo it will be added to
# your processes imageist.

class FileIcon(DisposableIcon): 
		
	def __init__(self, path, *flags):
		self.handle = 0
		flag = 256  # SHGFI_ICON
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
		if not fi.hIcon: raise RuntimeError("could not retrieve icon")
		DisposableIcon.__init__(self, fi.hIcon)
	
#************************************************
class SystemIcon(IconFromHandle):
	"""sytemicon class"""
	
	def __init__(self, iconname):
						
		try: icon = SYSTEM_ICONS[iconname]
		except: raise ValueError("invalid icon: %s" % iconname)
		handle = user32.LoadIconA(0, icon)
		if not handle: raise RuntimeError("could not create icon")
		IconFromHandle.__init__(self, handle)
	

#***************************************************
class IconFromBytes(DisposableIcon):
	
	def __init__(self, bytesMASK, bytesCOLOR, bits, w=0, h=0):
		handle =user32.CreateIcon(0, w, h, 1, bits,bytesMASK,bytesCOLOR)  
 		if not handle: raise RuntimeError("could not create icon")
		DisposableIcon.__init__(self, handle)


	
	