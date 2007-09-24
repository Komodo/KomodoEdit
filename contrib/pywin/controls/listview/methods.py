
from wnd.controls.listview.messagehandler import ListviewMessageHandler
from wnd.controls.listview.header import *


from wnd.controls.header import HeaderFromHandle
from wnd.controls.textin import TextinFromHandle
from wnd.controls.base.methods import ControlMethods
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class ListviewMethods(ListviewMessageHandler):
		
	
	def HandleKeyMessage(self, *vKeys):
		self._client_keyboardMsgs +=  list(vKeys)
	
	def SetTextMax(self, n):
		self._client_buffer = create_string_buffer(n +1)
	
	def GetTextMax(self):
		return sizeof(self._client_buffer) -1
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text + '\x00'
		return addressof(self._client_buffer)			
	
	def _client_SortFunc(self, lp1, lp2, lp):
		if self._client_CompFunc: 
			return self._client_CompFunc(lp1, lp2, lp)
		return 0
	
	def SetStyle(self, *styles):
		lv_styles = ['icon', 'report','smallicon','list']
		style = ControlMethods.GetStyleL(self, 'style')
		out=[]
		flag=False
		for i in styles:
			if i in lv_styles:
				style &= (~3)
				style |= lv_styles.index(i)
				flag=True
			else: out.append(i)
		if flag: ControlMethods.SetStyleL(self, 'style', style)
		if out: ControlMethods.SetStyle(self, *out)
	
	def GetStyle(self):
		styles = ControlMethods.GetStyle(self)
		flag=None
		for i in ('icon','report','smallicon','list'):
			try:
				styles.remove(i)
				flag=i
			except: pass
		if flag: styles.append(flag)
		return styles
	
	def SortCB(self, callback, lp=0):
		self._client_CompFunc = callback
		if not self.SendMessage(self.Hwnd, 				
							self.Msg.LVM_SORTITEMS,
							lp, self._client_p_SortFunc):
			raise RuntimeError("could not sort items")
		

	def __iter__(self):
		for i in range(self.__len__()): yield i


		#----------------------------------------------------------------------
	# column methods

	def Column(self, text, width=80, iImage=None, align=None):
		return self.InsertColumn(self.GetColumnCount(), text, width, iImage, align)

	def InsertColumn(self, columno, text, width=80, iImage=None, align=None):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_WIDTH | lvc.LVCF_TEXT
		lvc.cx = width
		lvc.pszText =  self._client_TruncText(text)
		if iImage !=None:
			lvc.mask |= lvc.LVCF_IMAGE
			lvc.iImage= iImage
		if align:
			lvc.mask |= lvc.LVCF_FMT
			#LVCFMT_JUSTIFYMASK     = 3				## ??
			#LVCFMT_IMAGE           = 2048					## ??
			#LVCFMT_COL_HAS_IMAGES  = 32768 ## header sends WM_DRAWITEM
			try: 
				lvc.fmt= {'left':0,'right':1,'ceneter':2,'bitmapright':4096}[align]
			except: raise ValueError("invalid flag: %s" % align)
		result = self.SendMessage(self.Hwnd, self.Msg.LVM_INSERTCOLUMN, columno, byref(lvc))
		if result > -1: return result
		raise RuntimeError("could not insert column")
	
	def GetColumnCount(self):
		SM = self.SendMessage
		LVM_GETCOLUMN = self.Msg.LVM_GETCOLUMN
		lvc = LV_COLUMN()
		lvc.mask = lvc.LVCF_SUBITEM
		lvc.iSubItem = 0
		i = 0
		while SM(self.Hwnd, LVM_GETCOLUMN, i, byref(lvc)):
			i += 1
			lvc.iSubItem  = i
		return i
	
	def IterColumns(self):
		SM = self.SendMessage
		LVM_GETCOLUMN = self.Msg.LVM_GETCOLUMN
		lvc = LV_COLUMN()
		lvc.mask = lvc.LVCF_SUBITEM
		lvc.iSubItem = 0
		i = 0
		while SM(self.Hwnd, LVM_GETCOLUMN, i, byref(lvc)):
			yield i
			i += 1
			lvc.iSubItem  = i
		
	def GetColumnText(self, columno):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_TEXT
		lvc.pszText = addressof(self._client_buffer)
		lvc.cchTextMax = sizeof(self._client_buffer)
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETCOLUMN, columno, byref(lvc)):
			raise RuntimeError("could not retrieve column text")
		return self._client_buffer.value
	
	def SetColumnText(self, columno, text):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_TEXT
		lvc.pszText = lvc.pszText =  self._client_TruncText(text)
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETCOLUMN, columno, byref(lvc)):
			raise RuntimeError("could not set column text")
	
	def GetColumnImage(self, columno=0):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_IMAGE
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETCOLUMN, columno, byref(lvc)):
			raise RuntimeError("could not retrieve column image")
		return lvc.iImage
	
	def SetColumnImage(self, columno, iImage):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_IMAGE
		lvc.iImage= iImage
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETCOLUMN, columno, byref(lvc)):
			raise RuntimeError("could not set column image")
			
	def GetColumnWidth(self, columno=0):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_WIDTH	
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETCOLUMN, columno, byref(lvc)):
			raise RuntimeError("could not retrieve column width")
		return lvc.cx
	
	def SetColumnWidth(self, columno, width):
		if width=='autosize': width= -1					# LVSCW_AUTOSIZE
		elif width=='autosizeheader': width= -2	 #	LVSCW_AUTOSIZE_USEHEADER
		elif not isinstance(width, (int, long)):
			raise ValueError("invalid flag: %s" % flag)
		if self.GetStyleL('style') & self.Style.LVS_LIST: columnno= -1
		self.SendMessage(self.Hwnd, self.Msg.LVM_SETCOLUMNWIDTH, columno, MAKELONG(width, 0))
		
			
	def SetColumnOrder(self, *order):
		arr = (INT*len(order))(*order)
		if not self.SendMessage(self.Hwnd, 				
						self.Msg.LVM_SETCOLUMNORDERARRAY,
						len(arr), 
						byref(arr)):
			raise RuntimeError("could not set column order")
					
	def GetColumnOrder(self, columno=0):
		arr = (INT*self.GetColumnCount())()
		if not self.SendMessage(self.Hwnd, 				
						self.Msg.LVM_GETCOLUMNORDERARRAY,
						len(arr), 
						byref(arr)):
			raise RuntimeError("could not retrieve column order")
		return list(arr)
	
		
	def ColumnIndexToOrder(self, i):
		lvc=LV_COLUMN()
		lvc.mask = lvc.LVCF_ORDER	
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETCOLUMN, i, byref(lvc)):
			raise RuntimeError("could not set column order index")
		return lvc.iOrder
		
	
	
	def RemoveColumn(self, columnno):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_DELETECOLUMN, columnno, 0):
			raise RuntimeError("could not delete column")
	
	def ClearColumns(self):
		for i in range(self.GetColumnCount())[::-1]:
			self.RemoveColumn(i)
	
	#-----------------------------------------------------------------------
	# item methods

	def Item(self, text=None, iImage=None, lp=None, iStateImage=0, iOverlayImage= 0):
		return self.InsertItem(self.__len__(), text, iImage, lp, iStateImage, iOverlayImage)
			
	
	def InsertItem(self, lineno, text=None, iImage=None, lp=None, iStateImage=0, iOverlayImage= 0):
		lvi =LV_ITEM()
		
		if text != None:
			lvi.mask   |= lvi.LVIF_TEXT
			if text==-1: lvi.pszText= -1
			else: lvi.pszText= self._client_TruncText(text)
		lvi.iItem= lineno
		if iImage != None:
			lvi.mask  |= lvi.LVIF_IMAGE
			lvi.iImage=iImage
		if lp != None:
			lvi.mask   |= lvi.LVIF_PARAM
			lvi.lParam= lp
		if iStateImage or iOverlayImage:
			lvi.mask |= lvi.LVIF_STATE
			lvi.state= INDEXTOSTATEIMAGEMASK(iStateImage) |	\
								INDEXTOOVERLAYMASK(iOverlayImage)
		#
		# TODO item indent
		#
		result = self.SendMessage(self.Hwnd, self.Msg.LVM_INSERTITEM, lineno, byref(lvi))
		if result > -1: return result
		raise RuntimeError("could not insert item")
		
	
# Not shure if to take this in
# 
#	def SetItem(self, lineno, columnno, text=None, iImage=None, lp=None, iStateImage=0):
#		lvi =LV_ITEM()
#		lvi.iItem= lineno
#		lvi.iSubItem= columnno
#		if text !=None:
#			lvi.mask   |= lvi.LVIF_TEXT
#			if text==-1: lvi.pszText= -1
#			else: lvi.pszText= self._client_TruncText(text)
#		if iImage != None:
#			lvi.mask  |= lvi.LVIF_IMAGE
#			lvi.iImage=iImage
#		if lp != None:
#			lvi.mask   |= lvi.LVIF_PARAM
#			lvi.lParam= lp
#		if iStateImage:
#			lvi.mask |= lvi.LVIF_STATE
#			lvi.state= INDEXTOSTATEIMAGEMASK(iStateImage)
#		result = self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEM, lineno, byref(lvi))
#		if result > -1: return result
#		raise "could not set item"
		
	
	
	def RemoveItem(self, lineno):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_DELETEITEM, lineno, 0):
			raise RuntimeError("could not remove item")
	
	def SetItemText(self, lineno, columnno, text):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_TEXT
		lvi.pszText = self._client_TruncText(text)
		lvi.iItem =lineno
		lvi.iSubItem = columnno
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEM, lineno, byref(lvi)):
			raise RuntimeError("could not set item text")
	
	def GetItemText(self, lineno, columnno):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_TEXT
		lvi.iItem = lineno
		lvi.iSubItem = columnno
		lvi.pszText = addressof(self._client_buffer)
		lvi.cchTextMax = sizeof(self._client_buffer)
		if not self.SendMessage(self.Hwnd,self.Msg.LVM_GETITEM,  lineno, byref(lvi)):
			raise RuntimeError("could not retrieve item text")
		return self._client_buffer.value

	def SetItemImage(self,lineno, columno,  iImage):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_IMAGE 
		lvi.iItem = lineno
		lvi.iSubItem = columno
		lvi.iImage = iImage
		if not self.SendMessage(self.Hwnd,self.Msg.LVM_SETITEM,  lineno, byref(lvi)):
			raise RuntimeError("could not set image")
		return lvi.iImage
	
	def GetItemImage(self, lineno, columno):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_IMAGE 
		lvi.iItem = lineno
		lvi.iSubItem = columno
		if not self.SendMessage(self.Hwnd,self.Msg.LVM_GETITEM,  lineno, byref(lvi)):
			raise RuntimeError("could not retrieve item image")
		return lvi.iImage
	
	def GetItemLparam(self, lineno):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_PARAM
		lvi.iItem = lineno
		if not self.SendMessage(self.Hwnd,self.Msg.LVM_GETITEM,  lineno, byref(lvi)):
			raise RuntimeError("could not retrieve item lParam")
		return lvi.lParam

	def SetItemLparam(self, lineno, lparam):
		lvi =LV_ITEM()
		lvi.mask = lvi.LVIF_PARAM
		lvi.iItem = lineno
		lvi.lParam = lparam
		if not self.SendMessage(self.Hwnd,self.Msg.LVM_SETITEM,  lineno, byref(lvi)):
			raise RuntimeError("could not retrieve item image")
		return lvi.lParam
		
	def GetItemPos(self, i):
		pt=POINT()
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMPOSITION, i, byref(pt)):
			raise RuntimeError("could not retrieve item position")
		return pt
		
	def SetItemStateImage(self, i, iStateImage):
		LVIS_STATEIMAGEMASK    = 61440
		lvi =LV_ITEM()
		lvi.mask   = lvi.LVIF_STATE
		lvi.stateMask = LVIS_STATEIMAGEMASK
		lvi.state = INDEXTOSTATEIMAGEMASK(iStateImage)
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, i, byref(lvi)):
			raise RuntimeError("could not set state image")
				
	def GetItemStateImage(self, i):
		LVIS_STATEIMAGEMASK    = 61440
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, i, LVIS_STATEIMAGEMASK)
		return (result >> 12)
			
	def SetItemOverlayImage(self, i, iOverlImage):
		LVIS_OVERLAYMASK     =   0x0F00
		lvi =LV_ITEM()
		lvi.mask   = lvi.LVIF_STATE
		lvi.stateMask = LVIS_OVERLAYMASK
		lvi.state = INDEXTOOVERLAYMASK(iOverlayImage)
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, i, byref(lvi)):
			raise RuntimeError("could not set state image")
				
	def GetItemOverlayImage(self, i):
		LVIS_OVERLAYMASK     =   0x0F00
		
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, i, LVIS_OVERLAYMASK)
		return (result >> 8)
			
	
	
	
	def GetItemRect(self, lineno, columno):
		rc = RECT()	# LVIR_BOUNDS 
		if columno:
			rc.top=columno
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETSUBITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		else:
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		return rc
	
	def GetItemIconRect(self, lineno, columno):
		rc = RECT(1)	# LVIR_ICON
		if columno: 
			rc.top=columno
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETSUBITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		else:
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		return rc

	def GetItemLabelRect(self, lineno, columno):
		rc = RECT(2)	# LVIR_LABEL
		if columno: 
			rc.top=columno
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETSUBITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		else:
			if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMRECT, lineno, byref(rc)):
				raise RuntimeError("could not retrieve item position")
		return rc

	def GetItemSelectedRect(self, lineno):
		rc = RECT(3)	# LVIR_SELECTBOUNDS
		
		# not supportrd for subitems
		#if columno: 
		#	rc.top=columno
		#	if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETSUBITEMRECT, lineno, byref(rc)):
		#		raise "could not retrieve item position"
		#else:
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMRECT, lineno, byref(rc)):
			raise RuntimeError("could not retrieve item position")
		return rc
	
	def __len__(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMCOUNT, 0, 0)

	def Clear(self):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_DELETEALLITEMS, 0, 0):
			raise RuntimeError("could not clear items")
			

	#-----------------------------------------------------------------------
	# search and find
	
	def Find(self, string, start=-1, wrap=False):
		lfi = LVFINDINFO()
		lfi.flags = lfi.LVFI_STRING|lfi.LVFI_PARTIAL
		if wrap:	lfi.flags |= lfi.LVFI_PARTIAL
		lfi.psz = string
		result = self.SendMessage(self.Hwnd,
					self.Msg.LVM_FINDITEM, start,	byref(lfi))
		if result > -1: return result
			
	def FindExact(self, string, start=-1, wrap=False):
		lfi = LVFINDINFO()
		lfi.flags = lfi.LVFI_STRING
		if wrap:	lfi.flags |= lfi.LVFI_WRAP
		lfi.psz = string
		result = self.SendMessage(self.Hwnd,
					self.Msg.LVM_FINDITEM, start,	byref(lfi))
		if result > -1: return result
		
	def FindLparam(self, lp, start=-1, wrap=False):
		lfi = LVFINDINFO()
		lfi.flags = lfi.LVFI_PARAM
		if wrap:	lfi.flags |= lfi.LVFI_WRAP
		lfi.lParam = lp
		result = self.SendMessage(self.Hwnd,
					self.Msg.LVM_FINDITEM, start,	byref(lfi))
		if result > -1: return result
		
	def FindXY(self, x, y, start=-1, wrap=True):
		lfi = LVFINDINFO()
		lfi.flags = lfi.LVFI_NEARESTXY 
		if wrap:	lfi.flags |= lfi.LVFI_WRAP
		VK_UP       = 38
		VK_DOWN       = 40
		lfi.pt = x, y
		lfi.vkDirection =VK_DOWN
		result = self.SendMessage(self.Hwnd, self.Msg.LVM_FINDITEM, start, byref(lfi))
		
		if result > -1: return result
		
	
	
	#-----------------------------------------------------------------
	# selecting and scrolling
	#
	# LVIS_GLOW              = 16		## ??
	# LVIS_ACTIVATING        = 32	 ## ??
	#
		
	def SelectItem(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = lvi.LVIS_SELECTED 
		lvi.state = lvi.LVIS_SELECTED 
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise RuntimeError("could not select item")
		
	def IsItemSelected(self, lineno):
		#LVIS_SELECTED        =   2
		return bool( self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, lineno, 2))
				
	def GetSelectedItem(self):
		LVNI_SELECTED          = 2
		result = self.SendMessage(self.Hwnd, self.Msg.LVM_GETNEXTITEM, -1, LVNI_SELECTED)
		if result > -1: return result
	
	def DeselectItem(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = lvi.LVIS_SELECTED 
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise RuntimeError("could not deselect item")

	def SetFocusItem(self, lineno):
		lvi = LV_ITEM()
		lvi.stateMask = 1	# LVIS_FOCUSED
		lvi.state = 1			#  LVIS_FOCUSED
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not set focus")
	
	def ItemHasFocus(self, lineno):
		#VIS_FOCUSED           = 1
		return bool(self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, lineno, 1))
			
	def GetFocusItem(self):
		LVNI_FOCUSED           = 1
		result=self.SendMessage(self.Hwnd, self.Msg.LVM_GETNEXTITEM, 0, LVNI_FOCUSED)
		if result > -1: return result
	
	def RemoveItemFocus(self, lineno):
		lvi = LV_ITEM()
		lvi.stateMask = 1	# LVIS_FOCUSED
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not remove focus")
	
		
	def CutSelectItem(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = 4		# LVIS_CUT
		lvi.state = 4				# LVIS_CUT
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not cut select item")
	
	def IsItemCutSelected(self, lineno):
		#LVIS_CUT               = 4
		return bool(self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, lineno, 4))
				
	def RemoveItemCutSelect(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = 4		# LVIS_CUT
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not remove cut selection")
	
	def DropHilightItem(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = 8		# LVIS_DROPHILITED
		lvi.state = 8				# LVIS_DROPHILITED
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not cut select item")
		
	def IsItemDropHilighted(self, lineno):
		#LVIS_DROPHILITED      = 8
		return bool(self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSTATE, lineno, 8))
			
	def RemoveItemDropHilight(self, lineno=-1):
		lvi = LV_ITEM()
		lvi.stateMask = 8		# LVIS_DROPHILITED
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMSTATE, lineno, byref(lvi)):
			raise  RuntimeError("could not cut select item")
		
		
	def GetSelectedCount(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETSELECTEDCOUNT, 0, 0)


	def IterSelected(self):
		LVNI_SELECTED          = 2
		LVM_GETNEXTITEM=self.Msg.LVM_GETNEXTITEM
		SM = self.SendMessage
		lineno = -1
		for i in range(self.GetSelectedCount()):
			lineno =  SM(self.Hwnd, LVM_GETNEXTITEM, lineno, LVNI_SELECTED)
			yield lineno

	def GetTopIndex(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETTOPINDEX, 0, 0)
	
	
	def Scroll(self, vScroll=0, hScroll=0):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SCROLL, hScroll, vScroll): raise RuntimeError("could not scroll listview")
	
	def EnshureVisible(self, lineno):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_ENSUREVISIBLE, lineno, 1):
			raise RuntimeError("could not scroll item into view")
	

	#-----------------------------------------------------------------
	# listview methods
	
	def Reset(self):
		self.Clear()
		self.ClearColumns()
		
	def ItemHittest(self, x, y):
		pt = POINT(x, y)
		user32.ScreenToClient(self.Hwnd, byref(pt))
		lvh = LVHITTESTINFO(pt)
		result=self.SendMessage(self.Hwnd, self.Msg.LVM_SUBITEMHITTEST, 0, byref(lvh))
		out= [result, lvh.iSubItem]
		if lvh.flags & (2|4|8): 
			out.append('item')
			if lvh.flags & 2: out.append('icon')		# LVHT_ONITEMICON
			if lvh.flags & 4: out.append('label')		# LVHT_ONITEMLABEL
			if lvh.flags==8: out.append('state')		# LVHT_ONITEMSTATEICON
		if lvh.flags & 1:	 out.append('nowhere')	# LVHT_NOWHERE
		if result >-1: return out
			
	def GetStringWidth(self, *strings):
		maxW=0
		for i in strings:
			maxW=max(maxW, 
									self.SendMessage(self.Hwnd, self.Msg.LVM_GETSTRINGWIDTH, 0, i))
		return maxW
	
	def RedrawItems(self, nFirst=0, nLast=-1):
		if nLast==-1:	nLast=self.__len__()-1
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_REDRAWITEMS, nFirst, nLast):
			raise RuntimeError("could not redraw items")
		user32.UpdateWindow(self.Hwnd)		## required
	
	def GetBkColor(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETBKCOLOR, 0, 0)
		
	def SetBkColor(self, colorref):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETBKCOLOR, 0, colorref):
			raise RuntimeError("could not set background color")
		#self.RedrawClientArea()
	
	def GetTextColor(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETTEXTCOLOR, 0, 0)
	
	def SetTextColor(self, colorref):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETTEXTCOLOR, 0, colorref):
			raise RuntimeError("could not set background color")
		#self.RedrawClientArea()
	
	def GetTextBkColor(self):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_GETTEXTBKCOLOR, 0, 0)
	
	def SetTextBkColor(self, colorref):
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_SETTEXTBKCOLOR, 0, colorref):
			raise RuntimeError("could not set background color")
		self.RedrawClientArea()
	
	
	def GetHeaderControl(self):
		hwndHd = self.SendMessage(self.Hwnd,
					self.Msg.LVM_GETHEADER, 0, 0)
		if not hwndHd: raise RuntimeError("could not retrieve header control")
		## do not sublass 
		
		hd= HeaderFromHandle(hwndHd)
		fw.SetFlagMsgReflect(hd, False)
		return hd
	
	def GetEditControl(self):
		hwndEdit = self.SendMessage(self.Hwnd,
					self.Msg.LVM_GETEDITCONTROL, 0, 0)
		if not hwndEdit: raise RuntimeError("could not retrieve edit control")
		
		txt= TextinFromHandle(hwndEdit)
		fw.SetFlagMsgReflect(txt, False)
		return txt
		
	
	def EditLabel(self, lineno):
		hwndEdit = self.SendMessage(self.Hwnd,
					self.Msg.LVM_EDITLABEL, lineno, 0)
		#if not hwndEdit: raise RuntimeError("could not edit label")
		#return TextinFromHandle(hwndEdit)
	
	def SetItemCount(self, n, noinvalidate=False, noscroll=False):
		flag = 0
		if noinvalidate: flag |= 1
		if noscroll: flag |= 2
		self.SendMessage(self.Hwnd, self.Msg.LVM_SETITEMCOUNT , n, flag)
	
	def SetImagelistSmall(self, Imagelist=None):
		LVSIL_SMALL            = 1
		if Imagelist !=None: lp = Imagelist.handle
		else: lp=0
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_SETIMAGELIST, LVSIL_SMALL, lp)
		if result: return result
	
	def GetImagelistSmall(self):
		LVSIL_SMALL            = 1
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETIMAGELIST, LVSIL_SMALL, 0)
		if result: return result
		
	def SetImagelistNormal(self, Imagelist=None):
		LVSIL_NORMAL  = 0
		if Imagelist !=None: 
			lp = Imagelist.handle
		else: 
			lp=0
		result= self.SendMessage(self.Hwnd, 
		self.Msg.LVM_SETIMAGELIST, LVSIL_NORMAL, lp)
		if result: return result

	def GetImagelistNormal(self):
		LVSIL_NORMAL           = 0
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETIMAGELIST, LVSIL_NORMAL, 0)
		if result: return result
	
	def SetImagelistState(self, Imagelist=None):
		LVSIL_STATE  = 2
		if Imagelist !=None: lp = Imagelist.handle
		else: lp=0
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_SETIMAGELIST, LVSIL_STATE, lp)
		if result: return result
	
	def GetImagelistState(self):
		LVSIL_STATE            = 2
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETIMAGELIST, LVSIL_STATE, 0)
		if result: return result
	
	
	
	def ApproximateViewRect(self, nItems):
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_APPROXIMATEVIEWRECT, nItems, 0)
		return LOWORD(result), HIWORD(result)
		
	def GetPageCount(self):
		return self.SendMessage(self.Hwnd,self.Msg.LVM_GETCOUNTPERPAGE, 0, 0)
	
	def StateToString(self, state):
		out= []
		if state & 1: out.append('focused')				# LVIS_FOCUSED
		if state & 2: out.append('selected')				# LVIS_SELECTED
		if state & 4: out.append('cuthilighted')		# LVIS_CUT
		if state & 8: out.append('drophilighted')	# LVIS_DROPHILITED
		if state & 16: out.append('glowing')			# LVIS_GLOW
		if state & 32: out.append('activating')			# LVIS_ACTIVATING
		return out
	
	
	
	#**************************************************
	# listview 'icon' methods
	
	def SetTooltips(self, tooltip):
		return self.SendMessage(self.Hwnd, self.Msg.LVM_SETTOOLTIPS, 0, tooltip.Hwnd)

	def GetTooltips(self):
		result= self.SendMessage(self.Hwnd, self.Msg.LVM_GETTOOLTIPS, 0, 0)
		if result: return result
	
	
	def Arrange(self, flag=0):
		"""For listview 'icon' style."""
		if flag:
			if flag=='left': flagg=1	 # LVA_ALIGNLEFT
			elif flag=='top': flag=2	# LVA_ALIGNTOP
			elif flag=='snaptogrid': flag=5	# LVA_SNAPTOGRID
			else: raise ValueError("invalid flag: %s" % flag)
		else: flag=0
		if not self.SendMessage(self.Hwnd, self.Msg.LVM_ARRANGE, flag, 0):
			raise RuntimeError("could not arrange items")			
	
	# can't get hover to work
	#def GetHoverTime(self):
	#	return self.SendMessage(self.Hwnd, self.Msg.LVM_GETHOVERTIME , 0, 0)
	
	#def GetCallbackMask(self):
	#	return self.SendMessage(self.Hwnd,
	#			self.Msg.LVM_GETCALLBACKMASK, 0, 0)						

	#def SetIconSpacing(self, w=0, h=0):
	#	"""Sets horizontal and vertical icon spacing
	#	for 'icon' and 'smallicon' listviews. For all others 
	#	this has no effect.
	#	You can set w and/or h to -1 to switch back to system
	#	default. w or h set to 0 will keep the current value.
	#	Does not work on my machine (win98)."""
	#	result=self.SendMessage(self.Hwnd, self.Msg.LVM_SETICONSPACING, 0, MAKELONG(w, h))
	#	return (HIWORD(result), LOWORD(result))
		
#	def GetItemSpacing(self):
#			"""Retrieves horizontal and vertical icon spacing
#			for 'icon' and 'smallicon' listviews as tuple(w, h). For all others return value is allways none."""
#			style =  self.GetStyleL('style')
#			#if style & 3 == 0:	# LVS_ICON
#			#	flag=0
#			if style & 3 == 2:	# LVS_SMALLICON:
#				flag=1
#			else:
#				flag= 0
#			
#			#else: return None
#			result=self.SendMessage(self.Hwnd, self.Msg.LVM_GETITEMSPACING , flag, 0)
#			print 'xxx', result
#			return (HIWORD(result), LOWORD(result))


