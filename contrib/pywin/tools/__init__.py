

"""***************************************************************************
Create a new GUID and sets it as string to the clipboard
***************************************************************************"""
def ClipGUID():
	from ctypes import oledll, byref
	from ctypes.com import GUID
	from wnd.api import clipboard

	guid= GUID()
	oledll.ole32.CoCreateGuid(byref(guid))
	text= clipboard.cf.text(str(guid))
	do= clipboard.DataObject(text)
	clipboard.SetDataObject(do)
	clipboard.Flush()
	do.Close()
	text.value= None

