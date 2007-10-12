

from wnd.tools.dlgeditor.mnutemplate import *
from wnd.wintypes import *
import os



m= MnuTemplate()
m.BeginTemplate()
	
(	
m.Item(100, 'menubar-1', MFT_STRING, 0, MF_BEGIN),
		m.Item(102, 'item-1', MFT_STRING),
		m.Item(102, 'item-2', MFT_STRING),
		m.Item(102, 'item-3', MFT_STRING),
		m.Item(102, 'item-4', MFT_STRING),
		m.Item(102, '', MFT_SEPARATOR),
m.Item(102, 'item-5', MFT_STRING, 0, MF_END),


m.Item(100, 'menubar-2', MFT_STRING, 0, MF_BEGIN),
		m.Item(102, 'item-1', MFT_STRING, 0, MF_BEGIN),
				m.Item(102, 'item-2', MFT_STRING),
				m.Item(102, 'item-3', MFT_STRING),
				m.Item(102, 'item-4', MFT_STRING),
				m.Item(102, '', MFT_SEPARATOR),
				m.Item(102, 'item-1', MFT_STRING, 0, MF_BEGIN),
						m.Item(102, 'item-2', MFT_STRING),
						m.Item(102, 'item-3', MFT_STRING),
						m.Item(102, 'item-4', MFT_STRING),
				m.Item(102, 'item-5', MFT_STRING, 0, MF_END),
		m.Item(102, 'item-5', MFT_STRING, 0, MF_END),
		m.Item(102, 'item-2', MFT_STRING),
		m.Item(102, 'item-3', MFT_STRING),
		m.Item(102, 'item-4', MFT_STRING),
m.Item(102, 'item-5', MFT_STRING, 0, MF_END),


m.Item(100, 'menubar-3', MFT_STRING, 0, MF_BEGIN),
m.Item(102, 'cc', MFT_STRING, 0, MF_END),

m.Item(100, 'menubar-4', MFT_STRING, 0, MF_BEGIN),
m.Item(102, 'cc', MFT_STRING, 0, MF_END),

)
	
m.RunModal()




def ToHex(p):
	out= []
	for i in p:
		h= hex(ord(i))
		h= h[2:].rjust(2, '0')
		out.append('\\x%s' % h)
	return ''.join(out)


data= repr(m.ToString())
#data= ToHex(data)

	

fp= open('%s\\test2.mnu' % os.getcwd(), 'wb')
try: 
	fp.write(data)
finally: fp.close()



# save as binary data
fp= open('%s\\test.mnu' % os.getcwd(), 'wb')
try: fp.write(m.ToBuffer().raw)
finally: fp.close()


fp= open('%s\\test.mnu' % os.getcwd(), 'rb')
try: fp.read()
finally: fp.close()





