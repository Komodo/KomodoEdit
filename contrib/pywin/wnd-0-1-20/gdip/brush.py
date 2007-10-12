
from wnd.gdip.wintypes import *
#***************************************************
#
#		Brush Classes
#
#***************************************************
class BrushFromPointer(object):
	
	def __init__(self, ptr):
		self.ptr = ptr		# pointer to the C instance
	
	def SetColor(self, Color):
		result=gdip.GdipSetSolidFillColor(self.ptr, Color.value)
		if result: raise GdiPlusError(result)
	
	def GetColor(self):
		color = c_ulong()
		result=gdip.GdipGetSolidFillColor(self.ptr, byref(color))
		if result: raise GdiPlusError(result)
		return color.value
	
	def Close(self):
		result=gdip.GdipDeleteBrush(self.ptr)
		if result: raise GdiPlusError(result)
		self.ptr = None

#*************************************************************************************
#*************************************************************************************
class SolidBrush(BrushFromPointer):
	def __init__(self, Color):
		self.ptr = pointer(c_ulong())
		result=gdip.GdipCreateSolidFill(Color.value, byref(self.ptr))
		if result: raise GdiPlusError(result)

