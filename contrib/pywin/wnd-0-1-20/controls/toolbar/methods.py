

from wnd.controls.toolbar.header import *
from wnd.controls.toolbar.messagehandler import ToolbarMsgHandler
from wnd.controls.toolbar.helpers import Snapshot
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# TODO
#
# Limit string size for tooltips to INFOTIPSIZE chars
#
#


class ToolbarMethods(ToolbarMsgHandler):	
	
	#-------------------------------------------------------------------
	# helper methods
	
	
	def _client_GetButton(self, i):
		tbb=TBBUTTON()
		if not self.SendMessage(self.Hwnd, self.Msg.TB_GETBUTTON, i, byref(tbb)):
			raise IndexError("could not retrieve button info")
		return tbb
		
	def _client_GetButtonInfo(self, ID):
		tbi=TBBUTTONINFO()
		tbi.dwMask= TBIF_ALL
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETBUTTONINFO, ID, byref(tbi))
		if result <0: raise RuntimeError("could not retrieve button info")
		return tbi
		
	def _client_SetItem(self, iImage, ID, state,style, lp, title, iItem):
		fStyle=style
		if state:
			# disabled 'ellipses':64,
			# dono what it is and its not retrived in TBBUTTON()
			styles={'check':2,'group':4,'checkgroup':6,
							'dropdown':8,'autosize':16,'noprefix':32}
			states={'checked':1, 'pressed':2,'enabled':4,'hidden':8,
					'grayed':16,'wrap':32,'selected':128}
			fState = 0
			for i in state:
				try:  
					fState |= states[i]
				except: 
					try: fStyle |= styles[i]
					except:	return "invalid state: %s" % i
		else: fState = 4	
		
		iTitle=TBI_NOTEXT
		if title:
			#iTitle=self._client_TruncText(title)
			iTitle=self.SendMessage(self.Hwnd, self.Msg.TB_ADDSTRING, 0, '%s\x00\x00' % title[:self._client_textMax-1])
			if iTitle < 0:
				raise "could not add item string"
		
		tb=TBBUTTON(iImage, ID, fState, fStyle, lp, iTitle)
		if iItem ==-1:
			if not self.SendMessage(self.Hwnd, self.Msg.TB_ADDBUTTONS, 1, byref(tb)):
				return "could not add item"
		else:	
			if not self.SendMessage(self.Hwnd, self.Msg.TB_INSERTBUTTON, iItem, byref(tb)):
				return "could not insert item"
		self.SendMessage(self.Hwnd, self.Msg.TB_AUTOSIZE, 0, 0)
		
	
	def _client_GetSnapshot(self):
		snapshot=[]
		for i in range(self.__len__()):
			tbb=self._client_GetButton(i)
			snapshot.append((tbb, self.GetButtonText(tbb.idCommand)))
		return snapshot
	
	def _client_StringToSnapshot(self, s):
		out=[]
		s=s.split(',')
		if len(s) % 7: raise RuntimeError("invalid snapshot")
		for i in range(0, len(s), 7):
			data=s[i:i+7]
			text=data.pop()
			if len(text) > 127: raise RuntimeError("invalid snapshot")
			for i in text:
				if ord(i) > 126: raise RuntimeError("invalid snapshot")
			out.append((TBBUTTON(*map(int, data)),	text))
		return out

	
	#------------------------------------------------------------------------------------
	# methods
	
	def Button(self, ID, title, *state, **kwargs):
		result = self._client_SetItem(kwargs.get('iImage', 0), ID, state,  TBSTYLE_BUTTON, kwargs.get('lp', 0), title, -1)
		if result: raise RuntimeError(result)
	
	def InsertButton(self, i, ID, title, *state, **kwargs):
		result = self._client_SetItem(kwargs.get('iImage'), ID, state,  TBSTYLE_BUTTON, kwargs.get('lp', 0), title, i)
		if result: raise RuntimeError(result)
	
	
	# NEW METHOD
	def ResetSnapshot(self):
		if self._client_snapshot: self._client_snapshot= None
	
	
	def Write(self):
		if not self._client_snapshot:
			n= self.__len__()
			arr= (TBBUTTON*n)()
			iStrings= []
			for i in range(n):
				arr[i]= self._client_GetButton(i)
				if arr[i].iString > -1:
					iStrings.append(arr[i].iString)
			# map string indexes Toolbar relative to snapshot relative	
			iStrings.sort()
			for i in arr:
				if i.iString > -1:
					i.iString= iStrings.index(i.iString)
			self._client_snapshot= Snapshot(arr)
			for i in arr:
				self._client_snapshot.AddText(i.iString,					\
											self.GetButtonText(i.idCommand))
		return self._client_snapshot.Write()
	
	
	def __len__(self):
			return self.SendMessage(self.Hwnd, self.Msg.TB_BUTTONCOUNT, 0, 0)
		
	def __iter__(self):
		for i in range(self.__len__()):
			yield self._client_GetButton(i).idCommand
	
	def __contains__(self, ID):
		try: 
			self.IDToIndex(ID)
			return True
		except: return False
	
	
	def SetTextMax(self, n): self._client_textMax= n +1
	def GetTextMax(self): return self._client_textMax -1

	
	def IDToIndex(self, ID):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_COMMANDTOINDEX , ID, 0)
		if result < 0: raise IndexError("invalid ID")
		return result
	
	def IndexToID(self, i):
		return self._client_GetButton(i).idCommand
	

	def Separator(self, ID=0):
		result = self._client_SetItem(0, ID, 0, TBSTYLE_SEP, 0, None, -1)
		if result: raise RuntimeError(result	)	

	def InsertSeparator(self, i, ID=0):
		result = self._client_SetItem(0, ID, 0, TBSTYLE_SEP, 0, None, i)
		if result: raise RuntimeError(result	)	
	
	def RemoveButton(self, ID):
		i=self.IDToIndex(ID)
		if not self.SendMessage(self.Hwnd, self.Msg.TB_DELETEBUTTON , i, 0):
			raise RuntimeError("could not remove item")
	
	def MoveButton(self, iOld, iNew):
		if not self.SendMessage(self.Hwnd, self.Msg.TB_MOVEBUTTON,  iOld, iNew):
			raise RuntimeError("colould not move item")

	def SetButtonText(self, ID, text):
		tbi=TBBUTTONINFO()
		tbi.dwMask=TBIF_TEXT
		tbi.pszText =text[:self._client_textMax-1]
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETBUTTONINFO , ID, byref(tbi))
		if result < 0: raise RuntimeError("could not set item text")
		
	
	def GetButtonText(self, ID):
		#try: self.IDToIndex(ID)
		#except: raise IndexError("invalid ID")
		p=create_string_buffer(self._client_textMax)
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETBUTTONTEXT, ID, p)
		if result < 0:
				# can not raise here, separators return -1, too
				#raise "could not retrive item text"
				return ''
		return p.value
	
	
	def SetButtonImage(self, ID, i):
		if not self.SendMessage(self.Hwnd, self.Msg.TB_CHANGEBITMAP,  ID, i):
			raise IndexError("colould not set item image")

	def GetButtonImage(self, ID):
		# self.SendMessage(self.Hwnd, self.Msg.TB_GETBITMAP,  ID, 0)
		# return 8 for separatos on my machine, same in TBBUTTON()
		i=self.IDToIndex(ID)
		tbb = self._client_GetButton(i)
		if tbb.fsStyle & TBSTYLE_SEP: return None
		return tbb.iBitmap
		
	
	def SetButtonLparam(self, ID, lParam):
		tbi=TBBUTTONINFO()
		tbi.dwMask=TBIF_LPARAM
		tbi.lParam =lParam
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETBUTTONINFO , ID, byref(tbi))
		if result < 0: raise RuntimeError("could not set item lParam")
		
	def GetButtonLparam(self, ID):
		try: return self._client_GetButtonInfo(ID).lParam
		except:  raise RuntimeError("could not retrieve item lParam")
		
	
		
	
	def GetButtonSize(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETBUTTONSIZE,  0, 0)
		return LOWORD(result), HIWORD(result)
		
	def SetButtonSize(self, w, h):
		if not self.SendMessage(self.Hwnd,	self.Msg.TB_SETBUTTONSIZE , 0, MAKELONG(w,h)):
			raise RuntimeError("could not set button size")
	
	def GetButtonRect(self, ID):
		rc=RECT()
		if not self.SendMessage(self.Hwnd, self.Msg.TB_GETRECT,  ID, byref(rc)):
			raise RuntimeError("colould not retrieve item rect")
		return rc
		
	
	#------------------------------------------------------------------------------------------
	# all the is- methods
	
	def IsButton(self, ID):
		return not self._client_GetButtonInfo(ID).fsStyle & TBSTYLE_SEP
				
	def IsCheckButton(self, ID):
		return bool(self._client_GetButtonInfo(ID).fsStyle & TBSTYLE_CHECKGROUP==TBSTYLE_CHECK)
		
	def IsCheckGroup(self, ID):
		return bool(self._client_GetButtonInfo(ID).fsStyle & TBSTYLE_CHECKGROUP==TBSTYLE_CHECKGROUP)
			
	def IsDropDown(self, ID):
		return bool(self._client_GetButtonInfo(ID).fsStyle & BTNS_DROPDOWN)
			
	def IsSeparator(self, ID):
		return bool(self._client_GetButtonInfo(ID).fsStyle & TBSTYLE_SEP)
			
	def IsButtonPressed(self, ID):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TB_ISBUTTONPRESSED,  ID, 0))
			
	def PressButton(self, ID):
		if self.IsButtonPressed(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_PRESSBUTTON,  ID, 1):
			raise RuntimeError("could not press button")
		return True
	
	def ReleaseButton(self, ID):
		if not self.IsButtonPressed(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_PRESSBUTTON,  ID, 0):
			raise RuntimeError("could not release button")
		return True
	
	def IsButtonChecked(self, ID):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TB_ISBUTTONCHECKED,  ID, 0))
				
	def CheckButton(self, ID):
		if self.IsButtonChecked(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_CHECKBUTTON,  ID, 1):
			raise RuntimeError("could not check button")
		return True
	
	def UncheckButton(self, ID):
		if not self.IsButtonChecked(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_CHECKBUTTON,  ID, 0):
			raise RuntimeError("could not uncheck button")
		return True
	
	def IsButtonEnabled(self, ID):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TB_ISBUTTONENABLED,  ID, 0))
		
	def EnableButton(self, ID):
		if self.IsButtonEnabled(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_ENABLEBUTTON,  ID, 1):
			raise RuntimeError("could not enable button")
		return True
	
	def DisableButton(self, ID):
		if not self.IsButtonEnabled(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_ENABLEBUTTON,  ID, 0):
			raise RuntimeError("could not disable button")
		return True
		
	def IsButtonVisible(self, ID):
		return not self.SendMessage(self.Hwnd, self.Msg.TB_ISBUTTONHIDDEN , ID, 0)
		
	def HideButton(self, ID):
		state=self.SendMessage(self.Hwnd, self.Msg.TB_GETSTATE, ID, 0)
		if not state & TBSTATE_HIDDEN:
			state |= TBSTATE_HIDDEN
			if not self.SendMessage(self.Hwnd, self.Msg.TB_SETSTATE , ID, state):
				raise RuntimeError("could not hide button")
			return True
		return False

	def ShowButton(self, ID):
		state=self.SendMessage(self.Hwnd, self.Msg.TB_GETSTATE, ID, 0)
		if state & TBSTATE_HIDDEN:
			state &= ~TBSTATE_HIDDEN
			if not self.SendMessage(self.Hwnd, self.Msg.TB_SETSTATE , ID, state):
				raise RuntimeError("could not show button")
			return True
		return False
	
	def GetHilightButton(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETHOTITEM, 0, 0)
		if result < 0: return
		tbb=self._client_GetButton(i).idCommand
				
	def HilightButton(self, ID):
		if self.IsButtonHilighted(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_MARKBUTTON , ID, 1):
			raise RuntimeError("could not hilight Button")
		return True
		
	def UnhilightButton(self, ID):
		if not self.IsButtonHilighted(ID): return False
		if not self.SendMessage(self.Hwnd, self.Msg.TB_MARKBUTTON , ID, 0):
			raise RuntimeError("could not set unhilight button")
		return True
	
	def HilightUnhilightButton(self, ID):
		if not self.UnhilightButton(ID): return self.HilightButton(ID)
		return False
	
	def IsButtonHilighted(self, ID):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TB_ISBUTTONHIGHLIGHTED, ID, 0))
						
	#----------------------------------------------------------------------------------------------------
	
	def Clear(self):
		for i in range(self.__len__()):
			if not self.SendMessage(self.Hwnd, self.Msg.TB_DELETEBUTTON ,0, 0):
				raise RuntimeError("could not remove item: (%s)" % i)
		if self.__len__():
			raise RuntimeError("could not clear toolbar")
		
	def GetItemsSize(self):
		sz=SIZE()
		if not self.SendMessage(self.Hwnd, self.Msg.TB_GETMAXSIZE,  0, byref(sz)):
			raise RuntimeError("could not retrieve items size")
		return sz.cx, sz.cy
	
	def Customize(self): self.SendMessage(self.Hwnd, self.Msg.TB_CUSTOMIZE, 0, 0)
			
	def ItemHittest(self, x, y):
		pt=POINT(x, y)
		result= self.SendMessage(self.Hwnd, self.Msg.TB_HITTEST, 0, byref(pt))
		if result > -1:
			return self._client_GetButton(result).idCommand
			
	def SetTooltips(self, Tooltip):
		self.SendMessage(self.Hwnd, self.Msg.TB_SETTOOLTIPS, Tooltip.Hwnd, 0)
		
	def GetTooltips(self, Tooltip):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETTOOLTIPS, 0, 0)
		if result: return result
		
	
	#-----------------------------------------------------------------------------------------------------
	# colors, metrics, images

	
	
	def SetRows(self, n, allowMore=True):
		rc=RECT()
		if allowMore: allowMore= 1
		else: allowMore= 0
		self.SendMessage(self.Hwnd, self.Msg.TB_SETROWS , MAKELONG(n, allowMore), byref(rc))
		return rc
	
	def GetRows(self):	return self.SendMessage(self.Hwnd, self.Msg.TB_GETROWS, 0, 0)
	
	def LimitButtonWidth(self, minW, maxW):
		if not self.SendMessage(self.Hwnd, self.Msg.TB_SETBUTTONWIDTH , 0, MAKELONG(minW, maxW)):
			raise RuntimeError("could not set indent")
	
	def SetIndent(self, n):
		if not self.SendMessage(self.Hwnd, self.Msg.TB_SETINDENT , n, 0):
			raise RuntimeError("could not set indent")
	
	def GetPadding(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETPADDING, 0, 0)
		return LOWORD(result), HIWORD(result)

	def SetPadding(self, h, v):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETPADDING, 0, MAKELONG(h, v))
		return LOWORD(result), HIWORD(result)
	
	def SetColorScheme(self, colorrefHilight, colorrefShadow):
		clsc=COLORSCHEME(sizeof(COLORSCHEME), colorrefHilight, colorrefShadow)
		self.SendMessage(self.Hwnd, self.Msg.TB_SETCOLORSCHEME, 0, byref(clsc))

	def GetColorScheme(self):
		clsc=COLORSCHEME(sizeof(COLORSCHEME), 0, 0)
		self.SendMessage(self.Hwnd, self.Msg.TB_GETCOLORSCHEME, 0, byref(clsc))
		return clsc.clrBtnHighlight, clsc.clrBtnShadow
	
	def LoadImages(self, ID, hInst=None):
		if not hInst: 
			hInst=4294967295		# HINST_COMMCTRL
			#hInst=-1
			try: ID={'stdsmall':0,'stdlarge': 1,'viewsmall':4,
						'viewlarge':5,'histsmall':8,'histlarge':9}[ID]
			except: raise RuntimeError("invalid image ID: %s" % ID)
		return self.SendMessage(self.Hwnd, self.Msg.TB_LOADIMAGES, ID, hInst)

	def SetImagelistNormal(self, Imagelist):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETIMAGELIST, 0, Imagelist.handle)
		if result: return result

	def SetImagelistHot(self, Imagelist):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETHOTIMAGELIST, 0, Imagelist.handle)
		if result: return result

	def SetImagelistDisabled(self, Imagelist):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_SETDISABLEDIMAGELIST, 0, Imagelist.handle)
		if result: return result
	
	def GetImagelistNormal(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETIMAGELIST, 0, 0)
		if result: return result

	def GetImagelistHot(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETHOTIMAGELIST, 0, 0)
		if result: return result

	def GetImagelistDisabled(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TB_GETDISABLEDIMAGELIST, 0, 0)
		if result: return result

		
	###########################################################
	
	
	
			