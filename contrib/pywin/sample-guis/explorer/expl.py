
"""The very start of a file manager...

"""

import sys
import wnd
from wnd import gdi
from wnd.wintypes import RECT
from wnd.api import winpath, display
from wnd.wintypes import RGB, GETRGB
from wnd.controls.statusbar import Statusbar 
from wnd.custom.dirlist import DirList
from wnd.custom.splitter import Splitter

import expl_menu
import expl_dircombo
import expl_statusbar
import expl_ini

PATHICO= '%s\\py.ico' % sys.prefix

#******************************************************************
#******************************************************************

class Window(wnd.Window):
	def __init__(self):
		
		
		self.activePane= None
		self.DirCombo= None
		self.title=  'wnd_explorer 01 -- %s'

		self.Ini= expl_ini.Ini(self)
		
		size= self.Ini.GetValue('mainwindow', 'size', default= None)
		
		if size:
			## make shure window is visible on monitor
			try:
				x, y, w, h= map(int, size.split(','))
				rc= display.GetMonitorXY(x, y)[3]	## working rect
				rc2= RECT(x,
									y, 
									x+gdi.GetSystemMetric('cxmin'),
									y+gdi.GetSystemMetric('cymin')) 
				
				if not rc2.InRect(rc):
					x= rc.left
					y= rc.top
			except:
				x= y= w= h= None
		else:
			x= y= w= h= None
		wnd.Window.__init__(self, 'wnd_explorer', self.title % '', x, y, w, h, 'overlappedwindow', 'clipchildren', 'dialoglike')
			
		
		## set python icon
		try:
			ico= gdi.IconFromFile(PATHICO)
			self.SetIcon(ico)
		except: pass
		
				
		## init combobox andstatusbar
		self.DirCombo= expl_dircombo.ExplDircombo(self)
		self.Statusbar= expl_statusbar.ExplStatusbar(self)
				
		## init menu
		self.Menu= expl_menu.ExplMenu(self)
		self.Menu.Set(self)
					
		## init dirlists
		self.DirList1= DirList(self, 0, 0, 0, 0, 'border', 'editlabels', 'showselalways', 'report', 'clientedge', 'tabstop')
		self.DirList2= DirList(self, 0, 0, 0, 0, 'largeicon', 'clientedge', 'editlabels', 'showselalways', 'report', 'tabstop')
		self.DirList1.onMSG= self.DirList2.onMSG= self.on_dirlist
		
		def init_dirlist(dirlist, inisection):
			flag= False
			dirr= self.Ini.GetValue(inisection, 'dir')
			if winpath.GetRoot(dirr):
				if winpath.Exists(dirr):
					if winpath.IsDir(dirr):
						dirlist.ListDir(dirr)
						flag= True
			else:
				flag= dirlist.ListDir(dirr)
			if not flag:
				dirlist.ListDir('desktop')
			
		init_dirlist(self.DirList1, 'pane1')
		init_dirlist(self.DirList2, 'pane2')
		
		
		
		## init splitter
		w= self.GetClientRect().ToSize()[2]
				
		self.SplitteritterW= 5
		self.Splitter= Splitter(self, (w/2)-(self.SplitteritterW/2), 0, self.SplitteritterW, 0, 'feedbackbar', 'vert')
		colorBk= gdi.GetSysColor('msgbox')
		
		self.Splitter.SetPageSize(30)
		#colorHi= gdi.GetSysColor('highlight')
		rgb= GETRGB(colorBk)
		colorHi= RGB(rgb[0]+30, rgb[1]+30, rgb[2]+30)
		self.Splitter.SetColors(colorBk, colorHi)
		self.Splitter.onMSG= self.on_splitter

				
			
				
	
	
	def on_dirlist(self, hwnd, msg, wp, lp):
		
		if msg=='itemchanged':
						
			if 'selected' in lp[0] and not 'selected' in lp[1]:
				## an item has been deselected
				self.Statusbar.Expl_SetItemsSelected(
						self.activePane.GetSelectedCount())
				
			if 'selected' not in lp[0] and  'selected' in lp[1]:
				## an item has been selected
				
				size= 0
				for i in self.activePane.IterSelected():
					n= self.activePane.GetSize(i, asstring=False)
					if n != None:
						size += n

				self.Statusbar.Expl_SetItemsSelected(
						self.activePane.GetSelectedCount(),
						self.activePane.FormatInt(size))
				
		
		elif msg=='shell_contextmenu':
			if wp=='open':
				self.Statusbar.SetSimple()
			elif wp=='helpstring':
				self.Statusbar.SetText(lp)
			elif wp=='close':
				self.Statusbar.SetText('')
				self.Statusbar.SetMultiple()
		
		elif msg in ('setfocus', 'dirchanged'):
			if hwnd== self.DirList1.Hwnd:
				self.cur_sel_pane1= []
				self.activePane=  self.DirList1
			else:
				self.cur_sel_pane2= []
				self.activePane=  self.DirList2
						
			path= self.activePane.GetCwd(path=True)
			self.SetText(self.title % path)
			self.DirCombo.SetText(
				path, 
				self.activePane.GetFilespec()[0]
				)

			size= 0
			for i in self.activePane.IterSelected():
				n= self.activePane.GetSize(i, asstring=False)
				if n != None:
					size += n
			
			self.Statusbar.Expl_SetItemsSelected(
						self.activePane.GetSelectedCount(), 
						self.activePane.FormatInt(size))
			
			
			

		
	def size_controls(self, ):			
			
			x, y, w, h= self.GetClientRect().ToSize()
			
			paneOffsY= 4
			stH= self.Statusbar.GetWindowRect().ToSize()[3]
			cmbH= self.DirCombo.GetWindowRect().ToSize()[3]
			rcSpl= self.Splitter.GetWindowRect()
			rcSpl.ScreenToClient(self.Hwnd)
										
			self.DeferWindows(
			(self.DirCombo, None, None, (w/10)*6, cmbH),
			
			(self.Splitter, rcSpl.left, cmbH+paneOffsY, self.SplitteritterW, h-stH-cmbH-paneOffsY),
			
			(self.DirList1, 0, 0+cmbH+paneOffsY, rcSpl.left-1, h-stH-cmbH-paneOffsY),
			(self.DirList2, rcSpl.right+1, 0+cmbH+paneOffsY, (w-rcSpl.right)-1, h-stH-cmbH-paneOffsY),
			
			(self.Statusbar, 0, h-stH, w, stH),
			)

			w= w/10
			self.Statusbar.SetParts(w, w*8, -1)
			

	def on_splitter(self, hwnd, msg, wp, lp):
		if msg=="moved": 
			self.size_controls()
			
	
	
	def onMSG(self, hwnd, msg, wp, lp):
		
		if msg=="size":
			self.size_controls()
			
		elif msg in ('menu open', 'menu popup', 'menu choice'):
			self.Menu.handle_menu_msg(hwnd, msg, wp, lp)
		
		elif msg=="open":
			self.DirList1.SetFocus()
			self.activePane= self.DirList1
		
		elif msg=="close":
						
			if self.DirCombo != None:	## combos have a __len_ attr !!
				self.DirCombo.Expl_SaveState()
			
			self.Ini.SetValue('mainwindow', 'size', '%s,%s,%s,%s' %	
													self.GetWindowRect().ToSize())
			
			self.Ini.Save()



#********************************************************************* 
if __name__=='__main__':                  
	w = Window()
	w.Run()



