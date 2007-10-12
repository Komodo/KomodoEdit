
import gc
from wnd import fwtypes as fw
from wnd.wintypes import (user32, 
													gdi32,
													shell32,
													kernel32,
													addressof, 
													byref,
													sizeof,
													pointer,
													WINFUNCTYPE, 
													GetLastError,
													WinError,
													RECT,
													POINT,
													INT,
													c_long,
													c_ulong,
													c_ushort,
													HANDLE, 
													LPARAM,
													create_string_buffer,
													MAKELONG,
													MAKEWORD,
													LOBYTE, 
													HIBYTE, 
													HIWORD, 
													LOWORD, 
													SIZE,
													PAINTSTRUCT,
													FLASHWINFO)	
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
HT_FLAGS = [		# WM_NCHITTEST et al
		'nowhere','client','caption','sysmenu','size',
		'menu','hscroll','vscroll','minbutton','maxbutton','left',
		'right','top','topleft','topright','bottom','bottomleft',
		'bottomright','border','object','close','help','error',
		'transparent']


"""*****************************************************************************
Creates a name postfixed with either the curent desktop name
the current sesion id or the current user domain

This applies to NT systems only. For win9x systems the name is returned
unchanged. If something goes wrong the name is returnd unchanged.

flag can be: 'desktop', 'session' or 'trustee'


code is adopted from:
	http://www.flounder.com/nomultiples.htm

*****************************************************************************"""
def CreateExclusionName(name, flag):
	from wnd.api import winos
	if winos.IsNT():

		if flag=='desktop':
			## create a name exclusive to the current desktop
			#UOI_NAME     = 2
			hDesk= user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
			
			dwLen= c_ulong()
			user32.GetUserObjectInformationA(hDesk, 2, None, 0, byref(dwLen))
			p = create_string_buffer('', size=dwLen.value)
			if user32.GetUserObjectInformationA(hDesk, 2, p, dwLen.value, byref(dwLen)):
				name = '%s-%s' % (name, p.value)
			user32.CloseDesktop(hDesk)
			return name

		elif flag== 'session':
			## create a name exclusive to the current session
			from wnd.api import privleges
			try:
				st= privleges.GetTokenStats(None)
				name = '%s-%s' % (name, st.AuthenticationId)
			except: pass
			return name
		
		elif flag == 'trustee':
			## create a name exclusive to the current, well trustee that is.  
			import os
			domain= os.getenv('USERDOMAIN')
			if domain:
				return '%s-%s' % (name, domain)
		
	# default
	return name	


#***********************************************************************************
#***********************************************************************************

ENUMWINDOWSPROC = WINFUNCTYPE(INT, HANDLE, LPARAM)

class _HandleList(object):
	def __init__(self):
		self._pEnumProc = ENUMWINDOWSPROC(self._EnumProc)
		self._enum_result = []
			
	def HandleList(self, flag=None):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		user32.EnumWindows(self._pEnumProc, flag)
		return self._enum_result
	
	def ChildWindows(self, hwnd, flag=None):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		user32.EnumChildWindows(hwnd, self._pEnumProc, flag)
		return self._enum_result
		
	def ThreadWindows(self, hwnd, flag):
		if flag=='excludehidden': flag= 1
		elif flag== 'excludevisible': flag= 2
		else: flag= 0
		self._enum_result = []
		threadId = user32.GetWindowThreadProcessId(hwnd, 0)
		user32.EnumThreadWindows(threadId, self._pEnumProc, flag)
		return self._enum_result
		
	def _EnumProc(self, hwnd, lp):
		if lp== 1: 
			if not user32.IsWindowVisible(hwnd): return 1
		elif lp== 2:
			if user32.IsWindowVisible(hwnd): return 1
		self._enum_result.append(hwnd)
		return 1

_EnumWindows= _HandleList()
#**************************************************

class _CommonMethods:
		
	CallWindowProc=user32.CallWindowProcA
	SendMessage = user32.SendMessageA
	PostMessage = user32.PostMessageA
					
	
	## NEW METHOD
	#********************************************************************
	# Helper method to reflect a message to a control sending it
	#
	# The control will receive a WND_MSGREFLECT mesage with wParam
	# set to the hwnd of the caller and lParam set to the address of a
	# MSGREFLECT structure.
	# The control the message is send to should set the 'fReturn' member
	# to 1 to indicate that the return value is to be returned.
	# If its 0 this method calls DefWindowProc.
	#
	# This mechanism enshures default processing for anonymous 
	# system classes ASAP
	#
	#*******************************************************************
	
	
	def GetGUID(self):
		return self._base_guid
		
	def SetGUID(self, guid):
		self._base_guid= guid
	
	def ThreadWindows(self, flag=None):
		return _EnumWindows.ThreadWindows(self.Hwnd, flag)
	
	def ChildWindows(self, flag=None):
		return _EnumWindows.ChildWindows(self.Hwnd)
	
	def WalkGui(self, hwnd=None, topdown=True):
		# get top level window
		if hwnd==None:
			hwndParent= user32.GetParent(self.Hwnd)
			if not hwndParent: hwnd= self.Hwnd
			while hwndParent:
				hwnd= hwndParent
				hwndParent= user32.GetParent(hwndParent)
		
		children= [i for i in  _EnumWindows.ChildWindows(hwnd)	 \
							if user32.GetParent(i)==hwnd]
		if topdown:
			yield hwnd, children
		for i in children:
			for x in self.WalkGui(i):
				yield x
		if not topdown:
			yield hwnd, children
		
	def DeferWindows(self, *windows):
				
		handle= user32.BeginDeferWindowPos(len(windows))
		if handle:
			try:
				for wnd, x, y, w, h in windows:
					flag= 4|16		# SWP_NOZORDER|SWP_NOACTIVATE
					if x==None or y==None:
						flag |= 2		# SWP_NOSIZE 
					if w==None or h==None:
						flag |= 1		# SWP_NOMOVE
					if isinstance(wnd, (int, long)):
						newHandle= user32.DeferWindowPos(handle, wnd, 0, x, y, w, h, flag)
					else:
						newHandle= user32.DeferWindowPos(handle, wnd.Hwnd, 0, x, y, w, h, flag)
					if newHandle: handle= newHandle
					else: raise ''
			except Exception, d:
				user32.EndDeferWindowPos(handle)
				if GetLastError():
					raise WinError(GetLastError())
				else:
					raise RuntimeError, d
			
			if user32.EndDeferWindowPos(handle): return
		raise WinError(GetLastError())

	
	def HideWindows(self, *windows):
	#SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE|SWP_HIDEWINDOWSWP_NOCOPYBITS|WP_HIDEWINDOW
		flag= 1|2|4|128|256|128
		handle= user32.BeginDeferWindowPos(len(windows))
		if handle:
			try:
				for i in windows:
					if isinstance(i, (int, long)):
						newHandle= user32.DeferWindowPos(handle, i, 0, 0,0,0,0, flag)
					else:
						newHandle= user32.DeferWindowPos(handle, i.Hwnd, 0, 0, 0,0,0, flag)
					if newHandle: handle= newHandle
					else: raise ''
			except Exception, d:
				user32.EndDeferWindowPos(handle)
				if GetLastError():
					raise WinError(GetLastError())
				else:
					raise RuntimeError, d
			if user32.EndDeferWindowPos(handle): return
		raise WinError(GetLastError())
	
	def ShowWindows(self, *windows):
		# SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE|SWP_SHOWWINDOW|SWP_NOCOPYBITS|SWP_SHOWWINDOW
		flag= 1|2|4|128|256|64
		handle= user32.BeginDeferWindowPos(len(windows))
		if handle:
			try:
				for i in windows:
					if isinstance(i, (int, long)):
						newHandle= user32.DeferWindowPos(handle, i, 0, 0,0,0,0, flag)
					else:
						newHandle= user32.DeferWindowPos(handle, i.Hwnd, 0, 0,0,0,0, flag)
					if newHandle: handle= newHandle
					else: raise ''
			except Exception, d:
				user32.EndDeferWindowPos(handle)
				if GetLastError():
					raise WinError(GetLastError())
				else:
					raise RuntimeError, d
			if user32.EndDeferWindowPos(handle): return
		raise WinError(GetLastError())
		
		
	#--------------------------------------------------------------------------------------------

	def GetTextExtend(self, *text):
		hDC=user32.GetDC(self.Hwnd)
		if hDC:
			WM_GETFONT          = 49
			hFont = self.SendMessage(self.Hwnd, WM_GETFONT, 0, 0)
			if hFont: hOldFont= gdi32.SelectObject(hDC, hFont)
			sz=SIZE()
			maxW, maxH=0, 0 
			for i in text:
				result= gdi32.GetTextExtentPoint32A(hDC, i, len(i), byref(sz))
				maxW, maxH=max(maxW, sz.cx), max(maxH, sz.cy)
				if not result:
					if hFont: gdi32.SelectObject(hDC, hOldFont)
					user32.ReleaseDC(self.Hwnd, hDC)
					raise RuntimeError("could not retrieve text extend")	 # WinError NT only
			user32.ReleaseDC(self.Hwnd, hDC)
			if hFont: gdi32.SelectObject(hDC, hOldFont)
			return maxW, maxH
			return sz.cx, sz.cy
		else: raise RuntimeError("could not retrieve device context") # WinError NT only

	def GetTextExtendM(self,*text):
		hDC=user32.GetDC(self.Hwnd)
		if hDC:
			WM_GETFONT          = 49
			hFont = self.SendMessage(self.Hwnd, WM_GETFONT, 0, 0)
			if hFont: hOldFont= gdi32.SelectObject(hDC, hFont)
			rc=RECT()
			DT_CALCRECT             = 1024
			maxL, maxT,maxR, maxB=0, 0, 0, 0 
			for i in text:
				
				result= user32.DrawTextA(hDC, i, len(i), byref(rc), DT_CALCRECT)
				maxL,maxT,maxR, maxB=max(maxL, rc.left), max(maxT, rc.top), max(maxR, rc.right), max(maxB, rc.bottom)
				if not result:
					if hFont: gdi32.SelectObject(hDC, hOldFont)
					user32.ReleaseDC(self.Hwnd, hDC)
					raise RuntimeError("could not retrieve text extend") # WinError NT only
			user32.ReleaseDC(self.Hwnd, hDC)
			if hFont: gdi32.SelectObject(hDC, hOldFont)
			return maxR-maxL, maxB-maxT
			return rc.right-rc.left, rc.bottom-rc.top
		else: raise RuntimeError("could not retrieve device context") # WinError NT only
 

 	#-------------------------------------------------------------------------------------------------

	def DragAcceptFiles(self, Bool):
		if Bool:
			if self._base_dragAcceptFiles:
				raise RuntimeError("window alreaddy registered for drag accept files")
			self._base_dragAcceptFiles=True
			shell32.DragAcceptFiles(self.Hwnd, 1)
		else:
			if not self._base_dragAcceptFiles:
				raise RuntimeError("window is not registered for drag accept files")
			self._base_dragAcceptFiles=False	
			shell32.DragAcceptFiles(self.Hwnd, 0)

	def Beep(self, msg='default'):
		try:
			msg={'ok':0,'hand':16,'question':32,'exclamation':48,
					'asterisk':64, 'default':0xFFFFFFFF}[msg]
		except: raise ValueError("invalid beep message: %s" % msg)
		if not user32.MessageBeep(msg): raise WinError(GetLastError())
		
	#----------------------------------------------------------------------
	# timers and events
	
	def NewTimerID(self):
		fw.WND_N_TIMER_IDS += 1
		return fw.WND_N_TIMER_IDS
	
	def GetTimers(self): return self._base_timers
	
	
	def IsOwnTimer(self, ID):
		return ID in self._base_timers
	
	
	def SetTimer(self, ID, nTimeout):
		# TODO: find out about timer ID's used by the system
		#
		if not ID: raise ValueError("invalid ID: %s" % ID)
		if ID in self._base_timers: raise RuntimeError("timer alreaddy set: %s" % ID)
		else: self._base_timers.append(ID)
		if not user32.SetTimer(self.Hwnd, ID, nTimeout, None):
			raise WinError(GetLastError())
		 
	def KillTimer(self, ID):
		# TODO
		#
		# would ne nice to dump all open timers to TrackHandler
		# when the window is closed for a status report
		result= user32.KillTimer(self.Hwnd, ID)
		try: self._base_timers.remove(ID)
		except: raise IndexError, "no such timer registered: %s" % ID
		if not result:		
			raise WinError(GetLastError())
		
			
	def HandleMessage(self, Const):
		self._base_registeredMessages.append(Const)
	
	def SetStyleL(self, offset, style):
		if offset == 'style':
			user32.SetWindowLongA(self.Hwnd, -16, style)	# GWL_STYLE
		elif offset=='exstyle':
			user32.SetWindowLongA(self.Hwnd, -20, style)	# GWL_EXSTYLE
		elif offset=='extendedstyle':
			try: self.SendMessage(self.Hwnd, self.Msg.MSG_SETEXSTYLE, 0, style)
			except: raise AttributeError, "control does not define extended styles"
		elif ofset=='basestyle':
			self._base_style[0] = style
		elif offset=='clientstyle':
			self._base_style[1] = style
		else:
			raise ValueError, "invalid style offset: %s" % offset
		self.RedrawFrame()	## or do some heavy parsing to see if the frame is afected
			
	def GetStyleL(self, offset):
		if offset=='style': 
			return user32.GetWindowLongA(self.Hwnd, -16)	# GWL_STYLE
		elif offset =='exstyle':
			return user32.GetWindowLongA(self.Hwnd, -20)	# GWL_EXSTYLE
		elif offset == 'extendedstyle':
			try: return self.SendMessage(self.Hwnd, self.Msg.MSG_GETEXSTYLE, 0, 0)
			except: raise AttributeError, "control does not define extendedstyles"
		elif offset == 'basestyle':
			return self._base_style[0]
		elif offset == 'clientstyle':
			return self._base_style[1]
		else:
			raise ValueError, "invalid style offset: %s" % offset

	def GetStyle(self):
		
		# retrive all the syles
		style=user32.GetWindowLongA(self.Hwnd, -16)			# GWL_STYLE
		exstyle=user32.GetWindowLongA(self.Hwnd, -20)		# GWL_EXSTYLE
		try:		##
			extendedstyle= self.SendMessage(self.Hwnd, self.Msg.MSG_GETEXSTYLE, 0, 0)
		except: extendedstyle = None
		baseStyle=self.GetStyleL('basestyle')	
		clientStyle=self.GetStyleL('clientstyle')	
			
		out = []
		for name, value in self.Style.__dict__.items():
			if not isinstance(value, (int, long)):
				continue
				
			name = name.split('_', 2)
			if name[0]=='WS':
				if name[1]=='EX':
					if exstyle & value:
						out.append(name[2].lower())
				elif name[1]=='BASE':
					if baseStyle & value:
						out.append(name[2].lower())
				elif name[1]=='CLIENT':
					if clientStyle & value:
						out.append(name[2].lower())
				else:
					if style & value:
						out.append(name[1].lower())
			else:
				if name[1]=='EX':
					if extendedstyle != None:
						if extendedstyle & value:
							out.append(name[2].lower())
				else:
					if style & value==value:
						out.append(name[1].lower())	
		return out
	
	def SetStyle(self, *styles):
				
		style=user32.GetWindowLongA(self.Hwnd, -16)			# GWL_STYLE
		exstyle=user32.GetWindowLongA(self.Hwnd, -20)		# GWL_EXSTYLE
		try: 
			extendedstyle = self.SendMessage(self.Hwnd, self.Msg.MSG_GETEXSTYLE, 0, 0)
			hasExtStyle= True
		except:  extendedstyle, hasExtStyle = 0, False
		
		result = self.ParseStyles(styles, 
										style,
										exstyle,
										extendedstyle,
										self._base_style[0],
										self._base_style[1]
										)
		if result[0] != style:
			user32.SetWindowLongA(self.Hwnd, -16, result[0])		# GWL_STYLE
		if result[1] != exstyle:
			user32.SetWindowLongA(self.Hwnd, -20, result[1])		# GWL_EXSTYLE
		if hasExtStyle:
			if result[2] != extendedstyle:
				self.SendMessage(self.Hwnd, self.Msg.MSG_SETEXSTYLE, 0, result[2])
		self._base_style[0] = result[3]
		self._base_style[1] = result[4]
		self.RedrawFrame()
		
	
	def ParseStyles(self, styles, style=0, exstyle=0, extendedstyle=0, basestyle=0, clientstyle=0):
		prefixes, styledict = self.Style.prefix, self.Style.__dict__
		for i in styles:
			if i[0] in ('-~'): flag, i= i[0], i[1:].upper()	# to be kind strip() ??
			else: flag, i= None, i.upper()						# to be kind strip() ??
			error = True
			for prefix in prefixes:
				stylename = '%s%s' % (prefix, i)
				try:
					value = styledict[stylename]
					offset = 0
					prefix = prefix.split('_', 2)
					
					if prefix[0]=='WS': 
						if prefix[1]=='EX': 
							if flag==None: exstyle |= value
							elif flag=='-': exstyle &= ~value
							elif flag=='~': exstyle ^= value
						elif prefix[1]=='BASE': 
							if flag==None: basestyle |= value
							elif flag=='-': basestyle &= ~value
							elif flag=='~': basestyle ^= value
						elif prefix[1]=='CLIENT': 
							if flag==None: clientstyle |= value
							elif flag=='-': clientstyle &= ~value
							elif flag=='~': clientstyle ^= value
						else:
							if flag==None: style |= value
							elif flag=='-': style &= ~value
							elif flag=='~': style ^= value
					elif prefix[1]=='EX': 
						if flag==None: extendedstyle |= value
						elif flag=='-': extendedstyle &= ~value
						elif flag=='~': extendedstyle ^= value
					else:
						if flag==None: style |= value
						elif flag=='-': style &= ~value
						elif flag=='~': style ^= value
					error=False
					break
				except: pass
			if error: raise ValueError("invalid style: %s" % i.lower())
			# ENDFOR
		# ENDFOR
		## make shure result is c_long (at least for 0, 1, 2), c_ulong is not good enough
		return [c_long(style).value, 
					c_long(exstyle).value, 
					c_long(extendedstyle).value,
					c_long(basestyle).value, 
					c_long(clientstyle).value]
		#return out
	
	# kick out (nonsense)
	#
	#def GetBkColor(self):
	#	hDC = user32.GetDC(self.Hwnd)
	#	clr = gdi32.GetBkColor(hDC)
	#	user32.ReleaseDC(self.Hwnd, hDC)
	#	return clr

	# kick out (nonsense)
	#
	#def GetTextColor(self):
	#	hDC = user32.GetDC(self.Hwnd)
	#	clr = gdi32.GetTextColor(hDC)
	#	user32.ReleaseDC(self.Hwnd, hDC)
	#	return clr
		
	def GetClassName(self):
		p = create_string_buffer(fw.WND_MAX_CLASSNAME+1)
		result= user32.GetClassNameA(self.Hwnd, p,
									fw.WND_MAX_CLASSNAME+1)
		if not result:
			if GetLastError(): raise WinError(GetLastError())
		return p.value

	def BeginPaint(self):
		ps = PAINTSTRUCT()
		hDC = user32.BeginPaint(self.Hwnd, byref(ps))
		if hDC: return hDC, ps
		raise RuntimeError("could not begin paint")	# only NT defines WinError
		
	def EndPaint(self, paintsstruct):
		user32.EndPaint(self.Hwnd, byref(paintsstruct))
	
	def GetFont(self):
		handle = self.SendMessage(self.Hwnd, self.Msg.WM_GETFONT, 0, 0)
		if handle: return handle
				
	def SetFont(self, Font):
		if isinstance(Font, (int, long)):
			self.SendMessage(self.Hwnd, self.Msg.WM_SETFONT, Font, 1)
		else:
			self.SendMessage(self.Hwnd, self.Msg.WM_SETFONT, Font.handle, 1)
	
	def SetRedraw(self, Bool):
		if Bool: self.SendMessage(self.Hwnd, self.Msg.WM_SETREDRAW, 1, 0)
		else: self.SendMessage(self.Hwnd, self.Msg.WM_SETREDRAW, 0, 0)
	
	def RedrawClientArea(self):
		user32.InvalidateRgn(self.Hwnd, 0, 1)
		if not user32.UpdateWindow(self.Hwnd): raise RuntimeError("could not redraw client area")	# only NT defines WinError
	
	def RedrawFrame(self):
		# SWP_FRAMECHANGED|SWP_NOACTIVATE|SWP_NOSIZE|SWP_NOMOVE|		SWP_NOZORDER
		if not user32.SetWindowPos(self.Hwnd, 0, 0, 0, 0, 0, 1|2|4|16|32):
			raise WinError(GetLastError())
		
	def HitTest(self):
		pt = POINT()
		if not user32.GetCursorPos(byref(pt)):
			raise WinError(GetLastError())
		hittest = self.DefWindowProc(self.Hwnd, self.Msg.WM_NCHITTEST, 0, MAKELONG(pt.x, pt.y))
		try: return HT_FLAGS[hittest]
		except: return 'unknown'
	
	def SetCursorPos(self, x, y):
		if not user32.SetCursorPos(x, y): raise WinError(GetLastError())
		
	def GetCursorPos(self):
		pt = POINT()
		if user32.GetCursorPos(byref(pt)): return pt.x, pt.y
		raise WinError(GetLastError())
		
	def SetText(self, text):
		# Todo: Limit text lenght ??"""
		if not user32.SetWindowTextA(self.Hwnd, text):
			raise WinError(GetLastError())

	def GetText(self):
		p=create_string_buffer(self.GetTextLen()+1)
		user32.GetWindowTextA(self.Hwnd, p, sizeof(p))
		return p.value
		# no errorcheck here ("" is an error for the system), leave to caller
	
	def ReleaseMouseCapture(self):
		if not user32.ReleaseCapture(): 
			raise WinError(GetLastError())
		
	def GetClientRect(self):
		rc = RECT()
		if user32.GetClientRect(self.Hwnd, byref(rc)):	return rc
		raise WinError(GetLastError())
		
	def GetWindowRect(self):
		rc = RECT()
		if user32.GetWindowRect(self.Hwnd, byref(rc)): return rc
		raise WinError(GetLastError())
		
	def SetWindowPosAndSize(self, x, y, w, h):
		if not user32.MoveWindow(self.Hwnd, x, y, w, h, 1):
			raise WinError(GetLastError())
	
	def SetWindowPos(self, x, y): 
		# SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
		if not user32.SetWindowPos(self.Hwnd, 0, x, y, 0, 0, 1|4|16):
			raise WinError(GetLastError())

	def SetWindowSize(self, w, h): 
		# SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
		if not user32.SetWindowPos(self.Hwnd, 0, 0, 0, w, h, 2|4|16):
			raise WinError(GetLastError())
			
	def OffsetWindowSize(self, offsetW, offsetH):
		x, y, w, h = self.GetWindowRect().ToSize()
		self.SetWindowSize(w + offsetW, h +offsetH)

	def OffsetWindowPos(self, offsetX, offsetY):
		rc=self.GetWindowRect()
		rc.ScreenToClient(self.GetParent())
		self.SetWindowPos(rc.left + offsetX, rc.top +offsetY)
		 	
	def ChildWindowFromPoint(self, Point, flag='all'):
		if flag=='all': flag= 0										# CWP_ALL
		elif flag=='skipinvisible': flag= 1					# CWP_SKIPINVISIBLE
		elif flag=='skipdisabled': flag= 2				# CWP_SKIPDISABLED
		elif flag=='skiptransparent': flag= 4			# CWP_SKIPTRANSPARENT
		result= user32.ChildWindowFromPointEx(self.Hwnd, Point.x, Point.y, flag)
		if result: return result
	
	
	def GetParent(self): return user32.GetParent(self.Hwnd)
	def IsWindow(self): return bool(user32.IsWindow(self.Hwnd))
	def GetTextLen(self): return user32.GetWindowTextLengthA(self.Hwnd) 
	def SetFocus(self): user32.SetFocus(self.Hwnd)
	def GetFocus(self): return user32.GetFocus()
	def HasFocus(self): return user32.GetFocus()==self.Hwnd
	def HasMouseCapture(self): return user32.GetCapture()==self.Hwnd
	def GetMouseCapture(self): return user32.GetCapture()
	def SetMouseCapture(self): return user32.SetCapture(self.Hwnd)
	def IsVisible(self): return bool(user32.IsWindowVisible(self.Hwnd))
	def Hide(self): user32.ShowWindow(self.Hwnd, 0)
	def Show(self): user32.ShowWindow(self.Hwnd, 1)
	def Enable(self): user32.EnableWindow(self.Hwnd, 1)
	def Disable(self): user32.EnableWindow(self.Hwnd, 0)
	def IsEnabled(self): return bool(user32.IsWindowEnabled(self.Hwnd))

	
#****************************************************

class ControlMethods(_CommonMethods):
	
	# NEW METHOD
	def SetParent(self, NewParent):
		if not NewParent: NewParent= None
		else: NewParent= NewParent.Hwnd
		if not user32.SetParent(self.Hwnd, NewParent):
			raise RuntimeError, "could not set parent"
	
	def Subclass(self):
		if not self._base_pWndProc: raise RuntimeError, "can not subclass control" 
		if self._base_pOldWndProc: raise RuntimeError, "control is alreaddy subclassed" 
		if not self._base_subclassable: raise RuntimeError, "custom classes should not be subclassed" 
		self._base_pOldWndProc = user32.SetWindowLongA(self.Hwnd, -4, self._base_pWndProc)
		if not self._base_pOldWndProc: raise RuntimeError, "could not subclass window"
		
	
	def Close(self):
		if self.IsSubclassed():
			user32.SetWindowLongA(self.Hwnd, -4, self._base_pOldWndProc)
						
		user32.DestroyWindow(self.Hwnd)
		self.__delattr__('Hwnd')
		gc.collect()		## not really required (if I done my job well)

	def GetDlgID(self): return user32.GetDlgCtrlID(self.Hwnd)
	def IsSubclassable(self): return self._base_subclassable
	def IsSubclassed(self): return bool(self._base_pWndProc)

#****************************************************

class WindowMethods(_CommonMethods):
	
	def ForceSingleInstance(self, Bool, restore=True, flag=None):
		
		if Bool:
			if self.GetGUID():
				ERROR_ACCESS_DENIED             = 5
				ERROR_ALREADY_EXISTS            = 183
				
				fRunning= False
				if self._base_mutext_singleinst:
					fRunning= True
				else:
					if flag:
						if flag in ('desktop', 'session', 'trustee'):
							self._base_mutext_singleinst= kernel32.CreateMutexA(None, 0, CreateExclusionName(self._base_guid, flag))
						else: raise ValueError, "invalid flag: %s" % flag
					else:
						self._base_mutext_singleinst= kernel32.CreateMutexA(None, 0, self._base_guid)
					if GetLastError() in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
						kernel32.CloseHandle(self._base_mutext_singleinst)
						self._base_mutext_singleinst= None
						fRunning= True

				if fRunning:
					if restore:
						## take advantage of copydata FindGUID method here
						from wnd.api import copydata
						cd= copydata.CopyData()
						hwnd= cd.FindGUID(self.Hwnd, self.GetGUID())
	
						if hwnd:
							user32.SetForegroundWindow(hwnd)
							if user32.IsIconic(hwnd):
								user32.ShowWindow(hwnd, 9)		# SW_RESTORE
					
					self.Close()
					raise RuntimeError, "single instance enforced"
			else:
				raise RuntimeError, "GUID is required"
		else:
			if self._base_mutext_singleinst:
				kernel32.CloseHandle(self._base_mutext_singleinst)
				self._base_mutext_singleinst= None
	
	
	def SetBkColor(self, Brush):
		oldbrush = user32.SetClassLongA(self.Hwnd, -10, Brush.handle)	 # GCL_HBRBACKGROUND
		gdi32.DeleteObject(oldbrush) # # make shure
		Brush.Release()
		self.RedrawClientArea()
	
	# not documented. Kick out ??
	#
	def Subclass(self, pWindowProc):
		if self._base_pOldWndProc:
			raise RuntimeError, "window is alreaddy subclassed"
		self._base_pOldWndProc = user32.SetWindowLongA(self.hwnd, -4, pWindowProc)
		if not self._base_pOldWndProc:
			raise RuntimeError, "could not subclass window"

	# not documented. Kick out ??
	#
	def RestoreOldProc(self):
		if not self._base_pOldWndProc:
			raise RuntimeError, "window is not subclassed"
		result = user32.SetWindowLongA(self.hwnd, -4, self._base_pOldWndProc)
		self._base_pOldWndProc=None
		return result

	def SetIcon(self, icon):
		GCL_HICON         = -14
		oldicon = user32.SetClassLongA(self.Hwnd, GCL_HICON, icon.handle)
		user32.DestroyIcon(oldicon)	# # just to make shure
		icon.Release()

	# not documented. kick out
	#
	def GetDlgItem(self, ID):
		result = user32.GetDlgItem(self.Hwnd, ID)
		if result: return result
		raise WinError(GetLastError())

	def RegisterHotkey(self, ID, vk, *modkeys):
		flags = {'alt':1,'control':2,'shift':4, 'win':8}
		modkey = 0
		if modkeys:
			for i in modkeys:
				try: modkey |= flags[i]
				except: raise ValueError, "invalid modkey flag: %s" % i
		result = user32.RegisterHotKey(self.Hwnd, ID, modkey, vk)
		if not result: raise WinError(GetLastError())
			
	def UnregisterHotkey(ID):
		if not user32.UnregisterHotKey(self.Hwnd, ID):
			raise WinError(GetLastError())
	
	def SetHotkey(self, vk, *modkeys):
		flags = {'shift':1, 'control':2, 'alt':4, 'extended':8}
		modkey = 0
		if modkeys:
			for i in modkeys:
				try: modkey |= flags[i]
				except: raise ValueError, "invalid modkey flag: %s" % i
		result = self.SendMessage(self.Hwnd, self.Msg.WM_SETHOTKEY, MAKEWORD(vk, modkey), 0)
		if result == -1: raise ValueError, "invalid hotkey"
		elif result == 0:	raise ValueError, "invalid window"
		elif result==2: raise RuntimeError, "hotkey unavailable"
				 
	def GetHotkey(self):
		result = self.sendmessage(self.Hwnd, self.Msg.WM_GETHOTKEY, 0, 0)
		if not result: return None
		VK = LOBYTE(result)
		modkey = HIBYTE(result)
		out = [VK, ]
		if modkey:
			flags = {1:'shift', 2:'control',4:'alt',8:'extended'}
			for i in flags:
				if modkey & i:
					out.append(flags[i])
		return out
			
	def FlashWindow(self, nCount, nTimeout, *flags):
		FLASHW={'stop':0,'caption':1,'tray':2,'all':3,'timer':4,'timernofg':12}
		flag=0
		for i in flags:
			try: flag|=FLASHW[i]
			except:  raise ValueError, "invalid flash flag: %s" % i
		fi=FLASHWINFO()
		fi.hwnd=self.Hwnd
		fi.dwFlags=flag
		fi.uCount=nCount
		fi.dwTimeout=nTimeout
		user32.FlashWindowEx(byref(fi))

	def Minimize(self): user32.ShowWindow(self.Hwnd, 6)		# SW_MINIMIZE
	def IsMinimized(self): return bool(user32.IsIconic(self.Hwnd))
	def Maximize(self): user32.ShowWindow(self.Hwnd, 3)	# SW_MAXIMIZE
	def IsMaximized(self): return bool(user32.IsZoomed(self.Hwnd))
	def Restore(self): user32.ShowWindow(self.Hwnd, 9)		# SW_RESTORE
	def IsTopmost(self): return user32.GetForegroundWindow()== self.Hwnd
	
	def SetForegroundWindow(self, hwnd=None): 
		if not hwnd: hwnd= self.Hwnd
		return bool(user32.SetForegroundWindow(hwnd))
	
	def SetBackgroundWindow(self, hwnd=None):
		if not hwnd: hwnd= self.Hwnd
		HWND_BOTTOM    = 1
		#SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE
		if not user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, 1|2|16):
			raise WinError(GetLastError())
	
	def GetWindow(self, flag):
		## never use GetWindow in a loop !! It will most likely cause infinite recursion
		## not implemented
		#GW_OWNER        = 4
		#GW_CHILD        = 5
		#GW_ENABLEDPOPUP = 6
		try: flag= ('first','last','next','prev').index(flag)
		except: raise ValueError("invalid flag: %s" % flag)
		result= user32.GetWindow(self.Hwnd, flag)
		if result: return result
		if GetLastError():
			raise WinError(GetLastError())

		
	def Close(self): 
		if self.Hwnd:
			user32.DestroyWindow(self.Hwnd)
			self.hwnd= 0

	
						
#****************************************************
class DialogMethods(_CommonMethods):
	
	def GetDlgItem(self, ID):
		result = user32.GetDlgItem(self.Hwnd, ID)
		if result: return result
		raise WinError(GetLastError())

	def SetDefButton(self, Button=None):
		prevHwnd = self.GetDefButton()
		if prevHwnd:
			GWL_STYLE      = -16
			style = user32.GetWindowLongA(prevHwnd, GWL_STYLE)
			style ^= 1 # BS_DEFPUSHBUTTON
			BM_SETSTYLE = 244
			self.SendMessage(prevHwnd, BM_SETSTYLE, style, 1)
		ID = 0
		if Button: ID = Button.GetDlgID()
		self.SendMessage(self.Hwnd, self.Msg.DM_SETDEFID, ID, 0)
				
	def GetDefButton(self):
		DC_HASDEFID      = 21323
		result=self.SendMessage(self.Hwnd, 
								self.Msg.DM_GETDEFID, 0, 0)
		if HIWORD(result) == DC_HASDEFID:
			return user32.GetDlgItem(self.Hwnd, LOWORD(result))
		
	def Minimize(self): user32.ShowWindow(self.Hwnd, 6)		# SW_MINIMIZE
	def IsMinimized(self): return bool(user32.IsIconic(self.Hwnd))
	def Maximize(self): user32.ShowWindow(self.Hwnd, 3)	# SW_MAXIMIZE
	def IsMaximized(self): return bool(user32.IsZoomed(self.Hwnd))
	def Restore(self): user32.ShowWindow(self.Hwnd, 9)		# SW_RESTORE
	def IsTopmost(self): return user32.GetForegroundWindow()== self.Hwnd
	def SetForegroundWindow(self): return			

				

	
