@echo off
echo envrun-moz-vc6-x86: setting up Visual C++ 6/x86 compiler environment

set _CURR_DRIVE=%~d0%
set _CURR_PATH=%~p0%
set _SETENV_SCRIPT=%_CURR_DRIVE%%_CURR_PATH%..\setenv-moz-msvc6.bat
call %_SETENV_SCRIPT%
set RETVAL=%ERRORLEVEL%

:check_setup
if "%RETVAL%x" == "0x" goto run_cmd
echo envrun-moz-vc6-x86: setting up Mozilla VC6 environment failed: %RETVAL%: aborting run
exit %RETVAL%

:run_cmd
echo envrun-moz-vc6-x86: running: %*
%*
set RETVAL=%ERRORLEVEL%
if "%RETVAL%x" == "0x" goto succeeded
echo envrun-moz-vc6-x86: '%*' failed: %RETVAL%
exit %RETVAL%

:succeeded
