
from wnd.controls.listview.header import *

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class ListviewMessageHandler:
	
		
	def onMESSAGE(self, hwnd, msg, wp, lp):
		
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
	
				if msgr.msg==self.Msg.WM_NOTIFY:
					# custom draw
					nm=NMHDR.from_address(msgr.lParam)
					notify= nm.code
					if notify == self.Msg.NM_CUSTOMDRAW:
						cd =  NMLVCUSTOMDRAW.from_address(msgr.lParam)
						result= self.onMSG(hwnd, "customdraw", 0, cd)
						if result !=None: return result
						return 0
					
					elif notify==self.Msg.LVN_GETDISPINFO or notify==self.Msg.LVN_GETDISPINFOW:
						di=NMLVDISPINFO.from_address(msgr.lParam)
						result= self.onMSG(hwnd, "getdispinfo", (di.item.iItem, di.item.iSubItem), di.item.lParam)
						if result:
							if len(result)==2:
								if di.item.mask & LVIF_TEXT:
									if result[0]:
										di.item.pszText= self._client_TruncText(result[0])
								if di.item.mask & LVIF_IMAGE:
									di.item.iImage= result[1]
							else:
								raise "expected 2-tuple: (%s) missing" % 2-len(result)
						return 0
						
					elif notify ==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasecapture", 0, 0)
					elif notify == self.Msg.NM_CLICK:
						self.onMSG(hwnd, "click", 0, 0)
					elif notify== self.Msg.NM_RCLICK:
						self.onMSG(hwnd, "rmbup", 0, 0)
					elif notify==self.Msg.NM_DBLCLK:
						self.onMSG(hwnd, "lmbdouble", 0, 0)
					elif notify==self.Msg.LVN_BEGINDRAG:
						nmlv=NMLISTVIEW.from_address(msgr.lParam)
						self.onMSG(hwnd, "begindrag", 0, (nmlv.iItem, nmlv.iSubItem))
					elif notify==self.Msg.LVN_BEGINRDRAG:
						nmlv=NMLISTVIEW.from_address(msgr.lParam)
						self.onMSG(hwnd, "beginrdrag", 0, (nmlv.iItem, nmlv.iSubItem))
					elif notify==self.Msg.LVN_COLUMNCLICK :
						nml=NMLISTVIEW.from_address(msgr.lParam)
						self.onMSG(hwnd, "columnclick", 0, nml.iSubItem)
					
					#elif notify==self.Msg.LVN_ITEMCHANGING:
					#	nml=NMLISTVIEW.from_address(msgr.lParam)
					#	state=[]
					#	for name, val in LV_ITEMSTATES.items():
					#		if nml.uNewState & val:
					#			state.append(name)
					#	self.onMSG(hwnd, "itemchanging", nml.iItem, state)
					
					elif notify==self.Msg.LVN_ITEMCHANGED:
						nml=NMLISTVIEW.from_address(msgr.lParam)
						self.onMSG(hwnd, "itemchanged", nml.iItem, (nml.uOldState, nml.uNewState))
										
					elif notify==self.Msg.LVN_BEGINLABELEDIT or notify==self.Msg.LVN_BEGINLABELEDITW:
						disp = NMLVDISPINFO.from_address(msgr.lParam)
						# do not use disp.item.pszText here
						#
						result=self.onMSG(self.Hwnd, 
									"beginlabeledit", 
									self.GetItemText(disp.item.iItem, 0),
									(disp.item.iItem, disp.item.iSubItem))
						if result==False: return 1
						return 0
					
					elif notify == self.Msg.LVN_ENDLABELEDIT or notify == self.Msg.LVN_ENDLABELEDITW:
						disp = NMLVDISPINFO.from_address(msgr.lParam)
						text = c_char_p(disp.item.pszText).value
						result=self.onMSG(self.Hwnd, 
										"endlabeledit", 
										text,
										(disp.item.iItem, disp.item.iSubItem))
						if result==False: return 0
						if text:
							if len(text) > self.GetTextMax():
								# raise "max text exceedded"
								return 0
						return 1
					
					elif notify == self.Msg.LVN_KEYDOWN:
						nmkey = NMKEY.from_address(msgr.lParam)
						if nmkey.nVKey == 32:		# VK_SPACE
							self.onMSG(hwnd, "space", 0, 0)
							return 1
						elif nmkey.nVKey == 13:		# VK_RETURN
							self.onMSG(hwnd, "return", 0, 0)
							return 1
						elif nmkey.nVKey in self._client_keyboardMsgs:
							result = self.onMSG(hwnd, "key", nmkey.nVKey, nmkey.uFlags)
							if result != None: return result
						
			return 0 # default
		
		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
								
		elif msg==self.Msg.WM_STYLECHANGING:
			# set LVS_SHAREIMAGELISTS as unchangable style
			if wp==(1l<<32) - 16:		# GWL_STYLE
				LVS_SHAREIMAGELISTS = 64
				sst = STYLESTRUCT.from_address(lp)
				sst.styleNew = sst.styleNew|LVS_SHAREIMAGELISTS
				return 0
		elif msg==self.Msg.WM_LBUTTONDOWN:
			self.onMSG(hwnd, "lmbdown", wp, (LOWORD(lp), HIWORD(lp)))
		elif msg==self.Msg.WM_LBUTTONUP:
			self.onMSG(hwnd, "lmbup", wp, (LOWORD(lp), HIWORD(lp)))
		
		elif msg==self.Msg.WM_SETFOCUS:
			self.onMSG(hwnd, "setfocus", wp, lp)
		elif msg==self.Msg.WM_KILLFOCUS:
			self.onMSG(hwnd, "killfocus", wp, lp)
		
		
