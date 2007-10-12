
 
 # Common dialog errors

def ComdlgError(errno):
	CDERR={65535 : "DIALOGFAILURE",
						1 : "GENERALCODES",
						2 : "STRUCTSIZE",
						3 : "NOTEMPLATE",
						4 : "NOINSTANCE",
						5 : "LOADSTRFAILURE",
						6 : "FINDRESFAILURE",
						7 : "LOADRESFAILURE",
						8 : "LOCKRAISEFAILURE",
						9 : "MEMALLOCFAILURE",
						10 : "MEMLOCKFAILURE",
						11 : "NOHOOK",
						12 : "REGISTERMSGFAIL",
								
						20480 : "CHOOSECOLORCODES",
								
						8192 : "CHOOSEFONTCODES",     
						8193 : "NOFONTS",    
						8194 : "MAXLESSTHANMIN",  
						
						12288 : "FLENAMECODES", 
						12289 : "SUBCLASSFAILURE",
						12290 : "INVALIDFILENAME",
						12291 : "BUFFERTOOSMALL",

						16384 : "FINDREPLACECODES", 
						16385 : "BUFFERLENGTHZERO", 
						}
	try:
		return CDERR[errno]
	except:
		return "unknown error"