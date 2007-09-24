
"""some helper methods"""


# parses styles against a list of styles according to the framework rules
# all styles are considered being stings.
def ParseStylesSZ(validstyles, currentstyles, styles):		
		currentstyles= list(currentstyles)
		error= False 
		for i in styles:
			if i[0]=='-':
				if i[1: ] not in validstyles: raise "invalid style: %s" % i
				if i[1:] in currentstyles: currentstyles.remove(i[1:])
			elif i[0]=='~':
				if i[1: ] not in validstyles: raise "invalid style: %s" % i
				if i[1:] in currentstyles: currentstyles.remove(i[1:])
				else: currentstyles.append(i[1:])
			else:  
				if i not in validstyles: raise "invalid style: %s" % i
				if i not in currentstyles: currentstyles.append(i)
		return currentstyles
