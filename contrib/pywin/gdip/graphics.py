

from wnd.gdip.wintypes import *
#***************************************************
#
#		Graphics Classes
#
#****************************************************
class Graphics(object):
	def __init__(self, hDc):
		self.ptr = pointer(c_ulong())
		result = gdip.GdipCreateFromHDC(hDc, byref(self.ptr))
		if result: raise GdiPlusError(result)
		
	def DrawLineL(self, Pen, x1, y1, x2, y2):
		result=gdip.GdipDrawLineI(self.ptr, Pen.ptr, x1, y1, x2, y2)
		if result: raise GdiPlusError(result)
	
	def DrawLine(self, Pen, x1, y1, x2, y2):
		x1,y1,x2,y2 = c_float(x1),c_float(y1),c_float(x2),c_float(y2)
		result=gdip.GdipDrawLine(self.ptr, Pen.ptr, x1, y1, x2, y2)
		if result: raise GdiPlusError(result)
	
	def FillRectL(self, Brush, x, y, w, h):
		result=gdip.GdipFillRectangleI(self.ptr, Brush.ptr, x, y, w, h)
		if result: raise GdiPlusError(result)
	
	def FillRect(self, Brush, x, y, w, h):
		x,y,w,h = c_float(x),c_float(y),c_float(w),c_float(h)
		result=gdip.GdipFillRectangle(self.ptr, Brush.ptr, x, y, w, h)
		if result: raise GdiPlusError(result)
	
	def DrawRectI(self, Pen, x, y, w, h):
		result=gdip.GdipDrawRectangleI(self.ptr, Pen.ptr, x, y, w, h)
		if result: raise GdiPlusError(result)
	
	
	def Save(self):
		state = c_ulong()
		result=gdip.GdipSaveGraphics(self.ptr, byref(state))
		if result: raise GdiPlusError(result)
		return state.value
    
	def Restore(self, state):
		""""""
		result=gdip.GdipRestoreGraphics(self.ptr, state)
		if result: raise GdiPlusError(result)
	
	
	def Close(self):
		result=gdip.GdipDeleteGraphics(self.ptr)
		if result: raise GdiPlusError(result)
		self.ptr = None

#****************************************************
#****************************************************

class GraphicsFromHwnd(Graphics):
	def __init__(self, hwnd):
		self.ptr = pointer(c_ulong())
		result = gdip.GdipCreateFromHWND(hwnd, byref(self.ptr))
		if result: raise GdiPlusError(result)
