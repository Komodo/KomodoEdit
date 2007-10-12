
"""simple DataObject viewer
Displays information for either the DataObject currently on th eclipboard
or the DataObject dropped
"""

import wnd
from wnd.api import clipboard, msgbox
from wnd.api.ole import dragdrop
from wnd.controls.menu import Menu
from wnd.controls.listview import Listview
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

## menu IDs
IDM_FILE    =    1000
IDM_FILE_EXIT    =    1001

idNext  =   IDM_FILE_EXIT + 1

IDM_CLIPBOARD      =      idNext
IDM_CLIPBOARD_GET_DO    =    IDM_CLIPBOARD + 1 
IDM_CLIPBOARD_CLEAR    =    IDM_CLIPBOARD + 2 

idNext  =   IDM_CLIPBOARD_CLEAR + 1

IDM_VIEW       =       idNext
IDM_VIEW_CLEAR    =     IDM_VIEW + 1  


#**********************************************************
#**********************************************************
class window(wnd.Window):
			
	def __init__(self):
		
		self.title= 'DataObject viewer [drop data or get clipboard]'
		wnd.Window.__init__(self, 'wnd_dobjview', self.title, None, None, None, None, 'sysmenu', 'sizebox')
		
		# setup menu
		self.menu= Menu()
		pop= self.menu.Popup('&File', IDM_FILE)
		pop.Item('E&xit', IDM_FILE_EXIT)
		pop= self.menu.Popup('&Clipboard', IDM_CLIPBOARD)
		pop.Item('&Get DataObject', IDM_CLIPBOARD_GET_DO)
		pop.Item('&Clear Clipboard', IDM_CLIPBOARD_CLEAR)
		pop= self.menu.Popup('&View', IDM_VIEW)
		pop.Item('&Clar View', IDM_VIEW_CLEAR)
		self.menu.Set(self)
		
		# setup listview
		self.lv = Listview(self, 0, 0, 0, 0, 'report', 'border', 'fullrowselect', 'showselalways', 'gridlines')
		self.lv.Column('get/set')
		self.lv.Column('name')
		self.lv.Column('aspect')
		self.lv.Column('tymed')
		self.lv.Column('index')
				
		# register listview as drop target 
		self.drag= dragdrop.DragDrop(self.lv.Hwnd)
		self.drag.onMSG= self.on_dragdrop
		dragdrop.Register(self.lv.Hwnd, self.drag)
		
	
	# helper methods ---------------------------------------------------------------------
	
	def lv_PrintDataObject(self, dataobject):
		## helper method to print clipformats of a DataObject to the listview
		
		def tmp_setdata(fmt, get=True):
			# simply format the string representation of the clipboard format
			s= str(fmt).split('{')
			if get:
				n= self.lv.Item('(get)')
			else:
				n= self.lv.Item('(set)')
			self.lv.SetItemText(n, 1, s[1][s[1].index('=')+1:-2])
			self.lv.SetItemText(n, 2, '{%s' % s[2])
			self.lv.SetItemText(n, 3, '{%s' % s[3])
			self.lv.SetItemText(n, 4, '{%s' % s[4][:-1])
		
		self.lv.Clear()
		try:
			n= 0
			for i in dataobject.ListFormats(): 
				tmp_setdata(i, get=True)
				n += 1
			self.lv.Item('')
		except: pass
		try:
			for i in dataobject.ListFormats(get=False): 
				n += 1
				tmp_setdata(i, get=False)
		except: pass
		self.SetText('%s --%s formats found--' % (self.title, n))
				
		
	def error(self, msg):
		# throws a messagebox
		
		msgbox.Msg(self.Hwnd, msg, 'DataObject viewer', 'ok', 'systemmodal')
	
	
	# message handlers --------------------------------------------------------------
	
	def menu_HandleMessage(self, hwnd, msg, wp, lp):
		# menu handler
			
		if msg=='menu choice':
			if lp[0]==IDM_FILE_EXIT: 
				self.Close()
			elif lp[0]==IDM_CLIPBOARD_GET_DO: 
				try:
					self.lv_PrintDataObject(clipboard.GetDataObject())
				except: 
					self.error("error! \n failed to retrieve DataObject")
			elif lp[0]==IDM_CLIPBOARD_CLEAR: 
				clipboard.Clear()
			elif lp[0]==IDM_VIEW_CLEAR: 
				self.lv.Clear()

		
	def on_dragdrop(self, hwnd, msg, wp, lp):
		# drag and drop handler
		
		if msg=='dragdrop':
			if wp=='drop':
				try: 
					self.lv_PrintDataObject(lp[0])
				except: 
					self.error("error! \n failed to retrieve DataObject")
				return False	## reject drop anyway
	
			
	def onMSG(self, hwnd, msg, wp, lp):
		# GUI message handler				
		
		if msg=='size':
			self.lv.SetWindowPosAndSize(*lp)
			w= lp[2]/5
			self.lv.SetColumnWidth(0, w/2)
			self.lv.SetColumnWidth(1, w)
			self.lv.SetColumnWidth(2, w)
			self.lv.SetColumnWidth(3, w + (w/2))
			self.lv.SetColumnWidth(4, w)
		
		elif msg in ('menu choice', 'menu open', 'menu popup'):
			self.menu_HandleMessage(hwnd, msg, wp, lp)
		
		elif msg=='close':
			try: dragdrop.Revoke(self.lv.Hwnd)
			except: pass
			
		
#**********************************************************
#**********************************************************
		
w = window()
w.Run()


