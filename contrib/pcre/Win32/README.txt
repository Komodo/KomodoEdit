Building PCRE for Windows
=========================

This directory contains ActiveState-added build support files for PCRE for
Windows.

vc6: Visual C++ 6
-----------------

Originally the Visual C++ 6 build files were added. At least I *believe* so.
ActiveState's original checkin of these files (p4 change 256935, in
//depot/main/support/pcre/Win32/...) doesn't give details.

    pcre.dsw
    pcre.dsp
    libpcre.dsp
    dftables.dsp
    (... there are others, but the four above are the main ones...)

To build with these:

1. Open "pcre.dsw" in the Visual C++ 6 IDE.
2. Build.


vc7: Visual Studio .NET 2003 (vs7.1)
------------------------------------

In p4 change 263072 in the //depot/main/Apps/Komodo-devel/... tree, some
build support files for Visual Studio 7.1 were added.

    libpcre.sln
    dftables.sln

Currently these aren't used by Komodo -- mainly because Komodo builds don't
use vc7.


vc8: Visual Studio 2005
-----------------------

Instead of adding Visual Studio project files (.sln, .vcproj) for
VC8 (aka Visual Studio 2005) and VC9 (aka Visual Studio 2008) etc., I've just
exported makefiles from the VC6 project files:

    libpcre.mak
    libpcre.dep
    dftables.mak
    dftables.dep
    pcregrep.mak
    pcregrep.dep
    pcretest.mak
    pcretest.dep
    tests.mak
    tests.dep

This should allow building with any Visual Studio/C++ compiler. See the next
section.

Note: These makefiles should be improved to deal with some compiler
warnings from more recent versions of Visual C++. For example, vc8 warns:

    cl.exe /nologo /MT /W3 /GX /O2 /I "Win32" /I "." /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /D "PCRE_STATIC" /Fp".\Release\libpcre.pch" /YX /Fo".\Release\\" /Fd".\Release\\" /FD /c ..\pcre_config.c
    cl : Command line warning D9035 : option 'GX' has been deprecated and will be removed in a future release
    cl : Command line warning D9036 : use 'EHsc' instead of 'GX'
    cl : Command line warning D9002 : ignoring unknown option '/YX'


Building PCRE with any MSVC compiler version
--------------------------------------------


1. Setup your shell environment for the appropriate Visual Studio/Visual
   C++. Typically this is done by either:

   (a) Running the "Command Prompt" shortcut in the Start Menu folder for
       that version of visual studio; or
   (b) Running the "vcvars32.bat" environment script provided with each
       version of Visual Studio. Examples:

       - vc6:
         "C:\Program Files\Microsoft Visual Studio\VC98\Bin\vcvars32.bat"
       - vc7:
         "C:\Program Files\Microsoft Visual Studio .NET 2003\Vc7\bin\vcvars32.bat"
       - vc8:
         "C:\Program Files\Microsoft Visual Studio 8\VC\bin\vcvars32.bat"
         "C:\Program Files\Microsoft Visual Studio 8\VC\bin\x86_amd64\vcvarsx86_amd64.bat" (cross-compile for x64 arch)
       - vc9:
         "C:\Program Files\Microsoft Visual Studio 9.0\VC\bin\vcvars32.bat"
         "C:\Program Files\Microsoft Visual Studio 9.0\VC\bin\x86_amd64\vcvarsx86_amd64.bat" (cross-compile for x64 arch)

2. Build the "dftables" and "libpcre" projects:

    cd Win32
    nmake -nologo -f dftables.mak
    nmake -nologo -f libpcre.mak

   The build output should be in the "Release" subdir.


