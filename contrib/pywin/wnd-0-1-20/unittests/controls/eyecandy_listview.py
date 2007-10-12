"""just included if SO feels the need for some eye candy.
(hey!, eye candy is the listview not the code :-)"""

import wnd
from wnd.wintypes import *
from wnd.wintypes import RGB
from wnd import gdi
from wnd.controls.listview import Listview, ListviewFromHandle
from wnd.controls.imagelist import Imagelist
import time, random
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'Listview-test', 'Listview-test', None, None, None, None, 'sysmenu')

				
		# setup an Imagelist
		icons= ('application' ,'asterisk', 'error', 
						'exclamation', 'hand', 'information' ,
						'question', 'warning', 'winlogo' )
		ico= gdi.SystemIcon(icons[0])
		w, h= ico.GetSize()
		self.img= Imagelist(w, h, len(icons), 0, 'color16', 'mask')
		self.img.AddIcons(ico)
		for i in icons[1:]:
			self.img.AddIcons(gdi.SystemIcon(i))

		
		# setup listview
		x,y,w,h= self.GetClientRect().ToSize()
		self.l= Listview(self, x, y, w, h, 'report', 'border', 'gridlines', 'fullrowselect', 'subitemimages', 'showselalways', 'editlabels')
		self.l.onMSG=self.on_debug
		
		self.hd= self.l.GetHeaderControl()
		self.ed= None
		
		
		self.tests= [(self.l, 'testing [Listview]')]
		
		
		self.customdraw= 0
		if self.customdraw:
			self.prepdraw(self.l)
		
		else:
			#self.unittest(self.l)
			#self.l.Reset()
			self.l2= ListviewFromHandle(self.l.Hwnd)
			
			self.tests.append((self.l2, 'testing [ListviewFromHandle]'))
			#self.unittest(self.l2)
		
			
	
	
	
	
	
	def prepdraw(self, what):
		for i in range(3):
			what.Column('test-%s' % i, width=100)
		for i in range(5):
			what.Item('item-%s' % i, None)
			for j in range(what.GetColumnCount())[1:]:
				what.SetItemText(i, j, 'sub-%s-%s' % (i, j))

	def RandomColor(self):
		rng= (0, 255)
		return RGB(random.randrange(*rng),
								random.randrange(*rng),
								random.randrange(*rng))	
	
	
	def unittest(self, what):
		
		# imagelists
		what.SetImagelistSmall(self.img)
		assert(what.GetImagelistSmall()==self.img.handle)	
		what.SetImagelistNormal(self.img)
		assert(what.GetImagelistNormal()==self.img.handle)	
		what.SetImagelistState(self.img)
		assert(what.GetImagelistState()==self.img.handle)	
				
		# columns
		for i in range(10):
			what.RedrawItems(0, 0)
			time.sleep(0.1)
		
			what.Column('test-%s' % i, iImage=2)
		assert(what.GetColumnCount()==10)
		for i in what.IterColumns(): pass
		assert(i==9)
		assert(what.GetColumnText(9)=='test-9')
		what.SetColumnText(9, '9th column')
		assert(what.GetColumnText(9)=='9th column')
		what.SetColumnWidth(9, 400)
		assert(what.GetColumnWidth(9)==400)
		what.SetColumnWidth(1, 'autosizeheader')
		
		assert(what.GetColumnImage(1)==2)
		what.SetColumnImage(1, 5)
		assert(what.GetColumnImage(1)==5)

		# column order
		rng= range(what.GetColumnCount())[::-1]
		what.SetColumnOrder(*rng)
		assert(what.GetColumnOrder()==rng)
		assert(what.ColumnIndexToOrder(0)==9)	 # should be now

		what.RemoveColumn(9)
		assert(what.GetColumnCount()==9)
		what.ClearColumns()
		assert(what.GetColumnCount()==0)

			
		# items
		for i in range(10):
			what.Column('test-%s' % i, width=140, iImage=2, align='right')
			what.RedrawItems(0, 0)
			time.sleep(0.1)
		
		
		for i in range(20):
			what.Item('item-%s' % i, None)
			for j in range(what.GetColumnCount())[1:]:
				what.RedrawItems(i, i)
				what.SetItemText(i, j, 'sub-%s-%s' % (i, j))
		assert(len(what)==20)
		
		
		
		j= 0
		for i in range(len(what)):
			assert(what.GetItemText(i, 0)=='item-%s' % i)	
			for j in range(what.GetColumnCount())[1:]:
				assert(what.GetItemText(i, j)== 'sub-%s-%s' % (i, j))
				
				
		what.InsertItem(10, 'foo item')
		assert(what.GetItemText(11, 0)=='item-10')
		what.RemoveItem(10)
		assert(what.GetItemText(10, 0)=='item-10')
		
		
		
		for i in range(len(what)):
			what.SetItemImage(i, 3, 1)
			assert(what.GetItemImage(i, 3)==1)
			what.RedrawItems(i, i)
			time.sleep(0.05)
		
		for i in range(len(what)):
			what.SetItemStateImage(i, 3)
			assert(what.GetItemStateImage(i)==3)
			what.RedrawItems(i, i)
			time.sleep(0.05)
		
		
		what.SetItemLparam(1, 999)
		assert(what.GetItemLparam(1)==999)
		
		
		

		pt= what.GetItemPos(1)
		rc= what.GetItemRect(0, 0)
		rc= what.GetItemRect(0, 2)
		
		rc= what.GetItemIconRect(0, 0)
		rc= what.GetItemIconRect(0, 2)
		rc= what.GetItemLabelRect(0, 0)
		rc= what.GetItemLabelRect(0, 2)
		rc= what.GetItemSelectedRect(1)

		
		# selecting and stuff
		what.SelectItem(1)
		assert(what.IsItemSelected(1))
		assert(what.GetSelectedItem()==1)
		what.DeselectItem(1)
		assert(not what.IsItemSelected(1))
		
		what.SetFocusItem(1)
		assert(what.ItemHasFocus(1))
		assert(what.GetFocusItem()==1)
		what.RemoveItemFocus(1)
		assert(not what.ItemHasFocus(1))

		what.CutSelectItem(1)
		assert(what.IsItemCutSelected(1))
		what.RemoveItemCutSelect(1)
		assert(not what.IsItemCutSelected(1))

		what.DropHilightItem(1)
		assert(what.IsItemDropHilighted(1))
		what.RemoveItemDropHilight(1)
		assert(not what.IsItemDropHilighted(1))
		
			
		
		what.GetTopIndex()
		what.Scroll(200, 100)
		what.Scroll(-200, -100)
		what.EnshureVisible(10)
		
		
		#
		what.SetItemCount(100)
		r= what.GetPageCount()
		r= what. ItemHittest(300, 300)
		r= what.GetStringWidth('abcdefg')
		what.RedrawItems()

		# some colors
		for i in range(3):
			color= self.RandomColor()
			what.SetBkColor(color)
			assert(what.GetBkColor()==color)

			color= self.RandomColor()
			what.SetTextBkColor(color)
			assert(what.GetTextBkColor()==color)
			what.SetTextColor(~color)
			assert(what.GetTextColor()==~color)
			time.sleep(0.2)

		
		# dispinfo
		
		

		
			
	
	def on_debug(self, hwnd, msg, wp, lp):
		
		
		if self.customdraw:
			if msg=="customdraw":
				flag= 1
				if flag:
					if lp.drawStage==lp.PREPAINT: 
						return lp.NOTIFYITEMDRAW
					elif lp.drawStage==lp.ITEMPREPAINT:
						return lp.NOTIFYSUBITEMDRAW
					elif lp.drawStage==lp.SUBITEMPREPAINT:
						if lp.iItem==0 and lp.iSubItem==0:
							pass
						else:
							return lp.DODEFAULT
				else:
					if lp.drawStage==lp.PREPAINT:
						return lp.NOTIFYPOSTPAINT
					elif lp.drawStage==lp.POSTPAINT:
						
						return lp.ITEMPOSTPAINT
					
			else:
				if msg=="beginlabeledit":
					ed= self.l.GetEditControl()
					
					
				pass
				
				
		
	def onMSG(self, hwnd, msg, wp, lp):
		if msg=="open":
			n= len(self.tests)
			for j, i in enumerate(self.tests):
				self.lv, title= i			## required for message handler
				self.SetText(title)
				self.unittest(self.lv)
				if j+1 < n:
					self.lv.Reset()
		
		

w = window()
w.Run()
#









