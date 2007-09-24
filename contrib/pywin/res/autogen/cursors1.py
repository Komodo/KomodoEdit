
"""Autogen script"""


from wnd import gdi
from wnd.res import pyres
from ctypes import windll
comctl32= windll.comctl32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

path= r'D:\_scr_\py\Scr\wnd\res\cursors\cursors1.py'
res= {"cursors": 
			[
				('splitterwe', 
				'west-east || splitter from comctl32.dll', 
				gdi.CursorFromInstance(comctl32, "#107"), 
				1),
				('splitterns',
				'north-south || splitter from comctl32.dll',
				gdi.CursorFromInstance(comctl32, "#135"), 
				1), 
			]
		}

pyres.PyResFile(path, res)





