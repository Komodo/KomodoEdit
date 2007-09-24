
"""Just the very beginning of some resource dumper
for converting wi32 resources to resources that can
be loaded dynamically from a python module

This works currently for 1-bit icons and cursors only.
Higher bit resources need quite some special handling
(storing: the device-independend bits including the color pallette,
loading: create a device-independend bitmap
				restore palette
				create a device dependend from the device-independend one
				then use CreateIconIndirect or the like)

So maybe best keep is as a little 1-bit dumper


TODO
	

"""


from wnd import gdi
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

DIVIDER= '%s\n' % ('#' * 57)
DIVIDER2= '#%s\n\n' % (':'*102)
# I'll take this one (with one minor change), pure poetry ;)
NOTE= '''# NOTE: This is a GENERATED file. Please do not make changes,
				# they will be overwritten next time it is generated.\n'''.replace('\t', '')

IMPORT_CURSOR= 'from wnd.gdi import CursorFromBytes\n'
IMPORT_ICON= 'from wnd.gdi import IconFromBytes\n'

#*************************************************************************

def IconToPyRes(name, doc, ico, bits, w, h):
	"""Converts an icon (...) to a string writable as python function
	name= name of the function
	doc= docstring (can not be ommitted)
	ico= the icon to dump
	bits= desired bit-depth of the icon
	w= width of the icon
	h= height of the icon
	"""
	ii= ico.GetIconInfo()
	MASK, COLOR= ico.GetDibBits(ii, bits)
	gdi.FlipDibBits(MASK)
	gdi.FlipDibBits(COLOR)
	res= ['\ndef %s():\n' % name,
				'\t\"\"\"%s\"\"\"\n\n' % doc, 
				'\tBITS, W, H= %s, %s, %s\n' % (bits, w, h),
				"\tMASK= %s\n" % repr(buffer(MASK)[:]),
				"\tCOLOR= %s\n" % repr(buffer(COLOR)[:]),
				'\treturn IconFromBytes(MASK, COLOR, BITS, W, H)\n\n'
			]
	return ''.join(res)


def CursorToPyRes(name, doc, cur, bits):
	"""Converts a cursor (...) to a string writable as python function
	name= name of the function
	doc= docstring (can not be ommitted)
	cur= the cursor to dump
	bits= desired bit-depth of the cursor
	"""
	ci= cur.GetCursorInfo()
	AND, XOR= cur.GetDibBits(ci, bits=bits)
	gdi.FlipDibBits(AND)
	gdi.FlipDibBits(XOR)
	res= ['\ndef %s():\n' % name,
				'\t\"\"\"%s\"\"\"\n\n' % doc, 
				'\tHOTX, HOTY= %s, %s\n' % (ci.xHotspot, ci.yHotspot),
				"\tAND= %s\n" % repr(buffer(AND)[:]),
				"\tXOR= %s\n" % repr(buffer(XOR)[:]),
				'\treturn CursorFromBytes(HOTX, HOTY, AND, XOR)\n\n'
			]
	return ''.join(res)
	



def PyResFile(path, data):
	"""Dumps a dict containing resources to file.

	data should be a dict of resources to dump

	key= 'cursors'
	value= list[
							(function-name, docstring, cursor-1, bitDepth),
							(function-name, docstring, cursor-n, bitDepth)
						]

	key= 'icons'
	value= list[
							(function-name, docstring, icon-1, bitDepth, width, height),
							(function-name, docstring, icon-n, bitDepth, width, height)
						]
	
	"""
		
	out= {'import':[], }
	
	if 'cursors' in data:
		out['cursors']= []
		if not IMPORT_CURSOR in out:
			out['import'].append(IMPORT_CURSOR)
		for i in data['cursors']:
			out['cursors'].append(CursorToPyRes(*i))
			
	if 'icons' in data:
		out['icons']= []
		if not IMPORT_ICON in out:
			out['import'].append(IMPORT_ICON)
		for i in data['icons']:
			out['icons'].append(IconToPyRes(*i))
		
	fp= open(path, 'w')
	try:
		if out['import']:
			fp.write('\n')
			fp.write(DIVIDER)
			fp.write(NOTE)
			fp.write(DIVIDER)
			fp.write('\n%s\n' % ''.join(out.pop('import')))
			fp.write(DIVIDER2)
			for resType, res in out.items():
				fp.write('## %s\n' % resType)
				fp.write(''.join(res))
	finally: fp.close()








