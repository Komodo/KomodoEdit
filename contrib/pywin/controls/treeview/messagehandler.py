
	# currently not implemented
				#
				# TVN_SINGLEEXPAND	# sounds like nonsense
				# TVN_GETINFOTIP
				# TVN_SETDISPINFO
				# TVN_SELCHANGED
				# TVN_ITEMEXPANDED
				# TVN_GETDISPINFO
				# NM_RDBLCLICK	# never seen this
				# NM_SETCURSOR 



from wnd.controls.treeview.header import * 

from ctypes import cdll, c_char_p
msvcrt = cdll.msvcrt
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	


class TreeviewMessageHandler:		

	def onMESSAGE(self, hwnd, msg, wp, lp):
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
				nm=NMTREEVIEW.from_address(msgr.lParam)
														
				
				# custom draw
				if nm.hdr.code == self.Msg.NM_CUSTOMDRAW:
					cd =  NMTVCUSTOMDRAW.from_address(msgr.lParam)
					result= self.onMSG(hwnd, "customdraw", 0, cd)
					if result !=None: return result
					return 0
					
				elif nm.hdr.code==self.Msg.TVN_GETDISPINFO or nm.hdr.code==self.Msg.TVN_GETDISPINFOW:
					di=NMTVDISPINFO.from_address(msgr.lParam)
					result= self.onMSG(hwnd, "getdispinfo", di.item.hItem, di.item.lParam)
					if result:
							if len(result)==4:
								if di.item.mask & TVIF_TEXT:
									if result[0]:
										di.item.pszText= self._client_TruncText(result[0])
								if di.item.mask & TVIF_IMAGE:
									di.item.iImage= result[1]
								if di.item.mask & TVIF_SELECTEDIMAGE:
									di.item.iSelectedImage= result[2]
								if di.item.mask & TVIF_CHILDREN:
									di.item.cChildren= result[2] and 1 or 0
							else:
								raise "expected 4-tuple: (%s) missing" % 4-len(result)
					return 0
					
										
					# still not quite shure how to handle this...
					# docs claim to copy the string into the buffer pointed to by 
					# di.item.pszText, but is it there, and what size is it ??
					
					result= self.onMSG(hwnd, "getdispinfo", di.item.hItem, di.item.lParam)
					if result:
						if len(result)==4:
							if di.item.mask & TVIF_TEXT:
								if result[0]:
									di.item.pszText= self._client_TruncText(result[0])
							if di.item.mask & TVIF_IMAGE:
								di.item.iImage= result[1]
							if di.item.mask & TVIF_SELECTEDIMAGE:
								di.item.iSelectedImage= result[2]
							if di.item.mask & TVIF_CHILDREN:
								di.item.cChildren= result[3] and 1 or 0
						else:
							raise "expected 4-tuple: (%s) missing" % 4-len(result)
					return 0
						
				elif nm.hdr.code==self.Msg.TVN_SETDISPINFO or nm.hdr.code==self.Msg.TVN_SETDISPINFOW:	
					# some bug here in the SDK docs...
					# I guess, this is only send if an items text changes 
					# in response to a labeledit. Other aspects changing do not 
					# seem to trigger ihis message.
					di=NMTVDISPINFO.from_address(msgr.lParam)
					if di.item.mask & TVIF_TEXT:
						text= c_char_p(di.item.pszText).value
					else: text= ''
					self.onMSG(hwnd, "setdispinfo", di.item.hItem, (di.item.lParam, text))
					
					return 0
					
									
				elif nm.hdr.code==self.Msg.TVN_ITEMEXPANDING:
					flag=None
					if nm.action==TVE_EXPAND: flag="expand"
					elif nm.action==TVE_EXPANDPARTIAL: 
						flag="expandpartial"
					elif nm.action==TVE_TOGGLE: flag="toggle"
					elif nm.action==TVE_COLLAPSE: flag="collapse"	
					elif nm.action==TVE_COLLAPSERESET:
						flag="collapsereset"
					result=self.onMSG(hwnd, "expand", flag, nm.itemNew.hItem)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_SELCHANGING or nm.hdr.code==self.Msg.TVN_SELCHANGINGW:
					result=self.onMSG(hwnd, "selchange", nm.itemOld.hItem, nm.itemNew.hItem)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_KEYDOWN:
					nmk=NMTVKEYDOWN.from_address(msgr.lParam)
					result=self.onMSG(hwnd, "key", nmk.wVKey, 0)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_BEGINLABELEDIT or nm.hdr.code==self.Msg.TVN_BEGINLABELEDITW:
					di=NMTVDISPINFO.from_address(msgr.lParam)
					if di.item.pszText:
						text= c_char_p(di.item.pszText).value
					else: text= None
					result=self.onMSG(hwnd, "beginlabeledit", 
									di.item.hItem, (di.item.lParam, text))
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_ENDLABELEDIT or nm.hdr.code==self.Msg.TVN_ENDLABELEDITW:
					di=NMTVDISPINFO.from_address(msgr.lParam)
					if di.item.pszText:
						text= c_char_p(di.item.pszText).value
						result=self.onMSG(hwnd, "endlabeledit", 
								di.item.hItem, (di.item.lParam, text))
						if result==False: return 0
						if text:
							if len(text) > self.GetTextMax():
								#raise "max text exceedded"		## ??
								return 0
						return 1
								
				elif nm.hdr.code==self.Msg.NM_CLICK:
					result=self.onMSG(hwnd, "click", 0, 0)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.NM_DBLCLK :
					result=self.onMSG(hwnd, "dblclick", 0, 0)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.NM_RCLICK:
					result=self.onMSG(hwnd, "rclick", 0, 0)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.NM_RETURN:
					result=self.onMSG(hwnd, "return", 0, 0)
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_BEGINDRAG:
					result=self.onMSG(hwnd, "begindrag", nm.itemNew.hItem,
									(nm.itemNew.lParam, nm.ptDrag))
					if result==False: return 1
					return 0
				elif nm.hdr.code==self.Msg.TVN_BEGINRDRAG:
					result=self.onMSG(hwnd, "beginrdrag", nm.itemNew.hItem,
									(nm.itemNew.lParam, nm.ptDrag))
					if result==False: return 1
					return 0
				
				elif nm.hdr.code==self.Msg.TVN_DELETEITEM:
					result=self.onMSG(hwnd, "removeitem",
									nm.itemOld.hItem, nm.itemOld.lParam)
					return 0
			return 0
		 	
		elif msg==self.Msg.WM_SETFOCUS:
			self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			self.onMSG(hwnd, "killfocus", wp, lp)
		

		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			