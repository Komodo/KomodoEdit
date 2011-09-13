# Microsoft Developer Studio Project File - Name="SilverCityLib" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=SilverCityLib - Win32 Debug
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "SilverCityLib.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "SilverCityLib.mak" CFG="SilverCityLib - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "SilverCityLib - Win32 Release" (based on "Win32 (x86) Static Library")
!MESSAGE "SilverCityLib - Win32 Debug" (based on "Win32 (x86) Static Library")
!MESSAGE 

# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName "SilverCityLib"
# PROP Scc_LocalPath "..\.."
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "SilverCityLib - Win32 Release"

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
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /I "..\..\scintilla\win32" /I "..\..\scintilla\include" /I "..\..\scintilla\lexers" /I "..\..\scintilla\src" /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /YX /FD /c
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo

!ELSEIF  "$(CFG)" == "SilverCityLib - Win32 Debug"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 1
# PROP BASE Output_Dir "Debug"
# PROP BASE Intermediate_Dir "Debug"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 1
# PROP Output_Dir "Debug"
# PROP Intermediate_Dir "Debug"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /Gm /GX /ZI /Od /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" /YX /FD /GZ /c
# ADD CPP /nologo /MTd /W3 /Gm /GX /ZI /Od /I "..\..\scintilla\win32" /I "..\..\scintilla\include" /I "..\..\scintilla\lexers" /I "..\..\scintilla\src" /D "WIN32" /D "_DEBUG" /D "_MBCS" /D "_LIB" /D "LINK_LEXERS" /YX /FD /GZ /c
# ADD BASE RSC /l 0x409 /d "_DEBUG"
# ADD RSC /l 0x409 /d "_DEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo /out:"Debug\SilverCityLibD.lib"

!ENDIF 

# Begin Target

# Name "SilverCityLib - Win32 Release"
# Name "SilverCityLib - Win32 Debug"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=..\Src\BufferAccessor.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\KeyMap.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\KeyWords.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexAda.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexAsm.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexAVE.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexBaan.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexBullant.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexCLW.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexConf.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexCPP.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexCrontab.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexCSS.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexEiffel.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexEScript.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexForth.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexFortran.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexHTML.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexLisp.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexLout.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexLua.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexMatlab.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexMetapost.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexMMIXAL.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexMPT.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexNsis.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexOthers.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPascal.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPB.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPerl.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPOV.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPS.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexPython.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexRuby.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexScriptol.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexSQL.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexTeX.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexVB.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\LexYAML.cxx
# End Source File
# Begin Source File

SOURCE=..\Src\LineVector.cxx
# End Source File
# Begin Source File

SOURCE=..\Src\Platform.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\PropSet.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\StyleContext.cxx
# End Source File
# Begin Source File

SOURCE=..\..\scintilla\src\UniConversion.cxx
# End Source File
# End Group
# Begin Group "Header Files"

# PROP Default_Filter "h;hpp;hxx;hm;inl"
# End Group
# End Target
# End Project
