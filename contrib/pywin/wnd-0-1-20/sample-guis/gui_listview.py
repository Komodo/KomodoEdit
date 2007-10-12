
import wnd

import os, sys
from wnd.wintypes import LOWORD, HIWORD, RGB
from wnd.controls.tab import Tab
from wnd.controls.listview import Listview
from wnd.controls.imagelist import (Imagelist, 
													ImagelistFromFile)
from wnd import gdi


#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class SimpleListview:
	def __init__(self, parent):
		self.lv = Listview(parent, 5, 150, 100, 140, 'report', 'border', 'fullrowselect', 'showselalways', 'gridlines', 'editlabels', 'debug')
				
		self.lv.onMSG=self.on_lv
		self.lv.Column('simple listview', width=80)

		for i in range(10):
			self.lv.Item('test-%s' % i)
		
		self.lv.HandleMessage(self.lv.Msg.WM_SIZE)
		
		
	def GetControl(self):
		return self.lv
	
	def on_lv(self, hwnd, msg, wp, lp):
		if msg=="rmbup":
			n=self.lv.GetSelected()
			if n != None:
				self.lv.EditLabel(n)

		elif msg==self.lv.Msg.WM_SIZE:
			self.lv.SetColumnWidth(0, LOWORD(lp))
		
		


class ListviewCheckItems:
	"""Listview displaying some checkable items."""
	def __init__(self, parent):
		self.lv = Listview(parent, 5, 5, 100, 140, 'report', 'border', 'fullrowselect', 'showselalways', 'gridlines')
		
		self.lv.onMSG = self.on_lvCheck
		self.lv.HandleMessage(self.lv.Msg.WM_SIZE)
				
		self.lv.Column('custom checkitems', width=100)
		
		
		bm= gdi.SystemBitmap('checkboxes')
		w, h= bm.GetSize()
		bmW, bmH = w/4, h/3      # sprite size
		bmUnchecked= bm.Extract(None, bmW, 0, bmW, bmH)
		bmChecked= bm.Extract(None, bmW*2, 0, bmW, bmH)
		self.imglCheck = Imagelist(bmW, bmH, 2, 0, 'color')
		self.imglCheck.AddBitmap(bmChecked)
		self.imglCheck.AddBitmap(bmUnchecked)
		bm.Close()

		self.lv.SetImagelistState(self.imglCheck)
		for i in range(5): 
			self.lv.Item('item %s' % str(i), -1, iStateImage=1)
			
	def GetControl(self):
		return self.lv
	
	def lv_toggle_ckeckmark(self, iItem):
		if self.lv.GetItemStateImage(iItem)==1:
			self.lv.SetItemStateImage(iItem, 2)
			self.lv.DeselectItem(-1)
			self.lv.SelectItem(iItem)
		else: self.lv.SetItemStateImage(iItem, 1)
	
	def on_lvCheck(self, hwnd, msg, wp, lp):
		if msg=="space":
			item=self.lv.GetSelectedItem()
			if item != None: self.lv_toggle_ckeckmark(item)
		elif msg in ("lmbup", "lmbdouble", "click"):	
			item = self.lv.ItemHittest(*self.lv.GetCursorPos())
			if item != None: self.lv_toggle_ckeckmark(item[0])
		elif msg==self.lv.Msg.WM_SIZE:
			self.lv.SetColumnWidth(0, LOWORD(lp))
				

class ListviewCustomDraw:
	""""""
	def __init__(self, parent):
		self.lv = Listview(parent, 115, 5, 260, 180, 'report', 'border', 'fullrowselect', 'gridlines', 'customdraw')
				
		self.lv.onMSG = self.on_lvCDraw
		self.lv.HandleMessage(self.lv.Msg.WM_SIZE)
		
		self.lv.Column('', width=100)
		self.lv.Column('customdraw listview', width=160)
		self.lv.Item('test')
		self.lv.Item('foo')
		self.lv.SetItemText(0, 1, 'subitem1')
		self.lv.SetItemText(1, 1, 'subitem')

		self.n= 0
		
		
		self.font = gdi.Font('tahoma', 12, weight=600, underline=True, italic=True)
		
		# use some cheat here to set the item heights for listviews  
		self.imglCDraw = Imagelist(1, 70, 1, 0, 'color')
		self.imglCDraw.AddIcons(gdi.IconFromBytes('', '', 1, 1, 70))
		self.lv.SetImagelistSmall(self.imglCDraw)

		# setup another imagelist for custom icons
		self.imglCDraw2 = Imagelist(32, 32, 1, 0, 'color16', 'mask')
		self.imglCDraw2.AddIcons(gdi.SystemIcon('application'),
																		gdi.SystemIcon('error'))
		
	def GetControl(self):
		return self.lv		
	
	def on_lvCDraw(self, hwnd, msg, wp, lp):
		
		if msg==self.lv.Msg.WM_SIZE:
			# adjust second column to fit display area
			rc= self.lv.GetItemRect(0, 1)
			self.lv.SetColumnWidth(1, LOWORD(lp)-rc.left)
		
		# draw item by item
		elif msg=="customdraw":
			if lp.drawStage==lp.PREPAINT: 
				return lp.NOTIFYITEMDRAW
			elif lp.drawStage==lp.ITEMPREPAINT:
				return lp.NOTIFYSUBITEMDRAW
			elif lp.drawStage==lp.SUBITEMPREPAINT:
			
				if lp.iItem==0 and lp.iSubItem ==0:
					# draw custom icon for this item
					dc = gdi.DCFromHandle(lp.hdc)
					rc=self.lv.GetItemRect(0, 0)
					self.imglCDraw2.Draw(dc,0, rc.left+30, rc.top+10)
					dc.Close()
					# tell windows, we did all the drawing...
					return lp.SKIPDEFAULT
				
				elif lp.iItem==1 and lp.iSubItem ==0:
					# draw custom icon and new background
					dc = gdi.DCFromHandle(lp.hdc)
					brush= gdi.SolidBrush(RGB(255, 235, 0))
					rc=self.lv.GetItemRect(1, 0)
					brush.FillRect(dc, rc)
					self.imglCDraw2.Draw(dc, 1, rc.left+30, rc.top+10)
					dc.Close()
					brush.Close()
					return lp.SKIPDEFAULT
				
				elif lp.iItem==0 and lp.iSubItem ==1:
					# draw the this item from scratch
					rc = self.lv.GetItemRect(0, 1)
					dc = gdi.DCFromHandle(lp.hdc)
					font= dc.GetFont()
					if lp.itemState& lp.FOCUS:
						brush= gdi.SolidBrush(gdi.GetSysColor('highlight'))
						dc.SetTextColor(gdi.GetSysColor('highlighttext'))
					else:
						brush= gdi.SolidBrush(self.lv.GetBkColor())
						dc.SetTextColor(gdi.GetSysColor('btntext'))
					brush.FillRect(dc, rc)
					brush.Close()
					text = 'custom icon and some fit to size text here (sorry, flickers)...'
					font.DrawText(dc, rc, text, 'wordbreak',)
					dc.Close()
					font.Close()
					return lp.SKIPDEFAULT
				
				elif lp.iItem==1 and lp.iSubItem ==1:
					# change background color and set new font
					## to be more eeffective here its enough to select the font once
					## and return DODEFAULT in subsequent calls
					## colors are taken over dor all subsequent items anyway
					lp.clrTextBk = RGB(240, 220, 0)
					dc = gdi.DCFromHandle(lp.hdc)
					dc.SelectObject(self.font)
					## dono why, but this will drive gdi crazy after a while... (error 'invalid object')
					#font = gdi.Font('tahoma', 12, weight=600, underline=True, italic=True)
					#dc.SelectObject(self.font)
					#font.Close()
					dc.Close()
					# tell windows we set a new font...
					return lp.NEWFONT
				
			

class window(wnd.Window):
			
	def __init__(self):
		wnd.Window.__init__(self, 'listview-sample', 'listview-sample', None, None, None, None, 'sysmenu', 'sizebox')
		
		self.tab= Tab(self, 0, 0, 0, 0)
		self.tab.onMSG= self.on_tab

		self.tab.Item('simple')
		self.tab.Item('checkboxes')
		self.tab.Item('customdraw')
				
		self.a= SimpleListview(self.tab)
		self.b= ListviewCheckItems(self.tab)
		self.c=ListviewCustomDraw(self.tab)

		self.tabs= (self.a.GetControl(), self.b.GetControl(), self.c.GetControl())
		self.HideWindows(*self.tabs[1:])
		self.tab.Select(0)

			
	def adjust_tab(self):
		rc= self.tab.GetDisplayRect()
		rc.ScreenToClient(self.tab.Hwnd)
		rc= rc.ToSize()
		self.tab.DeferWindows(
			(self.tabs[0], ) + rc,
			(self.tabs[1], ) + rc,
			(self.tabs[2], ) + rc,
			)


		
	def on_tab(self, hwnd, msg, wp, lp):
		if msg=="selchanging":
			self.tabs[wp].Hide()
	
		elif msg=="selchanged":
			self.tabs[wp].Show()
		
			
	def onMSG(self, hwnd, msg, wp, lp):
		#print hwnd, msg, wp, lp
		if msg=="size":
			self.tab.SetWindowPosAndSize(*lp)
			self.adjust_tab()


		elif msg=="destroyed":
			pass
		
w = window()
w.Run()

