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

rem This is a slightly modified version of mozilla-build\start-msvc6.bat:
rem - don't start "msys\bin\bash"
rem - add some extra paths
echo ================ setup Mozilla/MSVC6 build env ===================

rem Keep guess-msvc.bat from trouncing the current PATH.
set MOZ_NO_RESET_PATH=1


SET MOZ_MSVCVERSION=6

if "x%MOZILLABUILD%" == "x" ( 
    set MOZILLABUILD=C:\mozilla-build
)

echo Mozilla tools directory: %MOZILLABUILD%

REM Get MSVC paths
call "%MOZILLABUILD%\guess-msvc.bat"
REM Ignore retval from guess-msvc.bat. It will return an error retval if,
REM for example, you've never had any of the Platform SDKs installed -- which
REM according to the current Mozilla Windows Build Prerequisites page is not
REM required when building with VC8 professional.
call cmd.exe /c exit 0

if "%VC6DIR%"=="" (
    ECHO "Microsoft Visual C++ version 6 was not found. Exiting."
    pause
)

REM For MSVC6, we use the "old" non-static moztools
set MOZ_TOOLS=%MOZILLABUILD%\moztools-180compat

rem append moztools to PATH
SET PATH=%PATH%;%MOZ_TOOLS%\bin

rem Other PATH additions.
rem - not sure make 3.81 is necessary but probably is
rem - msys\local\bin to get iconv.exe
set PATH=%MOZILLABUILD%\make-3.81\bin;%PATH%
set PATH=%MOZILLABUILD%\msys\local\bin;%PATH%
set PATH=%MOZILLABUILD%\info-zip;%PATH%
set PATH=%MOZILLABUILD%\msys\bin;%PATH%

rem Prepend MSVC paths
call "%VC6DIR%\Bin\vcvars32.bat"

echo ========================== done ==================================
