"""dragdrop handler for the dirlist


The shell is doing most of the work here. On the drop side we can query for the
IDropTarget on an item in the current folder or the IDropTarget of the current folder
and pass the DataObject to the interface directly. 
If we want to drag data we simply query for the DataObject of one or more pIdls
in our folder and the shell will equip it with the required data to do the drag 
in IDLISTARAY and HDROP format. We could equip the DataObject by hand with
Performed DropEffect" and "Preferred DropEffect", but I don't know if this is realy
necesary.  We'll see.

"""

from wnd.api import shell
from wnd.api.ole import dragdrop

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class DragDrop(dragdrop.DragDrop):
	def __init__(self, mainframe):
		
		self.Mainframe= mainframe
		
		dragdrop.DragDrop.__init__(self, self.Mainframe.Listview.Hwnd)
		dragdrop.Register(self.Mainframe.Listview.Hwnd, self)
		dragdrop.Register(self.Mainframe.Header.Hwnd, self)

		self.fRMouse= False

	
	def Close(self):
		dragdrop.Revoke(self.Mainframe.Listview.Hwnd)
		dragdrop.Revoke(self.Mainframe.Header.Hwnd)
	
	
	#-------------------------------------------------------------
	# drag handler
	
	def onDrag(self, hwnd, msg, wp, lp):
		arr= self.Mainframe.Listview.DL_GetPidlsSelected()
		if arr:
			DataObject= self.Mainframe.Shell.GetDataObject(arr)
			dragdrop.DoDragDrop(DataObject, self, 'copy', 'move', 'link')
				
	
	#--------------------------------------------------------------
	# drop handler

	def onMSG(self, hwnd, msg, wp, lp):
		if msg=='dragdrop':
			
			if wp=='dragenter':
				if lp[0].HasFormat(dragdrop.cf.idlistarray)  or	 \
					lp[0].HasFormat(dragdrop.cf.hdropfiles):
					self.Mainframe.Listview.SetFocus()
					
					self.fRMouse = bool(lp[1] & dragdrop.MK_RBUTTON)
					return True
				return False	
					
						
			elif wp=='dragover':
				self.Mainframe.Listview.RemoveItemDropHilight(-1)
				result= self.Mainframe.Listview.ItemHittest(lp[1].x, lp[1].y)
				if result:
					self.Mainframe.Listview.DropHilightItem(result[0])
					pIdl= self.Mainframe.Listview.DL_GetPidlRel(result[0])
				else:
					pIdl= None
				return bool(self.Mainframe.Shell.GetDropTarget(pIdl))
				## XXX CHECK 
				## stupid shell always returns True here...
				#return self.Mainframe.Shell.IsDropTarget(pIdl)
														
									
			elif wp=='dragleave':
				self.Mainframe.Listview.RemoveItemDropHilight(-1)
				return False
			
					
			elif wp=='drop':
				## Catch22 is here to always call 'DragEnter' before calling
				## 'Drag'. This is due to implementation details of IDropTarget
				## ('DragEnter' is usually used to set a var indicating if to allow drop in
				## the 'Drop' method). Simply bypass this nonsense here... 
				## Also querying the DropTarget interface this late saves some messy
				## bookeeping of various DropTargets on DragOver.
				self.Mainframe.Listview.RemoveItemDropHilight(-1)				
				result= self.Mainframe.Listview.ItemHittest(lp[2].x, lp[2].y)
				if result:
					pIdl= self.Mainframe.Listview.DL_GetPidlRel(result[0])
				else:
					pIdl= None
				DropTarget= self.Mainframe.Shell.GetDropTarget(pIdl)
							
				if DropTarget:
					if self.fRMouse:	## always display menu on RBUTTON
						lp= list(lp)
						lp[1] |= dragdrop.MK_CONTROL
					
					if DropTarget.DragEnter(*lp):
						if self.fRMouse:
							self.MenuAddDropEffects(lp[0], lp[3])
											
						if DropTarget.Drop(*lp):
							return True
				return False


	def MenuAddDropEffects(self, DataObject, pEffects):
			## adds some additional drop effects to the menu that pops up 
			## when the shift key is held on RBUTTON
			##
			idlarr= dragdrop.cf.idlistarray()
			if DataObject.HasFormat(idlarr):
				DataObject.GetData(idlarr)
				idlist= idlarr.value
				idlarr.value= None
								
				cwd= self.Mainframe.Shell.GetCwd()
				
				try:
					self.Mainframe.Shell.SetCwd(idlist[0])

					arr= (shell.PIDL*(len(idlist)-1))()
					for n, i in enumerate(idlist[1:]):
						arr[n]= i

					fAttrs= dragdrop.DROPEFFECT_COPY | dragdrop.DROPEFFECT_MOVE |  dragdrop.DROPEFFECT_LINK
					pEffects[0] |= self.Mainframe.Shell.GetAttributes(arr, fAttrs) & fAttrs
				except: pass						
								
				self.Mainframe.Shell.SetCwd(cwd)

			

				
		