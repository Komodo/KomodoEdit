@echo off
echo ================ setup Mozilla/MSVC6 build env ===================

rem Keep guess-msvc.bat from trouncing the current PATH.
set MOZ_NO_RESET_PATH=1


SET MOZ_MSVCVERSION=6

rem If there's no setting for MOZILLABUILD,
rem hardcode it to the Mozilla default:
rem     SET MOZILLABUILDDRIVE=%~d0%
rem     SET MOZILLABUILDPATH=%~p0%
rem     SET MOZILLABUILD=%MOZILLABUILDDRIVE%%MOZILLABUILDPATH%

if "x%MOZILLABUILD%" == "x" ( 
    set MOZILLABUILD=C:\mozilla-build
)

echo Mozilla tools directory: %MOZILLABUILD%

REM Get MSVC paths
call "%MOZILLABUILD%\guess-msvc.bat"

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
