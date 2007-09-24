

from wnd.gdip.wintypes import *
from wnd.gdip.brush import BrushFromPointer

#***************************************************
#
#		Pen Classes
#
#****************************************************
class Pen(object):
	def __init__(self, color, width, unit=2):
		self.ptr = pointer(c_ulong())
		width = c_float(width)
		if gdip.GdipCreatePen1(color, width, unit, byref(self.ptr)):
			raise GdiPlusError(result)
	
	def GetWidth(self):
		width = c_float()
		if gdip.GdipGetPenWidth(self.ptr, byref(width)):
			raise GdiPlusError(result)
		return width.value
	
	def SetWidth(self, width):
		if gdip.GdipSetPenWidth(self.ptr, c_float(width)):
			raise GdiPlusError(result)
		
	def GetColor(self):
		clr = c_ulong()
		if gdip.GdipGetPenColor(self.ptr, byref(clr)):
			raise GdiPlusError(result)
		return clr.value
	
	def SetColor(self, color):
		if gdip.GdipSetPenColor(self.ptr, color):
			raise GdiPlusError(result)
		
	def GetUnit(self):
		unit = c_ushort()
		if gdip.GdipGetPenUnit(self.ptr, byref(unit)):
			raise GdiPlusError(result)
		return unit.value
	
	def SetUnit(self, unit):
		if gdip.GdipSetPenUnit(self.ptr, unit):
			raise GdiPlusError(result)
	
	def SetBrush(self, Brush):
		if gdip.GdipSetPenBrushFill(self.ptr, Brush.ptr):
			raise GdiPlusError(result)
		
	def getBrush(self):
		ptrBrush = pointer(c_ulong())
		if gdip.GdipGetPenBrushFill(self.ptr, byref(ptrBrush)):
			raise GdiPlusError(result)
		return BrushFromPointer(ptrBrush)
		
	def SetCaps(self, start, end, dash):
		if gdip.GdipSetPenLineCap197819(self.ptr, start, end, dash):
			raise GdiPlusError(result)
	
	def GetEndCap(self):
		cap = c_ushort()
		if gdip.GdipGetPenEndCap(self.ptr, byref(cap)):
			raise GdiPlusError(result)
		return cap.value
	
	def SetEndCap(self, cap):
		if gdip.GdipSetPenEndCap(self.ptr, cap):
			raise GdiPlusError(result)
	
	def GetStartCap(self):
		cap = c_ushort()
		if gdip.GdipGetPenStartCap(self.ptr, byref(cap)):
			raise GdiPlusError(result)
		return cap.value
	
	def SetStartCap(self, cap):
		if gdip.GdipSetPenStartCap(self.ptr, cap):
			raise GdiPlusError(result)
		
	def GetDashCap(self):
		cap = c_ushort()
		if gdip.GdipGetPenStartCap(self.ptr, byref(cap)):
			raise GdiPlusError(result)
		return cap.value
	
	def SetDashCap(self, dashcap):
		if gdip.GdipSetPenDashCap197819(self.ptr, dashcap):
			raise GdiPlusError(result)
	
	def GetDashStyle(self):
		dash = c_ushort()
		if gdip.GdipGetPenDashStyle(self.ptr, byref(dash)):
			raise GdiPlusError(result)
		return dash.value
	
	def SetDashStyle(self, dash):
		if gdip.GdipSetPenDashStyle(self.ptr, dash):
			raise GdiPlusError(result)
		
	def GetDashPattern(self):
		n = c_uint()
		if gdip.GdipGetPenDashCount(self.ptr, byref(n)):
			raise GdiPlusError(result)
		n = n.value
		arrDash = (c_float*n)()
		if gdip.GdipGetPenDashArray(self.ptr, byref(arrDash), n):
			raise GdiPlusError(result)
		return list(arrDash)
	
	def SetDashPattern(self, *dashes):
		n = len(dashes)
		arrDash=(c_float*n)(*dashes)
		if gdip.GdipSetPenDashArray(self.ptr, byref(arrDash), n):
			raise GdiPlusError(result)
   
	
	def getLineJoin(self):
		LineJoin = c_ushort()
		if gdip.GdipGetPenLineJoin(self.ptr, byref(LineJoin)):
			raise GdiPlusError(result)
		return LineJoin.value
	
	def setLineJoin(self, LineJoin):
		if gdip.GdipSetPenLineJoin(self.ptr, LineJoin):
			raise GdiPlusError(result)
	
	
	def GetCompoundPattern(self):
		n = c_uint()
		result=gdip.GdipGetPenCompoundCount(self.ptr, byref(n))
		if result: raise GdiPlusError(result)
		n = n.value
		arrComp = (c_float*n)()
		result=gdip.GdipGetPenCompoundArray(self.ptr, byref(arrComp), n)
		if result: raise GdiPlusError(result)
		return list(arrComp)
	
	def SetCompoundPattern(self, *compounds):
		n = len(compounds)
		arrComp=(c_float*n)(*compounds)
		result=gdip.GdipSetPenCompoundArray(self.ptr, byref(arrComp), n)
		if result: raise GdiPlusError(result)
	
	
	
	def Close(self):
		result = gdip.GdipDeletePen(self.ptr)
		if result: raise GdiPlusError(result)
		self.ptr = None
	