"""
LAST VISITED
	10.04.05


NOTES
	- focus rect got messed up in heavier resizing actions. 
		Switched ro background an hilight color setting instead.


TODO
	- 'feedbackbar' may not get erased completely under certain circumstances 

"""

from wnd.wintypes import (user32,
												comctl32,
												gdi32,
												POINT,									
												byref,
												DWORD,
												RECT,
												LOWORD,
												HIWORD,
												c_short,
												WORD)

from wnd.controls import blank
from wnd.controls import windowclass
from wnd.res.cursors import cursors1
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# we are no global class, so every classname registered has to be unique/process 
N_SPLITTERS= 0

class Styles: 
	WS_CLIENT_HORZ= 0
	WS_CLIENT_VERT= 1
	WS_CLIENT_FEEDBACKBAR= 2
	
#class Msgs: pass


#**************************************************************************
#**************************************************************************

class Splitter(blank.Blank):

	def __init__(self, parent, x, y, w, h, *styles):	
		
		self._custom_fDrag  =  False
		self._custom_dragPoint = None
		self._custom_colors  =  None			# [colorbk, colorhi]
		self._custom_pageSize = None
		self._custom_oldpos= None

				
		
		# preregister a class
		global N_SPLITTERS
		N_SPLITTERS += 1
		classname="splitter-%s" % N_SPLITTERS
		wc = windowclass.WindowClass()
		wc.SetClassName(classname)
		if 'vert' in styles: 
			style, cur= 'vert', cursors1.splitterwe()
		else: 
			style, cur= 'horz', cursors1.splitterns()
		wc.SetCursor(cur)
		wc.SetBackground('window')
		
		# create the window
		blank.Blank.__init__(self, parent, wc, x, y, w, h)
		# set styles after updating custom styles
		self.Style.__dict__.update(Styles.__dict__)
		self.SetStyle(*styles)
		
	
	#--------------------------------------------------------------------------------------	
	# message handler
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
			
		## draging

		if msg==self.Msg.WM_MOUSEMOVE:
			pt=POINT(LOWORD(lp), HIWORD(lp))
			if self._custom_fDrag:
				if self._custom_dragPoint:
					style= self.GetStyleL('clientstyle')
					
					if style & self.Style.WS_CLIENT_FEEDBACKBAR:
						## move later on LMBUP
												
						rc= self.GetWindowRect()
						rcNew= rc.Copy()
						rcParent= RECT()
						user32.GetClientRect(self.GetParent(), byref(rcParent))
						rcParent.ClientToScreen(self.GetParent())
						
						if style & self.Style.WS_CLIENT_VERT:
							## +2 ??
							rcNew.Offset(c_short(pt.x).value - self._custom_dragPoint.x, 0)
						else:
							rcNew.Offset(0, c_short(pt.y).value - self._custom_dragPoint.y)

						if rcNew.InRect(rcParent):
							if self._custom_oldpos:
								self._custom_DrawFeedbackBar(*self._custom_oldpos)
							
							rcInters= rcNew.Intersect(rc)
							if not rcInters.IsEmpty():
								rcNew= rcNew.Subtract(rcInters)
							
							x, y, w, h= rcNew.ToSize()
							self._custom_DrawFeedbackBar(x, y, w, h)
							self._custom_oldpos= x, y, w, h
						
							
					
					elif  style & self.Style.WS_CLIENT_VERT:
						self._custom_MoveSplitter(c_short(pt.x).value	-self._custom_dragPoint.x, 0)
					else:
						self._custom_MoveSplitter(0, pt.y-self._custom_dragPoint.y)
				else:
					self._custom_dragPoint= pt
					self._custom_dragPoint.x=c_short(self._custom_dragPoint.x).value
					# if the mouse leaves the window to the left x will be 65535 (SHORT(-1)) or lower

		
		elif msg==self.Msg.WM_LBUTTONDOWN:
			self.SetMouseCapture()
			self._custom_fDrag=True
			
		elif msg==self.Msg.WM_LBUTTONUP:
			self.ReleaseMouseCapture()
			
			## move 'feedbackbar' splitter
			style= self.GetStyleL('clientstyle')
			if  style & self.Style.WS_CLIENT_FEEDBACKBAR:
				if self._custom_dragPoint:
					pt= POINT(*self.GetCursorPos())
					pt.ScreenToClient(self.GetParent())
					
					## final erasing of the last poisition brfore actually moving
					if self._custom_oldpos:
						self._custom_DrawFeedbackBar(*self._custom_oldpos)
					
					if  style & self.Style.WS_CLIENT_VERT:
						
						self.DragSplitter(pt.x - self._custom_dragPoint.x)
					else:
						self.DragSplitter(pt.y - self._custom_dragPoint.y)
									
			# reset				
			self._custom_fDrag=False
			self._custom_dragPoint=None
			self._custom_oldpos= None
		
		
		#-----------------------------------------------------------
		
		elif msg==self.Msg.WM_MOUSEACTIVATE:
			self.SetFocus()
		
		elif msg==self.Msg.WM_SETFOCUS:
			self._custom_SetHilight(True)
			self.onMSG(hwnd, "setfocus", wp, lp)
			return 0

		elif msg==self.Msg.WM_KILLFOCUS:
			self._custom_SetHilight(False)
			self.onMSG(hwnd, "killfocus", wp, lp)
			return 0
				
		elif msg==self.Msg.WM_GETDLGCODE:
			return 1		# DLGC_WANTARROWS for keyboard interface
		
  		elif msg==self.Msg.WM_KEYDOWN:
			if wp==33:	self.PageUp()				# VK_PGUP	
			elif wp==34: self.PageDown()		# VK_PGDN 
			elif wp==37: self.StepUp()				# VK_LEFT
			elif wp == 38: self.StepLeft()			# VK_UP
			elif wp == 39: self.StepRight()		# VK_RIGHT
			elif wp == 40:self.StepDown()		# VK_DOWN
			return 0
			
		
		elif msg==2:	# WM_DESTROY
			# nothing to cleanup here
			pass
		
								
	#------------------------------------------------------------------------------------
	# helper methods
	
	def _custom_DrawFeedbackBar(self, x, y, w, h):
		
				
		hDC= user32.GetDC(0)
		hBr= None
		hBm= None
		
		if hDC:
			pat= (WORD*8)(0x00aa, 0x0055, 0x00aa, 0x0055, 
										0x00aa, 0x0055, 0x00aa, 0x0055)
			hBm = gdi32.CreateBitmap(8, 8, 1, 1, byref(pat))
			if hBm:
				hBr = gdi32.CreatePatternBrush(hBm)
				if hBr:
					hbrushOld = gdi32.SelectObject(hDC, hBr)
					gdi32.PatBlt(hDC, x, y, w, h, 5898313)	# PATINVERT   = 5898313
					gdi32.SelectObject(hDC, hbrushOld)

		if hBm:
			gdi32.DeleteObject(hBm)
		if hBr:
			gdi32.DeleteObject(hBr)
		if hDC:
			user32.ReleaseDC(0, hDC)
			
	
	
	def _custom_SetHilight(self, Bool):
		if self._custom_colors:
			if Bool:
				hBrush= gdi32.CreateSolidBrush(self._custom_colors[1])
			else:
				hBrush= gdi32.CreateSolidBrush(self._custom_colors[0])
					
			GCL_HBRBACKGROUND = -10
			oldBrush = user32.SetClassLongA(self.Hwnd, GCL_HBRBACKGROUND, hBrush)
			gdi32.DeleteObject(oldBrush) # # make shure
			self.RedrawClientArea()
	
		
	def _custom_MoveSplitter(self, offsX, offsY):
		# moves the splitter, taking care it is not moved outside	the 
		# parent windows bounds.
		#
		# Return value: True if the splitter was actually moved. False otherwise
		#
		hwndParent= self.GetParent()
		rcCli= RECT()
		user32.GetClientRect(hwndParent, byref(rcCli))
		rc= self.GetWindowRect()
		rc.ScreenToClient(hwndParent)
		rc1= rc.Copy()
		rc.Offset(offsX, offsY)
		if offsX:
			if rc.left < 0: 
				rc.right= rc.right-rc.left
				rc.left= 0
			elif  rc.right > rcCli.right: 
				rc.Offset(rcCli.right-rc.right, 0)
				if rc.left <0:
					rc.right= rc.right-rc.left
					rc.left= 0
		if offsY:
			if rc.top < 0: 
				rc.bottom= rc.bottom-rc.top
				rc.top= 0
			elif  rc.bottom > rcCli.bottom: 
				rc.Offset(0, rcCli.bottom-rc.bottom)
				if rc.top < 0:
					rc.bottom= rc.bottom-rc.top
					rc.top= 0
		if rc1.left != rc.left or rc1.top != rc.top:
			if self.onMSG(self.Hwnd, "move", 0, rc) != False:
				self.SetWindowPos(rc.left, rc.top)
				self.onMSG(self.Hwnd, "moved", 0, 0)
				return True
		return False
	
		
	#---------------------------------------------------------------
	# splitter methods
		
	# TODO test
			
	def SetPageSize(self, n):
		if isinstance(n, (int, long)) or n==None:
			self._custom_pageSize= n
		else: raise ValueError("int or long expected: %s" % n)
	
	
	def DragSplitter(self, newpos):
		rc= self.GetWindowRect()
		rc.ScreenToClient(self.GetParent())
		if self.GetStyleL('clientstyle') & self.Style.WS_CLIENT_VERT:
			return self._custom_MoveSplitter(newpos-rc.left, 0)
		else:
			return self._custom_MoveSplitter(0, newpos-rc.top)
		
	def PageUp(self):
		isVert=  bool(self.GetStyleL('clientstyle') & self.Style.WS_CLIENT_VERT)
		if self._custom_pageSize == None:
			rc=self.GetWindowRect()
			if isVert:
				self._custom_pageSize= rc.right-rc.left
			else:
				self._custom_pageSize= rc.bottom-rc.top
		if isVert:
			return self.OffsetSplitter(-(self._custom_pageSize))
		else: return  self.OffsetSplitter(-(self._custom_pageSize))
			
	def PageDown(self):
		isVert=  bool(self.GetStyleL('clientstyle') & self.Style.WS_CLIENT_VERT)
		if self._custom_pageSize == None:
			rc=self.GetWindowRect()
			if isVert:
				self._custom_pageSize= rc.right-rc.left
			else:
				self._custom_pageSize= rc.bottom-rc.top
		if isVert:
			return self.OffsetSplitter(self._custom_pageSize)
		else: return  self.OffsetSplitter(self._custom_pageSize)
		
	def StepDown(self): return self.OffsetSplitter(1)	
	def StepUp(self):	return self.OffsetSplitter(-1)
	def StepRight(self): return self.OffsetSplitter(1)
	def StepLeft(self): return self.OffsetSplitter(-1)
		
		
	def OffsetSplitter(self, offset):
		if offset:
			if self.GetStyleL('clientstyle') & self.Style.WS_CLIENT_VERT:
				return self._custom_MoveSplitter(offset, 0)
			else:
				return self._custom_MoveSplitter(0, offset)
		
	def SetColors(self, colorBk, colorHi):
		if colorBk==None and  colorHi==None:
			self._custom_colors= None
			COLOR_MSGBOX     = 4		## ??
			color= user32.GetSysColor(COLOR_MSGBOX)
			self._custom_colors= color, color
			self._custom_SetHilight(False)
			self._custom_colors= None
		else:		
			try: DWORD(colorBk)
			except: raise ValueError("invalid color bk: %s" % colorBk)
			try: DWORD(colorHi)
			except: raise ValueError("invalid color hi: %s" % colorHi)
			self._custom_colors= colorBk, colorHi
			if self.HasFocus():
				self._custom_SetHilight(True)
			else: 
				self._custom_SetHilight(False)
	
	


