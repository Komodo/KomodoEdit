

import random
from wnd.controls.toolbar.header import (TBBUTTON, 
																			Structure,
																			sizeof,
																			addressof,
																			memmove,
																			create_string_buffer,
																			UINT,
																			INT,
																			c_char, )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
"""
Toolbars have the strange (as I feel) behaviour to save and restore their state
from registry. I do not feel to comfortable about this.

So here are some helpers to deal with this. Main purpose is to get all the data
required to restore a certain state of a Toolbar in hand.

The Snapshot class deals with storing a certain state of a Toolbar.
Intended use is to store a Toolbar in its full glory, all buttons available
to the user and save the state changes a user may have done.
Next time the Toolbar is created it is restored in three steps:
	1. add the string resource
	2. restore the Toolbar in its initial state
	3. adjust it according to user changes


Init the Snapshot class it with the array of TBBUTTON structures for the Toolbar.
Save all text strings to the class, using its AddString method.

AddString(i, text)
	takes two argumnets, the index of the string for the item as it appears 
	in the TBBUTOON structure (-1 is ignored) and the actual text. 
	The index has to be mapped from relative button order to relative Snapshot order. 

When the user cals the customisation dialog all that needs to be done
is calling the SetButtonOrder method to store the users choice.

SetButtonOrder(*idCommand)
	

The snapshot is now complete and the Write method returns all
the bytes required to restore it to a certain state.

Write()

If no customisation is done, fine anyway. Use the stored snapshot to create the
Toolbar next time you load it.


The ReadSnapshot function obviously extracts all required data from 
a string, returning an array of TBBUTTON structures + the string array +
the buton order array. 


"""	

SNAP_COOKIE= "TB"


class TBSNAPSHOT(Structure):
	_pack_=2
	_fields_= [("bytesInRes", UINT),			# overall size of the resource
						("cbSize", UINT),					# size of this structure
						("type", c_char*2),				# just a cookie
						("version", UINT),				# version (not used)
						("cbText", UINT),					# sizeof of the char array (NULL-terminared
																		#	 ...strings, terminated with two NULL
																		#	 ...bytes)
						("cbButtons", UINT),			# sizeof of the TBBUTTON array
						("cbUserButtons", UINT)]	# sizeof of user defined buttons
	def __init__(self): self.cbSize= sizeof(self)
	# 	emidiately following the cbOrderArray member is the the text array
	# array of TBBUTTON structures, next , next the order array.



class Snapshot(object):
	def __init__(self, buttons, text=None, userButtons=None):
		self.buttons= buttons
		if text:	self.textBuffer= text
		else: self.textBuffer= [None, ]*len(self.buttons)
		if userButtons: self.userButtons= userButtons
		else: self.userButtons= None
		self.tbSize= None

	def AddText(self, i, text):
		if i > -1: 
				self.textBuffer[i]= text

	
	def SetUserButtons(self, buttons):
		# simple test if something has changed
		if buffer(self.buttons)[:] != buffer(buttons)[:]:	
			self.userButtons= buttons
		
	def Write(self):
		if isinstance(self.textBuffer, list):
			text= [i for i in self.textBuffer  if i != None]
			text= '%s\x00\x00' % '\x00'.join(text)
		else:
			text= self.textBuffer
					
		sn= TBSNAPSHOT()
		sn.type= SNAP_COOKIE
		sn.version= 0
		if self.tbSize:
			sn.cx, sn.cy= self.tbSize
		
		sn.cbText= len(text)
		sn.cbButtons= len(self.buttons)* sizeof(TBBUTTON)
		if self.userButtons:
			sn.cbUserButtons= sizeof(self.userButtons)
		sn.bytesInRes= sn.cbSize+sn.cbText+sn.cbButtons+sn.cbUserButtons
		

		p= buffer(sn)[:]
		p+=buffer(text)[:]
		if self.buttons:
			p+=buffer(self.buttons)[:]
		if self.userButtons:
			p+=buffer(self.userButtons)[:]
		
		
		return p
		
		


def ReadSnapshot(data):
	error = True
	data= create_string_buffer(data)
	addr= addressof(data)
	
	nBytes= UINT.from_address(addr)
	if nBytes.value== sizeof(data)-1:
		n= 4
		cb= UINT.from_address(addr+n)
		if cb.value== sizeof(TBSNAPSHOT):
			n+= 4
			type= (c_char*2).from_address(addr+n)
			if type.value== SNAP_COOKIE:
				
				n += 2
				# not used
				version= UINT.from_address(addr+n)
				n += 4
				
				cbText= UINT.from_address(addr+n)
				n += 4
				cbButtons= UINT.from_address(addr+n)
				if not cbButtons.value % sizeof(TBBUTTON):
					n += 4
					cbUserButtons= UINT.from_address(addr+n)
					if not cbUserButtons.value % sizeof(TBBUTTON):
						n += 4
					
						# access data section
						#
						text= data[n:n+cbText.value]
						n+= cbText.value
												
						arrBt= (TBBUTTON*(cbButtons.value / sizeof(TBBUTTON)))()
						memmove(addressof(arrBt), addr+n, cbButtons.value)
						n+= cbButtons.value

						if cbUserButtons.value:
							arrUBt= (TBBUTTON*(cbUserButtons.value / sizeof(TBBUTTON)))()
							memmove(addressof(arrUBt), addr+n, cbUserButtons.value)
						else:
							arrUBt=None
						#n+= cbUserButtons.value
						
						
						error= False
						
		
					else:
						error= "invalid user button array"
				else:
					error= "invalid button array"
			else:
				error= "invalid cookie"
		else:
			error= "invalid snapshot header" 
	else:
		error= "sizeof missmatch"
	
	
	
	if error: raise ValueError("invalid data: %s" % error)
	return arrBt, text, arrUBt
				
		
	
	

def test():
	
	arr= (TBBUTTON*4)(
		TBBUTTON(1,2,3, 0, 0, -1),
		TBBUTTON(4,5,6, 0, 0, 0),
		TBBUTTON(7,8,9, 0, 0, 1),
		TBBUTTON(7,8,9, 0, 0, 1),
		)

	
	arrUser= (TBBUTTON*2)(
		TBBUTTON(1,2,3, 0, 0, -1),
		TBBUTTON(4,5,6, 0, 0, 0),
		)
	
	s= Snapshot(arr)		
	s.AddText(0, 'foo')
	s.AddText(1, 'aaa')
	s.SetUserButtons(arrUser)
	r= s.Write()
	#print repr(r)

	ReadSnapshot(r)

#test()