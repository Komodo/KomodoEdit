

import os, array
os_join=os.path.join
os_split= os.path.split
os_splitext=os.path.splitext
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Helpers:
	"""Adds some helper methods, a message cache to a controls test suite"""


	def __init__(self):	
		self.cache= []
		self.ctrl.onMSG=self.onMSG
	
	def onMSG(self, *params):
		self.cache.append(params)
			
	# 
	def GetMsg(self, msg):
		"""Retrieves a message from the cache and returns  it.
			Returns the message if found, False otherwise"""
		flag= False
		for n, i in enumerate(self.cache):
			if i[1]==msg: 
				flag= True
				break
		if flag: 
			msg= self.cache[n]
			del self.cache[n]
			return msg
		return flag
	
	def PeekMsg(self, msg):
		"""peeks a message from the cache an removes it if found.
			Return True if the message was found, False otherwise"""
		flag= False
		for n, i in enumerate(self.cache):
			if i[1]==msg: flag= True
		if flag: del self.cache[n]
		return flag

	def ClearMsgCache(self):
		self.cache= []

#**************************************************************
#**************************************************************

class LineBuffer:
	"""Helper class. Interface between stream output
	and listview input."""
	def __init__(self):
		self.array = array.array
		self.buff =self.array('c')
		
	def flush(self):
		"""Flushes the buffer in an iterator loop, returning
		the contents of the buffer linewise.
		Currently not needed."""		
		out = []
		while True:
			try:
				n = self.buff.index('\n')
				p = self.buff[:n].tostring()
				del self.buff[:n+1]
				yield p
			except:
				n = self.buff.buffer_info( )[1]
				if n:
					p = self.buff[:n].tostring()
					del self.buff[:n]
					yield p
				else:
					break

	def write(self, chars):
		"""Writes chars to the buffer and returns the next line
		if there is a complete line, else returns None."""
		if len(chars)==1:
			self.buff.append(chars)
		else:
			p = self.array('c', chars)
			self.buff.extend(p)
				
		try:
			n = self.buff.index('\n')
			p = self.buff[:n].tostring()
			del self.buff[:n+1]
			return p
		except:
			return None


#***********************************************************
#***********************************************************

def RemovePyc(path):
	## removes all 'pyc' files in dir and sub
	root, dirs, files = os.walk(path).next()
	for i in files:
		if os_splitext(i)[1].lower()==".pyc":
			os.remove(os_join(root, i))
				