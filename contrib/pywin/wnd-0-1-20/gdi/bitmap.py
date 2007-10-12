"""Bitmaps.

The module defines a list SYSTEM_BITMAPS with the string 
identifiers all available predefined system bitmaps to be used
with the 'systembitmap' class.
"""

from wnd.gdi.wintypes import *
from wnd.gdi.trackhandles import TrackHandler
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
__all__= ("SYSTEM_BITMAPS", "FlipDibBits", "BitmapFromHandle", "DisposableBitmap",  "CompatibleBitmap", "BitmapFromFile", 
"SystemBitmap", "BitmapFromBytes")

SYSTEM_BITMAPS = {
			'lfarrowi' : 32734,
			'rgarrowi' : 32735,
			'dnarrowi' : 32736,
			'uparrowi' : 32737,
			'combo' : 32738,
			'mnarrow' : 32739,
			'lfarrowd' : 32740,
			'rgarrowd' : 32741,
			'dnarrowd' : 32742,
			'uparrowd' : 32743,
			'restored' : 32744,
			'zoomd' : 32745,
			'reduced' : 32746,
			'restore' : 32747,
			'zoom' : 32748,
			'reduce' : 32749,
			'lfarrow' : 32750,
			'rgarrow' : 32751,
			'dnarrow' : 32752,
			'uparrow' : 32753,
			'close' : 32754,
			'btncorners' : 32758,
			'checkboxes' : 32759,
			'check' : 32760,
			'btsize' : 32761,
			'size' : 32766,
			}

RASTEROPERATIONS={
			'srccopy' : 13369376,
			'srcpaint' : 15597702, 
			'srcsnd' : 8913094, 
			'srcinvert' : 6684742, 
			'srcinvert' : 4457256, 
			'notsrccopy' : 3342344, 
			'notsrcerase' : 1114278,  
			'mergecopy' : 12583114, 
			'mergepaint' : 12255782, 
			'patcopy' : 15728673, 
			'patpaint' : 16452105, 
			'patinvert' : 5898313, 
			'dstinvert' : 5570569, 
			'blackness' : 66, 
			'whiteness' : 16711778,
			}

#*************************************************
# functions
def FlipDibBits(arrBytes):
	n= len(arrBytes)
	for i in range(0, n/2, 4):
		arrBytes[i:i+4], arrBytes[n-i-4:n-i]= arrBytes[n-i-4:n-i], arrBytes[i:i+4]
	#return arrBytes


#**************************************************
#
#				Bitmap classes
#
#**************************************************

class BitmapFromHandle(object):
	def __init__(self, handle):
		self.handle = handle
			
	
	def GetSize(self):
		bm=self.GetBitmap()
		return bm.bmWidth, bm.bmHeight
	
	def GetBitmap(self):
		bmp = BITMAP()
		result = gdi32.GetObjectA(self.handle, sizeof(BITMAP),		
		byref(bmp))
		if not result: raise RuntimeError("could not retrieve bitmap info")
		return bmp

	
	def GetBitmapInfo(self, bits=32):
		#
		# TODO
		# currently only RGB compression is supported
		#
		bmp = BITMAP()
		if not gdi32.GetObjectA(self.handle, sizeof(BITMAP), byref(bmp)):
			raise RuntimeError("could not retrieve bitmap info")
			
		if bits: bmp.bmBitsPixel=bits
		# get bitcount 
		nBits = bmp.bmPlanes * bmp.bmBitsPixel
		if nBits == 1: 	nBits = 1 
		elif nBits <= 4: nBits = 4; 
		elif nBits <= 8: nBits = 8; 
		elif nBits <= 16: nBits = 16 
		elif nBits <= 24: nBits = 24 
		else: nBits = 32
		bmp.bmBitsPixel= nBits

		nColors= 1<<nBits
		if nColors >256: nColors= 0	# no RGBQUAD array for 24 bit bitmaps
	
		# setup BITMAPINFO for the bitmap
		BITMAPINFO = setupBITMAPINFO(nColors=nColors)
		bi = BITMAPINFO()
		bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
		bi.bmiHeader.biWidth = bmp.bmWidth 
		bi.bmiHeader.biHeight = bmp.bmHeight 
		bi.bmiHeader.biPlanes = bmp.bmPlanes 
		bi.bmiHeader.biBitCount = bmp.bmBitsPixel
		bi.bmiHeader.biClrUsed = nColors
		bi.bmiHeader.biCompression = 0		# BI_RGB
		
		 #((((bi.biWidth * bi.biBitCount) + 31) & 31) / 8) * bi.biHeight;
		bi.bmiHeader.biSizeImage = (((bi.bmiHeader.biWidth * nBits +31) & ~31) /8) * bi.bmiHeader.biHeight
		bi.bmiHeader.biClrImportant = 0
		return bi
		
	def GetDibBits(self, bitmapinfo, Dc=None):
		"""Returns an array containing the raw bytes of the
		bitmap"""

		## TODO:
		## dono if we have to pad to align data on DWORD boundary
		##
		
		#data = create_string_buffer(bitmapinfo.bmiHeader.biSizeImage)
		data = (c_ubyte*bitmapinfo.bmiHeader.biSizeImage)()
		if Dc == None: hDc= user32.GetDC(0)
		else: hDc = DC.handle
		DIB_RGB_COLORS      = 0
		# get device independend bits
		result= gdi32.GetDIBits(hDc, self.handle, 0,
									bitmapinfo.bmiHeader.biHeight,
									data, 
									byref(bitmapinfo),
									DIB_RGB_COLORS)
		if hDc == None:
			user32.ReleaseDC(0, hDc)
		if result: return data
		raise RuntimeError("could not retrieve bitmap bytes")
			
	
	def SaveToFile(self, path, bits=32):
		"""Saves the bitmap to file."""
		bi= self.GetBitmapInfo(bits=bits)
		bytes= self.GetDibBits(bi)
		bfh= BITMAPFILEHEADER()
		bfh.bfType= MAKEWORD(ord('B'), ord('M'))
		bfh.bfSize= (sizeof(BITMAPFILEHEADER) +
						bi.bmiHeader.biSize +
						bi.bmiHeader.biClrUsed * sizeof(RGBQUAD) +
						bi.bmiHeader.biSizeImage)
		bfh.bfOffBits= bfh.bfSize - bi.bmiHeader.biSizeImage
		fp= open(path, 'wb')
		try:
			fp.write(buffer(bfh)[:])
			fp.write(buffer(bi)[:])
			fp.write(buffer(bytes)[:])
		finally:
			fp.close()

		

	#-------------------------------------------------------------------------------
	# bitmaps
	#
	# TODO
	# 
	# all the select object stuff
	
	def BitBlt(self, destDC, x, y, w, h, sourceDC, x2, y2, flag):
		try: 
			flag= RASTEROPERATIONS[flag]
		except: 
			raise RuntimeError("invalid flag: %s" % flag)
		hOldObj = gdi32.SelectObject(sourceDC.handle, self.handle)
		if not hOldObj: 
			raise RuntimeError("invalid bitmap")
		if not gdi32.BitBlt(destDC.handle,x,y,w,h,sourceDC.handle,x2,y2,flag):
			gdi32.SelectObject(sourceDC.handle, hOldObj)
			raise RuntimeError("could not blt")
		gdi32.SelectObject(sourceDC.handle, hOldObj)
		
		
	def StretchBlt(self, destDC, x, y, w, h, sourceDC, x2, y2, w2, h2, flag):
		try: 
			flag= RASTEROPERATIONS[flag]
		except: 
			raise RuntimeError("invalid flag: %s" % flag)
		hOldObj = gdi32.SelectObject(sourceDC.handle, self.handle)
		if not hOldObj: 
			raise RuntimeError("invalid bitmap")
		if not gdi32.StretchBlt(destDC.handle, x, y, w, h, sourceDC.handle, x2, y2, w2, h2, flag):
			gdi32.SelectObject(sourceDC.handle, hOldObj)
			raise RuntimeError("could not stretch blt")
		gdi32.SelectObject(sourceDC.handle, hOldObj)
	
	
	def Extract(self, dc, x, y, w, h, newW=None, newH=None):
		error= None
		DCsrc= None
		DCdst= None
		hBm= None
		hOldBm= None
		hOldBm2 = None
				
		if dc: DCsrc= dc.handle
		else: DCsrc = gdi32.CreateCompatibleDC(0)
		if DCsrc:
			hOldBm = gdi32.SelectObject(DCsrc, self.handle)
			if hOldBm:
				DCdst = gdi32.CreateCompatibleDC(DCsrc)
				if DCdst:
					if newW == None: newW= w
					if newH == None: newH= h
					hBm = gdi32.CreateCompatibleBitmap(DCsrc, newW, newH)
					if hBm:
						hOldBm2 =  gdi32.SelectObject(DCdst, hBm)
						if hOldBm2:
							SRCCOPY     = 13369376		
							if not gdi32.StretchBlt(DCdst, 0, 0, newW, newH, DCsrc, x, y, w, h, SRCCOPY):
								error= "could not stretch blt"
						else: error= "could not select new bitmap"
					else: error="could not create new bitmap"
				else: error="could not create dest dc"
			else: error= "could not select bitmap"
		else: error= "could not create source dc"
		if DCsrc:
			if hOldBm: gdi32.SelectObject(DCsrc, hOldBm)
			if not dc: gdi32.DeleteDC(DCsrc)
			if DCdst:
				if hOldBm2: gdi32.SelectObject(DCdst, hOldBm2)
				gdi32.DeleteDC(DCdst)
		if error: 
			if hBm: gdi32.DeleteObject(hBm)
			raise RuntimeError(error)
		else:	
			return DisposableBitmap(hBm)
		
	def Stretch(self, dc, w=None, h=None):
		wB, hB= self.GetSize()
		return self.Extract(dc, 0, 0, wB, hB, w, h)
				
	def Copy(self, dc):
		wB, hB= self.GetSize()
		return self.Extract(dc, 0, 0, wB, hB, wB, hB)

	def Release(self): 
		self.Close()
	
	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("bitmap is closed")
	
#*************************************************************
class DisposableBitmap(BitmapFromHandle):
	def __init__(self, handle):
		self.handle= handle
		TrackHandler.Register('bitmaps', self.handle)

	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('bitmaps', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("bitmap is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('bitmaps', self.handle)
			result= gdi32.DeleteObject(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not close bitmap")
		else:
			raise RuntimeError("bitmap is closed")

#***************************************************
class CompatibleBitmap(DisposableBitmap):
		
	def __init__(self, DC, width, height):
		"""Create a compatible bitmap."""
		handle = gdi32.CreateCompatibleBitmap(DC.handle, width, height)
		if not handle:	raise RuntimeError("could not create bitmap")
		DisposableBitmap.__init__(self, handle)
		
				
#**************************************************
class BitmapFromFile(DisposableBitmap): 
	
	def __init__(self, path, w=0, h=0):
		IMAGE_BITMAP      = 0
		LR_LOADFROMFILE      = 16
		handle = user32.LoadImageA(0, path, IMAGE_BITMAP, w, h, LR_LOADFROMFILE)
		if not handle:	raise RuntimeError("could not load bitmap: %s" % path)
		DisposableBitmap.__init__(self, handle)
			

#**************************************************
class SystemBitmap(BitmapFromHandle):
	
	def __init__(self, bitmapname, w=None, h=None):
		try: bitmap= SYSTEM_BITMAPS[bitmapname]
		except: raise ValueError("invalid bitmap: %s" % bitmapname)
		handle = user32.LoadBitmapA(0, bitmap)
		if not handle: raise RuntimeError("could not load bitmap: %s" % bitmapname)
		BitmapFromHandle.__init__(self, handle)
		
	#**************************************************
class BitmapFromBytes(BitmapFromHandle):
	
	def __init__(self, w, h, colorplanes, bits, bytes):
		handle = gdi32.CreateBitmap(w, h, colorplanes, bits, byref(bytes))
		if not handle: raise RuntimeError("could not create bitmap")
		BitmapFromHandle.__init__(self, handle)



	
		


class SystemBitmap2(CompatibleBitmap):
	
	def __init__(self, bitmap, w=None, h=None):
		"""Load one of the predefined system bitmaps. 
		Predefined bitmaps are:

		Or, if an instancehandle is given, icon should be the name of
		the resource	identifier of the icon in the executable file.
		"""
			
		try: bitmap = OBM_BITMAPS [bitmap]
		except: raise "invalid bitmap: %s" % bitmap
		if bitmap < 0:
			# get sprite from bitmap
			error=None
							
			hBmp = user32.LoadBitmapA(0, 32759)	 # OBM_CHECKBOXES
			if not hBmp: raise "could not load bitmap"
			bmp = BITMAP()
			if not gdi32.GetObjectA(hBmp, sizeof(bmp), byref(bmp)):
				raise "could not retrieve bitmap info"
			bmpW, bmpH = bmp.bmWidth, bmp.bmHeight
			if w==None: w=bmpW/4
			if h==None: h=bmpH/3
			DCsrc = gdi32.CreateCompatibleDC(0)
			if not DCsrc: error="could not create source dc"
			hOldBmp1 = gdi32.SelectObject(DCsrc, hBmp)
			DCdst = gdi32.CreateCompatibleDC(DCsrc)
			if not DCdst: error="could not create dest dc"
			self.handle = gdi32.CreateCompatibleBitmap(DCsrc, w, h)
			if not self.handle:  error="could not create bitmap"
			hOldBmp2 =  gdi32.SelectObject(DCdst, self.handle)
					
			if bitmap==-1: xB, yB, wB, hB=0, 0, bmpW/4, bmpH/3
			elif bitmap==-2: xB, yB, wB, hB = bmpW/4, 0, bmpW/4, bmpH/3
			elif bitmap==-3: xB, yB, wB, hB = (bmpW/4)*2, 0, bmpW/4, bmpH/3
			elif bitmap==-4: xB, yB, wB, hB = (bmpW/4)*3, 0, bmpW/4, bmpH/3
			elif bitmap==-5: xB, yB, wB, hB=0,  bmpH/3, bmpW/4, bmpH/3
			elif bitmap==-6: xB, yB, wB, hB = bmpW/4, bmpH/3, bmpW/4, bmpH/3
			elif bitmap==-7: xB, yB, wB, hB = (bmpW/4)*2, bmpH/3, bmpW/4, bmpH/3
			elif bitmap==-8: xB, yB, wB, hB = (bmpW/4)*3, bmpH/3, bmpW/4, bmpH/3
							
			SRCCOPY     = 13369376		
			#result= gdi32.StretchBlt(DCdst, 0, 0, w, h, DCsrc, xB, yB, wB, hB, SRCCOPY)
			result= gdi32.BitBlt(DCdst, 0, 0, w, h, DCsrc, xB, yB, SRCCOPY)
			if not result: error="could not StretchBlt"
			gdi32.SelectObject(DCsrc, hOldBmp1)
			gdi32.SelectObject(DCdst, hOldBmp2)
			gdi32.DeleteObject(hBmp)
			gdi32.DeleteDC(DCsrc)
			gdi32.DeleteDC(DCdst)
			if error:
				raise error
		
		else:
			self.handle = user32.LoadBitmapA(0, bitmap)
			if not self.handle:
				raise "could not load bitmap"
		
		TrackHandler.Register('bitmaps', self.handle)

#systembitmap('size', 40, 40)
		




#*************************************************
# Samples:

# save a bitmap to file
#path = r'D:\_scr_\py\scripts\name\api\gdi\test.bmp'
#bmp = bitmapfromfile(r'C:\WINDOWS\Strohmatte.bmp', 100, 100)
#bi = bmp.getBITMAPINFO()
#bytes = bmp.getbytes(bi)
#bmp.savetofile(bi, bytes, path)
