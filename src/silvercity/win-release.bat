echo off
rm -rf build
c:\python20\python setup.py install
if errorlevel 1 goto :installerror
rm -rf build
c:\python21\python setup.py install
if errorlevel 1 goto :installerror
rm -rf build
if errorlevel 1 goto :installerror
c:\python22\python setup.py install
rm -rf build

c:\python20\python PySilverCity\Scripts\test.py
if errorlevel 1 goto testerror
c:\python21\python PySilverCity\Scripts\test.py
if errorlevel 1 goto testerror
c:\python22\python PySilverCity\Scripts\test.py
if errorlevel 1 goto testerror

rm -rf dist
c:\python22\python setup.py sdist --formats=gztar,zip
rm -rf build
c:\python20\python setup.py bdist --formats=wininst
rm -rf build
c:\python21\python setup.py bdist --formats=wininst
rm -rf build
c:\python22\python setup.py bdist --formats=wininst

cd dist
mkdir temp
cp SilverCity-*.zip temp
cd temp
unzip *.zip
rm *.zip
rm *.gz
cd SilverCity-*
c:\python22\python setup.py build
if errorlevel 1 goto sdisterror

cd ..\..
rm -rf temp
cd ..
echo Success!
goto end

:installerror
echo install failure
goto end

:testerror
echo test failure
goto end

:sdisterror
echo sdist build failure
goto end

:end