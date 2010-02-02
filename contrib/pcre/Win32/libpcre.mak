# Microsoft Developer Studio Generated NMAKE File, Based on libpcre.dsp
!IF "$(CFG)" == ""
CFG=libpcre - Win32 Release
!MESSAGE No configuration specified. Defaulting to libpcre - Win32 Release.
!ENDIF 

!IF "$(CFG)" != "libpcre - Win32 Release" && "$(CFG)" != "libpcre - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "libpcre.mak" CFG="libpcre - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "libpcre - Win32 Release" (based on "Win32 (x86) Static Library")
!MESSAGE "libpcre - Win32 Debug" (based on "Win32 (x86) Static Library")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

!IF  "$(CFG)" == "libpcre - Win32 Release"

OUTDIR=.\Release
INTDIR=.\Release
# Begin Custom Macros
OutDir=.\Release
# End Custom Macros

!IF "$(RECURSE)" == "0" 

ALL : "$(OUTDIR)\libpcre.lib"

!ELSE 

ALL : "dftables - Win32 Release" "$(OUTDIR)\libpcre.lib"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"dftables - Win32 ReleaseCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcre_chartables.obj"
	-@erase "$(INTDIR)\pcre_compile.obj"
	-@erase "$(INTDIR)\pcre_config.obj"
	-@erase "$(INTDIR)\pcre_dfa_exec.obj"
	-@erase "$(INTDIR)\pcre_exec.obj"
	-@erase "$(INTDIR)\pcre_fullinfo.obj"
	-@erase "$(INTDIR)\pcre_get.obj"
	-@erase "$(INTDIR)\pcre_globals.obj"
	-@erase "$(INTDIR)\pcre_info.obj"
	-@erase "$(INTDIR)\pcre_maketables.obj"
	-@erase "$(INTDIR)\pcre_ord2utf8.obj"
	-@erase "$(INTDIR)\pcre_printint.obj"
	-@erase "$(INTDIR)\pcre_refcount.obj"
	-@erase "$(INTDIR)\pcre_study.obj"
	-@erase "$(INTDIR)\pcre_tables.obj"
	-@erase "$(INTDIR)\pcre_try_flipped.obj"
	-@erase "$(INTDIR)\pcre_ucp_findchar.obj"
	-@erase "$(INTDIR)\pcre_valid_utf8.obj"
	-@erase "$(INTDIR)\pcre_version.obj"
	-@erase "$(INTDIR)\pcre_xclass.obj"
	-@erase "$(INTDIR)\pcreposix.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(OUTDIR)\libpcre.lib"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

MTL=midl.exe
CPP=cl.exe
CPP_PROJ=/nologo /MT /W3 /EHsc /O2 /I "Win32" /I "." /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /D "PCRE_STATIC" /Fp"$(INTDIR)\libpcre.pch" /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /c 

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
BSC32_FLAGS=/nologo /o"$(OUTDIR)\libpcre.bsc" 
BSC32_SBRS= \
	
LIB32=link.exe -lib
LIB32_FLAGS=/nologo /out:"$(OUTDIR)\libpcre.lib" 
LIB32_OBJS= \
	"$(INTDIR)\pcre_chartables.obj" \
	"$(INTDIR)\pcre_compile.obj" \
	"$(INTDIR)\pcre_config.obj" \
	"$(INTDIR)\pcre_dfa_exec.obj" \
	"$(INTDIR)\pcre_exec.obj" \
	"$(INTDIR)\pcre_fullinfo.obj" \
	"$(INTDIR)\pcre_get.obj" \
	"$(INTDIR)\pcre_globals.obj" \
	"$(INTDIR)\pcre_info.obj" \
	"$(INTDIR)\pcre_maketables.obj" \
	"$(INTDIR)\pcre_ord2utf8.obj" \
	"$(INTDIR)\pcre_printint.obj" \
	"$(INTDIR)\pcre_refcount.obj" \
	"$(INTDIR)\pcre_study.obj" \
	"$(INTDIR)\pcre_tables.obj" \
	"$(INTDIR)\pcre_try_flipped.obj" \
	"$(INTDIR)\pcre_ucp_findchar.obj" \
	"$(INTDIR)\pcre_valid_utf8.obj" \
	"$(INTDIR)\pcre_version.obj" \
	"$(INTDIR)\pcre_xclass.obj" \
	"$(INTDIR)\pcreposix.obj"

"$(OUTDIR)\libpcre.lib" : "$(OUTDIR)" $(DEF_FILE) $(LIB32_OBJS)
    $(LIB32) @<<
  $(LIB32_FLAGS) $(DEF_FLAGS) $(LIB32_OBJS)
<<

!ELSEIF  "$(CFG)" == "libpcre - Win32 Debug"

OUTDIR=.\Debug
INTDIR=.\Debug
# Begin Custom Macros
OutDir=.\Debug
# End Custom Macros

!IF "$(RECURSE)" == "0" 

ALL : "$(OUTDIR)\libpcre.lib"

!ELSE 

ALL : "dftables - Win32 Debug" "$(OUTDIR)\libpcre.lib"

!ENDIF 

!IF "$(RECURSE)" == "1" 
CLEAN :"dftables - Win32 DebugCLEAN" 
!ELSE 
CLEAN :
!ENDIF 
	-@erase "$(INTDIR)\pcre_chartables.obj"
	-@erase "$(INTDIR)\pcre_compile.obj"
	-@erase "$(INTDIR)\pcre_config.obj"
	-@erase "$(INTDIR)\pcre_dfa_exec.obj"
	-@erase "$(INTDIR)\pcre_exec.obj"
	-@erase "$(INTDIR)\pcre_fullinfo.obj"
	-@erase "$(INTDIR)\pcre_get.obj"
	-@erase "$(INTDIR)\pcre_globals.obj"
	-@erase "$(INTDIR)\pcre_info.obj"
	-@erase "$(INTDIR)\pcre_maketables.obj"
	-@erase "$(INTDIR)\pcre_ord2utf8.obj"
	-@erase "$(INTDIR)\pcre_printint.obj"
	-@erase "$(INTDIR)\pcre_refcount.obj"
	-@erase "$(INTDIR)\pcre_study.obj"
	-@erase "$(INTDIR)\pcre_tables.obj"
	-@erase "$(INTDIR)\pcre_try_flipped.obj"
	-@erase "$(INTDIR)\pcre_ucp_findchar.obj"
	-@erase "$(INTDIR)\pcre_valid_utf8.obj"
	-@erase "$(INTDIR)\pcre_version.obj"
	-@erase "$(INTDIR)\pcre_xclass.obj"
	-@erase "$(INTDIR)\pcreposix.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vc60.pdb"
	-@erase "$(OUTDIR)\libpcre.lib"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

MTL=midl.exe
CPP=cl.exe
CPP_PROJ=/nologo /MTd /W3 /Gm /EHsc /ZI /Od /I "Win32" /I "." /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" /D "PCRE_STATIC" /Fp"$(INTDIR)\libpcre.pch" /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /GZ /c 

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
BSC32_FLAGS=/nologo /o"$(OUTDIR)\libpcre.bsc" 
BSC32_SBRS= \
	
LIB32=link.exe -lib
LIB32_FLAGS=/nologo /out:"$(OUTDIR)\libpcre.lib" 
LIB32_OBJS= \
	"$(INTDIR)\pcre_chartables.obj" \
	"$(INTDIR)\pcre_compile.obj" \
	"$(INTDIR)\pcre_config.obj" \
	"$(INTDIR)\pcre_dfa_exec.obj" \
	"$(INTDIR)\pcre_exec.obj" \
	"$(INTDIR)\pcre_fullinfo.obj" \
	"$(INTDIR)\pcre_get.obj" \
	"$(INTDIR)\pcre_globals.obj" \
	"$(INTDIR)\pcre_info.obj" \
	"$(INTDIR)\pcre_maketables.obj" \
	"$(INTDIR)\pcre_ord2utf8.obj" \
	"$(INTDIR)\pcre_printint.obj" \
	"$(INTDIR)\pcre_refcount.obj" \
	"$(INTDIR)\pcre_study.obj" \
	"$(INTDIR)\pcre_tables.obj" \
	"$(INTDIR)\pcre_try_flipped.obj" \
	"$(INTDIR)\pcre_ucp_findchar.obj" \
	"$(INTDIR)\pcre_valid_utf8.obj" \
	"$(INTDIR)\pcre_version.obj" \
	"$(INTDIR)\pcre_xclass.obj" \
	"$(INTDIR)\pcreposix.obj"

"$(OUTDIR)\libpcre.lib" : "$(OUTDIR)" $(DEF_FILE) $(LIB32_OBJS)
    $(LIB32) @<<
  $(LIB32_FLAGS) $(DEF_FLAGS) $(LIB32_OBJS)
<<

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("libpcre.dep")
!INCLUDE "libpcre.dep"
!ELSE 
!MESSAGE Warning: cannot find "libpcre.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "libpcre - Win32 Release" || "$(CFG)" == "libpcre - Win32 Debug"
SOURCE=.\pcre_chartables.c

"$(INTDIR)\pcre_chartables.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=..\pcre_compile.c

"$(INTDIR)\pcre_compile.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_config.c

"$(INTDIR)\pcre_config.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_dfa_exec.c

"$(INTDIR)\pcre_dfa_exec.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_exec.c

"$(INTDIR)\pcre_exec.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_fullinfo.c

"$(INTDIR)\pcre_fullinfo.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_get.c

"$(INTDIR)\pcre_get.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_globals.c

"$(INTDIR)\pcre_globals.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_info.c

"$(INTDIR)\pcre_info.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_maketables.c

"$(INTDIR)\pcre_maketables.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_ord2utf8.c

"$(INTDIR)\pcre_ord2utf8.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_printint.c

"$(INTDIR)\pcre_printint.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_refcount.c

"$(INTDIR)\pcre_refcount.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_study.c

"$(INTDIR)\pcre_study.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_tables.c

"$(INTDIR)\pcre_tables.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_try_flipped.c

"$(INTDIR)\pcre_try_flipped.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_ucp_findchar.c

"$(INTDIR)\pcre_ucp_findchar.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_valid_utf8.c

"$(INTDIR)\pcre_valid_utf8.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_version.c

"$(INTDIR)\pcre_version.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcre_xclass.c

"$(INTDIR)\pcre_xclass.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


SOURCE=..\pcreposix.c

"$(INTDIR)\pcreposix.obj" : $(SOURCE) "$(INTDIR)"
	$(CPP) $(CPP_PROJ) $(SOURCE)


!IF  "$(CFG)" == "libpcre - Win32 Release"

"dftables - Win32 Release" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\dftables.mak" CFG="dftables - Win32 Release" 
   cd "."

"dftables - Win32 ReleaseCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\dftables.mak" CFG="dftables - Win32 Release" RECURSE=1 CLEAN 
   cd "."

!ELSEIF  "$(CFG)" == "libpcre - Win32 Debug"

"dftables - Win32 Debug" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\dftables.mak" CFG="dftables - Win32 Debug" 
   cd "."

"dftables - Win32 DebugCLEAN" : 
   cd "."
   $(MAKE) /$(MAKEFLAGS) /F ".\dftables.mak" CFG="dftables - Win32 Debug" RECURSE=1 CLEAN 
   cd "."

!ENDIF 

SOURCE=.\mkchartables.empty

!IF  "$(CFG)" == "libpcre - Win32 Release"

InputPath=.\mkchartables.empty

".\pcre_chartables.c" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	<<tempfile.bat 
	@echo off 
	dftables.exe pcre_chartables.c 
	del testtry 
<< 
	

!ELSEIF  "$(CFG)" == "libpcre - Win32 Debug"

InputPath=.\mkchartables.empty
USERDEP__MKCHA="dftables.exe"	

".\pcre_chartables.c" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)" $(USERDEP__MKCHA)
	<<tempfile.bat 
	@echo off 
	dftables.exe pcre_chartables.c 
	del testtry 
<< 
	

!ENDIF 


!ENDIF 

