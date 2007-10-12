
"""Sample GUI, monitoring file sytem related changes.
(creating, deleting of files and folders and other related stuff)

You may drop a folder on either the ShellNotify or the ShellChangeNotification
pane to start monitoring the folder for changes. 

The ShellChangeNotification pane accepts only filesystem folders, while
the ShellNotify pane accepts non filesystem folders aswell. Only one pane
may be active and monitoring at a time.


REMARKS
ShellChangeNotification is quite inacurate here. Its nomore then giving
an idea of how it works. To tell notifications  for related events apart
one handler has to be registered per event to be monitored.
So you may get file related changes in the 'dirname' handler and vice versa.
Have to test this more in detail rather then blaming it to soon on the crappy
FindFirstChangeNotification api ;)

"""


import os, wnd
from wnd.wintypes import RGB
from wnd.api import shell
from wnd.api.ole import dragdrop 
from wnd.controls.listview import Listview
from wnd.controls import menu

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		
IDM_FILE= 100
IDM_EXIT= 101

IDM_VIEW= 200
IDM_CLEARSHN= 201
IDM_CLEARSHC= 202

class window(wnd.Window):
			
	def __init__(self):
		
		self.title= 'SHNotify sample: -- monitoring [%s] --'
		self.sh= None
		self.shn= None
		self.shc= None
		self.colorhi= RGB(255, 255, 255)
		self.colorlo= RGB(208, 208, 255)

				
		self.shn_msg= wnd.RegisterWindowMessage("sh_notify_msg")
		
		wnd.Window.__init__(self, 'SHNotify sample', self.title % 'drop folder to monitor changes', None, None, None, None, 'sysmenu', 'sizebox')
		
		# setup menu
		m= menu.Menu()
		pop= m.Popup('&File', IDM_FILE)
		pop.Item('&Exit', IDM_EXIT)

		pop= m.Popup('&View', IDM_VIEW)
		pop.Item('Clear SH&Notify', IDM_CLEARSHN)
		pop.Item('Clear SH&Change', IDM_CLEARSHC)
		self.menu= m
		self.menu.Set(self)
		
				
		# setup the two listviews
		self.lv = Listview(self, 0, 0, 0, 0, 'report', 'clientedge', 'fullrowselect', 'showselalways', 'gridlines')
		self.lv.onMSG=self.on_lv
		self.lv.Column('ShellNotify action')
		self.lv.Column('param1')
		self.lv.Column('param2')
		#self.lv.DragAcceptFiles(True)
		self.lv.HandleMessage(self.shn_msg)
		
		self.lv2 = Listview(self, 0, 0, 0, 0, 'report', 'clientedge', 'fullrowselect', 'showselalways', 'gridlines')
		self.lv2.onMSG=self.on_lv
		#self.lv2.DragAcceptFiles(True)
		self.lv2.Column('ShellChangeNotification action')

		self.set_colors(self.lv, hilight=False)
		self.set_colors(self.lv2, hilight=False)
		
		
		## register listviews as drop targets
		self.drop1= dragdrop.DragDrop(self.lv.Hwnd)
		self.drop2= dragdrop.DragDrop(self.lv2.Hwnd)
		self.drop1.onMSG= self.drop2.onMSG= self.on_drop
		dragdrop.Register(self.lv.Hwnd, self.drop1)
		dragdrop.Register(self.lv2.Hwnd, self.drop2)

		
		# setup shell change notify
		self.shc_flags= ('filename','dirname','attributes','size','lastwrite',
										'lastaccess','creation','security')

		self.shc_flags= ('filename','dirname')
		self.shc= []
		for n, i in enumerate(self.shc_flags):
			shc= shell.ShellChangeNotification()
			shc.onMSG= self.on_lv
			self.shc.append(shc)

			
		# setup shell namespace and shell notify 
		self.sh= shell.ShellNamespace()
		self.shn= shell.ShellNotify(self.lv, self.shn_msg, self.on_shellnotify)
	
	
	
	#--------------------------------------------------------------------------------
	
	def error(self, msg):
		from wnd.api import msgbox
		msgbox.Msg(self.Hwnd, msg, 'gui shellnotify', 'ok', 'systemmodal')

	
	def set_colors(self, lv, hilight=False):
		if hilight:
			lv.SetBkColor(self.colorhi)
			lv.SetTextBkColor(self.colorhi)
		else:
			lv.SetBkColor(self.colorlo)
			lv.SetTextBkColor(self.colorlo)
	
	
	def close_notifiers(self):
		## closes (resets) SHNotify and ShellChangeNotification handlers
		try:
			self.set_colors(self.lv, hilight=False)
		except:pass
		try:
			self.set_colors(self.lv2, hilight=False)
		except: pass
		try:
			if self.shn: self.shn.Close()
		except: pass
		try:
			if self.shc: self.shc_close()
		except: pass
	
	
	def dataobject_get_pIdl(self, dataobject, idlarray=False):
		## returns the pIdl (abs) of the first folder in the DataObject or None
		## if idlarray is True the DataObject is queried preferably for IDLISTARRAY
		## format, else HDROP is queried

		pIdlAbs= None
		if idlarray:
			il=  dragdrop.cf.idlistarray()
			if dataobject.HasFormat(il):
				dataobject.GetData(il)
				arr= il.value
				il.value= None
				self.sh.SetCwd(arr[0])
											
				for i in arr[1:]:
					if self.sh.IsFolder(i):
						pIdlAbs= shell.PidlJoin(arr[0], i)								
						break
									
				for i in arr:
					shell.PidlFree(i)
			
		if pIdlAbs: return pIdlAbs
				
		## query for hdrop format
		hd=  dragdrop.cf.hdropfiles()
		if dataobject.HasFormat(hd):
			dataobject.GetData(hd)
			arr= hd.value
			hd.value= None
			for  i in arr:
				if os.path.isdir(i):
					pIdlAbs= self.sh.ParseDisplayName(i)
					break
		
		return pIdlAbs
						

	
	## drop target handler
	def on_drop(self, hwnd, msg,wp, lp):
		
		if hwnd==self.lv.Hwnd:
			## accepts IDLISTARRAY and HDROP

			if wp=='dragenter':
				if lp[0].HasFormat(dragdrop.cf.idlistarray) or  lp[0].HasFormat(dragdrop.cf.hdropfiles):
					return True
			
			elif wp=='drop':
				self.close_notifiers()
								
				error= True
				try:
					pIdl= self.dataobject_get_pIdl(lp[0], idlarray=True)
					if pIdl:
						self.sh.SetCwd(pIdl)		## shell is taking care now
						self.shn.Register(pIdl)
						self.SetText(str(self.title % self.sh.GetParseName()))
						self.set_colors(self.lv, hilight=True)
						error= False
				except: 
					pass
						
				if error:
					self.error("no or invalid folder found in drop")
				
				return False
						
		elif hwnd==self.lv2.Hwnd:
			## accepts HDROP only
			
			if wp=='dragenter':
				if lp[0].HasFormat(dragdrop.cf.hdropfiles):
					return True
			
			elif wp=='drop':
				self.close_notifiers()

				error= True
				try:
					pIdl= self.dataobject_get_pIdl(lp[0], idlarray=False)
					if pIdl:
						try:
							path= shell.GetPathFromPidl(pIdl)						
							self.shc_register(path)
							self.SetText(str(self.title % path))
							self.set_colors(self.lv2, hilight=True)
							shell.PidlFree(pIdl)
							error= False
						except: 
							shell.PidlFree(pIdl)
							raise ''
				except: 
					pass
					
				if error:
					self.error("no or invalid folder found in drop")
				
				return False
			
		
		
	## methods for SHNotify ------------------------
	
	# callback for shell notify
	def on_shellnotify(self, hwnd, msg, wp, lp):
		if msg=="shellnotify":
			n= self.lv.Item(wp)
			if lp:
				if wp in ("rename", "renamefolder", "delete", "rmdir"):
														
					if lp[0]: 
						pIdl= shell.PidlCopy(lp[0])
						pIdlChild= shell.PidlSplit(pIdl)
						self.sh.SetCwd(pIdl)
						try:
							self.lv.SetItemText(n, 1, self.sh.GetParseName(pIdlChild))
						finally:
							shell.PidlFree(pIdl)
							shell.PidlFree(pIdlChild)
					
					if lp[1]: 
						pIdl= shell.PidlCopy(lp[1])
						pIdlChild= shell.PidlSplit(pIdl)
						self.sh.SetCwd(pIdl)
						try:
							self.lv.SetItemText(n, 2, self.sh.GetParseName(pIdlChild))
						finally:
							shell.PidlFree(pIdl)
							shell.PidlFree(pIdlChild)
						
				else:
					if lp[0]: 
						pIdl= shell.PidlCopy(lp)
						pIdlChild= shell.PidlSplit(pIdl)
						self.sh.SetCwd(pIdl)
						try:
							self.lv.SetItemText(n, 1, self.sh.GetParseName(pIdlChild))
						finally:
							shell.PidlFree(pIdl)
							shell.PidlFree(pIdlChild)
								
			self.lv.EnshureVisible(n)	
	
		
		
	
	## methods for ShellChangeNotification ------------------------
	
	def shc_register(self, path):
		## registers all ShellChangeNotifications
		for n, i in enumerate(self.shc):
			try:
				i.Register(path, self.shc_flags[n], hwnd=n)
			except: 
				## can not register all classes on win98
				## 'lastaccess','creation','security' will fail
				pass
	
	
	def shc_close(self):
		## closes all ShellChangeNotifications
		for i in self.shc:
			try:
				i.Close()
			except: pass

	def shc_handlemessage(self, hwnd, msg, wp, lp):
		if msg=="shellchange":
			try:
				evt= self.shc_flags[hwnd]
				n= self.lv2.Item(evt)
				self.lv2.EnshureVisible(n)
			except: pass
		

	# message handlers ------------------------------------------------------------
	
	## menu message handler
	def handle_menu_msg(self, hwnd, msg, wp, lp):
		if msg=='menu choice':
			if lp[0]== IDM_EXIT:
				self.Close()
			elif lp[0]== IDM_CLEARSHN:
				self.lv.Clear()
			elif lp[0]== IDM_CLEARSHC:
				self.lv2.Clear()
	
	
	# listview message handler
	def on_lv(self, hwnd, msg, wp, lp):
		if msg== self.shn_msg:
			self.shn.HandleMessage(hwnd, msg, wp, lp)
		
		elif msg=="shellchange":
			self.shc_handlemessage(hwnd, msg, wp, lp)
						
								
	# GUI message handler				
	def onMSG(self, hwnd, msg, wp, lp):
		if msg in ('menu open', 'menu popup', 'menu choice'):
			self.handle_menu_msg(hwnd, msg, wp, lp)
		
		if msg=="size":
			x, y, w, h= lp
			
			self.DeferWindows(
			(self.lv, x, y, w, h/2),
			(self.lv2, x, y+(h/2), w, h/2),
			)
			self.lv2.SetColumnWidth(0, w-1)
			w= lp[2]/5
			self.lv.SetColumnWidth(0, w)
			self.lv.SetColumnWidth(1, w*2)
			self.lv.SetColumnWidth(2, w*2-1)
		
				
		elif msg=="destroy":
			try:
				dragdrop.Revoke(self.lv.Hwnd)
			except: pass
			try:
				dragdrop.Revoke(self.lv2.Hwnd)
			except: pass
			try: 
				if self.sh: self.sh.Close()
			except: pass
			self.close_notifiers()
			
			
#---------------------------------------------------		

w = window()
w.Run()


