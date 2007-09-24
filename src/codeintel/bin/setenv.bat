@echo off
echo ==== setting up environment for codeintel development ====

python support\mkenvconf.py -q
if ERRORLEVEL 1 goto error

call tmp\envconf.bat
if ERRORLEVEL 1 goto error

echo ====
goto done


:error
echo ****
echo * There was an error setting up your environment for codeintel dev.
echo * You must correct these errors before continuing.
echo ****

:done
