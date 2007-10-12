

from wnd.gdip.wintypes import COLORREF
#****************************************************
#
#	Color class
#
#*****************************************************
class Color(object):
	
	
	def __init__(self, alpha=0, red=0, green=0, blue=0):
		self.value = blue|(green << 8)|(red << 16)|(alpha << 24)
	
	def setValue(self, a, r, g, b):
		self.value = b|(g << 8)|(r << 16)|(a << 24)
	
	def GetA(self): return self.value >> 24 & 255
	def GetR(self): return self.value >> 16 & 255
	def GetG(self): return self.value >> 8 & 255
	def GetB(self): return self.value & 255
	
	def ToCOLORREF(self):
		return  (self.value >> 16 & 255)|				\
					((self.value >> 8 & 255)<<8)|		\
					((self.value & 255)<<16)		
	
	def FromCOLORREF(self, colorref):			
		self.value =(colorref >> 16 & 255)|			\
						((colorref >> 8 & 255)<< 8)|	\
						((colorref & 255) << 16)|			\
						(255 << 24)
	
	def GetColor(self): return self.value
	def SetColor(self, color): self.value= color
	
	def MakeColor(self, alpha=0, red=0, green=0, blue=0):
		return blue|(green << 8)|(red << 16)|(alpha << 24)

