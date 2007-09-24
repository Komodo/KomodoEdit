
"""
LAST VISITED: 20.02.05



TODO

	- tooltips do not work. stausbars can not be set a tooltip control ?!?
	


# NOT IMPLEMENTED
#
# SB_SETMINHEIGHT
# SB_GETUNICODEFORMAT
# SB_SETUNICODEFORMAT
# SB_SETTIPTEXT	 # not working currently
# SB_GETTITEXT	 # not working currently
# WM_DRAWITEM



"""



from wnd.wintypes import (NMHDR, 
												byref,
												c_int,
												RECT,
												LOWORD, 
												UINT_MAX,
												create_string_buffer,
												InitCommonControlsEx)
from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
ICC_BAR_CLASSES        = 4 
InitCommonControlsEx(ICC_BAR_CLASSES)

#***************************************************

class StatusbarMethods:
	#-----------------------------------------------------------------	
	# message handlers	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm = NMHDR.from_address(msgr.lParam)
					if nm.code ==self.Msg.NM_CLICK:
						self.onMSG(hwnd, "click", 0, 0)
					elif nm.code ==self.Msg.NM_DBLCLK:
						self.onMSG(hwnd, "dblclick", 0, 0)
					elif nm.code ==self.Msg.NM_RCLICK:
						self.onMSG(hwnd, "rclick", 0, 0)
					elif nm.code ==self.Msg.NM_RDBLCLK:
						self.onMSG(hwnd, "rdblclick", 0, 0)
					elif nm.code ==self.Msg.SBN_SIMPLEMODECHANGE:
						self.onMSG(hwnd, "simplemodechange", 0, 0)
			return 0		# 
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
						
	#-------------------------------------------------------------------------
	# methods
	
	def SetText(self, text, i=0, flag=0):
		text=text[:127]
		if self.IsSimple():	i=255	# here its 255
		else:
			if i >= self.__len__():	raise IndexError("index out of range")
		if flag=='noborders': flag= SBT_NOBORDERS
		elif flag=='popout': flag= SBT_POPOUT
		elif flag=='rtlreading': flag= SBT_RTLREADING
		elif not flag: flag=0
		else: raise ValueError("invalid flag")
		#flag=SBT_TOOLTIPS
		if not self.SendMessage(self.Hwnd, self.Msg.SB_SETTEXT, i|flag, text):
			raise RuntimeError("could not set text")

	def GetText(self, i=0):
		if self.IsSimple():
			return ControlMethods.GetText(self)
		else:
			if i >= self.__len__():	raise IndexError("index out of range")
		n = self.SendMessage(self.Hwnd, self.Msg.SB_GETTEXTLENGTH, i, 0)
		if not n:	return ''
		p = create_string_buffer(LOWORD(n) +1)
		self.SendMessage(self.Hwnd, self.Msg.SB_GETTEXT, i, p)
		return p.value

	def GetParts(self):
		n = self.__len__()
		arr = (c_int*n)()
		if not self.SendMessage(self.Hwnd, self.Msg.SB_GETPARTS, n, byref(arr)):
			raise RuntimeError("could not get parts")
		return tuple(map(None, arr))
		
	def SetParts(self, *parts):
		if len(parts) > 255: raise RuntimeError("too many parts")
		n = len(parts)
		arr = (c_int*n)(*parts)
		if not self.SendMessage(self.Hwnd, self.Msg.SB_SETPARTS, n, byref(arr)):
			raise RuntimeError("could not set parts")

	def __len__(self):
		"""Return the length of the statusbar, i.e the number
		of cells is has."""
		result = self.SendMessage(self.Hwnd, self.Msg.SB_GETPARTS, 0, 0)
		if not result:
			raise RuntimeError("could not retrieve lenght")
		return result
	
	def GetPartRect(self, i=0):
		rc = RECT()
		if not self.SendMessage(self.Hwnd, self.Msg.SB_GETRECT, i, byref(rc)):
			raise RuntimeError("could not retrieve part rect")
		return rc
		
	def GetBorders(self):
		arrInt=(c_int*3)()
		if not self.SendMessage(self.Hwnd, self.Msg.SB_GETBORDERS, 0, byref(arrInt)):
			raise RuntimeError("could not retrieve borders")
		return arrInt[0], arrInt[1], arrInt[2]

	def SetBkColor(self, colorref):
		if colorref==None: colorref=CLR_DEFAULT
		result= self.SendMessage(self.Hwnd, self.Msg.SB_SETBKCOLOR, 0, colorref)
		if result != CLR_DEFAULT: return result
	
	def SetIcon(self, icon, i=0):
		if self.IsSimple():	i=-1	# for the fun of it here its -1
		else:
			if i >= self.__len__():	raise IndexError("index out of range")
		if not self.SendMessage(self.Hwnd, self.Msg.SB_SETICON, i, icon.handle):
			raise RuntimeError("could not set icon")
	
	def GetIcon(self, i=0):
		if self.IsSimple():	i=-1
		else:
			if i >= self.__len__():	raise IndexError("index out of range")
		result= self.SendMessage(self.Hwnd, self.Msg.SB_GETICON, i, 0)
		if not result: raise RuntimeError("could not retrieve icon")
		return result
	
	def IsSimple(self):
		return bool(self.SendMessage(self.Hwnd, self.Msg.SB_ISSIMPLE, 0, 0))
			
	def SetSimple(self):
		if self.IsSimple(): return False
		# docs claim return value is nonzero on success, but allways zero is returned
		self.SendMessage(self.Hwnd, self.Msg.SB_SIMPLE, 1, 0)
		return True
	
	def SetMultiple(self):
		if not self.IsSimple(): return False
		# same as SetSimple
		self.SendMessage(self.Hwnd, self.Msg.SB_SIMPLE, 0, 0)
		return True 
		
	# NOT working
	# it is working but I never seen tolltip
	#def SetTipText(self, text, i=0):
	#	"""Sets the tooltip for a cell.
	#	Note:
	#	If the statusbar is not created with the 'tooltips' style
	#	an error is raised.
	#	TODO:
	#	Not working
	#	"""
	#	if i >= self.__len__():
	#		raise "index out of range"
	#	if not self.GetStyleL('style') & self.Style.SBARS_TOOLTIPS:
	#		raise "tooltips style not set"
	#	self.SendMessage(self.Hwnd, self.Msg.SB_SETTIPTEXT, i, text)


#**********************************************************************************
#***********************************************
NM_FIRST = UINT_MAX
SBN_FIRST               = UINT_MAX-880 
WM_USER = 1024
#***********************************************


class Styles:
	CCS_TOP           = 1
	CCS_NOMOVEY       = 2
	CCS_BOTTOM        = 3		# currently not documented
	CCS_NORESIZE      = 4
	CCS_NOPARENTALIGN = 8
		
	SBARS_SIZEGRIP = 256
	SBARS_TOOLTIPS = 2048
		
	WS_CLIENT_NORESIZE=1
	
Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += 'CCS_', 'SBARS_'

class Msgs: 
		
	NM_CLICK           = NM_FIRST - 2  # uses NMCLICK type
	NM_DBLCLK          = NM_FIRST - 3
	NM_RETURN          = NM_FIRST - 4
	NM_RCLICK          = NM_FIRST - 5  # uses NMCLICK type
	
	NM_RDBLCLK         = NM_FIRST - 6
	SBN_SIMPLEMODECHANGE = SBN_FIRST
	
		
	# for tooltips
	SB_SETTEXT           = WM_USER + 1
	SB_GETTEXT           = WM_USER + 2
	SB_GETTEXTLENGTH     = WM_USER + 3
	
	SB_SETPARTS          = WM_USER + 4
	SB_GETPARTS          = WM_USER + 6
	SB_GETBORDERS        = WM_USER + 7
	SB_SETMINHEIGHT      = WM_USER + 8
	SB_SIMPLE            = WM_USER + 9
	SB_GETRECT           = WM_USER + 10
	SB_ISSIMPLE          = WM_USER + 14
	SB_SETICON           = WM_USER + 15
	SB_SETTIPTEXT        = WM_USER + 16
	SB_GETTIPTEXT        = WM_USER + 18
	SB_GETICON           = WM_USER + 20
	SB_SETBKCOLOR        = 8193  # lParam = bkColor

Msgs.__dict__.update(control.control_msgs.__dict__)



class Statusbar(StatusbarMethods, control.BaseControl, ControlMethods):
		
	
	def __init__(self, parent, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		


		# clipsiblings paints the statusbar correctly in respect to eventully overlapping
		# neighbour windows, but introduces clipping errors with the gripper
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "msctls_statusbar32", "", 0, 0, 0, 0, *styles)	
		
		#if not 'noresize' in styles:
		#	parent.RegisterResizing(self, 1)
		
		
class StatusbarFromHandle(StatusbarMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd,*styles)
		
	

	
	

	#------------------------------------------------------------------------
	
	
	
	# not shure what this does
	#def setheight(self, n):
	#	 self.SendMessage(self.Hwnd, self.Msg.SB_SETMINHEIGHT, n, 0)
	#	 self.updateclientarea()


CLR_DEFAULT = 4278190080

SBT_OWNERDRAW        = 4096
SBT_NOBORDERS        = 256
SBT_POPOUT           = 512
SBT_RTLREADING       = 1024
SBT_TOOLTIPS         = 2048
SBT_NOTABPARSING     = 2048



