@echo off

rem ***** BEGIN LICENSE BLOCK *****
rem Version: MPL 1.1/GPL 2.0/LGPL 2.1
rem 
rem The contents of this file are subject to the Mozilla Public License
rem Version 1.1 (the "License"); you may not use this file except in
rem compliance with the License. You may obtain a copy of the License at
rem http://www.mozilla.org/MPL/
rem 
rem Software distributed under the License is distributed on an "AS IS"
rem basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
rem License for the specific language governing rights and limitations
rem under the License.
rem 
rem The Original Code is Komodo code.
rem 
rem The Initial Developer of the Original Code is ActiveState Software Inc.
rem Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
rem ActiveState Software Inc. All Rights Reserved.
rem 
rem Contributor(s):
rem   ActiveState Software Inc
rem 
rem Alternatively, the contents of this file may be used under the terms of
rem either the GNU General Public License Version 2 or later (the "GPL"), or
rem the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
rem in which case the provisions of the GPL or the LGPL are applicable instead
rem of those above. If you wish to allow use of your version of this file only
rem under the terms of either the GPL or the LGPL, and not to allow others to
rem use your version of this file under the terms of the MPL, indicate your
rem decision by deleting the provisions above and replace them with the notice
rem and other provisions required by the GPL or the LGPL. If you do not delete
rem the provisions above, a recipient may use your version of this file under
rem the terms of any one of the MPL, the GPL or the LGPL.
rem 
rem ***** END LICENSE BLOCK *****

echo envrun-vc6-x86: setting up Visual C++ 6/x86 compiler environment


if exist "C:\Program Files\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT" goto vc6_in_progfiles
if exist "C:\Program Files (x86)\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT" goto vc6_in_progfilesx86
set RETVAL=1

:vc6_error
echo envrun-vc6-x86: setting up vc6-x86 environment failed: aborting run
exit %RETVAL%

:vc6_in_progfiles
call "C:\Program Files\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT"
set RETVAL=%ERRORLEVEL%
if "%RETVAL%x" == "0x" goto run_cmd
goto vc6_error

:vc6_in_progfilesx86
call "C:\Program Files (x86)\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT"
set RETVAL=%ERRORLEVEL%
if "%RETVAL%x" == "0x" goto run_cmd
goto vc6_error

:run_cmd
echo envrun-vc6-x86: running: %*
%*
set RETVAL=%ERRORLEVEL%
if "%RETVAL%x" == "0x" goto succeeded
echo envrun-vc6-x86: '%*' failed: %RETVAL%
exit %RETVAL%

:succeeded

