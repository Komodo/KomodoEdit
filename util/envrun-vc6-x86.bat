@echo off
echo envrun-vc6-x86: setting up Visual C++ 6/x86 compiler environment

call "C:\Program Files\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT"
set RETVAL=%ERRORLEVEL%

:check_setup
if "%RETVAL%x" == "0x" goto run_cmd
echo envrun-vc6-x86: setting up vc6-x86 environment failed: %RETVAL%: aborting run
echo Perhaps MSVC6 is installed in a non-default location.
echo This stub expects MSVC6's setup batch file to be installed here:
echo   "C:\Program Files\Microsoft Visual Studio\VC98\bin\VCVARS32.BAT"
exit %RETVAL%

:run_cmd
echo envrun-vc6-x86: running: %*
%*
set RETVAL=%ERRORLEVEL%
if "%RETVAL%x" == "0x" goto succeeded
echo envrun-vc6-x86: '%*' failed: %RETVAL%
exit %RETVAL%

:succeeded

