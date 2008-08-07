# Microsoft Developer Studio Generated NMAKE File, Based on tests.dsp
!IF "$(CFG)" == ""
CFG=tests - Win32 Release
!MESSAGE No configuration specified. Defaulting to tests - Win32 Release.
!ENDIF 

!IF "$(CFG)" != "tests - Win32 Release" && "$(CFG)" != "tests - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "tests.mak" CFG="tests - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "tests - Win32 Release" (based on "Win32 (x86) Generic Project")
!MESSAGE "tests - Win32 Debug" (based on "Win32 (x86) Generic Project")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

OUTDIR=.\Release
INTDIR=.\Release

!IF "$(RECURSE)" == "0" 

ALL : ".\testtry" 

!ELSE 

ALL : "pcretest - Win32 Release" "pcregrep - Win32 Release" ".\testtry" 

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"pcregrep - Win32 ReleaseCLEAN" "pcretest - Win32 ReleaseCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase 
	-@erase "testtry"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

!IF  "$(CFG)" == "tests - Win32 Release"

MTL=midl.exe
MTL_PROJ=

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

MTL=midl.exe
MTL_PROJ=

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("tests.dep")
!INCLUDE "tests.dep"
!ELSE 
!MESSAGE Warning: cannot find "tests.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "tests - Win32 Release" || "$(CFG)" == "tests - Win32 Debug"

!IF  "$(CFG)" == "tests - Win32 Release"

"pcregrep - Win32 Release" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcregrep.mak" CFG="pcregrep - Win32 Release" 
   cd "."

"pcregrep - Win32 ReleaseCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcregrep.mak" CFG="pcregrep - Win32 Release" RECURSE=1 CLEAN 
   cd "."

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

"pcregrep - Win32 Debug" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcregrep.mak" CFG="pcregrep - Win32 Debug" 
   cd "."

"pcregrep - Win32 DebugCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcregrep.mak" CFG="pcregrep - Win32 Debug" RECURSE=1 CLEAN 
   cd "."

!ENDIF 

!IF  "$(CFG)" == "tests - Win32 Release"

"pcretest - Win32 Release" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcretest.mak" CFG="pcretest - Win32 Release" 
   cd "."

"pcretest - Win32 ReleaseCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcretest.mak" CFG="pcretest - Win32 Release" RECURSE=1 CLEAN 
   cd "."

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

"pcretest - Win32 Debug" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcretest.mak" CFG="pcretest - Win32 Debug" 
   cd "."

"pcretest - Win32 DebugCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\pcretest.mak" CFG="pcretest - Win32 Debug" RECURSE=1 CLEAN 
   cd "."

!ENDIF 

SOURCE=.\RunTest

!IF  "$(CFG)" == "tests - Win32 Release"

InputPath=.\RunTest

".\testtry" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	<<tempfile.bat 
	@echo off 
	set PATH=%cygwin%\bin;%PATH% 
	sh.exe RunTest 1 2 4 5 6 7 8 9 
	sh.exe RunGrepTest 
<< 
	

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

InputPath=.\RunTest

".\testtry" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	<<tempfile.bat 
	@echo off 
	set PATH=%cygwin%\bin;%PATH% 
	sh.exe RunTest 1 2 4 5 6 7 8 9 
	sh.exe RunGrepTest 
<< 
	

!ENDIF 


!ENDIF 

