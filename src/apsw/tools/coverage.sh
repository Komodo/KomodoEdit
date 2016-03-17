#!/bin/bash
#

set -e

if [ $# = 0 ]
then
  args="tests.py"
else
  args="$@"
fi

# Measure code coverage
GCOVOPTS="-b -c"
GCOVOPTS=""
rm -f *.gcda *.gcov *.gcno sqlite3/*.gcov apsw.so
# find python
PYTHON=python # use whatever is in the path
INCLUDEDIR=`$PYTHON -c "import distutils.sysconfig,sys; sys.stdout.write(distutils.sysconfig.get_python_inc())"`

CFLAGS=''

if [ -f sqlite3/sqlite3config.h ]
then
    CFLAGS="$CFLAGS -DAPSW_USE_SQLITE_CONFIG=\"sqlite3/sqlite3config.h\""
fi
set -x
gcc -pthread -fno-strict-aliasing -ftest-coverage -fprofile-arcs -g -fPIC -Wall $CFLAGS -DEXPERIMENTAL -DSQLITE_ENABLE_API_ARMOR -DSQLITE_DEBUG -DAPSW_USE_SQLITE_AMALGAMATION=\"sqlite3.c\" -DAPSW_NO_NDEBUG -DAPSW_TESTFIXTURES -I$INCLUDEDIR -I. -Isqlite3 -Isrc -c src/apsw.c
gcc -pthread -ftest-coverage -fprofile-arcs -g -shared apsw.o -o apsw.so
gcc -fPIC -shared -Isqlite3 -I. -o testextension.sqlext -Isqlite3 src/testextension.c
set +e
$PYTHON $args
res=$?
gcov $GCOVOPTS apsw.gcno > /dev/null
mv sqlite3.c.gcov sqlite3/
mv *.gcov src/
python tools/coverageanalyser.py
exit $res
