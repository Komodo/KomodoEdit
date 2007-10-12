import wnd
from wnd import gdi
from wnd.res import pyres
from ctypes import windll

comctl32= windll.comctl32
shell32= windll.shell32
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

path= '%s\\icons\\icons1.py' % wnd.WND_RESPATH
res= {"icons":
			[
				('ico_font_ansi', 
				'ansi font icon',
				gdi.IconFromFile(r'D:\download\res\icons\1.ico'), 
				1,
				32,
				32),
				('ico_font_truetype', 
				'truetype font icon',
				gdi.IconFromFile(r'D:\download\res\icons\2.ico'), 
				1,
				32,
				32),
				('ico_arrowhead_right', 
				'small arrow head',
				gdi.IconFromFile(r'D:\download\res\icons\76.ico'), 
				1,
				32,
				32),
				('ico_link_overlay', 
				'link overlay icon',
				gdi.IconFromFile(r'D:\download\res\icons\197.ico', 32, 32), 
				1,
				32,
				32),
											
			]
		}

pyres.PyResFile(path, res)
