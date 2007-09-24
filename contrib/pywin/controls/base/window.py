

from wnd.wintypes import (user32, 
													shell32,
													kernel32,
													c_short,
													byref,
													addressof,
													pointer,
													GetLastError,
													POINT,
													create_string_buffer,
													MSG,
													WNDPROC,
													LOWORD,
													HIWORD,
													UINT,
													NMHDR,
													MINMAXINFO,
													LOWORD,
													HIWORD)

from wnd import fwtypes as fw
import atexit
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class _GuiExit(object):
	
	def __init__(self, func=user32.DestroyWindow): 
		self.func=func
		self.Hwnds= []
	
	def Register(self, hwnd): 
		if hwnd in self.Hwnds:
			raise RuntimeError("GUI alreaddy registered: %s" % hwnd)
		self.Hwnds.append(hwnd)
	
	def Unregister(self, hwnd): 
		if hwnd in self.Hwnds:
			self.Hwnds.remove(hwnd)
		else: raise RuntimeError("could not unregister hwnd: %s" % hwnd)
	
	def Close(self):
		if self.Hwnds:
			for i in self.Hwnds:
				self.func(i)
			self.Hwnds= []

_exit= _GuiExit()
atexit.register(_exit.Close)



#class Data(object):
#	def __init__(self):
#		self.hAccelerator = 0					# accelerator tabel
#		self.registeredMessages = []
#		self.Appbar=None						# not supported currently
#		self.dragAcceptFiles=False
#		self.timers= []
#		self.fIsopen= False						# WM_SIZE needs this, not notify the user
																	# unless the gui is open
#		self.Debugger= None
#		self.pWndProc= None
#		self.pOldWndProc = 0
#		self.baseStyle= 0
#		self.userStyle = 0


#********************************************************************
#********************************************************************

class BaseWindow(object):
	
	DefWindowProc=user32.DefWindowProcA
		
	def __init__(self, WindowClass, title, x, y, w, h, *styles):
		
			
		if fw.WND_GUIMAIN:
			raise RuntimeError, "a GUI can only have one main window"
		fw.WND_GUIMAIN = True
		
		#self.Data= 	Data()
			
		
		self._base_hAccelerator = 0					# accelerator tabel
		self._base_registeredMessages = []
		self._base_Appbar=None						# not supported currently
		self._base_dragAcceptFiles=False
		self._base_timers= []
		self._base_hwndDlgMsg= 0			## hwnd for wich 'IsDialogMsg' dispatches
		
		self._base_fIsopen= False		# WM_SIZE needs this, not notify the user
															# unless the gui is open
		self._base_debugger= None
		self._base_guid = None
		self._base_mutext_singleinst = None
							
		# styles
		iStyles = self.ParseStyles(styles)
		#self.Data.baseStyle = iStyles[3]
		#self.Data.clientStyle = iStyles[4]
			
		self._base_style = [iStyles[3], iStyles[4]]	# base/clientstyle
				
		# check if debugging is requested and set the windowproc
		#self.Data.Debugger= fw.GetDebugger(self.Data.baseStyle, self.Msg)
		#self.Data.pWndProc= 	WNDPROC(self._base_WndProc)
		
		self._base_debugger= fw.GetDebugger(iStyles[3], self.Msg)
		self._base_pWndProc= 	WNDPROC(self._base_WndProc)
		self._base_pOldWndProc = 0
		
		# register the class and create the window
		WindowClass.SetWindowProc(self._base_pWndProc)
		if x==None: x=2147483648		# CW_USEDEFAULT
		if y==None: y=2147483648		# CW_USEDEFAULT
		if w==None: w=2147483648	# CW_USEDEFAULT
		if h==None: h=2147483648	# CW_USEDEFAULT
		WindowClass.Register()		## XP doesn't like atoms being passed !!
		self.Hwnd=user32.CreateWindowExA(
							iStyles[1],WindowClass.lpszClassName,
							title,iStyles[0],x,y,w,h,0,0,0,0)
		if not self.Hwnd:
			raise RuntimeError, "could not create window"
		# make shure window is destroyed if an error occurs
		# before the gui is up and running
		_exit.Register(self.Hwnd)
		#ExitHandler._RegisterGuiExitFunc(user32.DestroyWindow, self.Hwnd)
			
		self._base_hwndDlgMsg= self.Hwnd

				

	
	#--------------------------------------------------------------------
	def _base_WndProc(self, hwnd, msg, wp, lp):
		try:	
			
			#if msg==fw.WND_WM_NOTIFY: 
			#	print 1
			#	return 0
			
			if self._base_debugger:
				result= self._base_debugger.HandleMessage(hwnd, msg, wp, lp)
				if result: self.onMSG(hwnd, "debug", *result)
					
			
			
			result= fw.IsReflectMessage(hwnd, msg, wp, lp)
			if result != None: return result
			
			result = self.onMESSAGE(hwnd, msg, wp, lp)
			if result !=None: return result
			
						
			
			
			#-------------------------------------------------------------------
			if msg==43:		# WM_DRAWITEM
				## ownerdraw menus
				self.onMSG(hwnd, "drawitem", 0, DRAWITEMSTRUCT.from_address(lp))
				return 1

			elif msg==44:	# WM_MEASUREITEN
				## ownerdraw menus
				self.onMSG(hwnd, "measureitem", 0, MEASUREITEMSTRUCT.from_address(lp))
				return 1
			
			
			elif msg==2:	 # WM_DESTROY
				self.onMSG(hwnd, "close", 0, 0)
				# catch errors ??
				# use atexit ??
				for i in self._base_timers: user32.KillTimer(hwnd, i)
				user32.PostQuitMessage(0)
				return 0

			elif msg==self.Msg.WM_NCDESTROY:
				self.onMSG(hwnd, "destroy", 0, 0)
				if self._base_Appbar:
					self._base_Appbar.Close()
				if self._base_dragAcceptFiles:
					shell32.DragAcceptFiles(self.Hwnd, 0)
				if self._base_mutext_singleinst:
					kernel32.CloseHandle(self._base_mutext_singleinst)
				return 0
				
			elif msg==self.Msg.WM_QUERYENDSESSION:
				ENDSESSION_LOGOFF = 2147483648
				if lp==ENDSESSION_LOGOFF: fLogoff=True
				else: fLogoff=False
				if self.onMSG(hwnd, "close", "endsession", fLogoff)==False:
					return 1
					#return 0	## have to test on this
				return 1
			
			elif msg==self.Msg.WM_ENDSESSION:
				if wp:
					ENDSESSION_LOGOFF = 2147483648
					if lp==ENDSESSION_LOGOFF: fLogoff=True
					else: fLogoff=False
					self.onMSG(hwnd, "destroy", "endsession", fLogoff)
				return 0
				
			elif msg==self.Msg.WM_CONTEXTMENU:
				self.onMSG(hwnd, "contextmenu",0,  0)
				return 0
			
			
			# settings change ----------------------------------------------------------------------------------------
			# WM_DEVICECHANGE
			# WM_DEVMODECHANGE
			# WM_FONTCHANGE
			# WM_COMPACTING
			# WM_INPUTLANGUAGECHANGE
			# WM_PALETTECHANGED
			# WM_POWERBROADCAST
			# WM_QUERYNEWPALETTE
			# WM_TIMECHANGE
			# WM_USERCHANGED win9x only

			# WM_SETTINGCHANGE !!
			# WM_SYSCOLORCHANGE !! forward to all common controls
				
			# lp=(bits/pixel, cxScreen, cyScreen)

			
			elif msg==self.Msg.WM_DISPLAYCHANGE:
				self.onMSG(hwnd, "displaychanged", wp,  (LOWORD(lp), HIWORD(lp)))
				return 0
							
			elif msg==self.Msg.WM_SYSCOLORCHANGE:
				# forward to all child windows
				for i  in self.ChildWindows():
					self.SendMessage(i, msg, wp, lp)
				self.onMSG(hwnd, "syscolorchanged", 0, 0)
				return 0	
					
			elif msg==self.Msg.WM_FONTCHANGE:
				self.onMSG(hwnd, "fontchanged", 0,  0)
				return 0
			
			if msg== fw.WND_WM_TRAY:
				if lp==self.Msg.WM_MOUSEMOVE:
					self.onMSG(hwnd, "traymessage", wp, "mousemove")
				elif lp==self.Msg.WM_LBUTTONDOWN:
					self.onMSG(hwnd, "traymessage", wp, "lmbdown")
				elif lp==self.Msg.WM_LBUTTONUP:
					self.onMSG(hwnd, "traymessage", wp, "lmbup")
				elif lp==self.Msg.WM_LBUTTONDBLCLK:
					self.onMSG(hwnd, "traymessage", wp, "lmbdouble")
				elif lp==self.Msg.WM_RBUTTONDOWN:
					self.onMSG(hwnd, "traymessage", wp, "rmbdown")
				elif lp==self.Msg.WM_RBUTTONUP:
					self.onMSG(hwnd, "traymessage",  wp, "rmbup")
				elif lp==self.Msg.WM_RBUTTONDBLCLK:
					self.onMSG(hwnd, "traymessage", wp, "rmbdouble")
				return 0
					
			elif msg==self.Msg.WM_TIMER:
				self.onMSG(hwnd, "timer", wp, lp)
				if self.IsOwnTimer(wp):
					return 0
		       							
			elif msg==278: # WM_INITMENU
				self.onMSG(hwnd, "menu open", wp, 0)
			
			elif msg==279:		# WM_INITMENUPOPUP
				if HIWORD(lp):	# system menu
					pass
				else:					# menu
					self.onMSG(hwnd, "menu popup", wp, 0)
					
			elif msg==273:	# WM_COMMAND 
				if not lp:
					if HIWORD(wp):	# accelerator message
						self.onMSG(hwnd, "menu choice", user32.GetMenu(self.Hwnd), (LOWORD(wp), True))
					else:						# menu message
						self.onMSG(hwnd, "menu choice", user32.GetMenu(self.Hwnd), (LOWORD(wp), False))
										
			elif msg==5:		# WM_SIZE
				if self._base_fIsopen:
					self.onMSG(hwnd, "size", 0, [0, 0, LOWORD(lp), HIWORD(lp)])
				
			elif msg==self.Msg.WM_ENTERSIZEMOVE:
				self.onMSG(self.Hwnd, "entersizemove", 0, 0)
				
			elif msg==self.Msg.WM_EXITSIZEMOVE:
				self.onMSG(self.Hwnd, "exitsizemove", 0, 0)
								
			elif msg==self.Msg.WM_MOUSELEAVE:
				self.onMSG(self.Hwnd, "mouseleave", wp, lp)
				
			elif msg==self.Msg.WM_GETMINMAXINFO:
				self.onMSG(hwnd, "getminmaxinfo", 0, MINMAXINFO.from_address(lp))
				return 0
											
			elif msg==self.Msg.WM_HOTKEY:
				self.onMSG(hwnd, "hotkey", wp, (HIWORD(lp), LOWORD(lp)))
				
			elif msg==self.Msg.WM_SETFOCUS:
				self.onMSG(hwnd, "setfocus", wp, 0)
			
			elif msg==self.Msg.WM_KILLFOCUS:
				self.onMSG(hwnd, "killfocus", wp, 0)
			
			elif msg==self.Msg.WM_LBUTTONUP:
				self.onMSG(hwnd, "lmbup", wp, 0)
			
			elif msg==self.Msg.WM_LBUTTONDOWN:
				self.onMSG(hwnd, "lmbdown", wp, 0)
				
			elif msg==self.Msg.WM_DROPFILES:
				pt=POINT()
				fClient= shell32.DragQueryPoint(wp, byref(pt))
				if fClient: fClient= True
				else: fClient= False
				## get the number of dropped files
				n= shell32.DragQueryFile(wp, -1, None, 0)
				p = create_string_buffer(260 +1)		# MAX_PATH +1 or not... damn C
				out=[]
				for i in range(n):
					shell32.DragQueryFile(wp, i, p, 260 +1)	#  MAX_PATH
					out.append(p.value)
				shell32.DragFinish(wp)
				self.onMSG(self.Hwnd, "droppedfiles", (pt.x, pt.y, fClient), out)
			
			
			#---------------------------------------------------
			# drag window by its client area
			# thanks to catch22.net 
			elif msg==132:		# WM_NCHITTEST
				if self.GetStyleL('basestyle') & self.Style.WS_BASE_MOVE:
					hittest = self.DefWindowProc(hwnd, msg, wp, lp)
					if hittest == 1:		#HTCLIENT 
						return 2				# HTCAPTION
					return hittest	
			

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
			
			
			# framework messages -------------------------------------------------------
			
			elif msg==fw.WND_WM_NOTIFY:
								
				if wp==fw.WND_NM_MENU:
					mnu= fw.WND_MENU.from_address(lp)
					if nmu.type==fw.MNUT_MENU:
						if nmu.code==fw.MNUF_REMOVE:
							# clears a menu from the menu bar, does not free it.
							## TODO: better not raise here, leave it to caller
							if user32.GetMenu(self.Hwnd)==nmu.handle:
								if not user32.SetMenu(self.Hwnd, 0):
									raise RuntimeError, "could not remove menu"
								if not user32.DrawMenuBar(self.Hwnd):
									raise RuntimeError, "could not redraw menu bar"
								return 1
					elif nmu.type==fw.MNUT_ACCEL:
						# remove accelerator table
						if nmu.code==fw.MNUF_REMOVE:
							self._base_hAccelerator = 0
							return 1
					return 0
				
				elif wp== fw.WND_NM_DLGDISPATCH:
					if lp: self._base_hwndDlgMsg = lp
					else: self._base_hwndDlgMsg = self.Hwnd
				
				elif wp== fw.WND_NM_GETGUID:
					guid= self.GetGUID()
					if guid:
						fw.CopyData(self.Hwnd, lp, fw.WND_CD_GUID, guid, 1)
						return 1
					return 0
				
				
				elif wp== fw.WND_NM_ISMAINWINDOW:
					return fw.WND_MSGRESULT_TRUE
				
				elif wp== fw.WND_NM_ISFWWINDOW:
					return fw.WND_MSGRESULT_TRUE
				
				
				
				elif wp==fw.WND_NM_EXCEPTION:
					nexc= fw.WND_EXCEPTION.from_address(lp)
				
					if nexc.type==fw.EXC_EXCEPTION:
						fw.WND_ERRORLEVEL += 1
						if fw.WND_ERRORLEVEL > fw.WND_MAXERROR:
							print "\nmax error (%s) exceeded, taking down the gui" % fw.WND_MAXERROR
							raise fw.ChildwindowExit()
					
					elif nexc.type==fw.EXC_FATAL:
						print "\nsome fatal exception occured, taking down the gui"
						raise fw.ChildwindowExit()
											
					elif nexc.type==fw.EXC_MAXERROR:
						print "\nmax error (%s) exceeded, taking down the gui" % fw.WND_MAXERROR
						raise fw.ChildwindowExit()
												
					return 0
				return 0
					
											
			#--------------------------------------------------
			# pass registered messages 
			else:	
				if msg in self._base_registeredMessages:
					result=self.onMSG(hwnd, msg, wp, lp)
					if result !=None: return result
			
			# default
			return self.DefWindowProc(hwnd, msg, wp, lp)
		
		
		
		except Exception, details:
			if isinstance(details, fw.ChildwindowExit):
				# child window should have printed exc already
				import sys
				sys.exit()
			
			else:
				import traceback
				traceback.print_exc()
				fw.WND_ERRORLEVEL += 1
				if fw.WND_ERRORLEVEL > fw.WND_MAXERROR:
					user32.PostQuitMessage(fw.EXC_MAXERROR)
					#print "max error (%s) exceeded, taking down the GUI" % fw.WND_MAXERROR
					import sys
					sys.exit()
				return self.DefWindowProc(hwnd, msg, wp, lp)
			
	
	#--------------------------------------------------------------------

	def onMESSAGE(self, hwnd,message,wparam,lparam):
		"""global message handler for the window.
		Overwrite in derrived classes."""
		pass
		#if message==16:	# WM_CLOSE
		#	self.Close()
				
		
	def onMSG(self, hwnd,message,wparam,lparam):
		"""Message handler for user.
		Overwrite in derrived classes."""
		pass
	
	
	#----------------------------------------------------------------------
	
	
	def Run(self, show='normal'):
		try: show=['hidden','normal', 'minimized','maximized'].index(show)
		except:
			try: range(4)[show]
			except:	raise ValueError, "invalid flag: %s" % show			
		
		# run the messageloop
		self._base_fIsopen= True
		self.onMSG(self.Hwnd, "create", 0, 0)	# looks like take it out
		user32.ShowWindow(self.Hwnd, show)
		user32.UpdateWindow(self.Hwnd)
		GM, TM, DM, TACC=(user32.GetMessageA,
									user32.TranslateMessage,
									user32.DispatchMessageA,
									user32.TranslateAcceleratorA) 
		msg = MSG()
				
		pMsg = pointer(msg)
		if self.GetStyleL('basestyle') & self.Style.WS_BASE_DIALOGLIKE:
			IsDialogMessage=user32.IsDialogMessageA
			#
			# TODO
			#
			# would be better to call when all childwindows have been created
			# but thats a thing we don't know
			# needs some heavier testing, we'll see
			#
			self.onMSG(self.Hwnd, "open", 0, 0)
			_exit.Unregister(self.Hwnd)
			while GM( pMsg, 0, 0, 0) > 0:
				if not IsDialogMessage(self._base_hwndDlgMsg, pMsg):
					if self._base_hAccelerator:
						if not TACC(self.Hwnd, self._base_hAccelerator, pMsg):
							TM(pMsg)
					else:
						TM(pMsg)
					DM(pMsg)
		
				
		else:
			self.onMSG(self.Hwnd, "open", 0, 0)
			_exit.Unregister(self.Hwnd)
			while GM( pMsg, 0, 0, 0) > 0:
				if self._base_hAccelerator:
					if not TACC(self.Hwnd, self._base_hAccelerator, pMsg):
						TM(pMsg)
				else:
					TM(pMsg)
				DM(pMsg)
		
		# PostQuitMessage(erorcode) --> wParam WM_QUIT
		# 0 = OK
		# -1 = RuntimeError
		# -2 = MAXERROR exceeded
		#return c_short(msg.wParam).value
	
	

	#def Close(self, exitcode=0):
	#	"""Closes the window."""
	#	user32.PostQuitMessage(exitcode)	
	


#***************************************************************************
#***************************************************************************

class window_styles:
	"""window styles"""	
	WS_OVERLAPPED      = 0
	WS_MINIMIZE        = 536870912
	WS_VISIBLE         = 268435456
	WS_DISABLED        = 134217728
	WS_CLIPCHILDREN    = 33554432
	WS_MAXIMIZE        = 16777216
	WS_CAPTION         = 12582912 
	WS_BORDER          = 8388608
	WS_DLGFRAME        = 4194304
	WS_VSCROLL         = 2097152
	WS_HSCROLL         = 1048576
	WS_SYSMENU         = 524288
	WS_SIZEBOX           =  262144	# WS_THICKFRAME 
	WS_MINIMIZEBOX     = 131072
	WS_MAXIMIZEBOX     = 65536
	WS_THICKFRAME      = 262144		## not documented
	WS_OVERLAPPEDWINDOW= WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
	
	
	WS_EX_DLGMODALFRAME   = 1
	WS_EX_TOPMOST         = 8
	WS_EX_ACCEPTFILES     = 16
	WS_EX_TRANSPARENT     = 32
	WS_EX_TOOLWINDOW      = 128
	WS_EX_SMCAPTION       = 128
	WS_EX_WINDOWEDGE      = 256
	WS_EX_CLIENTEDGE      = 512
	WS_EX_CONTEXTHELP     = 1024
	WS_EX_RIGHT           = 4096
	WS_EX_LEFT            = 0
	WS_EX_RTLREADING      = 8192
	WS_EX_LTRREADING      = 0
	WS_EX_LEFTSCROLLBAR   = 16384
	WS_EX_RIGHTSCROLLBAR  = 0
	WS_EX_STATICEDGE      = 131072
	WS_EX_CONTROLPARENT   = 65536
	WS_EX_APPWINDOW       = 262144
	WS_EX_LAYERED         = 524288
	WS_EX_NOINHERITLAYOUT = 1048576
	WS_EX_LAYOUTRTL       = 4194304
	WS_EX_COMPOSITED      = 33554432
	WS_EX_NOACTIVATE      = 134217728

	WS_POPUP           = 2147483648
	WS_POPUPWINDOW     = WS_POPUP | WS_BORDER | WS_SYSMENU

window_styles.__dict__.update(fw.wnd_window_styles.__dict__)	


class window_msgs: 
	"""window messages"""
	WM_NULL = 0
	WM_CREATE = 1	
	WM_DESTROY  = 2
	WM_MOVE = 3
	WM_SIZE = 5
	WM_ACTIVATE = 6
	WM_SETFOCUS = 7	
	WM_KILLFOCUS = 8		
	WM_ENABLE           = 10	
	WM_SETREDRAW = 11
	WM_SETTEXT          = 12		
	WM_GETTEXT          = 13		
	WM_GETTEXTLENGTH    = 14	 
	WM_PAINT = 15		
	WM_CLOSE = 16
	WM_QUERYENDSESSION = 17
	WM_QUIT = 18
	WM_QUERYOPEN = 19
	WM_ERASEBKGND = 20	
	WM_SYSCOLORCHANGE = 21
	WM_ENDSESSION = 22
	WM_SHOWWINDOW = 24
	WM_WININICHANGE = 26
	WM_SETTINGCHANGE = WM_WININICHANGE
	WM_DEVMODECHANGE = 27
	WM_ACTIVATEAPP = 28
	WM_FONTCHANGE = 29
	WM_TIMECHANGE = 30
	WM_CANCELMODE = 31
	WM_SETCURSOR = 32
	WM_MOUSEACTIVATE = 33
	WM_CHILDACTIVATE = 34
	WM_QUEUESYNC = 35
	WM_GETMINMAXINFO = 36
	WM_PAINTICON = 38
	WM_ICONERASEBKGND = 39
	WM_NEXTDLGCTL = 40
	WM_SPOOLERSTATUS = 42
	WM_DRAWITEM         = 43
	WM_MEASUREITEM = 44
	WM_DELETEITEM = 45
	WM_VKEYTOITEM = 46
	WM_CHARTOITEM = 47
	WM_SETFONT = 48			
	WM_GETFONT = 49	
	WM_SETHOTKEY = 50
	WM_GETHOTKEY = 51
	WM_QUERYDRAGICON = 55
	WM_COMPAREITEM = 57
	WM_GETOBJECT = 61
	WM_COMPACTING = 65
	WM_COMMNOTIFY = 68
	WM_WINDOWPOSCHANGING = 70
	WM_WINDOWPOSCHANGED = 71
	WM_POWER = 72
	WM_COPYDATA = 74
	WM_CANCELJOURNAL = 75
	WM_NOTIFY = 78
	WM_INPUTLANGCHANGEREQUEST = 80
	WM_INPUTLANGCHANGE = 81
	
	WM_HELP = 83
	WM_USERCHANGED = 84
	WM_NOTIFYFORMAT = 85
	WM_CONTEXTMENU      = 123		
	WM_STYLECHANGING = 124
	WM_STYLECHANGED = 125
	WM_DISPLAYCHANGE = 126
	WM_GETICON = 127
	WM_SETICON = 128
	WM_NCCREATE = 129		
	WM_NCDESTROY = 130
	WM_NCCALCSIZE = 131
	WM_NCHITTEST        = 132	
	WM_NCPAINT = 133
	WM_NCACTIVATE = 134
	WM_GETDLGCODE = 135
	WM_SYNCPAINT = 136
	WM_NCMOUSEMOVE = 160
	WM_NCLBUTTONDOWN = 161
	WM_NCLBUTTONUP = 162
	WM_NCLBUTTONDBLCLK = 163
	WM_NCRBUTTONDOWN = 164
	WM_NCRBUTTONUP = 165
	WM_NCRBUTTONDBLCLK = 166
	WM_NCMBUTTONDOWN = 167
	WM_NCMBUTTONUP = 168
	WM_NCMBUTTONDBLCLK = 169
	
	WM_KEYDOWN = 256
	WM_KEYUP            = 257	
	WM_CHAR             = 258	
	WM_DEADCHAR = 259
	WM_SYSKEYDOWN = 260
	WM_SYSKEYUP         = 261	
	WM_SYSCHAR = 262
	WM_SYSDEADCHAR = 263
	WM_KEYLAST = 264
		
	#WM_INITDIALOG = 272
	WM_COMMAND = 273
	WM_SYSCOMMAND = 274
	WM_TIMER = 275
	WM_HSCROLL = 276
	WM_VSCROLL = 277
	WM_INITMENU = 278
	WM_INITMENUPOPUP = 279
	WM_MENUSELECT = 287
	WM_MENUCHAR = 288
	WM_ENTERIDLE = 289
	#WM_MENURBUTTONUP = 290	# menus
	#WM_MENUDRAG = 291
	#WM_MENUGETOBJECT = 292
	WM_UNINITMENUPOPUP = 293
	#WM_MENUCOMMAND = 294
	WM_CHANGEUISTATE    = 295
	WM_UPDATEUISTATE    = 296
	WM_QUERYUISTATE     = 297
	#
	WM_CTLCOLORMSGBOX = 306
	WM_CTLCOLOREDIT = 307
	WM_CTLCOLORLISTBOX = 308
	WM_CTLCOLORBTN = 309
	WM_CTLCOLORDLG = 310
	WM_CTLCOLORSCROLLBAR = 311
	WM_CTLCOLORSTATIC = 312
	#
	WM_MOUSEMOVE        = 512		
	WM_LBUTTONDOWN = 513	
	WM_LBUTTONUP = 514	 
	WM_LBUTTONDBLCLK = 515		
	WM_RBUTTONDOWN = 516	 
	WM_RBUTTONUP = 517		
	WM_RBUTTONDBLCLK = 518	
	WM_MBUTTONDOWN = 519		 
	WM_MBUTTONUP = 520
	WM_MBUTTONDBLCLK = 521
	WM_MOUSEWHEEL  = 522
	
	WM_PARENTNOTIFY = 528
	WM_ENTERMENULOOP = 529
	WM_EXITMENULOOP = 530
	WM_NEXTMENU = 531
	WM_SIZING = 532
	WM_CAPTURECHANGED = 533
	WM_MOVING = 534
	WM_POWERBROADCAST = 536
	WM_DEVICECHANGE = 537
		
	WM_ENTERSIZEMOVE = 561
	WM_EXITSIZEMOVE = 562
	WM_DROPFILES = 563
	WM_MOUSELEAVE        = 675
	
	WM_CUT = 768
	WM_COPY = 769
	WM_PASTE = 770
	WM_CLEAR = 771
	WM_UNDO = 772
	
	WM_QUERYNEWPALETTE = 783
	WM_PALETTEISCHANGING = 784
	WM_PALETTECHANGED = 785
	WM_HOTKEY = 786
	WM_PRINT = 791
	WM_PRINTCLIENT = 792
	WM_USER = 1024
	WM_APP = 32768	

window_msgs.__dict__.update(fw.wnd_window_msgs.__dict__)







