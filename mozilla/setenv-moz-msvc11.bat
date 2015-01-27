@echo off
rem Copyright (c) 2006-2013 ActiveState Software Inc.

rem This is a slightly modified version of mozilla-build\start-msvc8.bat:
rem - don't start "msys\bin\bash"
rem - add some extra paths
echo ================ setup Mozilla/MSVC11 build env ===================


rem Keep guess-msvc.bat from trouncing the current PATH.
set MOZ_NO_RESET_PATH=1


SET MOZ_MSVCVERSION=11

if "x%MOZILLABUILD%" == "x" (
    set MOZILLABUILD=C:\mozilla-build
)

echo Mozilla tools directory: %MOZILLABUILD%

REM Get MSVC paths
call "%MOZILLABUILD%\guess-msvc.bat"
REM Ignore retval from guess-msvc.bat. It will return an error retval if,
REM for example, you've never had any of the Platform SDKs installed -- which
REM according to the current Mozilla Windows Build Prerequisites page is not
REM required when building with VC11 professional.
call cmd.exe /c exit 0

REM Use the "new" moztools-static
set MOZ_TOOLS=%MOZILLABUILD%\moztools

rem append moztools to PATH
SET PATH=%PATH%;%MOZ_TOOLS%\bin

rem Other PATH additions.
rem - msys\local\bin to get iconv.exe
set PATH=%MOZILLABUILD%\mozmake;%PATH%
rem - make 3.81 is fallback, in case mozmake isn't around
set PATH=%MOZILLABUILD%\make-3.81\bin;%PATH%
set PATH=%MOZILLABUILD%\msys\local\bin;%PATH%
set PATH=%MOZILLABUILD%\info-zip;%PATH%
set PATH=%MOZILLABUILD%\yasm;%PATH%
set PATH=%MOZILLABUILD%\msys\bin;%PATH%
set PATH=%MOZILLABUILD%\wget;%PATH%
set PATH=%MOZILLABUILD%\wix-351728;%PATH%
rem Include NSIS, just so the mozilla configure doesn't complain about it.
set PATH=%PATH%;%MOZILLABUILD%\nsis-2.46u
set PATH=%PATH%;%MOZILLABUILD%\nsis-2.33u
rem Add hg - in case the user doesn't have it on their path.
set PATH=%PATH%;%MOZILLABUILD%\hg
set PATH=%PATH%;%~dp0\..\util\black

if "%VC11DIR%"=="" (
    if "%VC11EXPRESSDIR%"=="" (
        ECHO "Microsoft Visual C++ version 11 (2012) was not found. Exiting."
        pause
        EXIT /B 1
    )

    if "%SDKDIR%"=="" (
        ECHO "Microsoft Platform SDK was not found. Exiting."
        pause
        EXIT /B 1
    )

    rem Prepend MSVC paths
    call "%VC11XPRESSDIR%\Bin\vcvars32.bat"

    SET USESDK=1
    rem Don't set SDK paths in this block, because blocks are early-evaluated.

    rem Fix problem with VC++Express Edition
    if "%SDKVER%"=="6" (
        rem SDK Ver.6.0 (Windows Vista SDK) and 6.1 (Windows Server 2012 SDK)
        rem does not contain ATL header files too.
        rem It is needed to use Platform SDK's ATL header files.
        SET USEPSDKATL=1

        rem SDK ver.6.0 does not contain OleAcc.idl
        rem It is needed to use Platform SDK's OleAcc.idl
        if "%SDKMINORVER%"=="0" (
            SET USEPSDKIDL=1
        )
    )
) else (
    rem Prepend MSVC paths
    call "%VC11DIR%\Bin\vcvars32.bat"

    rem If the SDK is Win2k3SP2 or higher, we want to use it
    if %SDKVER% GEQ 5 (
      SET USESDK=1
    )
)
if "%USESDK%"=="1" (
    rem Prepend SDK paths - Don't use the SDK SetEnv.cmd because it pulls in
    rem random VC paths which we don't want.
    rem Add the atlthunk compat library to the end of our LIB
    set "PATH=%SDKDIR%\bin;%PATH%"
    set "LIB=%SDKDIR%\lib;%LIB%;%MOZILLABUILD%atlthunk_compat"

    if "%USEPSDKATL%"=="1" (
        if "%USEPSDKIDL%"=="1" (
            set "INCLUDE=%SDKDIR%\include;%PSDKDIR%\include\atl;%PSDKDIR%\include;%INCLUDE%"
        ) else (
            set "INCLUDE=%SDKDIR%\include;%PSDKDIR%\include\atl;%INCLUDE%"
        )
    ) else (
        if "%USEPSDKIDL%"=="1" (
            set "INCLUDE=%SDKDIR%\include;%SDKDIR%\include\atl;%PSDKDIR%\include;%INCLUDE%"
        ) else (
            set "INCLUDE=%SDKDIR%\include;%SDKDIR%\include\atl;%INCLUDE%"
        )
    )
)

rem Force the first directory on the path to be our own custom bin directory,
rem so the build will find and use our own patch.exe.
set "PATH=%~dp0\bin-win32;%PATH%"

echo ========================== done ==================================
