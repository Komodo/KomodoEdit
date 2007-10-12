"""simple MDIFrame sample"""

import wnd
from wnd import gdi
from wnd.controls.tab import Tab
from wnd.controls.menu import Menu
from wnd.controls.editbox import Editbox
from wnd.controls.static import StaticHorz
from wnd.controls.mdiframe import MDIFrame
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

## setup menu IDs, all IDs should be > MDIFrame.MIN_MENU_ID
IDM_FILE            =           MDIFrame.MIN_MENU_ID + 1
IDM_FILE_NEW          =         IDM_FILE + 1
IDM_FILE_EXIT        =          IDM_FILE + 2

idNext = IDM_FILE_EXIT +1

IDM_WINDOW           =             idNext
IDM_WINDOW_NEXT    =        IDM_WINDOW + 1
IDM_WINDOW_PREV       =      IDM_WINDOW + 2
IDM_WINDOW_TILEHORZ       =        IDM_WINDOW  +3
IDM_WINDOW_TILEVERT        =        IDM_WINDOW + 4
IDM_WINDOW_CASCADE        =       IDM_WINDOW + 5
IDM_WINDOW_MINIMIZE       =         IDM_WINDOW + 6
IDM_WINDOW_RESTORE        =        IDM_WINDOW + 7
IDM_WINDOW_CLOSE        =        IDM_WINDOW + 8
IDM_WINDOW_ICONARANGE    =    IDM_WINDOW + 9

	

class MyWindow(MDIFrame):
	def __init__(self):
		
		self.n= 0						## just a counter
		self.controls= {}		## hwnd MDI child --> associated control instance
											## NOTE
											## still a problem with ctypes. Cached controls
											## leave pretty much garbage behind when destroyed
											## and removed from the cache
		selftabH= 0			## height of a tab button
		self.tabOffs= 0		## vert offset inbetween buttons
		self.staticH= 0		## calculate static divider height
		
		
		MDIFrame.__init__(self, 'MDI test', None, None, None, None, 'overlappedwindow')
		
		rc= self.GetClientRect()	
		
		## init menu
		self.mnu= Menu()
		popMdi= self.mnu.Popup('&File', IDM_FILE)
		popMdi.Item('&new MDI child', IDM_FILE_NEW)
		popMdi.Separator(0)
		popMdi.Item('&Exit', IDM_FILE_EXIT)
		
		pop= self.mnu.Popup('&Window', IDM_WINDOW)
		pop.Item('&Next', IDM_WINDOW_NEXT)
		pop.Item('&Previous', IDM_WINDOW_PREV)
		pop.Separator(0)
		pop.Item('Tile &Horizontally', IDM_WINDOW_TILEHORZ)
		pop.Item('Tile &Vertically', IDM_WINDOW_TILEVERT)
		pop.Item('&Cascade', IDM_WINDOW_CASCADE)
		pop.Separator(0)
		pop.Item('&Minimize All', IDM_WINDOW_MINIMIZE)
		pop.Item('&Restore All', IDM_WINDOW_RESTORE)
		pop.Item('&Close All', IDM_WINDOW_CLOSE)
		pop.Separator(0)
		pop.Item('&Arrange Icons', IDM_WINDOW_ICONARANGE)

		self.mnu.Set(self)
		
		
		## static divider above the tab control
		self.st= StaticHorz(self, 0, 0, 100)
		self.staticH= self.st.GetWindowRect().ToSize()[3]
		
		## setup tab control
		## TODO: some cusromdrawing could help to make the buttons look better 
		self.tab= Tab(self, 0, 0, 0, 0, 'buttons', 'flatseparators', 'fixedwidth', 'flatbuttons')
		self.tab.onMSG= self.on_tab
		self.tab.SetStyle('multiline')
		self.tabH, self.tabOffs= self.calculate_tab_metrics()
		self.tab.SetWindowSize(rc.right-rc.left, selftabH+1)
				
		## setup MDIClient
		self.mdi= self.MDIClient(0, 0, 0, 0, 'clientedge', hMenu=popMdi.handle)
		self.mdi.onMSG= self.on_mdi
		
			
		## all MDI client windows will be created dynamically from menu command
		
	## helper methods ----------------------------------------------------------------
	
	def calculate_tab_metrics(self):
		## helper method
		## calculates self.tabH and self.tabOffs
		## required to adjust the tab control dynamically
		## 1. !! the tab control has to fit exactly the parents with
		## 3. calculate the tab button height
		## 2. calculate the offset inbetween tab buttons 
		##
		## TODO: 
		##		- check if we have to readjust tab metrics on fontchanges
		##
		n= len(self.tab)
		if n < 2:
			## enshure at least two buttons are avaiable
			self.tab.Item('foo')
			if n==0:
				self.tab.Item('foo')
							
		## calculate button size
		tabH= self.tab.GetItemRect(0).ToSize()[3]
				
		## force tab to show multiple lines of tabs
		w, h= self.tab.GetWindowRect().ToSize()[2:]
		self.tab.SetWindowSize(0, 0)
		
		## calculate the offset inbetween buttons
		rc1= self.tab.GetItemRect(0)
		rc2= self.tab.GetItemRect(1)
		if self.tab.GetRowCount()==1:	## fallback, not corect for 'flatbuttons'
			tabOffs= rc2.left-rc1.right
		else:
			tabOffs= rc2.top-rc1.bottom
		self.tab.SetWindowSize(w, h)
		
		if n < 2:	
			self.tab.RemoveItem(1)
			if n==0:
				self.tab.RemoveItem(0)
			
		return tabH, tabOffs


	def size_controls(self, size= None):
		## helper method
		## handles resizing of controls
		
		if size==None:
			w, h= self.GetClientRect().ToSize()[2:]
		else:
			w, h= size[2:]

		## adjust tab height to filt tab rowcount
		n= self.tab.GetRowCount()
		self.tab.SetWindowSize(w, (n*self.tabH) + (n*self.tabOffs))
		tabW, tabH= self.tab.GetWindowRect().ToSize()[2:]
						
		self.DeferWindows(
			(self.st, None, None, w, self.staticH),
			(self.tab, 0, 0+self.staticH, w, tabH), 
			(self.mdi, 0, 0+tabH+self.staticH, w, h-tabH-self.staticH)
			)	

	
	
	## message handlers ----------------------------------------------------------------
	
	def HandleMenuMsg(self, hwnd, msg, wp, lp):
		
		if msg=="menu choice":
			
			if lp[0]== IDM_FILE_NEW:
				## create a new MDI child and place a simple editbox upon it
				
				n1= self.tab.GetRowCount()
				self.n += 1
				
				w, h= self.mdi.GetClientRect().ToSize()[2:]
				ico= gdi.FileIcon('*.txt')
				mdi= self.mdi.NewChild('child-%s' % self.n,  0, 0, w/2, h/2, icon=ico)
				w, h= mdi.GetClientRect().ToSize()[2:]
				self.controls[mdi.Hwnd]= Editbox(mdi, 'sample text', 0, 0, w, h, 'autovscroll', 'autohscroll', 'wantreturn', 'vscroll', 'hscroll')

				## adjust tab height to filt rowcount
				n2= self.tab.GetRowCount()
				if n1 != n2:
					self.size_controls()
											
			elif lp[0]==IDM_FILE_EXIT:
				self.Close()
			elif lp[0]==IDM_WINDOW_NEXT:
				self.mdi.ActivateNext()
			elif lp[0]==IDM_WINDOW_PREV:
				self.mdi.ActivatePrevious()
			elif lp[0]==IDM_WINDOW_TILEHORZ:
				self.mdi.Tile('horizontal')
			elif lp[0]==IDM_WINDOW_TILEVERT:
				self.mdi.Tile('verticalal')
			elif lp[0]==IDM_WINDOW_CASCADE:
				self.mdi.Cascade()
			elif lp[0]==IDM_WINDOW_MINIMIZE:
				for i in self.mdi: self.mdi.Minimize(i)
			elif lp[0]==IDM_WINDOW_RESTORE:
				for i in self.mdi: self.mdi.Restore(i)
			elif lp[0]==IDM_WINDOW_CLOSE:
				self.mdi.Clear()
			elif lp[0]==IDM_WINDOW_ICONARANGE:
				self.mdi.IconArrange()

		
				
	def on_tab(self, hwnd, msg, wp, lp):
		if msg=="selchanged":
			## this is what happens when a tab is selected
			hwndMdi= self.tab.GetItemLparam(wp)
			if self.mdi.IsMinimized(hwndMdi):
				self.mdi.Restore(hwndMdi)
			self.mdi.Activate(hwndMdi)
	
	
	## message handler of the MDI client window
	def on_mdi(self, hwnd, msg, wp, lp):	
		
		if msg=="childsizing":
			## control may not yet be available if 'size' is send in
			## response to creating a MDI child
			if wp in self.controls:
				mdi= self.mdi.GetChild(wp)
				w, h= mdi.GetClientRect().ToSize()[2:]
				ctl= self.controls[wp]
				ctl.SetWindowSize(w, h)
					
		elif msg=="childcreated":
			## create a tab for the MDI child
			ctl= self.mdi.GetChild(wp)
			self.tab.Item(ctl.GetText(), lp=wp)
			
		elif msg=="childdestroyed":
			## remove tab ++ control from the cache
						
			i= self.tab.FindLparam(wp)
			if i != None:
				n1= self.tab.GetRowCount()
				
				self.tab.RemoveItem(i)
				self.controls[wp].Close()
				del self.controls[wp]
				## collect garbage. See notes
				import gc
				gc.collect()

				## adjust tab height to filt rowcount
				n2= self.tab.GetRowCount()
				if n1 != n2:
					self.size_controls()
					
								
		elif msg=="childactivated":
			## select the associated tab
			
			i= self.tab.FindLparam(wp)
			if i != None:
				self.tab.Select(i)
			
						
	## message handler of the MDI frame window
	def onMSG(self, hwnd, msg, wp, lp):
		
		if msg=="size":
			self.size_controls(lp)
			
		elif msg in ('menu open', 'menu popup', 'menu choice'):
			self.HandleMenuMsg(hwnd, msg, wp, lp)
		
		elif msg=="open": pass		
		if msg=="close": pass
		
		
#************************************************************* 
#**************************************************************                  
w = MyWindow()
w.Run()

#wnd.Debug('leaks')
## hopefully None

