"""
LAST VISITED 23.02.05

TODO
	'ownerdraw' is currently to messy. There is no way to reflect
	the message to the control. It blocks all messages while
	processing WM_MEASUREITEM, and they never appear here.
	Trying to reflect them brings them back to the parents loop
	causing infinite recursion. 

	
	
	wnd.custom.ODCombobox handles this

	




NOT IMPLEMENTED
	CB_GETLOCALE
	CB_SETLOCALE
	CB_LIMITTEXT
	CB_SETDROPPEDWIDTH
	CB_GETDROPPEDWIDTH       = 351
	CCM_SETUNICODEFORMAT
	CCM_GETUNICODEFORMAT
	
	
	CBN_SELCHANGE

	WM_COMPAREITEM	# send to parent



"""



#from wnd.base import *

from wnd.wintypes import (RECT,
													LOWORD,
													HIWORD,
													MAKELONG,
													byref,
													sizeof,
													user32,
													create_string_buffer)
from wnd import fwtypes as fw
from wnd.controls.textin import TextinFromHandle
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class ComboboxMethods:
	#-----------------------------------------------------------------
	# some special handling for GetStyle

	def GetStyle(self):
		style=ControlMethods.GetStyle(self)
		if 'dropdownlist' in style:
			style.remove('dropdown')
		return style
	

	#--------------------------------------------------------------------
	# message handler
				
	def onMESSAGE(self, hwnd, msg, wp, lp):
				
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_COMMAND:
					notify=HIWORD(msgr.wParam)
					if notify == self.Msg.CBN_DROPDOWN:
						self.onMSG(hwnd, "opendropdown", 0, 0)
					elif notify == self.Msg.CBN_CLOSEUP:
						self.onMSG(hwnd, "closedropdown", 0, 0)
					elif notify == self.Msg.CBN_EDITCHANGE:
						self.onMSG(hwnd, "change", 0, 0)
					elif notify == self.Msg.CBN_EDITUPDATE:
						self.onMSG(hwnd, "update", 0, 0)	
					elif notify == self.Msg.CBN_ERRSPACE:
						self.onMSG(hwnd, "errspace", 0, 0)
					elif notify == self.Msg.CBN_SELENDCANCEL:
						self.onMSG(hwnd, "selectcancel", 0, 0)
					elif notify == self.Msg.CBN_SELENDOK:
						self.onMSG(hwnd, "select", 0, 0)
					elif notify == self.Msg.CBN_DBLCLK:
						self.onMSG(hwnd, "lmbdouble", 0, 0)
					elif notify==self.Msg.CBN_SETFOCUS:
						self.onMSG(hwnd, "setfocus", 0, 0)
					elif notify==self.Msg.CBN_KILLFOCUS:
						self.onMSG(hwnd, "killfocus", 0, 0)
			return 0
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
		
	#--------------------------------------------------------------------
	# combobox methods
	
	def GetTextMax(self): return self._client_textMax
	def SetTextMax(self, n): self._client_textMax= n
	
	
	def __iter__(self): 
		for i in range(self.__len__()): yield i
	
	def __len__(self):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETCOUNT, 0, 0)
		if result <0: raise RuntimeError("could not retrieve item count")
		return result
	
	def Clear(self):
		self.SendMessage(self.Hwnd, self.Msg.CB_RESETCONTENT, 0, 0)
	
	def SetItemCount(self, nItems, nItemSize):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_INITSTORAGE , nItems, nItemSize)
		if result <0: raise RuntimeError("could not set item count")
		return result
	
	def SetExtendedUI(self, Bool):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETEXTENDEDUI, Bool and 1 or 0, 0)
		if result <0: raise RuntimeError("could not set user interface")

	def HasExtendedUI(self):
		return bool(self.SendMessage(self.Hwnd, self.Msg.CB_GETEXTENDEDUI, 0, 0))
			
	def GetScrollWidth(self):
		return self.SendMessage(self.Hwnd, self.Msg.CB_GETHORIZONTALEXTENT, 0, 0)

	def SetScrollWidth(self, n):
		self.SendMessage(self.Hwnd, self.Msg.CB_SETHORIZONTALEXTENT, n, 0)

	
	#************************************************
	def Item(self, text, lp=None):
		result = self.SendMessage(self.Hwnd, self.Msg.CB_ADDSTRING, 0, text[:self.GetTextMax()])
		if result <0: raise RuntimeError("could not append item")
		if lp !=None:	self.SetItemLparam(result, lp)
		return result
			
	def InsertItem(self, i, text, lp=None):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_INSERTSTRING, i, text[:self.GetTextMax()])
		if result <0: raise RuntimeError("could not insert item")
		if lp !=None:	self.SetItemLparam(result, lp)
		return result

	def RemoveItem(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_DELETESTRING, i, 0)
		if result <0: raise RuntimeError("could not remove item")
		return result
	
	def GetItemTextLen(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETLBTEXTLEN, i, 0)
		if result< 0: raise RuntimeError("could not retrieve text length")
		return result
	
	def GetItemText(self, i):
		n=self.GetItemTextLen(i)
		p=create_string_buffer(n+1)
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETLBTEXT, i, (p))
		if result< 0: raise RuntimeError("could not retrieve item text")
		return p.value

	def SetItemText(self, i, text):
		try:
			lp= self.GetItemLparam(i)
			self.RemoveItem(i)
			self.InsertItem(i, text[:self.GetTextMax()], lp)
		except: raise RuntimeError("could not set item text")

	def SetItemLparam(self, i, lp):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETITEMDATA , i, lp)
		if result <0: raise RuntimeError("could not set item lparam")
		
	def GetItemLparam(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETITEMDATA, i, 0)
		if result < 0: raise RuntimeError("could not retrieve item lparam")
		return result

	def GetItemHeight(self, i=0):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETITEMHEIGHT, i, 0)
		if result< 0: raise RuntimeError("could not retrieve item height")
		return result
	
	def SetItemHeight(self, h, i=0):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETITEMHEIGHT, i, h)
		if result< 0: raise RuntimeError("could not set item height")
		
	
	#------------------------------------------------------------------
	# edit methods
	
	def GetEditSelection(self):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETEDITSEL, 0, 0)
		return LOWORD(result), HIWORD(result)
		
	def SetEditSelection(self, nStart=0, nStop=-1):
		nSel=MAKELONG(nStart, nStop)
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETEDITSEL, 0, nSel)
		if result< 0: raise RuntimeError("could not set edit field selection")
		
	
	#------------------------------------------------------------------
	# dropdown methods
	
	def OpenDropdown(self):
		self.SendMessage(self.Hwnd, self.Msg.CB_SHOWDROPDOWN, 1, 0)
	
	def CloseDropdown(self):
		self.SendMessage(self.Hwnd, self.Msg.CB_SHOWDROPDOWN, 0, 0)

	def IsDroppedDown(self):
		return bool(self.SendMessage(self.Hwnd, self.Msg.CB_GETDROPPEDSTATE , 0, 0))
			
	def GetDropdownRect(self):
		rc=RECT()
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETDROPPEDCONTROLRECT, 0, byref(rc))
		if result< 0: raise RuntimeError("could not retrieve dropdown rect")
		return rc

	#------------------------------------------------------------------
	# selecting and finding

	def Select(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETCURSEL, i, 0)
		if result< 0: raise RuntimeError("could not select item")
		return result

	def SelectItemText(self, what, i=-1):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SELECTSTRING, i, what)
		if result >-1: return result 
		
	def Find(self, what, i=-1):
		result = self.SendMessage(self.Hwnd, self.Msg.CB_FINDSTRING, i, what)
		if result > -1: return result
	
	def FindExact(self, what, i=-1):
		result = self.SendMessage(self.Hwnd, self.Msg.CB_FINDSTRINGEXACT, i, what)
		if result > -1: return result

	def GetSelected(self):
		result = self.SendMessage(self.Hwnd, self.Msg.CB_GETCURSEL, 0, 0)
		if result > -1: return result
		
	def GetTopItem(self):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_GETTOPINDEX, 0, 0)
		if result< 0: raise RuntimeError("could not retrieve top item")
		return result

	def SetTopItem(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.CB_SETTOPINDEX, i, 0)
		if result< 0: raise RuntimeError("could not set top item")
		return result
	
	
	def GetEditControl(self, *flags):
		# get the editbox for the combo and subclass it
		p=create_string_buffer(5)
		flag= False
		for i in self.ChildWindows():
			if user32.GetParent(i)==self.Hwnd:
				user32.GetClassNameA(i, p, sizeof(p))
				if p.value.lower()=="edit":
					flag= True
					break
		if flag: 
			txt= TextinFromHandle(i, 'subclass', *flags)
			fw.SetFlagMsgReflect(txt, False)
			return txt
		
		raise RuntimeError("could not retrieve edit control")
				

#***********************************************************************

class Styles:
	CBS_SIMPLE            = 1
	CBS_DROPDOWN          = 2
	CBS_DROPDOWNLIST      = 3
	
	# Combo Box styles
	CBS_OWNERDRAWFIXED    = 16
	CBS_OWNERDRAWVARIABLE = 32
	CBS_AUTOHSCROLL       = 64
	CBS_OEMCONVERT        = 128
	CBS_SORT              = 256
	CBS_HASSTRINGS        = 512
	CBS_NOINTEGRALHEIGHT  = 1024
	CBS_DISABLENOSCROLL   = 2048
	CBS_UPPERCASE         = 8192
	CBS_LOWERCASE         = 16384

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['CBS_', ]

class Msgs:
	# Combo Box Notification Codes
	CBN_ERRSPACE     = -1
	CBN_SELCHANGE    = 1
	CBN_DBLCLK       = 2
	CBN_SETFOCUS     = 3
	CBN_KILLFOCUS    = 4
	CBN_EDITCHANGE   = 5
	CBN_EDITUPDATE   = 6
	CBN_DROPDOWN     = 7
	CBN_CLOSEUP      = 8
	CBN_SELENDOK     = 9
	CBN_SELENDCANCEL = 10
	CBN_SELCANCEL    = CBN_SELENDCANCEL

	# Combo Box messages
	CB_GETEDITSEL            = 320
	CB_LIMITTEXT             = 321
	CB_SETEDITSEL            = 322
	CB_ADDSTRING             = 323
	CB_DELETESTRING          = 324
	CB_DIR                   = 325
	CB_GETCOUNT              = 326
	CB_GETCURSEL             = 327
	CB_GETLBTEXT             = 328
	CB_GETLBTEXTLEN          = 329
	CB_INSERTSTRING          = 330
	CB_RESETCONTENT          = 331
	CB_FINDSTRING            = 332
	CB_SELECTSTRING          = 333
	CB_SETCURSEL             = 334
	CB_SHOWDROPDOWN          = 335
	CB_GETITEMDATA           = 336
	CB_SETITEMDATA           = 337
	CB_GETDROPPEDCONTROLRECT = 338
	CB_SETITEMHEIGHT         = 339
	CB_GETITEMHEIGHT         = 340
	CB_SETEXTENDEDUI         = 341
	CB_GETEXTENDEDUI         = 342
	CB_GETDROPPEDSTATE       = 343
	CB_FINDSTRINGEXACT       = 344
	CB_SETLOCALE             = 345
	CB_GETLOCALE             = 346
	CB_GETTOPINDEX           = 347
	CB_SETTOPINDEX           = 348
	CB_GETHORIZONTALEXTENT   = 349
	CB_SETHORIZONTALEXTENT   = 350
	CB_GETDROPPEDWIDTH       = 351
	CB_SETDROPPEDWIDTH       = 352
	CB_INITSTORAGE           = 353
	CB_MULTIPLEADDSTRING     = 355
	CB_GETCOMBOBOXINFO       = 356
	CB_MSGMAX                = 357  # depends on Windows version

Msgs.__dict__.update(control.control_msgs.__dict__)

class Combobox(ComboboxMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
				
		#flag = False
		#if 'simple' in styles: flag=True
		#elif 'dropdown' in styles: flag=True
		#elif 'dropdownlist' in styles: flag=True
		#if not flag:
		styles += 'subclass', 'nointegralheight',
						
		control.BaseControl.__init__(self, parent, "combobox", '', x, y, w, h, *styles)
		#self._base_pChildEnumProc= ENUMWINDOWSPROC(self._base_ChildEnumProc)

		self._client_textMax= 512

		
	
class ComboboxFromHandle(ComboboxMethods, control.ControlFromHandle, ControlMethods):
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		#self._base_pChildEnumProc= ENUMWINDOWSPROC(self._base_ChildEnumProc)

		self._client_textMax= 512
		

		

#***********************************************

# Combo Box return Values
CB_OKAY     = 0
CB_ERR      = -1
CB_ERRSPACE = -2
	
#*****************************************************
DDL_READWRITE = 0
DDL_READONLY  = 1
DDL_HIDDEN    = 2
DDL_SYSTEM    = 4
DDL_DIRECTORY = 16
DDL_ARCHIVE   = 32

DDL_POSTMSGS  = 8192
DDL_DRIVES    = 16384
DDL_EXCLUSIVE = 32768

