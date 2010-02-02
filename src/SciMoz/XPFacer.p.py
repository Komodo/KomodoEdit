# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import string, os, sys

# Some MH hacks to avoid duplicate files.
# "Face.py" and 'Scintilla.iface' are in the scintilla directory
# As this is also under ActiveState source control, preventing
# duplicate files ensures that SciMoz is definately in synch with
# the relevant scintilla!

scintillaFilesPath = ""

try:
    import Face
except ImportError:
    scintillaFilesPath = os.path.abspath( 
                os.path.join( 
                    os.path.split(sys.argv[0])[0], "../scintilla/include"
                ))
    if not os.path.isfile(os.path.join(scintillaFilesPath,"Scintilla.iface")):
        print "WARNING: Excepting to find 'Face.py' and 'Scintilla.iface' in path"
        print scintillaFilesPath, ", but I can't.  I'm probably gunna fail real-soon-now!"
    sys.path.insert(0, scintillaFilesPath)
    import Face

unwantedValues = [ "SCI_START", "SCI_OPTIONAL_START", "SCI_LEXER_START"]

# XXX IDL_string_type should be an argument to this script, but
# I don't expect we will be changing it once things work right
# XXX Currently only wstring works 100% correctly
#
# it can be:
#   string        - pre 2.5 char *
#   wstring       - unicode PRUnichar *
#   AString       - unicode class
#   AUTF8String   - utf-8 class
#
# xpconnect handles translations automaticly for AUTF8String
# the difference between using AUTF8String is whether we let the
# XPCOM layer handle translations for us or we do it manually, but
# either way, translation will occure.
C_out_string_types = ["char **","nsACString& ","PRUnichar **","nsAString& "]
IDL_string_type = "AString"

# IDL uses string
if IDL_string_type == "string":
    IDL_in_string =     ["in ", 	"string",	"const char *"]
    IDL_out_string =    ["out ",	"string",	"char **"]
# IDL uses wstring
elif IDL_string_type == "wstring":
    IDL_in_string =     ["in ", 	"wstring",	"const PRUnichar *"]
    IDL_out_string =    ["out ",	"wstring",	"PRUnichar **"]
# IDL uses AString (wchar_t class)
elif IDL_string_type == "AString":
    IDL_in_string =     ["in ", 	"AString",	"const nsAString& "]
    IDL_out_string =    ["out ",	"AString",	"nsAString& "]
# IDL uses AUTF8String
elif IDL_string_type == "AUTF8String":
    IDL_in_string =     ["in ", 	"AUTF8String",	"const nsACString& "]
    IDL_out_string =    ["out ",	"AUTF8String",	"nsACString& "]

typeInfo = {
	# iface		direction	idl		cxx
	"string": 		IDL_in_string,
	"stringresult": 	IDL_out_string,
	"int": 			["in ", 	"long",	"PRInt32 "], 
# #if ARCHITECTURE == 'x86_64'
	"ptr": 			["in ", 	"long long",	"PRInt64 "],
# #else
	"ptr": 			["in ", 	"long",	"PRInt32 "],
# #endif
	"bool": 		["in ", 	"boolean",	"PRBool "], 
	"position": 		["in ", 	"long",	"PRInt32 "], 
	"colour": 		["in ", 	"long",	"PRInt32 "], 
	"keymod": 		["in ",		"long",	"PRInt32 "], 
	"void": 		["in ", 	"void",	"void"],
	
	# special stuff to provide translations used later
	"utf8string":           ["in ", 	"AUTF8String",	"const nsACString& "],
	"utf8stringresult":     ["out ",	"AUTF8String",	"nsACString& "],
	"wstring":              ["in ", 	"wstring",	"const PRUnichar *"],
	"wstringresult":        ["out ",	"wstring",	"PRUnichar **"],

	# functions using these types have been discarded in the
	# discardedFeatures variable below
	"cells": 		["in ", 	"string",	"const char *"], 
	"textrange": 		["inout ", 	"string",	"char **"], 
	"findtext": 		["inout ", 	"string",	"char **"],
	
	# these are not being used by scintilla.iface
	#"countedstring": 	["out ",	"string",	"char **"], 
	#"point": 		["inout ", 	"string",	"char **"], 
	#"charrange": 		["inout ", 	"string",	"char **"], 
	#"rectangle": 		["inout ", 	"string",	"char **"],
	
	"": 			["", 		"",		""],
}

safeAttributes = [ "long", "boolean", "long long" ]

# These Scintilla features are either not needed for SciMoz or are implemented by hand
discardedFeatures = [
	# Not needed
	"exGetSel", "exSetSel", "exLineFromChar", "null",
	"findText", "findTextEx", #"searchAnchor", "searchNext", "searchPrev",
	"getSel", "lineIndex", "selectionType", "setMargins", "command", "notify",  
	# Implemented by hand
	# note: items returning strings or complex types are easier to
	# manage when we implement them by hand.
	"getStyledText", "getCurLine", "assignCmdKey", "clearCmdKey",
	"charFromPos", "posFromChar", "lineFromChar", "getMargins", "getRect", 
	"getTextRange", "getText", "setText",
	"getSelText", "getLine", "charPosAtPosition",
	"replaceTarget", "replaceTargetRE", "searchInTarget",
	"getModEventMask", "setModEventMask",
	# The focus attribute was renamed to isFocused to avoid collision with
	# the html focus() method.
	"getFocus", "setFocus",
]

# NOTE: Only need either the "get" or "set" version - not both (tho it doesnt hurt :-)
liteFeatures = string.split("""gotoLine gotoPos getSelectionStart getSelectionEnd 
                                     getReadOnly getLength getCurrentPos insertText addText
                                     selectAll hideSelection replaceSel newLine deleteBack
                                     styleSetFore startStyling setStyling
                                     getAnchor getCurrentPos
                                     setAnchor setCurrentPos
                                     markerNext markerAdd
                                     setLineScroll getLineScroll
                                     setXOffset getXOffset
                                     setScrollWidth getScrollWidth
                                     getIsFocused setIsFocused
                                     """)

def knownType(ifaceType):
	return ifaceType in typeInfo.keys()
	
def ioio(ifaceType):
	if knownType(ifaceType):
		return typeInfo[ifaceType][0]
	else:
		return ""
		
def idlType(ifaceType):
	if knownType(ifaceType):
		return typeInfo[ifaceType][1]
	else:
		return ifaceType

def cxxType(ifaceType):
	if knownType(ifaceType):
		return typeInfo[ifaceType][2]
	else:
		return ""
		
def DEFINEName(ifaceName):	
	featureDefineName = string.upper(ifaceName)
	if "_" not in featureDefineName:
		featureDefineName = "SCI_" + featureDefineName
	if featureDefineName == "SCI_GETLINE": # Need to use length-safe version
		featureDefineName = "EM_GETLINE"
	return featureDefineName
	
def withoutUnderbit(name):
	if "_" in name:
		return name[string.find(name, "_")+1:]
	else:
		return name
		
def idlName(ifaceName):
	return interCaps(withoutUnderbit(ifaceName))

def needsCast(argType):
	return argType in ["string", "cells"]
	
def castIfNeeded(name, sourceType, destType):
	if sourceType == "_force_cast_":
		return "reinterpret_cast<" + destType + ">(" + name + ")"
	elif cxxType(sourceType) == "const char *":
		return "reinterpret_cast<" + destType + ">(" + name + ")"
	elif cxxType(sourceType) == "char **":
		return "reinterpret_cast<" + destType + ">(" + name + ")"
	elif cxxType(sourceType) == "const PRUnichar *":
		return "reinterpret_cast<" + destType + ">(NS_ConvertUTF16toUTF8(" + name + ").get())"
	elif cxxType(sourceType) == "const nsAString& ":
		return "reinterpret_cast<" + destType + ">((const char *)ToNewUTF8String(" + name + "))"
	elif cxxType(sourceType) == "const nsACString& ":
		return "reinterpret_cast<" + destType + ">((const char *)ToNewCString(" + name + "))"
	else:
		return name

def interCaps(name, upper=0):
	if upper:
		return string.upper(name[0]) + name[1:]
	else:
		return string.lower(name[0]) + name[1:]
			
def attributeName(name):
	if string.find(name, "Get") != -1:
		x = string.find(name, "Get")
		return idlName(name[:x] + name[x+3:])
	elif string.find(name, "Set") != -1:
		x = string.find(name, "Set")
		return idlName(name[:x] + name[x+3:])
	else:
		return idlName(name)
		
def setterVersion(name):
	if string.find(name, "Get") != -1:
		x = string.find(name, "Get")
		return name[:x] + "Set" + name[x+3:]
	elif string.find(name, "get") != -1:
		x = string.find(name, "get")
		return name[:x] + "set" + name[x+3:]
	else:
		return "set" + name
	
def getterVersion(name):
	if string.find(name, "Set") != -1:
		x = string.find(name, "Set")
		return name[:x] + "Get" + name[x+3:]
	elif string.find(name, "set") != -1:
		x = string.find(name, "set")
		return name[:x] + "get" + name[x+3:]
	else:
		return "get" + name
	
def idlis(f):
	funcs = 0
	usedNames = []
	attributes = []
	for name in f.order:
		v = f.features[name]
		if v["FeatureType"] == "get" and idlType(v["ReturnType"]) in safeAttributes and \
			v["Param1Name"] == "" and v["Param2Name"] == "":
			attributes.append(name)
	idldefs = idldefs_lite = ""
	impls = ""
	for name in f.order:
		v = f.features[name]
		nameIDL = idlName(name)
		if v["FeatureType"] in ["fun", "get", "set"] and \
			nameIDL not in usedNames and \
			nameIDL not in discardedFeatures:
			usedNames.append(nameIDL)
			funcs = funcs+1
			funcDef = ""
			retType = v["ReturnType"]
			p1Type = v["Param1Type"]
			p1Name = v["Param1Name"]
			p2Type = v["Param2Type"]
			p2Name = v["Param2Name"]
			allTypesKnown = knownType(retType) and knownType(p1Type) and knownType(p2Type)
			if not allTypesKnown:
				funcDef = funcDef + "//"
			funcName = nameIDL
			cxxName = interCaps(nameIDL,1)
				
			wouldBeFuncDef = ""
			if v["FeatureType"] == "get" and name in attributes:
				#if set version then no readonly
				if setterVersion(name) not in f.order:
					funcDef = funcDef + "readonly "
				funcDef = funcDef + "attribute " + idlType(retType) + " " + attributeName(name) + ";"
				cxxName = "Get" + interCaps(attributeName(name), 1)
			elif v["FeatureType"] == "set" and getterVersion(name) in attributes:
				cxxName = "Set" + interCaps(attributeName(name), 1)
				argUsed = p1Type
				if not argUsed:
					argUsed = p2Type
				wouldBeFuncDef = funcDef + "attribute " + idlType(argUsed) + " " + attributeName(name) + ";"
			else:
				funcDef = funcDef + idlType(v["ReturnType"])
				funcDef = funcDef + " " + funcName + "("
				if p1Name:
					funcDef = funcDef + ioio(p1Type)
					funcDef = funcDef + idlType(p1Type)
					if funcDef[-1] not in "*&":
						funcDef = funcDef + " "
					funcDef = funcDef + idlName(p1Name)
				if p2Name:
					if p1Name:
						funcDef = funcDef + ", "
					funcDef = funcDef + ioio(p2Type)
					funcDef = funcDef + idlType(p2Type)
					if funcDef[-1] not in "*&":
						funcDef = funcDef + " "
					funcDef = funcDef + idlName(p2Name)
				funcDef = funcDef + ");"
			if funcDef:
				newdef = "\t" + funcDef + "\n"
				if nameIDL not in liteFeatures:
					idldefs = idldefs + newdef
				else:
					idldefs_lite = idldefs_lite + newdef

			if wouldBeFuncDef:	# Setter with getter so no extra line in idl but want definition in implementation
				funcImpl = "/* " + wouldBeFuncDef + " */\n"
			else:
				funcImpl = "/* " + funcDef + " */\n"
			if allTypesKnown:
				funcImpl = funcImpl + "NS_IMETHODIMP SciMoz::"
				funcImpl = funcImpl + cxxName
				funcImpl = funcImpl + "("
				if p1Name:
					funcImpl = funcImpl + cxxType(p1Type) + p1Name
				if p2Name:
					if p1Name:
						funcImpl = funcImpl + ", "
					funcImpl = funcImpl + cxxType(p2Type) + p2Name
				if retType != "void":
					if p2Name or p1Name:
						funcImpl = funcImpl + ", "
					funcImpl = funcImpl + cxxType(retType) + " *_retval"
				funcImpl = funcImpl + ") {\n"
				funcImpl = funcImpl + "#ifdef SCIMOZ_DEBUG\n"
				funcImpl = funcImpl + '\tprintf("SciMoz::' + cxxName + '\\n");\n'
				funcImpl = funcImpl + "#endif\n"
				funcImpl = funcImpl + '\tSCIMOZ_CHECK_VALID("' + cxxName + '")'
				stringresult = 0
				structType = ""
				if (cxxType(p1Type) in C_out_string_types) or \
					(cxxType(p2Type) in C_out_string_types):
					if (cxxType(p1Type) in C_out_string_types):
					    stringresult = C_out_string_types.index(cxxType(p1Type)) + 1
					    pName = p1Name
					else:
					    stringresult = C_out_string_types.index(cxxType(p2Type)) + 1
					    pName = p2Name
					# Due to excessive stack usage, use a static buffer and a lock for thread-safety.
					funcImpl += """\
	static char _buffer[32 * 1024];
/*#ifdef NS_DEBUG
	static PRThread *myThread = nsnull;
	if (myThread == nsnull)
		myThread = PR_GetCurrentThread();
	// If this fires, caller should be using a proxy!  Scintilla is not free-threaded!
	NS_PRECONDITION(PR_GetCurrentThread()==myThread, "buffer (and Scintilla!) is not thread-safe!!!!");
#endif */ // NS_DEBUG
	_buffer[32 * 1024-1] = '\\0';\
					"""
					# Placing the buffer size at the start of the buffer is only used by GetLine
					# but it is harmless for the others.
					funcImpl = funcImpl + "\tshort _buflen = static_cast<short>(sizeof(_buffer)-1);\n"
					funcImpl = funcImpl + "\tmemcpy(_buffer, &_buflen, sizeof(_buflen));\n"
				if (p1Type == "point") or (p2Type == "point"):
					structType = "point"
					if (p1Type == "point"):
						pName = p1Name
					else:
						pName = p2Name
					pTempName = "&_pt"
					funcImpl = funcImpl + "\tPOINT _pt={0,0};\n"
					funcImpl = funcImpl + "\tif (*" + pName + ")\n"
					funcImpl = funcImpl + '\t\tsscanf(*'
					funcImpl = funcImpl + pName
					funcImpl = funcImpl + ',"%d %d", &_pt.x, &_pt.y);\n'
				if (p1Type == "charrange") or (p2Type == "charrange"):
					structType = "charrange"
					if (p1Type == "charrange"):
						pName = p1Name
					else:
						pName = p2Name
					pTempName = "&_cr"
					funcImpl = funcImpl + "\tCHARRANGE _cr={0,0};\n"
					funcImpl = funcImpl + "\tif (*" + pName + ")\n"
					funcImpl = funcImpl + '\t\tsscanf(*'
					funcImpl = funcImpl + pName
					funcImpl = funcImpl + ',"%ld %ld", &_cr.cpMin, &_cr.cpMax);\n'
				if (p1Type == "textrange") or (p2Type == "textrange"):
					structType = "textrange"
					if (p1Type == "textrange"):
						pName = p1Name
					else:
						pName = p2Name
					pTempName = "&_tr"
					funcImpl = funcImpl + "\tTEXTRANGE _tr={{0,0},0};\n"
					funcImpl = funcImpl + "\tif (*" + pName + ")\n"
					funcImpl = funcImpl + '\t\tsscanf(*'
					funcImpl = funcImpl + pName
					funcImpl = funcImpl + ',"%ld %ld", &_tr.chrg.cpMin, &_tr.chrg.cpMax);\n'
					funcImpl = funcImpl + '\t_tr.lpstrText = _buffer;\n'
				if (p1Type == "findtext") or (p2Type == "findtext"):
					structType = "findtext"
					if (p1Type == "findtext"):
						pName = p1Name
					else:
						pName = p2Name
					pTempName = "&_ft"
					funcImpl = funcImpl + "\tFINDTEXTEX _ft;\n"
					funcImpl = funcImpl + "\t_ft.chrg.cpMin = 0;\n"
					funcImpl = funcImpl + "\t_ft.chrg.cpMax = 0;\n"
					funcImpl = funcImpl + "\t_ft.lpstrText = 0;\n"
					funcImpl = funcImpl + "\t_ft.chrgText.cpMin = 0;\n"
					funcImpl = funcImpl + "\t_ft.chrgText.cpMax = 0;\n"
					funcImpl = funcImpl + "\tif (*" + pName + ") {\n"
					funcImpl = funcImpl + '\t\tsscanf(*'
					funcImpl = funcImpl + pName
					funcImpl = funcImpl + ',"%ld %ld", &_ft.chrg.cpMin, &_ft.chrg.cpMax);\n'
					funcImpl = funcImpl + "\t\tconst char *_cpText=strchr(*" + pName + ",' ');\n"
					funcImpl = funcImpl + "\t\tconst char *_cpText2=_cpText?strchr(_cpText+1,' '):0;\n"
					funcImpl = funcImpl + "\t\t_ft.lpstrText = _cpText2?(char *)_cpText2+1:0;\n"
					funcImpl = funcImpl + '\t};\n'
				if (p1Type == "rectangle") or (p2Type == "rectangle"):
					structType = "rectangle"
					if (p1Type == "rectangle"):
						pName = p1Name
					else:
						pName = p2Name
					pTempName = "&_rc"
					funcImpl = funcImpl + "\tRECT _rc={0,0,0,0};\n"
					funcImpl = funcImpl + "\tif (*" + pName + ")\n"
					funcImpl = funcImpl + '\t\tsscanf(*'
					funcImpl = funcImpl + pName
					funcImpl = funcImpl + ',"%ld %ld %ld %ld", &_rc.left, &_rc.top, &_rc.right, &_rc.bottom);\n'
				funcImpl = funcImpl + "\t"
				if retType != "void":
					funcImpl = funcImpl + "*_retval = "
				funcImpl = funcImpl + "SendEditor("
				funcImpl = funcImpl + DEFINEName(name)
				funcImpl = funcImpl + ", "
				if p1Name:
					if cxxType(p1Type) == "char **":
						if structType:
							funcImpl = funcImpl + castIfNeeded(pTempName, p1Type, "unsigned long")
						else:
							funcImpl = funcImpl + castIfNeeded(p1Name, p1Type, "unsigned long")
					else:
						funcImpl = funcImpl + castIfNeeded(p1Name, p1Type, "unsigned long")
				else:
					funcImpl = funcImpl + "0"
				funcImpl = funcImpl + ", "
				if p2Name:
					if cxxType(p2Type) == "char **" or \
						cxxType(p2Type) == "nsACString& " or \
						cxxType(p2Type) == "PRUnichar **" or \
						cxxType(p2Type) == "nsAString& ":
						if structType:
							funcImpl = funcImpl + castIfNeeded(pTempName, p2Type, "long")
						else:
							funcImpl = funcImpl + castIfNeeded("_buffer", "_force_cast_", "long")
					else:
						funcImpl = funcImpl + castIfNeeded(p2Name, p2Type, "long")
				else:
					funcImpl = funcImpl + "0"
				funcImpl = funcImpl + ");\n"
				if stringresult > 0:
					if structType and (structType != "textrange"):
						funcImpl = funcImpl + "\tsprintf(_buffer,"
						if structType == "point":
							funcImpl = funcImpl + '"%d %d", _pt.x, _pt.y);\n'
						elif structType == "charrange":
							funcImpl = funcImpl + '"%ld %ld", _cr.cpMin, _cr.cpMax);\n'
						elif structType == "rectangle":
							funcImpl = funcImpl + '"%ld %ld %ld %ld", _rc.left, _rc.top, _rc.right, _rc.bottom);\n'
						else:	# Find text ex
							funcImpl = funcImpl + '"%ld %ld", _ft.chrgText.cpMin, _ft.chrgText.cpMax);\n'
					if stringresult == 1: # char **
						funcImpl = funcImpl + "\t*" + pName + \
							" = reinterpret_cast<char*>(nsAllocator::Clone(_buffer, strlen(_buffer)+1));\n"
					elif stringresult == 2: # nsACString
						funcImpl = funcImpl + "\t" + pName + ".Assign(_buffer, strlen(_buffer)+1);\n"
					elif stringresult == 3: # PRUnichar *
						funcImpl = funcImpl + "\t*" + pName + \
							" =  ToNewUnicode(NS_ConvertUTF8toUTF16(_buffer));\n"
					elif stringresult == 4: # nsAString *
						funcImpl = funcImpl + "\t" + pName + ".Assign(NS_ConvertUTF8toUTF16(_buffer));\n"
					funcImpl = funcImpl + "\treturn (*_buffer) ? NS_OK : NS_ERROR_OUT_OF_MEMORY;\n"
				else:
					funcImpl = funcImpl + "\treturn NS_OK;\n"
				funcImpl = funcImpl + "}\n"
				impls = impls + funcImpl + "\n"
		elif v["FeatureType"] == "val":
			if name not in unwantedValues:
				constDef = "\tconst long " 
				constDef = constDef + name + " = " + v["Value"] + ";"
				idldefs = idldefs + constDef + "\n"
	return idldefs_lite, idldefs, impls


# Generate the interface information and dump them to separate files
# to be included by or patched into ISciMoz.idl and npscimoz.cxx.
f = Face.Face()
f.ReadFromFile(os.path.join(scintillaFilesPath, "Scintilla.iface"))
idldefs_lite, idldefs, impls = idlis(f)

idlLiteFileName = "ISciMoz_lite_gen.idl.fragment"
print "Dumping ISciMoz 'lite' inteface to %s" % idlLiteFileName
fout = open(idlLiteFileName, "w")
fout.write(idldefs_lite)
fout.close()

idlFileName = "ISciMoz_gen.idl.fragment"
print "Dumping ISciMoz inteface to %s" % idlFileName
fout = open(idlFileName, "w")
fout.write(idldefs)
fout.close()

npscimozGenFileName = "npscimoz_gen.h"
print "Dumping C++ SciMoz implementation to %s" % npscimozGenFileName
fout = open(npscimozGenFileName, "w")
fout.write(impls)
fout.close()

