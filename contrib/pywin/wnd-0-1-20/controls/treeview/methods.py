
from wnd.controls.treeview.header import * 
from wnd.controls.treeview.messagehandler import TreeviewMessageHandler 


#***********************************************
from ctypes import *


class TreeviewMethods(TreeviewMessageHandler ):
	
			
	#--------------------------------------------------------------------
	def SetTextMax(self, n):
		self._client_buffer = create_string_buffer(n) +1
	
	def GetTextMax(self):
		return sizeof(self._client_buffer) -1
	
	def _client_TruncText(self, text):
		"""Truncates text to _client_buffer. Return value is
		the address of the buffer."""
		#if text==-1: return text
		n = len(text)
		szeof = sizeof(self._client_buffer) -1
		if n > szeof: text = '%s...\x00' % text[:szeof-3]
		else: text = '%s\x00' % text
		self._client_buffer.raw = text +'\x00'
		return addressof(self._client_buffer)			
				

	
	def _client_ItemHasState(self, handle, state):
		"""Helper method. Returns True or False wether an item
		has the specified state. State is one of the TVIS_* flags"""
		tvi = TVITEMEX()
		tvi.mask = TVIF_HANDLE | TVIF_STATE
		tvi.hItem = handle
		tvi.stateMask = TVIF_HANDLE | state
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			return -1
		return bool(tvi.state & state)
			
	#------------------------------------------------------------------------
	# 
	
	def GetRoot(self):
		result= handle = self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM , TVGN_ROOT, 0)
		if result: return result
	
	def __len__(self):
		return self.SendMessage(self.Hwnd, self.Msg.TVM_GETCOUNT, 0, 0)
	
	def Clear(self):
		"""Deletes all items in the treeview."""
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_DELETEITEM, 0, 0):
			raise RuntimeError("could not clear treeview")
	
	def Item(self, hParent, text, iImage=None, iSelectedImage=None, iStateImage=None, lp=None, fInsert='last', integral=None, childinfo=False):
		
		if not isinstance(fInsert, (int, long)):
			if fInsert=='last': fInsert= 294901762				# TVI_LAST 
			elif fInsert=='first': fInsert= 4294901761		# TVI_FIRST 
			elif fInsert=='sort': fInsert= 4294901763		# TVI_SORT
			else: raise ValueError("invalid flag: %s" % fInsert)
		
		tvin = TVINSERTSTRUCT()
		tvin.hParent = hParent or 0
		tvin.hInsertAfter = fInsert
		if text:
			tvin.item.mask = TVIF_TEXT	
			if text==-1:
				tvin.item.pszText = -1
			else:		
				tvin.item.pszText =  self._client_TruncText(text)
						
		if iImage != None:
			tvin.item.mask |= TVIF_IMAGE
			tvin.item.iImage = iImage
		if iSelectedImage != None:
			tvin.item.mask |= TVIF_SELECTEDIMAGE
			tvin.item.iSelectedImage = iSelectedImage
		if iStateImage != None:
			tvin.item.mask |= TVIF_STATE
			tvin.item.stateMask = TVIS_STATEIMAGEMASK
			tvin.item.state=INDEXTOSTATEIMAGEMASK(iStateImage)
		if lp !=None:
			tvin.item.mask |= TVIF_PARAM 
			tvin.item.lParam=lp
		if integral != None:
			tvin.item.mask |= TVIF_INTEGRAL
			tvin.item.iIntegral= integral
		if childinfo:
			tvin.item.mask |=TVIF_CHILDREN
			if childinfo==-1:
				tvin.item.cChildren = -1
			else:
				tvin.item.cChildren = 1
							
		handle = self.SendMessage(self.Hwnd, self.Msg.TVM_INSERTITEM, 0, byref(tvin))
		if handle: return handle
		raise RuntimeError("could not add item")
		
	
	def ItemFromPath(self, path, iImage=None, iSelectedImage=None, iStateImage=None, lp=None, fInsert='last', integral=None):
		try:									# item level
			nextname = path.next()
		except AttributeError:				# root level
			path =self._client_IterPath.setpath(path)
			nextname = path.next()
		except StopIteration:
			return path.hParent			# return handle to the user
					
		# see if there is alreaddy a child named 'nextname', else create it
		handle= None
		for i in self.IterChildren(path.hParent):
			if self.GetItemText(i)==nextname:
				handle= i
				break
		if not handle:
			 handle= self.Item(path.hParent, nextname,  iImage, iSelectedImage, iStateImage, lp, fInsert)
		path.hParent= handle
		return self.ItemFromPath(path, iImage, iSelectedImage, iStateImage, lp, fInsert,  integral)
	
	
	def IsPath(self, path):
		try:																	# item level
			nextname = path.next()
		except AttributeError:								# root level
			path = self._client_IterPath.setpath(path)
			nextname = path.next()
		except StopIteration:
			return True
		handle= None
		for i in self.IterChildren(path.hParent):
			if self.GetItemText(i)==nextname:
				handle= i
		if not handle:
			return False
		path.hParent= handle
		return self.IsPath(path)
				
	
	def HandleFromPath(self, path):
		try:										# item level
			nextname = path.next()
		except AttributeError:				# root level -- setup path iterator
			path =  self._client_IterPath.setpath(path)
			nextname = path.next()
		except StopIteration:
			return path.hParent	 # return the handle of the key
		handle= None
		for i in self.IterChildren(path.hParent):
			if self.GetItemText(i)==nextname:
				handle= i
		if not handle:
			raise KeyError('\\'.join(path.path))
		path.hParent= handle
		result = self.HandleFromPath(path)		
		return result
	
	def GetItemPath(self, handle):
		out = [self.GetItemText(handle), ]
		while True:
			handle = self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM, TVGN_PARENT, handle)
			if not handle: break
			out.insert(0, self.GetItemText(handle))
			handle = handle
		return '\\'.join(out)
	#----------------------------------------------------------------------
	# items

	
	def GetItemIntegral(self, handle):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_INTEGRAL 
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve integral")
		return tvi.iIntegral
	
	def SetItemIntegral(self, handle, n):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_INTEGRAL 
		tvi.iIntegral= n
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set integral")
		
	
	def GetParentItem(self, handle):
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM, TVGN_PARENT, handle)
		if result: return result
		
		#path = self.GetItemPath(handle)
		#n = path.rfind('\\')
		#if n == -1:	return None
		#return self.GetItem(path[:n])
	
	def RemoveItem(self, handle):
		"""Removes a key from the treeview. If key is zero the treeview is
	cleared."""
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_DELETEITEM, 0, handle):
			raise 'could not delete key'
	
	def SetItemText(self, handle, text):
		tvi = TVITEMEX()
		tvi.mask=TVIF_TEXT |  TVIF_HANDLE
		tvi.hItem = handle
		tvi.pszText =  self._client_TruncText(text)
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set item text")		
	
	def GetItemText(self, handle):
		tvi = TVITEMEX()
		tvi.mask=TVIF_TEXT |  TVIF_HANDLE
		tvi.hItem = handle
		tvi.pszText=addressof(self._client_buffer)
		tvi.cchTextMax=sizeof(self._client_buffer)
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve item text")
		return self._client_buffer.value
		
	
	def SetItemLparam(self, handle, lp):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_PARAM 
		tvi.lParam=lp
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set lparam")
	
	def GetItemLparam(self, handle):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_PARAM 
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve lparam")
		return tvi.lParam
	
	def SetItemStateImage(self, handle, i):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_STATE
		tvi.stateMask = TVIS_STATEIMAGEMASK
		tvi.state=INDEXTOSTATEIMAGEMASK(i)
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set state image")

	def GetItemStateImage(self, handle):
		tvi = TVITEMEX()
		tvi.hItem = handle
		tvi.mask = TVIF_HANDLE | TVIF_STATE
		tvi.stateMask = TVIS_STATEIMAGEMASK
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve state image")
		return tvi.state >> 12
	
	def GetItemImage(self, handle):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_IMAGE
		tvi.hItem = handle
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve item image")
		return tvi.iImage
	
	def SetItemImage(self, handle, i, iSelectedImage=None):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_IMAGE
		tvi.hItem = handle
		tvi.iImage=i
		if iSelectedImage != None:
			tvi.mask |=TVIF_SELECTEDIMAGE
			tvi.iSelectedImage= iSelectedImage
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set item image")
			
	def GetItemSelectedImage(self, handle):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_SELECTEDIMAGE 
		tvi.hItem = handle
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve item selected image")
		return tvi.iSelectedImage

	def SetItemSelectedImage(self, handle, i):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_SELECTEDIMAGE 
		tvi.hItem = handle
		tvi.iSelectedImage =i
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve item image")
		return tvi.iImage
		
	def HasChildren(self, handle):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_CHILDREN 
		tvi.hItem = handle
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve child count")
		return bool(tvi.cChildren)
		
	def SetChildInfo(self, handle, value):
		tvi = TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_CHILDREN 
		tvi.hItem = handle
		if value ==-1:
			tvi.cChildren=-1
		else:
			tvi.cChildren= value and 1 or 0
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not retrieve child count")
		return bool(tvi.cChildren)
		
	
	
	#--------------------------------------------------------------------------
	# metrics

	def GetItemHeight(self):
		return self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEMHEIGHT, 0, 0)
	
	def SetItemHeight(self, n):
		return self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEMHEIGHT, n, 0)

	def GetItemRect(self, handle):
		rc = RECT(handle)
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEMRECT, 0, byref(rc)):
			raise RuntimeError("could not retrieve item rect")
		return rc
	
	def GetItemTextRect(self, handle):
		rc = RECT(handle)
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_GETITEMRECT, 1, byref(rc)):
			raise RuntimeError("could not retrieve item rect")
		return rc
	
	
	#-----------------------------------------------------------------------
	# item attributes 

	def IsSelected(self, handle):
		result=self._client_ItemHasState(handle, TVIS_SELECTED)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	def Select(self, handle):
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SELECTITEM , TVGN_CARET, handle):
			raise RuntimeError("could not select item")
	
	def GetSelected(self):
		handle =  self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM , TVGN_CARET, 0)
		if handle: return handle
	
	def Deselect(self):
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SELECTITEM , TVGN_CARET, 0):
			raise RuntimeError("could not deselect")
		
	
	def DropHilight(self, handle):
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SELECTITEM , TVGN_DROPHILITE, handle):
			raise RuntimeError("could not drop-hilight item")
	
	def RemoveDropHilight(self):
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SELECTITEM , TVGN_DROPHILITE, 0):
			raise "could not drag seklect item"
	
	def IsDropHilighted(self, handle):
		result=self._client_ItemHasState(handle, TVIS_DROPHILITED )
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	def GetDropHilighted(self):
		handle =  self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM , TVGN_DROPHILITE, 0)
		if handle: return handle
	
		
		
	def IsCutHilighted(self, handle):
		result=self._client_ItemHasState(handle, TVIS_CUT)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	def CutHilight(self, handle):
		tvi= TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_STATE 
		tvi.hItem = handle
		tvi.stateMask= TVIS_CUT
		tvi.state= TVIS_CUT
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set state")
	
	def RemoveCutHilight(self, handle):
		tvi= TVITEMEX()
		tvi.mask=TVIF_HANDLE | TVIF_STATE 
		tvi.hItem = handle
		tvi.stateMask= TVIS_CUT
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
			raise RuntimeError("could not set state")
	
	
	def IsBold(self, handle):
		result=self._client_ItemHasState(handle, TVIS_BOLD)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	
	#def SetBold(self, handle):
	#	tvi= TVITEMEX()
	#	tvi.mask=TVIF_HANDLE | TVIF_STATE 
	#	tvi.hItem = handle
	#	tvi.stateMask= TVIS_BOLD
	#	tvi.state= TVIS_BOLD
	#	if not self.SendMessage(self.Hwnd, self.Msg.TVM_SETITEM, 0, byref(tvi)):
	#		raise "could not set state"
			

	def EnshureVisible(self, handle):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_ENSUREVISIBLE, 0, handle))
			
	def Expand(self, handle):
		TVE_EXPAND  = 2
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_EXPAND, TVE_EXPAND, handle))
		
	def IsExpanded(self, handle):
		result=self._client_ItemHasState(handle, TVIS_EXPANDED)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
		
	def Collapse(self, handle):
		TVE_COLLAPSE   = 1
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_EXPAND, TVE_COLLAPSE, handle))
				
	def IsExpandedOnce(self, handle):
		result=self._client_ItemHasState(handle, TVIS_EXPANDEDONCE)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	def Toggle(self, handle):
		TVE_TOGGLE   = 3
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_EXPAND, TVE_TOGGLE, handle))
			
	def IsExpandedPartial(self, handle):
		result=self._client_ItemHasState(handle, TVIS_EXPANDPARTIAL)
		if result ==-1: raise RuntimeError("could not retrieve item state")
		return result
	
	def ExpandPartial(self, handle):
		flag = 2 | 16384	# TVE_EXPAND | TVE_EXPANDPARTIAL
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_EXPAND, flag, handle))
			
	def CollapseReset(self, handle):
		flag = 1 | 32768	# TVE_COLLAPSE | TVE_COLLAPSERESET 
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_EXPAND, flag, handle))
			
	#--------------------------------------------------------------------
	# misc methods
	
	def GetEditControl(self):
		hwndEdit = self.SendMessage(self.Hwnd,
					self.Msg.TVM_GETEDITCONTROL, 0, 0)
		if not hwndEdit: raise RuntimeError("could not retrieve edit control")
		txt= TextinFromHandle(hwndEdit)
		fw.SetFlagMsgReflect(txt, False)
		return txt
		
		
	def EditLabel(self, handle):
		if not self.SendMessage(self.Hwnd, self.Msg.TVM_EDITLABEL , 0, handle):
			raise RuntimeError("could not edit label")
	
	def EndEditLabel(self, cancel=False):
		return bool(self.SendMessage(self.Hwnd, self.Msg.TVM_ENDEDITLABELNOW, save and 1 or 0, 0))
	
	def ItemHittest(self, x, y):
		hi=TVHITTESTINFO()
		pt = POINT(x, y)
		user32.ScreenToClient(self.Hwnd, byref(pt))
		hi.pt= pt
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_HITTEST, 0, byref(hi))
		#TVHT_NOWHERE           = 1
		out=[hi.hItem, ]
		if hi.flags& 1: out.append('nowhere')
		if hi.flags& 2: out.append('onitemicon')
		if hi.flags& 4: out.append('onitemlabel')
		if hi.flags& 8: out.append('onitemindent')
		if hi.flags& 16: out.append('onitembutton')
		if hi.flags& 32: out.append('onitemright')
		if hi.flags& 64: out.append('onitemstateicon')
		if hi.flags& 256: out.append('above')
		if hi.flags& 512: out.append('below')
		if hi.flags& 1024: out.append('toright')
		if hi.flags& 2048: out.append('toleft')
		if hi.flags& (TVHT_ONITEMICON | TVHT_ONITEMLABEL | TVHT_ONITEMSTATEICON): out.append('onitem')
		return out


	
	#-----------------------------------------------------------------------
	# iterators		
			
	
	def _client_Iterator(self, iterator_type, handle):
		while True:
			handle = self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM, iterator_type, handle)
			if not handle: break
			yield handle
			handle=handle
	
	def IterSiblings(self, handle=0, revert=False):
		if revert:
			return self._client_Iterator(TVGN_PREVIOUS, handle)
		return self._client_Iterator(TVGN_NEXT, handle)
				
	def IterParents(self, handle=0):
		return self._client_Iterator(TVGN_PARENT, handle)
		
	def IterChildren(self, handle=0):
		handle = self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM , TVGN_CHILD, handle)
		if handle:
			yield handle
			for i in self._client_Iterator(TVGN_NEXT, handle):
				yield i
		
	def IterVisibleItems(self):
		handle = self.SendMessage(self.Hwnd, self.Msg.TVM_GETNEXTITEM , TVGN_FIRSTVISIBLE , 0)
		if handle:
			yield handle
			for i in self._client_Iterator(TVGN_NEXTVISIBLE , handle):
				yield i
	
	def Walk(self, handle=0, topdown=True):
		root= False
		if not handle:
			handle =  self.GetRoot()
			if not handle: return
			root= True
			
		if topdown:
			yield handle
		for a in self.IterChildren(handle):
			for b in self.Walk(a, topdown):
				yield b		
		if not topdown:
			yield handle
		
		if root:
			for c in self.IterSiblings(handle):
				for d in self.Walk(c, topdown):
					yield d
				
		
	#----------------------------------------------------------------------
	# sorting
	def Sort(self, handle):
		if not self.SendMessage(self.Hwnd,
			self.Msg.TVM_SORTCHILDREN , 0, handle):
			raise RuntimeError("colud not sort item")
	
	def _client_SortFunc(self, lp1, lp2, lp):
		if self._client_CompFunc: 
			return self._client_CompFunc(lp1, lp2, lp)
		return 0
	
	def SortCB(self, handle, callback, lp=0):
		self._client_CompFunc = callback
		tvs=TVSORTCB(handle, self._client_p_SortFunc, lp)
		self._client_CompFunc = callback
		result= self.SendMessage(self.Hwnd,
					self.Msg.TVM_SORTCHILDRENCB, 0, byref(tvs))
		self._client_CompFunc = None
		if not result: raise RuntimeError("colud not sort item")
	
	#------------------------------------------------------------------------
	# colors
	
	def SetBkColor(self, colorref):
		if colorref==None: colorref= -1		# default color
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_SETBKCOLOR,0,colorref)
		if result != -1: return result
		
	def SetTextColor(self, colorref):
		if colorref==None: colorref= -1		# default color
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_SETTEXTCOLOR,0,colorref)
		if result != -1: return result
	
	def GetInsertmarkColor(self):
		return  self.SendMessage(self.Hwnd, self.Msg.TVM_GETINSERTMARKCOLOR,0,0)
		
	def SetInsertmarkColor(self, colorref):
		"""Sets the color for the insertion mark.
		Todo: ??"""
		return self.SendMessage(self.Hwnd, self.Msg.TVM_SETINSERTMARKCOLOR, 0, colorref)
		
	#--------------------------------------------------------------------------
	# indent

	def GetIndent(self):
		return self.SendMessage(self.Hwnd, self.Msg.TVM_GETINDENT,0,0)
	
	def SetIndent(self, n):
		self.SendMessage(self.Hwnd, self.Msg.TVM_SETINDENT,n,0)

	#-------------------------------------------------------------------------------------
	# imagelists
	
	def SetImagelistNormal(self, Imagelist):
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_SETIMAGELIST, 0, Imagelist.handle)
		if result: return result
	
	def GetImagelistNormal(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_GETIMAGELIST, 0, 0)
		if result: return result	
	
	def SetImagelistState(self, Imagelist):
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_SETIMAGELIST, 2, Imagelist.handle)
		if result: return result

	def GetImagelistState(self):
		result= self.SendMessage(self.Hwnd, self.Msg.TVM_GETIMAGELIST, 2, 0)
		if result: return result	
	
