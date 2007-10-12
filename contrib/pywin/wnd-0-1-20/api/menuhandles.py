

from wnd.wintypes import *
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


def GetOpen():
	ISMENU= user32.IsMenu
	out=[]
	for handle in xrange(0xFFFF):
		if ISMENU(handle): out.append(handle)
	return out
		
	
def Compare(oldHandles, newHandles):
	out=[]
	for i in newHandles:
		if i not in oldHandles: out.append(i)
	return out
		

	

#a=GetOpen()
#b=GetOpen()






