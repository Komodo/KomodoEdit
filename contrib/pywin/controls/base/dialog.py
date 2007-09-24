
"""
TODO
	- disallow multiple creation of the same dialog
		propsheets bypass the Run method-- how to stop them ??

	- 'dialoglike' keyboard handling for standalone dialogs (modeless)
		have to run a dispatch loop for this

"""

from wnd.wintypes import (user32,
												shell32,
												WNDPROC,
												MINMAXINFO,
												LOWORD,
												HIWORD, 
												NMHDR, 
												WORD, 
												POINT, 
												byref, 
												create_string_buffer)

from wnd import fwtypes as fw
import gc
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

PSM_QUERYSIBLINGS   =     1024 + 108		# WM_USER # propertysheets


#********************************************************************************
#********************************************************************************
	
class BaseDialog(object):
	
	DefDlgProc=user32.DefDlgProcA
	
	
	def __init__(self, title, x, y, w, h, *styles):
		
		self.Hwnd= 0
		self.Msg = dialog_msgs
		self.Style = dialog_styles

		#self.Hwnd = 0
		self._base_registeredMessages = []
		self._base_dragAcceptFiles=False
		self._base_dialogMode='modeless'	## in respect to property sheets
																			## 
		
		self._base_timers= []
		self._base_debugger= None
		self._base_guid = None
								
				
		# styles		
		iStyles = self.ParseStyles(styles)
		self._base_style = [iStyles[3], iStyles[4]]	# base/clientstyle
				
		# check if debugging is requested and set the windowproc
		self._base_debugger= fw.GetDebugger(iStyles[3], self.Msg)
		self._base_pWndProc= 	WNDPROC(self._base_WndProc)
		self._base_pOldWndProc = 0
				
		# create a small template
		clss = 0
		helpId = 0
		p =[1,0xFFFF, LOWORD(helpId),
		HIWORD(helpId), LOWORD(iStyles[1]),
		HIWORD(iStyles[1]), LOWORD(iStyles[0]),
		HIWORD(iStyles[0]),0,x,y,w,h,0,clss] 
		p += map(ord, title) + [0]
		if len(p) % 2:
			p.append(0)
		self._base_dlgTemplate = buffer((WORD * len(p))(*p))[:]
		
	
		
			
	
	#---------------------------------------------------------------------
	
	# for uniformity reasons
	def DefWindowProc(self, Hwnd, msg, wp, lp):
		return self.DefDlgProc(Hwnd, msg, wp, lp)
	
	
	def _base_WndProc(self, hwnd, msg, wp, lp):
		

		try:
						
			if self._base_debugger:
					result= self._base_debugger.HandleMessage(hwnd, msg, wp, lp)
					if result: self.onMSG(hwnd, "debug", *result)
						
			result= fw.IsDialogReflectMessage(hwnd, msg, wp, lp, self._base_dialogMode)
			if result != None: return result						
			
					
			if msg == self.Msg.WM_INITDIALOG:
				self.Hwnd= hwnd
				result= self.onINITDIALOG(hwnd, msg, wp, lp)
				if result != None: return result
				return 0
			
			result=self.onMESSAGE(hwnd, msg, wp, lp)
			if result != None: return result
				
			
			
			#---------------------------------------------------------------------------
						
			elif msg==self.Msg.WM_ACTIVATE:
				#WA_INACTIVE    = 0
				#WA_ACTIVE      = 1
				#WA_CLICKACTIVE = 2
								
				if self.GetStyleL('basestyle') & self.Style.WS_BASE_DIALOGLIKE:
					## tell the mainwindow to dispatch/clear IsDialogMessage 					
					
					hwndMain= self.GetMainWindow()
					if hwndMain:
						if LOWORD(wp) & 3:	# activated					
							
							self.SendMessage(hwndMain, fw.WND_WM_NOTIFY, fw.WND_NM_DLGDISPATCH, self.Hwnd)
						else:
							self.SendMessage(hwndMain, fw.WND_WM_NOTIFY, fw.WND_NM_DLGDISPATCH, 0)	# clear	
				
				
			
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
			
			
			
			## property sheets
			elif msg==PSM_QUERYSIBLINGS:
				result= self.onMSG(hwnd, "prop_querysiblings", wp, lp)
				if result: return result
				return 0
				
			
			elif msg==self.Msg.WM_SYSCOLORCHANGE:
				## forward to all child windows
				for i  in self.ChildWindows():
					self.SendMessage(i, msg, wp, lp)
				self.onMSG(hwnd, "syscolorchanged", 0, 0)
				return 0	
			
			elif msg==278: # WM_INITMENU
				self.onMSG(hwnd, "menu open", wp, 0)
			
			elif msg==279:		# WM_INITMENUPOPUP
				if HIWORD(lp):	# system menu
					pass
				else:					# menu
					self.onMSG(hwnd, "menu popup", wp, 0)
		

			elif msg==self.Msg.WM_COMMAND:
				
				if self._base_dialogMode=='modal':
					## filter out default IDS for 'modal' dialog boxes
					# we can not set ID of the def button to IDOK
					# so we have to explicitely test for it
					if wp==1 or lp==self.GetDefButton():		# IDOK
						result=self.onMSG(hwnd,"command", 0,"ok")
						if result==False:
							pass
						elif isinstance(result, (int, long)):
							self.Close(result)
						else: self.Close()
						return 0
					if wp==2:	# IDCANCEL
						result=self.onMSG(hwnd,"command", 0, "cancel")
						if result==False: 
							pass
						elif isinstance(result, (int, long)):
							self.Close(result)
						else: self.Close()
						return 0
								
				#if lp:
					# WM_COMMAND from non framework controls or controls wich
					# have disabled the message reflect flag, so let them splip
				
				if not lp:					
					code= HIWORD(wp)
					if code==0:						# menu message
						self.onMSG(hwnd, "menu choice", user32.GetMenu(self.Hwnd), (LOWORD(wp), False))
					elif code==1:	# accelerator message
						self.onMSG(hwnd, "menu choice", user32.GetMenu(self.Hwnd), (LOWORD(wp), True))
						
						
			elif msg==fw.WND_WM_TRAY:
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
			
			elif msg==5:		#WM_SIZE     = 5
				self.onMSG(hwnd, "size", 0, [0, 0, LOWORD(lp), HIWORD(lp)])
						
			elif msg==self.Msg.WM_ENTERSIZEMOVE:
				self.onMSG(self.Hwnd, "entersizemove", 0, 0)
				
			elif msg==self.Msg.WM_EXITSIZEMOVE:
				self.onMSG(self.Hwnd, "exitsizemove", 0, 0)
				
			elif msg==self.Msg.WM_GETMINMAXINFO:
				self.onMSG(hwnd, "getminmaxinfo", 0, MINMAXINFO.from_address(lp))
				return 0
				
			elif msg==self.Msg.WM_SETFOCUS:
				self.onMSG(hwnd, "setfocus", wp, 0)
			
			elif msg==self.Msg.WM_KILLFOCUS:
				self.onMSG(hwnd, "killfocus", wp, 0)
				
			elif msg==self.Msg.WM_TIMER:
				self.onMSG(hwnd, "timer", wp, lp)
					
				
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
				self.onMSG(self.Hwnd, "droppedfiles", (pt.x, pt.y, clientarea), out)
			
			
			# drag window by its client area ---------------------------------------------------
			## does not work for dialogs ??
			##
			#elif msg==132:		# WM_NCHITTEST
			#	if self.GetStyleL('basestyle') & self.Style.WS_BASE_MOVE:
			#		hittest = self.DefDlgProc(hwnd, msg, wp, lp)
			#		if hittest == 1:		#HTCLIENT 
			#			return 2				# HTCAPTION
			#		return hittest	
				
				
							
			## TODO
			## WM_ENDSESSION (...)	??
			##
			elif msg==self.Msg.WM_CLOSE:
				self.onMSG(hwnd, "close", 0, 0)
			
			elif msg==self.Msg.WM_DESTROY:
				for i in self._base_timers: user32.KillTimer(hwnd, i)
				if self._base_dragAcceptFiles:
					shell32.DragAcceptFiles(self.Hwnd, 0)
					self._base_dragAcceptFiles=False
				
				self.Hwnd= 0
				self.onMSG(hwnd, "destroy", 0, 0)

			
			
			
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
										
				elif wp== fw.WND_NM_GETGUID:
					guid= self.GetGUID()
					if guid:
						fw.CopyData(self.Hwnd, lp, fw.WND_CD_GUID, guid, 1)
						return 1
					return 0
				
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
												
			
			
			else:	
				if msg in self._base_registeredMessages:
					result=self.onMSG(hwnd, msg, wp, lp)
					if result !=None: return result
			
			# default
			return 0

		except Exception, details:
			## TODO
			## If an error in a dialog occurs ther is probabbly no need to quit 
			## the GUI (if there is one). So maybe dialogs should get their own
			## MAX_ERROR and stuff
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
				return 0

	#---------------------------------------------------------------------
		
	def Close(self, result=0):
		if self._base_dialogMode=='modal':
			user32.EndDialog(self.Hwnd, result)
		elif self._base_dialogMode=='modeless':
			user32.DestroyWindow(self.Hwnd)
				
	
	def RunModal(self, parent=None, lp=0):		
		if self.Hwnd: 
			raise RuntimeError("Dialog allreaddy running")
		if not parent: parent= 0
		else: parent= parent.Hwnd
					
		self._base_dialogMode = 'modal'
		result = user32.DialogBoxIndirectParamA(
							0, self._base_dlgTemplate, parent,
							self._base_pWndProc, lp)
		gc.collect()
		return result

	def RunModeless(self, parent=None, lp=0):
		if self.Hwnd: 
			raise RuntimeError("Dialog allreaddy  running")
		if not parent: parent= 0
		else: parent= parent.Hwnd
		self._base_dialogMode = 'modeless'
		self.Hwnd = user32.CreateDialogIndirectParamA(
								0, self._base_dlgTemplate, parent,
								self._base_pWndProc , lp)
		
			 	
	
	def onINITDIALOG(self, hwnd, msg, wp, lp):
		"""Client handler . Overwrite in derrived 
		client classes."""
		pass
	def onMESSAGE(self, hwnd, msg, wp, lp):
		"""Client handler for messages. Overwrite in derrived 
		client classes."""
		pass
	def onINIT(self, hwnd, msg, wp, lp):
		"""User handler. Overwrite in derrived classes"""
		pass
	
	def onMSG(self, hwnd, msg, wp, lp):
		"""User handler. Overwrite in derrived classes"""
		pass


	def GetTemplate(self):
		return self._base_dlgTemplate

	def GetDlgProc(self):
		return self._base_pWndProc

	def GetMainWindow(self):
		hwndMain= None
		for i in self.ThreadWindows():
			result= self.SendMessage(i, fw.WND_WM_NOTIFY, fw.WND_NM_ISMAINWINDOW, 0)
			if result == fw.WND_MSGRESULT_TRUE: 
				hwndMain= i
				break
		return hwndMain

#***********************************************************************
#***********************************************************************

class BaseDialogFromTemplate(BaseDialog):
	def __init__(self, template, *styles):
				
		
		self.Msg = dialog_msgs
		self.Style = dialog_styles			
		
		self._base_registeredMessages = []
		self._base_dragAcceptFiles=False
		self._base_timers= []
		self._base_debugger= None
		self._base_dialogMode=None
		self._base_style = [0, 0]				# base/clientstyle
		self._base_guid = None
				
		valid_flags=('debug', 'debugall')
		for i in styles:
			if i not in valid_flags:
				raise ValueError("invalid flag: %s" % i)

		self._base_dlgTemplate= template
				
		# check if debugging is requested and set the windowproc
		dbglevel= 0
		if 'debug' in styles:	dbglevel= fw.WS_BASE_DEBUG
		elif 'debugall' in styles:	dbglevel= fw.WS_BASE_DEBUGALL
		self._base_debugger= fw.GetDebugger(dbglevel, self.Msg)
		self._base_pWndProc= 	WNDPROC(self._base_WndProc)
		self._base_pOldWndProc = 0	
		
	
#************************************************************************
# base class for common-dialogs
#************************************************************************

class BaseCommonDialog(BaseDialog):
	
	def __init__(self, mode, *styles):
		self.Msg = dialog_msgs
		self.Style = dialog_styles
		
		# mode= 'modal' / 'modeless'
				
		valid_flags=('debug', 'debugall', 'modal', 'modeless')
		for i in styles:
			if i not in valid_flags:
				raise ValueError("invalid flag: %s" % i)
			
		
		self._base_dialogMode= 'modal' in styles and 'modal' or 'modeless'
				
		self.Hwnd = 0
		
		self._base_registeredMessages = []
		self._base_dragAcceptFiles=False
		self._base_timers= []
		self._base_guid = None
		
		# styles		
		self._base_dialogMode=mode
		self._base_style = [0, 0]				# base/clientstyle
		## enables keyboard handling for 'modeless' common dialogs
		if self._base_dialogMode== 'modeless':
			self._base_style[0] |= self.Style.WS_BASE_DIALOGLIKE
		
		
		# check if debugging is requested and set the windowproc
		dbglevel= 0
		if 'debug' in styles:	dbglevel= fw.WS_BASE_DEBUG
		elif 'debugall' in styles:	dbglevel= fw.WS_BASE_DEBUGALL
		self._base_debugger= fw.GetDebugger(dbglevel, self.Msg)
		self._base_pWndProc= 	WNDPROC(self._base_WndProc)
		self._base_pOldWndProc = 0	
		
		
	def GetTemplate(self):
		return None
	
	
	def Close(self):
		## there is some special processing how to quit common dialogs
		## ChooseColor should be quitted like this:
		#WM_COMMAND
		#IDABORT    = 3
		user32.PostMessageA(self.Hwnd, 273, 3, 3)

	def RunModeless(self, lp=0):
		raise RuntimeError("you can not run a Common Dialog")
	def RunModal(self, lp=0):
		raise RuntimeError("you can not run a Common Dialog")

	

#*****************************************************************		
#*****************************************************************

class dialog_styles:
	"""dialog styles"""
	WS_CHILD = 1073741824
	
	WS_VISIBLE         = 268435456
	WS_OVERLAPPED      = 0
	WS_MINIMIZE        = 536870912
	WS_VISIBLE         = 268435456
	WS_DISABLED        = 134217728
	WS_CLIPSIBLINGS    = 67108864
	WS_CLIPCHILDREN    = 33554432
	WS_MAXIMIZE        = 16777216
	WS_CAPTION         = 12582912 
	WS_BORDER          = 8388608
	WS_DLGFRAME        = 4194304
	WS_VSCROLL         = 2097152
	WS_HSCROLL         = 1048576
	WS_SYSMENU         = 524288
	WS_THICKFRAME      = 262144
	WS_SIZEBOX           = WS_THICKFRAME
	WS_MINIMIZEBOX     = 131072
	WS_MAXIMIZEBOX     = 65536

		
	DS_3DLOOK        = 4
	DS_ABSALIGN      = 1
	DS_SYSMODAL      = 2
	DS_3DLOOK        = 4
	DS_FIXEDSYS      = 8
	DS_NOFAILCREATE  = 16
	DS_LOCALEDIT     = 32 # Edit items get Local storage.
	DS_SETFONT       = 64 # User specified font for Dlg controls
	DS_MODALFRAME    = 128 # Can be combined with WS_CAPTION
	DS_NOIDLEMSG     = 256 # WM_ENTERIDLE message will not be sent
	DS_SETFOREGROUND = 512 # not in win3.1
	DS_CONTROL       = 1024
	DS_CENTER        = 2048
	DS_CENTERMOUSE   = 4096
	DS_CONTEXTHELP   = 8192


dialog_styles.__dict__.update(fw.wnd_window_styles.__dict__)
dialog_styles.prefix += 'DS_',



class dialog_msgs: 
	"""dialog messages"""
	WM_USER = 1024
	
	WM_INITDIALOG       = 272

	DM_GETDEFID      = WM_USER + 0
	DM_SETDEFID      = WM_USER + 1
	DM_REPOSITION    = WM_USER + 2
	DC_HASDEFID      = 21323

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


dialog_msgs.__dict__.update(fw.wnd_window_msgs.__dict__)



