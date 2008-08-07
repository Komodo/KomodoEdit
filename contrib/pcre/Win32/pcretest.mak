# Microsoft Developer Studio Generated NMAKE File, Based on pcretest.dsp
!IF "$(CFG)" == ""
CFG=pcretest - Win32 Release
!MESSAGE No configuration specified. Defaulting to pcretest - Win32 Release.
!ENDIF 

!IF "$(CFG)" != "pcretest - Win32 Release" && "$(CFG)" != "pcretest - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "pcretest.mak" CFG="pcretest - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "pcretest - Win32 Release" (based on "Win32 (x86) Console Application")
!MESSAGE "pcretest - Win32 Debug" (based on "Win32 (x86) Console Application")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

!IF  "$(CFG)" == "pcretest - Win32 Release"

OUTDIR=.\Release
INTDIR=.\Release

!IF "$(RECURSE)" == "0" 

ALL : ".\pcretest.exe"

!ELSE 

ALL : "libpcre - Win32 Release" ".\pcretest.exe"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"libpcre - Win32 ReleaseCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcre_tables.obj"
	-@erase "$(INTDIR)\pcretest.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase ".\pcretest.exe"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MD /W3 /GX /O2 /I "./" /D "WIN32" /D "NDEBUG" /D "_CONSOLE" /D "SUPPORT_UTF8" /D "SUPPORT_UCP" /D POSIX_MALLOC_THRESHOLD=10 /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /c 

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
BSC32_FLAGS=/nologo /o"$(OUTDIR)\pcretest.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=libpcre-6.3.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:console /incremental:no /pdb:"$(OUTDIR)\pcretest.pdb" /machine:I386 /out:"pcretest.exe" /libpath:"Release" 
LINK32_OBJS= \
	"$(INTDIR)\pcre_tables.obj" \
	"$(INTDIR)\pcretest.obj" \
	"$(OUTDIR)\libpcre.lib"

".\pcretest.exe" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ELSEIF  "$(CFG)" == "pcretest - Win32 Debug"

OUTDIR=.\Debug
INTDIR=.\Debug
# Begin Custom Macros
OutDir=.\Debug
# End Custom Macros

!IF "$(RECURSE)" == "0" 

ALL : ".\pcretest.exe" "$(OUTDIR)\pcretest.bsc"

!ELSE 

ALL : "libpcre - Win32 Debug" ".\pcretest.exe" "$(OUTDIR)\pcretest.bsc"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"libpcre - Win32 DebugCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcre_tables.obj"
	-@erase "$(INTDIR)\pcre_tables.sbr"
	-@erase "$(INTDIR)\pcretest.obj"
	-@erase "$(INTDIR)\pcretest.sbr"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vc60.pdb"
	-@erase "$(OUTDIR)\pcretest.bsc"
	-@erase "$(OUTDIR)\pcretest.pdb"
	-@erase ".\pcretest.exe"
	-@erase ".\pcretest.ilk"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MTd /W3 /Gm /GX /Zi /Od /I "./" /D "WIN32" /D "_DEBUG" /D "_CONSOLE" /D "SUPPORT_UTF8" /D "SUPPORT_UCP" /D POSIX_MALLOC_THRESHOLD=10 /D "STATIC" /FR"$(INTDIR)\\" /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /GZ /c 

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
BSC32_FLAGS=/nologo /o"$(OUTDIR)\pcretest.bsc" 
BSC32_SBRS= \
	"$(INTDIR)\pcre_tables.sbr" \
	"$(INTDIR)\pcretest.sbr"

"$(OUTDIR)\pcretest.bsc" : "$(OUTDIR)" $(BSC32_SBRS)
    $(BSC32) @<<
  $(BSC32_FLAGS) $(BSC32_SBRS)
<<

LINK32=link.exe
LINK32_FLAGS=libpcre-6.3.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib /nologo /subsystem:console /incremental:yes /pdb:"$(OUTDIR)\pcretest.pdb" /debug /machine:I386 /out:"pcretest.exe" /pdbtype:sept /libpath:"Debug" 
LINK32_OBJS= \
	"$(INTDIR)\pcre_tables.obj" \
	"$(INTDIR)\pcretest.obj" \
	"$(OUTDIR)\libpcre.lib"

".\pcretest.exe" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("pcretest.dep")
!INCLUDE "pcretest.dep"
!ELSE 
!MESSAGE Warning: cannot find "pcretest.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "pcretest - Win32 Release" || "$(CFG)" == "pcretest - Win32 Debug"
SOURCE=..\pcre_tables.c

!IF  "$(CFG)" == "pcretest - Win32 Release"


"$(INTDIR)\pcre_tables.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!ELSEIF  "$(CFG)" == "pcretest - Win32 Debug"


"$(INTDIR)\pcre_tables.obj"	"$(INTDIR)\pcre_tables.sbr" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!ENDIF 

SOURCE=..\pcretest.c

!IF  "$(CFG)" == "pcretest - Win32 Release"


"$(INTDIR)\pcretest.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!ELSEIF  "$(CFG)" == "pcretest - Win32 Debug"


"$(INTDIR)\pcretest.obj"	"$(INTDIR)\pcretest.sbr" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!ENDIF 

!IF  "$(CFG)" == "pcretest - Win32 Release"

"libpcre - Win32 Release" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Release" 
   cd "."

"libpcre - Win32 ReleaseCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\libpcre.mak" CFG="libpcre - Win32 Release" RECURSE=1 CLEAN 
   cd "."

!ELSEIF  "$(CFG)" == "pcretest - Win32 Debug"

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

