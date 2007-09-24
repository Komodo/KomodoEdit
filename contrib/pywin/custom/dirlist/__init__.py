
"""
TODO

		- keep an eye on 'expand' message. 'collapsereset' as flag seems not to
			be passed. Some logic behind it, but if this is not respected by all
			supported systems collapsing will fail

		
		- Tooltips
			Still working on a way to implement Tooltips..
			Currently processing of the view is messed up completely
			when enabeling them. If anyone is interseted go to the 
			dl_listview module and enable and uncomment
			#self.HandleMessage(self.Msg.WM_MOUSEMOVE)
			This will enable tooltips for items in details view that are not
			fully visible


		
		- Header
			
			- DL_AdjustHeader does not work 110% reliable
				Sometimes the header is sized over the bounds of the Listview
				unecessarily making the scrollbar apear

			- Header does not relect the listview border style corrently
						
		
		
		- dragdrop
			expose DROPEFFECTS_* so the user can adjust them ??
		
		
		- ListFiles/ShellChangeNotification
			There seems to be an issue with ShellChangeNotification and
			Network drives. I have no way to test this currently.
			Dono if this affects ShellNotify aswell.
			
			For network drives winpath.IsDir should return False. 
			If so ShellNotify registers the notification handle. If not
			ShellChangeNotification takes over the job.

		- filespec
			allow setting of multiple filespecs ?? ('*.txt;*.ini')
		
		- ShellNotify
			Verify if or if not ShellNotify works with Explorer not being present
			on the system. Read somewhere that the SHChangeNotifyRegister
			api relies on Explorers DDE window being present (??). 
			The alternative shell coders come to my mind here.
			
		- Header
			sends 'rmbup'. Should be possible to trigger this from kexboard aswell

		- Enable user defined columns and columnorder
		
		- keyboard accelerators



KNOWN ISSUES
	- when the parent folder of of a folder is removed there is no
		notification that the items are no longer valid (would require
		to monitoring all parent folders of a folder, too). All attempts to
		process these items should throw a msgbox ('files system error')


"""






import os
from wnd.api import shell
from dl_main import Mainframe
from wnd.api import winpath
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class DirList(object):
	def __init__(self, parent, x, y, w, h, *styles):
				
		self._custom_Mainframe= Mainframe(parent, 
												x,
												y,
												w,
												h,
												self.onMESSAGE,
												*styles)
		self.Hwnd=  self._custom_Mainframe.Hwnd

	#-----------------------------------------------------------------------
	
	
	def SetRedraw(self, Bool):
		return self._custom_Mainframe.Listview.SetRedraw(Bool)
	
	def ListDir(self, path):
		return self._custom_Mainframe.Listview.DL_ListFiles(path)
	

	def IsDesktopFolder(self):
		return self._custom_Mainframe.Shell.IsDesktopFolder()
	
	
	def SortBy(self, sorttype='type', direction='ascending'):
		self._custom_Mainframe.FileLister.SetSortType(sorttype, direction)
		
	def GetSortBy(self):
		return self._custom_Mainframe.FileLister.GetSortType()
		
	def AllowNavigate(self, Bool, hideheader=False):
		return self._custom_Mainframe.FileLister.AllowNavigate(Bool, hideheader)
	
	def IsNavigateAllowed(self):
		return self._custom_Mainframe.FileLister.IsNavigateAllowed()
	
	def ShowFolders(self, Bool):
		return self._custom_Mainframe.FileLister.ShowFolders(Bool)

	def AreFoldersVisible(self):
		return self._custom_Mainframe.FileLister.AreFoldersVisible()
		
	def SetLang(self, lang_code):
		return self._custom_Mainframe.SetLang(lang_code)
	
	def GetLang(self):
		return self._custom_Mainframe.GetLang()
		
	def SetFilespec(self, filespec):
		self._custom_Mainframe.FileLister.SetFilespec(filespec)
	
	def GetFilespec(self):
		return self._custom_Mainframe.FileLister.GetFilespec()
		
	def Refresh(self):
		return self._custom_Mainframe.Listview.DL_Refresh()
	
	def GetLastError(self):
		return self._custom_Mainframe.GetLastError()
			
	def GetMinContextMenuID(self):
		return self._custom_Mainframe.SHContextMenu.GetMinContextMenuID() +1
			
	def IsSmallIcon(self):	
		return self._custom_Mainframe.DL_IsSmallIcon()
	
	
	## shell methods
	
	def GetPidl(self, lineo):
		return self._custom_Mainframe.Listview.DL_GetPidlAbs(lineno)
	
	def GetPidlRel(self, lineo):
		return shell.PidlCopy(self._custom_Mainframe.Listview.DL_GetPidlRel(lineno))
	
	def PidlFree(self, pIdl):
		return shell.PidlFree(pIdl)
	
	def GetName(self, lineno):
		return self._custom_Mainframe.Listview.GetItemText(lineno, 0)

	def GetPath(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		path= self._custom_Mainframe.Shell.GetParseName(pIdlRel)
		if winpath.Exists(path):
			return path
	
	def GetCwd(self, path=False):
		if path:
			path=  self._custom_Mainframe.Shell.GetParseName()
			if winpath.IsDir(path):
				return path
			return ''
		return self._custom_Mainframe.Shell.GetCwd()
	
	
	def GetCLSIDL(self):
		pIdl= self._custom_Mainframe.Shell.GetCwd()
		result= shell.CLSIDL_FromPidl(pIdl)
		shell.PidlFree(pIdl)
		return result


	
	def GetSize(self, lineno, asstring=False):
		## can not use getItemtext here, cos the thread may still be working
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		result= self._custom_Mainframe.Shell.GetData(pIdlRel)
		if result:
			if asstring:
				return self._custom_Mainframe.FormatInt(result[0])
			return result[0]
		
	def FormatInt(self, n):
		return self._custom_Mainframe.FormatInt(n)
	
	
	def GetDate(self, lineno, asstring=False):
		## can not use getItemtext here, cos the thread may still be working
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		result= self._custom_Mainframe.Shell.GetData(pIdlRel)
		if result:
			if asstring:
				return self._custom_Mainframe.FormatTime(result[1])
			return result[1]
			
	
	def GetIconIndex(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.GetIconIndex(pIdlRel)
	
	def IsFileSystem(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsFilesystem(pIdlRel)
	
	def IsFileSystemAnchestor(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsFileSystemAnchestor(pIdlRel)
	
	def IsRemovable(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsRemovable(pIdlRel)
	
	def IsHidden(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsHidden(pIdlRel)
	
	def IsFolder(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsFolder(pIdlRel)
	
	def IsLink(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsLink(pIdlRel)
	
	def IsReadOnly(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.IsReadOnly(pIdlRel)
	
	def IsShared(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.Isshared(pIdlRel)
	
	def CanCopy(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.CanCopy(pIdlRel)
	
	def CanMove(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.CanMove(pIdlRel)
	
	def CanLink(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.CanLink(pIdlRel)
	
	def CanRename(self, lineno):
		pIdlRel= self._custom_Mainframe.Listview.DL_GetPidlRel(lineno)
		return self._custom_Mainframe.Shell.CanRename(pIdlRel)
	
	## listview methods
	
	def __iter__(self):
		return self._custom_Mainframe.Listview.__iter__()
	
	def GetSelectedCount(self):
		return self._custom_Mainframe.Listview.GetSelectedCount()
	
	def SelectItem(lineno):
		return self._custom_Mainframe.Listview.SelectItem(lineno)
	
	def GetSelectedItem(self):
		return self._custom_Mainframe.Listview.GetSelectedItem()
	
	def IterSelected(self):
		return self._custom_Mainframe.Listview.IterSelected()
	
	def IsItemSelected(lineno):
		return self._custom_Mainframe.Listview.IsItemSelected(lineno)
	
	def DeselectItem(lineno):
		return self._custom_Mainframe.Listview.DeselectItem(lineno)
	
	def EnshureVisible(lineno):
		return self._custom_Mainframe.Listview.EnshureVisible(lineno)
	
	# base methods
	
	def SetFocus(self): return self._custom_Mainframe.Listview.SetFocus()
	def Show(self): return self._custom_Mainframe.Container.Show()
	def Hide(self): return self._custom_Mainframe.Container.Hide()
	def IsVisible(self): return self._custom_Mainframe.Container.IsVisible()
	
	def Disable(self): return self._custom_Mainframe.Container.Disable()
	def Enable(self): return self._custom_Mainframe.Container.Enable()
	def IsEnabled(self): return self._custom_Mainframe.Container.Isenabled()

	def GetWindowRect(self):	return self._custom_Mainframe.Container.GetWindowRect()
	def GetClientRect(self): return self._custom_Mainframe.Container.GetClientRect()
	
	def SetWindowPos(self, x, y): return self._custom_Mainframe.Container.SetWindowPos(x, y)
	def SetWindowSize(self, w, h): return self._custom_Mainframe.Container.SetWindowSize(w, h)
	def SetWindowPosAndSize(self, x, y, w, h): return self._custom_Mainframe.Container.SetWindowPosAndSize(x, y, w, h)
	def OffsetWindowPos(self, offX, offsY): return self._custom_Mainframe.Container.OffsetWindowPos(offsX, offsY)
	def OffsetWindowSize(self, offW, offsH): return self._custom_Mainframe.Container.OffsetWindowSize(offsW, offsH)

	
	
	#----------------------------------------------
	
	def onMESSAGE(self, hwnd, msg, wp, lp):
		self.onMSG(self.Hwnd, msg, wp, lp)
						
		
	def onMSG(self, hwnd, msg, wp, lp):
		pass
	

	
