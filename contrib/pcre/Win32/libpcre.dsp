# Microsoft Developer Studio Project File - Name="libpcre" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=libpcre - Win32 Debug
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "libpcre.mak".
!MESSAGE 
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

# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName "Perforce Project"
# PROP Scc_LocalPath ".."
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "libpcre - Win32 Release"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Release"
# PROP BASE Intermediate_Dir "Release"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "Release"
# PROP Intermediate_Dir "Release"
# PROP Target_Dir ""
MTL=midl.exe
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /YX /FD /c
# ADD CPP /nologo /W3 /MT /GX /O2 /I "Win32" /I "." /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /D "PCRE_STATIC" /YX /FD /c
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo

!ELSEIF  "$(CFG)" == "libpcre - Win32 Debug"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 1
# PROP BASE Output_Dir "libpcre___Win32_Debug"
# PROP BASE Intermediate_Dir "libpcre___Win32_Debug"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 1
# PROP Output_Dir "Debug"
# PROP Intermediate_Dir "Debug"
# PROP Target_Dir ""
MTL=midl.exe
# ADD BASE CPP /nologo /W3 /Gm /GX /ZI /Od /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" /YX /FD /GZ /c
# ADD CPP /nologo /MTd /W3 /Gm /GX /ZI /Od /I "Win32" /I "." /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" /D "PCRE_STATIC" /YX /FD /GZ /c
# ADD BASE RSC /l 0x409 /d "_DEBUG"
# ADD RSC /l 0x409 /d "_DEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo

!ENDIF 

# Begin Target

# Name "libpcre - Win32 Release"
# Name "libpcre - Win32 Debug"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\pcre_chartables.c
# End Source File
# Begin Source File

SOURCE=..\pcre_compile.c
# End Source File
# Begin Source File

SOURCE=..\pcre_config.c
# End Source File
# Begin Source File

SOURCE=..\pcre_dfa_exec.c
# End Source File
# Begin Source File

SOURCE=..\pcre_exec.c
# End Source File
# Begin Source File

SOURCE=..\pcre_fullinfo.c
# End Source File
# Begin Source File

SOURCE=..\pcre_get.c
# End Source File
# Begin Source File

SOURCE=..\pcre_globals.c
# End Source File
# Begin Source File

SOURCE=..\pcre_info.c
# End Source File
# Begin Source File

SOURCE=..\pcre_maketables.c
# End Source File
# Begin Source File

SOURCE=..\pcre_ord2utf8.c
# End Source File
# Begin Source File

SOURCE=..\pcre_printint.c
# End Source File
# Begin Source File

SOURCE=..\pcre_refcount.c
# End Source File
# Begin Source File

SOURCE=..\pcre_study.c
# End Source File
# Begin Source File

SOURCE=..\pcre_tables.c
# End Source File
# Begin Source File

SOURCE=..\pcre_try_flipped.c
# End Source File
# Begin Source File

SOURCE=..\pcre_ucp_findchar.c
# End Source File
# Begin Source File

SOURCE=..\pcre_valid_utf8.c
# End Source File
# Begin Source File

SOURCE=..\pcre_version.c
# End Source File
# Begin Source File

SOURCE=..\pcre_xclass.c
# End Source File
# Begin Source File

SOURCE=..\pcreposix.c
# End Source File
# End Group
# Begin Group "Header Files"

# PROP Default_Filter "h;hpp;hxx;hm;inl"
# Begin Source File

SOURCE=.\config.h
# End Source File
# Begin Source File

SOURCE=..\internal.h
# End Source File
# Begin Source File

SOURCE=.\pcre.h
# End Source File
# Begin Source File

SOURCE=..\pcre_internal.h
# End Source File
# Begin Source File

SOURCE=..\pcreposix.h
# End Source File
# End Group
# Begin Source File

SOURCE=.\mkchartables.empty

!IF  "$(CFG)" == "libpcre - Win32 Release"

# Begin Custom Build
InputPath=.\mkchartables.empty

"pcre_chartables.c" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	dftables.exe pcre_chartables.c 
	del testtry 
	
# End Custom Build

!ELSEIF  "$(CFG)" == "libpcre - Win32 Debug"

USERDEP__MKCHA="dftables.exe"	
# Begin Custom Build
InputPath=.\mkchartables.empty

"pcre_chartables.c" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	dftables.exe pcre_chartables.c 
	del testtry 
	
# End Custom Build

!ENDIF 

# End Source File
# End Target
# End Project
