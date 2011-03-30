patch.exe
=========
This is built from patch 2.6.1 with msys patches (plus one extra hack for mingw
instead of msys).  The upstream source is
http://downloads.sourceforge.net/mingw/patch-2.6.1-1-msys-1.0.13-src.tar.lzma
Compiled with mingw-w64 linux32->mingw32 cross compiler (automated nightly for
1.0 branch / gcc 4.5.3, 2011-03-25) with configure arguments
--host=i686-w64-mingw32 CFLAGS="-Os -s -mtune=core2"
CXXFLAGS="-Os -s -mtune=core2" LDFLAGS="-Wl,--enable-auto-import".
