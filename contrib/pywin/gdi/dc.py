

"""
BUGS
	
	XP
		- SetBkMode fails sometimes -> see unittest Treeview in ownerdraw
			FIXED


"""



"""
All device context classes support the following beahviour:
Upon initializing, the device contexts' state is saved.
When calling 'close' the initial state of the device context
is restored so that its save to close (delete) all objects 
formerly selected into it, as long as you close the device context
BEFORE closing the object(s).

Curently the DC classes MUST be closed when done with them !!
Al other objects like pens, brushes (...) are freed automatically
when running out of scope. There is currently no way to enshure
that a dc is closed before all objects selected into it are released,
so you have to call 'close' when done with a DC to prevent
GDI leaks.
		

Background::
			
	All objects have to be freed when done with them.
	After selecting an object into a device context the dc will keep
	a reference of the object. So the object can not actually be destroyed	as long	as you don't reverse this action and remove the
	object from the dc. In C this is done like this:

		hNewObject = CreateWhatever()
		hOldObject = SelectObject(hDC, hNewObject)
		(..) # do whatever
		hNewObject = SelectObject(hDC, hOldObject)
		DeleteObject(hNewObject)
			
	SelectObject returns a handle of an object formerly selected
	into the dc, maybe a default object. By selecting this object
	back	into the dc, the handle to NewObject is returned and it
	is released from the dc.

	This is way easier achieved by using the SaveDC and
	RestoreDC	api's, especially for a larger number of objects:
			
		hNewObject = CreateWhatever()
		hSavedDC = SaveDC(hDC)
		SelectObject(hDC, hNewObject)
		(..) # do whatever
		RestoreDC(hDC, hSavedDC)
		DeleteObject(hNewObject)
			
	A call to RestoreDC will release all references to the handles
	of objects formerly selected into the dc, and its save to delete
	them afterwards. No messing with all the handles, as long as
	you restore the dc before deleting them.

				
Note: there is no support for saving multiple states of the 
dc's in these classes.

"""


from wnd.wintypes import *
from wnd.gdi.trackhandles import TrackHandler
from wnd.gdi.font import DisposableFont
from wnd.gdi.pen import DisposablePen
from wnd.gdi.brush import DisposableBrush
from wnd.gdi.bitmap import DisposableBitmap
from wnd.gdi.region import DisposableRegion
#**************************************************
#
#				Device context classes
#
#**************************************************
# NOT implemented
#
# gdi32.GetClipRgn
#	gdi32.SetMetaRgn

# TODO:
#
# ScrollDC

__all__= ("DCFromHandle", "DisposableDC", "DCFromDriver", "ClientDC", "WindowDC", "CompatibleDC")


EDGES = {				# DrawEdge edge parameters
			'raisedouter' : 1,
			'sunkenouter' : 2,
			'raisedinner' : 4,
			'sunkeninner' : 8,
			'raised' : 5,		# raisedouter | raisedinner
			'sunken' : 10,		# sunkenouter | sunkeninner
			'etched' : 6,		# sunkenouter | raisedinner
			'bump' : 9,			# raisedouter | sunkeninner
			}
BORDERS	={				# DrawEdge border parameters
			'left' : 1,
			'top' : 2,
			'topleft' : 3,
			'right' : 4,
			'topright' : 6,
			'bottom' : 8,
			'bottomleft' : 9,
			'bottomright' : 12,
			'rect' : 15,
			'diagonal' : 16,
			'diagonal_endtopleft' : 19,
			'diagonal_endtopright' : 22,
			'diagonal_endbottomleft' : 25,
			'diagonal_endbottomright' : 28,
			'middle' : 2048,
			'soft' : 4096,
			'adjust' : 8192,
			'flat' : 16384,
			'mono' : 32768,
			}
RGNMODES=[None,'and','or','xor','diff','copy']	# simple enum




class DCMethods(object):		
		
	def Save(self):
		hSavedDC = gdi32.SaveDC(self.handle)
		if not hSavedDC: raise RuntimeError("could not save dc")
		return hSavedDC
	
	def Restore(self, hSavedDC):
		if not gdi32.RestoreDC(self.handle, hSavedDC):
			raise RuntimeError("could not restore dc")
	
	def GetFont(self):
		hObj=gdi32.GetCurrentObject(self.handle, 6)	# OBJ_FONT
		if not hObj: raise RuntimeError("could not retrieve font")
		return DisposableFont(hObj) 
	
	def GetPen(self):
		hObj=gdi32.GetCurrentObject(self.handle, 1)	# OBJ_PEN
		if not hObj: raise RuntimeError("could not retrieve pen")
		return DisposablePen(hObj) 
		
	def GetBrush(self):
		hObj=gdi32.GetCurrentObject(self.handle, 2)	# OBJ_BRUSH
		if not hObj: raise RuntimeError("could not retrieve brush")
		return DisposableBrush(hObj) 
		
	def GetBitmap(self):
		hObj=gdi32.GetCurrentObject(self.handle, 7)	# OBJ_BITMAP
		if not hObj: raise RuntimeError("could not retrieve brush")
		return DisposableBitmap(hObj) 
			
# NOT YET IMPLEMENTED
#	def GetPal(self):
#		hObj=gdi32.GetCurrentObject(self.handle, 5)	# OBJ_PAL
#		if not hObj: raise "could not retrieve palette"
#		return DCPrivatePal(hObj) 
		
		
	#-----------------------------------------------------------------------------------------------------------------
	# paths
	
	# TODO
	#
	# GetPath
	# WidenPath

	def BeginPath(self):
		if not gdi32.BeginPath(self.handle):	raise RuntimeError("could not create path")
	
	def EndPath(self, dc):
		if not gdi32.EndPath(self.handle): raise RuntimeError("could not end path")
			
	def AbortPath(self, dc):
		if not gdi32.AbortPath(self.handle): raise RuntimeError("could not abort path")

	def ClosePathFigure(self):
			if not gdi32.CloseFigure(self.handle): raise RuntimeError("could not close figure")
		
	def FlattenPath(self):
			if not gdi32.FlattenPath(self.handle): raise "could not flatten path"
	
	def GetMiterLimit(self):
		limit=c_float()
		if not gdi32.GetMiterLimit(self.handle, byref(limit)): raise RuntimeError("could retrieve miter limt")
		return limit.value
	
	def PathToRegion(self):
		result= gdi32.PathToRegion(self.handle) 
		if not result:	raise RuntimeError("could convert path")
		return DisposableRegion(result)
		
	def FillPath(self, Brush):
		if Brush:
			hOldObject = gdi32.SelectObject(self.handle, Brush.handle)
			if not hOldObject: raise RuntimeError("invalid brush")
		result= gdi32.FillPath(self.handle)
		if Brush: gdi32.SelectObject(self.handle, hOldObject)	
		if not result: raise RuntimeError("could not fill path")
	
	def SetMiterLimit(self, Float):
		limit=c_float(Float)
		if not gdi32.SetMiterLimit(self.handle, byref(limit), None): raise RuntimeError("could set miter limt")
		
	def StrokeAndFillPath(self, Pen, Brush):
		if Pen:
			hOldPen = gdi32.SelectObject(self.handle, Pen.handle)
			if not hOldPen: raise RuntimeError("invalid pen")
		if Brush:
			hOldBrush = gdi32.SelectObject(self.handle, Brush.handle)
			if not hOldBrush: 
				if Pen: 
					gdi32.SelectObject(self.handle, hOldPen)
				raise RuntimeError("invalid brush")
		result= gdi32.StrokeAndFillPath(self.handle)
		if Pen: gdi32.SelectObject(self.handle, hOldPen)
		if Brush: gdi32.SelectObject(self.handle, hOldBrush)
		if not result: raise RuntimeError("could not stroke and fill path")
	
	def StrokePath(self, Pen):
		if Pen:
			hOldPen = gdi32.SelectObject(self.handle, Pen.handle)
			if not hOldPen: raise RuntimeError("invalid pen")
		result= gdi32.StrokePath(self.handle)
		if Pen: gdi32.SelectObject(self.handle, hOldPen)
		if not result: raise RuntimeError("could not stroke path")

	def SetClipPath(self, mode):
		try: mode=RGNMODES.index(mode)
		except: raise ValueError("invalid flag: %s" % mode)
		if not gdi32.SelectClipPath(self.handle, mode):
			raise RuntimeError("could not set clip path")
 
	
	#-------------------------------------------------------------------------------------------------------------------
	# clipping

	def SetClipRegion(self, Region):
		if not Region:
			if not gdi32.SelectClipRgn(self.handle, None):
				raise RuntimeError("could not set clip region")
		else:
			if not gdi32.SelectClipRgn(self.handle, Region.handle):
				raise RuntimeError("could not set clip region")

	def SetClipRegionEx(self, Region, mode):
		try: mode=RGNMODES.index(mode)
		except: raise ValueError("invalid flag: %s" % mode)
		if Region: hRegion= Region.handle
		else: hRegion=None
		if not gdi32.ExtSelectClipRgn(self.handle, hRegion, mode):
			raise RuntimeError("could not set clip region")

	def GetClipBox(self):
		rc= RECT()
		if not gdi32.GetClipBox(self.handle, byref(rc)): 
			raise RuntimeError("could not retrieve clip box")
		return rc

	def ExcludeClipRect(self, Rect):
		if not gdi32.ExcludeClipRect(self.handle, Rect.left, Rect.top, Rect.right, Rect.bottom):
			raise RuntimeError("could not exclude clip rect")
			
 	def IntersectClipRect(self, Rect):
		if not gdi32.IntersectClipRect(self.handle, Rect.left, Rect.top, Rect.right, Rect.bottom):
			raise RuntimeError("could not intersect clip rect")
	
	def OffsetClipRegion(self, x, y):
		if not gdi32.OffsetClipRegion(self.handle, x, y):
			raise RuntimeError("could not offset clip region")
  
	def PointInClipRegion(self, x, y):
		return bool(gdi32.PtVisible(self.handle, x, y))
 	
	def RectInClipRegion(self, Rect):
		return bool(gdi32.RectVisible(self.handle, byref(Rect)))
 
	#-------------------------------------------------------------------------------------------------------------------------
	def InvertRect(self, Rect):
		if not user32.InvertRect(self.handle, byref(Rect)):
			raise RuntimeError("could not invert rect")
	
	def GetPixel(self, x, y):
		colorref = gdi32.GetPixel(self.handle, x, y)
		if colorref==	4294967295:	# CLR_INVALID
			raise RuntimeError("could not retrieve pixel")
		return colorref
		
	def SetPixel(self, x, y, colorref):
		if not gdi32.SetPixelV(self.handle, x, y, colorref): raise RuntimeError("could not set pixel")
	
	def SelectObject(self, Object):
		hOldObject = gdi32.SelectObject(self.handle, Object.handle)
		if gdi32.GetObjectType(Object.handle)==8:	# OBJ_REGION
			if hOldObject ==4294967295:	# GDI_ERROR
				raise RuntimeError("invalid region")
		else: 
			if not hOldObject: raise RuntimeError("invalid object")
		class DummyObject(object):
			def __init__(self, handle):
				self.handle=handle
			def Close(self):
				if hasattr(self, 'handle'):
					if not gdi32.DeleteObject(self.handle):
						raise RuntimeError, "could not delete object"
					self.__delattr__('handle')
				else:
					raise RuntimeError("object is closed")
		return DummyObject(hOldObject )

	def GetCurrentObject(self, objecttype):
		try:
			hObject = gdi32.GetCurrentObject(self.handle, {'pen':1,'brush':2,'pal':5,'font':6,'bitmap':7}[objecttype])
		except: raise RuntimeError("invalid type: %s" % objecttype)
		if not hObject:	raise RuntimeError("'%s' % could not retrieve object: %s" % objecttype)
		return hObject
		
	def GetBkMode(self):
		bkmode = gdi32.GetBkMode(self.handle)
		if not bkmode:
			raise RuntimeError("could not retrieve background mode")
		if bkmode == 1:	return 'transparent'
		elif bkmode == 2: return 'opaque'

	def SetBkMode(self, mode):
		if mode=='opaque': 
			if not gdi32.SetBkMode(self.handle, 2):
				raise WinError("could not set background mode")
		elif mode=='transparent': 
			if not gdi32.SetBkMode(self.handle, 1):
				raise RuntimeError("could not set background mode")
		else: raise ValueError("invalid ackground mode: %s" % mode)
				
	def SetBkColor(self, colorref):
		prevcolor = gdi32.SetBkColor(self.handle, colorref)
		if prevcolor ==  4294967295:	 # CLR_INVALID
			raise RuntimeError("could not set background color") 
		return prevcolor

	def GetBkColor(self):
		CLR_INVALID         = 4294967295
		result = gdi32.GetBkColor(self.handle)
		if result == CLR_INVALID:
			raise RuntimeError("could not retrieve background color")
		return result

	def SetTextColor(self, colorref):
		"""Sets the text color."""
		colorref = gdi32.SetTextColor(self.handle, colorref)
		if colorref == 4294967295:	# CLR_INVALID 
			raise ValueError("invalid text color") 
		return colorref
	
	def GetTextColor(self):
		colorref = gdi32.GetTextColor(self.handle)
		if color == 4294967295:	# CLR_INVALID 
			raise RuntimeError("could not retrieve text color") 
		return colorref
	
	def GetPolyFillMode(self):
		mode = gdi32.GetPolyFillMode(self.handle)
		if not mode:	raise RuntimeError("could not retrieve poly fill mode")
		if mode == 1:	return 'alternate'
		elif mode == 2:	return 'winding'
		else: return 'unknown mode'

	def SetPolyFillMode(self, mode):
		if mode == 'alternate': mode = 1
		elif mode == 'winding': mode = 2
		else:	raise ValueError("invalid mode: %s" % mode)
		mode = gdi32.SetPolyFillMode(self.handle, mode)
		if not mode: raise RuntimeError("could set poly fill mode")
		if mode == 1: return 'alternate'
		elif mode == 2: return 'winding'
		else: return 'unknown mode'
		
	
	#-----------------------------------------------------------------------
	# others
	
	def DrawFocusRect(self, Rect):
		if not user32.DrawFocusRect(self.handle, byref(Rect)):
			raise RuntimeError("could not draw focus rect"	)
	
	def DrawEdge(self, Rect, edge, *border):
		try: edge = EDGES[edge]
		except: raise "invalid edge: %s" % edge
		_border = 0
		for i in border:
			try: _border |= BORDERS[i]
			except: raise ValueError("invalid border: %s" % i)
		if not user32.DrawEdge(self.handle, byref(Rect), edge, _border):
			raise RuntimeError("could not draw edge")
		

	def DrawBorder(self, Rect, *flags):
		style=0
		for i in flags:
			if i=='border': style |= 1
			elif i=='flat': style |= 2
			elif i=='clientedge': style |= 4
			elif i=='pushed': style |= 8
			elif i=='normal': pass
			else: raise ValueError("invalid flag: %s" % i)
		rcIn=Rect.ToTuple()
		if style==0:		# normal border raised
			# EDGE_RAISED, BF_SOFT
			if not user32.DrawEdge(self.handle, byref(Rect), 5, 4096|15):
				raise RuntimeError("could not draw border")
		elif style==8:	# normal border sunken
			# EDGE_SUNKEN, BF_SOFT
			if not user32.DrawEdge(self.handle, byref(Rect), 10, 4096|15):
				raise RuntimeError("could not draw border")
		elif style==1:	# 'border' border raised	
			# EDGE_RAISEDOUTER, BF_MONO
			if not user32.DrawEdge(self.handle, byref(Rect), 1, 32768|15):
				raise RuntimeError("could not draw border")	
			Rect.Inflate(-2, -2)
			# EDGE_RAISED
			if not user32.DrawEdge(self.handle, byref(Rect), 5, 0|15):
				raise RuntimeError("could not draw border")
		elif style==9:		# 'border' border sunken	
			# EDGE_RAISEDOUTER, BF_MONO
			if not user32.DrawEdge(self.handle, byref(Rect), 1, 32768|15):
				raise RuntimeError("could not draw border")	
			Rect.Inflate(-2, -2)
			# EDGE_RAISED
			if not user32.DrawEdge(self.handle, byref(Rect), 5, 0|15):
				raise RuntimeError("could not draw border")		
		elif style==2 or style==10:	 # flat border
			# # EDGE_BUMP, BF_MONO
			if not user32.DrawEdge(self.handle, byref(Rect), 9, 32768|15):
				raise RuntimeError("could not draw border")	
		elif style==3 or style==11:	 # flat + 'border' border
			# EDGE_RAISEDOUTER, BF_MONO
			if not user32.DrawEdge(self.handle, byref(Rect), 1, 32768|15):
				raise RuntimeError("could not draw border")	
			Rect.Inflate(-1, -1)
			# # EDGE_BUMP, BF_MONO
			if not user32.DrawEdge(self.handle, byref(Rect), 9, 32768|15):
				raise RuntimeError("could not draw border")	
		else:
			# ...clientedge borders
			# EDGE_SUNKEN, 0
			if not user32.DrawEdge(self.handle, byref(Rect), 10, 0|15):
				raise RuntimeError("could not draw border")	
			Rect.Inflate(-2, -2)
			if style==4 or style==5:	 # clientedge (border) raised
				# EDGE_RAISED, BF_SOFT
				if not user32.DrawEdge(self.handle, byref(Rect), 5, 4096|15):
					raise RuntimeError("could not draw border")	
			elif style==12 or style==13:	 # clientedge (border) sunken
				# EDGE_SUNKEN, BF_SOFT
				if not user32.DrawEdge(self.handle, byref(Rect), 10, 4096|15):
					raise RuntimeError("could not draw border")	
			else: 	# clientedge + flat + (border)	 (6, 7, 14, 15)
				# EDGE_BUMP, BF_MONO
				if not user32.DrawEdge(self.handle, byref(Rect), 9, 32768|15):
					raise RuntimeError("could not draw border")	
		Rect.Inflate(-2, -2)
		return (Rect.left-rcIn[0], Rect.top-rcIn[1])
	
		
	
#***********************************************************************************************
class DCFromHandle(DCMethods):
	
	def __init__(self, handle=0):
		self.handle = handle
		
	def Release(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else: raise RuntimeError("dc is closed")
				
	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else: raise RuntimeError("dc is closed")
							

#***********************************************************************************************

# TODO 
# not public currently
# Close would need more information on how to close it
class DisposableDC(DCMethods):
	
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('dcs', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('dcs', self.handle)
			self.__delattr__('handle')
		else: raise RuntimeError("dc is closed")
				
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('dcs', self.handle)
			self.__delattr__('handle')
		else: raise RuntimeError("dc is closed")


#*****************************************************************

class CompatibleDC(DisposableDC):
	def __init__(self, DC=None):
		if DC: handle = gdi32.CreateCompatibleDC(DC.handle)
		else: handle = gdi32.CreateCompatibleDC(0)
		if not handle: raise RuntimeError("could not create compatible dc")
		DisposableDC.__init__(self, handle)
		
	def Close(self):
		if self.handle:
			TrackHandler.Unregister('dcs', self.handle)
			result= gdi32.DeleteDC(self.handle)
			self.__delattr__('handle')
			if not result:	raise RuntimeError("could not delete dc")
				
#*************************************************
class DCFromDriver(DisposableDC):
	def __init__(self, driver, devicename=0, initdata=0):
		self.handle = gdi32.CreateDCA(driver, devicename, 0, initdata)
		if not self.handle: raise RuntimeError("could not create dc")
		DisposableDC.__init__(self, handle)
		
	def Close(self):
		if self.handle:
			TrackHandler.Unregister('dcs', self.handle)
			result= gdi32.DeleteDC(self.handle)
			self.__delattr__('handle')
			if not result:	raise RuntimeError("could not delete dc")
				
	
#**************************************************
#
#				window DCs
#
#**************************************************
class ClientDC(DisposableDC):
		
	def __init__(self, hwnd):
		handle = user32.GetDC(hwnd)
		if not handle: raise RuntimeError("could not retrieve client dc")
		self.Hwnd=hwnd
		DisposableDC.__init__(self, handle)
				
	def Close(self):
		if self.handle:
			TrackHandler.Unregister('dcs', self.handle)
			result= user32.ReleaseDC(self.Hwnd, self.handle)
			self.__delattr__('handle')
			if not result:	raise RuntimeError("could not release dc")			

#**************************************************
class WindowDC(DisposableDC):
	
	def __init__(self, hwnd):
		self.handle = user32.GetWindowDC(hwnd)
		if not self.handle: raise RuntimeError("could not retrieve window dc")
		self.hwnd = hwnd
		DisposableDC.__init__(self, handle)

	def Close(self):
		if self.handle:
			TrackHandler.Unregister('dcs', self.handle)
			result= user32.ReleaseDC(self.hwnd, self.handle)
			self.__delattr__('handle')
			if not result:	raise RuntimeError("could not release dc")
			

	
			
