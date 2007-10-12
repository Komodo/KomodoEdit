
from wnd.wintypes import POINT
from wnd.gdi.trackhandles import TrackHandler
from ctypes import windll

gdi32= windll.gdi32

#************************************************
#
#				Pen classes
#
#************************************************
__all__= ("PenFromHandle", "DisposablePen", "Pen")

PEN_STYLES=('solid','dash','dot','dashdot','dashdotdot','null','insideframe')



class PenFromHandle(object):
	def __init__(self, handle):
		self.handle= handle

	def SetPenPos(self, dc, x, y):
		if not gdi32.MoveToEx(dc.handle, x, y, 0):
			raise RuntimeError("could not set position")
	
	def LineTo(self, dc, x, y):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid pen")
		result= gdi32.LineTo(dc.handle, x, y) 
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: raise RuntimeError("could not draw line")
		
	def PolyLine(self, dc, pointArray):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid pen")
		result= gdi32.Polyline(dc.handle, byref(pointArray), len(pointArray))
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: raise RuntimeError("could not draw poly line")
			
	def PolyLineP(self, dc, *Point):
		pointArray=(POINT*len(Point))(*Point)
		self.PolyLine(dc, pointArray)
		return pointArray
		
	def PolyLineI(self, dc, *points):
		pointArray=(POINT*len(points))(*points)
		self.PolyLine(dc, pointArray)
		return pointArray
		
	def PolyLineTo(self, dc, pointArray):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid pen")
		result= gdi32.PolylineTo(dc.handle, byref(pointArray), len(pointArray))
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result:	raise RuntimeError("could not draw poly line")
		
	def PolyLineToP(self, dc, *Point):
		pointArray=(POINT*len(Point))(*Point)
		self.PolyLineTo(dc, pointArray)
		return pointArray

	def PolyLineToL(self, dc, *points):
		pointArray=(POINT*len(points))(*points)
		self.PolyLineTo(dc, pointArray)
		return pointArray
		
	def Arc(self, dc, Rect, toX, toY, fromX, fromY):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid pen")
		result= gdi32.Arc(dc.handle, Rect.left, Rect.top, Rect.right, Rect.bottom, toX, toY, fromX, fromY)
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result:	raise RuntimeError("could not draw arc")
		
		
	def Release(self):
		self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("pen is closed")


#*************************************************************
class DisposablePen(PenFromHandle):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('pens', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('pens', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("pen is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('pen', self.handle)
			result= gdi32.DeleteObject(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete pen")
			
		else:
			raise RuntimeError("pen is closed")
	

#*********************************************************************
class Pen(DisposablePen):
	"""Pen class."""
	def __init__(self, width, colorref, style='solid'):
		try: PEN_STYLES.index(style)
		except: raise ValueError("invalid style: %s" % style)
		handle = gdi32.CreatePen(style, width, colorref)
		if not handle: raise RuntimeError("could not create pen")
		DisposablePen.__init__(self, handle)
		
#***********************************************************************************************

	# NT only
	#def SetArcDirection(self, dc, direction):
	#	if direction=='clockwise': direction = 2	# AD_CLOCKWISE
	#	if direction=='counterclockwise': direction = 1	# AD_CLOCKWISE
	#	result= gdi32.SetArcDirection(dc.handle, direction)
	#	if result: return result
	#	raise "could not retrieve arc direction"
	#	if result==2: return 'clockwise'	
	#	if result==1: return 'counterclockwise'

	#def GetArcDirection(self, dc):
	#	result= gdi32.GetArcDirection(dc.handle)
	#	if result==2: return 'clockwise'	
	#	if result==1: return 'counterclockwise'

	#def ArcTo(self, dc, Rect, toX, toY, fromX, fromY):
	#	hOldObject = gdi32.SelectObject(dc.handle, self.handle)
	#	if hOldObject == 0xFFFFFFFFL: # GDI_ERROR
	#		raise "could not select object"
	#	if not gdi32.ArcTo(dc.handle, Rect.left, Rect.top, Rect.right, Rect.bottom, toX, toY, fromX, fromY):
	#		raise "could not draw arc"
	#	gdi32.SelectObject(dc.handle, hOldObject)	