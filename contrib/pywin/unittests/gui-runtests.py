
"""Runs unittests from a GUI.

The gui will search all subfolders for modules starting with 'test_'.
All files matching this pattern will be listed (dynamically) in the 
GUIs menu.

Each module should define a suites function, returning the runable test suites

Each modue shoulddefine a variable PARENT, to allow the GUI to
assign itsself to. Right before running the suite the GUI will assign 
itsself to this variable to allow the tests to use the GUI as parent
window.  

Each test case may include the Helpers class from the testhelpers
module within its base classes. The helpers class includes
a message handler ('onMSG'), collecting all messages send in a 
cache. The methods 'GetMsg' and 'PeekMsg' can be used to
find out if a certain message was send. 'ClearMsgCache' will clear
the cache.





"""


import os, array, imp, unittest

## only dependency on the framework here is 'fw.IsReflectMessage'
from wnd import fwtypes as fw
from wnd.tools.dlgeditor import dlgeditor
from ctypes.wintypes import *

windll.comctl32.InitCommonControls()
user32= windll.user32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

VERBOSITY= 2

#********************************************************************
#********************************************************************

class Dialog(dlgeditor.DlgEditor):
	def __init__(self):
		
		# setup a template
		self.BeginTemplate(None, 'unittest', 50, 50, 300, 300, None, 'sysmenu', 'sizebox', )
		self.Item(WC_LISTVIEW, IDC_LV1, '', 0, 0, 200, 189, 'visible', 'showselalways', 'report', 'border')
		
		self.Hwnd= 0								## test suites require this to be present
		self.hwndLv= 0
		self.linebuffer= LineBuffer()
			
	#--------------------------------------------------------------------
	# message handler
	
	def onMSG(self, hwnd, msg, wp, lp):
		
		## required to make framework controls work
		result= fw.IsReflectMessage(hwnd, msg, wp, lp)
		if result != None: return result
		
		
		if msg==WM_INITDIALOG:
			self.Hwnd= hwnd
			user32.SetMenu(hwnd, self.SetupMenu())
			
			# setup the listview to display unittest output
			self.hwndLv= user32.GetDlgItem(hwnd, IDC_LV1)
			if not self.hwndLv: 
				import sys
				sys.exit(1)
			self.LVAddColumn( 'unittest output')
			self.LVSetExtendedStyles()
			self.SizeControls(hwnd)

		
		elif msg==WM_SIZE:
			## size controls along with the parent window
			self.SizeControls(hwnd)

		
		elif msg==WM_INITMENUPOPUP:
			if HIWORD(lp): return ##system menu
			
			if SZ_POPUP_UNITTEST== self.MenuItemText(hwnd, wp):
				## fill menu 1 dynamically with folders containing unittests
				self.MenuClear(wp)
				ID.Reset()
				id= ID.New()
				user32.AppendMenuA(wp, MF_STRING,  id, SZ_MENUITEM_ALL)
				user32.AppendMenuA(wp, MF_SEPARATOR, 0, 0)
				curdir= os.getcwd()
				for root, dirs, files in os.walk(curdir):
					for i in files:
						if IsUnittest(i):
							id = ID.New()
							user32.AppendMenuA(wp, MF_STRING,  id, root[len(curdir)+1:])
							break
			
			elif SZ_POPUP_UNITTEST2== self.MenuItemText(hwnd, wp):
				## fill menu 2 dynamically with unittest folders and files
				self.MenuClear(wp)
				ID2.Reset()
				curdir= os.getcwd()
				
				for root, dirs, files in os.walk(curdir):
					tests= [i for i in files if IsUnittest(i)]
					if tests:
						hPopup = user32.CreatePopupMenu()
						user32.AppendMenuA(wp, MF_POPUP, hPopup, '%s\\' % root[len(curdir)+1:])
						for n, i in enumerate(tests):
							id = ID2.New()
							if n % 17: 
								user32.AppendMenuA(hPopup, MF_STRING,  id, i)
							else:
								user32.AppendMenuA(hPopup, MF_STRING | MFT_MENUBARBREAK,  id, i)
							
							
			
		
		elif msg==WM_COMMAND:
			if not lp:							# menu commands
				#if HIWORD(wp):		# accelerator message
				if not wp: return


				name=  self.MenuItemText(hwnd, wp)
				hParent= self.MenuGetParent(user32.GetMenu(hwnd), wp)
				nameParent= self.MenuItemText(hwnd, hParent)
				
				if nameParent.endswith('\\'):
					# run single file unittest
					path= os.path.join(os.getcwd(), nameParent, name)
					self.RunUnitTest(os.path.splitext(name)[0], path)
				
				elif name== SZ_MENUITEM_ALL:
					# run all unittest folders
					ids= self.ListMenu(hParent)
					out= []
					for i in ids:
						name=  self.MenuItemText(hwnd, i)
						if name and name != SZ_MENUITEM_ALL:
							out.append(name)
					self.RunUnitTests(*out)	

				else:
					# run single unittest folder
					path= os.path.join(os.getcwd(), name)
					self.RunUnitTests(path)
				
											
	
	#--------------------------------------------------------------------
	# equipment for unittests
	# unittest output is redirected here
	
	def write(self, data):
		line=	self.linebuffer.write(data)
		if line != None:
			self.LVAddItem(line)
	
	def flush(self):
		for i in self.linebuffer.flush():
			if i != None:
				self.LVAddItem(line)
				
	## runs unittests of a single file
	def RunUnitTest(self, name, path):
		self.LVClear()
			
		mod= imp.load_source(name, path)
		if hasattr(mod, 'suite'):
			self.write('testing: %s\n' % name[5:])
			
			mod.PARENT= self
			suite=unittest.TestSuite(mod.suite())
			unittest.TextTestRunner(stream=self, 
						verbosity=VERBOSITY).run(suite)
			self.write('*' *64 + '\n' )
			mod.PARENT= None
				
	
	## runs unittests of all files in dir(s)
	def RunUnitTests(self, *dirs):
		self.LVClear()
		for i in dirs:
			root, dirs, files = os.walk(i).next()
			for x in files:
				if x.startswith('test_'):
					name, ext= os.path.splitext(x)
					if ext.lower()=='.py':
						self.write('testing: %s\n' % name[5:])
											
						path=os.path.join(root, x)
						mod= imp.load_source(name, path)
						if hasattr(mod, 'suite'):
							mod.PARENT= self
							suite=unittest.TestSuite(mod.suite())
							unittest.TextTestRunner(stream=self, 
										verbosity=VERBOSITY).run(suite)
							
							self.write('*' *64 + '\n' + '*' *64 + '\n')
							mod.PARENT= None
				
		
		
	#---------------------------------------------------------------------
	# helper methods

	def SizeControls(self, hwnd):
		## to reduce flicker use DefferWindowPos, should help even for one control
		rc= RECT()
		if user32.GetClientRect(hwnd, byref(rc)):
			user32.MoveWindow(self.hwndLv, rc.left, rc.top, rc.right-rc.left, rc.bottom-rc.top, 1)
			user32.SendMessageA(self.hwndLv, 
													LVM_SETCOLUMNWIDTH,
													0, 
													rc.right-rc.left -(user32.GetSystemMetrics(SM_CXEDGE)*2)	 ##
													)
		
	
	def SetupMenu(self):
		hMenu = user32.CreateMenu()
		hPopup1 = user32.CreatePopupMenu()
		user32.AppendMenuA(hMenu, MF_POPUP, hPopup1, SZ_POPUP_UNITTEST)
		hPopup2 = user32.CreatePopupMenu()
		user32.AppendMenuA(hMenu, MF_POPUP, hPopup2, SZ_POPUP_UNITTEST2)
		return hMenu
	
	def MenuItemText(self, hwnd, ID, bypos=False):
		bypos= bypos and MF_BYPOSITION or MF_BYCOMMAND
		n= user32.GetMenuStringA(user32.GetMenu(hwnd), ID, None, 0, bypos)
		p= create_string_buffer(n +1)
		user32.GetMenuStringA(user32.GetMenu(hwnd), ID, p, sizeof(p), bypos)
		return p.value

	def MenuGetParent(self, hMenu, ID):
		for hParent, ids in self.MenuWalk(hMenu):
			if ID in ids:
				return hParent
			
	def ListMenu(self, hMenu):
		n = user32.GetMenuItemCount(hMenu)
		mi= MENUITEMINFO()
		out= []
		for i in range(n):
			mi.fMask = 2 #  MIIM_ID
			user32.GetMenuItemInfoA(hMenu, i, 1, byref(mi))
			out.append(mi.wID)
		return out
	
	def MenuWalk(self, hMenu=None):
		n = user32.GetMenuItemCount(hMenu)
		mi= MENUITEMINFO()
		for i in range(n):
			mi.fMask = 2 #  MIIM_ID
			user32.GetMenuItemInfoA(hMenu, i, 1, byref(mi))
			handle = user32.GetSubMenu(hMenu, i)
			if handle:
				yield handle, self.ListMenu(handle)
				for i in self.MenuWalk(handle): 
					yield i
				
	def MenuClear(self, hMenu):
		n = user32.GetMenuItemCount(hMenu)
		for i in range(n):
			if not user32.DeleteMenu(hMenu, 0, MF_BYPOSITION):
				raise RuntimeError("could not remove item")

	
	def LVAddItem(self,text):
		n= user32.SendMessageA(self.hwndLv, LVM_GETITEMCOUNT, 0, 0)
		lvi =LV_ITEM()
		lvi.mask= LVIF_TEXT
		lvi.pszText= text
		lvi.iItem   = n
		result= user32.SendMessageA(self.hwndLv, LVM_INSERTITEM, 0, byref(lvi))
		if result > -1:
			user32.SendMessageA(self.hwndLv, LVM_ENSUREVISIBLE, result, 1)
			user32.SendMessageA(self.hwndLv, LVM_REDRAWITEMS, result, result)
			user32.UpdateWindow(self.Hwnd)

	def LVAddColumn(self, name):
			lvc= LV_COLUMN()
			lvc.mask = LVCF_WIDTH | LVCF_TEXT
			lvc.cx = 100
			lvc.pszText = name
			result = user32.SendMessageA(self.hwndLv, LVM_INSERTCOLUMN, 0, byref(lvc))
		
	def LVSetExtendedStyles(self):	
		user32.SendMessageA(self.hwndLv, LVM_SETEXTENDEDLISTVIEWSTYLE, LVS_EX_GRIDLINES, LVS_EX_GRIDLINES)

	def LVClear(self):
		user32.SendMessageA(self.hwndLv, LVM_DELETEALLITEMS, 0, 0)
		



#**************************************************************************
# helpers 
#**************************************************************************

class LineBuffer:
	"""Helper class. Interface between stream output
	and listview input."""
	def __init__(self):
		self.array = array.array
		self.buff =self.array('c')
		
	def flush(self):
		"""Flushes the buffer in an iterator loop, returning
		the contents of the buffer linewise."""		
		out = []
		while True:
			try:
				n = self.buff.index('\n')
				p = self.buff[:n].tostring()
				del self.buff[:n+1]
				yield p
			except:
				n = self.buff.buffer_info( )[1]
				if n:
					p = self.buff[:n].tostring()
					del self.buff[:n]
					yield p
				else:
					break

	def write(self, chars):
		"""Writes chars to the buffer and returns the next line
		if there is a complete line, else returns None."""
		if len(chars)==1:
			self.buff.append(chars)
		else:
			p = self.array('c', chars)
			self.buff.extend(p)
		try:
			n = self.buff.index('\n')
			p = self.buff[:n].tostring()
			del self.buff[:n+1]
			return p
		except:
			return None


# reserve some ids for dynamic popups
class _ID:
	
	def __init__(self, start):
		self.start= start
		self.ids= start
	
	def New(self):
		self.ids += 1
		return self.ids
	
	def Reset(self):
		self.ids= self.start

ID= _ID(10000)
ID2= _ID(11000)



##
def IsUnittest(name):
	if os.path.basename(name).startswith('test_') and os.path.splitext(name)[1]=='.py':
		return True
	return False


## removes all 'pyc' files in tree
def StripPyc(path):
	for  root, dirs, files in os.walk(path):
		for i in files:
			if os.path.splitext(i)[1].lower()==".pyc":
				os.remove(os.path.join(root, i))
				


#**************************************************************************
# header stuff
#**************************************************************************

SZ_POPUP_UNITTEST  = 'test-dirs'
SZ_POPUP_UNITTEST2  = 'test-files'
SZ_MENUITEM_ALL    =   '*all*'
IDC_LV1               =     1000

def LOWORD(dword): return dword & 0x0000ffff
def HIWORD(dword): return dword >> 16

WM_INITDIALOG       = 272
WM_SIZE     = 5
WM_COMMAND          = 273
WM_INITMENUPOPUP    = 279

SM_CXEDGE              = 45

WC_LISTVIEW = "SysListView32"

class LV_COLUMN(Structure):
	_fields_ = [("mask",  c_uint),
						("fmt",  c_int),
						("cx",  c_int),
						("pszText", LPCSTR),						
						("cchTextMax",  c_int),
						("iSubItem",  c_int),
						("iImage",  c_int),
						("iOrder",  c_int)]	
	
class LV_ITEM(Structure):
	_fields_ = [("mask",  c_uint),
						("iItem",  c_int),
						("iSubItem",  c_int),
						("state",  c_uint),
						("stateMask",  c_uint),
						("pszText", LPSTR),
						("cchTextMax",  c_int),
						("iImage",  c_int),
						("lParam", LPARAM),
						("iIndent",  c_int)]

LVCF_WIDTH             = 2
LVCF_TEXT              = 4
LVIF_TEXT              = 1

LVM_FIRST = 4096
LVM_INSERTCOLUMN      = LVM_FIRST + 27
LVM_SETCOLUMNWIDTH  =  4126
LVM_SETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 54
LVM_GETITEMCOUNT  =  LVM_FIRST + 4
LVM_INSERTITEM = LVM_FIRST + 7
LVM_ENSUREVISIBLE      = LVM_FIRST + 19
LVM_DELETEALLITEMS     = LVM_FIRST + 9
LVM_REDRAWITEMS        = LVM_FIRST + 21

LVS_EX_GRIDLINES        = 1


class MENUITEMINFO(Structure):
	_fields_=[("cbSize", c_uint),  
					("fMask", c_uint), 
					("fType", c_uint), 
					("fState", c_uint), 
					("wID", c_uint), 
					("hSubMenu", HANDLE),
					("hbmpChecked", HANDLE),
					("hbmpUnChecked", HANDLE), 
					("dwItemData", DWORD), 
					("dwTypeData", DWORD),	# depends on fType 
					("cch", c_uint)] 
	def __init__(self):
		self.cbSize = sizeof(self)

MF_POPUP           = 16
MF_STRING          = 0
MF_SEPARATOR       = 2048
MF_CHECKED         = 8
MF_GRAYED          = 1
MF_DISABLED        = 2
MFT_MENUBARBREAK   = 32

MIIM_TYPE       = 16
MIIM_SUBMENU    = 4

MF_BYCOMMAND       = 0
MF_BYPOSITION      = 1024


#********************************************************************************
#********************************************************************************

d= Dialog()
d.RunModal()

## quite some leaks here

StripPyc(os.getcwd())
