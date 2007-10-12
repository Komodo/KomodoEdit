
import thread
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Handles(object):
	def __init__(self, initval=0):
				
		self.handles= [initval, ]
		self.lock= thread.allocate_lock()
		
	
	def GetHandles(self):
		#self.lock.acquire()
		handles= self.handles[:]
		#self.lock.release()
		return handles
	
	def Close(self, handle):
		#self.lock.acquire()
		try:
			self.handles.remove(handle)
		except: 
			self.lock.release()
			raise ValueError, "no handle found to close"
		#self.lock.release()
	
	def New(self):
		#self.lock.acquire()
		result= None
		tmp_h= self.GetHandles()
		s= len(self.handles)
		for n, i in enumerate(tmp_h):
			if n+1 < s:
				if self.handles[n+1] > i+1:
					self.handles.insert(n+1, i+1)
					result=  i+1
					break
						
			else:
				self.handles.append(i+1)
				result=  i+1
		
		#self.lock.release()
		return result		

