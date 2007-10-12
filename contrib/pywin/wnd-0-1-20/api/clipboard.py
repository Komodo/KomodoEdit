"""clipboard the ole way


TODO
	SetClipboardViewer

"""

from wnd.api.ole.wintypes import (ole32,
																user32,
																byref,
																POINTER,
																pointer)
from wnd.api.ole.dataobject import (DataObject, 
																DataObjectPointer,
																IDataObject)
from wnd.api.clipformats import (cf,
															GetFormatName,
															GetFrameworkName,
															GetFormatNameN,
															GetFrameworkNameN,
															RegisterClipboardFormat,)
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def Clear():
	result= False
	if user32.OpenClipboard(None):
		if user32.EmptyClipboard():
			result= True
		user32.CloseClipboard()
	return result

def IsFormatAvailable(format):
	return bool(user32.IsClipboardFormatAvailable(format.fmt.cfFormat))
	
def GetDataObject():
	dataobject = DataObjectPointer()
	ole32.OleGetClipboard(dataobject.ptr)
	return dataobject
	
def SetDataObject(dataobject):
	ole32.OleSetClipboard(0)
	result = ole32.OleSetClipboard(dataobject.GetComPointer())

def Flush():
	return not ole32.OleFlushClipboard()

def IsClipboard(dataobject):
	return not ole32.OleIsCurrentClipboard(dataobject.GetComPointer())



