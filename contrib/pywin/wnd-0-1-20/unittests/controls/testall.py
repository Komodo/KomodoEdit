

"""Run all test suites in folder

Each module prefixed with 'test_' is loaded, checked if it defines a suites function.
If so its suites get executed by calling this function.
Due to the fact that controls are tested each module should define a variable
PARENT. 
Right befere the suites get executed this class assigns itsself to the variable, so
that the controls can be created as childwindows of thee.

"""

import wnd
from wnd.controls.listview import Listview
import os, imp, unittest
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
VERBOSITY= 2

PARENT= None	
PATH=  os.path.split(__file__)[0]
DIRUP=  os.path.split(PATH)[0]

PATH_STANDALONE= os.path.join(DIRUP, 'teststandalone.py')
PATH_HELPERS= os.path.join(DIRUP, 'testhelpers.py')

helpers= imp.load_source('helpers',PATH_HELPERS)


#**************************************************************
#**************************************************************

class Main:
	def __init__(self):
		self.mainframe= wnd.Window('unittest-all', 'unittest', None, None, None, None, 'sysmenu', 'sizebox')
		self.mainframe.onMSG= self.on_msg
		self.lv= Listview(self.mainframe, 0, 0, 0, 0, 'report', 'gridlines')
		self.lv.SetWindowPosAndSize(*self.mainframe.GetClientRect().ToSize())
		self.lv.Column('unittests output')
		
		# have to keep references to the controls here
		# still a bit weird with ctypes callbacks
		self.suites= []
		self.linebuffer= helpers.LineBuffer()
		self.mainframe.Run()


	def write(self, data):
		line=	self.linebuffer.write(data)
		if line != None:
			n= self.lv.Item(line)
			self.lv.EnshureVisible(n)
			self.lv.RedrawItems(n, n)

	def flush(self):
		for i in self.linebuffer.flush():
			if i != None:
				n= self.lv.Item(line)
				self.lv.EnshureVisible(n)
				self.RedrawItems(n, n)
				


	def on_msg(self, hwd, msg, wp, lp):
		if msg=="open": 
			self.RunTests()
		elif msg=="size": 
			self.lv.SetWindowPosAndSize(*lp)
			self.lv.SetColumnWidth(0, lp[2])
		elif msg=="close": pass
	
	def RunTests(self):	
		root, dirs, files = os.walk(os.getcwd()).next()
		for i in files:
			if i.startswith('test_'):
				name, ext= os.path.splitext(i)
				if ext.lower()=='.py':
					path=os.path.join(os.getcwd(), i)
					mod= imp.load_source(name, path)
					if hasattr(mod, 'suite'):
						mod.PARENT= self.mainframe
						suite=unittest.TestSuite(mod.suite())
						self.suites.append(suite)	#####
						unittest.TextTestRunner(stream=self, verbosity=VERBOSITY).run(suite)
						

		helpers.RemovePyc(PATH)

	def Run(self):
		self.mainframe.Run()
				
						
if __name__=='__main__':		
	main= Main()
	
	#main.Close()
	


