@echo off
rem Copyright (c) 2006-2008 ActiveState Software Inc.

rem This is a slightly modified version of mozilla-build\start-msvc8.bat:
rem - don't start "msys\bin\bash"
rem - add some extra paths
echo ================ setup Mozilla/MSVC8 build env ===================


rem Keep guess-msvc.bat from trouncing the current PATH.
set MOZ_NO_RESET_PATH=1


SET MOZ_MSVCVERSION=9

if "x%MOZILLABUILD%" == "x" ( 
    set MOZILLABUILD=C:\mozilla-build
)

echo Mozilla tools directory: %MOZILLABUILD%

REM Get MSVC paths
call "%MOZILLABUILD%\guess-msvc.bat"
REM Ignore retval from guess-msvc.bat. It will return an error retval if,
REM for example, you've never had any of the Platform SDKs installed -- which
REM according to the current Mozilla Windows Build Prerequisites page is not
REM required when building with VC9 professional.
call cmd.exe /c exit 0

REM Use the "new" moztools-static
set MOZ_TOOLS=%MOZILLABUILD%\moztools

rem append moztools to PATH
SET PATH=%PATH%;%MOZ_TOOLS%\bin

rem Other PATH additions.
rem - not sure make 3.81 is necessary but probably is
rem - msys\local\bin to get iconv.exe
set PATH=%MOZILLABUILD%\make-3.81\bin;%PATH%
set PATH=%MOZILLABUILD%\msys\local\bin;%PATH%
set PATH=%MOZILLABUILD%\info-zip;%PATH%
set PATH=%MOZILLABUILD%\msys\bin;%PATH%


if "%VC9DIR%"=="" (
    if "%VC9EXPRESSDIR%"=="" (
        ECHO "Microsoft Visual C++ version 9 (2008) was not found. Exiting."
        pause
        EXIT /B 1
    )

    if "%SDKDIR%"=="" (
        ECHO "Microsoft Platform SDK was not found. Exiting."
        pause
        EXIT /B 1
    )

    rem Prepend MSVC paths
    call "%VC9XPRESSDIR%\Bin\vcvars32.bat"

    SET USESDK=1
    rem Don't set SDK paths in this block, because blocks are early-evaluated.

    rem Fix problem with VC++Express Edition
    if "%SDKVER%"=="6" (
        rem SDK Ver.6.0 (Windows Vista SDK) and 6.1 (Windows Server 2008 SDK)
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
    call "%VC9DIR%\Bin\vcvars32.bat"

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
    set LIB=%SDKDIR%\lib;%LIB%;%MOZBUILDDIR%atlthunk_compat

    if "%USEPSDKATL%"=="1" (
        if "%USEPSDKIDL%"=="1" (
            set INCLUDE=%SDKDIR%\include;%PSDKDIR%\include\atl;%PSDKDIR%\include;%INCLUDE%
        ) else (
            set INCLUDE=%SDKDIR%\include;%PSDKDIR%\include\atl;%INCLUDE%
        )
    ) else (
        if "%USEPSDKIDL%"=="1" (
            set INCLUDE=%SDKDIR%\include;%SDKDIR%\include\atl;%PSDKDIR%\include;%INCLUDE%
        ) else (
    set INCLUDE=%SDKDIR%\include;%SDKDIR%\include\atl;%INCLUDE%
        )
    )
)

echo ========================== done ==================================
