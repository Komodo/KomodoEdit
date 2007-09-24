

from wnd.wintypes import (user32, 
													shell32,
													byref, 
													create_string_buffer,
													WNDPROC,
													POINT,
													NMHDR,
													UINT,
													DLGCODES,
													LOWORD,
													HIWORD)
from wnd import fwtypes as fw
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class BaseControl(object):
	
	
	_base_DefWindowProc=user32.DefWindowProcA
	
	def __init__(self, Parent, NameOrClass, title, x, y, w, h, *styles):
			
			
		self._base_subclassable = False
		self._base_registeredMessages = []
		self._base_dragAcceptFiles=False
		self._base_timers= []
		self._base_debugger= None
		self._base_fMsgReflect= 1
		self._base_guid = None
		
		
		# ...all the style parsing
		# default  WS_CHILD|WS_VISIBLE|WS_CLIPCHILDREN|WS_CLIPSIBLINGS
		iStyles = self.ParseStyles(styles, 					
								style=1073741824|268435456|33554432|67108864)
		self._base_style = [iStyles[3], iStyles[4]]	# base/clientstyle
		
		# check if debugging is requested and set the windowproc
		self._base_debugger= fw.GetDebugger(iStyles[3], self.Msg)
		self._base_pWndProc= 	WNDPROC(self._base_WndProc)
		self._base_pOldWndProc = 0
		
		# check if we have to register the class
		subclass = iStyles[3] & self.Style.WS_BASE_SUBCLASS 
		if isinstance(NameOrClass, str):
			classname = NameOrClass
			if not subclass:	# systemdefined class the user can subclass
				self._base_subclassable = True
		else:
			NameOrClass.SetWindowProc(self._base_pWndProc)
			try: 
				r=NameOrClass.Register()
				classname= NameOrClass.lpszClassName
			except: raise RuntimeError("invalid class" % NameOrClass)
			subclass=False	# --> ignore style 'subclass'

		# create the control
		self.Hwnd=user32.CreateWindowExA(
							iStyles[1],classname,title,iStyles[0],x,y,w,h,
							Parent.Hwnd,fw.ID.New(),0,0)
		if not self.Hwnd: raise RuntimeError("could not create window")
		
		# subclass the control
		if subclass:
			self._base_pOldWndProc = user32.SetWindowLongA(self.Hwnd, -4, self._base_pWndProc)
			if not self._base_pOldWndProc:
				raise RuntimeError("could not subclass window")

		# set extended comctl styles
		if iStyles[2]: 
			self.SetStyleL('extendedstyle', iStyles[2])
		
	
	#----------------------------------------------------------------------
	# call OldProc if subclassed, DefProc if not
	
	def DefWindowProc(self, hwnd, msg, wp, lp):
		if self._base_pOldWndProc:
			return self.CallWindowProc(self._base_pOldWndProc,
																	hwnd, msg, wp, lp)
		return self._base_DefWindowProc(hwnd, msg, wp, lp)
	
	
	#------------------------------------------------------------------------
	def _base_WndProc(self, hwnd, msg, wp, lp):
		
		try:				
			
			if self._base_debugger:
				result= self._base_debugger.HandleMessage(hwnd, msg, wp, lp)
				if result: self.onMSG(hwnd, "debug", *result)
			
			
			result= fw.IsReflectMessage(hwnd, msg, wp, lp)
			if result != None: return result
			
			
			
			result = self.onMESSAGE(hwnd, msg, wp, lp)
			
			# have to process here, coos default retval is 0 from childwindow handlers
			if msg==fw.WND_WM_NOTIFY:
				if wp== fw.WND_NM_GETGUID:
					guid= self.GetGUID()
					if guid:
						fw.CopyData(self.Hwnd, lp, fw.WND_CD_GUID, guid, 1)
						return 1
					return 0
			
			if result !=None: return result

			
			
					# copydata -------------------------------------------------------
			
			elif msg== self.Msg.WM_COPYDATA:
				
				result = fw.HandleCopyData(hwnd, msg, wp, lp)
				if result == None: 
					return 0
				if HIWORD(result[0]):	# reserved for framework, must be mislead
					return 0
				if self.onMSG(hwnd, "copydata", wp, (result[0], result[1]))== False:
					return 0
				return 1
			
			#---------------------------------------------------
			
			## forward to all childwindows
			if msg==self.Msg.WM_SYSCOLORCHANGE:
				for i  in self.ChildWindows():
					self.SendMessage(i, msg, wp, lp)
				self.onMSG(hwnd, "syscolorchanged", 0, 0)
				return 0	
			
			elif msg==self.Msg.WM_GETDLGCODE:
				# request dlgCode from:
				# 1. the client handler of the control
				# 2. DefWindowProc
				# ...call user with the result
				dlgCode =0
				result= self.onMESSAGE(hwnd, msg, wp,lp)
				if result == None:
					if self._base_pOldWndProc:
						dlgCode = self.CallWindowProc(
													self._base_pOldWndProc,
													hwnd, msg, wp, lp)
				else:
					dlgCode=result
				out=[]
				for sz, value in DLGCODES.items():
					if dlgCode & value: out.append(sz)
				result= self.onMSG(hwnd, "getdlgcode", 0, out)
				if result != None:
					flag=0
					for i in result:
						try: flag |=DLGCODES[i]
						except: raise "invalid dialogcode: %s" % i
					return flag
				return dlgCode
				#return 0	# just to make shure
						
							
			
	
			
			
						
			
			elif msg==self.Msg.WM_DROPFILES:
				pt=POINT()
				clientarea=shell32.DragQueryPoint(wp, byref(pt))
				if clientarea: clientarea=True
				else: clientarea=False
				# get the number of dropped files
				n=shell32.DragQueryFile(wp, -1, None, 0)
				MAX_PATH=260
				p = create_string_buffer(MAX_PATH)
				out=[]
				for i in range(n):
					shell32.DragQueryFile(wp, i, p, MAX_PATH)
					out.append(p.value)
				shell32.DragFinish(wp)
				self.onMSG(self.Hwnd, "droppedfiles", 
										(pt.x, pt.y, clientarea), out)
	   
			elif msg==self.Msg.WM_TIMER:
				self.onMSG(hwnd, "timer", wp, lp)
				## do not return 0; pass it to DefWindowProc to enshure default processing
				## Listview header, for example, user timer messages
				if self.IsOwnTimer(wp):
					return 0
			
			elif msg==self.Msg.WM_MOUSELEAVE:
				self.onMSG(self.Hwnd, "mouseleave", 0, 0)
			
			elif msg==self.Msg.WM_DESTROY:
				
				ID= user32.GetWindowLongA(self.Hwnd, -12)		# GWL_ID
				if ID:
					try:
						fw.ID.Recycle(ID)
					except: pass
				
				if self._base_dragAcceptFiles:
					shell32.DragAcceptFiles(self.Hwnd, 0)
				# catch errors ??
				# use atexit ??
				for i in self._base_timers: user32.KillTimer(hwnd, i)
												
				
			#--------------------------------------------------
			# pass registered messages 
			if msg in self._base_registeredMessages:
				result=self.onMSG(hwnd, msg, wp, lp)
				if result !=None: return result
		
			
			# default
			return self.DefWindowProc(hwnd, msg, wp, lp)
				
		
		
		
		except :
			exc= fw.EXC_EXCEPTION
			import traceback
			traceback.print_exc()
			# let the parent handle the details
			toplevel=self.GetParent()
			exc= fw.WND_EXCEPTION(hwnd, exc)
			self.SendMessage(toplevel, 
												fw.WND_WM_NOTIFY,
												fw.WND_NM_EXCEPTION, 
												byref(exc))	
			return user32.DefWindowProcA(hwnd, msg, wp, lp)
		
		
	#----------------------------------------------------------------------
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		"""Global message handler for the control.
		Overwrite"""
		
		pass
	
	def onMSG(self, hwnd, msg, wp, lp):
		"""Message handler for the user.
		Overwrite in"""
		pass
	
#***************************************************	
#***************************************************

class ControlFromHandle(BaseControl):
	_base_DefWindowProc=user32.DefWindowProcA
	
	def __init__(self, hwnd, *styles):
				
		valid_flags=('debug', 'debugall', 'subclass', 'nosubclass')
		for i in styles:
			if i not in valid_flags:
				raise "invalid flag: %s" % i
			
		self.Hwnd=hwnd
		self._base_style = [0, 0]	# base/clientstyle
		
		self._base_registeredMessages = []
		self._base_subclassable = True
		self._base_dragAcceptFiles=False
		self._base_timers= []
		self._base_debugger= None
		self._base_fMsgReflect= 1
		self._base_guid = None
		
		# set the windowproc
		self._base_pWndProc= 0
		self._base_pOldWndProc = 0
		if 'nosubclass' in styles:
			self._base_subclassable = False
		
		else:
			## leaks for MDI childwindows if setup with 'nosubclass' ??
			self._base_pWndProc= 	WNDPROC(self._base_WndProc)
			
			# check if debugging is requested and set the windowproc
			dbglevel= 0
			if 'debug' in styles:	dbglevel= fw.WS_BASE_DEBUG
			elif 'debugall' in styles:	dbglevel= fw.WS_BASE_DEBUGALL
			self._base_debugger= fw.GetDebugger(dbglevel, self.Msg)
			
			if 'subclass' in styles:
				self.Subclass()
				self._base_subclassable = False




#******************************************************************
#******************************************************************

class control_styles:
	"""control styles"""
	WS_POPUP           = 2147483648
	
	WS_GROUP = 131072
	WS_TABSTOP = 65536
	WS_VISIBLE = 268435456
	WS_DISABLED = 134217728
	WS_CHILD = 1073741824
	WS_CLIPCHILDREN    = 33554432
	WS_CLIPSIBLINGS    = 67108864
	WS_HSCROLL = 1048576
	WS_VSCROLL = 2097152
	WS_BORDER          = 8388608
	WS_EX_ACCEPTFILES = 16
	WS_EX_CLIENTEDGE = 512
	WS_EX_MDICHILD = 64
	WS_EX_CONTROLPARENT   = 65536
	
		
	#WS_SYSMENU         = 524288
	#WS_POPUPWINDOW     = WS_POPUP | WS_BORDER | WS_SYSMENU
control_styles.__dict__.update(fw.wnd_control_styles.__dict__)	
	

class control_msgs:
	"""control messages"""
	WM_APP              = 32768
	
	WM_CREATE = 1		
	WM_DESTROY = 2		
	WM_MOVE     = 3
	WM_SIZE     = 5
	WM_SETFOCUS = 7	
	WM_KILLFOCUS = 8		
	WM_ENABLE           = 10	
	WM_SETREDRAW = 11
	WM_SETTEXT          = 12		
	WM_GETTEXT          = 13		
	WM_GETTEXTLENGTH    = 14	 
	WM_PAINT = 15			
	WM_CLOSE = 16
	WM_ERASEBKGND = 20		
	WM_SYSCOLORCHANGE = 21
	WM_SHOWWINDOW = 24
	WM_SETCURSOR = 32
	WM_MOUSEACTIVATE = 33
	WM_DRAWITEM         = 43
	WM_MEASUREITEM      = 44
	WM_SETFONT = 48			
	WM_GETFONT = 49			
	WM_WINDOWPOSCHANGING = 70
	WM_WINDOWPOSCHANGED  = 71
	WM_COPYDATA = 74
	WM_NOTIFY = 78
	WM_CONTEXTMENU      = 123		
	WM_STYLECHANGING    = 124
	WM_STYLECHANGED     = 125
	WM_NCCREATE = 129		
	WM_NCDESTROY = 130
	WM_NCCALCSIZE       = 131
	WM_NCHITTEST        = 132	
	WM_NCPAINT = 133
	WM_GETDLGCODE = 135
	WM_KEYDOWN = 256		
	WM_KEYUP            = 257	
	WM_CHAR             = 258	
	WM_SYSKEYUP         = 261	
	WM_COMMAND = 273
	WM_TIMER = 275
	WM_HSCROLL = 276
	WM_VSCROLL = 277
	WM_MOUSEMOVE        = 512		
	WM_LBUTTONDOWN = 513	
	WM_LBUTTONUP = 514	 
	WM_LBUTTONDBLCLK = 515		
	WM_RBUTTONDOWN = 516	 
	WM_RBUTTONUP = 517		
	WM_RBUTTONDBLCLK = 518		
	WM_MOUSEWHEEL       = 522
	WM_SIZING           = 532
	WM_CAPTURECHANGED = 533
	WM_MOVING           = 534

	WM_DROPFILES = 563
	WM_MOUSELEAVE        = 675

control_msgs.__dict__.update(fw.wnd_window_msgs.__dict__)

