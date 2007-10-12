

from wnd.controls.base import control
from wnd.controls.base.methods import ControlMethods
#*************************************************
class Styles:
	SS_BITMAP   = 14
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += 'SS_', 
	
class Msgs: 
		STM_SETIMAGE = 370
		STM_GETIMAGE = 371
		
Msgs.__dict__.update(control.control_msgs.__dict__)

class StaticBitmapMethods:
		
	def SetBitmap(self, Bitmap):
		"""Sets an icon to be displayed by the control."""
		IMAGE_BITMAP      = 0
		self.SendMessage(self.Hwnd, self.Msg.STM_SETIMAGE, IMAGE_BITMAP, Bitmap.handle)
		
	def GetBitmap(self):
			"""Returns the handle of the image associated to the
			control."""
			IMAGE_BITMAP      = 0
			return self.SendMessage(self.Hwnd, self.Msg.STM_GETICON, IMAGE_BITMAP, 0)



class StaticBitmap(StaticBitmapMethods, control.BaseControl, ControlMethods):
	
	def __init__(self, parent, Bitmap, x, y, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'bitmap',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, 0, 0,   *styles)						
		if Bitmap: self.SetBitmap(Bitmap)

	
class StaticBitmapFromHandle(StaticBitmapMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		



#**********************************************
class Styles2:
	SS_ICON = 3
	
Styles2.__dict__.update(control.control_styles.__dict__)
Styles2.prefix += ['SS_', ]
	
		
class Msgs2: 
		STM_SETIMAGE = 370
		STM_GETIMAGE = 371

Msgs2.__dict__.update(control.control_msgs.__dict__)


class StaticIconMethods:
	def SetIcon(self, Icon):
		"""Sets an icon to be displayed by the control."""
		IMAGE_ICON        = 1
		self.SendMessage(self.Hwnd, self.Msg.STM_SETIMAGE, IMAGE_ICON, Icon.handle)
		
	def GetIcon(self):
			"""Returns the handle of the image associated to the
			control."""
			IMAGE_ICON        = 1
			return self.SendMessage(self.Hwnd, self.Msg.STM_GETICON, IMAGE_ICON, 0)


class StaticIcon(StaticIconMethods, control.BaseControl, ControlMethods):
	
	
	def __init__(self, parent, Icon, x, y, *styles):
		self.Style= Styles2
		self.Msg= Msgs2
		
		
		styles += 'icon',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, 0, 0, *styles)						
		if Icon: self.SetIcon(Icon)



class StaticIconFromHandle(StaticIconMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles2
		self.Msg= Msgs2
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		

#

		
#****************************************************
class Styles3:
	SS_BLACKRECT       = 4
	SS_GRAYRECT        = 5
	SS_WHITERECT       = 6
Styles3.__dict__.update(control.control_styles.__dict__)
Styles3.prefix += ['SS_', ]
		
class Msgs3: pass
Msgs3.__dict__.update(control.control_msgs.__dict__)


class StaticRectMethods:
	
	def SetStyle(self, *styles):
		rcStyles = ['blackrect','grayrect','whiterect']
		rcStyles2 = ['-blackrect','-grayrect','-whiterect']
		a, b= [], []
		for i in styles:
			if i in rcStyles: a.append(i)
			else: b.append(i)
		if a:
			rcStyles2.remove('-%s' % a[-1])
			b += rcStyles2 + [a[-1]]
		ControlMethods.SetStyle(self, *b)
		self.RedrawClientArea()
		
	def GetStyle(self):
		styles = ControlMethods.GetStyle(self)
		if 'whiterect' in styles or 'grayrect' in styles:
			styles.remove('blackrect')
		return styles


class StaticRect(StaticRectMethods, control.BaseControl, ControlMethods):
		

	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles3
		self.Msg= Msgs3 
		
		
		styles += 'grayrect',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, w, h, *styles)

		

class StaticRectFromHandle(StaticRectMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles3
		self.Msg= Msgs3 
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		


#*************************************************
class Styles4:
	SS_ETCHEDVERT      = 17
Styles4.__dict__.update(control.control_styles.__dict__)
Styles4.prefix += ['SS_', ]
		
class Msgs4: pass
Msgs4.__dict__.update(control.control_msgs.__dict__)


class StaticVert(control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, h, *styles):
		self.Style= Styles4
		self.Msg= Msgs4 
		
		
		styles += 'etchedvert',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, 0, h, *styles)

		

class StaticVertFromHandle( control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles4
		self.Msg= Msgs4
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		



	
#*************************************************
class Styles5:
	SS_ETCHEDHORZ      = 16
Styles5.__dict__.update(control.control_styles.__dict__)
Styles5.prefix += ['SS_', ]
		
class Msgs5: pass
Msgs5.__dict__.update(control.control_msgs.__dict__)


class StaticHorz(control.BaseControl, ControlMethods):
		
	
	def __init__(self, parent, x, y, w, *styles):
		self.Style= Styles5
		self.Msg= Msgs5 
		
		styles += 'etchedhorz',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, w, 0, *styles)


class StaticVertFromHandle(control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles5
		self.Msg= Msgs5 
		
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		


	
#*************************************************
class Styles6:
	SS_BLACKFRAME      = 7
	SS_GRAYFRAME       = 8
	SS_WHITEFRAME      = 9
	SS_ETCHEDFRAME     = 18
Styles6.__dict__.update(control.control_styles.__dict__)
Styles6.prefix += ['SS_', ]
		
class Msgs6: pass
Msgs6.__dict__.update(control.control_msgs.__dict__)


class StaticFrameMethods:
	
	def GetStyle(self):
		styles = ControlMethods.GetStyle(self)
		if 'whiteframe' in styles:
			styles.remove('grayframe')
		return styles
	
	def SetFrame(self):
		style=ControlMethods.GetStyleL(self, 'style')
		style |= 7|8|9|16|17|18
		style ^= 7|8|9|16|17|18
		style |= 18 
		ControlMethods.SetStyleL(self, 'style', style)

	def SetStyle(self, *styles):
		"""Use this at your own risk."""
		st = {'blackframe':7,'grayframe':8,'whiteframe':9, 'etchedframe':18}
		style=ControlMethods.GetStyleL(self, 'style')
		out = []
		flag = False
		for i in styles:
			if i in st:
				style |= 7|8|9|18
				style ^= 7|8|9|18
				style |= st[i]
				flag = True
			else: out.append(i)
		if flag: 
			ControlMethods.SetStyleL(self, 'style', style)
			# Not enough
			#self.OffsetWindowSize(1, 1)
			#self.OffsetWindowSize(-1, -1)
			x,y,w,h = self.GetWindowRect().ToSize()
			self.SetWindowSize(0, 0)
			self.SetWindowSize(w, h)
		if out: ControlMethods.SetStyle(self, *out)

class StaticFrame(StaticFrameMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles6
		self.Msg= Msgs6 
		
		
		styles += 'grayframe',
		control.BaseControl.__init__(self, parent, 'Static', '', x, y, w, h, *styles)
	

class StaticFrameFromHandle(StaticFrameMethods,  control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles6
		self.Msg= Msgs6
		
		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)


		
#***********************************************
class Styles7:
	SS_LEFT            = 0	
	SS_CENTER          = 1	
	SS_RIGHT           = 2	 
	SS_SIMPLE          = 11	
	SS_LEFTNOWORDWRAP  = 12	
Styles7.__dict__.update(control.control_styles.__dict__)
Styles7.prefix += ['SS_', ]
		
class Msgs7: pass
Msgs7.__dict__.update(control.control_msgs.__dict__)



class StaticTextMethods:
	def SetText(self, text):
		"""By default set text for static controls is not allowed,
		use this at your own risk."""
		ControlMethods.SetText(self, text)
		x,	y, w, h = self.GetWindowRect().ToSize()
		self.SetWindowSize(0, 0)
		self.SetWindowSize(w, h)
		
	def GetStyle(self):
		""" """
		styleList =ControlMethods.GetStyle(self)
		if 'right' in styleList or 'center' in styleList or 'leftnowordwrap' in styleList:
			styleList.remove('left')
		if 'simple' in styleList:
			styleList.remove('right')
			styleList.remove('center')
		return styleList
				
	def SetStyle(self, *styles):
		"""  """
		st = {'left':0,'center':1,'right':2,'simple':11,
						'leftnowordwrap':12}
		style=ControlMethods.GetStyleL(self, 'style')
		out = []
		flag = False
		for i in styles:
			if i in st:
				style |= 1|2|11|12
				style ^= 1|2|11|12
				style |= st[i]
				flag = True
			else:
				out.append(i)
		if flag:
			ControlMethods.SetStyleL(self, 'style', style)
		if out:
			ControlMethods.SetStyle(self, *out)


class StaticText(StaticTextMethods, control.BaseControl, ControlMethods):
	

	def __init__(self, parent, title, x, y, w, h, *styles):
		self.Style= Styles7
		self.Msg= Msgs7 
		
		
		control.BaseControl.__init__(self, parent, 'Static', title, x, y, w, h, *styles)						
		

		

class StaticTextFromHandle(StaticTextMethods,  control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles7
		self.Msg= Msgs7 
		

		#styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)






	