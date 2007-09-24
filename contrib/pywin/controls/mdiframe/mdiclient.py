

from wnd.wintypes import (user32,
												byref,
												Structure,
												WNDPROC,
												HANDLE, 
												UINT,
												LOWORD,
												HIWORD,
												BOOL)

from wnd import fwtypes as fw
from wnd.controls.base import control
from wnd.controls.base import methods

from wnd.controls.windowclass import WindowClass, SZ_CONTROL_CLASS

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
N_MDICHILD= 0

WM_PARENTNOTIFY     = 528

WM_NCDESTROY = 130
WM_CREATE = 1

WS_EX_MDICHILD        = 64
GWL_ID         = -12

WM_MDICREATE        = 544
WM_MDIDESTROY       = 545
WM_MDIACTIVATE      = 546
WM_MDIRESTORE       = 547
WM_MDINEXT          = 548
WM_MDIMAXIMIZE      = 549
WM_MDITILE          = 550
WM_MDICASCADE       = 551
WM_MDIICONARRANGE   = 552
WM_MDIGETACTIVE     = 553
WM_MDISETMENU       = 560
WM_MDIREFRESHMENU   = 564

WS_MAXIMIZE        = 16777216
WS_MINIMIZE        = 536870912
WS_VSCROLL         = 2097152
WS_HSCROLL         = 1048576
#****************************************************************************
# MDI child window
#****************************************************************************

class Styles: pass
	
Styles.__dict__.update(control.control_styles.__dict__)
#Styles.prefix += []

class Msgs: pass
		
Msgs.__dict__.update(control.control_msgs.__dict__)


class MDIChild(control.ControlFromHandle, methods.ControlMethods):
	
	def __init__(self, hwnd, *styles):
		
		self.Msg= Msgs
		self.Style= Styles
		
		control.ControlFromHandle.__init__(self, hwnd, *styles)

#****************************************************************************
# MDI client window
#****************************************************************************

class MDIClient(control.ControlFromHandle, methods.ControlMethods):
	
	def __init__(self, hwndParent, hMenu, x, y, w, h, *styles):
		
		self.Msg= Msgs
		self.Style= Styles
		
		self.pChildProc= WNDPROC(self.ChildProc)
		self._client_fMessageSend= False
		self._client_MDIChildren= []	
	
		iStyles = self.ParseStyles(styles, 					
								style=1073741824|268435456|33554432|67108864)
		self._base_style = [iStyles[3], iStyles[4]]	# base/clientstyle
				
		cs= CLIENTCREATESTRUCT(hMenu, fw.WND_ID_MDICHILD_MIN)
			
		# create the MDI-client
		## default  WS_CHILD|WS_VISIBLE|WS_CLIPCHILDREN|
		## WS_CLIPSIBLINGS|WS_HSCROLL|WS_VSCROLL
		#iStyles= 1073741824|268435456|33554432|67108864|1048576|2097152
		hwnd=user32.CreateWindowExA(
							iStyles[1],"mdiclient",'',iStyles[0],	x,y,w,h,
							hwndParent,fw.ID.New(),0,byref(cs))
		if not hwnd: raise "could not create MDIFrame"

		control.ControlFromHandle.__init__(self, hwnd, 'nosubclass')
		
		
	
	#*******************************************************************
	# MDI child methods
	#*******************************************************************
	
	def ChildProc(self, hwnd, msg, wp, lp):
		
		if msg==5:	## WM_SIZE
			self.onMSG(hwnd, "childsizing", hwnd, [0, 0, LOWORD(lp), HIWORD(lp)])

		elif msg==WM_CREATE:
			self._client_MDIChildren.append(hwnd)
			self.onMSG(self.Hwnd, "childcreated", hwnd, 0)
		
		elif msg==WM_MDIACTIVATE:
			if self._client_fMessageSend==True:
				self._client_fMessageSend=False
			else:
				self._client_fMessageSend=True
				self.onMSG(self.Hwnd, "childactivated", lp, wp)
		
		elif msg==WM_NCDESTROY:
			self._client_MDIChildren.remove(hwnd)
			self.onMSG(self.Hwnd, "childdestroyed", hwnd, 0)
					
		return user32.DefMDIChildProcA(hwnd, msg, wp, lp)
	
	
	#----------------------------------------------------------------------------------------------
			
	def NewChild(self, title, x, y, w, h, *styles, **kwargs):
		
		global N_MDICHILD
		N_MDICHILD += 1
		wc = WindowClass()
		
		classname= SZ_CONTROL_CLASS % "mdichild-%s" % N_MDICHILD
		wc.SetClassName(classname)
		wc.SetCursor()
		
		Icon= kwargs.get('icon')
		if Icon:
			wc.SetIcons(Icon)
		wc.SetBackground('window')
		wc.SetWindowProc(self.pChildProc)
		wc.Register()
		## don't need an ID here. MDI is taking care about it, including recycling.
				
		
		# WS_CHILD|WS_VISIBLE|WS_CLIPCHILDREN|WS_CLIPSIBLINGS
		iStyle= 1073741824|268435456|33554432|67108864
		if styles:
			st= {'maximized':WS_MAXIMIZE,
					'minimized':WS_MINIMIZE,
					'vscroll':WS_VSCROLL,
					'hscroll':WS_HSCROLL}
			for i in styles:
				try: iStyle |= st[i]
				except: raise ValueError, "invalid style: %s" % i
		
		hwnd=user32.CreateWindowExA(
							WS_EX_MDICHILD,classname,title, 
							iStyle,x,y,w,h,
							self.Hwnd,0,0,0)
		if not hwnd: raise RuntimeError, "could not create MDI child"
		return self.GetChild(hwnd)
	
	def __iter__(self):
		for i in self._client_MDIChildren: yield i
		
	def IsChild(self, hwnd):
		return hwnd in self.self._client_MDIChildren
	
	def GetChild(self, hwnd):
		return MDIChild(hwnd, 'nosubclass')
		
	def Activate(self, hwnd):
		return user32.SendMessageA(self.Hwnd, WM_MDIACTIVATE, hwnd, 0)
	
	def GetActive(self):
		return user32.SendMessageA(self.Hwnd, WM_MDIGETACTIVE, 0, 0)
	
	def ActivateNext(self, hwnd=None):
		user32.SendMessageA(self.Hwnd, WM_MDINEXT, hwnd and hwnd or 0, 0)

	def ActivatePrevious(self, hwnd=None):
		user32.SendMessageA(self.Hwnd, WM_MDINEXT, hwnd and hwnd or 0, 1)
	
	def Destroy(self, hwnd):
		user32.SendMessageA(self.Hwnd, WM_MDIDESTROY, hwnd, 0)

	def Clear(self):
		out= []
		for i in self: out.append(i)
		for i in out: self.Destroy(i)
		
	def Maximize(self, hwnd):
		user32.SendMessageA(self.Hwnd, WM_MDIMAXIMIZE, hwnd, 0)
	
	def IsMaximized(self, hwnd):
		b= BOOL()
		user32.SendMessageA(self.Hwnd, WM_MDIGETACTIVE, 0, byref(b))
		return bool(b.value)
	
	def Restore(self, hwnd):
		user32.SendMessageA(self.Hwnd, WM_MDIRESTORE, hwnd, 0)
	
	def Tile(self, flag='vertical'):
		if flag=='vertical': flag= 0			# MDITILE_VERTICAL
		if flag=='horizontal': flag= 1		# MDITILE_HORIZONTAL
		#elif flag=='zorder': flag= 4			# MDITILE_ZORDER	## ??
		WM_MDITILE          = 550
		if not user32.SendMessageA(self.Hwnd, WM_MDITILE, flag, 0):
			raise "could not tile windows"
	
	
	def Cascade(self, skipdisabled=True):
		if skipdisabled: flag= 2	# MDITILE_SKIPDISABLED
		else: flag= 0
		WM_MDICASCADE       = 551
		if not user32.SendMessageA(self.Hwnd, WM_MDICASCADE, flag, 0):
			raise "could not cascade windows"

	def IconArrange(self):
		user32.SendMessageA(self.Hwnd, WM_MDIICONARRANGE, 0, 0)

	def Minimize(self, hwnd): user32.ShowWindow(hwnd, 6)		# SW_MINIMIZE
	
	def IsMinimized(self, hwnd):
		return bool(user32.IsIconic(hwnd))

## TODO
#WM_MDISETMENU
#WM_MDIREFRESHMENU

#****************************************************************

class CLIENTCREATESTRUCT(Structure):
	_fields_ = [("hWindowMenu", HANDLE),
					("idFirstChild", UINT)]

