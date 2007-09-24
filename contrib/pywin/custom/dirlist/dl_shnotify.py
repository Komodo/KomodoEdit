"""shell notify handler for the dirlist"""


from wnd.api import shell
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


## notify used for non filesystem part of the namespace
class SHNotify(shell.ShellNotify,):
	def __init__(self, mainframe, receiver):
		
		self.Mainframe= mainframe
		

		shell.ShellNotify.__init__(self, receiver, self.Mainframe.SHN_MSG, self.DL_OnHNotify)

	def Close(self):
		shell.ShellNotify.Close(self)
		

	def DL_OnHNotify(self, hwnd, msg, wp, lp):
		
		if msg=='shellnotify':
			
			## TODO 
			# -test driveadd and friends (...)
			# - test netshare/unshare
			# - updatedir, updateitem
			
			if wp in ('rename', 'renamefolder'):
				self.Mainframe.Listview.DL_RenamePidl(lp[0], lp[1])
			
			elif wp in ('create', 'mkdir', 'mediainserted', 'driveadd'):
				self.Mainframe.Listview.DL_AddPidl(lp)
			
			elif wp in ('delete', 'rmdir', 'mediaremoved', 'driveremoved'):
				self.Mainframe.Listview.DL_RemovePidl(lp[0])
						
			elif wp in ('netshare', 'netunshare'):
				self.Mainframe.Listview.DL_ShareUnsharePidl(lp, share= wp == 'netshare')
	
			elif wp=='updatedir':
				self.Mainframe.Listview.DL_Update()
				


## notify used for filesystem part of the namespace
class SHChangeNotify(shell.ShellChangeNotification):
	def __init__(self, mainframe):
		
		self.Mainframe= mainframe
		
		shell.ShellChangeNotification.__init__(self)

	def Register(self, path):
		shell.ShellChangeNotification.Register(self, path, 'filename', 'dirname')
		
	def Close(self):
		shell.ShellChangeNotification.Close(self)
	
	
	def onMSG(self, hwnd, msg, wp, lp):
				
		if msg=='shellchange':
						
			pIdls= self.Mainframe.pIdls.values()
			pIdlsNew= []
			
			## find out what has changed
			for i in self.Mainframe.Shell:
				free= True
				match= False
				for x in pIdls:
					if shell.PidlIsEqual(x, i):
						pIdls.remove(x)
						match= True
				
				if not match:
					pIdlsNew.append(i)
					free= False
				
				if free:
					shell.PidlFree(i)

			pIdlAbs= self.Mainframe.Shell.GetCwd()
			
			## remove pIdls
			for i in pIdls:
				self.Mainframe.Listview.DL_RemovePidl(shell.PidlJoin(pIdlAbs, i))
			
			## add new pIdls
			for i in pIdlsNew:
				self.Mainframe.Listview.DL_AddPidl(shell.PidlJoin(pIdlAbs, i))
				shell.PidlFree(i)
			
			## remame is just a remove followed by an add
			
			shell.PidlFree(pIdlAbs)
		
				

