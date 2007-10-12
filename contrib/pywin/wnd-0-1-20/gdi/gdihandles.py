

from wnd.wintypes import *
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
OBJ_PEN         = 1
OBJ_BRUSH       = 2
OBJ_DC          = 3
OBJ_METADC      = 4
OBJ_PAL         = 5
OBJ_FONT        = 6
OBJ_BITMAP      = 7
OBJ_REGION      = 8
OBJ_METAFILE    = 9
OBJ_MEMDC       = 10
OBJ_EXTPEN      = 11
OBJ_ENHMETADC   = 12
OBJ_ENHMETAFILE = 13

OBJECTS={1 : 'pen',2 : 'brush',3 : 'dc',	4 : 'metadc',5 : 'pal',
			6 : 'font',7 : 'bitmap',8 : 'region',9 : 'metafile',10 : 'memdc',
			11 : 'extpen',	12 : 'enhmetadc',13 : 'enhmetafile'}


def GetOpen():
	# stored in 16-bit GDI heap
	# handle value must end in 2, 6, A or E
	# and must be less than 0x6000
	case_1=(OBJ_PEN,OBJ_BRUSH,OBJ_DC,OBJ_METADC,
					OBJ_PAL,OBJ_BITMAP,OBJ_MEMDC,
					OBJ_EXTPEN,OBJ_ENHMETADC)	# OBJ_COLORSPACE ??
	# special case
	# undocumented...
	case_2=(OBJ_METAFILE,OBJ_ENHMETAFILE)
	# stored in 32-bit GDI heap
	# handle value is a multiple of 4	
	case_3=(OBJ_FONT,OBJ_REGION)
	flag = False
	handles={}
	
	GETOBJTYPE = gdi32.GetObjectType
	for handle in xrange(0xFFFF):
		result = GETOBJTYPE(handle)
		if result:
			if result  in case_1:
				if handle & 2 and (handle % 2 == 0) and handle <= 0x6000:
					flag = True
			elif result in case_2:
				flag = True
			elif result in case_3: 
				if handle % 4 == 0:
					flag = True
			if flag:
				try: handles[OBJECTS[result]].append(handle)
				except: handles[OBJECTS[result]]=[handle, ]
				flag = False
	
	for i in OBJECTS.values():
		if i not in  handles:
			handles[i]=[]
	return handles



def Compare(oldHandles, newHandles):
	openHandles = {}
	for res_type, handles in newHandles.items():
		for handle in handles:
			try:
				oldHandles[res_type].index(handle)
			except:
				try:	openHandles[res_type].append(handle)
				except: openHandles[res_type]=[handle, ]
	
	for i in OBJECTS.values():
		if i not in openHandles:
			openHandles[i]=[]
	return openHandles


def Stat(oldHandles, newHandles):
	out={}
	for res_type, handles in oldHandles.items():
		out[res_type]=len(handles), len(newHandles[res_type])
	return out
			


#a=GetOpen()
#b=GetOpen()





