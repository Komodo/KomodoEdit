
"""
LAST VISITED
	29.03.05


NOT IMPLEMENTED
	
	LB_SELITEMRANGEEX
	LB_GETLOCALE
	LB_SETLOCALE
	LB_SETTABSTOPS
	
	LBS_OWNERDRAWFIXED
	LBS_OWNERDRAWVARIABLE
	LBS_NODATA		## should be used when the itemcount exceeds 1000


TODO
	- in depth test all the methods
		there was one fatal exception when setting the column width to 0
		in LBS_MULTICOLUMN, may be some more to find...
	- check the ListDir stuuf to find out if it is of any use

"""

from wnd.wintypes import (byref,
												Structure,
												DWORD,
												RECT,
												INT,
												HIWORD,
												LOWORD,
												MAKELONG,
												create_string_buffer,
												DRAWITEMSTRUCT,)
from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
LB_ERR      = -1
LB_ERRSPACE = -2		


class ListboxMethods:

	#-----------------------------------------------------------------	
	# message handler	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_COMMAND:
					notify = HIWORD(msgr.wParam)
					if notify == self.Msg.LBN_ERRSPACE:
						self.onMSG(hwnd, "errspace", 0, 0)
					elif notify == self.Msg.LBN_SELCHANGE:
						self.onMSG(hwnd, "change", 0, 0)
					elif notify == self.Msg.LBN_SELCANCEL:
						self.onMSG(hwnd, "cancel", 0, 0)
			return 0
		
		elif msg==self.Msg.WM_STYLECHANGING:
			# make shure LBS_MULTIPLESEL and LBS_EXTENDEDSEL
			# can not be changed at runtime 
			# (will deadlock on some method calls)
			if wp==(1l<<32) - 16:			# GWL_STYLE
				#LVS_SHAREIMAGELISTS = 64
				sst = STYLESTRUCT.from_address(lp)
				if sst.styleOld & 8:			# LBS_MULTIPLESEL
					if not sst.styleNew & 8:
						sst.styleNew |= 8
				elif not sst.styleOld & 8:
					if sst.styleNew & 8:
						sst.styleNew &= ~8
				
				if sst.styleOld & 2048:	# LBS_EXTENDEDSEL
					if not sst.styleNew & 2048:
						sst.styleNew |= 2048
				elif not sst.styleOld & 2048:
					if sst.styleNew & 2048:
						sst.styleNew &= ~2048
				return 0
						
		elif msg==self.Msg.WM_SETFOCUS:
			self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			self.onMSG(hwnd, "killfocus", wp, lp)
		elif msg==self.Msg.WM_RBUTTONUP:
			self.onMSG(hwnd, "rmbup", wp, lp)
		elif msg==self.Msg.WM_LBUTTONUP:
			self.onMSG(hwnd, "lmbup", wp, lp)
		elif msg==self.Msg.WM_LBUTTONDBLCLK:
			self.onMSG(hwnd, "lmbdouble", wp, lp)
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
				
	#-------------------------------------------------------------------------
	# listbox methods

	def __len__(self):
		result = self.SendMessage(self.Hwnd, self.Msg.LB_GETCOUNT, 0, 0)
		if result==LB_ERR: raise RuntimeError("could not retrieve len")
		return result
	
	def __iter__(self):
		for i in range(self.__len__()): yield i
			
	def Item(self, text, lp=None):
		result = self.SendMessage(self.Hwnd, 
							self.Msg.LB_ADDSTRING, 0, text)
		if result==LB_ERR: raise RuntimeError("could not add item")
		elif result==LB_ERRSPACE: raise MemoryError("listbox out of space")
		if lp !=None:
			if self.SendMessage(self.Hwnd,
					self.Msg.LB_SETITEMDATA, result, lp)==LB_ERR:
				raise RuntimeError, "could not set lparam"
		return result

	def InsertItem(self, i, text, lp=None):
		result = self.SendMessage(self.Hwnd, self.Msg.LB_INSERTSTRING, i, text)
		if result==LB_ERR: raise RuntimeError("could not insert item")
		elif result==LB_ERRSPACE: raise MemoryError("listbox out of space")
		if lp != None:
			if self.SendMessage(self.Hwnd,
					self.Msg.LB_SETITEMDATA, result, lp)==LB_ERR:
				raise RuntimeError("could not set lparam")
		return result
		
	def GetItemText(self, i):
		result = self.SendMessage(self.Hwnd, self.Msg.LB_GETTEXTLEN, i, 0)
		if result==LB_ERR: raise RuntimeError("could not retrieve item text")
		p = create_string_buffer(result+1)
		self.SendMessage(self.Hwnd, self.Msg.LB_GETTEXT, i, p)
		return p.value
	
	def SetItemText(self, i, text):
		try:
			lp= self.GetItemLparam(i)
			self.RemoveItem(i)
			self.InsertItem(i, text, lp)
		except: raise RuntimeError("could not set item text")
		
	def SetItemLparam(self, i, lp):
		result=self.SendMessage(self.Hwnd, self.Msg.LB_SETITEMDATA, i, lp)
		if result==LB_ERR: raise RuntimeError("could not set lparam")
		
	def GetItemLparam(self, i):
		result=self.SendMessage(self.Hwnd,
						self.Msg.LB_GETITEMDATA, i, 0)
		if result==LB_ERR: raise RuntimeError("could not retrieve lparam")
		return result

	def RemoveItem(self, i):
		result = self.SendMessage(self.Hwnd,
							self.Msg.LB_DELETESTRING, i, 0)
		if result==LB_ERR: raise RuntimeError("could not retmove item")
		return result
	
	def Clear(self):
		self.SendMessage(self.Hwnd, self.Msg.LB_RESETCONTENT, 0, 0)
		 
	#-------------------------------------------------------------------
	# selecting and finding

			
	def Find(self, what, i=-1):
		result = self.SendMessage(self.Hwnd,
							self.Msg.LB_FINDSTRING, i, what)
		if result != LB_ERR: return result
	
	def FindExact(self, what, i=-1):
		result = self.SendMessage(self.Hwnd,
							self.Msg.LB_FINDSTRINGEXACT, i, what)
		if result != LB_ERR: return result
	
	def FindXY(self, x, y):
		result = self.SendMessage(self.Hwnd,
							self.Msg.LB_ITEMFROMPOINT , 0, MAKELONG(x, y))
		if not HIWORD(result):
			return LOWORD(result)
		
	
	def Select(self, i, stop=0):
		if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
			if stop:
				result=self.SendMessage(self.Hwnd,
									self.Msg.LB_SELITEMRANGE, 1, MAKELONG(i, stop))
				if result==LB_ERR:	raise "could not select items"
			else:
				result= self.SendMessage(self.Hwnd, self.Msg.LB_SETSEL, 1, i)
				if result==LB_ERR: raise "could not select item"
		else:
			result=self.SendMessage(self.Hwnd, self.Msg.LB_SETCURSEL, i, 0)
			if i !=-1:
				if result==LB_ERR:	raise "could not select item"
			
	
	def IsSelected(self, i):
		result=self.SendMessage(self.Hwnd,	self.Msg.LB_GETSEL, i, 0)
		if result < 0: raise "could not retreive selection status"
		if result: return True
		return False
		
	def Deselect(self, i, stop=0):
		if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
			if stop:
				result=self.SendMessage(self.Hwnd,
									self.Msg.LB_SELITEMRANGE, 0, MAKELONG(i, stop))
				if result==LB_ERR:	raise "could not select items"
			else:
				result= self.SendMessage(self.Hwnd, self.Msg.LB_SETSEL, 0, i)
				if result==LB_ERR:	raise "could not deselect item"
		else:
			self.SendMessage(self.Hwnd, self.Msg.LB_SETCURSEL, -1, 0)
	
	def GetSelected(self):
		if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
			result=self.SendMessage(self.Hwnd,
									self.Msg.LB_GETSELCOUNT, 0, 0)
			if result:
				return self.SendMessage(self.Hwnd,
									self.Msg.LB_GETANCHORINDEX, 0, 0)
		else:
			result=self.SendMessage(self.Hwnd,
									self.Msg.LB_GETCURSEL, 0, 0)
			if result !=LB_ERR: return result
	
	
	def SelectItems(self, start, stop):
		result=self.SendMessage(self.Hwnd,
									self.Msg.LB_SELITEMRANGE, 1, MAKELONG(start, stop))
		if result==LB_ERR:	raise "could not select items"
		
	def DeselectItems(self, start, stop):
		result=self.SendMessage(self.Hwnd,
									self.Msg.LB_SELITEMRANGE, 0, MAKELONG(start, stop))
		if result==LB_ERR:	raise "could not deselect items"	
	
	def SelectItemText(self, what, i=-1):
		result=self.SendMessage(self.Hwnd, self.Msg.LB_SELECTSTRING, i, what)
		if result > -1: 
			# maybe there is some reason for not selecting result in 'multiplesel'
			# Listboxes, maybe not. Anyway, select by hand here.
			if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
				self.Select(result)
			return result
		
	def GetSelectedCount(self):
		if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
			return self.SendMessage(self.Hwnd,
									self.Msg.LB_GETSELCOUNT, 0, 0)
		else:
			result=self.SendMessage(self.Hwnd,
									self.Msg.LB_GETCURSEL, 0, 0)
			if result==LB_ERR: return 0
			return 1
	
	def IterSelected(self):
		style= self.GetStyleL('style')
		if style & self.Style.LBS_MULTIPLESEL or	 \
			style & self.Style.LBS_EXTENDEDSEL:
						
			n=self.SendMessage(self.Hwnd, self.Msg.LB_GETSELCOUNT, 0, 0)
			if n:
				arr = (INT * n)()
				r= self.SendMessage(self.Hwnd,
									self.Msg.LB_GETSELITEMS , len(arr), byref(arr))
				for i in arr:
					yield i
		else:
			result=self.SendMessage(self.Hwnd,
									self.Msg.LB_GETCURSEL, 0, 0)
			if result !=LB_ERR:  yield result
	
	
	def GetFocusItem(self):
		if self.GetStyleL('style') & self.Style.LBS_MULTIPLESEL:
			result=self.SendMessage(self.Hwnd,	self.Msg.LB_GETCARETINDEX, 0, 0)
			if result != LB_ERR: return result
		
	def SetFocusItem(self, i):
		result=self.SendMessage(self.Hwnd, self.Msg.LB_SETCARETINDEX, i, 0)
		if result != LB_ERR: return result
		
	
	#---------------------------------------------------------------------
	# scrolling
	
	def SetTopIndex(self, i):
		if self.SendMessage(self.Hwnd, self.Msg.LB_SETTOPINDEX, i, 0) <0:
			raise "could not set top index"
	
	def GetTopIndex(self):
		return self.SendMessage(self.Hwnd, self.Msg.LB_GETTOPINDEX , 0, 0)
	
	def GetScrollWidth(self):
		return self.SendMessage(self.Hwnd, self.Msg.LB_GETHORIZONTALEXTENT, 0, 0)
		
	def SetScrollWidth(self, n):
		self.SendMessage(self.Hwnd, self.Msg.LB_SETHORIZONTALEXTENT, n, 0)
		
	#-------------------------------------------------------------------------
	# metrics
	
	def SetItemHeight(self, h, i=0):
		if self.SendMessage(self.Hwnd, self.Msg.LB_SETITEMHEIGHT
		, i, h)== LB_ERR:
			raise "could not set item height"
	
	def GetItemHeight(self, i=0):
		result = self.SendMessage(self.Hwnd, self.Msg.LB_GETITEMHEIGHT, i, 0)
		if result==LB_ERR:	raise "could not retrieve item height"
		return result
	
	def SetColumnWidth(self, w):
		# fatal error here if w= 0
		# + nonn 'multicolumn' Listboxes react unpredictable
		if self.GetStyleL('style') & self.Style.LBS_MULTICOLUMN:
			if w <= 0: raise "column width must be at least 1" 
			self.SendMessage(self.Hwnd, self.Msg.LB_SETCOLUMNWIDTH, w, 0)
		
	def GetItemRect(self, i):
		rc=RECT()
		result=self.SendMessage(self.Hwnd, self.Msg.LB_GETITEMRECT, i, byref(rc))
		if result==LB_ERR: raise "could not retrieve item rect"
		return rc

	def InitStorage(self, nItems, nItemSize):
		result=self.SendMessage(self.Hwnd, self.Msg.LB_INITSTORAGE, nItems, nItemSize)
		if result== LB_ERRSPACE: raise "could not init storage"
		return result
		
	def ListDir(self, path, *flags):
		flag= 0
		for i in flags:
			try: flag |= DIR_FLAGS[i]
			except: raise "invalid flag: %s" % i
		if self.SendMessage(self.Hwnd, self.Msg.LB_DIR, flag, path) < 0:
			raise "could not list dir"
		

#**********************************************************************
WS_VSCROLL         = 2097152
WS_BORDER          = 8388608

class Styles:
	LBS_NOTIFY            = 1 # disabled. Is default.
	LBS_SORT              = 2
	LBS_NOREDRAW          = 4
	LBS_MULTIPLESEL       = 8
	LBS_OWNERDRAWFIXED    = 16
	LBS_OWNERDRAWVARIABLE = 32
	LBS_HASSTRINGS        = 64
	LBS_USETABSTOPS       = 128
	LBS_NOINTEGRALHEIGHT  = 256
	LBS_MULTICOLUMN       = 512
	LBS_WANTKEYBOARDINPUT = 1024	# not yet
	LBS_EXTENDEDSEL       = 2048
	LBS_DISABLENOSCROLL   = 4096
	LBS_NODATA            = 8192
	LBS_NOSEL             = 16384
	LBS_STANDARD          = LBS_NOTIFY | LBS_SORT | WS_VSCROLL | WS_BORDER	

Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['LBS_', ]



class Msgs: 
	# Listbox Notification Codes
	LBN_ERRSPACE  = -2
	LBN_SELCHANGE = 1
	LBN_DBLCLK    = 2
	LBN_SELCANCEL = 3
	LBN_SETFOCUS  = 4
	LBN_KILLFOCUS = 5

	# Listbox messages
	LB_ADDSTRING          = 384
	LB_INSERTSTRING       = 385
	LB_DELETESTRING       = 386
	LB_SELITEMRANGEEX     = 387
	LB_RESETCONTENT       = 388
	LB_SETSEL             = 389
	LB_SETCURSEL          = 390
	LB_GETSEL             = 391
	LB_GETCURSEL          = 392
	LB_GETTEXT            = 393
	LB_GETTEXTLEN         = 394
	LB_GETCOUNT           = 395
	LB_SELECTSTRING       = 396
	LB_DIR                = 397
	LB_GETTOPINDEX        = 398
	LB_FINDSTRING         = 399
	LB_GETSELCOUNT        = 400
	LB_GETSELITEMS        = 401
	LB_SETTABSTOPS        = 402
	LB_GETHORIZONTALEXTENT= 403
	LB_SETHORIZONTALEXTENT= 404
	LB_SETCOLUMNWIDTH     = 405
	LB_ADDFILE            = 406
	LB_SETTOPINDEX        = 407
	LB_GETITEMRECT        = 408
	LB_GETITEMDATA        = 409
	LB_SETITEMDATA        = 410
	LB_SELITEMRANGE       = 411
	LB_SETANCHORINDEX     = 412
	LB_GETANCHORINDEX     = 413
	LB_SETCARETINDEX      = 414
	LB_GETCARETINDEX      = 415
	LB_SETITEMHEIGHT      = 416
	LB_GETITEMHEIGHT      = 417
	LB_FINDSTRINGEXACT    = 418
	LB_SETLOCALE          = 421
	LB_GETLOCALE          = 422
	LB_SETCOUNT           = 423
	LB_INITSTORAGE        = 424
	LB_ITEMFROMPOINT      = 425
	LB_MULTIPLEADDSTRING  = 433
	LB_GETLISTBOXINFO     = 434
	LB_MSGMAX             = 435  # depends on Windows version
	
Msgs.__dict__.update(control.control_msgs.__dict__)



class Listbox(ListboxMethods, control.BaseControl, ControlMethods):
	

	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass','nointegralheight', 'notify'
		control.BaseControl.__init__(self, parent, "listbox", "", x, y, w, h, *styles)
				

class ListboxFromHandle(ListboxMethods, control.ControlFromHandle, ControlMethods):
	
	
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		

#***********************************************
DDL_READWRITE = 0
DDL_READONLY  = 1
DDL_HIDDEN    = 2
DDL_SYSTEM    = 4
DDL_DIRECTORY = 16
DDL_ARCHIVE   = 32

DDL_POSTMSGS  = 8192
DDL_DRIVES    = 16384
DDL_EXCLUSIVE = 32768


DIR_FLAGS= {
'readwrite': DDL_READWRITE,
'readonly': DDL_READONLY,
'hidden': DDL_HIDDEN,
'system': DDL_SYSTEM,
'directory': DDL_DIRECTORY,
'archive': DDL_ARCHIVE,
#'postmsgs': DDL_POSTMSGS,		## ??
'drives': DDL_DRIVES,
'exclusive': DDL_EXCLUSIVE,
}

class STYLESTRUCT(Structure):
	_fields_ = [("styleOld", DWORD), 
					("styleNew", DWORD)]

