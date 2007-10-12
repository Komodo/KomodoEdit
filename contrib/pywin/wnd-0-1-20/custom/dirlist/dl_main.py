"""mainframe class for the dirlist"""


import traceback
from wnd.wintypes import user32
from wnd.controls import helpers
from wnd.api import shell, wintime

import dl_container, dl_listview, dl_header_control, dl_shnotify, dl_contextmenu, dl_dragdrop, dl_tooltip, dl_listfiles

## language support
import locale, dl_lang
DECIMALSEP= locale.localeconv()['decimal_point']

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


class Mainframe(object):
	SHN_MSG= user32.RegisterWindowMessageA("sh_notify_msg")
	CLSIDLS= {'desktop' : 0,'internet' : 1,'programs' : 2,'controls' : 3,
			'printers' : 4,'personal' : 5,'favorites' : 6,'startup' : 7,'recent' : 8,
			'sendto' : 9,'bitbucket' : 10,'startmenu' : 11,'desktopdirectory' : 16,
			'drives' : 17,'network' : 18,'nethood' : 19,'fonts' : 20,'templates' : 21,
			'common_startmenu' : 22,'common_programs' : 23,'common_startup' : 24,
			'common_desktopdirectory' : 25,'appdata' : 26,'printhood' : 27,
			'altstartup' : 29,'common_altstartup' : 30,'common_favorites' : 31,
			'internet_cache' : 32,'cookies' : 33,'history' : 34}
	
	
	
	def __init__(self, parent, x, y, w, h, msgHandler, *styles):

		
		self.lastError= None

				
		self.Lang= dl_lang.get_lang(locale.getdefaultlocale()[0][:2])
		
		
		self.Shell= shell.ShellNamespace()

		self.pIdls= {}		## address --> obj
		
		self.validstyles= ['largeicon', 'border', 'clientedge', 'editlabels',
										'showselalways', 
										
										## can not be changed at runtime
										'noshellnotify', 'nocontextmenu',
										'nocontextmenu2', 'nohandleerrors',
										
										'nodragdrop', 'list', 'icon', 'report', 'tabstop']
		self.styles= []

		self.MsgHandler= msgHandler
		
		## init windows
		self.Container= dl_container.Container(self, parent, x, y, w, h)
		self.Hwnd= self.Container.Hwnd
		
		self.Listview= dl_listview.Listview(self, self.Container, 'gridlines')
		# 'nocolumnheader'
		## makes style parsing easier
		self.Listview.Style.WS_CLIENT_LARGEICON= 0
		self.Listview.Style.WS_CLIENT_NOSHELLNOTIFY= 0
		self.Listview.Style.WS_CLIENT_NOCONTEXTMENU= 0
		self.Listview.Style.WS_CLIENT_NOCONTEXTMENU2= 0
		self.Listview.Style.WS_CLIENT_NODRAGDROP= 0
		self.Listview.Style.WS_CLIENT_NOHANDLERRORS= 0
				
		self.Header= dl_header_control.HeaderControl(self, self.Container)

		self.FileLister= dl_listfiles.ListFiles(self)
		
		styles= list(styles)
		if 'noshellnotify' in styles:
			self.SHNotify= None
			self.SHChangeNotify= None

		else:
			self.SHNotify= dl_shnotify.SHNotify(self, self.Listview)
			self.SHChangeNotify= dl_shnotify.SHChangeNotify(self)
		
		if 'nocontextmenu' in styles:
			self.SHContextMenu= None
		else:
			self.SHContextMenu= dl_contextmenu.SHContextMenu(self)
		
		if 'nodragdrop' in styles:
			self.DragDrop= None
		else:
			self.DragDrop= dl_dragdrop.DragDrop(self)

		
		if 'nocontextmenu2' in styles:
			self.ContextMenu2= None
		else:
			self.ContextMenu2= dl_contextmenu.ContextMenu2(self)

					
		
		## currently disabled
		self.Tooltip= dl_tooltip.DLTooltip(self, self.Listview)
		self.Tooltip.SetFont(self.Listview.GetFont())
		#self.Listview.SetTooltips(self.Tooltip)
		#self.Tooltip.SetToolTip(self.Listview, 'foo text')


		## may apply on more instances...
		if 'nohandleerrors' in styles:
			self.FileLister.handle_errors= False		
		
		self.SetStyle(*styles)
		
				

	def SetStyle(self, *styles):
		newstyle= helpers.ParseStylesSZ(self.validstyles, self.styles, styles)
		
		if 'largeicon' in newstyle:
			if self.Listview.DL_IsSmallIcon():
				self.Listview.DL_SetImagelist('large')
		else:
			if not self.Listview.DL_IsSmallIcon():
				self.Listview.DL_SetImagelist('small')
		
		self.Listview.SetStyle(*styles)
		
		if 'tabstop' in styles:
			self.Container.SetStyle('tabstop')
		else:
			self.Container.SetStyle('-tabstop')
		
			
		self.styles= newstyle
		
	
	
	
	def SetLastError(self, exc, value):
		if exc and value:
			self.lastError= ''.join(traceback.format_exception_only(exc, value))
		else:
			self.lastError= None
			
	def GetLastError(self):
		error= self.lastError
		self.lastError= None
		return error


	def Reset(self):
		for pIdl in self.pIdls.values():
			shell.PidlFree(pIdl)
		self.pIdls= {}


	def Close(self):
		self.Reset()
		try: self.Shell.Close()
		except: pass	
		try: self.DragDrop.Close()
		except: pass
		try: self.SHContextMenu.Close()
		except: pass
		try: self.SHNotify.Close()
		except: pass

	def DL_HasDir(self):
		return self.Header.DL_HasDir()


	def FormatInt(self, n):
		## formats an integer as string according to locale settings
		n= str(n)
		out= []
		counter= 0
		
		for i in reversed(range(len(n))):
			out.insert(0, n[i])
			if counter==2:
				if i == 0: break
				out.insert(0, DECIMALSEP)
				counter= 0
			else:
				counter += 1
		
		return ''.join(out)

	def FormatTime(self, filetime):
		filetime= wintime.FiletimeToLocalFiletime(filetime)
		t= wintime.FiletimeToSystemtime(filetime)
		return '%s.%s.%s %s:%s:%s' % (t.wDay, 
																t.wMonth,
																t.wYear, 
																t.wHour, 
																t.wMinute,
																t.wSecond)
		
	def GetViewLang(self):
		## used internally. Returns the currently used language (module)
		return self.Lang

	def GetLang(self):
		return self.Lang.LANG
	
	def SetLang(self, lang_code):
		self.Lang= dl_lang.get_lang(lang_code)
		self.Listview.SetLang(self.Lang)
		self.ContextMenu2.SetLang(self.Lang)