

from wnd.wintypes import *
from wnd.gdi.trackhandles import TrackHandler
from wnd.gdi.region import RectRegion

#***************************************************
__all__= ("FontFromHandle", "DisposableFont", "FontFromLogfont", "Font", "EnumFonts")

class LOGFONT(Structure):  
	"""Logfont struct."""
	_fields_=[("lfHeight", LONG), 
					("lfWidth", LONG), 
					("lfEscapement", LONG), 
					("lfOrientation", LONG), 
					("lfWeight", LONG), 
					("lfItalic", BYTE), 
					("lfUnderline", BYTE),
					("lfStrikeOut", BYTE), 
					("lfCharSet", BYTE), 
					("lfOutPrecission", BYTE), 
					("lfClipPrecision", BYTE), 
					("lfQuality", BYTE),
					("lfPitchAndFamily", BYTE), 
					("lfFaceName", CHAR *32)]

class NEWTEXTMETRIC(Structure):
	_fields_ = [("tmHeight", LONG),
					("tmAscent", LONG),
					("tmDescent",  LONG),
					("tmInternalLeading",  LONG),
					("tmExternalLeading", LONG), 
					("tmAveCharWidth", LONG), 
					("tmMaxCharWidth", LONG),
					("tmWeight", LONG),
					("tmOverhang",  LONG),
					("tmDigitizedAspectX", LONG),
					("tmDigitizedAspectY", LONG),
					("tmFirstChar", c_char),
					("tmLastChar", c_char),
					("tmDefaultChar", c_char),
					("tmBreakChar", c_char),
					("tmItalic", BYTE),	
					("tmUnderlined", BYTE),
					("tmStruckOut", BYTE),
					("tmPitchAndFamily", BYTE),
					("tmCharSet", BYTE),
					("ntmFlags", DWORD),
					("ntmSizeEM", c_uint),
					("ntmCellHeight", c_uint),
					("ntmAvgWidth", c_uint)]

class TEXTMETRIC(Structure):
	_fields_ = [("tmHeight", LONG),
					("tmAscent", LONG),
					("tmDescent", LONG),
					("tmInternalLeading", LONG),
					("tmExternalLeading", LONG),
					("tmAveCharWidth", LONG),
					("tmMaxCharWidth", LONG),
					("tmWeight", LONG),
					("tmOverhang", LONG),
					("tmDigitizedAspectX", LONG),
					("tmDigitizedAspectY", LONG),
					("tmFirstChar", CHAR),
					("tmLastChar", CHAR),
					("tmDefaultChar", CHAR),
					("tmBreakChar", CHAR),
					("tmItalic", BYTE),
					("tmUnderlined", BYTE),
					("tmStruckOut", BYTE),
					("tmPitchAndFamily", BYTE),
					("tmCharSet", BYTE)]


LF_FULLFACESIZE = 64

class ENUMLOGFONTEX(Structure):
	_fields_ = [("lfLogFont", LOGFONT),
					("elfFullName", c_char*LF_FULLFACESIZE),
					("elfStyle", c_char*LF_FULLFACESIZE),
					("elfScript", c_char*LF_FULLFACESIZE)]

class FONTSIGNATURE(Structure):
	_fields_ = [("fsSub", DWORD*4),
					("fsCsb", DWORD*2)]

class NEWTEXTMETRICEX(Structure):
	_fields_ = [("ntmentm", NEWTEXTMETRIC),
					("ntmeFontSignature", FONTSIGNATURE)]

ENUMFONTNAMEXPROC = WINFUNCTYPE(c_int,
		POINTER(ENUMLOGFONTEX),
		POINTER(NEWTEXTMETRIC),	 ## or NEWTEXTMETRICEX
		c_int,
		LPARAM)

DTFLAGS = {		# flags for DrawText
			'left' : 0,
			'top' : 0,
			'center' : 1,
			'right' : 2,
			'vcenter' : 4,
			'bottom' : 8,
			'wordbreak' : 16,
			'singleline' : 32,
			'expandtabs' : 64,
			'tabstop' : 128,
			'noclip' : 256,
			'externalleading' : 512,
			'calcrect' : 1024,
			'noprefix' : 2048,
			'internal' : 4096,
			'editcontrol' : 8192,
			'path_ellipsis' : 16384 | 65536, # DT_MODIFYSTRING
			'end_ellipsis' : 32768 | 65536, # DT_MODIFYSTRING
			'rtlreading' : 131072,
			'wordellipsis' : 262144,
			'nofullwidthcharbreak' : 524288,
			'hideprefix' : 1048576,
			'prefixonly' : 2097152,
			'word_ellipsis' : 262144| 65536
			}

#**************************************************
#
#						Font classes
#
#**************************************************


class FontFromHandle(object):
	"""Wrapps a font class around a font handle."""
	def __init__(self, handle):
		self.handle=handle
			
	def GetLogfont(self):
		lf=LOGFONT()
		if not gdi32.GetObjectA(self.handle, sizeof(LOGFONT), byref(lf)):
			raise RuntimeError("could not retrieve LOGFONT")
		return lf
 
	def GetAverageCharWidth(self, dc):
		hOldObject= gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		tm= TEXTMETRIC()
		result= gdi32.GetTextMetricsA(dc.handle, byref(tm))
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result:	
			raise RuntimeError("could not retirieve text metrics")
		return tm.tmAveCharWidth
	
	def GetMaxHeight(self, dc):
		hOldObject= gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		tm= TEXTMETRIC()
		result= gdi32.GetTextMetricsA(dc.handle, byref(tm))
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result:	
			raise RuntimeError("could not retirieve text metrics")
		return tm.tmHeight
	
	def LFHeightToSize(self, dc, lfHeight):
		if not dc: hDC = user32.GetDC(0)
		else: hDC= dc.handle
		LOGPIXELSY     = 90	##		
		size=int(round(float(abs(lfHeight)) /					\
				gdi32.GetDeviceCaps(hDC, LOGPIXELSY)	\
				*72))
		user32.ReleaseDC(0, hDC)
		return size
	
	def SizeToLFHeight(self, dc, size):
		if not dc: hDC = user32.GetDC(0)
		else: hDC= dc.handle
		LOGPIXELSY     = 90	##
		lfHeight= -(gdi32.GetDeviceCaps(hDC, LOGPIXELSY) *size /72)
		user32.ReleaseDC(0, hDC)
		return lfHeight
		
	
		

	def GetTextAlign(self, dc):
		raise RuntimeError("under construction !!")
		GDI_ERROR   = 4294967295
		align = gdi32.GetTextAlign(dc.handle)
		if align == GDI_ERROR:
			raise RuntimeError("could not retrieve text allign")
		
		flags = {
			'left' : 0,
			'right' : 2,
			
			'top' : 0,
			'bottom' : 8,
			
			'center' : 0,
			'baseline' : 24,
			
			'noupdatecp' : 0,
			'updatecp' : 1,			
			
			'rtlreading' : 256,
			}

	#(align | top) & baseline = top ?????????????
	
		
	def GetTextExtend(self, dc, text):
		size = SIZE()		
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		if not gdi32.GetTextExtentPoint32A(dc.handle, text, len(text), byref(size)):
			raise RuntimeError("could not retrieve text extend")
		gdi32.SelectObject(dc.handle, hOldObject)
		return size.cx, size.cy
	
	def GetTextExtendEx(self, dc, maxW, text):
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		chrMax=INT()
		sz=SIZE()
		arrPart = (INT*len(text))()
		if not gdi32.GetTextExtentExPointA(dc.handle, text, len(text), maxW, byref(chrMax), byref(arrPart), byref(sz)):
			raise RuntimeError("could not calculate text extend")
		gdi32.SelectObject(dc.handle, hOldObject)
		return (chrMax.value,	arrPart[ :chrMax.value],	(sz.cx, sz.cy))		
	
	
	def DrawState(self, dc, x, y, text, *flags):
		#validFlags=('disabled','right''union''prefixtext')
		if 'prefixtext' in flags: 	nFlag= 2		# DST_PREFIXTEXT
		else: nFlag= 1									# DST_TEXT
		for i in flags:
			if i=='disabled': nFlag |= 32		# DSS_DISABLED
			elif i=='right':nFlag |= 32768		# DSS_RIGHT
			elif i=='union':nFlag |= 16			# DSS_UNION
			elif i=='prefixtext': pass
			else: raise ValueError("invalid flag: %s" % i)
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		result= user32.DrawStateA(dc.handle, 0, None, text, len(text), x, y, 0, 0, nFlag)
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: raise RuntimeError("could not draw state")
	
	#-----------------------------------------------------------------------------------------------------------------------
	def DrawStateEx(self, dc, Rect, text, *flags):
		#
		# TODO just a raw version so far
		#
		# flags 'path_ellipsis', 'word_ellipsis', 'wordbreak' + some other DrawText flags are not yet implemented
		
		# check flags
		testFlags=('bottom','center','disabled','end_ellipsis','left','wordbreak',
							'right',	'singleline','top','union','vcenter','prefixtext','editcontrol', 'expandtabs')
		for i in flags:
			if i not in testFlags: raise ValueError("invalid flag: %s" % i)
						
		text=text.replace('\t', '        ')
		# prepair the dc for drawing
		gdi32.SaveDC(dc.handle)
		rg=RectRegion(Rect)
		if not gdi32.SelectClipRgn(dc.handle, rg.handle):
				raise RuntimeError("could not set clip region")
		rg.Close()
		if not gdi32.SelectObject(dc.handle, self.handle):
			raise RuntimeError("invalid font")
				
		chrMax=INT()
		sz=SIZE()
		arrPart = (INT*len(text))()
		if 'wordbreak' in flags:
			out=[]
			y=Rect.top
			fEnd=False
			while text:
				if not gdi32.GetTextExtentExPointA(dc.handle, text, len(text), Rect.right-Rect.left, byref(chrMax), byref(arrPart), byref(sz)):
					if not gdi32.RestoreDC(dc.handle, -1):
						raise RuntimeError("could not restore dc")
					raise RuntimeError("could not calculate text extend")
				#
				# break text at newline or whitespace
				n = text[:chrMax.value].find('\n') +1
				if n:	
					text, data= text[n:], text[:n-1]
					chrMax.value=n-1
				else:
					if len(text) > chrMax.value:
						n=text[:chrMax.value].rfind(' ') +1
						if n: chrMax.value=n
					text, data= text[chrMax.value:], text[:chrMax.value]
				#
				# if text extends the height of the rect add ellipsis and break next turn
				if 'editcontrol' in flags:
					if (y + sz.cy+sz.cy)  > Rect.bottom-Rect.top:
						fEnd=True
				else:
					if (y + sz.cy)  > Rect.bottom-Rect.top:
						fEnd=True
				
				if fEnd:
					if text: 
						#
						# TODO hope end ellipsis is processed correctly							
						#
						if 'end_ellipsis' in flags:
							text, data = '', '%s...' % data[:-3]
							if not gdi32.GetTextExtentExPointA(dc.handle, data, len(data), Rect.right-Rect.left, byref(chrMax), byref(arrPart), byref(sz)):
								if not gdi32.RestoreDC(dc.handle, -1):
									raise RuntimeError("could not restore dc")
								raise RuntimeError("could not calculate text extend")
							data=data[len(data)-chrMax.value:]
					else: text =''
				#		
				# horizontal text align
				if 'center' in flags:
					x=(Rect.left + (Rect.right-Rect.left - arrPart[chrMax.value-1])/2)
				elif 'right' in flags: x=Rect.right-arrPart[chrMax.value-1]
				else: x=Rect.left
				out.append((data, x, y))
				y +=sz.cy
			# END WHILE
			#	
			# flags
			if 'noprefix' in flags: flag= 1				# DST_TEXT
			else: flag=2											# DST_PREFIXTEXT
			if 'disabled' in flags: flag |= 32			# DSS_DISABLED
			elif 'union' in flags: flag|= 16			# DSS_UNION
			for text, x, y in out:
				if not user32.DrawStateA(dc.handle, 0, None, text, len(text), x, y, 0, 0, flag):
					if not gdi32.RestoreDC(dc.handle, -1):
									raise RuntimeError("could not restore dc")
					raise RuntimeError("could not draw state")
					
		else:		# singleline
			if not gdi32.GetTextExtentExPointA(dc.handle, text, len(text), Rect.right-Rect.left, byref(chrMax), byref(arrPart), byref(sz)):
				if not gdi32.RestoreDC(dc.handle, -1):
					raise RuntimeError("could not restore dc")
				raise RuntimeError("could not calculate text extend")
			
			data= text[:chrMax.value]
			
			# check for end_ellipsis
			if 'end_ellipsis' in flags:
				if chrMax.value < len(text):
					#
					# TODO hope end ellipsis is processed correctly							
					#
					data = '%s...' % data[:-3]
					if not gdi32.GetTextExtentExPointA(dc.handle, data, len(data), Rect.right-Rect.left, byref(chrMax), byref(arrPart), byref(sz)):
						if not gdi32.RestoreDC(dc.handle, -1):
							raise RuntimeError("could not restore dc")
						raise RuntimeError("could not calculate text extend")
					data=data[len(data)-chrMax.value:]
			#		
			# hotizontal text align
			if 'center' in flags:
				x=(Rect.left + (Rect.right-Rect.left - arrPart[chrMax.value-1])/2)
			elif 'right' in flags: x=Rect.right-arrPart[chrMax.value-1]
			else: x=Rect.left
			#
			# vertical text align
			if 'vcenter' in flags or ('bottom' in flags and 'top' in flags):
				y=((Rect.bottom-Rect.top)/2)-(sz.cy/2)
			elif 'bottom' in flags: y=Rect.bottom-sz.cy
			else: y=Rect.top
			#
			# flags
			if 'prefixtext' in flags: flag= 2	 			# DST_PREFIXTEXT
			else: flag= 1											# DST_TEXT
			if 'disabled' in flags: flag |= 32			# DSS_DISABLED
			elif 'union' in flags: flag|= 16			# DSS_UNION
			if not user32.DrawStateA(dc.handle, 0, None, data, len(data), x, y, 0, 0, flag):
					if not gdi32.RestoreDC(dc.handle, -1):
						raise RuntimeError("could not restore dc")
					raise RuntimeError("could not draw state")
				
		# finally
		if not gdi32.RestoreDC(dc.handle, -1): raise RuntimeError("could not restore dc")
		
	#----------------------------------------------------------------------------------------------------------------
		
	def TextOutEx(self, dc, text, x, y, *flags, **kwargs):
	
		options = {	'opaque':2,'clipped':4,'glyph_index':16,'rtlreading':128}
		flag = 0
		for i in flags:
			try: flag |= options[i]
			except:	raise ValueError("invalid flag: %s" % i) 
		
		rect= kwargs.get('rect')
		if rect: rect = byref(rect)
		spacing= kwargs.get('spacing')
		if spacing:
			arrSp=(c_int*len(spacing))(*spacing)
			spacing = byref(arrSp)
				
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		result= gdi32.ExtTextOutA(dc.handle, x, y, flag, rect, text, len(text), spacing)
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: raise RuntimeError("could not print text out ex")

		
	
	def DrawText(self, dc, Rect, text, *flags):
		flag = 0
		for i in flags:
			try: flag |= DTFLAGS[i]
			except: raise ValueError("invalid flag: %s" % i)
		# REMOVED
		#if tabwidth:
		#	flag |= 128	# DT_TABSTOP
		#	flag |= tabwidth << 8	# HIBYTE of LOWORD
		hOldObject = gdi32.SelectObject(dc.handle, self.handle)
		if not hOldObject: raise RuntimeError("invalid font")
		result= user32.DrawTextA(dc.handle, text, len(text), byref(Rect), flag)
		gdi32.SelectObject(dc.handle, hOldObject)
		if not result: 	raise RuntimeError("could not draw text")
		
	def Release(self): self.Close()

	def Close(self):
		if hasattr(self, 'handle'):
			self.__delattr__('handle')
		else:
			raise RuntimeError("font is closed")	


#*********************************************************************
class DisposableFont(FontFromHandle):
	def __init__(self, handle):
		self.handle = handle
		TrackHandler.Register('fonts', self.handle)
		
	def Release(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('fonts', self.handle)
			self.__delattr__('handle')
		else:
			raise RuntimeError("font is closed")
	
	def Close(self):
		if hasattr(self, 'handle'):
			TrackHandler.Unregister('fonts', self.handle)
			result= gdi32.DeleteObject(self.handle)
			self.__delattr__('handle')
			if not result: raise RuntimeError("could not delete font")
		else:
			raise RuntimeError("font is closed")

#*****************************************************

class FontFromLogfont(DisposableFont):
	def __init__(self, logfont):
		handle = gdi32.CreateFontIndirectA(byref(logfont)) 
		if not handle: raise RuntimeError("could not create font")
		DisposableFont.__init__(self, handle)
		
#*****************************************************
class Font(DisposableFont):
	"""Font class"""
	
	# TODO
	# some more kwargs
	#
	def __init__(self, fontname=None, size=0, width=0, weight=0, escapement=0, orientation=0, italic=0, underline=0):
		lf=LOGFONT()
		if fontname==None:							# DEFAULT
			SYSTEM_FONT = 13 
			gdi32.GetObjectA(gdi32.GetStockObject(SYSTEM_FONT),
									sizeof(lf), 
									byref(lf))
		else:
			lf.lfHeight = self.SizeToLFHeight(None, size)
			lfWidth = width
			lf.lfFaceName = fontname
			lfEscapement = escapement
			lfOrientation = orientation
			lf.lfWeight = weight
			lf.lfItalic = italic
			lf.lfUnderline = underline
		
		handle = gdi32.CreateFontIndirectA(byref(lf)) 
		if not handle: raise RuntimeError("could not create font")
		DisposableFont.__init__(self, handle)
		
		
				

#**************************************************
class EnumFonts(object):
	"""Enumerates all available fonts.
	Use:
	e = enumfonts()
	fontdata = e.enumfontfamilies()
	e.close()		# recomended

	Where fontdata is a list of tupels:
	(
	'font-name',		# like 'arial'
	'font-type',			# 'raster' or 'truetype'
	available-sizes		# as list
	)
		
	Available sizes for 'truetype' fonts are always some
	commonly used default sizes:
	8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72
	- feel free to use other sizes.
	Available sizes for 'raster' fonts are fixed and no others 
	should be used.
	"""

	RASTER_FONTTYPE   = 1
	DEVICE_FONTTYPE   = 2
	TRUETYPE_FONTTYPE = 4
	
	def __init__(self, DC=0, ttDefaultSizes=None):
		"""Init the font enumerator.
		If hDc is specified it should be a handle to a device
		context. Note: you should not call 'close' if you handle
		out your own dc. You are responsible for closing it.
		Use 'ttDefaultSizes' to specify alternative default sizes for
		trutype fonts.
		'"""
		self._p_enumproc = ENUMFONTNAMEXPROC(self._EnumFontsFamProc)
		self.logfont = LOGFONT()
		
		self.ownDC=False
		if DC: self.hDC = DC.handle
		else: 
			self.hDC = user32.GetDC(0)
			self.ownDC=True
		if ttDefaultSizes:
			self.defaultsizes = ttDefaultSizes
		else:
			self.defaultsizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
		self.out = []

	
	def EnumFontFamilies(self, facename=''):
		"""Enumerates all font families. You can specify a
		facename to enumerate available fonts for this font
		only."""
		self.out, self.tmp_sizes = [], []
		self.logfont.lfFaceName = facename
		lparam = 0
		if facename: lparam = 1
		gdi32.EnumFontFamiliesExA(self.hDC, byref(self.logfont), self._p_enumproc, lparam, 0)
		self.out.sort()
		return self.out
		
		
	def __del__(self): self.close()
	def Close(self):
		"""Frees all opend handles."""
		if self.ownDC:
			user32.ReleaseDC(0, self.hDC)

	def _EnumFontsFamProc(self, pLfe, pNtme, FontType, lparam):
		if FontType==self.RASTER_FONTTYPE:
			if not lparam:
				out = self.out		# make tmp copy so self.out
										# is allways [] on exit
				self.EnumFontFamilies(pLfe[0].lfLogFont.lfFaceName)
				self.out = out
				self.tmp_sizes.sort()
				self.out.append((pLfe[0].lfLogFont.lfFaceName,
										'raster',
										self.tmp_sizes))
			else:
				# gather sizes for raster fonts
				self.tmp_sizes.append(pNtme[0].tmMaxCharWidth)
		
		elif FontType==self.TRUETYPE_FONTTYPE:
			self.out.append((pLfe[0].lfLogFont.lfFaceName,
									'truetype',
									self.defaultsizes))
		elif FontType==self.DEVICE_FONTTYPE:
			pass
		return 1	


#**************************************************
#e = enumfonts()
#fontdata = e.enumfontfamilies()

#e.close()		# recomended
