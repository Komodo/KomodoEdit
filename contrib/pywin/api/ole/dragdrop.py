
from ctypes.com import IUnknown, GUID, STDMETHOD, HRESULT, COMObject, ole32
from wnd.api.ole.dataobject import IDataObject, DataObjectFromPointer
from wnd.api.clipformats import cf
from wnd.wintypes import (BOOL,
												DWORD,
												POINT,
												POINTER,
												byref,
												windll
												)
from ctypes.com import (REFIID)
ole32= windll.ole32
import traceback
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::.

class IDropSource(IUnknown):
    _iid_ = GUID("{00000121-0000-0000-C000-000000000046}")

IDropSource._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "QueryContinueDrag", BOOL, DWORD),
    STDMETHOD(HRESULT, "GiveFeedback", DWORD)]


class IDropTarget(IUnknown):
    _iid_ = GUID("{00000122-0000-0000-C000-000000000046}")

IDropTarget._methods_ = IUnknown._methods_ + [
    STDMETHOD(HRESULT, "DragEnter", POINTER(IDataObject), DWORD, POINT, POINTER(DWORD)),
    STDMETHOD(HRESULT, "DragOver", DWORD, POINT, POINTER(DWORD)),
    STDMETHOD(HRESULT, "DragLeave"),
    STDMETHOD(HRESULT, "Drop", POINTER(IDataObject), DWORD, POINT, POINTER(DWORD))]	


S_OK  =  0
E_UNEXPECTED         = 0x8000FFFFL
E_INVALIDARG             = 0x80070057L

DROPEFFECT_NONE   = 0 
DROPEFFECT_COPY   = 1 
DROPEFFECT_MOVE   = 2 
DROPEFFECT_LINK   = 4 
DROPEFFECT_SCROLL = -2147483648


D_EFFECTS= {'none':0,'copy':1,'move':2,'link':4}


MK_LBUTTON  = 1
MK_RBUTTON  = 2
MK_SHIFT    = 4
MK_CONTROL  = 8
MK_MBUTTON    =      16
MK_ALT	=  32


DRAGDROP_S_CANCEL = 262401
DRAGDROP_S_DROP = 262400
DRAGDROP_S_USEDEFAULTCURSORS = 262402

E_OUTOFMEMORY      =             0x8007000L
E_UNEXPECTED                 =              0x8000FFFFL


	
#***********************************************************
# drag drop class
#***********************************************************
class DragDropFactory(object):
    def LockServer(self, arg, arg2):
		pass

#***********************************************************
class DragDrop(COMObject):
	_com_interfaces_ = [IDropTarget, IDropSource]
	_factory = DragDropFactory()


	def __init__(self, hwnd):
		COMObject.__init__(self)
				
		self.allow_drop = False
		self.Hwnd= hwnd
		self.dropeffect= DROPEFFECT_MOVE | DROPEFFECT_COPY | DROPEFFECT_LINK


			
	def GetDropTargetPointer(self):
		return byref(self._com_pointers_[0][1])
	
	def GetDropSourcePointer(self):
		return byref(self._com_pointers_[2][1])
	
	
		
	def SetDropEffect(self, *effects):
		self.dropeffect= 0
		for i in effects:
			try:
				self.dropeffect |=D_EFFECTS[i]
			except: raise ValueError, "invalid drop effect: %s" % i
	
	def GetDropEffect(self):
		out= []
		if self.dropeffect & DROPEFFECT_MOVE: out.append('move')
		if self.dropeffect & DROPEFFECT_COPY: out.append('copy')
		if self.dropeffect & DROPEFFECT_LINK: out.append('link')
		if out: return out
		return ['none', ]
	
	
	def _get_dropeffect(self, keystate, point, allowed):
		# 1. check "point" -> do we allow a drop at the specified coordinates?
		
		effect = 0
		test= keystate & (MK_CONTROL|MK_SHIFT)
		if test==MK_CONTROL:
			effect  = allowed & (self.dropeffect & DROPEFFECT_COPY)
		elif test==MK_SHIFT:
			effect =  allowed & (self.dropeffect & DROPEFFECT_MOVE)
		elif test==MK_CONTROL|MK_SHIFT:
			effect =  allowed & (self.dropeffect & DROPEFFECT_LINK)
		
		if effect == 0:
			if allowed & DROPEFFECT_MOVE:
				effect = self.dropeffect & DROPEFFECT_MOVE
				if effect: return effect
						
			if allowed & DROPEFFECT_COPY:
				effect =  self.dropeffect & DROPEFFECT_COPY
				if effect: return effect

			if allowed & DROPEFFECT_LINK:
				effect =   self.dropeffect & DROPEFFECT_LINK
		return effect
			
	
	## drop target methods
	def DragEnter(self, this, pDataObject, keystate, point, pEffect):
		if pEffect:
			try:
				result= self.onMSG(self.Hwnd, "dragdrop", "dragenter", ( 				DataObjectFromPointer(pDataObject), keystate, point, pEffect))
			except:
				traceback.print_exc()
				return E_UNEXPECTED
			if result==False:
					pEffect[0] = DROPEFFECT_NONE
					self.allow_drop = False
			else:
				pEffect[0] = self._get_dropeffect(keystate, point, pEffect[0])
				self.allow_drop = True
			return S_OK
		else:
			return E_INVALIDARG
			
	
	def DragOver(self, this, keystate, point, pEffect):
		if pEffect:
			if self.allow_drop:
				try:
					result= self.onMSG(self.Hwnd, "dragdrop", "dragover", (keystate, point, pEffect))
					if result !=False:
						pEffect[0] = self._get_dropeffect(keystate, point, pEffect[0])
						return S_OK
				except:
					traceback.print_exc()
					return  E_UNEXPECTED
				
		pEffect[0] = DROPEFFECT_NONE
		return S_OK

	
	def DragLeave(self, this):
		try:
			self.onMSG(self.Hwnd, "dragdrop", "dragleave", 0)
		except:
			traceback.print_exc()
		return S_OK
	
	
	def Drop(self, this, pDataObject, keystate, point, pEffect):
		if self.allow_drop:
			try:
				result= self.onMSG(self.Hwnd, "dragdrop", "drop", (DataObjectFromPointer(pDataObject), keystate, point, pEffect))
				if result != False:
					pEffect[0] = self._get_dropeffect(keystate, point, pEffect[0])
					return S_OK
			except:
				traceback.print_exc()
			
		pEffect[0] = DROPEFFECT_NONE
		return S_OK
	
	
	
	## drop source methods
	def QueryContinueDrag(self, this, fEscapePressed, grfKeyState):
		if fEscapePressed:
			return DRAGDROP_S_CANCEL
		if not (grfKeyState & (MK_LBUTTON|MK_RBUTTON)):
			return DRAGDROP_S_DROP
		return S_OK
 
	def GiveFeedback(self, this, dwEffect):
		try:
			result= self.onMSG(self.Hwnd, "dragdrop", "feedback", dwEffect)
			if result==False:
				return S_OK
		except:
			traceback.print_exc()
		return DRAGDROP_S_USEDEFAULTCURSORS
	
	
	def onMSG(self, hwnd, msg, wp, lp):
		pass

	
#********************************************************
# 
#********************************************************
# TODO: document

class DropTargetPointer(object):
	def __init__(self):
		self._DropTarget= POINTER(IDropTarget)()
		self.refiid= REFIID(IDropTarget._iid_)
		self.ptr= byref(self._DropTarget)

		
	def AddRef(self):
		return self._DropTarget.AddRef()
	
	def Release(self):
		return self._DropTarget.Release()
	
	
	def DragEnter(self, DataObject, KeyState, Point, pEffect):
		try:
			self._DropTarget.DragEnter(DataObject.GetComPointer(), KeyState, Point,  pEffect)
			return True
		except:
			return False

	def DragLeave(self):
		try:
			self._DropTarget.DragLeave()
			return True
		except:
			return False

	def DragOver(self, KeyState, Point, pEffect):
		try:
			self._DropTarget.DragOver(KeyState, Point, pEffect)
			return True
		except:
			return False

	def Drop(self, DataObject, KeyState, Point, pEffect):
		try:
			self._DropTarget.Drop(DataObject.GetComPointer(), KeyState, Point, pEffect)
			return True
		except:
			return False

#********************************************************
# drag drop functions
#********************************************************

def Register(hwnd, DropTarget):
	return ole32.RegisterDragDrop(hwnd, DropTarget.GetDropTargetPointer())

Revoke = ole32.RevokeDragDrop

def DoDragDrop(DataObject, DropSource, *effects):
	effect= 0
	for i in effects:
		try:
			effect |= D_EFFECTS[i]
		except:
			raise ValueError, "invalid drop effect: %s" % i
	
	effectOut= DWORD()
	result = ole32.DoDragDrop(DataObject.GetComPointer(),
														DropSource.GetDropSourcePointer(),
														effect,
														byref(effectOut)
														)
	if result==DRAGDROP_S_CANCEL: result= 'cancel'
	elif result==DRAGDROP_S_DROP: result= 'drop'
	elif result==E_OUTOFMEMORY: result= 'outofmemory'
	elif result==E_UNEXPECTED: result= 'unexpected'
	else: result= 'unknown error'
	if effectOut.value==DROPEFFECT_NONE: effect= 'none'
	elif effectOut.value==DROPEFFECT_COPY: effect= 'copy'
	elif effectOut.value==DROPEFFECT_MOVE: effect= 'move'
	elif effectOut.value==DROPEFFECT_LINK: effect= 'link'
	else: effect= 'unknown'
	return result, effect

