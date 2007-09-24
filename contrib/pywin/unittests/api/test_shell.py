

from wnd.api import shell

from ctypes.com.mallocspy import MallocSpy 
m= MallocSpy()

import unittest, imp, os, sys
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

PARENT= None	
PATH=  os.path.split(__file__)[0]
DIRUP=  os.path.split(PATH)[0]

PATH_STANDALONE= os.path.join(DIRUP, 'teststandalone.py')
PATH_HELPERS= os.path.join(DIRUP, 'testhelpers.py')

helpers= imp.load_source('helpers',PATH_HELPERS)

#*****************************************************************
# 
#*******************************************************************

class TestPidls(unittest.TestCase,):
	def setUp(self):
		self.sh= shell.ShellNamespace()
			
	def tearDown(self):
		self.sh.Close()
		
	
	def test_PidlEnum(self):
		pIdl= self.sh.ParseDisplayName(sys.prefix)
		self.failIf(not pIdl)
		self.failUnless(shell.Malloc.GetSize(pIdl))
		
		## dono what to test here for
		for i in shell.PidlEnum(pIdl):
			pass

		shell.PidlFree(pIdl)
		self.failUnless(shell.Malloc.GetSize(pIdl)==	 0)


	
	def test_PidlGetParent(self):
						
		pIdl= self.sh.ParseDisplayName(sys.prefix)
		self.failIf(not pIdl)
		self.failUnless(shell.Malloc.GetSize(pIdl))
				
		pIdl2= shell.PidlCopy(pIdl)
		self.failIf(not pIdl2)

		shell.PidlGetParent(pIdl)
		
		pIdlChild= shell.PidlSplit(pIdl2)
		self.failIf(not pIdlChild)

		pIdl3= shell.PidlJoin(pIdl, pIdlChild)
		self.failIf(not pIdl3)

		self.failUnless(self.sh.GetParseName(pIdl).lower()==	\
									os.path.split(sys.prefix)[0].lower())	
		self.failUnless(self.sh.GetParseName(pIdl3).lower()==	\
									sys.prefix.lower())	
		
		shell.PidlFree(pIdl)
		shell.PidlFree(pIdl2)
		shell.PidlFree(pIdl3)
		shell.PidlFree(pIdlChild)
		self.failUnless(shell.Malloc.GetSize(pIdl)==	 \
									shell.Malloc.GetSize(pIdl2)==	 \
									shell.Malloc.GetSize(pIdlChild)==	 \
									0)


	
	def test_PidlSplit(self):
				
		pIdl= self.sh.ParseDisplayName(sys.prefix)
		self.failIf(not pIdl)
		self.failUnless(shell.Malloc.GetSize(pIdl))
		
		pIdlChild= shell.PidlSplit(pIdl)
		self.failIf(not pIdlChild)
		
		pIdl2= shell.PidlJoin(pIdl, pIdlChild)
		self.failIf(not pIdl2)
		
		self.failUnless(self.sh.GetParseName(pIdl).lower()==	\
									os.path.split(sys.prefix)[0].lower())	
		
		
		self.failUnless(self.sh.GetParseName(pIdl2).lower()==	\
									sys.prefix.lower())	
		
		shell.PidlFree(pIdl)
		shell.PidlFree(pIdl2)
		shell.PidlFree(pIdlChild)
		self.failUnless(shell.Malloc.GetSize(pIdl)==	 \
									shell.Malloc.GetSize(pIdl2)==	 \
									shell.Malloc.GetSize(pIdlChild)==	 \
									0)


	
	def test_PidlFree(self):
		
		pIdl= self.sh.ParseDisplayName(sys.prefix)
		self.failIf(not pIdl)
		self.failUnless(shell.Malloc.GetSize(pIdl))
		
		shell.PidlFree(pIdl)
		self.failIf(shell.Malloc.GetSize(pIdl))

		
	def test_PidlCopy(self):
				
		pIdl= self.sh.ParseDisplayName(sys.prefix)
		pIdl2= shell.PidlCopy(pIdl)
		
		self.failUnless(self.sh.GetParseName(pIdl).lower()==	\
									self.sh.GetParseName(pIdl2).lower()==	\
									sys.prefix.lower())
		
		self.failIf(not pIdl or not pIdl2)
		self.failUnless(buffer(pIdl[0])[:]==buffer(pIdl2[0])[:])
		
		shell.PidlFree(pIdl)
		shell.PidlFree(pIdl2)
		self.failUnless(shell.Malloc.GetSize(pIdl)==	 \
									shell.Malloc.GetSize(pIdl2)==	\
									0)
		
		
				


#************************************************************************
def suite():
	return (unittest.makeSuite(TestPidls),
				)


	
						
PARENT= None			

if __name__=='__main__':
	mod= imp.load_source('foo', PATH_STANDALONE)
	PARENT= mod.Main()
	PARENT.RunTest(suite)
	helpers.RemovePyc(PATH)
	