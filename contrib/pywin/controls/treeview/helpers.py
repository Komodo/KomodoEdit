
import os
os_normpath = os.path.normpath
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


# TODO
# rewrite to enable backslash escaping 

def splitpath(path):
	out= []
	x= len(path)
	n1= -1
	for n, i in enumerate(path):
		if i=='\\':
			if n + 1< x:
				if path[n+1] != '\\':
					out.append(path[n1+1:n])
					n1= n
	if n1 < x:
		out.append(path[n1+1:])
	return out



class ITERPATH(object):
	"""Helper class. Returns an iterator over a given path, returning
	the next part in path in turn.
	the hParent attribute is intended to store the parent handle of the node."""
	def __init__(self):
		pass
	
	def setpath(self, path):
		#self.path = os_normpath(path).split('\\')
		#self.path =path.split('\\')
		self.path= splitpath(path)
		self.hParent=0
		self.index = -1
		return self
		
	def __iter__(self): return self
	
	def next(self):
		self.index += 1
		try: return self.path[self.index]
		except:	raise StopIteration
	
