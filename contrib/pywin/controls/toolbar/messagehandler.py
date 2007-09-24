	

from wnd.controls.toolbar.header import (TBBUTTON,
																				byref,
																				NMHDR,
																				NMTOOLBAR,
																				NMMOUSE,
																				NMTBHOTITEM,
																				LOWORD,
																				HIWORD,
																				UINT_MAX,
																				POINT,
																				)
from wnd import fwtypes as fw
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

	
class ToolbarMsgHandler:	
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
				
		if msg==fw.WND_WM_NOTIFY:
			if wp==fw.WND_NM_MSGREFLECT:
				msgr= fw.WND_MSGREFLECT.from_address(lp)
				msgr.fReturn= self._base_fMsgReflect
		
				if msgr.msg==self.Msg.WM_COMMAND:
					self.onMSG(hwnd, "command", LOWORD(wp), 0)
					return 1
				
				elif msgr.msg==self.Msg.WM_NOTIFY:
					nm=NMHDR.from_address(msgr.lParam)
										
					# -->
					# handlers for rcustomisation dialog
					#
					if nm.code==self.Msg.TBN_BEGINADJUST:
						self._client_fAdjust= True
						if not self.snapshot:
							self.Write()
						self.onMSG(hwnd, "beginadjust", 0, 0)
						return 0
					
					elif nm.code==self.Msg.TBN_GETBUTTONINFO or nm.code==self.Msg.TBN_GETBUTTONINFOW:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						if self.snapshot:
							if nmtb.iItem >=0 and nmtb.iItem < len(self.snapshot.buttons):
								nmtb.tbButton = self.snapshot.buttons[nmtb.iItem]
								# TODO:
								# the customize dialog does not display
								# strings for items removed with iString==-1
								# How to get the local string here
								#
								#if nmtb.tbButton.iString==-1:
								##### string= '%s\x00' % string[:nmtb.cchText-2]
								#	s= 'separator\x00'
								#	if nmtb.cchText >= len(s):
								#		nmtb.pszText= s[:nmtb.cchText]
								return 1		
						return 0
				
					
					elif nm.code==self.Msg.TBN_QUERYINSERT:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						if self.onMSG(hwnd, "queryinsert", nmtb.tbButton.idCommand, 0)==False:	return 0
						return 1

					elif nm.code==self.Msg.TBN_QUERYDELETE:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						if self.onMSG(hwnd, "querydelete", nmtb.tbButton.idCommand, 0)==False:
							return 0
						return 1

					elif nm.code==self.Msg.TBN_DELETINGBUTTON:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						self.onMSG(hwnd, "deletingbutton", nmtb.tbButton.idCommand, 0)
						return 0
					
					elif nm.code==self.Msg.TBN_TOOLBARCHANGE:
						# make snapshot of user changes
						if self.snapshot:
							n= self.__len__()
							arr= (TBBUTTON*n)()
							for i in range(n):
								arr[i]= self._client_GetButton(i)
							self.snapshot.SetUserButtons(arr)
						self.onMSG(hwnd, "toolbarchange", 0, 0)
						return 0
				
					elif nm.code==self.Msg.TBN_RESET:
						# restore toolbar from snapshot
						self.Clear()
						self.snapshot.userButtons= None
						if not self.SendMessage(self.Hwnd, self.Msg.TB_ADDBUTTONS, len(self.snapshot.buttons), byref(self.snapshot.buttons)):
								raise "could not reset items"
						return 0
						
					elif nm.code==self.Msg.TBN_ENDADJUST:
						self._client_fAdjust= False
						self.onMSG(hwnd, "endadjust", 0, 0)
						return 0
					#
					# handlers fo customisation dialog
					# <--
					
					elif nm.code==self.Msg.TBN_BEGINDRAG:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						self.onMSG(hwnd, "begindrag",nmtb.iItem, 0)
						return 0
					
					elif nm.code==self.Msg.TBN_DRAGOUT:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						self.onMSG(hwnd, "dragout",nmtb.iItem, 0)
						return 0
				
					elif nm.code==self.Msg.TBN_ENDDRAG:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						self.onMSG(hwnd, "enddrag", 0, 0)
						return 0

					elif nm.code==self.Msg.TBN_DROPDOWN:
						nmtb=NMTOOLBAR.from_address(msgr.lParam)
						return self.onMSG(hwnd, "dropdown",nmtb.iItem, 0)
											
					elif nm.code==self.Msg.NM_RELEASEDCAPTURE:
						self.onMSG(hwnd, "releasedcapture", 0, 0)
						return 0

					elif nm.code==self.Msg.NM_RCLICK:
						nmm=NMMOUSE.from_address(msgr.lParam)
						if nmm.dwItemSpec ==UINT_MAX-1:	ID=None
						else: ID=nmm.dwItemSpec
						result= self.onMSG(hwnd, "rclick", ID,	(nmm.dwItemData, POINT(nmm.pt.y, nmm.pt.y)))
						if result==False: return 1
						return 0
					
					elif nm.code==self.Msg.NM_RDBLCLK:
						result= self.onMSG(hwnd, "rdblclick", 0,	0)
						if result==False: return 1
						return 0

					elif nm.code==self.Msg.TBN_HOTITEMCHANGE:
						nmh=NMTBHOTITEM.from_address(msgr.lParam)
						if nmh.dwFlags==0: 
							out=['unknown', ]
						else:
							out=[]
							if nmh.dwFlags & 1: out.append('mouse') # HICF_MOUSE
							if nmh.dwFlags & 2: out.append('arrowkeys') # HICF_ARROWKEYS
							if nmh.dwFlags & 4: out.append('accelerator') # HICF_ACCELERATOR
							if nmh.dwFlags & 8: out.append('dupaccel') # HICF_DUPACCEL
							if nmh.dwFlags & 16: out.append('entering') # HICF_ENTERING
							if nmh.dwFlags & 32: out.append('leaving') # HICF_LEAVING
							if nmh.dwFlags & 64: out.append('reselect') # HICF_RESELECT
							if nmh.dwFlags & 128: out.append('lmouse') # HHICF_LMOUSE
							if nmh.dwFlags & 256: out.append('toggledropdown') # 	HICF_TOGGLEDROPDOWN
						result= self.onMSG(hwnd, "hotitemchange", (nmh.idOld, nmh.idNew), out)
						if result==False: return 1
						return 0
								

			return 0		# <- do not remove !! 

		elif msg==self.Msg.WM_DESTROY:
			self.onMSG(hwnd, "destroy", 0, 0)
			

