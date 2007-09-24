

from wnd.gdi.trackhandles import TrackHandler
from ctypes import windll, c_ubyte, byref, sizeof

user32= windll.user32
gdi32= windll.gdi32
#*************************************************
#
#						Brush classes
#
#**************************************************
__all__= ("BrushFromHandle", "DisposableBrush", "SolidBrush", "SysColorBrush", "PatternBrush", "StockBrush")	



BLTMODES = {
			'patcopy':15728673,
			'paint':16452105,
			'patinvert':5898313,
			'destinvert' : 5570569,
			'blackness':66,
			'whiteness':16711778}

STOCK_BRUSHES= {
	'whitebrush': 0,
	'ltgraybrush':1,
	'graybrush':2,
	'dkgraybrush':3,
	'blackbrush':4,
	'nullbrush':5}


#******************************************************************************************
class BrushFromHandle(object):
	def __init__(self, handle):
		self.handle= handle

	def FillRegion(self, dc, Region):
		if not gdi32.FillRgn(dc.handle, Region.handle, self.handle):
			raise RuntimeError("could not fill region")

	def FrameRect(self, dc, Rect):
		if not user32.FrameRect(dc.handle, byref(Rect), self.handle):
			raise RuntimeError("could not frame rect")
	
	def FillRect(self, dc, Rect):
		if not user32.FillRect(dc.handle, byref(Rect), self.handle):
			raise RuntimeError("could not fill rect")
	
	def PatBlt(self, dc, Rect, mode):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid brush")
		try: mode=BLTMODES[mode]
		except: raise ValueError("invalid mode: %s" % mode)
		result= gdi32.PatBlt(dc.handle, Rect.left, Rect.top, Rect.right-Rect.left, Rect.bottom-Rect.top, mode)
		gdi32.SelectObject(dc.handle, hOldObject)	
		if not result:	raise RuntimeError("Could not pat blt")

	def Release(self):
		self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("brush is closed")

#*********************************************************************
class DisposableBrush(BrushFromHandle):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('brushes', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('brushes', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("brush is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('brushes', self.handle)
			result= gdi32.DeleteObject(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete brush")
		else:
			raise RuntimeError("brush is closed")
	
#*****************************************************

class SolidBrush(DisposableBrush):
		
	def __init__(self, colorref):
		handle = gdi32.CreateSolidBrush(colorref)
		if not handle: raise RuntimeError, "could not create brush"
		DisposableBrush.__init__(self, handle)
	

#**********************************************
class SysColorBrush(BrushFromHandle):
		
	def __init__(self, colorname):
		from wnd.gdi import SYSTEM_COLORS
		
		try: color = SYSTEM_COLORS[colorname]
		except: raise ValueError("invalid color: %s" % colorname)
		handle = user32.GetSysColorBrush(color)
		if not handle: raise RuntimeError("could not create sys color brush")
		BrushFromHandle.__init__(self, handle)
		
	
#**********************************************
class StockBrush(BrushFromHandle):
		
	def __init__(self, brush):
				
		try: brush = STOCK_BRUSHES[brush]
		except: raise ValueError("invalid brush: %s" % brush)
		handle = gdi32.GetStockObject(brush)
		if not handle: raise RuntimeError("could not retreieve stock brush")
		BrushFromHandle.__init__(self, handle)
	

#***********************************************

class PatternBrush(DisposableBrush):
	def __init__(self, colors):
		if isinstance(colors, (list, tuple)):
			if len(colors) > 64: raise ValueError("too many colors: (64) max")
			colors=(c_ubyte*64)(*colors)
		elif isinstance(colors, Array):
			if sizeof(colors) * 2 > 64: ValueError("too many colors: (64) max")
		hBmp=gdi32.CreateBitmap(8, 8, 1, 1, byref(colors))
		if not hBmp: raise RuntimeError("colud not create bitmap")
		handle =gdi32.CreatePatternBrush(hBmp)
		gdi32.DeleteObject(hBmp)
		if not handle: raise RuntimeError("could not create sys color brush")
		DisposableBrush.__init__(self, handle)
		