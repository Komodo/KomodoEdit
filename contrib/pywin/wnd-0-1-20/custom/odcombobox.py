"""

TODO

	
NOTES	
	- GetFont/SetFont are unusable for ownerdraw comboboxes, so they are not 
		imple mented


"""

from wnd.controls.blank import Blank
from wnd.controls import windowclass
from wnd.controls.combobox import Combobox
from wnd.wintypes import (DRAWITEMSTRUCT, 
													MEASUREITEMSTRUCT,
													WINDOWPOS,
													LOWORD,
													HIWORD)
from wnd import fwtypes as fw

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

_CUSTOM_N_ODCOMBOBOXES = 0


class ODCombobox(Combobox):
	
	def __init__(self, parent, *styles):
		
		# register a class for a container window
		global _CUSTOM_N_ODCOMBOBOXES
		_CUSTOM_N_ODCOMBOBOXES += 1
		c="odcombobox-container-%s" % _CUSTOM_N_ODCOMBOBOXES
		classname=windowclass.SZ_CONTROL_CLASS % c
		wc = windowclass.WindowClass()
		wc.SetClassName(classname)
		wc.SetCursor()
		wc.SetBackground('activecaption')	## some ugly color for testing
		
		# init the container
		self._custom_Container= Blank(parent, wc, 0, 0, 0, 0, *styles)
		self._custom_Container.onMESSAGE= self.onMESSAGEContainer

		self.Hwnd= 0	## has to be initialized before creating the combobox	
		
		
		# 'simple' comboboxes not get redrawn correctly when resized 
		# right after __init__ (??). This is really unelegant, but currently helps.
		self._custom_bugfix= False
		
	def InitCombobox(self, x, y, w, h, *styles):
		
		Combobox.__init__(self, self._custom_Container, x, y, w, h, *styles)
		if self.GetStyleL('style') & 3 < 2:		# simple comboobx
			self._custom_Container.SetWindowPosAndSize(x, y, w, h)
		else:
			rc= self.GetWindowRect()
			self._custom_Container.SetWindowPosAndSize(x, y, w, rc.bottom-rc.top)
		
					
	#-----------------------------------------------------------------------------------------------
	# catch the first WM_MEASUREITEM messages 
	# send before Combobox returns from __init__
	def onMESSAGEContainer(self, hwnd, msg, wp, lp):
		
		if msg== 44:	# WM_MEASUREITEM:
			mi= MEASUREITEMSTRUCT.from_address(lp)
			self.onMSG(self.Hwnd, "measureitem", wp, mi)
			return 1
		
		elif msg== 5:	# WM_SIZE
			if self.Hwnd:
				if self.GetStyleL('style') & 3 < 2:		# simple comboobx
					if not self._custom_bugfix:
						self._custom_bugfix= True
						self.SetWindowSize(LOWORD(lp)-1,  HIWORD(lp))
					self.SetWindowSize(LOWORD(lp),  HIWORD(lp))
				else:
					rc= self.GetWindowRect()
					self.SetWindowSize(LOWORD(lp),  rc.bottom - rc.top)
				
								
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				if msgr.msg== 43:	# WM_DRAWITEM
					msgr.fReturn= 1
					di= DRAWITEMSTRUCT.from_address(msgr.lParam)
					self.onMSG(self.Hwnd, "drawitem", wp, di)
					return 1
				elif msgr.msg== 44:	# WM_MEASUREITEM
					msgr.fReturn= 1
					mi= MEASUREITEMSTRUCT.from_address(msgr.lParam)
					self.onMSG(self.Hwnd, "measureitem", wp, mi)
					return 1
		
		return Combobox.onMESSAGE(self, hwnd, msg, wp, lp)
	
	
	#-----------------------------------------------------------------
	# overwritten methods 

	def onMSG(self,  hwnd, msg, wp, lp):	
		# overwrite
		pass
		

	
	def Show(self):
		return self._custom_Container.Show()
			
	def Hide(self):
		return self._custom_Container.Hide()
			
	def GetContainer(self):
		return self._custom_Container
			
	
			
#**************************************************************************************

class Styles:
	prefix=[]

class Msgs:
	pass