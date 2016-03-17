#!/bin/bash
# Run valgrind on testsuite
#
# See the accompanying LICENSE file.
#
# You should build a debug Python, with this being an example using /space/pydebug as
# the root.
#
# ver=2.7.5
# mkdir /space/pydebug
# cd /space/pydebug
# wget -O -  http://www.python.org/ftp/python/$ver/Python-$ver.tar.bz2 | tar xfj -
# cd Python-$ver
# # As an optimization Python keeps lists of various objects around for quick recycling
# # instead of freeing and then mallocing.  Unfortunately that obfuscates which code
# # was actually responsible for their existence.  Consequently we set all these to zero
# # so that normal malloc/frees happen and valgrind can do its magic.  Before Python 2.6
# # they all had different arbitrary names and in many cases could not be overridden.
# # PyDict_MAXFREELIST
# # PyTuple_MAXFREELIST
# # PyUnicode_MAXFREELIST
# # PySet_MAXFREELIST
# # PyCFunction_MAXFREELIST
# # PyList_MAXFREELIST
# # PyFrame_MAXFREELIST
# # PyMethod_MAXFREELIST
# s="_MAXFREELIST=0"
# ./configure --enable-unicode=ucs4 --with-pydebug --without-pymalloc --prefix=/space/pydebug \
# CPPFLAGS="-DPyDict$s -DPyFloat$s -DPyTuple$s -DPyUnicode$s -DPySet$s -DPyCFunction$s -DPyList$s -DPyFrame$s -DPyMethod$s"
#
# make install
#
# Then put /space/pydebug/bin/ first on your path.  The CPPFLAGS setting is to make sure no tuples are saved on freelists

if [ $# = 0 ]
then
  args="tests.py"
else
  args="$@"
fi

if [ -z "$SHOWINUSE" ]
then
   showleaks=""
else
   showleaks="--leak-check=full --leak-resolution=high --show-reachable=yes"
fi

if [ -z "$CALLGRIND" ]
then
   options="--track-fds=yes --num-callers=50 $showleaks --freelist-vol=500000000 --suppressions=`dirname $0`/sqlite3.supp"
   cflags="-DAPSW_TESTFIXTURES -DAPSW_NO_NDEBUG"
   opt="-Os"
   APSW_TEST_ITERATIONS=${APSW_TEST_ITERATIONS:=150}
   apswopt="APSW_NO_MEMLEAK=t APSW_TEST_ITERATIONS=$APSW_TEST_ITERATIONS"
else
   options="--tool=callgrind --dump-instr=yes --trace-jump=yes"
   cflags=""
   opt="-O2"
   apswopt=""
fi

DEFS=""

if [ -f sqlite3/sqlite3config.h ]
then
    DEFS="$DEFS -DAPSW_USE_SQLITE_CONFIG=\"sqlite3/sqlite3config.h\""
fi
# find python
PYTHON=${PYTHON:-python} # use whatever is in the path
INCLUDEDIR=`$PYTHON -c "import distutils.sysconfig, sys; sys.stdout.write(distutils.sysconfig.get_python_inc())"`
set -x
rm -f apsw.o apsw.so
gcc -pthread -fno-strict-aliasing  -g $opt -fPIC -W -Wall $cflags -DEXPERIMENTAL $DEFS -DAPSW_USE_SQLITE_AMALGAMATION=\"sqlite3.c\" -I$INCLUDEDIR -Isrc -I. -Isqlite3 -c src/apsw.c
gcc -pthread  -g $opt -shared apsw.o -o apsw.so
time env $apswopt valgrind $options $PYTHON $args
