# Microsoft Developer Studio Project File - Name="tests" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Generic Project" 0x010a

CFG=tests - Win32 Debug
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "tests.mak".
!MESSAGE 
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

# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName "Perforce Project"
# PROP Scc_LocalPath "."
MTL=midl.exe

!IF  "$(CFG)" == "tests - Win32 Release"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "tests___Win32_Release"
# PROP BASE Intermediate_Dir "tests___Win32_Release"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "Release"
# PROP Intermediate_Dir "Release"
# PROP Target_Dir ""

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 1
# PROP BASE Output_Dir "tests___Win32_Debug"
# PROP BASE Intermediate_Dir "tests___Win32_Debug"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 1
# PROP Output_Dir "Debug"
# PROP Intermediate_Dir "Debug"
# PROP Target_Dir ""

!ENDIF 

# Begin Target

# Name "tests - Win32 Release"
# Name "tests - Win32 Debug"
# Begin Source File

SOURCE=.\RunTest

!IF  "$(CFG)" == "tests - Win32 Release"

# PROP Ignore_Default_Tool 1
# Begin Custom Build
InputPath=.\RunTest

"testtry" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	set PATH=%cygwin%\bin;%PATH% 
	sh.exe RunTest 1 2 4 5 6 7 8 9 
	sh.exe RunGrepTest 
	
# End Custom Build

!ELSEIF  "$(CFG)" == "tests - Win32 Debug"

# PROP Ignore_Default_Tool 1
# Begin Custom Build
InputPath=.\RunTest

"testtry" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	set PATH=%cygwin%\bin;%PATH% 
	sh.exe RunTest 1 2 4 5 6 7 8 9 
	sh.exe RunGrepTest 
	
# End Custom Build

!ENDIF 

# End Source File
# End Target
# End Project
