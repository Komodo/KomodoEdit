"""default template for OpenSaveFile dialog using dlgeditor"""

from wnd.consts import dlgs
from wnd.tools.dlgeditor.dlgeditor import DlgEditor
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

DLG_COLOR       =     10

COLOR_HUESCROLL  =     700  
COLOR_SATSCROLL  =     701
COLOR_LUMSCROLL   =    702
COLOR_HUE    =         703
COLOR_SAT     =        704
COLOR_LUM    =         705
COLOR_RED    =         706
COLOR_GREEN   =        707
COLOR_BLUE     =       708
COLOR_CURRENT    =     709
COLOR_RAINBOW    =     710
COLOR_SAVE      =      711
COLOR_ADD      =       712
COLOR_SOLID    =       713
COLOR_TUNE     =       714
COLOR_SCHEMES    =     715
COLOR_ELEMENT    =     716
COLOR_SAMPLES   =      717
COLOR_PALETTE   =      718
COLOR_MIX    =         719
COLOR_BOX1     =       720
COLOR_CUSTOM1    =     721

COLOR_HUEACCEL   =     723
COLOR_SATACCEL  =      724
COLOR_LUMACCEL   =     725
COLOR_REDACCEL    =    726
COLOR_GREENACCEL  =    727
COLOR_BLUEACCEL   =    728

COLOR_SOLID_LEFT  =    730
COLOR_SOLID_RIGHT  =   731

NUM_BASIC_COLORS    =  48
NUM_CUSTOM_COLORS   =  16

#*****************************************************************************
#*****************************************************************************
p= DlgEditor()

p.BeginTemplate(None, 'Color', 2, 0, 298, 184, ('Ms Sans Serif', 8, 0, 0), 'modalframe', 'popup', 'caption', 'contexthelp', '3dlook', 'sysmenu')

## color selectors
p.Item('static', 0xFFFFFFFF, '&Basic colors:', 4, 4, 140, 9, 'left', 'visible')
p.Item('static', COLOR_BOX1, '',  4, 14, 140, 86, 'simple', 'visible', 'tabstop', 'group')
	
p.Item('static', 0xFFFFFFFF, '&Custom colors:', 4, 106, 140, 9, 'left', 'visible')
p.Item('static', COLOR_CUSTOM1, '',  4, 116, 140, 28, 'simple', 'visible', 'tabstop', 'group')

p.Item('button', COLOR_MIX, '&Define Custom Colors >>', 4, 150, 140, 14, 'tabstop', 'visible', 'group')

## default buttons
p.Item('button', dlgs.IDOK, 'OK', 4, 166, 44, 14, 'tabstop', 'visible', 'group')
p.Item('button', dlgs.IDCANCEL, 'Cancel', 52, 166, 44, 14, 'tabstop', 'visible', 'group')
p.Item('button', dlgs.pshHelp, '&Help', 100, 166, 44, 14, 'tabstop', 'visible', 'group')
   

## custom colors ---------------------------------------------------------------------------------

## color selector
p.Item('static', COLOR_RAINBOW, '',  152, 4, 118, 116, 'simple', 'sunken', 'visible')
p.Item('static', COLOR_LUMSCROLL, '',  280, 4, 8, 116, 'simple', 'sunken', 'visible')
p.Item('static', COLOR_CURRENT, '',  152, 124, 40, 26, 'simple', 'sunken', 'visible')


## hidden group
p.Item('button', COLOR_SOLID, '&o', 300, 200, 4, 14, 'group', 'visible')
p.Item('static', COLOR_SOLID_LEFT, 'Color',  152, 4, 118, 116, 'right')
p.Item('static', COLOR_SOLID_RIGHT, '|S&olid',  172, 151, 20, 9, 'left')


## Hue/Sat/Lum editboxes
p.Item('static', COLOR_HUEACCEL, 'Hu&e:',  194, 126, 20, 9, 'right', 'visible')
p.Item('edit', COLOR_HUE, '',  216, 124, 18, 12, 'group', 'tabstop', 'visible', 'clientedge')

p.Item('static', COLOR_SATACCEL, '&Sat:',  194, 140, 20, 9, 'right', 'visible')
p.Item('edit', COLOR_SAT, '',  216, 138, 18, 12, 'group', 'tabstop', 'visible', 'clientedge')
	
p.Item('static', COLOR_LUMACCEL, '&Sat:',  194, 154, 20, 9, 'right', 'visible')
p.Item('edit', COLOR_LUM, '',  216, 152, 18, 12, 'group', 'tabstop', 'visible', 'clientedge') 

## RGB editboxes
p.Item('static', COLOR_REDACCEL, '&Red:',  243, 126, 24, 9, 'right', 'visible')
p.Item('edit',COLOR_RED, '',  269, 124, 18, 12, 'group', 'tabstop', 'visible', 'clientedge')  
p.Item('static', COLOR_GREENACCEL, '&Green:',  243, 140, 24, 9, 'right', 'visible')
p.Item('edit',COLOR_GREEN, '',  269, 138, 18, 12, 'group', 'tabstop', 'visible', 'clientedge')    

p.Item('static', COLOR_BLUEACCEL, 'Bl&ue:',  243, 154, 24, 9, 'right', 'visible')
p.Item('edit',COLOR_BLUE, '',  269, 152, 18, 12, 'group', 'tabstop', 'visible', 'clientedge')    
    

p.Item('button', COLOR_ADD, '&Add to Custom Colors',  152, 166, 142, 14, 'group', 'tabstop', 'visible')



#***********************************************************************************

if __name__=='__main__':
	from wnd.dlgs import choosecolor
	
	def callback(hwnd, msg, wp, lp):
			pass
			#if msg=="debug": print lp
					
	cc=choosecolor.ChooseColorFromTemplate(p.ToBuffer(), 'debug')
	cc[:]= (0xFF, 0xFF, 0xFF, 0xFF,
				0xFF, 0xFF, 0xFF, 0xFF,
				0xFF, 0xFF, 0xFF, 0xFF,
				0xFF, 0xFF, 0xFF, 0xFF)
	cc.onMSG= callback
	r= cc.Run(0, 'anycolor','hook', initcolor=0xFF)
	print r
	print cc[:]