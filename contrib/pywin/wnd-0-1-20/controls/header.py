"""
LAST VISITED 
	28.03.05

NOT IMPLEMENTED
	HDM_GETUNICODEFORMAT
	HDM_SETUNICODEFORMAT
	HDM_SETHOTDIVIDER
	HDM_CREATEDRAGIMAGE


TODO
	
	- alignement flags in 'Item' and 'InsertItem'


"""




from wnd.wintypes import (sizeof,
												addressof,
												Structure,
												POINTER,
												pointer,
												byref,
												RECT,
												POINT,
												HWND,
												UINT,
												NMHDR,
												DWORD,
												HIWORD,
												LOWORD,
												INT,
												HANDLE,
												LPARAM,
												WINDOWPOS,
												create_string_buffer,
												InitCommonControlsEx,	)

from wnd import fwtypes as fw
from wnd.controls.base.methods import ControlMethods
from wnd.controls.base import control
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

ICC_LISTVIEW_CLASSES   = 1 
InitCommonControlsEx(ICC_LISTVIEW_CLASSES)


#**********************************************************
#**********************************************************

class HeaderMethods:
	
		
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				if msgr.msg==self.Msg.WM_NOTIFY:
					nm = NMHDR.from_address(msgr.lParam)
											
					if nm.code==self.Msg.NM_CUSTOMDRAW:
						cd= NMCUSTOMDRAW.from_address(msgr.lParam)
						result= self.onMSG(hwnd, "customdraw", 0, cd)
						if result !=None: return result
						return 0		# CDRF_DODEFAULT 
					
				
					elif nm.code==self.Msg.HDN_ITEMCLICK or nm.code==self.Msg.HDN_ITEMCLICKW:
						nmh = NMHEADER.from_address(msgr.lParam)
						if nmh.iButton==0:
							self.onMSG(hwnd, "itemclick", nmh.iItem, 0)
					
					elif nm.code==self.Msg.HDN_ITEMDBLCLICK or nm.code==self.Msg.HDN_ITEMDBLCLICKW:
						nmh = NMHEADER.from_address(msgr.lParam)
						if nmh.iButton==0:
							self.onMSG(hwnd, "itemdouble", nmh.iItem, 0)
						# ...not triggered, on my machine (win98) iButton is allways
						# zero
						#if nmh.iButton==0:
						#	self.onMSG(hwnd, "lmbdouble", nmh.iItem, 0)
						#elif nmh.iButton==1:
						#	self.onMSG(hwnd, "rmbdouble", nmh.iItem, 0)
						#elif nmh.iButton==2:
						#	self.onMSG(hwnd, "mmbdouble", nmh.iItem, 0)
				
					elif nm.code==self.Msg.HDN_BEGINTRACK or nm.code==self.Msg.HDN_BEGINTRACKW:
						# no further info in NMHEADER
						self.onMSG(hwnd, "begintrack", 0, 0)
					elif nm.code==self.Msg.HDN_ENDTRACK:
						# no further info in NMHEADER
						self.onMSG(hwnd, "endtrack", 0, 0)
			return 0	
		
		# keyboard non HDS_BUTTON style
		elif msg==self.Msg.WM_RBUTTONUP:
			if not self.GetStyleL('style') & self.Style.HDS_BUTTONS:
				self.onMSG(hwnd, "rmbup", wp, 
											(HIWORD(lp), LOWORD(lp)))
		elif msg==self.Msg.WM_LBUTTONUP:
			if not self.GetStyleL('style') & self.Style.HDS_BUTTONS:
				self.onMSG(hwnd, "lmbup", wp, 
											(HIWORD(lp), LOWORD(lp)))
		elif msg==self.Msg.WM_LBUTTONDBLCLK:
			if not self.GetStyleL('style') & self.Style.HDS_BUTTONS:
				self.onMSG(hwnd, "lmbdouble", wp, 
											(HIWORD(lp), LOWORD(lp)))
		elif msg==self.Msg.WM_MOUSEACTIVATE:
			self.onMSG(hwnd, "mouseactivate", 0, 0)
			
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			
	
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		address of buffer."""
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text
		return addressof(self._client_buffer)			
	
		
	#--------------------------------------------------------------------------
			
	def __len__(self):
		result = self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEMCOUNT, 0, 0)
		if result > -1: return result
		raise RuntimeError("could not retrieve length")
									
	
	def Clear(self):
		for i in range(self.__len__()):
			self.RemoveItem(0)
	
	def Item(self, text, width= 80, iImage=None, lp=None):
		return self.InsertItem(self.__len__(), text, width, iImage, lp)
		
	def InsertItem(self, i, text, width=80, iImage=None, lp=None):
		hd = HDITEM()
		hd.mask = hd.HDI_TEXT | hd.HDI_WIDTH
		hd.cxy = width
		if iImage != None:
			hd.mask |= hd.HDI_IMAGE
			hd.iImage= iImage
		if lp != None:
			hd.mask |= hd.HDI_LPARAM
			hd.lParam= lp
		hd.pszText = self._client_TruncText(text)
		result = self.SendMessage(self.Hwnd, self.Msg.HDM_INSERTITEM, i, byref(hd))
		if result > -1: return result
		raise RuntimeError("could not insert item")
		
	def RemoveItem(self, i):
		if not self.SendMessage(self.Hwnd, self.Msg.HDM_DELETEITEM, i, 0):
			raise RuntimeError("could not remove item")
	
	def SetItemText(self, i, text):
		hd = HDITEM()
		hd.mask = hd.HDI_TEXT
		hd.pszText = self._client_TruncText(text)
		if not self.SendMessage(self.Hwnd, self.Msg.HDM_SETITEM, i, byref(hd)):
			raise RuntimeError("could not set item text")
				
	def GetItemText(self, i):
		hd = HDITEM()
		hd.mask = hd.HDI_TEXT
		hd.pszText = addressof(self._client_buffer)
		hd.cchTextMax = sizeof(self._client_buffer)
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEM, i, byref(hd)):
			return self._client_buffer.value
		raise RuntimeError("could not retrive item text")
			
	def GetItemLparam(self, i):
		hd = HDITEM()
		hd.mask = hd.HDI_LPARAM
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEM, i, byref(hd)):
			return hd.lParam
		raise RuntimeError("could not retrive lParam")
	
	def SetItemLparam(self, i, lp):
		hd = HDITEM()
		hd.mask = hd.HDI_LPARAM
		hd.lParam= lp
		if self.SendMessage(self.Hwnd, self.Msg.HDM_SETITEM, i, byref(hd)):
			return hd.lParam
		raise RuntimeError("could not set lParam")
	
	def GetItemImage(self, i):
		hd = HDITEM()
		hd.mask = hd.HDI_IMAGE
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEM, i, byref(hd)):
			return hd.iImage
		raise RuntimeError("could not retrive item image")
	
	def SetItemImage(self, i, iImage):
		hd = HDITEM()
		hd.mask = hd.HDI_IMAGE
		hd.iImage= iImage
		if self.SendMessage(self.Hwnd, self.Msg.HDM_SETITEM, i, byref(hd)):
			return hd.iImage
		raise RuntimeError("could not set irtem image")
	
	def GetItemWidth(self, i):
		hd = HDITEM()
		hd.mask = hd.HDI_WIDTH
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEM, i, byref(hd)):
			return hd.cxy
		raise RuntimeError("could not retrive item width")
	
	def SetItemWidth(self, i, n):
		hd = HDITEM()
		hd.mask = hd.HDI_WIDTH
		hd.cxy= n
		if self.SendMessage(self.Hwnd, self.Msg.HDM_SETITEM, i, byref(hd)):
			return hd.iImage
		raise RuntimeError("could not set item width")
	
	def GetItemRect(self, i):
		rc= RECT()
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEMRECT, i, byref(rc)):
			return rc
		raise RuntimeError("could not retrive item rect")

	def ItemHittest(self, x, y):
		# dono about these
		# HHT_ONFILTER 
		# HHT_ONFILTERBUTTON
		ht= HDHITTESTINFO()
		ht.pt.x, ht.pt.y = x, y
		result= self.SendMessage(self.Hwnd, self.Msg.HDM_HITTEST, 0, byref(ht))
		out= []
		if ht.flags & 1: out.append('nowhere')					# HHT_NOWHERE 
		elif ht.flags & 2: out.append('onheader')				# HHT_ONHEADER
		elif ht.flags & 4: out.append('ondivider')				# HHT_ONDIVIDER
		elif ht.flags & 8: out.append('ondivopen')				# HHT_ONDIVOPEN 
		elif ht.flags & 16: out.append('onfilter')					# HHT_ONFILTER 
		elif ht.flags & 32: out.append('onfilterbutton')		# HHT_ONFILTERBUTTON
		elif ht.flags & 256: out.append('above')					# HHT_ABOVE
		elif ht.flags & 512: out.append('below')					# HT_BELOW
		elif ht.flags & 1024: out.append('toright')				# HHT_TORIGHT
		elif ht.flags & 2048: out.append('toleft')					# HHT_TOLEFT
		if result > -1: out.insert(0, result)
		else: out.insert(0, None)
		return out
			
	def GetLayout(self, Rect):
		wp= WINDOWPOS()
		lo= HDLAYOUT(pointer(Rect), pointer(wp))
		if self.SendMessage(self.Hwnd, self.Msg.HDM_LAYOUT, 0, byref(lo)):
			return RECT(wp.x, wp.y, wp.cx, wp.cy)
		raise RuntimeError("could not retrieve header layout")
		
	def SetItemOrder(self, *iOrder):
		arr= (INT*len(iOrder))(*iOrder)
		if not self.SendMessage(self.Hwnd, self.Msg.HDM_SETORDERARRAY, len(arr), byref(arr)):
			raise RuntimeError("could not set item order")
		
	def GetItemOrder(self):
		arr= (INT*len(self))()
		if not self.SendMessage(self.Hwnd, self.Msg.HDM_GETORDERARRAY, len(arr), byref(arr)):
			raise RuntimeError("could not retrieve item order")
		return list(arr)
		
	def IndexToOrder(self, i):
		hd = HDITEM()
		hd.mask = hd.HDI_ORDER
		if self.SendMessage(self.Hwnd, self.Msg.HDM_GETITEM, i, byref(hd)):
			return hd.iOrder
		raise RuntimeError("could not retrive item order index")
		
	def OrderToIndex(self, iOrder):
		if  (len(self) > iOrder > -1):
			return self.SendMessage(self.Hwnd, self.Msg.HDM_ORDERTOINDEX, iOrder, 0)
		raise RuntimeError("index oput of range")
			
	def SetImagelist(self, Imagelist=None):
		if Imagelist==None: hImgl= 0
		else: hImgl= Imagelist.handle
		result= self.SendMessage(self.Hwnd, self.Msg.HDM_SETIMAGELIST, 0, hImgl)
		if result: return result

	def GetImagelist(self):
		result= self.SendMessage(self.Hwnd, self.Msg.HDM_GETIMAGELIST, 0,0)
		if result: return result


#***********************************************************************************
#***********************************************************************************

class Header(HeaderMethods, control.BaseControl, ControlMethods):
		
	def __init__(self, parent, x, y, w, h, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.BaseControl.__init__(self, parent, "SysHeader32", "", x, y, w, h, *styles)
		self._client_buffer = create_string_buffer(512)
		
	
class HeaderFromHandle(HeaderMethods, control.ControlFromHandle, ControlMethods):
		
	def __init__(self, hwnd, *styles):
		self.Style= Styles
		self.Msg= Msgs 
		
		styles += 'subclass',
		control.ControlFromHandle.__init__(self, hwnd, *styles)
		self._client_buffer = create_string_buffer(512)
		

#***********************************************************************************
#***********************************************************************************					

UINT_MAX = (1l << 32)
NM_FIRST = UINT_MAX
HDN_FIRST = (UINT_MAX) - 300
HDM_FIRST =  4608

##
class Styles:
	HDS_HORZ        = 0
	HDS_BUTTONS     = 2
	HDS_HOTTRACK    = 4
	HDS_HIDDEN      = 8
	HDS_DRAGDROP    = 64
	HDS_FULLDRAG    = 128
	HDS_FILTERBAR   = 256
	HDS_FLAT        = 512


Styles.__dict__.update(control.control_styles.__dict__)
Styles.prefix += ['HDS_', ]

	
class Msgs:
	NM_CUSTOMDRAW      = NM_FIRST - 12
	
	HDM_GETITEMCOUNT        = HDM_FIRST + 0
	HDM_INSERTITEM          =  HDM_FIRST + 1
	HDM_DELETEITEM         =  HDM_FIRST + 2
	HDM_GETITEM             =  HDM_FIRST + 3
	HDM_SETITEM             = HDM_FIRST + 4
	HDM_LAYOUT              = HDM_FIRST + 5
	HDM_HITTEST             = HDM_FIRST + 6
	HDM_GETITEMRECT         = HDM_FIRST + 7
	HDM_SETIMAGELIST        = HDM_FIRST + 8
	HDM_GETIMAGELIST        = HDM_FIRST + 9
	HDM_ORDERTOINDEX        = HDM_FIRST + 15
	HDM_CREATEDRAGIMAGE     = HDM_FIRST + 16  # wparam = which item by index
	HDM_GETORDERARRAY       = HDM_FIRST + 17
	HDM_SETORDERARRAY       = HDM_FIRST + 18
	HDM_SETHOTDIVIDER       = HDM_FIRST + 19

	HDM_SETBITMAPMARGIN     = HDM_FIRST + 20
	HDM_GETBITMAPMARGIN     = HDM_FIRST + 21
	HDM_SETFILTERCHANGETIMEOUT = HDM_FIRST + 22
	HDM_EDITFILTER             = HDM_FIRST + 23
	HDM_CLEARFILTER            = HDM_FIRST + 24

	HDN_ITEMCHANGING        = HDN_FIRST - 0
	HDN_ITEMCHANGED         = HDN_FIRST - 1
	HDN_ITEMCLICK           = HDN_FIRST - 2
	HDN_ITEMCLICKW          = HDN_FIRST - 22
	HDN_ITEMDBLCLICK        = HDN_FIRST - 3
	HDN_DIVIDERDBLCLICK     = HDN_FIRST - 5
	HDN_BEGINTRACK          = HDN_FIRST - 6
	HDN_ENDTRACK            = HDN_FIRST - 7
	HDN_TRACK               = HDN_FIRST - 8
	HDN_GETDISPINFO         = HDN_FIRST - 9
	HDN_BEGINDRAG           = HDN_FIRST - 10
	HDN_ENDDRAG             = HDN_FIRST - 11
	HDN_FILTERCHANGE        = HDN_FIRST - 12
	HDN_FILTERBTNCLICK      = HDN_FIRST - 13

	HDN_ITEMCHANGINGW       = HDN_FIRST - 20
	HDN_ITEMCHANGEDW        = HDN_FIRST - 21
	HDN_ITEMCLICKW          = HDN_FIRST - 22
	HDN_ITEMDBLCLICKW       = HDN_FIRST - 23
	HDN_DIVIDERDBLCLICKW    = HDN_FIRST - 25
	HDN_BEGINTRACKW         = HDN_FIRST - 26
	HDN_ENDTRACKW           = HDN_FIRST - 27
	HDN_TRACKW              = HDN_FIRST - 28
	HDN_GETDISPINFOW        = HDN_FIRST - 29


	NM_RCLICK          = NM_FIRST - 5

Msgs.__dict__.update(control.control_msgs.__dict__)



class HDITEM(Structure):
	HDI_WIDTH            = 1
	HDI_HEIGHT           = HDI_WIDTH
	HDI_TEXT             = 2
	HDI_FORMAT           = 4
	HDI_LPARAM           = 8
	HDI_BITMAP           = 16
	HDI_IMAGE            = 32
	HDI_DI_SETITEM       = 64
	HDI_ORDER            = 128
	#HDI_FILTER           = 256	# ??

	HDF_LEFT            = 0
	HDF_RIGHT           = 1
	HDF_CENTER          = 2
	HDF_JUSTIFYMASK     = 3
	HDF_RTLREADING      = 4

	HDF_OWNERDRAW       = 32768
	HDF_STRING          = 16384
	HDF_BITMAP          = 8192
	HDF_BITMAP_ON_RIGHT = 4096
	HDF_IMAGE           = 2048
	#HDF_SORTUP          = 1024		# ??
	#HDF_SORTDOWN        = 512	# ??

	_fields_ = [("mask", UINT),
					("cxy", INT),
					("pszText", DWORD),	# address of buffer
					("hbm", HANDLE),
					("cchTextMax", INT),
					("fmt", INT),
					("lParam", LPARAM),
					("iImage", INT),
					("iOrder", INT)]

class NMHDR(Structure):
	_fields_=[("hwndFrom", HWND),
						("idFrom", UINT),
						("code", UINT)]

class NMHEADER(Structure):
	_fields_ = [("hdr", NMHDR),
					("iItem", INT),
					("iButton", INT),
					("pitem", POINTER(HDITEM))]

class HDHITTESTINFO(Structure):
	_fields_ = [("pt", POINT),
					("flags", UINT),
					("iItem", INT)]

class HDLAYOUT(Structure):
	_fields_ = [("prc", POINTER(RECT)),
						("pwpos", POINTER(WINDOWPOS))]

class NMCUSTOMDRAW(Structure):
	ITEM               = 65536
		
	PREPAINT           = 1
	POSTPAINT          = 2
	
	ITEMPREPAINT       = (ITEM | PREPAINT)
	ITEMPOSTPAINT      = (ITEM | POSTPAINT)
	#print ITEM | SUBITEM| PREPAINT
	
	# customdraw return flags
	# CDRF_*
	DODEFAULT          = 0
	NEWFONT            = 2
	SKIPDEFAULT        = 4
	NOTIFYPOSTPAINT    = 16
	NOTIFYITEMDRAW	= 32
	
	
	
	_fields_ = [("hdr", NMHDR),
					("drawStage", DWORD),
					("hdc", HANDLE),
					("rc", RECT),
					("iItem", DWORD),
					("itemState", UINT),
					("itemlParam", LPARAM)]				