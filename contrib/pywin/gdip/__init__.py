
from wnd.gdip.wintypes import _GdipInit
import atexit


from wnd.gdip.color import Color
from wnd.gdip.graphics import Graphics, GraphicsFromHwnd
from wnd.gdip.pen import Pen
#***************************************************
_init = _GdipInit()
atexit.register(_init.Close)


#**************************************************
class TrackPointers(object):
	def __init__(self):
		self.pointers = {}
	
	def Register(self, ptrType, ptr):
		pass
	
	def Unregister(self, ptrType, ptr):
		pass
	
	def GetOpen(self):
		pass
	
	def Close(self):
		pass

#****************************************************
UnitWorld = 0			# World coordinate (non-physical unit)
UnitDisplay = 1		# Variable -- for PageTransform only
UnitPixel = 2			# Each unit is one device pixel.
UnitPoint = 3			# Each unit is a printer's point, or 1/72 inch.
UnitInch = 4			# Each unit is 1 inch.
UnitDocument = 5	# Each unit is 1/300 inch.
UnitMillimeter = 6	# Each unit is 1 millimeter.

LineCapFlat             = 0,
LineCapSquare           = 1
LineCapRound            = 2
LineCapTriangle         = 3
LineCapNoAnchor         = 16		# corresponds to flat cap
LineCapSquareAnchor     = 17		# corresponds to square cap
LineCapRoundAnchor      = 18		# corresponds to round cap
LineCapDiamondAnchor    = 19	# corresponds to triangle cap
LineCapArrowAnchor      = 20		# no correspondence
LineCapCustom           = 255		# custom cap
LineCapAnchorMask       = 15		# mask to check for anchor or not.

DashStyleSolid = 0
DashStyleDash = 1
DashStyleDot = 2
DashStyleDashDot = 3
DashStyleDashDotDot = 4
DashStyleCustom = 5

DashCapFlat         = 0
DashCapRound     = 2
DashCapTriangle   = 3

LineJoinMiter = 0
LineJoinBevel = 1
LineJoinRound = 2
LineJoinMiterClipped = 3








