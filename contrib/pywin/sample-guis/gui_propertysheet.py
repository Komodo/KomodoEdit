"""property sheet and witzard sample, bit lame currently

Quite civilized in comparison to the tons of aource code 
piling up behind the scenes"""

import gc
import wnd
from wnd import gdi
from wnd.wintypes import BYTE
from wnd.controls import dialog
from wnd.controls import propertysheet
from wnd.controls import button


#*********************************************************************
# dummy dialogs for property sheet and wizard
#*********************************************************************
## DialogFromTemplate is more flexible when it comes to font sizes

class dlg1(dialog.Dialog):
	def __init__(self, propsheet):
		self.propsheet= propsheet
		
		dialog.Dialog.__init__(self, 'dialog-1', 0, 0,propertysheet.PROP_MED_CXDLG, propertysheet.PROP_MED_CYDLG)

	def onINIT(self, hwnd, msg, wp, lp):
		self.bt= button.Button(self, 'Test', 20, 20, 60, 50)
		
		
class dlg2(dialog.Dialog):
	def __init__(self, propsheet):
		self.propsheet= propsheet
		
		dialog.Dialog.__init__(self, 'dialog-2', 0, 0, propertysheet.PROP_MED_CXDLG, propertysheet.PROP_MED_CYDLG)

	def onINIT(self, hwnd, msg, wp, lp):
		self.bt= button.Button(self, 'Test-1', 40, 20, 60, 50)
		self.bt2= button.Button(self, 'Test-2', 120, 20, 60, 50)
		self.bt.onMSG=self.on_bt

	def on_bt(self, hwnd, msg, wp, lp):
		if msg=='command':
			self.propsheet.QuerySiblings(1, 222)
			pass
	
	
	def onMSG(self, hwnd, msg, wp, lp):
		#print self.Hwnd
		pass
		

#*********************************************************************
# property sheet
#*********************************************************************

class _property_sheet(propertysheet.PropertySheet):
	def __init__(self):
		propertysheet.PropertySheet.__init__(self, 'foo', None, 'proptitle', 'hashelp',  startPage=0)
		
		self.d1= dlg1(self)
		self.d2= dlg2(self)

		self.Page(self.d1)
		self.Page(self.d2)

	def onMSG(self, hwnd, msg, wp, lp):
		if msg=='destroy':
			## have to run a full collect here
			gc.collect()
		

prop= _property_sheet()

#*********************************************************************
# wizard dialog
#*********************************************************************

class _wizard(propertysheet.PropertySheet):
	def __init__(self):
		
		## dummmy bitmap for the header background
		pat= (BYTE*1)(0xFF)
		self.bm= gdi.BitmapFromBytes(1, 1, 1, 1, pat)

				
		propertysheet.PropertySheet.__init__(self, 'my wizard', None, 'wizard97', startPage=0, bmpWatermark=self.bm)
		self.d1= dlg1(self)
		self.d2= dlg2(self)

				
		self.Page(self.d1, title='wizard page 1', 
										headerTitle='Header Title 1', 
										headerSubTitle='Some usefull text here as subtitle')
		self.Page(self.d2, title='wizard page 2', 
										headerTitle='Header Title 2', 
										headerSubTitle='Some usefull text here as subtitle on the second page')

	def onMSG(self, hwnd, msg, wp, lp):
		if msg=='setactive':
			if wp==self.d1.Hwnd:
				pass
				self.SetWizardButtons('next')
			
			elif wp==self.d2.Hwnd:
				pass
				self.SetFinishText('finish')
				
		elif msg=='destroy':
			## have to run a full collect here
			gc.collect()

wizard= _wizard()

#*********************************************************************
# main window
#*********************************************************************
class window(wnd.Window):
	def __init__(self):
		wnd.Window.__init__(self, 'propsheet sample', 'Prpertysheet Sample', None, None, None, None, 'sysmenu', 'sizebox', 'dialoglike')

		self.bt= button.Button(self, 'prop sheet...', 40, 20, 120, 50, 'tabstop')
		self.bt2= button.Button(self, 'wizard...', 40, 90, 120, 50, 'tabstop')
		self.bt.onMSG= self.bt2.onMSG= self.on_bt

			
	def on_bt(self, hwnd, msg, wp, lp):
		if msg=='command':
			if hwnd== self.bt.Hwnd:
				try:
					r=prop.Run()
				except: pass
			elif hwnd==self.bt2.Hwnd:
				try:
					r= wizard.Run()
				except: pass
				
			
	def onMSG(self, hwnd, msg, wp, lp):
		pass
		
	
w= window()
w.Run()

#wnd.Debug('leaks')


