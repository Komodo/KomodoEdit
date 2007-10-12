
from wnd.gdi.icons import SystemIcon 
from wnd.gdi.wintypes import *
from ctypes import *
from wnd.gdi import bitmaps

gdi32 = windll.gdi32
user32 = windll.user32
msvcrt = cdll.msvcrt
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def getinfo(hBitmap):
	bmp = BITMAP()
	if not gdi32.GetObjectA(hBitmap, sizeof(BITMAP), byref(bmp)):
		raise 'could not retrieve bitmap info'
	
	# still having problems with saving 16 bit + icons...
	if bmp.bmBitsPixel > 8:bmp.bmBitsPixel=8
	
	
	# get bitcount 
	nBits = bmp.bmPlanes * bmp.bmBitsPixel
	if nBits == 1: 	nBits = 1 
	elif nBits <= 4: nBits = 4; 
	elif nBits <= 8: nBits = 8; 
	elif nBits <= 16: nBits = 16 
	elif nBits <= 24: nBits = 24 
	else: nBits = 32 

	# setup BITMAPINFO for the bitmap
	if nBits == 24:	# no RGBQUAD array for 24 bit bitmaps
		BITMAPINFO = setupBITMAPINFO(nColors=0)
	else:
		BITMAPINFO = setupBITMAPINFO(nColors=(1<<nBits))
	bi = BITMAPINFO()
	bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
	bi.bmiHeader.biWidth = bmp.bmWidth 
	bi.bmiHeader.biHeight = bmp.bmHeight 
	bi.bmiHeader.biPlanes = bmp.bmPlanes 
	bi.bmiHeader.biBitCount = bmp.bmBitsPixel
	if nBits < 24: 
		bi.bmiHeader.biClrUsed = (1<<nBits)

	BI_RGB = 0
	bi.bmiHeader.biCompression = BI_RGB

	bi.bmiHeader.biSizeImage = ((bi.bmiHeader.biWidth * nBits +31) & ~31) /8 * bi.bmiHeader.biHeight
	
	bi.bmiHeader.biClrImportant = 0
	return bi


def getbytes(hBitmap, bitmapinfo, hDc=None):
	data = (c_ubyte*bitmapinfo.bmiHeader.biSizeImage)()
	if hDc == None:
		hDc = user32.GetDC(0)
	DIB_RGB_COLORS      = 0
	result = gdi32.GetDIBits(hDc, hBitmap, 0,
										bitmapinfo.bmiHeader.biHeight,
										byref(data), byref(bitmapinfo),
										DIB_RGB_COLORS)
	if hDc == None:
		user32.ReleaseDC(0, hDc)
	if not result:
		raise 'could not retrieve bitmap bytes'
	return data



def save_icon(biColor, bytesColor, biMask, bytesMask, path):
	
	ICONIMAGE = setupICONIMAGE(nColors=len(biColor.bmiColors),
								nXOR=sizeof(bytesColor),
								nAND=sizeof(bytesMask))
	
	# setup ICONIMAGE
	ii = ICONIMAGE()
	ii.icHeader = biColor.bmiHeader
	ii.icHeader.biHeight *= 2		##height mask + color
	ii.icHeader.biSizeImage += biMask.bmiHeader.biSizeImage
	ii.icHeader.biCompression = 0		# zero
	ii.icHeader.biXPelsPerMeter = 0		# zero
	ii.icHeader.biYPelsPerMeter = 0		# zero
	#ii.icHeader.biClrUsed = 0
	ii.icHeader.biClrImportant = 0		# zero
	ii.icColors = biColor.bmiColors
	ii.icXOR = bytesColor
	ii.icAND = bytesMask
	
	#print ii.icXOR
	#print ii.icAND
	

	
	# setup ICONDIERENTRY
	
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
	ide.dwImageOffset = sizeof(ICONDIR) + sizeof(ide)	##
		
	# setup ICONDIR
	idir = ICONDIR()
	idir.idType = 1
	idir.idCount = 1
		
	
	fp = msvcrt.fopen(path, "wb")
	if not fp:
		raise 'could not open file'
	# could do some error checking here
	msvcrt.fwrite(byref(idir), sizeof(ICONDIR), 1, fp)
	#msvcrt.fwrite('XXX', 3, 1, fp)
	
	a=msvcrt.fwrite(byref(ide), sizeof(ICONDIRENTRY), 1, fp)
	
	#msvcrt.fwrite('XXX', 3, 1, fp)
	
	msvcrt.fwrite(byref(ii), sizeof(ICONIMAGE), 1, fp)
	msvcrt.fclose(fp)
	


	
	#ii.icHeader = biColor.bmiHeader
	
	
	#ICONDIR = setupICONDIR(nEntries=1)
	#idir = ICONDIR()


	pass




i = SystemIcon('hand')

path = r'D:\_scr_\py\Scr\wnd\gdi\test_icon.ico'

ii = ICONINFO()
a=user32.GetIconInfo(i.handle, byref(ii))
bmpMask = ii.hbmMask
bmpColor = ii.hbmColor


try:
	biColor = getinfo(bmpColor)
	bytesColor = getbytes(bmpColor, biColor)
	
	biMask = getinfo(bmpMask)
	bytesMask = getbytes(bmpMask, biMask)
	
	
	save_icon(biColor, bytesColor, biMask, bytesMask, path)

finally:
	gdi32.DeleteObject(ii.hbmMask)
	gdi32.DeleteObject(ii.hbmColor)
	
	


  


