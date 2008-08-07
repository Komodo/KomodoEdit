# Microsoft Developer Studio Generated NMAKE File, Based on pcregrep.dsp
!IF "$(CFG)" == ""
CFG=pcregrep - Win32 Release
!MESSAGE No configuration specified. Defaulting to pcregrep - Win32 Release.
!ENDIF 

!IF "$(CFG)" != "pcregrep - Win32 Release" && "$(CFG)" != "pcregrep - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "pcregrep.mak" CFG="pcregrep - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "pcregrep - Win32 Release" (based on "Win32 (x86) Console Application")
!MESSAGE "pcregrep - Win32 Debug" (based on "Win32 (x86) Console Application")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

!IF  "$(CFG)" == "pcregrep - Win32 Release"

OUTDIR=.\Release
INTDIR=.\Release

!IF "$(RECURSE)" == "0" 

ALL : ".\pcregrep.exe"

!ELSE 

ALL : "libpcre - Win32 Release" ".\pcregrep.exe"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"libpcre - Win32 ReleaseCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcregrep.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase ".\pcregrep.exe"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MD /W3 /GX /O2 /I "./" /D "WIN32" /D "NDEBUG" /D "_CONSOLE" /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

RSC=rc.exe
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\pcregrep.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=libpcre-6.3.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:console /incremental:no /pdb:"$(OUTDIR)\pcregrep.pdb" /machine:I386 /out:"pcregrep.exe" /libpath:"./Release" 
LINK32_OBJS= \
	"$(INTDIR)\pcregrep.obj" \
	"$(OUTDIR)\libpcre.lib"

".\pcregrep.exe" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ELSEIF  "$(CFG)" == "pcregrep - Win32 Debug"

OUTDIR=.\Debug
INTDIR=.\Debug

!IF "$(RECURSE)" == "0" 

ALL : ".\pcregrep.exe"

!ELSE 

ALL : "libpcre - Win32 Debug" ".\pcregrep.exe"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"libpcre - Win32 DebugCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcregrep.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vc60.pdb"
	-@erase "$(OUTDIR)\pcregrep.pdb"
	-@erase ".\pcregrep.exe"
	-@erase ".\pcregrep.ilk"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MTd /W3 /Gm /GX /ZI /Od /I "./" /D "WIN32" /D "_DEBUG" /D "_CONSOLE" /D "STATIC" /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /GZ /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

RSC=rc.exe
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\pcregrep.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=libpcre-6.3.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:console /incremental:yes /pdb:"$(OUTDIR)\pcregrep.pdb" /debug /machine:I386 /out:"pcregrep.exe" /pdbtype:sept /libpath:"./Debug" 
LINK32_OBJS= \
	"$(INTDIR)\pcregrep.obj" \
	"$(OUTDIR)\libpcre.lib"

".\pcregrep.exe" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("pcregrep.dep")
!INCLUDE "pcregrep.dep"
!ELSE 
!MESSAGE Warning: cannot find "pcregrep.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "pcregrep - Win32 Release" || "$(CFG)" == "pcregrep - Win32 Debug"
SOURCE=..\pcregrep.c

"$(INTDIR)\pcregrep.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!IF  "$(CFG)" == "pcregrep - Win32 Release"

"libpcre - Win32 Release" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Release" 
   cd "."

"libpcre - Win32 ReleaseCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Release" RECURSE=1 CLEAN 
   cd "."

!ELSEIF  "$(CFG)" == "pcregrep - Win32 Debug"

"libpcre - Win32 Debug" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Debug" 
   cd "."

"libpcre - Win32 DebugCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Debug" RECURSE=1 CLEAN 
   cd "."

!ENDIF 


!ENDIF 

