
from wnd.wintypes import RECT, POINT
from ctypes import windll , byref
from wnd.gdi.trackhandles import TrackHandler

gdi32= windll.gdi32
#**************************************************
#
#			Region classes
#
#**************************************************
__all__= ("RegionFromHandle", "DisposableRegion", "RectRegion", "RoundRectRegion", "EllipticRegion", "PolygonRegion")


COMBINE_FLAGS=(None,'and','or','xor','diff','copy')


class RegionFromHandle(object):
	def __init__(self, handle):
		self.handle=handle
		
	def Combine(self, Region, flag):
		try: flag = COMBINE_FLAGS.index(flag)
		except: raise ValueError("invalid flag: %s" % flag)
		destRegion = self.__class__(gdi32.CreateRectRgn(0, 0, 0, 0))
		if not gdi32.CombineRgn(destRegion.handle, self.handle, Region.handle, flag):
			raise RuntimeError("could not combine regions")
		return destRegion
	
	def GetRect(self):
		rc = RECT()
		if not gdi32.GetRgnBox(self.handle, byref(rc)):
			raise RuntimeError("could not retrieve recangle")
		return rc
	
	def IsEqual(self, Region):
		return bool(gdi32.EqualRgn(self.handle, Region.handle))
		
	def Offset(self, x, y):
		if not gdi32.OffsetRgn(self.handle, x, y):
			raise RuntimeError("could not offset region")

	def PointInRegion(self, Point):
		return bool(gdi32.PtInRgn(self.handle, Point.x, Point.y))
	
	def RectInRegion(self, Rect):
		return bool(gdi32.RectInRgn(self.handle, byref(Rect)))
	
	def Fill(self, dc, Brush):
		if not gdi32.FillRgn(dc.handle, self.handle, Brush.handle):
			raise RuntimeError("could not fill region")

	def Paint(self, dc, Brush):
		hOldObject = gdi32.SelectObject(dc.handle, Brush.handle)
		if not hOldObject: raise RuntimeError("invalid brush")
		result= gdi32.PaintRgn(dc.handle, self.handle)
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: raise RuntimeError("could not paint region")
		
	def Invert(self, dc):
		if not gdi32.InvertRgn(dc.handle, self.handle):
			raise RuntimeError("could not invert region")
		
	def Frame(self, dc, Brush, framewidth, frameheight):
		if not gdi32.FrameRgn(dc.handle, self.handle, Brush.handle, framewidth, frameheight):
			raise RuntimeError("could not frame region")
	
	def Release(self):
		self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("region is closed")
		
	
#************************************************
class DisposableRegion(RegionFromHandle):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('regions', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('regions', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("region is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('regions', self.handle)
			result= gdi32.DeleteObject(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete region")
			
		else:
			raise RuntimeError("region is closed")

#************************************************
class RectRegion(DisposableRegion):
	
	def __init__(self, Rect):
		handle = gdi32.CreateRectRgn(Rect.left, Rect.top, Rect.right, Rect.bottom)
		if not handle: raise RuntimeError("could not create region")
		DisposableRegion.__init__(self, handle)
		
#************************************************
class RoundRectRegion(DisposableRegion):
		
	def __init__(self, Rect, ellipseheight, ellipsewidth):
		handle = gdi32.CreateRoudRectRgn(Rect.left, Rect.top, Rect.right, Rect.bottom, ellipseheight, ellipsewidth)
		if not handle: raise RuntimeError("could not create region")
		self.ellipseheight = ellipseheight
		self.ellipsewidth = ellipsewidth
		DisposableRegion.__init__(self, handle)
		
	def Combine(self, Region, flag):
		try: flag = COMBINE_FLAGS.index(flag)
		except: raise ValueError("invalid flag: %s" % flag)
		destRegion = self.__class__(RECT(), self.ellipseheight,  self.ellipsewidth)
		if not gdi32.CombineRgn(destRegion.handle, self.handle, Region.handle, flag):
			raise RuntimeError("could not combine regions")
		return destRegion

#************************************************
class EllipticRegion(DisposableRegion):
		
	def __init__(self, rect):
		handle = gdi32.CreateEllipticRgn(rect.left, rect.top, rect.right, rect.bottom)
		if not handle: raise RuntimeError("could not create region")
		#self.ellipseheight = ellipseheight
		#self.ellipsewidth = ellipsewidth
		DisposableRegion.__init__(self, handle)
		
	def Combine(self, Region, flag):
		try: flag = COMBINE_FLAGS.index(flag)
		except: raise ValueError("invalid flag: %s" % flag)
		destRegion = self.__class__(RECT())
		if not gdi32.CombineRgn(destRegion.handle, self.handle, Region.handle, flag):
			raise RuntimeError("could not combine regions")
		return destRegion

#************************************************
class PolygonRegion(DisposableRegion):
	
	def __init__(self, points, mode='alternate'):
		if mode == 'alternate':mode = 1
		elif mode == 'winding':mode = 2
		else: raise ValueError("invalid mode: %s" % mode)
		if isinstance(points, (tuple, list)):
			points= (POINT*len(points))(*points)
		handle=gdi32.CreatePolygonRgn(byref(points), len(points), mode)
		if not handle: raise RuntimeError("could not create region")
		DisposableRegion.__init__(self, handle)
		
	def Combine(self, Region, flag):
		try: flag = COMBINE_FLAGS.index(flag)
		except: raise ValueError("invalid flag: %s" % flag)
		destRegion = self.__class__((POINT*1)(), self.GetPolyFillMode())
		if not gdi32.CombineRgn(destRegion.handle, self.handle, Region.handle, flag):
			raise RuntimeError("could not combine regions")
		return destRegion
