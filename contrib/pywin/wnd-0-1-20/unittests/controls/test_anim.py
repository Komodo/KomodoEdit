
import wnd
from wnd.controls.animation import Animation, AnimationFromHandle

import unittest, imp, os
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

PARENT= None	
PATH=  os.path.split(__file__)[0]
DIRUP=  os.path.split(PATH)[0]

PATH_STANDALONE= os.path.join(DIRUP, 'teststandalone.py')
PATH_HELPERS= os.path.join(DIRUP, 'testhelpers.py')

helpers= imp.load_source('helpers',PATH_HELPERS)

ANIM_PATH= os.path.join(PATH, 'sample.avi')

#*****************************************************************
# default tests
#*****************************************************************
class Tests(helpers.Helpers):
	
	def __init__(self):
		helpers.Helpers.__init__(self)
		
	
	def test_PlayAnim(self):
		self.ctrl.OpenAnim(ANIM_PATH)
		self.ctrl.PlayAnim()
		self.ctrl.StopAnim()
	
	

#*****************************************************************
# test classes
#*****************************************************************
	
##
class TestAnimation(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl= Animation(PARENT ,  0, 0, 40, 40)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl.Close()
		

##
class TestAnimationFromHandle(unittest.TestCase, Tests):
	def setUp(self):
		self.ctrl0= Animation(PARENT , 0, 0, 40, 40)
		self.ctrl= AnimationFromHandle(self.ctrl0.Hwnd)
		Tests.__init__(self)

	def tearDown(self):
		self.ctrl0.Close()
		self.ctrl.Close()
	
	
#****************************************************************
#***************************************************************
def suite():
	return (unittest.makeSuite(TestAnimation),
				unittest.makeSuite(TestAnimationFromHandle),
					)


	
						

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	

	
