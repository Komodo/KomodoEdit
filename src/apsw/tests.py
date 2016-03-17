#!/usr/bin/env python

# See the accompanying LICENSE file.

# APSW test suite - runs under both Python 2 and Python 3 hence a lot
# of wierd constructs to be simultaneously compatible with both.
# (2to3 is not used).

import apsw
import sys
import os
import codecs

write=sys.stdout.write


def print_version_info(write=write):
    write("                Python "+sys.executable+" "+str(sys.version_info)+"\n")
    write("Testing with APSW file "+apsw.__file__+"\n")
    write("          APSW version "+apsw.apswversion()+"\n")
    write("    SQLite lib version "+apsw.sqlitelibversion()+"\n")
    write("SQLite headers version "+str(apsw.SQLITE_VERSION_NUMBER)+"\n")
    write("    Using amalgamation "+str(apsw.using_amalgamation)+"\n")

    if [int(x) for x in apsw.sqlitelibversion().split(".")]<[3,7,8]:
        write("You are using an earlier version of SQLite than recommended\n")

    sys.stdout.flush()

# sigh
iswindows=sys.platform in ('win32', 'win64')

py3=sys.version_info>=(3,0)

# prefix for test files (eg if you want it on tmpfs)
TESTFILEPREFIX=os.environ.get("APSWTESTPREFIX", "")

def read_whole_file(name, mode, encoding=None):
    if encoding:
        f=codecs.open(name, mode, encoding)
    else:
        f=open(name, mode)
    try:
        return f.read()
    finally:
        f.close()

# If two is present then one is encoding
def write_whole_file(name, mode, one, two=None):
    if two:
        f=codecs.open(name, mode, one)
        data=two
    else:
        f=open(name, mode)
        data=one
    try:
        f.write(data)
    finally:
        f.close()

# unittest stuff from here on

import unittest
import math
import random
import time
import threading
import glob
import pickle
import shutil
import getpass

if py3:
    import queue as Queue
else:
    import Queue
import traceback
import re
import gc
try:
    import ctypes
    import _ctypes
except:
    ctypes=None
    _ctypes=None

# yay
is64bit=ctypes and ctypes.sizeof(ctypes.c_size_t)>=8

# Unicode string/bytes prefix
if py3:
    UPREFIX=""
    BPREFIX="b"
else:
    UPREFIX="u"
    BPREFIX=""
# Return a unicode string - x should have been raw
def u(x):
    return eval(UPREFIX+"'''"+x+"'''")

# Return a bytes (py3)/buffer (py2) - x should have been raw
def b(x):
    if py3:
        return eval(BPREFIX+"'''"+x+"'''")
    return eval("buffer('''"+x+"''')")

# return bytes (py3)/string (py2) - x should have been raw
# Use this instead of b for file i/o data as py2 uses str
def BYTES(x):
    if py3: return b(x)
    return eval("'''"+x+"'''")

def l(x):
    if py3: return eval(x)
    return eval(x+"L")

# Various py3 things
if py3:
    long=int

if not py3:
    # emulation of py3 next built-in.  In py2 the iternext method is exposed
    # as object.next() but in py3 it is object.__next__().
    def next(iterator, *args):
        if len(args)>1:
            raise TypeError("bad args")
        try:
            return iterator.next()
        except StopIteration:
            if len(args):
                return args[0]
            raise

# Make next switch between the iterator and fetchone alternately
_realnext=next
_nextcounter=0
def next(cursor, *args):
    global _nextcounter
    _nextcounter+=1
    if _nextcounter%2:
        return _realnext(cursor, *args)
    res=cursor.fetchone()
    if res is None:
        if args:
            return args[0]
        return None
    return res

# py3 has a useless sys.excepthook mainly to avoid allocating any
# memory as the exception could have been running out of memory.  So
# we use our own which is also valueable on py2 as it says it is an
# unraiseable exception (with testcode you sometimes can't tell if it
# is unittest showing you an exception or the unraiseable).  It is
# mainly VFS code that needs to raise these.
def ehook(etype, evalue, etraceback):
    sys.stderr.write("Unraiseable exception "+str(etype)+":"+str(evalue)+"\n")
    traceback.print_tb(etraceback)
sys.excepthook=ehook

# exec is a huge amount of fun having different syntax
if py3:
    def execwrapper(astring, theglobals, thelocals):
        thelocals=thelocals.copy()
        thelocals["astring"]=astring
        exec("exec(astring, theglobals, thelocals)")
else:
    def execwrapper(astring, theglobals, thelocals):
        thelocals=thelocals.copy()
        thelocals["astring"]=astring
        exec ("exec astring in theglobals, thelocals")

# helper functions
def randomintegers(howmany):
    for i in range(howmany):
        yield (random.randint(0,9999999999),)

def randomstring(length):
    l=list("abcdefghijklmnopqrstuvwxyz0123456789")
    while len(l)<length:
        l.extend(l)
    l=l[:length]
    random.shuffle(l)
    return "".join(l)

# An instance of this class is used to get the -1 return value to the
# C api PyObject_IsTrue
class BadIsTrue(int):
    # py2 does this
    def __nonzero__(self):
        1/0
    # py3 does this
    def __bool__(self):
        1/0

# helper class - runs code in a seperate thread
class ThreadRunner(threading.Thread):

    def __init__(self, callable, *args, **kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.callable=callable
        self.args=args
        self.kwargs=kwargs
        self.q=Queue.Queue()
        self.started=False

    def start(self):
        if not self.started:
            self.started=True
            threading.Thread.start(self)

    def go(self):
        self.start()
        t,res=self.q.get()
        if t: # result
            return res
        else: # exception
            if py3:
                exec("raise res[1].with_traceback(res[2])")
            else:
                exec("raise res[0], res[1], res[2]")

    def run(self):
        try:
            self.q.put( (True, self.callable(*self.args, **self.kwargs)) )
        except:
            self.q.put( (False, sys.exc_info()) )

# Windows doesn't allow files that are open to be deleted.  Even after
# we close them, tagalongs such as virus scanners, tortoisesvn etc can
# keep them open.  But the good news is that we can rename a file that
# is in use.  This background thread does the background deletions of the
# renamed files
def bgdel():
    q=bgdelq
    while True:
        name=q.get()
        while os.path.exists(name):
            try:
                if os.path.isfile(name):
                    os.remove(name)
                else:
                    shutil.rmtree(name)
            except:
                pass
            if os.path.exists(name):
                time.sleep(0.1)

bgdelq=Queue.Queue()
bgdelthread=threading.Thread(target=bgdel)
bgdelthread.setDaemon(True)
bgdelthread.start()

def deletefile(name):
    l=list("abcdefghijklmn")
    random.shuffle(l)
    newname=name+"-n-"+"".join(l)
    count=0
    while os.path.exists(name):
        count+=1
        try:
            os.rename(name, newname)
        except:
            if count>30: # 3 seconds we have been at this!
                # So give up and give it a stupid name.  The sooner
                # this so called operating system withers into obscurity
                # the better
                n=list("abcdefghijklmnopqrstuvwxyz")
                random.shuffle(n)
                n="".join(n)
                try:
                    os.rename(name, "windowssucks-"+n+".deletememanually")
                except:
                    pass
                break
            # Make windows happy
            time.sleep(0.1)
            gc.collect()
    if os.path.exists(newname):
        bgdelq.put(newname)
        # Give bg thread a chance to run
        time.sleep(0.1)

# Monkey patching FTW
if not hasattr(unittest.TestCase, "assertTrue"):
    unittest.TestCase.assertTrue=unittest.TestCase.assert_

openflags=apsw.SQLITE_OPEN_READWRITE|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_URI

# main test class/code
class APSW(unittest.TestCase):

    connection_nargs={ # number of args for function.  those not listed take zero
        'createaggregatefunction': 2,
        'createcollation': 2,
        'createscalarfunction': 3,
        'collationneeded': 1,
        'setauthorizer': 1,
        'setbusyhandler': 1,
        'setbusytimeout': 1,
        'setcommithook': 1,
        'setprofile': 1,
        'setrollbackhook': 1,
        'setupdatehook': 1,
        'setprogresshandler': 2,
        'enableloadextension': 1,
        'createmodule': 2,
        'filecontrol': 3,
        'setexectrace': 1,
        'setrowtrace': 1,
        '__enter__': 0,
        '__exit__': 3,
        'backup': 3,
        'wal_autocheckpoint': 1,
        'setwalhook': 1,
        'readonly': 1,
        'db_filename': 1
        }

    cursor_nargs={
        'execute': 1,
        'executemany': 2,
        'setexectrace': 1,
        'setrowtrace': 1,
        }

    blob_nargs={
        'write': 1,
        'read': 1,
        'readinto': 1,
        'reopen': 1,
        'seek': 2
        }

    def deltempfiles(self):
        for name in ("testdb", "testdb2", "testdb3", "testfile", "testfile2", "testdb2x",
                     "test-shell-1", "test-shell-1.py",
                     "test-shell-in", "test-shell-out", "test-shell-err"):
            for i in "-wal", "-journal", "":
                if os.path.exists(TESTFILEPREFIX+name+i):
                    deletefile(TESTFILEPREFIX+name+i)

    saved_connection_hooks=[]

    def setUp(self):
        # clean out database and journals from last runs
        self.saved_connection_hooks.append(apsw.connection_hooks)
        gc.collect()
        self.deltempfiles()
        self.db=apsw.Connection(TESTFILEPREFIX+"testdb", flags=openflags)

    def tearDown(self):
        if self.db is not None:
            self.db.close(True)
        del self.db
        apsw.connection_hooks=self.saved_connection_hooks.pop() # back to original value
        gc.collect()
        self.deltempfiles()

    def assertTableExists(self, tablename):
        self.assertEqual(next(self.db.cursor().execute("select count(*) from ["+tablename+"]"))[0], 0)

    def assertTableNotExists(self, tablename):
        # you get SQLError if the table doesn't exist!
        self.assertRaises(apsw.SQLError, self.db.cursor().execute, "select count(*) from ["+tablename+"]")

    def assertTablesEqual(self, dbl, left, dbr, right):
        # Ensure tables have the same contents.  Rowids can be
        # different and select gives unordered results so this is
        # quite challenging
        l=dbl.cursor()
        r=dbr.cursor()
        # check same number of rows
        lcount=l.execute("select count(*) from ["+left+"]").fetchall()[0][0]
        rcount=r.execute("select count(*) from ["+right+"]").fetchall()[0][0]
        self.assertEqual(lcount, rcount)
        # check same number and names and order for columns
        lnames=[row[1] for row in l.execute("pragma table_info(["+left+"])")]
        rnames=[row[1] for row in r.execute("pragma table_info(["+left+"])")]
        self.assertEqual(lnames, rnames)
        # read in contents, sort and compare
        lcontents=l.execute("select * from ["+left+"]").fetchall()
        rcontents=r.execute("select * from ["+right+"]").fetchall()
        lcontents.sort()
        rcontents.sort()
        self.assertEqual(lcontents, rcontents)

    def assertRaisesUnraisable(self, exc, func, *args, **kwargs):
        orig=sys.excepthook
        try:
            called=[]
            def ehook(t,v,tb):
                called.append( (t,v,tb) )
            sys.excepthook=ehook
            try:
                try:
                    return func(*args, **kwargs)
                except:
                    # This ensures frames have their local variables
                    # cleared before we put the original excepthook
                    # back.  Clearing the variables results in some
                    # more SQLite operations which also can raise
                    # unraisables.  traceback.clear_frames was
                    # introduced in Python 3.4 and unittest was
                    # updated to call it in assertRaises.  See issue
                    # 164
                    if hasattr(traceback, "clear_frames"):
                        traceback.clear_frames(sys.exc_info()[2])
                    raise
            finally:
                if len(called)<1:
                    self.fail("Call %s(*%s, **%s) did not do any unraiseable" % (func, args, kwargs) )
                self.assertEqual(exc, called[0][0]) # check it was the correct type
        finally:
            sys.excepthook=orig

    def testSanity(self):
        "Check all parts compiled and are present"
        # check some error codes etc are present - picked first middle and last from lists in code
        apsw.SQLError
        apsw.MisuseError
        apsw.NotADBError
        apsw.ThreadingViolationError
        apsw.BindingsError
        apsw.ExecTraceAbort
        apsw.SQLITE_FCNTL_SIZE_HINT
        apsw.mapping_file_control["SQLITE_FCNTL_SIZE_HINT"]==apsw.SQLITE_FCNTL_SIZE_HINT
        apsw.URIFilename
        self.assertTrue(len(apsw.sqlite3_sourceid())>10)

    def testConnection(self):
        "Test connection opening"
        # bad keyword arg
        self.assertRaises(TypeError, apsw.Connection, ":memory:", user="nobody")
        # wrong types
        self.assertRaises(TypeError, apsw.Connection, 3)
        # non-unicode
        if not py3:
            self.assertRaises(UnicodeDecodeError, apsw.Connection, "\xef\x22\xd3\x9e")
        # bad file (cwd)
        self.assertRaises(apsw.CantOpenError, apsw.Connection, ".")
        # bad open flags can't be tested as sqlite accepts them all - ticket #3037
        # self.assertRaises(apsw.CantOpenError, apsw.Connection, "<non-existent-file>", flags=65535)

        # bad vfs
        self.assertRaises(TypeError, apsw.Connection, "foo", vfs=3, flags=-1)
        self.assertRaises(apsw.SQLError, apsw.Connection, "foo", vfs="jhjkds")

    def testConnectionFileControl(self):
        "Verify sqlite3_file_control"
        # Note that testVFS deals with success cases and the actual vfs backend
        self.assertRaises(TypeError, self.db.filecontrol, 1, 2)
        self.assertRaises(TypeError, self.db.filecontrol, "main", 1001, "foo")
        self.assertRaises(OverflowError, self.db.filecontrol, "main", 1001, l("45236748972389749283"))
        self.assertEqual(self.db.filecontrol("main", 1001, 25), False)

    def testConnectionConfig(self):
        "Test Connection.config function"
        self.assertRaises(TypeError, self.db.config)
        self.assertRaises(TypeError, self.db.config, "three")
        x=long(0x7fffffff)
        self.assertRaises(OverflowError, self.db.config, x*x*x*x*x)
        self.assertRaises(ValueError, self.db.config, 82397)
        self.assertRaises(TypeError, self.db.config, apsw.SQLITE_DBCONFIG_ENABLE_FKEY, "banana")
        for i in apsw.SQLITE_DBCONFIG_ENABLE_FKEY, apsw.SQLITE_DBCONFIG_ENABLE_TRIGGER:
            self.assertEqual(1, self.db.config(i, 1))
            self.assertEqual(1, self.db.config(i, -1))
            self.assertEqual(0, self.db.config(i, 0))

    def testMemoryLeaks(self):
        "MemoryLeaks: Run with a memory profiler such as valgrind and debug Python"
        # make and toss away a bunch of db objects, cursors, functions etc - if you use memory profiling then
        # simple memory leaks will show up
        c=self.db.cursor()
        c.execute("create table foo(x)")
        vals=[ [1], [None], [math.pi], ["kjkljkljl"], [u(r"\u1234\u345432432423423kjgjklhdfgkjhsdfjkghdfjskh")],
               [b(r"78696ghgjhgjhkgjkhgjhg\xfe\xdf")] ]
        c.executemany("insert into foo values(?)", vals)
        for i in range(MEMLEAKITERATIONS):
            db=apsw.Connection(TESTFILEPREFIX+"testdb")
            db.createaggregatefunction("aggfunc", lambda x: x)
            db.createscalarfunction("scalarfunc", lambda x: x)
            db.setbusyhandler(lambda x: False)
            db.setbusytimeout(1000)
            db.setcommithook(lambda x=1: 0)
            db.setrollbackhook(lambda x=2: 1)
            db.setupdatehook(lambda x=3: 2)
            db.setwalhook(lambda *args: 0)
            db.collationneeded(lambda x: 4)
            def rt1(c,r):
                db.setrowtrace(rt2)
                return r
            def rt2(c,r):
                c.setrowtrace(rt1)
                return r
            def et1(c,s,b):
                db.setexectrace(et2)
                return True
            def et2(c,s,b):
                c.setexectrace(et1)
                return True
            for i in range(120):
                c2=db.cursor()
                c2.setrowtrace(rt1)
                c2.setexectrace(et1)
                for row in c2.execute("select * from foo"+" "*i):  # spaces on end defeat statement cache
                    pass
            del c2
            db.close()


    def testBindings(self):
        "Check bindings work correctly"
        c=self.db.cursor()
        c.execute("create table foo(x,y,z)")
        vals=(
            ("(?,?,?)", (1,2,3)),
            ("(?,?,?)", [1,2,3]),
            ("(?,?,?)", range(1,4)),
            ("(:a,$b,:c)", {'a': 1, 'b': 2, 'c': 3}),
            ("(1,?,3)", (2,)),
            ("(1,$a,$c)", {'a': 2, 'b': 99, 'c': 3}),
            # some unicode fun
            (u(r"($\N{LATIN SMALL LETTER E WITH CIRCUMFLEX},:\N{LATIN SMALL LETTER A WITH TILDE},$\N{LATIN SMALL LETTER O WITH DIAERESIS})"), (1,2,3)),
            (u(r"($\N{LATIN SMALL LETTER E WITH CIRCUMFLEX},:\N{LATIN SMALL LETTER A WITH TILDE},$\N{LATIN SMALL LETTER O WITH DIAERESIS})"),
             {u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}"): 1,
              u(r"\N{LATIN SMALL LETTER A WITH TILDE}"): 2,
              u(r"\N{LATIN SMALL LETTER O WITH DIAERESIS}"): 3,})
            )

        for str,bindings in vals:
            c.execute("insert into foo values"+str, bindings)
            self.assertEqual(next(c.execute("select * from foo")), (1,2,3))
            c.execute("delete from foo")

        # currently missing dict keys come out as null
        c.execute("insert into foo values(:a,:b,$c)", {'a': 1, 'c':3}) # 'b' deliberately missing
        self.assertEqual((1,None,3), next(c.execute("select * from foo")))
        c.execute("delete from foo")

        # these ones should cause errors
        vals=(
            (apsw.BindingsError, "(?,?,?)", (1,2)), # too few
            (apsw.BindingsError, "(?,?,?)", (1,2,3,4)), # too many
            (apsw.BindingsError,          "(?,?,?)", None), # none at all
            (apsw.BindingsError, "(?,?,?)", {'a': 1}), # ? type, dict bindings (note that the reverse will work since all
                                                       # named bindings are also implicitly numbered
            (TypeError,          "(?,?,?)", 2),    # not a dict or sequence
            (TypeError,          "(:a,:b,:c)", {'a': 1, 'b': 2, 'c': self}), # bad type for c
            )
        for exc,str,bindings in vals:
            self.assertRaises(exc, c.execute, "insert into foo values"+str, bindings)

        # with multiple statements
        c.execute("insert into foo values(?,?,?); insert into foo values(?,?,?)", (99,100,101,102,103,104))
        self.assertRaises(apsw.BindingsError, c.execute, "insert into foo values(?,?,?); insert into foo values(?,?,?); insert some more",
                          (100,100,101,1000,103)) # too few
        self.assertRaises(apsw.BindingsError, c.execute, "insert into foo values(?,?,?); insert into foo values(?,?,?)",
                          (101,100,101,1000,103,104,105)) # too many
        # check the relevant statements did or didn't execute as appropriate
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=99"))[0], 1)
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=102"))[0], 1)
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=100"))[0], 1)
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=1000"))[0], 0)
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=101"))[0], 1)
        self.assertEqual(next(self.db.cursor().execute("select count(*) from foo where x=105"))[0], 0)

        # check there are some bindings!
        self.assertRaises(apsw.BindingsError, c.execute, "create table bar(x,y,z);insert into bar values(?,?,?)")

        # across executemany
        vals=( (1,2,3), (4,5,6), (7,8,9) )
        c.executemany("insert into foo values(?,?,?);", vals)
        for x,y,z in vals:
            self.assertEqual(next(c.execute("select * from foo where x=?",(x,))), (x,y,z))

        # with an iterator
        def myvals():
            for i in range(10):
                yield {'a': i, 'b': i*10, 'c': i*100}
        c.execute("delete from foo")
        c.executemany("insert into foo values($a,:b,$c)", myvals())
        c.execute("delete from foo")

        # errors for executemany
        self.assertRaises(TypeError, c.executemany, "statement", 12, 34, 56) # incorrect num params
        self.assertRaises(TypeError, c.executemany, "statement", 12) # wrong type
        self.assertRaises(apsw.SQLError, c.executemany, "syntax error", [(1,)]) # error in prepare
        def myiter():
            yield 1/0
        self.assertRaises(ZeroDivisionError, c.executemany, "statement", myiter()) # immediate error in iterator
        def myiter():
            yield self
        self.assertRaises(TypeError, c.executemany, "statement", myiter()) # immediate bad type
        self.assertRaises(TypeError, c.executemany, "select ?", ((self,), (1))) # bad val
        c.executemany("statement", ()) # empty sequence

        # error in iterator after a while
        def myvals():
            for i in range(2):
                yield {'a': i, 'b': i*10, 'c': i*100}
            1/0
        self.assertRaises(ZeroDivisionError, c.executemany, "insert into foo values($a,:b,$c)", myvals())
        self.assertEqual(next(c.execute("select count(*) from foo"))[0], 2)
        c.execute("delete from foo")

        # return bad type from iterator after a while
        def myvals():
            for i in range(2):
                yield {'a': i, 'b': i*10, 'c': i*100}
            yield self

        self.assertRaises(TypeError, c.executemany, "insert into foo values($a,:b,$c)", myvals())
        self.assertEqual(next(c.execute("select count(*) from foo"))[0], 2)
        c.execute("delete from foo")

        # some errors in executemany
        self.assertRaises(apsw.BindingsError, c.executemany, "insert into foo values(?,?,?)", ( (1,2,3), (1,2,3,4)))
        self.assertRaises(apsw.BindingsError, c.executemany, "insert into foo values(?,?,?)", ( (1,2,3), (1,2)))

        # incomplete execution across executemany
        c.executemany("select * from foo; select ?", ( (1,), (2,) )) # we don't read
        self.assertRaises(apsw.IncompleteExecutionError, c.executemany, "begin")

        # set type (pysqlite error with this)
        if sys.version_info>=(2, 4, 0):
            c.execute("create table xxset(x,y,z)")
            c.execute("insert into xxset values(?,?,?)", set((1,2,3)))
            c.executemany("insert into xxset values(?,?,?)", (set((4,5,6)),))
            result=[(1,2,3), (4,5,6)]
            for i,v in enumerate(c.execute("select * from xxset order by x")):
                self.assertEqual(v, result[i])

    def testCursor(self):
        "Check functionality of the cursor"
        c=self.db.cursor()
        # shouldn't be able to manually create
        self.assertRaises(TypeError, type(c))

        # give bad params
        self.assertRaises(TypeError, c.execute)
        self.assertRaises(TypeError, c.execute, "foo", "bar", "bam")

        # empty statements
        c.execute("")
        c.execute(" ;\n\t\r;;")

        # unicode
        self.assertEqual(3, next(c.execute(u("select 3")))[0])
        if not py3:
            self.assertRaises(UnicodeDecodeError, c.execute, "\x99\xaa\xbb\xcc")

        # does it work?
        c.execute("create table foo(x,y,z)")
        # table should be empty
        entry=-1
        for entry,values in enumerate(c.execute("select * from foo")):
            pass
        self.assertEqual(entry,-1, "No rows should have been returned")
        # add ten rows
        for i in range(10):
            c.execute("insert into foo values(1,2,3)")
        for entry,values in enumerate(c.execute("select * from foo")):
            # check we get back out what we put in
            self.assertEqual(values, (1,2,3))
        self.assertEqual(entry, 9, "There should have been ten rows")
        # does getconnection return the right object
        self.assertTrue(c.getconnection() is self.db)
        # check getdescription - note column with space in name and [] syntax to quote it
        cols=(
            ("x a space", "integer"),
            ("y", "text"),
            ("z", "foo"),
            ("a", "char"),
            (u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}\N{LATIN SMALL LETTER A WITH TILDE}"),
             u(r"\N{LATIN SMALL LETTER O WITH DIAERESIS}\N{LATIN SMALL LETTER U WITH CIRCUMFLEX}")),
            )
        c.execute("drop table foo; create table foo (%s)" % (", ".join(["[%s] %s" % (n,t) for n,t in cols]),))
        c.execute("insert into foo([x a space]) values(1)")
        for row in c.execute("select * from foo"):
            self.assertEqual(cols, c.getdescription())
            self.assertEqual(cols, tuple([d[:2] for d in c.description]))
            self.assertEqual((None,None,None,None,None), c.description[0][2:])
            self.assertEqual(list(map(len, c.description)), [7]*len(cols))
        # check description caching isn't broken
        cols2=cols[1:4]
        for row in c.execute("select y,z,a from foo"):
            self.assertEqual(cols2, c.getdescription())
            self.assertEqual(cols2, tuple([d[:2] for d in c.description]))
            self.assertEqual((None,None,None,None,None), c.description[0][2:])
            self.assertEqual(list(map(len, c.description)), [7]*len(cols2))
        # execution is complete ...
        self.assertRaises(apsw.ExecutionCompleteError, c.getdescription)
        self.assertRaises(apsw.ExecutionCompleteError, lambda: c.description)
        self.assertRaises(StopIteration, lambda xx=0: _realnext(c))
        self.assertRaises(StopIteration, lambda xx=0: _realnext(c))
        # fetchone is used throughout, check end behaviour
        self.assertEqual(None, c.fetchone())
        self.assertEqual(None, c.fetchone())
        self.assertEqual(None, c.fetchone())
        # nulls for getdescription
        for row in c.execute("pragma user_version"):
            self.assertEqual(c.getdescription(), ( ('user_version', None), ))
        # incomplete
        c.execute("select * from foo; create table bar(x)") # we don't bother reading leaving
        self.assertRaises(apsw.IncompleteExecutionError, c.execute, "select * from foo") # execution incomplete
        self.assertTableNotExists("bar")
        # autocommit
        self.assertEqual(True, self.db.getautocommit())
        c.execute("begin immediate")
        self.assertEqual(False, self.db.getautocommit())
        # pragma
        c.execute("pragma user_version")
        c.execute("pragma pure=nonsense")
        # error
        self.assertRaises(apsw.SQLError, c.execute, "create table bar(x,y,z); this is a syntax error; create table bam(x,y,z)")
        self.assertTableExists("bar")
        self.assertTableNotExists("bam")
        # fetchall
        self.assertEqual(c.fetchall(), [])
        self.assertEqual(c.execute("select 3; select 4").fetchall(), [(3,), (4,)] )

    def testTypes(self):
        "Check type information is maintained"
        c=self.db.cursor()
        c.execute("create table foo(row,x)")

        vals=test_types_vals

        for i,v in enumerate(vals):
            c.execute("insert into foo values(?,?)", (i, v))

        # add function to test conversion back as well
        def snap(*args):
            return args[0]
        self.db.createscalarfunction("snap", snap)

        # now see what we got out
        count=0
        for row,v,fv in c.execute("select row,x,snap(x) from foo"):
            count+=1
            if type(vals[row]) is float:
                self.assertAlmostEqual(vals[row], v)
                self.assertAlmostEqual(vals[row], fv)
            else:
                self.assertEqual(vals[row], v)
                self.assertEqual(vals[row], fv)
        self.assertEqual(count, len(vals))

        # check some out of bounds conditions
        # integer greater than signed 64 quantity (SQLite only supports up to that)
        self.assertRaises(OverflowError, c.execute, "insert into foo values(9999,?)", (922337203685477580799,))
        self.assertRaises(OverflowError, c.execute, "insert into foo values(9999,?)", (-922337203685477580799,))

        # invalid character data - non-ascii data must be provided in unicode
        if not py3: # py3 - all strings are unicode so not a problem
            self.assertRaises(UnicodeDecodeError, c.execute, "insert into foo values(9999,?)", ("\xfe\xfb\x80\x92",))

        # not valid types for SQLite
        self.assertRaises(TypeError, c.execute, "insert into foo values(9999,?)", (apsw,)) # a module
        self.assertRaises(TypeError, c.execute, "insert into foo values(9999,?)", (type,)) # type
        self.assertRaises(TypeError, c.execute, "insert into foo values(9999,?)", (dir,))  # function

        # check nothing got inserted
        self.assertEqual(0, next(c.execute("select count(*) from foo where row=9999"))[0])

        # playing with default encoding and non-ascii strings - py2 only
        if py3: return
        enc=sys.getdefaultencoding()
        reload(sys) # gets setdefaultencoding function back
        try:
            for v in vals:
                if type(v)!=unicode:
                    continue
                def encoding(*args):
                    return v.encode("utf8") # returns as str not unicode
                self.db.createscalarfunction("encoding", encoding)
                sys.setdefaultencoding("utf8")
                for row in c.execute("select encoding(3)"):
                    self.assertEqual(v, row[0])
                c.execute("insert into foo values(1234,?)", (v.encode("utf8"),))
                for row in c.execute("select x from foo where rowid="+str(self.db.last_insert_rowid())):
                    self.assertEqual(v, row[0])
        finally:
            sys.setdefaultencoding(enc)

    def testFormatSQLValue(self):
        "Verify text formatting of values"
        vals=(
            (3, "3"),
            (3.1, "3.1"),
            (-3, "-3"),
            (-3.1, "-3.1"),
            (9223372036854775807, "9223372036854775807"),
            (-9223372036854775808, "-9223372036854775808"),
            (None, "NULL"),
            ("ABC", "'ABC'"),
            (u(r"\N{BLACK STAR} \N{WHITE STAR} \N{LIGHTNING} \N{COMET} "), "'"+u(r"\N{BLACK STAR} \N{WHITE STAR} \N{LIGHTNING} \N{COMET} ")+"'"),
            ("", "''"),
            ("'", "''''"),
            ("'a", "'''a'"),
            ("a'", "'a'''"),
            ("''", "''''''"),
            ("'"*20000, "'"+"'"*40000+"'"),
            ("\0", "''||X'00'||''"),
            ("AB\0C", "'AB'||X'00'||'C'"),
            ("A'B'\0C", "'A''B'''||X'00'||'C'"),
            ("\0A'B", "''||X'00'||'A''B'"),
            ("A'B\0", "'A''B'||X'00'||''"),
            (b(r"AB\0C"), "X'41420043'"),
            )
        for vin, vout in vals:
            if not py3:
                if isinstance(vin, str):
                    vin=unicode(vin)
            out=apsw.format_sql_value(vin)
            if not py3:
                self.assertEqual(out, unicode(vout))
            else:
                self.assertEqual(out, vout)
        # Errors
        if not py3:
            self.assertRaises(TypeError, apsw.format_sql_value, "plain string")
        self.assertRaises(TypeError, apsw.format_sql_value, apsw)
        self.assertRaises(TypeError, apsw.format_sql_value)

    def testWAL(self):
        "Test WAL functions"
        # note that it is harmless calling wal functions on a db not in wal mode
        self.assertRaises(TypeError, self.db.wal_autocheckpoint)
        self.assertRaises(TypeError, self.db.wal_autocheckpoint, "a strinbg")
        self.db.wal_autocheckpoint(8912)
        self.assertRaises(TypeError, self.db.wal_checkpoint, -1)
        self.db.wal_checkpoint()
        self.db.wal_checkpoint("main")
        if sys.version_info>(2,4): # 2.3 barfs internally
            v=self.db.wal_checkpoint(mode=apsw.SQLITE_CHECKPOINT_PASSIVE)
            self.assertTrue(isinstance(v, tuple) and len(v)==2 and isinstance(v[0], int) and isinstance(v[1], int))
            self.assertRaises(apsw.MisuseError, self.db.wal_checkpoint, mode=876786)
        self.assertRaises(TypeError, self.db.setwalhook)
        self.assertRaises(TypeError, self.db.setwalhook, 12)
        self.db.setwalhook(None)
        # check we can set wal mode
        self.assertEqual("wal", self.db.cursor().execute("pragma journal_mode=wal").fetchall()[0][0])
        # errors in wal callback
        def zerodiv(*args): 1/0
        self.db.setwalhook(zerodiv)
        self.assertRaises(ZeroDivisionError, self.db.cursor().execute, "create table one(x)")
        # the error happens after the wal commit so the table should exist
        self.assertTableExists("one")

        def badreturn(*args): return "three"
        self.db.setwalhook(badreturn)
        self.assertRaises(TypeError, self.db.cursor().execute, "create table two(x)")
        self.assertTableExists("two")

        expectdbname=""
        def walhook(conn, dbname, pages):
            self.assertTrue(conn is self.db)
            self.assertTrue(pages>0)
            self.assertEqual(dbname, expectdbname)
            return apsw.SQLITE_OK

        expectdbname="main"
        self.db.setwalhook(walhook)
        self.db.cursor().execute("create table three(x)")
        self.db.cursor().execute("attach '%stestdb2?psow=0' as fred" % ("file:"+TESTFILEPREFIX,) )
        self.assertEqual("wal", self.db.cursor().execute("pragma fred.journal_mode=wal").fetchall()[0][0])
        expectdbname="fred"
        self.db.cursor().execute("create table fred.three(x)")

    def testAuthorizer(self):
        "Verify the authorizer works"
        retval=apsw.SQLITE_DENY
        def authorizer(operation, paramone, paramtwo, databasename, triggerorview):
            # we fail creates of tables starting with "private"
            if operation==apsw.SQLITE_CREATE_TABLE and paramone.startswith("private"):
                return retval
            return apsw.SQLITE_OK
        c=self.db.cursor()
        # this should succeed
        c.execute("create table privateone(x)")
        # this should fail
        self.assertRaises(TypeError, self.db.setauthorizer, 12) # must be callable
        self.db.setauthorizer(authorizer)
        for val in apsw.SQLITE_DENY, long(apsw.SQLITE_DENY), 0x800276889000212112:
            retval=val
            if val<100:
                self.assertRaises(apsw.AuthError, c.execute, "create table privatetwo(x)")
            else:
                self.assertRaises(OverflowError, c.execute, "create table privatetwo(x)")
        # this should succeed
        self.db.setauthorizer(None)
        c.execute("create table privatethree(x)")

        self.assertTableExists("privateone")
        self.assertTableNotExists("privatetwo")
        self.assertTableExists("privatethree")

        # error in callback
        def authorizer(operation, *args):
            if operation==apsw.SQLITE_CREATE_TABLE:
                1/0
            return apsw.SQLITE_OK
        self.db.setauthorizer(authorizer)
        self.assertRaises(ZeroDivisionError, c.execute, "create table shouldfail(x)")
        self.assertTableNotExists("shouldfail")

        # bad return type in callback
        def authorizer(operation, *args):
            return "a silly string"
        self.db.setauthorizer(authorizer)
        self.assertRaises(TypeError, c.execute, "create table shouldfail(x); select 3+5")
        self.db.setauthorizer(None) # otherwise next line will fail!
        self.assertTableNotExists("shouldfail")

        # back to normal
        self.db.setauthorizer(None)
        c.execute("create table shouldsucceed(x)")
        self.assertTableExists("shouldsucceed")

    def testExecTracing(self):
        "Verify tracing of executed statements and bindings"
        self.db.setexectrace(None)
        c=self.db.cursor()
        cmds=[] # this is maniulated in tracefunc
        def tracefunc(cursor, cmd, bindings):
            cmds.append( (cmd, bindings) )
            return True
        c.execute("create table one(x,y,z)")
        self.assertEqual(len(cmds),0)
        self.assertRaises(TypeError, c.setexectrace, 12) # must be callable
        self.assertRaises(TypeError, self.db.setexectrace, 12) # must be callable
        c.setexectrace(tracefunc)
        statements=[
            ("insert into one values(?,?,?)", (1,2,3)),
            ("insert into one values(:a,$b,$c)", {'a': 1, 'b': "string", 'c': None}),
            ]
        for cmd,values in statements:
            c.execute(cmd, values)
        self.assertEqual(cmds, statements)
        self.assertTrue(c.getexectrace() is tracefunc)
        c.setexectrace(None)
        self.assertTrue(c.getexectrace() is None)
        c.execute("create table bar(x,y,z)")
        # cmds should be unchanged
        self.assertEqual(cmds, statements)
        # tracefunc can abort execution
        count=next(c.execute("select count(*) from one"))[0]
        def tracefunc(cursor, cmd, bindings):
            return False # abort
        c.setexectrace(tracefunc)
        self.assertRaises(apsw.ExecTraceAbort, c.execute, "insert into one values(1,2,3)")
        # table should not have been modified
        c.setexectrace(None)
        self.assertEqual(count, next(c.execute("select count(*) from one"))[0])
        # error in tracefunc
        def tracefunc(cursor, cmd, bindings):
            1/0
        c.setexectrace(tracefunc)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into one values(1,2,3)")
        c.setexectrace(None)
        self.assertEqual(count, next(c.execute("select count(*) from one"))[0])
        # test across executemany and multiple statments
        counter=[0]
        def tracefunc(cursor, cmd, bindings):
            counter[0]=counter[0]+1
            return True
        c.setexectrace(tracefunc)
        c.execute("create table two(x);insert into two values(1); insert into two values(2); insert into two values(?); insert into two values(?)",
                  (3, 4))
        self.assertEqual(counter[0], 5)
        counter[0]=0
        c.executemany("insert into two values(?); insert into two values(?)", [[n,n+1] for n in range(5)])
        self.assertEqual(counter[0], 10)
        # error in func but only after a while
        c.execute("delete from two")
        counter[0]=0
        def tracefunc(cursor, cmd, bindings):
            counter[0]=counter[0]+1
            if counter[0]>3:
                1/0
            return True
        c.setexectrace(tracefunc)
        self.assertRaises(ZeroDivisionError, c.execute,
                          "insert into two values(1); insert into two values(2); insert into two values(?); insert into two values(?)",
                          (3, 4))
        self.assertEqual(counter[0], 4)
        c.setexectrace(None)
        # check the first statements got executed
        self.assertEqual(3, next(c.execute("select max(x) from two"))[0])
        # executemany
        def tracefunc(cursor, cmd, bindings):
            1/0
        c.setexectrace(tracefunc)
        self.assertRaises(ZeroDivisionError, c.executemany, "select ?", [(1,)])
        c.setexectrace(None)
        # tracefunc with wrong number of arguments
        def tracefunc(a,b,c,d,e,f):
            1/0
        c.setexectrace(tracefunc)
        self.assertRaises(TypeError, c.execute, "select max(x) from two")
        def tracefunc(*args):
            return BadIsTrue()
        c.setexectrace(tracefunc)
        self.assertRaises(ZeroDivisionError, c.execute, "select max(x) from two")
        # connection based tracing
        self.assertEqual( self.db.getexectrace(), None )
        traced=[False, False]
        def contrace(*args):
            traced[0]=True
            return True
        def curtrace(*args):
            traced[1]=True
            return True
        c.setexectrace(curtrace)
        c.execute("select 3")
        self.assertEqual( traced, [False, True] )
        traced=[False, False]
        self.db.setexectrace(contrace)
        c.execute("select 3")
        self.assertEqual( traced, [False, True] )
        traced=[False, False]
        c.setexectrace(None)
        c.execute("select 3")
        self.assertEqual( traced, [False, False] )
        traced=[False, False]
        self.db.cursor().execute("select 3")
        self.assertEqual( traced, [True, False] )
        self.assertEqual( self.db.getexectrace(), contrace )
        self.assertEqual( c.getexectrace(), None )
        self.assertEqual( self.db.cursor().getexectrace(), None )
        c.setexectrace(curtrace)
        self.assertEqual( c.getexectrace(), curtrace )

    def testRowTracing(self):
        "Verify row tracing"
        self.db.setrowtrace(None)
        c=self.db.cursor()
        c.execute("create table foo(x,y,z)")
        vals=(1,2,3)
        c.execute("insert into foo values(?,?,?)", vals)
        def tracefunc(cursor, row):
            return tuple([7 for i in row])
        # should get original row back
        self.assertEqual(next(c.execute("select * from foo")), vals)
        self.assertRaises(TypeError, c.setrowtrace, 12) # must be callable
        c.setrowtrace(tracefunc)
        self.assertTrue(c.getrowtrace() is tracefunc)
        # all values replaced with 7
        self.assertEqual(next(c.execute("select * from foo")), tuple([7]*len(vals)))
        def tracefunc(cursor, row):
            return (7,)
        # a single 7
        c.setrowtrace(tracefunc)
        self.assertEqual(next(c.execute("select * from foo")), (7,))
        # no alteration again
        c.setrowtrace(None)
        self.assertEqual(next(c.execute("select * from foo")), vals)
        # error in function
        def tracefunc(*result):
            1/0
        c.setrowtrace(tracefunc)
        try:
            for row in c.execute("select * from foo"):
                self.fail("Should have had exception")
                break
        except ZeroDivisionError:
            pass
        c.setrowtrace(None)
        self.assertEqual(next(c.execute("select * from foo")), vals)
        # returning null
        c.execute("create table bar(x)")
        c.executemany("insert into bar values(?)", [[x] for x in range(10)])
        counter=[0]
        def tracefunc(cursor, args):
            counter[0]=counter[0]+1
            if counter[0]%2:
                return None
            return args
        c.setrowtrace(tracefunc)
        countertoo=0
        for row in c.execute("select * from bar"):
            countertoo+=1
        c.setrowtrace(None)
        self.assertEqual(countertoo, 5) # half the rows should be skipped
        # connection based
        self.assertRaises(TypeError, self.db.setrowtrace, 12)
        self.assertEqual( self.db.getrowtrace(), None)
        traced=[False, False]
        def contrace(cursor, row):
            traced[0]=True
            return row
        def curtrace(cursor, row):
            traced[1]=True
            return row
        for row in c.execute("select 3,3"): pass
        self.assertEqual( traced, [False, False])
        traced=[False, False]
        self.db.setrowtrace(contrace)
        for row in self.db.cursor().execute("select 3,3"): pass
        self.assertEqual( traced, [True, False])
        traced=[False, False]
        c.setrowtrace(curtrace)
        for row in c.execute("select 3,3"): pass
        self.assertEqual( traced, [False, True])
        traced=[False, False]
        c.setrowtrace(None)
        for row in c.execute("select 3"): pass
        self.assertEqual( traced, [False, False])
        self.assertEqual( self.db.getrowtrace(), contrace)


    def testScalarFunctions(self):
        "Verify scalar functions"
        c=self.db.cursor()
        def ilove7(*args):
            return 7
        self.assertRaises(TypeError, self.db.createscalarfunction, "twelve", 12) # must be callable
        self.assertRaises(TypeError, self.db.createscalarfunction, "twelve", 12, 27, 28) # too many params
        try:
            self.db.createscalarfunction("twelve", ilove7, 900) # too many args
        except (apsw.SQLError, apsw.MisuseError):
            # https://sqlite.org/cvstrac/tktview?tn=3875
            pass
        # some unicode fun
        self.db.createscalarfunction, u(r"twelve\N{BLACK STAR}"), ilove7
        try:
            # SQLite happily registers the function, but you can't
            # call it
            self.assertEqual(c.execute("select "+u(r"twelve\N{BLACK STAR}")+"(3)").fetchall(),
                             [[7]])
        except apsw.SQLError:
            pass

        self.db.createscalarfunction("seven", ilove7)
        c.execute("create table foo(x,y,z)")
        for i in range(10):
            c.execute("insert into foo values(?,?,?)", (i,i,i))
        for i in range(10):
            self.assertEqual( (7,), next(c.execute("select seven(x,y,z) from foo where x=?", (i,))))
        # clear func
        self.assertRaises(apsw.BusyError, self.db.createscalarfunction,"seven", None) # active select above so no funcs can be changed
        for row in c.execute("select null"): pass # no active sql now
        self.db.createscalarfunction("seven", None)
        # function names are limited to 255 characters - SQLerror is the rather unintuitive error return
        try:
            self.db.createscalarfunction("a"*300, ilove7)
        except (apsw.SQLError, apsw.MisuseError):
            pass # see sqlite ticket #3875
        # have an error in a function
        def badfunc(*args):
            return 1/0
        self.db.createscalarfunction("badscalarfunc", badfunc)
        self.assertRaises(ZeroDivisionError, c.execute, "select badscalarfunc(*) from foo")
        # return non-allowed types
        for v in ({'a': 'dict'}, ['a', 'list'], self):
            def badtype(*args):
                return v
            self.db.createscalarfunction("badtype", badtype)
            self.assertRaises(TypeError, c.execute, "select badtype(*) from foo")
        # return non-unicode string
        def ilove8bit(*args):
            return "\x99\xaa\xbb\xcc"

        self.db.createscalarfunction("ilove8bit", ilove8bit)
        if not py3:
            self.assertRaises(UnicodeDecodeError, c.execute, "select ilove8bit(*) from foo")
        # coverage
        def bad(*args): 1/0
        self.db.createscalarfunction("bad", bad)
        self.assertRaises(ZeroDivisionError, c.execute, "select bad(3)+bad(4)")
        # turn a blob into a string to fail python utf8 conversion
        self.assertRaises(UnicodeDecodeError, c.execute, "select bad(cast (x'fffffcfb9208' as TEXT))")

        # register same named function taking different number of arguments
        for i in range(-1, 4):
            self.db.createscalarfunction("multi", lambda *args: len(args), i)
        gc.collect()
        for row in c.execute("select multi(), multi(1), multi(1,2), multi(1,2,3), multi(1,2,3,4), multi(1,2,3,4,5)"):
            self.assertEqual(row, (0, 1, 2, 3, 4, 5))

        # deterministic flag

        # check error handling
        self.assertRaises(TypeError, self.db.createscalarfunction, "twelve", deterministic="324")
        self.assertRaises(TypeError, self.db.createscalarfunction, "twelve", deterministic=324)

        # check it has an effect
        class Counter:  # on calling returns how many times this instance has been called
            num_calls=0
            def __call__(self):
                self.num_calls+=1
                return self.num_calls
        self.db.createscalarfunction("deterministic", Counter(), deterministic=True)
        self.db.createscalarfunction("nondeterministic", Counter(), deterministic=False)
        self.db.createscalarfunction("unspecdeterministic", Counter())

        self.assertEqual(c.execute("select deterministic()=deterministic()").fetchall()[0][0], 1)
        self.assertEqual(c.execute("select nondeterministic()=nondeterministic()").fetchall()[0][0], 0)
        self.assertEqual(c.execute("select unspecdeterministic()=unspecdeterministic()").fetchall()[0][0], 0)


    def testAggregateFunctions(self):
        "Verify aggregate functions"
        c=self.db.cursor()
        c.execute("create table foo(x,y,z)")
        # aggregate function
        class longest:
            def __init__(self):
                self.result=""

            def step(self, context, *args):
                for i in args:
                    if len(str(i))>len(self.result):
                        self.result=str(i)

            def final(self, context):
                return self.result

            def factory():
                v=longest()
                return None,v.step,v.final
            factory=staticmethod(factory)

        self.assertRaises(TypeError, self.db.createaggregatefunction,True, True, True, True) # wrong number/type of params
        self.assertRaises(TypeError, self.db.createaggregatefunction,"twelve", 12) # must be callable
        try:
            self.db.createaggregatefunction("twelve", longest.factory, 923) # max args is 127
        except (apsw.SQLError, apsw.MisuseError):
            # used to be SQLerror then changed https://sqlite.org/cvstrac/tktview?tn=3875
            pass
        self.assertRaises(TypeError, self.db.createaggregatefunction, u(r"twelve\N{BLACK STAR}"), 12) # must be ascii
        self.db.createaggregatefunction("twelve", None)
        self.db.createaggregatefunction("longest", longest.factory)

        vals=(
            ("kjfhgk","gkjlfdhgjkhsdfkjg","gklsdfjgkldfjhnbnvc,mnxb,mnxcv,mbncv,mnbm,ncvx,mbncv,mxnbcv,"), # last one is deliberately the longest
            ("gdfklhj",":gjkhgfdsgfd","gjkfhgjkhdfkjh"),
            ("gdfjkhg","gkjlfd",""),
            (1,2,30),
           )

        for v in vals:
            c.execute("insert into foo values(?,?,?)", v)

        v=next(c.execute("select longest(x,y,z) from foo"))[0]
        self.assertEqual(v, vals[0][2])

        # SQLite doesn't allow step functions to return an error, so we have to defer to the final
        def badfactory():
            def badfunc(*args):
                1/0
            def final(*args):
                self.fail("This should not be executed")
                return 1
            return None,badfunc,final

        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(ZeroDivisionError, c.execute, "select badfunc(x) from foo")

        # error in final
        def badfactory():
            def badfunc(*args):
                pass
            def final(*args):
                1/0
            return None,badfunc,final
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(ZeroDivisionError, c.execute, "select badfunc(x) from foo")

        # error in step and final
        def badfactory():
            def badfunc(*args):
                1/0
            def final(*args):
                raise ImportError() # zero div from above is what should be returned
            return None,badfunc,final
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(ZeroDivisionError, c.execute, "select badfunc(x) from foo")

        # bad return from factory
        def badfactory():
            def badfunc(*args):
                pass
            def final(*args):
                return 0
            return {}
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(TypeError, c.execute, "select badfunc(x) from foo")

        # incorrect number of items returned
        def badfactory():
            def badfunc(*args):
                pass
            def final(*args):
                return 0
            return (None, badfunc, final, badfactory)
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(TypeError, c.execute, "select badfunc(x) from foo")

        # step not callable
        def badfactory():
            def badfunc(*args):
                pass
            def final(*args):
                return 0
            return (None, True, final )
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(TypeError, c.execute, "select badfunc(x) from foo")

        # final not callable
        def badfactory():
            def badfunc(*args):
                pass
            def final(*args):
                return 0
            return (None, badfunc, True )
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(TypeError, c.execute, "select badfunc(x) from foo")

        # error in factory method
        def badfactory():
            1/0
        self.db.createaggregatefunction("badfunc", badfactory)
        self.assertRaises(ZeroDivisionError, c.execute, "select badfunc(x) from foo")


    def testCollation(self):
        "Verify collations"
        # create a whole bunch to check they are freed
        for i in range(1024):
            self.db.createcollation("x"*i, lambda x,y: i)
        for ii in range(1024):
            self.db.createcollation("x"*ii, lambda x,y: ii)

        c=self.db.cursor()
        def strnumcollate(s1, s2):
            "return -1 if s1<s2, +1 if s1>s2 else 0.  Items are string head and numeric tail"
            # split values into two parts - the head and the numeric tail
            values=[s1,s2]
            for vn,v in enumerate(values):
                for i in range(len(v),0,-1):
                    if v[i-1] not in "01234567890":
                        break
                try:
                    v=v[:i],int(v[i:])
                except ValueError:
                    v=v[:i],None
                values[vn]=v
            # compare
            if values[0]<values[1]:
                return -1 # return an int
            if values[0]>values[1]:
                return long(1) # and a long
            return 0

        self.assertRaises(TypeError, self.db.createcollation, "twelve", strnumcollate, 12) # wrong # params
        self.assertRaises(TypeError, self.db.createcollation, "twelve", 12) # must be callable
        self.db.createcollation("strnum", strnumcollate)
        c.execute("create table foo(x)")
        # adding this unicode in front improves coverage
        uni=u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}")
        vals=(uni+"file1", uni+"file7", uni+"file9", uni+"file17", uni+"file20")
        valsrev=list(vals)
        valsrev.reverse() # put them into table in reverse order
        valsrev=valsrev[1:]+valsrev[:1] # except one out of order
        c.executemany("insert into foo values(?)", [(x,) for x in valsrev])
        for i,row in enumerate(c.execute("select x from foo order by x collate strnum")):
            self.assertEqual(vals[i], row[0])

        # collation function with an error
        def collerror(*args):
            return 1/0
        self.db.createcollation("collerror", collerror)
        self.assertRaises(ZeroDivisionError, c.execute, "select x from foo order by x collate collerror")

        # collation function that returns bad value
        def collerror(*args):
            return {}
        self.db.createcollation("collbadtype", collerror)
        self.assertRaises(TypeError, c.execute, "select x from foo order by x collate collbadtype")

        # get error when registering
        c.execute("select x from foo order by x collate strnum") # nb we don't read so cursor is still active
        self.assertRaises(apsw.BusyError, self.db.createcollation, "strnum", strnumcollate)

        # unregister
        for row in c: pass
        self.db.createcollation("strnum", None)
        # check it really has gone
        try:
            c.execute("select x from foo order by x collate strnum")
        except apsw.SQLError:
            pass
        # check statement still works
        for _ in c.execute("select x from foo"): pass

        # collation needed testing
        self.assertRaises(TypeError, self.db.collationneeded, 12)
        def cn1(): pass
        def cn2(x, y): 1/0
        def cn3(x, y):
            self.assertTrue(x is self.db)
            self.assertEqual(y, "strnum")
            self.db.createcollation("strnum", strnumcollate)

        self.db.collationneeded(cn1)
        try:
            for _ in c.execute("select x from foo order by x collate strnum"): pass
        except TypeError:
            pass
        self.db.collationneeded(cn2)
        try:
            for _ in c.execute("select x from foo order by x collate strnum"): pass
        except ZeroDivisionError:
            pass
        self.db.collationneeded(cn3)
        for _ in c.execute("select x from foo order by x collate strnum"): pass
        self.db.collationneeded(None)
        self.db.createcollation("strnum", None)

        # check it really has gone
        try:
            c.execute("select x from foo order by x collate strnum")
        except apsw.SQLError:
            pass


    def testProgressHandler(self):
        "Verify progress handler"
        c=self.db.cursor()
        phcalledcount=[0]
        def ph():
            phcalledcount[0]=phcalledcount[0]+1
            return 0

        # make 400 rows of random numbers
        c.execute("begin ; create table foo(x)")
        c.executemany("insert into foo values(?)", randomintegers(400))
        c.execute("commit")

        self.assertRaises(TypeError, self.db.setprogresshandler, 12) # must be callable
        self.assertRaises(TypeError, self.db.setprogresshandler, ph, "foo") # second param is steps
        self.db.setprogresshandler(ph, -17) # SQLite doesn't complain about negative numbers
        self.db.setprogresshandler(ph, 20)
        next(c.execute("select max(x) from foo"))

        self.assertNotEqual(phcalledcount[0], 0)
        saved=phcalledcount[0]

        # put an error in the progress handler
        def ph(): return 1/0
        self.db.setprogresshandler(ph, 1)
        self.assertRaises(ZeroDivisionError, c.execute, "update foo set x=-10")
        self.db.setprogresshandler(None) # clear ph so next line runs
        # none should have taken
        self.assertEqual(0, next(c.execute("select count(*) from foo where x=-10"))[0])
        # and previous ph should not have been called
        self.assertEqual(saved, phcalledcount[0])
        def ph():
            return BadIsTrue()
        self.db.setprogresshandler(ph, 1)
        self.assertRaises(ZeroDivisionError, c.execute, "update foo set x=-10")

    def testChanges(self):
        "Verify reporting of changes"
        c=self.db.cursor()
        c.execute("create table foo (x);begin")
        for i in range(100):
            c.execute("insert into foo values(?)", (i+1000,))
        c.execute("commit")
        c.execute("update foo set x=0 where x>=1000")
        self.assertEqual(100, self.db.changes())
        c.execute("begin")
        for i in range(100):
            c.execute("insert into foo values(?)", (i+1000,))
        c.execute("commit")
        self.assertEqual(300, self.db.totalchanges())

    def testLastInsertRowId(self):
        "Check last insert row id"
        c=self.db.cursor()
        c.execute("create table foo (x integer primary key)")
        for i in range(10):
            c.execute("insert into foo values(?)", (i,))
            self.assertEqual(i, self.db.last_insert_rowid())
        # get a 64 bit value
        v=2**40
        c.execute("insert into foo values(?)", (v,))
        self.assertEqual(v, self.db.last_insert_rowid())

    def testComplete(self):
        "Completeness of SQL statement checking"
        # the actual underlying routine just checks that there is a semi-colon
        # at the end, not inside any quotes etc
        self.assertEqual(False, apsw.complete("select * from"))
        self.assertEqual(False, apsw.complete("select * from \";\""))
        self.assertEqual(False, apsw.complete("select * from \";"))
        self.assertEqual(True, apsw.complete("select * from foo; select *;"))
        self.assertEqual(False, apsw.complete("select * from foo where x=1"))
        self.assertEqual(True, apsw.complete("select * from foo;"))
        self.assertEqual(True, apsw.complete(u(r"select '\u9494\ua7a7';")))
        if not py3:
            self.assertRaises(UnicodeDecodeError, apsw.complete, "select '\x94\xa7';")
        self.assertRaises(TypeError, apsw.complete, 12) # wrong type
        self.assertRaises(TypeError, apsw.complete)     # not enough args
        self.assertRaises(TypeError, apsw.complete, "foo", "bar") # too many args

    def testBusyHandling(self):
        "Verify busy handling"
        c=self.db.cursor()
        c.execute("create table foo(x); begin")
        c.executemany("insert into foo values(?)", randomintegers(400))
        c.execute("commit")
        # verify it is blocked
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        c2=db2.cursor()
        c2.execute("begin exclusive")
        try:
            self.assertRaises(apsw.BusyError, c.execute, "begin immediate ; select * from foo")
        finally:
            del c2
            db2.close()
            del db2

        # close and reopen databases - sqlite will return Busy immediately to a connection
        # it previously returned busy to
        del c
        self.db.close()
        del self.db
        self.db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        c=self.db.cursor()
        c2=db2.cursor()

        # Put in busy handler
        bhcalled=[0]
        def bh(*args):
            bhcalled[0]=bhcalled[0]+1
            if bhcalled[0]==4:
                return False
            return True
        self.assertRaises(TypeError, db2.setbusyhandler, 12) # must be callable
        self.assertRaises(TypeError, db2.setbusytimeout, "12") # must be int
        db2.setbusytimeout(-77)  # SQLite doesn't complain about negative numbers, but if it ever does this will catch it
        self.assertRaises(TypeError, db2.setbusytimeout, 77,88) # too many args
        self.db.setbusyhandler(bh)

        c2.execute("begin exclusive")

        try:
            for row in c.execute("begin immediate ; select * from foo"):
                self.fail("Transaction wasn't exclusive")
        except apsw.BusyError:
            pass
        self.assertEqual(bhcalled[0], 4)

        # Close and reopen again
        del c
        del c2
        db2.close()
        self.db.close()
        del db2
        del self.db
        self.db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        c=self.db.cursor()
        c2=db2.cursor()

        # Put in busy timeout
        TIMEOUT=3 # seconds, must be integer as sqlite can round down to nearest second anyway
        c2.execute("begin exclusive")
        self.assertRaises(TypeError, self.db.setbusyhandler, "foo")
        self.db.setbusytimeout(int(TIMEOUT*1000))
        b4=time.time()
        try:
            c.execute("begin immediate ; select * from foo")
        except apsw.BusyError:
            pass
        after=time.time()
        took=after-b4
        # this sometimes fails in virtualized environments due to time
        # going backwards or not going forwards consistently.
        if took+1<TIMEOUT:
            write("Timeout was %d seconds but only %f seconds elapsed!" % (TIMEOUT, took))
            self.assertTrue(took>=TIMEOUT)

        # check clearing of handler
        c2.execute("rollback")
        self.db.setbusyhandler(None)
        b4=time.time()
        c2.execute("begin exclusive")
        try:
            c.execute("begin immediate ; select * from foo")
        except apsw.BusyError:
            pass
        after=time.time()
        self.assertTrue(after-b4<TIMEOUT)

        # Close and reopen again
        del c
        del c2
        db2.close()
        self.db.close()
        del db2
        del self.db
        self.db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        c=self.db.cursor()
        c2=db2.cursor()

        # error in busyhandler
        def bh(*args):
            1/0
        c2.execute("begin exclusive")
        self.db.setbusyhandler(bh)
        self.assertRaises(ZeroDivisionError, c.execute, "begin immediate ; select * from foo")
        del c
        del c2
        db2.close()

        def bh(*args):
            return BadIsTrue()
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        c=self.db.cursor()
        c2=db2.cursor()
        c2.execute("begin exclusive")
        self.db.setbusyhandler(bh)
        self.assertRaises(ZeroDivisionError, c.execute, "begin immediate ; select * from foo")
        del c
        del c2
        db2.close()

    def testBusyHandling2(self):
        "Another busy handling test"

        # Based on an issue in 3.3.10 and before
        con2=apsw.Connection(TESTFILEPREFIX+"testdb")
        cur=self.db.cursor()
        cur2=con2.cursor()
        cur.execute("create table test(x,y)")
        cur.execute("begin")
        cur.execute("insert into test values(123,'abc')")
        self.assertRaises(apsw.BusyError, cur2.execute, "insert into test values(456, 'def')")
        cur.execute("commit")
        self.assertEqual(1, next(cur2.execute("select count(*) from test where x=123"))[0])
        con2.close()

    def testInterruptHandling(self):
        "Verify interrupt function"
        # this is tested by having a user defined function make the interrupt
        c=self.db.cursor()
        c.execute("create table foo(x);begin")
        c.executemany("insert into foo values(?)", randomintegers(400))
        c.execute("commit")
        def ih(*args):
            self.db.interrupt()
            return 7
        self.db.createscalarfunction("seven", ih)
        try:
            for row in c.execute("select seven(x) from foo"):
                pass
        except apsw.InterruptError:
            pass
        # ::TODO:: raise the interrupt from another thread

    def testCommitHook(self):
        "Verify commit hooks"
        c=self.db.cursor()
        c.execute("create table foo(x)")
        c.executemany("insert into foo values(?)", randomintegers(10))
        chcalled=[0]
        def ch():
            chcalled[0]=chcalled[0]+1
            if chcalled[0]==4:
                return 1 # abort
            return 0 # continue
        self.assertRaises(TypeError, self.db.setcommithook, 12)  # not callable
        self.db.setcommithook(ch)
        self.assertRaises(apsw.ConstraintError, c.executemany, "insert into foo values(?)", randomintegers(10))
        self.assertEqual(4, chcalled[0])
        self.db.setcommithook(None)
        def ch():
            chcalled[0]=99
            return 1
        self.db.setcommithook(ch)
        self.assertRaises(apsw.ConstraintError, c.executemany, "insert into foo values(?)", randomintegers(10))
        # verify it was the second one that was called
        self.assertEqual(99, chcalled[0])
        # error in commit hook
        def ch():
            return 1/0
        self.db.setcommithook(ch)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into foo values(?)", (1,))
        def ch():
            return BadIsTrue()
        self.db.setcommithook(ch)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into foo values(?)", (1,))


    def testRollbackHook(self):
        "Verify rollback hooks"
        c=self.db.cursor()
        c.execute("create table foo(x)")
        rhcalled=[0]
        def rh():
            rhcalled[0]=rhcalled[0]+1
            return 1
        self.assertRaises(TypeError, self.db.setrollbackhook, 12) # must be callable
        self.db.setrollbackhook(rh)
        c.execute("begin ; insert into foo values(10); rollback")
        self.assertEqual(1, rhcalled[0])
        self.db.setrollbackhook(None)
        c.execute("begin ; insert into foo values(10); rollback")
        self.assertEqual(1, rhcalled[0])
        def rh():
            1/0
        self.db.setrollbackhook(rh)
        # SQLite doesn't allow reporting an error from a rollback hook, so it will be seen
        # in the next command (eg the select in this case)
        self.assertRaises(ZeroDivisionError, c.execute, "begin ; insert into foo values(10); rollback; select * from foo")
        # check cursor still works
        for row in c.execute("select * from foo"):
            pass

    def testUpdateHook(self):
        "Verify update hooks"
        c=self.db.cursor()
        c.execute("create table foo(x integer primary key, y)")
        uhcalled=[]
        def uh(type, databasename, tablename, rowid):
            uhcalled.append( (type, databasename, tablename, rowid) )
        self.assertRaises(TypeError, self.db.setupdatehook, 12) # must be callable
        self.db.setupdatehook(uh)
        statements=(
            ("insert into foo values(3,4)", (apsw.SQLITE_INSERT, 3) ),
            ("insert into foo values(30,40)", (apsw.SQLITE_INSERT, 30) ),
            ("update foo set y=47 where x=3", (apsw.SQLITE_UPDATE, 3), ),
            ("delete from foo where y=47", (apsw.SQLITE_DELETE, 3), ),
            )
        for sql,res in statements:
            c.execute(sql)
        results=[(type, "main", "foo", rowid) for sql,(type,rowid) in statements]
        self.assertEqual(uhcalled, results)
        self.db.setupdatehook(None)
        c.execute("insert into foo values(99,99)")
        self.assertEqual(len(uhcalled), len(statements)) # length should have remained the same
        def uh(*args):
            1/0
        self.db.setupdatehook(uh)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into foo values(100,100)")
        self.db.setupdatehook(None)
        # improve code coverage
        c.execute("create table bar(x,y); insert into bar values(1,2); insert into bar values(3,4)")
        def uh(*args):
            1/0
        self.db.setupdatehook(uh)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into foo select * from bar")
        self.db.setupdatehook(None)

        # check cursor still works
        c.execute("insert into foo values(1000,1000)")
        self.assertEqual(1, next(c.execute("select count(*) from foo where x=1000"))[0])

    def testProfile(self):
        "Verify profiling"
        # we do the test by looking for the maximum of PROFILESTEPS random
        # numbers with an index present and without.  The former
        # should be way quicker.
        c=self.db.cursor()
        c.execute("create table foo(x); begin")
        c.executemany("insert into foo values(?)", randomintegers(PROFILESTEPS))
        profileinfo=[]
        def profile(statement, timing):
            profileinfo.append( (statement, timing) )
        c.execute("commit; create index foo_x on foo(x)")
        self.assertRaises(TypeError, self.db.setprofile, 12) # must be callable
        self.db.setprofile(profile)
        for val1 in c.execute("select max(x) from foo"): pass # profile is only run when results are exhausted
        self.db.setprofile(None)
        c.execute("drop index foo_x")
        self.db.setprofile(profile)
        for val2 in c.execute("select max(x) from foo"): pass
        self.assertEqual(val1, val2)
        self.assertTrue(len(profileinfo)>=2) # see SQLite ticket 2157
        self.assertEqual(profileinfo[0][0], profileinfo[-1][0])
        self.assertEqual("select max(x) from foo", profileinfo[0][0])
        self.assertEqual("select max(x) from foo", profileinfo[-1][0])
        # the query using the index should take way less time
        self.assertTrue(profileinfo[0][1]<profileinfo[-1][1])
        def profile(*args):
            1/0
        self.db.setprofile(profile)
        self.assertRaises(ZeroDivisionError, c.execute, "create table bar(y)")
        # coverage
        wasrun=[False]
        def profile(*args):
            wasrun[0]=True
        def uh(*args): 1/0
        self.db.setprofile(profile)
        self.db.setupdatehook(uh)
        self.assertRaises(ZeroDivisionError, c.execute, "insert into foo values(3)")
        self.assertEqual(wasrun[0], False)
        self.db.setprofile(None)
        self.db.setupdatehook(None)

    def testThreading(self):
        "Verify threading behaviour"
        # We used to require all operations on a connection happen in
        # the same thread.  Now they can happen in any thread, so we
        # ensure that inuse errors are detected by doing a long
        # running operation in one thread.
        c=self.db.cursor()
        c.execute("create table foo(x);begin;")
        c.executemany("insert into foo values(?)", randomintegers(10000))
        c.execute("commit")

        vals={"stop": False,
              "raised": False}
        def wt():
            try:
                while not vals["stop"]:
                    c.execute("select min(max(x-1+x),min(x-1+x)) from foo")
            except apsw.ThreadingViolationError:
                vals["raised"]=True
                vals["stop"]=True

        t=ThreadRunner(wt)
        t.start()
        # ensure thread t has started
        time.sleep(0.1)
        b4=time.time()
        # try to get a threadingviolation for 30 seconds
        try:
            try:
                while not vals["stop"] and time.time()-b4<30:
                    c.execute("select * from foo")
            except apsw.ThreadingViolationError:
                vals["stop"]=True
                vals["raised"]=True
        finally:
            vals["stop"]=True
        t.go()
        self.assertEqual(vals["raised"], True)

    def testStringsWithNulls(self):
        "Verify that strings with nulls in them are handled correctly"

        c=self.db.cursor()
        c.execute("create table foo(row,str)")
        vals=("a simple string",
              "a simple string\0with a null",
              "a string\0with two\0nulls",
              "or even a \0\0\0\0\0\0sequence\0\0\0\0\of them",
              u(r"a \u1234 unicode \ufe54 string \u0089"),
              u(r"a \u1234 unicode \ufe54 string \u0089\0and some text"),
              u(r"\N{BLACK STAR} \N{WHITE STAR} \N{LIGHTNING} \N{COMET}\0more\0than you\0can handle"),
              u(r"\N{BLACK STAR} \N{WHITE STAR} \N{LIGHTNING} \N{COMET}\0\0\0\0\0sequences\0\0\0of them"))

        vals=vals+(
            "a simple string\0",
            u(r"a \u1234 unicode \ufe54 string \u0089\0"),
            )

        for i,v in enumerate(vals):
            c.execute("insert into foo values(?,?)", (i, v))

        if not py3:
            self.assertRaises(UnicodeDecodeError, c.execute, "insert into foo values(9000,?)", ("a simple string\0with a null and \xfe\xfb\x80\x92",))

        # add function to test conversion back as well
        def snap(*args):
            return args[0]
        self.db.createscalarfunction("snap", snap)

        # now see what we got out
        count=0
        for row,v,fv in c.execute("select row,str,snap(str) from foo"):
            count+=1
            self.assertEqual(vals[row], v)
            self.assertEqual(vals[row], fv)
        self.assertEqual(count, len(vals))

        # check execute
        for v in vals:
            self.assertEqual(v, next(c.execute("select ?", (v,)))[0])
            # nulls not allowed in main query string, so lets check the other bits (unicode etc)
            v2=v.replace("\0", " zero ")
            self.assertEqual(v2, next(c.execute("select '%s'" % (v2,)))[0])

        # ::TODO:: check collations

    def testSharedCache(self):
        "Verify setting of shared cache"

        # check parameters - wrong # or type of args
        self.assertRaises(TypeError, apsw.enablesharedcache)
        self.assertRaises(TypeError, apsw.enablesharedcache, "foo")
        self.assertRaises(TypeError, apsw.enablesharedcache, True, None)

        # the setting can be changed at almost any time
        apsw.enablesharedcache(True)
        apsw.enablesharedcache(False)

    # A check that various extensions (such as fts3, rtree, icu)
    # actually work.  We don't know if they were supposed to be
    # compiled in or not so the assumption is that they aren't.
    # However setup.py is being run then it sets environment variables
    # saying the extensions *must* be present if they were enabled.
    # See https://github.com/rogerbinns/apsw/issues/55 for what
    # led to this.
    def checkOptionalExtension(self, name, testquery):
        try:
            present=False
            apsw.Connection(":memory:").cursor().execute(testquery)
            present=True
        except apsw.Error:
            pass
        if "APSW_TEST_"+name.upper() in os.environ:
            self.assertEqual(present, True)
        return present

    def testFTS3Extension(self):
        "Check FTS3 extension (if present)"
        if not self.checkOptionalExtension("fts3", "create virtual table foo using fts3()"):
            return
        c=self.db.cursor()
        data={
            'cake': 'flour, eggs, milk',
            'bbq ribs': 'ribs, hot sauce',
            'mayo': 'oil, Eggs',
            'glue': 'Egg',
            'salmon': 'Fish',
            'burger': 'Mechanically recovered meat',
            # From https://sqlite.org/cvstrac/wiki?p=FtsUsage
            'broccoli stew': 'broccoli peppers cheese tomatoes',
            'pumpkin stew': 'pumpkin onions garlic celery',
            'broccoli pie': 'broccoli cheese onions flour',
            'pumpkin pie': 'pumpkin sugar flour butter'
            }

        c.execute("create virtual table test using fts3(name, ingredients)")
        c.executemany("insert into test values(?,?)", data.items())

        def check(pattern, expectednames):
            names=[n[0] for n in c.execute("select name from test where ingredients match ?", (pattern,))]
            names.sort()
            expectednames=list(expectednames)
            expectednames.sort()
            self.assertEqual(names, expectednames)

        check('onions cheese', ['broccoli pie'])
        check('eggs OR oil', ['cake', 'mayo'])
        check('"pumpkin onions"', ['pumpkin stew'])

    def testRTreeExtension(self):
        "Check RTree extension if present"
        if not self.checkOptionalExtension("rtree", "create virtual table foo using rtree(one, two, three, four, five)"):
            return
        c=self.db.cursor()
        data=(
            (1, 2, 3, 4),
            (5.1, 6, 7.2, 8),
            (1, 4, 9, 12),
            (77, 77.1, 3, 9),
            )
        c.execute("create virtual table test using rtree(ii, x1, x2, y1, y2)")
        for i,row in enumerate(data):
            c.execute("insert into test values(?,?,?,?,?)", (i, row[0], row[1], row[2], row[3]))

        def check(pattern, expectedrows):
            rows=[n[0] for n in c.execute("select ii from test where "+pattern)]
            rows.sort()
            expectedrows=list(expectedrows)
            expectedrows.sort()
            self.assertEqual(rows, expectedrows)

        check("x1>2 AND x2<7 AND y1>17.2 AND y2<=8", [])
        check("x1>5 AND x2<=6 AND y1>-11 AND y2<=8", [1])

    def testICUExtension(self):
        "Check ICU extension if present"
        if not self.checkOptionalExtension("icu", "select lower('I', 'tr_tr')"):
            return

        c=self.db.cursor()
        # we compare SQLite standard vs icu
        def check(text, locale, func="lower", equal=False):
            q="select "+func+"(?%s)"
            sqlite=c.execute(q % ("",), (text,)).fetchall()
            icu=c.execute(q % (",'"+locale+"'",), (text,)).fetchall()
            if equal:
                self.assertEqual(sqlite, icu)
            else:
                self.assertNotEqual(sqlite, icu)

        check("I", "tr_tr")
        check("I", "en_us", equal=True)

    def testTracebacks(self):
        "Verify augmented tracebacks"
        return
        def badfunc(*args):
            1/0
        self.db.createscalarfunction("badfunc", badfunc)
        try:
            c=self.db.cursor()
            c.execute("select badfunc()")
            self.fail("Exception should have occurred")
        except ZeroDivisionError:
            tb=sys.exc_info()[2]
            traceback.print_tb(tb)
            del tb
        except:
            self.fail("Wrong exception type")

    def testLoadExtension(self):
        "Check loading of extensions"
        # unicode issues
        if not py3:
            self.assertRaises(UnicodeDecodeError, self.db.loadextension, "\xa7\x94")
        # they need to be enabled first (off by default)
        self.assertRaises(apsw.ExtensionLoadingError, self.db.loadextension, LOADEXTENSIONFILENAME)
        self.db.enableloadextension(False)
        self.assertRaises(ZeroDivisionError, self.db.enableloadextension, BadIsTrue())
        # should still be disabled
        self.assertRaises(apsw.ExtensionLoadingError, self.db.loadextension, LOADEXTENSIONFILENAME)
        self.db.enableloadextension(True)
        # make sure it checks args
        self.assertRaises(TypeError, self.db.loadextension)
        self.assertRaises(TypeError, self.db.loadextension, 12)
        self.assertRaises(TypeError, self.db.loadextension, "foo", 12)
        self.assertRaises(TypeError, self.db.loadextension, "foo", "bar", 12)
        self.db.loadextension(LOADEXTENSIONFILENAME)
        c=self.db.cursor()
        self.assertEqual(1, next(c.execute("select half(2)"))[0])
        # second entry point hasn't been called yet
        self.assertRaises(apsw.SQLError, c.execute, "select doubleup(2)")
        # load using other entry point
        self.assertRaises(apsw.ExtensionLoadingError, self.db.loadextension, LOADEXTENSIONFILENAME, "doesntexist")
        self.db.loadextension(LOADEXTENSIONFILENAME, "alternate_sqlite3_extension_init")
        self.assertEqual(4, next(c.execute("select doubleup(2)"))[0])


    def testMakeSqliteMsgFromException(self):
        "Test C function that converts exception into SQLite error code"
        class Source:
            def Create1(self, *args):
                e=apsw.IOError()
                e.extendedresult=apsw.SQLITE_IOERR_ACCESS
                raise e

            def Create2(self, *args):
                e=apsw.IOError()
                e.extendedresult=long(apsw.SQLITE_IOERR_ACCESS)
                raise e

            def Create3(self, *args):
                e=apsw.IOError()
                e.extendedresult=(long("0x80")<<32)+apsw.SQLITE_IOERR_ACCESS # bigger than 32 bits
                raise e

        if not hasattr(self.db, "createmodule"): return
        self.db.createmodule("foo", Source())
        for i in "1", "2", "3":
            Source.Create=getattr(Source, "Create"+i)
            try:
                self.db.cursor().execute("create virtual table vt using foo()")
                1/0
            except:
                klass,value,tb=sys.exc_info()
            # check types and values
            if i=="3":
                self.assertEqual(klass, ValueError)
                continue
            self.assertEqual(klass, apsw.IOError)
            self.assertTrue(isinstance(value, apsw.IOError))
            # python 2.3 totally messes up on long<->int and signed conversions causing the test to fail
            # but the code is fine - so just ignore rest of test for py2.3
            if sys.version_info<(2,4):
                return

            self.assertEqual(value.extendedresult& ((long(0xffff)<<16)|long(0xffff)), apsw.SQLITE_IOERR_ACCESS)

    def testVtables(self):
        "Test virtual table functionality"

        data=( # row 0 is headers, column 0 is rowid
            ( "rowid",     "name",    "number", "item",          "description"),
            ( 1,           "Joe Smith",    1.1, u(r"\u00f6\u1234"), "foo"),
            ( 6000000000,  "Road Runner", -7.3, u(r"\u00f6\u1235"), "foo"),
            ( 77,          "Fred",           0, u(r"\u00f6\u1236"), "foo"),
            )

        dataschema="create table this_should_be_ignored"+str(data[0][1:])
        # a query that will get constraints on every column
        allconstraints="select rowid,* from foo where rowid>-1000 and name>='A' and number<=12.4 and item>'A' and description=='foo' order by item"
        allconstraintsl=[(-1, apsw.SQLITE_INDEX_CONSTRAINT_GT), # rowid >
                         ( 0, apsw.SQLITE_INDEX_CONSTRAINT_GE), # name >=
                         ( 1, apsw.SQLITE_INDEX_CONSTRAINT_LE), # number <=
                         ( 2, apsw.SQLITE_INDEX_CONSTRAINT_GT), # item >
                         ( 3, apsw.SQLITE_INDEX_CONSTRAINT_EQ), # description ==
                         ]


        for i in range(20):
            self.db.createmodule("x"*i, lambda x: i)
        for ii in range(20):
            # SQLite 3.7.13 change - can't register same names
            self.assertRaises(apsw.MisuseError, self.db.createmodule, "x"*ii, lambda x: ii)

        # If shared cache is enabled then vtable creation is supposed to fail
        # See https://sqlite.org/cvstrac/tktview?tn=3144
        try:
            apsw.enablesharedcache(True)
            db=apsw.Connection(TESTFILEPREFIX+"testdb2")
            db.createmodule("y", lambda x: 2)
        finally:
            apsw.enablesharedcache(False)

        # The testing uses a different module name each time.  SQLite
        # doc doesn't define the semantics if a 2nd module is
        # registered with the same name as an existing one and I was
        # getting coredumps.  It looks like issues inside SQLite.

        cur=self.db.cursor()
        # should fail since module isn't registered
        self.assertRaises(apsw.SQLError, cur.execute, "create virtual table vt using testmod(x,y,z)")
        # wrong args
        self.assertRaises(TypeError, self.db.createmodule, 1,2,3)
        # give a bad object
        self.db.createmodule("testmod", 12) # next line fails due to lack of Create method
        self.assertRaises(AttributeError, cur.execute, "create virtual table xyzzy using testmod(x,y,z)")

        class Source:
            def __init__(self, *expectargs):
                self.expectargs=expectargs

            def Create(self, *args): # db, modname, dbname, tablename, args
                if self.expectargs!=args[1:]:
                    raise ValueError("Create arguments are not correct.  Expected "+str(self.expectargs)+" but got "+str(args[1:]))
                1/0

            def CreateErrorCode(self, *args):
                # This makes sure that sqlite error codes happen.  The coverage checker
                # is what verifies the code actually works.
                raise apsw.BusyError("foo")

            def CreateUnicodeException(self, *args):
                raise Exception(u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}\N{LATIN SMALL LETTER A WITH TILDE}\N{LATIN SMALL LETTER O WITH DIAERESIS}"))

            def CreateBadSchemaType(self, *args):
                return 12, None

            def CreateBadSchema(self, *args):
                return "this isn't remotely valid sql", None

            def CreateWrongNumReturns(self, *args):
                return "way","too","many","items",3

            def CreateBadSequence(self, *args):
                class badseq(object):
                    def __getitem__(self, which):
                        if which!=0:
                            1/0
                        return 12

                    def __len__(self):
                        return 2
                return badseq()

        # check Create does the right thing - we don't include db since it creates a circular reference
        self.db.createmodule("testmod1", Source("testmod1", "main", "xyzzy", "1", '"one"'))
        self.assertRaises(ZeroDivisionError, cur.execute, 'create virtual table xyzzy using testmod1(1,"one")')
        # unicode
        uni=u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}\N{LATIN SMALL LETTER A WITH TILDE}\N{LATIN SMALL LETTER O WITH DIAERESIS}")
        self.db.createmodule("testmod1dash1", Source("testmod1dash1", "main", uni, "1", '"'+uni+'"'))
        self.assertRaises(ZeroDivisionError, cur.execute, u('create virtual table %s using testmod1dash1(1,"%s")') % (uni, uni))
        Source.Create=Source.CreateErrorCode
        self.assertRaises(apsw.BusyError, cur.execute, 'create virtual table xyzzz using testmod1(2, "two")')
        Source.Create=Source.CreateUnicodeException
        self.assertRaises(Exception, cur.execute, 'create virtual table xyzzz using testmod1(2, "two")')
        Source.Create=Source.CreateBadSchemaType
        self.assertRaises(TypeError, cur.execute, 'create virtual table xyzzz using testmod1(2, "two")')
        Source.Create=Source.CreateBadSchema
        self.assertRaises(apsw.SQLError, cur.execute, 'create virtual table xyzzz2 using testmod1(2, "two")')
        Source.Create=Source.CreateWrongNumReturns
        self.assertRaises(TypeError, cur.execute, 'create virtual table xyzzz2 using testmod1(2, "two")')
        Source.Create=Source.CreateBadSequence
        self.assertRaises(ZeroDivisionError, cur.execute, 'create virtual table xyzzz2 using testmod1(2, "two")')

        # a good version of Source
        class Source:
            def Create(self, *args):
                return dataschema, VTable(list(data))
            Connect=Create

        class VTable:

            # A set of results from bestindex which should all generate TypeError.
            # Coverage checking will ensure all the code is appropriately tickled
            badbestindex=(12,
                          (12,),
                          ((),),
                          (((),),),
                          ((((),),),),
                          (((((),),),),),
                          ((None,None,None,None,"bad"),),
                          ((0,None,(0,),None,None),),
                          ((("bad",True),None,None,None,None),),
                          (((0, True),"bad",None,None,None),),
                          (None,"bad"),
                          [4,(3,True),[2,False],1, [0]],
                          )
            numbadbextindex=len(badbestindex)

            def __init__(self, data):
                self.data=data
                self.bestindex3val=0

            def BestIndex1(self, wrong, number, of, arguments):
                1/0

            def BestIndex2(self, *args):
                1/0

            def BestIndex3(self, constraints, orderbys):
                retval=self.badbestindex[self.bestindex3val]
                self.bestindex3val+=1
                if self.bestindex3val>=self.numbadbextindex:
                    self.bestindex3val=0
                return retval

            def BestIndex4(self, constraints, orderbys):
                # this gives ValueError ("bad" is not a float)
                return (None,12,u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}"), "anything", "bad")

            def BestIndex5(self, constraints, orderbys):
                # unicode error
                return (None, None, "\xde\xad\xbe\xef")

            def BestIndex6(self, constraints, orderbys):
                return ( (0, 1, (2, BadIsTrue()), 3, 4), )

            def BestIndex7(self, constraints, orderbys):
                return (None, long(77), "foo", BadIsTrue(), 99)

            _bestindexreturn=99

            def BestIndex99(self, constraints, orderbys):
                cl=list(constraints)
                cl.sort()
                assert allconstraintsl == cl
                assert orderbys == ( (2, False), )
                retval=( [long(4),(3,True),[long(2),False],1, (0, False)], 997, u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}"), False, 99)[:self._bestindexreturn]
                return retval

            def BestIndexGood(self, constraints, orderbys):
                return None

            def BestIndexGood2(self, constraints, orderbys):
                return [] # empty list is same as None

            def Open(self):
                return Cursor(self)

            def Open1(self, wrong, number, of, arguments):
                1/0

            def Open2(self):
                1/0

            def Open3(self):
                return None

            def Open99(self):
                return Cursor(self)

            UpdateInsertRow1=None

            def UpdateInsertRow2(self, too, many, args):
                1/0

            def UpdateInsertRow3(self, rowid, fields):
                1/0

            def UpdateInsertRow4(self, rowid, fields):
                assert rowid is None
                return None

            def UpdateInsertRow5(self, rowid, fields):
                assert rowid is None
                return "this is not a number"

            def UpdateInsertRow6(self, rowid, fields):
                assert rowid is None
                return -922337203685477580799 # too big

            def UpdateInsertRow7(self, rowid, fields):
                assert rowid is None
                return 9223372036854775807 # ok

            def UpdateInsertRow8(self, rowid, fields):
                assert rowid is not None
                assert rowid==-12
                return "this should be ignored since rowid was supplied"

            def UpdateChangeRow1(self, too, many, args, methinks):
                1/0

            def UpdateChangeRow2(self, rowid, newrowid, fields):
                1/0

            def UpdateChangeRow3(self, rowid, newrowid, fields):
                assert newrowid==rowid

            def UpdateChangeRow4(self, rowid, newrowid, fields):
                assert newrowid==rowid+20

            def UpdateDeleteRow1(self, too, many, args):
                1/0

            def UpdateDeleteRow2(self, rowid):
                1/0

            def UpdateDeleteRow3(self, rowid):
                assert rowid==77

            def Disconnect1(self, too, many, args):
                1/0

            def Disconnect2(self):
                1/0

            def Disconnect3(self):
                pass

            def Destroy1(self, too, many, args):
                1/0

            def Destroy2(self):
                1/0

            def Destroy3(self):
                pass

            def Begin1(self, too, many, args):
                1/0

            def Begin2(self):
                1/0

            def Begin3(self):
                pass

            def Sync(self):
                pass

            def Commit(self):
                pass

            def Rollback(self):
                pass

            def Rename1(self, too, many, args):
                1/0

            def Rename2(self, x):
                1/0

            def Rename3(self, x):
                return ["thisshouldbeignored"*25, [1]]

            def FindFunction1(self, too, many, args):
                1/0

            def FindFunction2(self, name, nargs):
                1/0

            def FindFunction3(self, name, nargs):
                return "this isn't a function"

            def FindFunction4(self, name, nargs):
                if nargs==2:
                    return lambda x,y: x+y
                return None

        class Cursor:

            _bestindexreturn=99

            def __init__(self, table):
                self.table=table

            def Filter1(self, toofewargs):
                1/0

            def Filter2(self, *args):
                1/0

            def Filter99(self, idxnum, idxstr, constraintargs):
                self.pos=1 # row 0 is headers
                if self._bestindexreturn==0:
                    assert idxnum==0
                    assert idxstr==None
                    assert constraintargs==()
                    return
                if self._bestindexreturn==1:
                    assert idxnum==0
                    assert idxstr==None
                    assert constraintargs==('foo', 'A', 12.4, 'A', -1000)
                    return
                if self._bestindexreturn==2:
                    assert idxnum==997
                    assert idxstr==None
                    assert constraintargs==('foo', 'A', 12.4, 'A', -1000)
                    return
                # 3 or more
                assert idxnum==997
                assert idxstr==u(r"\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}")
                assert constraintargs==('foo', 'A', 12.4, 'A', -1000)

            def Filter(self,  *args):
                self.Filter99(*args)
                1/0

            def FilterGood(self, *args):
                self.pos=1 # row 0 is headers

            def Eof1(self, toomany, args):
                1/0

            def Eof2(self):
                1/0

            def Eof3(self):
                return BadIsTrue()

            def Eof99(self):
                return not ( self.pos<len(self.table.data) )

            def Rowid1(self, too, many, args):
                1/0

            def Rowid2(self):
                1/0

            def Rowid3(self):
                return "cdrom"

            def Rowid99(self):
                return self.table.data[self.pos][0]

            def Column1(self):
                1/0

            def Column2(self, too, many, args):
                1/0

            def Column3(self, col):
                1/0

            def Column4(self, col):
                return self # bad type

            def Column99(self, col):
                return self.table.data[self.pos][col+1] # col 0 is row id

            def Close1(self, too, many, args):
                1/0

            def Close2(self):
                1/0

            def Close99(self):
                del self.table  # deliberately break ourselves

            def Next1(self, too, many, args):
                1/0

            def Next2(self):
                1/0

            def Next99(self):
                self.pos+=1

        # use our more complete version
        self.db.createmodule("testmod2", Source())
        cur.execute("create virtual table foo using testmod2(2,two)")
        # are missing/mangled methods detected correctly?
        self.assertRaises(AttributeError, cur.execute, "select rowid,* from foo order by number")
        VTable.BestIndex=VTable.BestIndex1
        self.assertRaises(TypeError, cur.execute, "select rowid,* from foo order by number")
        VTable.BestIndex=VTable.BestIndex2
        self.assertRaises(ZeroDivisionError, cur.execute, "select rowid,* from foo order by number")
        # check bestindex results
        VTable.BestIndex=VTable.BestIndex3
        for i in range(VTable.numbadbextindex):
            self.assertRaises(TypeError, cur.execute, allconstraints)
        VTable.BestIndex=VTable.BestIndex4
        self.assertRaises(ValueError, cur.execute, allconstraints)
        if not py3:
            VTable.BestIndex=VTable.BestIndex5
            self.assertRaises(UnicodeDecodeError, cur.execute, allconstraints)
        VTable.BestIndex=VTable.BestIndex6
        self.assertRaises(ZeroDivisionError, cur.execute, allconstraints)
        VTable.BestIndex=VTable.BestIndex7
        self.assertRaises(ZeroDivisionError, cur.execute, allconstraints)

        # check varying number of return args from bestindex
        VTable.BestIndex=VTable.BestIndex99
        for i in range(6):
            VTable._bestindexreturn=i
            Cursor._bestindexreturn=i
            try:
                cur.execute(" "+allconstraints+" "*i) # defeat statement cache - bestindex is called during prepare
            except ZeroDivisionError:
                pass

        # error cases ok, return real values and move on to cursor methods
        del VTable.Open
        del Cursor.Filter
        self.assertRaises(AttributeError, cur.execute, allconstraints) # missing open
        VTable.Open=VTable.Open1
        self.assertRaises(TypeError, cur.execute,allconstraints)
        VTable.Open=VTable.Open2
        self.assertRaises(ZeroDivisionError, cur.execute,allconstraints)
        VTable.Open=VTable.Open3
        self.assertRaises(AttributeError, cur.execute, allconstraints)
        VTable.Open=VTable.Open99
        self.assertRaises(AttributeError, cur.execute, allconstraints)
        # put in filter
        Cursor.Filter=Cursor.Filter1
        self.assertRaises(TypeError, cur.execute,allconstraints)
        Cursor.Filter=Cursor.Filter2
        self.assertRaises(ZeroDivisionError, cur.execute,allconstraints)
        Cursor.Filter=Cursor.Filter99
        self.assertRaises(AttributeError, cur.execute, allconstraints)
        Cursor.Eof=Cursor.Eof1
        self.assertRaises(TypeError, cur.execute, allconstraints)
        Cursor.Eof=Cursor.Eof2
        self.assertRaises(ZeroDivisionError,cur.execute, allconstraints)
        Cursor.Eof=Cursor.Eof3
        self.assertRaises(ZeroDivisionError,cur.execute, allconstraints)
        Cursor.Eof=Cursor.Eof99
        self.assertRaises(AttributeError, cur.execute, allconstraints)
        # now onto to rowid
        Cursor.Rowid=Cursor.Rowid1
        self.assertRaises(TypeError, cur.execute,allconstraints)
        Cursor.Rowid=Cursor.Rowid2
        self.assertRaises(ZeroDivisionError, cur.execute,allconstraints)
        Cursor.Rowid=Cursor.Rowid3
        self.assertRaises(ValueError, cur.execute,allconstraints)
        Cursor.Rowid=Cursor.Rowid99
        self.assertRaises(AttributeError, cur.execute, allconstraints)
        # column
        Cursor.Column=Cursor.Column1
        self.assertRaises(TypeError, cur.execute,allconstraints)
        Cursor.Column=Cursor.Column2
        self.assertRaises(TypeError, cur.execute,allconstraints)
        Cursor.Column=Cursor.Column3
        self.assertRaises(ZeroDivisionError, cur.execute,allconstraints)
        Cursor.Column=Cursor.Column4
        self.assertRaises(TypeError, cur.execute,allconstraints)
        Cursor.Column=Cursor.Column99
        try:
            for row in cur.execute(allconstraints): pass
        except AttributeError:  pass
        # next
        Cursor.Next=Cursor.Next1
        try:
            for row in cur.execute(allconstraints): pass
        except TypeError:  pass
        Cursor.Next=Cursor.Next2
        try:
            for row in cur.execute(allconstraints): pass
        except ZeroDivisionError:  pass
        Cursor.Next=Cursor.Next99
        try:
            for row in cur.execute(allconstraints): pass
        except AttributeError:
            pass
        # close
        Cursor.Close=Cursor.Close1
        try:
            for row in cur.execute(allconstraints): pass
        except TypeError:  pass
        Cursor.Close=Cursor.Close2
        try:
            for row in cur.execute(allconstraints): pass
        except ZeroDivisionError:  pass
        Cursor.Close=Cursor.Close99

        # update (insert)
        sql="insert into foo (name, description) values('gunk', 'foo')"
        self.assertRaises(AttributeError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow1
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow2
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow3
        self.assertRaises(ZeroDivisionError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow4
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow5
        self.assertRaises(ValueError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow6
        self.assertRaises(OverflowError, cur.execute, sql)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow7
        cur.execute(sql)
        self.assertEqual(self.db.last_insert_rowid(), 9223372036854775807)
        VTable.UpdateInsertRow=VTable.UpdateInsertRow8
        cur.execute("insert into foo (rowid,name, description) values(-12,'gunk', 'foo')")

        # update (change)
        VTable.BestIndex=VTable.BestIndexGood
        Cursor.Filter=Cursor.FilterGood
        sql="update foo set description=='bar' where description=='foo'"
        self.assertRaises(AttributeError, cur.execute, sql)
        VTable.UpdateChangeRow=VTable.UpdateChangeRow1
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.UpdateChangeRow=VTable.UpdateChangeRow2
        self.assertRaises(ZeroDivisionError, cur.execute, sql)
        VTable.UpdateChangeRow=VTable.UpdateChangeRow3
        cur.execute(sql)
        VTable.UpdateChangeRow=VTable.UpdateChangeRow4
        cur.execute("update foo set rowid=rowid+20 where 1")

        # update (delete)
        VTable.BestIndex=VTable.BestIndexGood2  # improves code coverage
        sql="delete from foo where name=='Fred'"
        self.assertRaises(AttributeError, cur.execute, sql)
        VTable.UpdateDeleteRow=VTable.UpdateDeleteRow1
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.UpdateDeleteRow=VTable.UpdateDeleteRow2
        self.assertRaises(ZeroDivisionError, cur.execute, sql)
        VTable.UpdateDeleteRow=VTable.UpdateDeleteRow3
        cur.execute(sql)

        # rename
        sql="alter table foo rename to bar"
        VTable.Rename=VTable.Rename1
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.Rename=VTable.Rename2
        self.assertRaises(ZeroDivisionError, cur.execute, sql)
        VTable.Rename=VTable.Rename3
        # this is to catch memory leaks
        cur.execute(sql)
        del VTable.Rename # method is optional
        cur.execute("alter table bar rename to foo") # put things back

        # findfunction
        # mess with overload function first
        self.assertRaises(TypeError, self.db.overloadfunction, 1, 1)
        # https://sqlite.org/cvstrac/tktview?tn=3507
        # self.db.overloadfunction("a"*1024, 1)
        self.db.overloadfunction("xyz", 2)
        self.assertRaises(apsw.SQLError, cur.execute, "select xyz(item,description) from foo")
        VTable.FindFunction=VTable.FindFunction1
        self.assertRaises(TypeError, cur.execute, "select xyz(item,description) from foo ")
        VTable.FindFunction=VTable.FindFunction2
        self.assertRaises(ZeroDivisionError, cur.execute, "select xyz(item,description) from foo  ")
        VTable.FindFunction=VTable.FindFunction3
        try:
            for row in cur.execute("select xyz(item,description) from foo   "):
                pass
            1/0
        except TypeError:
            pass
        # this should work
        VTable.FindFunction=VTable.FindFunction4
        for row in cur.execute("select xyz(item,description) from foo    "):
                pass

        # transaction control
        # Begin, Sync, Commit and rollback all use the same underlying code
        sql="delete from foo where name=='Fred'"
        VTable.Begin=VTable.Begin1
        self.assertRaises(TypeError, cur.execute, sql)
        VTable.Begin=VTable.Begin2
        self.assertRaises(ZeroDivisionError, cur.execute, sql)
        VTable.Begin=VTable.Begin3
        cur.execute(sql)

        # disconnect - sqlite ignores any errors
        db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db.createmodule("testmod2", Source())
        cur2=db.cursor()
        for _ in cur2.execute("select * from foo"): pass
        VTable.Disconnect=VTable.Disconnect1
        self.assertRaises(TypeError, db.close) # nb close succeeds!
        self.assertRaises(apsw.CursorClosedError, cur2.execute, "select * from foo")
        del db
        db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db.createmodule("testmod2", Source())
        cur2=db.cursor()
        for _ in cur2.execute("select * from foo"): pass
        VTable.Disconnect=VTable.Disconnect2
        self.assertRaises(ZeroDivisionError, db.close) # nb close succeeds!
        self.assertRaises(apsw.CursorClosedError, cur2.execute, "select * from foo")
        del db
        db=apsw.Connection(TESTFILEPREFIX+"testdb")
        db.createmodule("testmod2", Source())
        cur2=db.cursor()
        for _ in cur2.execute("select * from foo"): pass
        VTable.Disconnect=VTable.Disconnect3
        db.close()
        del db

        # destroy
        VTable.Destroy=VTable.Destroy1
        self.assertRaises(TypeError, cur.execute, "drop table foo")
        VTable.Destroy=VTable.Destroy2
        self.assertRaises(ZeroDivisionError, cur.execute, "drop table foo")
        VTable.Destroy=VTable.Destroy3
        cur.execute("drop table foo")
        self.db.close()


    def testVTableExample(self):
        "Tests vtable example code"
        # Make sure vtable code actually works by comparing SQLite
        # results against manually computed results

        def getfiledata(directories):
            columns=None
            data=[]
            counter=1
            for directory in directories:
                for f in os.listdir(directory):
                    if not os.path.isfile(os.path.join(directory,f)):
                        continue
                    counter+=1
                    try:
                        st=os.stat(os.path.join(directory,f))
                        if columns is None:
                            columns=["rowid", "name", "directory"]+[x for x in dir(st) if x.startswith("st_")]
                        data.append( [counter, f, directory] + [getattr(st,x) for x in columns[3:]] )
                    except OSError:
                        # we ignore file and permission errors in this example
                        pass
            return columns, data

        class Source:
            def Create(self, db, modulename, dbname, tablename, *args):
                columns,data=getfiledata([eval(UPREFIX+a) for a in args]) # eval strips off layer of quotes
                schema="create table foo("+','.join(["'%s'" % (x,) for x in columns[1:]])+")"
                return schema,Table(columns,data)
            Connect=Create

        class Table:
            def __init__(self, columns, data):
                self.columns=columns
                self.data=data

            def BestIndex(self, *args):
                return None

            def Open(self):
                return Cursor(self)

            def Disconnect(self):
                pass

            Destroy=Disconnect

        class Cursor:
            def __init__(self, table):
                self.table=table

            def Filter(self, *args):
                self.pos=0

            def Eof(self):
                return self.pos>=len(self.table.data)

            def Rowid(self):
                return self.table.data[self.pos][0]

            def Column(self, col):
                return self.table.data[self.pos][1+col]

            def Next(self):
                self.pos+=1

            def Close(self):
                pass

        paths=[x.replace("\\","/") for x in sys.path if len(x) and os.path.isdir(x)]
        cols,data=getfiledata(paths)
        self.db.createmodule("filesource", Source())
        cur=self.db.cursor()
        args=",".join(["'%s'" % (x,) for x in paths])
        cur.execute("create virtual table files using filesource("+args+")")

        # Find the largest file (SQL)
        for bigsql in cur.execute("select st_size,name,directory from files order by st_size desc limit 1"):
            pass
        # Find the largest (manually)
        colnum=cols.index("st_size")
        bigmanual=(0,"","")
        for file in data:
            if file[colnum]>bigmanual[0]:
                bigmanual=file[colnum], file[1], file[2]

        self.assertEqual(bigsql, bigmanual)

        # Find the oldest file (SQL)
        for oldestsql in cur.execute("select st_ctime,name,directory from files order by st_ctime limit 1"):
            pass
        # Find the oldest (manually)
        colnum=cols.index("st_ctime")
        oldestmanual=(99999999999999999,"","")
        for file in data:
            if file[colnum]<oldestmanual[0]:
                oldestmanual=file[colnum], file[1], file[2]

        self.assertEqual( oldestmanual, oldestsql)


    def testClosingChecks(self):
        "Check closed connection is correctly detected"
        cur=self.db.cursor()
        rowid=next(cur.execute("create table foo(x blob); insert into foo values(zeroblob(98765)); select rowid from foo"))[0]
        blob=self.db.blobopen("main", "foo", "x", rowid, True)
        blob.close()
        nargs=self.blob_nargs
        for func in [x for x in dir(blob) if not x.startswith("__") and not x in ("close",)]:
            args=("one", "two", "three")[:nargs.get(func,0)]
            try:
                getattr(blob, func)(*args)
                self.fail("blob method "+func+" didn't notice that the connection is closed")
            except ValueError: # we issue ValueError to be consistent with file objects
                pass

        self.db.close()
        nargs=self.connection_nargs
        tested=0
        for func in [x for x in dir(self.db) if x in nargs or (not x.startswith("__") and not x in ("close",))]:
            tested+=1
            args=("one", "two", "three")[:nargs.get(func,0)]

            try:
                # attributes come back as None after a close
                func=getattr(self.db, func)
                if func:
                    func(*args)
                    self.fail("connection method "+str(func)+" didn't notice that the connection is closed")
            except apsw.ConnectionClosedError:
                pass
        self.assertTrue(tested>len(nargs))

        # do the same thing, but for cursor
        nargs=self.cursor_nargs
        tested=0
        for func in [x for x in dir(cur) if not x.startswith("__") and not x in ("close",)]:
            tested+=1
            args=("one", "two", "three")[:nargs.get(func,0)]
            try:
                getattr(cur, func)(*args)
                self.fail("cursor method "+func+" didn't notice that the connection is closed")
            except apsw.CursorClosedError:
                pass
        self.assertTrue(tested>=len(nargs))

    def testClosing(self):
        "Verify behaviour of close() functions"
        cur=self.db.cursor()
        cur.execute("select 3;select 4")
        self.assertRaises(apsw.IncompleteExecutionError, cur.close)
        # now force it
        self.assertRaises(TypeError, cur.close, sys)
        self.assertRaises(TypeError, cur.close, 1,2,3)
        cur.close(True)
        l=[self.db.cursor() for i in range(1234)]
        cur=self.db.cursor()
        cur.execute("select 3; select 4; select 5")
        l2=[self.db.cursor() for i in range(1234)]
        self.assertRaises(apsw.IncompleteExecutionError, self.db.close)
        self.assertRaises(TypeError, self.db.close, sys)
        self.assertRaises(TypeError, self.db.close, 1,2,3)
        self.db.close(True) # force it
        self.db.close() # should be fine now
        # coverage - close cursor after closing db
        db=apsw.Connection(":memory:")
        cur=db.cursor()
        db.close()
        cur.close()

    def testLargeObjects(self):
        "Verify handling of large strings/blobs (>2GB) [Python 2.5+, 64 bit platform]"
        if not is64bit:
            return
        # For binary/blobs I use an anonymous area slightly larger than 2GB chunk of memory, but don't touch any of it
        import mmap
        f=mmap.mmap(-1, 2*1024*1024*1024+25000)
        c=self.db.cursor()
        c.execute("create table foo(theblob)")
        self.assertRaises(apsw.TooBigError,  c.execute, "insert into foo values(?)", (f,))
        c.execute("insert into foo values(?)", ("jkghjk"*1024,))
        b=self.db.blobopen("main", "foo", "theblob", self.db.last_insert_rowid(), True)
        b.read(1)
        self.assertRaises(ValueError, b.write, f)
        def func(): return f
        self.db.createscalarfunction("toobig", func)
        self.assertRaises(apsw.TooBigError, c.execute, "select toobig()")
        f.close()
        # Other testing by fault injection
        if not hasattr(apsw, "faultdict"):
            return

        ## SetContextResultLargeUnicode
        apsw.faultdict["SetContextResultLargeUnicode"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("foo", lambda x: u("a unicode string"))
            for row in db.cursor().execute("select foo(3)"):
                pass
            1/0
        except apsw.TooBigError:
            pass

        ## SetContextResultLargeString
        if sys.version_info<(3,0):
            apsw.faultdict["SetContextResultLargeString"]=True
            try:
                db=apsw.Connection(":memory:")
                def func(x):
                    return "an ordinary string"*10000
                db.createscalarfunction("foo", func)
                for row in db.cursor().execute("select foo(3)"):
                    pass
                1/0
            except apsw.TooBigError:
                pass

        ## DoBindingLargeUnicode
        apsw.faultdict["DoBindingLargeUnicode"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("create table foo(x); insert into foo values(?)", (u("aaaa"),))
            1/0
        except apsw.TooBigError:
            pass

        ## DoBindingLargeString
        if sys.version_info<(3,0):
            apsw.faultdict["DoBindingLargeString"]=True
            try:
                db=apsw.Connection(":memory:")
                db.cursor().execute("create table foo(x); insert into foo values(?)", ("aaaa"*10000,))
                1/0
            except apsw.TooBigError:
                pass

    def testErrorCodes(self):
        "Verify setting of result codes on error/exception"
        fname=TESTFILEPREFIX+"gunk-errcode-test"
        write_whole_file(fname, "wb", b("A")*8192)
        db=None
        try:
            # The exception could be thrown on either of these lines
            # depending on several factors
            db=apsw.Connection(fname)
            db.cursor().execute("select * from sqlite_master")
            1/0 # should not be reachable
        except:
            klass,e,tb=sys.exc_info()
            self.assertTrue(isinstance(e, apsw.NotADBError))
            self.assertEqual(e.result, apsw.SQLITE_NOTADB);
            self.assertEqual(e.extendedresult&0xff, apsw.SQLITE_NOTADB)
        if db is not None:
            db.close(True)

        try:
            deletefile(fname)
        except:
            pass

    def testLimits(self):
        "Verify setting and getting limits"
        self.assertRaises(TypeError, self.db.limit, "apollo", 11)
        c=self.db.cursor()
        c.execute("create table foo(x)")
        c.execute("insert into foo values(?)", ("x"*1024,))
        old=self.db.limit(apsw.SQLITE_LIMIT_LENGTH)
        self.db.limit(apsw.SQLITE_LIMIT_LENGTH, 1023)
        self.assertRaises(apsw.TooBigError, c.execute, "insert into foo values(?)", ("y"*1024,))
        self.assertEqual(1023, self.db.limit(apsw.SQLITE_LIMIT_LENGTH, 0))
        # bug in sqlite - see https://sqlite.org/cvstrac/tktview?tn=3085
        if False:
            c.execute("insert into foo values(?)", ("x"*1024,))
            self.assertEqual(apsw.SQLITE_MAX_LENGTH, self.db.limit(apsw.SQLITE_LIMIT_LENGTH))

    def testConnectionHooks(self):
        "Verify connection hooks"
        del apsw.connection_hooks
        try:
            db=apsw.Connection(":memory:")
        except AttributeError:
            pass
        apsw.connection_hooks=sys # bad type
        try:
            db=apsw.Connection(":memory:")
        except TypeError:
            pass
        apsw.connection_hooks=("a", "tuple", "of", "non-callables")
        try:
            db=apsw.Connection(":memory:")
        except TypeError:
            pass
        apsw.connection_hooks=(dir, lambda x: 1/0)
        try:
            db=apsw.Connection(":memory:")
        except ZeroDivisionError:
            pass
        def delit(db):
            del db
        apsw.connection_hooks=[delit for _ in range(9000)]
        db=apsw.Connection(":memory:")
        db.close()
        apsw.connection_hooks=[lambda x: x]
        db=apsw.Connection(":memory:")
        db.close()

    def testCompileOptions(self):
        "Verify getting compile options"
        # We don't know what the right answers are, so just check
        # there are more than zero entries.
        v=apsw.compile_options
        self.assertEqual(type(v), tuple)
        self.assertTrue(len(v)>1)

    def testIssue4(self):
        "Issue 4: Error messages and SQLite ticket 3063"
        connection = apsw.Connection(":memory:")
        cursor = connection.cursor()

        cursor.execute("CREATE TABLE A_TABLE (ID ABC PRIMARY KEY NOT NULL)")
        try:
            cursor.execute("INSERT INTO A_TABLE VALUES (NULL)")
        except:
            klass,e,tb=sys.exc_info()
            assert "A_TABLE.ID" in str(e)

        try:
            cursor.execute("INSERT INTO A_TABLE VALUES (?)", (None,))
        except:
            klass,e,tb=sys.exc_info()
            assert "A_TABLE.ID" in str(e)

    def testIssue15(self):
        "Issue 15: Release GIL during calls to prepare"
        self.db.cursor().execute("create table foo(x)")
        self.db.cursor().execute("begin exclusive")
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        db2.setbusytimeout(30000)
        t=ThreadRunner(db2.cursor().execute, "select * from foo")
        t.start()
        time.sleep(1)
        self.db.cursor().execute("commit")
        t.go()

    def testIssue19(self):
        "Issue 19: Incomplete cursor execution"
        c=self.db.cursor()
        c.execute("create table numbers(x)")
        for i in range(10):
            c.execute("insert into numbers values(?)", (i,))
        c.execute("select * from numbers")
        next(c)
        next(c)
        next(c)
        self.db.cursor().execute("delete from numbers where x=5")
        next(c)
        next(c)

    def testIssue24(self):
        "Issue 24: Ints and Longs"
        c=self.db.cursor()
        for row in c.execute("select 3"): pass
        self.assertEqual(int, type(row[0]))
        for row in c.execute("select -2147483647-1"): pass
        self.assertEqual(int, type(row[0]))
        for row in c.execute("select 2147483647"): pass
        self.assertEqual(int, type(row[0]))
        # Depending on the platform, sizeof(long), 64 bitness etc we
        # may remain as python type int or type long. Check we are
        # getting the right numbers no matter what.  This duplicates
        # testTypes but you can never be too careful.
        for v in "2147483646", "2147483647", "2147483648", "2147483649", \
                "21474836460", "21474836470", "21474836480", "21474836490", \
                "147483646", "147483647", "147483648", "147483649":
            for neg in ("-", ""):
                val=c.execute("select "+neg+v).fetchall()[0][0]
                val=repr(val)
                if val.endswith("L"):
                    val=val[:-1]
                self.assertEqual(val, neg+v)

    def testIssue31(self):
        "Issue 31: GIL & SQLite mutexes with heavy threading, threadsafe errors from SQLite"
        randomnumbers=[random.randint(0,10000) for _ in range(10000)]

        cursor=self.db.cursor()
        cursor.execute("create table foo(x)")
        cursor.execute("begin")
        for num in randomnumbers:
            cursor.execute("insert into foo values(?)", (num,))
        cursor.execute("end")

        self.db.createscalarfunction("timesten", lambda x: x*10)

        def dostuff(n):
            # spend n seconds doing stuff to the database
            c=self.db.cursor()
            b4=time.time()
            while time.time()-b4<n:
                i=random.choice(randomnumbers)
                if i%5==0:
                    sql="select timesten(x) from foo where x=%d order by x" % (i,)
                    c.execute(sql)
                elif i%5==1:
                    sql="select timesten(x) from foo where x=? order by x"
                    called=0
                    for row in self.db.cursor().execute(sql, (i,)):
                        called+=1
                        self.assertEqual(row[0], 10*i)
                    # same value could be present multiple times
                    self.assertTrue(called>=1)
                elif i%5==2:
                    try:
                        self.db.cursor().execute("deliberate syntax error")
                    except apsw.SQLError:
                        assert("deliberate" in str(sys.exc_info()[1]))
                elif i%5==3:
                    try:
                        self.db.cursor().execute("bogus syntax error")
                    except apsw.SQLError:
                        assert("bogus" in str(sys.exc_info()[1]))
                else:
                    sql="select timesten(x) from foo where x=? order by x"
                    self.db.cursor().execute(sql, (i,))

        threads=[ThreadRunner(dostuff, 15) for _ in range(20)]
        for t in threads:
            t.start()

        for t in threads:
            # if there were any errors then exceptions would be raised here
            t.go()

    def testIssue50(self):
        "Issue 50: Check Blob.read return value on eof"
        # first get what the system returns on eof
        if iswindows:
            f=open("nul", "rb")
        else:
            f=open("/dev/null", "rb")
        try:
            # deliberately hit eof
            f.read()
            # now try to read some more
            feof=f.read(10)
        finally:
            f.close()
        cur=self.db.cursor()
        # make a blob to play with
        rowid=next(cur.execute("create table foo(x blob); insert into foo values(zeroblob(98765)); select rowid from foo"))[0]
        blobro=self.db.blobopen("main", "foo", "x", rowid, False)
        try:
            blobro.read(98765)
            beof=blobro.read(10)
            self.assertEqual(type(beof), type(feof))
            self.assertEqual(beof, feof)
        finally:
            blobro.close()

    def testIssue98(self, runfrom106=None):
        "Issue 98: An error in context manager commit should do a rollback"
        self.db.cursor().execute("create table foo(x); insert into foo values(3); insert into foo values(4)")
        # We need the reader to block a writer, which requires non-WAL mode
        self.db.cursor().execute("pragma journal_mode=delete")
        db2=apsw.Connection(TESTFILEPREFIX+"testdb")
        if runfrom106:
            db2.setexectrace(runfrom106)
        db2.cursor().execute("pragma journal_mode=delete")
        # deliberately don't read from cursor on connection 1 which will prevent a commit
        x=self.db.cursor().execute("select * from foo")
        db2.__enter__()
        db2.cursor().execute("insert into foo values(5)") # transaction is buffered in memory by SQLite
        try:
            db2.__exit__(None, None, None)
        except apsw.BusyError:
            pass
        # Ensure transaction was rolled back
        x.fetchall()
        for row in db2.cursor().execute("select * from foo where x=5"):
            self.fail("Transaction was not rolled back")
        db2.close()
        if runfrom106: return
        # Verify that error in tracer results in rollback
        self.db.__enter__()
        def h(*args): 1/0
        self.db.cursor().execute("insert into foo values(6)")
        self.db.setexectrace(h)
        try:
            self.db.__exit__(None, None, None)
        except ZeroDivisionError:
            self.db.setexectrace(None)
            pass
        for row in self.db.cursor().execute("select * from foo where x=6"):
            self.fail("Transaction was not rolled back")

    def testIssue103(self):
        "Issue 103: Error handling when sqlite3_declare_vtab fails"
        class Source:
            def Create(self, *args):
                return "create table x(delete)", None

        self.db.createmodule("issue103", Source())
        try:
            self.db.cursor().execute("create virtual table foo using issue103()")
            1/0 # should not be reached
        except apsw.SQLError:
            assert "near \"delete\": syntax error" in str(sys.exc_info()[1])

    def testIssue106(self):
        "Issue 106: Profiling and tracing"
        traces=[]
        def tracer(cur, sql, bindings):
            sql=sql.lower().split()[0]
            if sql in ("savepoint", "release", "rollback"):
                traces.append(sql)
            return True
        self.testIssue98(tracer)
        self.assertTrue(len(traces)>=3)
        self.assertTrue("savepoint" in traces)
        self.assertTrue("release" in traces)
        self.assertTrue("rollback" in traces)

    def testIssue142(self):
        "Issue 142: bytes from system during dump"
        orig_strftime=time.strftime
        orig_getuser=getpass.getuser
        fh=[]
        try:
            time.strftime=lambda arg: BYTES(r"gjkTIMEJUNKhgjhg\xfe\xdf")
            getpass.getuser=lambda : BYTES(r"\x81\x82\x83gjkhgUSERJUNKjhg\xfe\xdf")
            import codecs
            fh=[codecs.open(TESTFILEPREFIX+"test-shell-"+t, "w+b", encoding="utf8") for t in ("in", "out", "err")]
            kwargs={"stdin": fh[0], "stdout": fh[1], "stderr": fh[2]}

            rows=(["correct"], ["horse"], ["battery"], ["staple"])
            self.db.cursor().execute("create table foo(x)")
            self.db.cursor().executemany("insert into foo values(?)", rows)
            shell=apsw.Shell(db=self.db, **kwargs)
            shell.command_dump([])

            fh[1].seek(0)
            out=fh[1].read()

            for row in rows:
                self.assertTrue(row[0] in out)

            self.assertTrue("TIMEJUNK" in out)
            self.assertTrue("USERJUNK" in out)

        finally:
            for f in fh:
                f.close()
            time.strftim=orig_strftime
            getpass.getuser=orig_getuser

    def testIssue186(self):
        "Issue 186: desription cache between statements"
        cur=self.db.cursor()

        for i, row in enumerate(cur.execute("select 1; select 1,2; select 1,2,3; select 1,2,3,4;")):
            # this catches if the order of getting them makes a difference
            if i%2:
                self.assertEqual(len(cur.description), len(cur.getdescription()))
            else:
                self.assertEqual(len(cur.getdescription()), len(cur.description))
            self.assertEqual(len(cur.description), i+1)

        # check executemany too
        for i, row in enumerate(cur.executemany("select ?; select ?,?; select ?,?,?; select ?,?,?,?;",
                                                [(1, 1,2, 1,2,3, 1,2,3,4),
                                                 (1, 1,2, 1,2,3, 1,2,3,4),
                                                 ])):
            i%=4
            self.assertEqual(len(cur.getdescription()), i+1)

        # and the tracers
        def tracer(cursor, *args):
            self.assertEqual(len(cursor.getdescription()), expect)
            return True
        expect=1
        cur.setexectrace(tracer)
        cur.setrowtrace(tracer)
        for i, row in enumerate(cur.execute("select 1; select 1,2; select 1,2,3; select 1,2,3,4;")):
            expect+=1
        expect=1
        for i, row in enumerate(cur.executemany("select ?; select ?,?; select ?,?,?; select ?,?,?,?;",
                                                [(1, 1,2, 1,2,3, 1,2,3,4),
                                                 (1, 1,2, 1,2,3, 1,2,3,4),
                                                 ])):
            expect+=1
            if expect>4: expect=1


    def testTicket2158(self):
        "Check we are not affected by SQLite ticket #2158"
        # https://sqlite.org/cvstrac/tktview?tn=2158
        def dummy(x,y):
            if x<y: return -1
            if x>y: return 1
            return 0
        self.db.createcollation("dummy", dummy)
        cur=self.db.cursor()
        cur.execute("create table foo(x)")
        cur.executemany("insert into foo values(?)", randomintegers(20))
        for row in cur.execute("select * from foo order by x collate dummy"):
            pass
        self.db.createcollation("dummy", None)
        self.assertRaises(apsw.SQLError, cur.execute, "select * from foo order by x collate dummy")

    def testPysqliteRecursiveIssue(self):
        "Check an issue that affected pysqlite"
        # https://code.google.com/p/pysqlite/source/detail?r=260ee266d6686e0f87b0547c36b68a911e6c6cdb
        cur=self.db.cursor()
        cur.execute("create table a(x); create table b(y);")
        def foo():
            yield (1,)
            cur.execute("insert into a values(?)", (1,))
            yield (2,)
        self.assertRaises(apsw.ThreadingViolationError, cur.executemany, "insert into b values(?)", foo())

    def testWriteUnraiseable(self):
        "Verify writeunraiseable replacement function"
        def unraise():
            # We cause an unraiseable error to happen by writing to a
            # blob open for reading.  The close method called in the
            # destructor will then also give the error
            db=apsw.Connection(":memory:")
            rowid=next(db.cursor().execute("create table foo(x); insert into foo values(x'aabbccdd'); select rowid from foo"))[0]
            blob=db.blobopen("main", "foo", "x", rowid, False)
            try:
                blob.write(b("badd"))
            except apsw.ReadOnlyError:
                pass
            del db
            del blob
            gc.collect()

        # Normal excepthook
        self.assertRaisesUnraisable(apsw.ReadOnlyError, unraise)
        # excepthook with error to check PyErr_Display is called
        xx=sys.excepthook
        yy=sys.stderr
        sys.stderr=open(TESTFILEPREFIX+"errout.txt", "wt")
        def ehook(blah):
            1/0
        sys.excepthook=ehook
        unraise()
        sys.stderr.close()
        v=open(TESTFILEPREFIX+"errout.txt", "rt").read()
        deletefile(TESTFILEPREFIX+"errout.txt")
        self.assertTrue(len(v))
        sys.excepthook=xx
        sys.stderr=yy

    def testStatementCache(self, scsize=100):
        "Verify statement cache integrity"
        cur=self.db.cursor()
        cur.execute("create table foo(x,y)")
        cur.execute("create index foo_x on foo(x)")
        cur.execute("insert into foo values(1,2)")
        cur.execute("drop index foo_x")
        cur.execute("insert into foo values(1,2)") # cache hit, but needs reprepare
        cur.execute("drop table foo; create table foo(x)")
        try:
            cur.execute("insert into foo values(1,2)") # cache hit, but invalid sql
        except apsw.SQLError:
            pass
        cur.executemany("insert into foo values(?)", [[1],[2]])
        # overflow the statement cache
        l=[self.db.cursor().execute("select x from foo"+" "*i) for i in range(scsize+200)]
        del l
        gc.collect()
        # coverage
        l=[]
        for i in range(scsize+10):
            l.append(self.db.cursor().execute("select x from foo"+" "*i))
            for row in self.db.cursor().execute("select * from foo"):
                pass
        # other wrangling
        l=[self.db.cursor().execute("select x from foo") for i in range(scsize+200)]
        for i in range(scsize+200):
            for row in self.db.cursor().execute("select * from foo"+" "*i):
                pass
        del l
        gc.collect()
        db2=apsw.Connection(TESTFILEPREFIX+"testdb", statementcachesize=scsize)
        cur2=db2.cursor()
        cur2.execute("create table bar(x,y)")
        for _ in cur.execute("select * from foo"): pass
        db2.close()
        # Get some coverage - overflow apswbuffer recycle.  100 is
        # statementcache size, 256 is apswbufferrecycle bin size, and
        # 17 is to overflow
        l=[self.db.cursor().execute(u("select 3"+" "*i)) for i in range(100+256+17)]
        while l:
            l.pop().fetchall()

    def testStatementCacheZeroSize(self):
        "Rerun statement cache tests with a zero sized/disabled cache"
        self.db=apsw.Connection(TESTFILEPREFIX+"testdb", statementcachesize=-1)
        self.testStatementCache(-1)

    def testWikipedia(self):
        "Use front page of wikipedia to check unicode handling"
        # the text also includes characters that can't be represented in 16 bits
        text=u("""WIKIPEDIA\nEnglish\nThe Free Encyclopedia\n2 386 000+ articles\nDeutsch\nDie freie Enzyklop\\u00e4die\n753 000+ Artikel\nFran\\u00e7ais\nL\\u2019encyclop\\u00e9die libre\n662 000+ articles\nPolski\nWolna encyklopedia\n503 000+ hase\\u0142\n\\u65e5\\u672c\\u8a9e\n\\u30d5\\u30ea\\u30fc\\u767e\\u79d1\\u4e8b\\u5178\n492 000+ \\u8a18\\u4e8b\nItaliano\nL\\u2019enciclopedia libera\n456 000+ voci\nNederlands\nDe vrije encyclopedie\n440 000+ artikelen\nPortugu\\u00eas\nA enciclop\\u00e9dia livre\n380 000+ artigos\nEspa\\u00f1ol\nLa enciclopedia libre\n363 000+ art\\u00edculos\n\\u0420\\u0443\\u0441\\u0441\\u043a\\u0438\\u0439\n\\u0421\\u0432\\u043e\\u0431\\u043e\\u0434\\u043d\\u0430\\u044f \\u044d\\u043d\\u0446\\u0438\\u043a\\u043b\\u043e\\u043f\\u0435\\u0434\\u0438\\u044f\n285 000+ \\u0441\\u0442\\u0430\\u0442\\u0435\\u0439\nSearch \\u00b7 Suche \\u00b7 Rechercher \\u00b7 Szukaj \\u00b7 \\u691c\\u7d22 \\u00b7 Ricerca \\u00b7 Zoeken \\u00b7 Busca \\u00b7 Buscar\n\\u041f\\u043e\\u0438\\u0441\\u043a \\u00b7 S\\u00f6k \\u00b7 \\u641c\\u7d22 \\u00b7 S\\u00f8k \\u00b7 Haku \\u00b7 Cerca \\u00b7 Suk \\u00b7 \\u041f\\u043e\\u0448\\u0443\\u043a \\u00b7 C\\u0103utare \\u00b7 Ara\n 100 000+ \nCatal\\u00e0 \\u00b7 Deutsch \\u00b7 English \\u00b7 Espa\\u00f1ol \\u00b7 Fran\\u00e7ais \\u00b7 Italiano \\u00b7 Nederlands \\u00b7 \\u65e5\\u672c\\u8a9e \\u00b7 Norsk (bokm\\u00e5l) \\u00b7 Polski \\u00b7 Portugu\\u00eas \\u00b7 \\u0420\\u0443\\u0441\\u0441\\u043a\\u0438\\u0439 \\u00b7 Rom\\u00e2n\\u0103 \\u00b7 Suomi \\u00b7 Svenska \\u00b7 T\\u00fcrk\\u00e7e \\u00b7 \\u0423\\u043a\\u0440\\u0430\\u0457\\u043d\\u0441\\u044c\\u043a\\u0430 \\u00b7 Volap\\u00fck \\u00b7 \\u4e2d\\u6587\n 10 000+ \n\\u0627\\u0644\\u0639\\u0631\\u0628\\u064a\\u0629 \\u00b7 Asturianu \\u00b7 Krey\\u00f2l Ayisyen \\u00b7 Az\\u0259rbaycan / \\u0622\\u0630\\u0631\\u0628\\u0627\\u064a\\u062c\\u0627\\u0646 \\u062f\\u064a\\u0644\\u06cc \\u00b7 \\u09ac\\u09be\\u0982\\u09b2\\u09be \\u00b7 \\u0411\\u0435\\u043b\\u0430\\u0440\\u0443\\u0441\\u043a\\u0430\\u044f (\\u0410\\u043a\\u0430\\u0434\\u044d\\u043c\\u0456\\u0447\\u043d\\u0430\\u044f) \\u00b7 \\u09ac\\u09bf\\u09b7\\u09cd\\u09a3\\u09c1\\u09aa\\u09cd\\u09b0\\u09bf\\u09af\\u09bc\\u09be \\u09ae\\u09a3\\u09bf\\u09aa\\u09c1\\u09b0\\u09c0 \\u00b7 Bosanski \\u00b7 Brezhoneg \\u00b7 \\u0411\\u044a\\u043b\\u0433\\u0430\\u0440\\u0441\\u043a\\u0438 \\u00b7 \\u010cesky \\u00b7 Cymraeg \\u00b7 Dansk \\u00b7 Eesti \\u00b7 \\u0395\\u03bb\\u03bb\\u03b7\\u03bd\\u03b9\\u03ba\\u03ac \\u00b7 Esperanto \\u00b7 Euskara \\u00b7 \\u0641\\u0627\\u0631\\u0633\\u06cc \\u00b7 Galego \\u00b7 \\ud55c\\uad6d\\uc5b4 \\u00b7 \\u0939\\u093f\\u0928\\u094d\\u0926\\u0940 \\u00b7 Hrvatski \\u00b7 Ido \\u00b7 Bahasa Indonesia \\u00b7 \\u00cdslenska \\u00b7 \\u05e2\\u05d1\\u05e8\\u05d9\\u05ea \\u00b7 Basa Jawa \\u00b7 \\u10e5\\u10d0\\u10e0\\u10d7\\u10e3\\u10da\\u10d8 \\u00b7 Kurd\\u00ee / \\u0643\\u0648\\u0631\\u062f\\u06cc \\u00b7 Latina \\u00b7 Lumbaart \\u00b7 Latvie\\u0161u \\u00b7 L\\u00ebtzebuergesch \\u00b7 Lietuvi\\u0173 \\u00b7 Magyar \\u00b7 \\u041c\\u0430\\u043a\\u0435\\u0434\\u043e\\u043d\\u0441\\u043a\\u0438 \\u00b7 \\u092e\\u0930\\u093e\\u0920\\u0940 \\u00b7 Bahasa Melayu \\u00b7 \\u0928\\u0947\\u092a\\u093e\\u0932 \\u092d\\u093e\\u0937\\u093e \\u00b7 Norsk (nynorsk) \\u00b7 Nnapulitano \\u00b7 Occitan \\u00b7 Piemont\\u00e8is \\u00b7 Plattd\\u00fc\\u00fctsch \\u00b7 Shqip \\u00b7 Sicilianu \\u00b7 Simple English \\u00b7 Sinugboanon \\u00b7 Sloven\\u010dina \\u00b7 Sloven\\u0161\\u010dina \\u00b7 \\u0421\\u0440\\u043f\\u0441\\u043a\\u0438 \\u00b7 Srpskohrvatski / \\u0421\\u0440\\u043f\\u0441\\u043a\\u043e\\u0445\\u0440\\u0432\\u0430\\u0442\\u0441\\u043a\\u0438 \\u00b7 Basa Sunda \\u00b7 Tagalog \\u00b7 \\u0ba4\\u0bae\\u0bbf\\u0bb4\\u0bcd \\u00b7 \\u0c24\\u0c46\\u0c32\\u0c41\\u0c17\\u0c41 \\u00b7 \\u0e44\\u0e17\\u0e22 \\u00b7 Ti\\u1ebfng Vi\\u1ec7t \\u00b7 Walon\n 1 000+ \nAfrikaans \\u00b7 Alemannisch \\u00b7 \\u12a0\\u121b\\u122d\\u129b \\u00b7 Aragon\\u00e9s \\u00b7 Arm\\u00e3neashce \\u00b7 Arpitan \\u00b7 B\\u00e2n-l\\u00e2m-g\\u00fa \\u00b7 Basa Banyumasan \\u00b7 \\u0411\\u0435\\u043b\\u0430\\u0440\\u0443\\u0441\\u043a\\u0430\\u044f (\\u0422\\u0430\\u0440\\u0430\\u0448\\u043a\\u0435\\u0432i\\u0446\\u0430) \\u00b7 \\u092d\\u094b\\u091c\\u092a\\u0941\\u0930\\u0940 \\u00b7 Boarisch \\u00b7 Corsu \\u00b7 \\u0427\\u0103\\u0432\\u0430\\u0448 \\u00b7 Deitsch \\u00b7 \\u078b\\u07a8\\u0788\\u07ac\\u0780\\u07a8 \\u00b7 Eald Englisc \\u00b7 F\\u00f8royskt \\u00b7 Frysk \\u00b7 Furlan \\u00b7 Gaeilge \\u00b7 Gaelg \\u00b7 G\\u00e0idhlig \\u00b7 \\u53e4\\u6587 / \\u6587\\u8a00\\u6587 \\u00b7 \\u02bb\\u014clelo Hawai\\u02bbi \\u00b7 \\u0540\\u0561\\u0575\\u0565\\u0580\\u0565\\u0576 \\u00b7 Hornjoserbsce \\u00b7 Ilokano \\u00b7 Interlingua \\u00b7 \\u0418\\u0440\\u043e\\u043d \\u00e6\\u0432\\u0437\\u0430\\u0433 \\u00b7 \\u0c95\\u0ca8\\u0ccd\\u0ca8\\u0ca1 \\u00b7 Kapampangan \\u00b7 Kasz\\u00ebbsczi \\u00b7 Kernewek \\u00b7 \\u1797\\u17b6\\u179f\\u17b6\\u1781\\u17d2\\u1798\\u17c2\\u179a \\u00b7 Ladino / \\u05dc\\u05d0\\u05d3\\u05d9\\u05e0\\u05d5 \\u00b7 Ligure \\u00b7 Limburgs \\u00b7 Ling\\u00e1la \\u00b7 \\u0d2e\\u0d32\\u0d2f\\u0d3e\\u0d33\\u0d02 \\u00b7 Malti \\u00b7 M\\u0101ori \\u00b7 \\u041c\\u043e\\u043d\\u0433\\u043e\\u043b \\u00b7 N\\u0101huatlaht\\u014dlli \\u00b7 Nedersaksisch \\u00b7 \\u0928\\u0947\\u092a\\u093e\\u0932\\u0940 \\u00b7 Nouormand \\u00b7 Novial \\u00b7 O\\u2018zbek \\u00b7 \\u092a\\u093e\\u0934\\u093f \\u00b7 Pangasin\\u00e1n \\u00b7 \\u067e\\u069a\\u062a\\u0648 \\u00b7 \\u049a\\u0430\\u0437\\u0430\\u049b\\u0448\\u0430 \\u00b7 Ripoarisch \\u00b7 Rumantsch \\u00b7 Runa Simi \\u00b7 \\u0938\\u0902\\u0938\\u094d\\u0915\\u0943\\u0924\\u092e\\u094d \\u00b7 S\\u00e1megiella \\u00b7 Scots \\u00b7 Kiswahili \\u00b7 Tarand\\u00edne \\u00b7 Tatar\\u00e7a \\u00b7 \\u0422\\u043e\\u04b7\\u0438\\u043a\\u04e3 \\u00b7 Lea faka-Tonga \\u00b7 T\\u00fcrkmen \\u00b7 \\u0627\\u0631\\u062f\\u0648 \\u00b7 V\\u00e8neto \\u00b7 V\\u00f5ro \\u00b7 West-Vlams \\u00b7 Winaray \\u00b7 \\u5434\\u8bed \\u00b7 \\u05d9\\u05d9\\u05b4\\u05d3\\u05d9\\u05e9 \\u00b7 \\u7cb5\\u8a9e \\u00b7 Yor\\u00f9b\\u00e1 \\u00b7 Zazaki \\u00b7 \\u017demait\\u0117\\u0161ka\n 100+ \n\\u0710\\u072a\\u0721\\u071d\\u0710 \\u00b7 Ava\\u00f1e\\u2019\\u1ebd \\u00b7 \\u0410\\u0432\\u0430\\u0440 \\u00b7 Aymara \\u00b7 Bamanankan \\u00b7 \\u0411\\u0430\\u0448\\u04a1\\u043e\\u0440\\u0442 \\u00b7 Bikol Central \\u00b7 \\u0f56\\u0f7c\\u0f51\\u0f0b\\u0f61\\u0f72\\u0f42 \\u00b7 Chamoru \\u00b7 Chavacano de Zamboanga \\u00b7 Bislama \\u00b7 Din\\u00e9 Bizaad \\u00b7 Dolnoserbski \\u00b7 Emigli\\u00e0n-Rumagn\\u00f2l \\u00b7 E\\u028begbe \\u00b7 \\u06af\\u06cc\\u0644\\u06a9\\u06cc \\u00b7 \\u0a97\\u0ac1\\u0a9c\\u0ab0\\u0abe\\u0aa4\\u0ac0 \\u00b7 \\U00010332\\U0001033f\\U00010344\\U00010339\\U00010343\\U0001033a \\u00b7 Hak-k\\u00e2-fa / \\u5ba2\\u5bb6\\u8a71 \\u00b7 Igbo \\u00b7 \\u1403\\u14c4\\u1483\\u144e\\u1450\\u1466 / Inuktitut \\u00b7 Interlingue \\u00b7 \\u0915\\u0936\\u094d\\u092e\\u0940\\u0930\\u0940 / \\u0643\\u0634\\u0645\\u064a\\u0631\\u064a \\u00b7 Kongo \\u00b7 \\u041a\\u044b\\u0440\\u0433\\u044b\\u0437\\u0447\\u0430 \\u00b7 \\u0e9e\\u0eb2\\u0eaa\\u0eb2\\u0ea5\\u0eb2\\u0ea7 \\u00b7 lojban \\u00b7 Malagasy \\u00b7 M\\u0101z\\u0259r\\u016bni / \\u0645\\u0627\\u0632\\u0650\\u0631\\u0648\\u0646\\u06cc \\u00b7 M\\u00ecng-d\\u0115\\u0324ng-ng\\u1e73\\u0304 \\u00b7 \\u041c\\u043e\\u043b\\u0434\\u043e\\u0432\\u0435\\u043d\\u044f\\u0441\\u043a\\u044d \\u00b7 \\u1017\\u1019\\u102c\\u1005\\u102c \\u00b7 Ekakair\\u0169 Naoero \\u00b7 N\\u0113hiyaw\\u0113win / \\u14c0\\u1426\\u1403\\u152d\\u140d\\u140f\\u1423 \\u00b7 Norfuk / Pitkern \\u00b7 \\u041d\\u043e\\u0445\\u0447\\u0438\\u0439\\u043d \\u00b7 \\u0b13\\u0b21\\u0b3c\\u0b3f\\u0b06 \\u00b7 Afaan Oromoo \\u00b7 \\u0985\\u09b8\\u09ae\\u09c0\\u09af\\u09bc\\u09be \\u00b7 \\u0a2a\\u0a70\\u0a1c\\u0a3e\\u0a2c\\u0a40 / \\u067e\\u0646\\u062c\\u0627\\u0628\\u06cc \\u00b7 Papiamentu \\u00b7 Q\\u0131r\\u0131mtatarca \\u00b7 Romani / \\u0930\\u094b\\u092e\\u093e\\u0928\\u0940 \\u00b7 Kinyarwanda \\u00b7 Gagana S\\u0101moa \\u00b7 Sardu \\u00b7 Seeltersk \\u00b7 \\u0dc3\\u0dd2\\u0d82\\u0dc4\\u0dbd \\u00b7 \\u0633\\u0646\\u068c\\u064a \\u00b7 \\u0421\\u043b\\u043e\\u0432\\u0463\\u043d\\u044c\\u0441\\u043a\\u044a \\u00b7 Af Soomaali \\u00b7 SiSwati \\u00b7 Reo Tahiti \\u00b7 Taqbaylit \\u00b7 Tetun \\u00b7 \\u1275\\u130d\\u122d\\u129b \\u00b7 Tok Pisin \\u00b7 \\u13e3\\u13b3\\u13a9 \\u00b7 \\u0423\\u0434\\u043c\\u0443\\u0440\\u0442 \\u00b7 Uyghur / \\u0626\\u06c7\\u064a\\u063a\\u06c7\\u0631\\u0686\\u0647 \\u00b7 Tshiven\\u1e13a \\u00b7 Wollof \\u00b7 isiXhosa \\u00b7 Ze\\u00eauws \\u00b7 isiZulu\nOther languages \\u00b7 Weitere Sprachen \\u00b7 \\u4ed6\\u306e\\u8a00\\u8a9e \\u00b7 Kompletna lista j\\u0119zyk\\u00f3w \\u00b7 \\u5176\\u4ed6\\u8bed\\u8a00 \\u00b7 \\u0414\\u0440\\u0443\\u0433\\u0438\\u0435 \\u044f\\u0437\\u044b\\u043a\\u0438 \\u00b7 Aliaj lingvoj \\u00b7 \\ub2e4\\ub978 \\uc5b8\\uc5b4 \\u00b7 Ng\\u00f4n ng\\u1eef kh\\u00e1c""")
        self.db.close()

        for encoding in "UTF-16", "UTF-16le", "UTF-16be", "UTF-8":
            if os.path.exists(TESTFILEPREFIX+"testdb"):
                deletefile(TESTFILEPREFIX+"testdb")
            db=apsw.Connection(TESTFILEPREFIX+"testdb")
            c=db.cursor()
            c.execute("pragma encoding=\"%s\"" % (encoding,))
            for row in c.execute("pragma encoding"):
                # we use startswith as UTF-16 will be returned with le/be suffix
                self.assertTrue(row[0].startswith(encoding))
            c.execute("create table foo(x); insert into foo values(?)", (text,))
            for row in c.execute("select * from foo"):
                self.assertEqual(row[0], text)
            db.close()


    # calls that need protection
    calls={
        'sqlite3api': { # items of interest - sqlite3 calls
                        'match': re.compile(r"(sqlite3_[A-Za-z0-9_]+)\s*\("),
                        # what must also be on same or preceding line
                        'needs': re.compile("PYSQLITE(_|_BLOB_|_CON_|_CUR_|_SC_|_VOID_|_BACKUP_)CALL"),

           # except if match.group(1) matches this - these don't
           # acquire db mutex so no need to wrap (determined by
           # examining sqlite3.c).  If they acquire non-database
           # mutexes then that is ok.

           # In the case of sqlite3_result_*|declare_vtab, the mutex
           # is already held by enclosing sqlite3_step and the
           # methods will only be called from that same thread so it
           # isn't a problem.
                        'skipcalls': re.compile("^sqlite3_(blob_bytes|column_count|bind_parameter_count|data_count|vfs_.+|changes|total_changes|get_autocommit|last_insert_rowid|complete|interrupt|limit|free|threadsafe|value_.+|libversion|enable_shared_cache|initialize|shutdown|config|memory_.+|soft_heap_limit(64)?|randomness|db_readonly|db_filename|release_memory|status64|result_.+|user_data|mprintf|aggregate_context|declare_vtab|backup_remaining|backup_pagecount|sourceid|uri_.+)$"),
                        # also ignore this file
                        'skipfiles': re.compile(r"[/\\]apsw.c$"),
                        # error message
                        'desc': "sqlite3_ calls must wrap with PYSQLITE_CALL",
                        },
        'inuse':        {
                        'match': re.compile(r"(convert_column_to_pyobject|statementcache_prepare|statementcache_finalize|statementcache_next)\s*\("),
                        'needs': re.compile("INUSE_CALL"),
                        'desc': "call needs INUSE wrapper",
                        },
        }
    def sourceCheckMutexCall(self, filename, name, lines):
        # we check that various calls are wrapped with various macros
        for i,line in enumerate(lines):
            if "PYSQLITE_CALL" in line and "Py" in line:
                self.fail("%s: %s() line %d - Py call while GIL released - %s" % (filename, name, i, line.strip()))
            for k,v in self.calls.items():
                if v.get('skipfiles', None) and v['skipfiles'].match(filename):
                    continue
                mo=v['match'].search(line)
                if mo:
                    func=mo.group(1)
                    if v.get('skipcalls', None) and v['skipcalls'].match(func):
                        continue
                    if not v["needs"].search(line) and not v["needs"].search(lines[i-1]):
                        self.fail("%s: %s() line %d call to %s(): %s - %s\n" % (filename, name, i, func, v['desc'], line.strip()))

    def sourceCheckFunction(self, filename, name, lines):
        # not further checked
        if name.split("_")[0] in ("ZeroBlobBind", "APSWVFS", "APSWVFSFile", "APSWBuffer", "FunctionCBInfo", "apswurifilename") :
                return

        checks={
            "APSWCursor":
                {
                  "skip": ("dealloc", "init", "dobinding", "dobindings", "doexectrace", "dorowtrace", "step", "close", "close_internal"),
                  "req":
                      {
                         "use": "CHECK_USE",
                         "closed": "CHECK_CURSOR_CLOSED",
                      },
                  "order": ("use", "closed")
                },

            "Connection":
                {
                  "skip": ("internal_cleanup", "dealloc", "init", "close", "interrupt", "close_internal", "remove_dependent", "readonly", "getmainfilename", "db_filename"),
                  "req":
                      {
                         "use": "CHECK_USE",
                         "closed": "CHECK_CLOSED",
                      },
                  "order": ("use", "closed")
                },

            "APSWBlob":
               {
                  "skip":  ("dealloc", "init", "close", "close_internal"),
                  "req":
                      {
                        "use": "CHECK_USE",
                        "closed": "CHECK_BLOB_CLOSED"
                      },
                  "order": ("use", "closed")
               },
            "APSWBackup":
               {
                  "skip": ("dealloc", "init", "close_internal",
                           "get_remaining", "get_pagecount"),
                  "req":
                      {
                        "use":  "CHECK_USE",
                        "closed": "CHECK_BACKUP_CLOSED"
                      },
                  "order": ("use", "closed")
               },
            "apswvfs":
               {
                 "req":
                      {
                        "preamble": "VFSPREAMBLE",
                        "tb": "AddTraceBackHere",
                        "postamble": "VFSPOSTAMBLE"
                      },
                 "order": ("preamble", "tb", "postamble")
               },
            "apswvfspy":
               {
                "req":
                     {
                        "check": "CHECKVFSPY",
                        "notimpl": "VFSNOTIMPLEMENTED(%(base)s,"
                     },
                "order": ("check", "notimpl"),
               },
            "apswvfspy_unregister":
               {
               "req":
                    {
                        "check": "CHECKVFSPY",
                    },
               },
            "apswvfsfile":
               {
                 "req":
                      {
                        "preamble": "FILEPREAMBLE",
                        "postamble": "FILEPOSTAMBLE",
                      },
                 "order": ("preamble", "postamble")
               },
            "apswvfsfilepy":
               {
               "skip": ("xClose", ),
                "req":
                     {
                        "check": "CHECKVFSFILEPY",
                        "notimpl": "VFSFILENOTIMPLEMENTED(%(base)s,"
                     },
                "order": ("check", "notimpl"),
               },

            }

        prefix,base=name.split("_", 1)
        if name in checks:
            checker=checks[name]
        elif prefix in checks:
            checker=checks[prefix]
        else:
            self.fail(filename+": "+prefix+" not in checks")

        if base in checker.get("skip", ()):
            return

        format={"base": base, "prefix": prefix}

        found={}
        for k in checker["req"]:
            found[k]=None

        # check the lines
        for i,line in enumerate(lines):
            for k,v in checker["req"].items():
                v=v % format
                if v in line and found[k] is None:
                    found[k]=i

        # check they are present
        for k,v in checker["req"].items():
            if found[k] is None:
                v=v%format
                self.fail(filename+": "+k+" "+v+" missing in "+name)

        # check order
        order=checker.get("order", ())
        for i in range(len(order)-2):
            b4=order[i]
            after=order[i+1]
            if found[b4]>found[after]:
                self.fail(filename+": "+checker["req"][b4]%format+" should be before "+checker["req"][after]%format+" in "+name)

        return

    def testSourceChecks(self):
        "Check various source code issues"
        # We expect a coding style where the functions are named
        # Object_method, are at the start of the line and have a first
        # parameter named self.
        if not os.path.exists("src/apsw.c"): return

        for filename in glob.glob("src/*.c"):
            # check not using C++ style comments
            code=read_whole_file(filename, "rt").replace("http://", "http:__").replace("https://", "https:__")
            if "//" in code:
                self.fail("// style comment in "+filename)

            # check check funcs
            funcpat1=re.compile(r"^(\w+_\w+)\s*\(\s*\w+\s*\*\s*self")
            funcpat2=re.compile(r"^(\w+)\s*\(")
            name1=None
            name2=None
            lines=[]
            infunc=0
            for line in read_whole_file(filename, "rt").split("\n"):
                if line.startswith("}") and infunc:
                    if infunc==1:
                        self.sourceCheckMutexCall(filename, name1, lines)
                        self.sourceCheckFunction(filename, name1, lines)
                    elif infunc==2:
                        self.sourceCheckMutexCall(filename, name2, lines)
                    else:
                        assert False
                    infunc=0
                    lines=[]
                    name1=None
                    name2=None
                    continue
                if name1 and line.startswith("{"):
                    infunc=1
                    continue
                if name2 and line.startswith("{"):
                    infunc=2
                    continue
                if infunc:
                    lines.append(line)
                    continue
                m=funcpat1.match(line)
                if m:
                    name1=m.group(1)
                    continue
                m=funcpat2.match(line)
                if m:
                    name2=m.group(1)
                    continue

    def testConfig(self):
        "Verify sqlite3_config wrapper"
        # we need to ensure there are no outstanding sqlite objects
        self.db=None
        gc.collect()
        self.assertRaises(apsw.MisuseError, apsw.config, apsw.SQLITE_CONFIG_MEMSTATUS, True)
        apsw.shutdown()
        try:
            self.assertRaises(TypeError, apsw.config)
            self.assertRaises(TypeError, apsw.config, "chicken")
            apsw.config(apsw.SQLITE_CONFIG_SINGLETHREAD)
            apsw.config(long(apsw.SQLITE_CONFIG_SINGLETHREAD))
            self.assertRaises(TypeError, apsw.config, apsw.SQLITE_CONFIG_SINGLETHREAD, 2)
            self.assertRaises(TypeError, apsw.config, apsw.SQLITE_CONFIG_MEMSTATUS)
            apsw.config(apsw.SQLITE_CONFIG_MEMSTATUS, True)
            apsw.config(apsw.SQLITE_CONFIG_MEMSTATUS, False)
            self.assertRaises(TypeError, apsw.config, 89748937)
            x=long(0x7fffffff)
            self.assertRaises(OverflowError, apsw.config, x*x*x*x)
            self.assertTrue(apsw.config(apsw.SQLITE_CONFIG_PCACHE_HDRSZ)>=0);
            apsw.config(apsw.SQLITE_CONFIG_PMASZ, -1)
        finally:
            # put back to normal
            apsw.config(apsw.SQLITE_CONFIG_SERIALIZED)
            apsw.config(apsw.SQLITE_CONFIG_MEMSTATUS, True)
            apsw.initialize()

    def testMemory(self):
        "Verify memory tracking functions"
        self.assertNotEqual(apsw.memoryused(), 0)
        self.assertTrue(apsw.memoryhighwater() >= apsw.memoryused())
        self.assertRaises(TypeError, apsw.memoryhighwater, "eleven")
        apsw.memoryhighwater(True)
        self.assertEqual(apsw.memoryhighwater(), apsw.memoryused())
        self.assertRaises(TypeError, apsw.softheaplimit, 1, 2)
        apsw.softheaplimit(0)
        self.assertRaises(TypeError, apsw.releasememory, 1, 2)
        res=apsw.releasememory(0x7fffffff)
        self.assertTrue(type(res) in (int, long))
        apsw.softheaplimit(l("0x1234567890abc"))
        self.assertEqual(l("0x1234567890abc"), apsw.softheaplimit(l("0x1234567890abe")))

    def testRandomness(self):
        "Verify randomness routine"
        self.assertRaises(TypeError, apsw.randomness, "three")
        self.assertRaises(OverflowError, apsw.randomness, l("0xffffffffee"))
        self.assertRaises(ValueError, apsw.randomness, -2)
        self.assertEqual(0, len(apsw.randomness(0)))
        self.assertEqual(1, len(apsw.randomness(1)))
        self.assertEqual(16383, len(apsw.randomness(16383)))
        self.assertNotEqual(apsw.randomness(77), apsw.randomness(77))

    def testSqlite3Pointer(self):
        "Verify getting underlying sqlite3 pointer"
        self.assertRaises(TypeError, self.db.sqlite3pointer, 7)
        self.assertTrue(type(self.db.sqlite3pointer()) in (int,long))
        self.assertEqual(self.db.sqlite3pointer(), self.db.sqlite3pointer())
        self.assertNotEqual(self.db.sqlite3pointer(), apsw.Connection(":memory:").sqlite3pointer())

    def testPickle(self, module=None):
        "Verify data etc can be pickled"
        if module==None:
            import pickle
            self.testPickle(pickle)
            try:
                import cPickle
                self.testPickle(cPickle)
            except ImportError:
                pass
            return

        import pickle
        PicklingError=pickle.PicklingError
        try:
            import cPickle
            PicklingError=(PicklingError, cPickle.PicklingError)
        except ImportError:
            pass

        # work out what protocol versions we can use
        versions=[]
        for num in range(-1, 20):
            try:
                module.dumps(3, num)
                versions.append(num)
            except ValueError:
                pass

        # some objects to try pickling
        vals=test_types_vals
        cursor=self.db.cursor()
        cursor.execute("create table if not exists t(i,x)")
        def canpickle(val):
            if py3: return True
            # Python <= 2.5 wide builds screws up unicode codepoints
            # above 0xffff with pickle
            if sys.version_info<(2,6) and isinstance(val, unicode):
                for a in val:
                    if ord(a)>0xffff:
                        return False

            return not isinstance(val, buffer)

        cursor.execute("BEGIN")
        cursor.executemany("insert into t values(?,?)", [(i,v) for i,v in enumerate(vals) if canpickle(v)])
        cursor.execute("COMMIT")

        for ver in versions:
            for row in cursor.execute("select * from t"):
                self.assertEqual(row, module.loads(module.dumps(row, ver)))
                rownum, val=row
                if type(vals[rownum]) is float:
                    self.assertAlmostEqual(vals[rownum], val)
                else:
                    self.assertEqual(vals[rownum], val)
            # can't pickle cursors
            try:
                module.dumps(cursor, ver)
            except TypeError:
                pass
            except PicklingError:
                pass
            # some versions can pickle the db, but give a zeroed db back
            db=None
            try:
                db=module.loads(module.dumps(self.db, ver))
            except TypeError:
                pass
            if db is not None:
                self.assertRaises(apsw.ConnectionClosedError, db.db_filename, "main")
                self.assertRaises(apsw.ConnectionClosedError, db.cursor)
                self.assertRaises(apsw.ConnectionClosedError, db.getautocommit)

    def testStatus(self):
        "Verify status function"
        self.assertRaises(TypeError, apsw.status, "zebra")
        self.assertRaises(apsw.MisuseError, apsw.status, 2323)
        for i in apsw.mapping_status:
            if type(i)!=type(""): continue
            res=apsw.status(getattr(apsw, i))
            self.assertEqual(len(res), 2)
            self.assertEqual(type(res), tuple)
            self.assertTrue(res[0]<=res[1])

    def testDBStatus(self):
        "Verify db status function"
        self.assertRaises(TypeError, self.db.status, "zebra")
        self.assertRaises(apsw.SQLError, self.db.status, 2323)
        for i in apsw.mapping_db_status:
            if type(i)!=type(""): continue
            res=self.db.status(getattr(apsw, i))
            self.assertEqual(len(res), 2)
            self.assertEqual(type(res), tuple)
            if i!="SQLITE_DBSTATUS_CACHE_USED":
                self.assertTrue(res[0]<=res[1])

    def testZeroBlob(self):
        "Verify handling of zero blobs"
        self.assertRaises(TypeError, apsw.zeroblob)
        self.assertRaises(TypeError, apsw.zeroblob, "foo")
        self.assertRaises(TypeError, apsw.zeroblob, -7)
        self.assertRaises(TypeError, apsw.zeroblob, size=27)
        self.assertRaises(OverflowError, apsw.zeroblob, 4000000000)
        cur=self.db.cursor()
        cur.execute("create table foo(x)")
        cur.execute("insert into foo values(?)", (apsw.zeroblob(27),))
        v=next(cur.execute("select * from foo"))[0]
        self.assertEqual(v, b(r"\x00"*27))
        # Make sure inheritance works
        class multi:
            def __init__(self, *args):
                self.foo=3
        class derived(apsw.zeroblob):
            def __init__(self, num):
                #multi.__init__(self)
                apsw.zeroblob.__init__(self, num)
        cur.execute("delete from foo; insert into foo values(?)", (derived(28),))
        v=next(cur.execute("select * from foo"))[0]
        self.assertEqual(v, b(r"\x00"*28))
        self.assertEqual(apsw.zeroblob(91210).length(), 91210)

    def testBlobIO(self):
        "Verify Blob input/output"
        cur=self.db.cursor()
        rowid=next(cur.execute("create table foo(x blob); insert into foo values(zeroblob(98765)); select rowid from foo"))[0]
        self.assertRaises(TypeError, self.db.blobopen, 1)
        self.assertRaises(TypeError, self.db.blobopen, u("main"), "foo\xf3")
        if sys.version_info>=(2,4):
            # Bug in python 2.3 gives internal error when complex is
            # passed to PyArg_ParseTuple for Long instead of raising
            # TypeError.  Corrected in 2.4
            self.assertRaises(TypeError, self.db.blobopen, u("main"), "foo", "x", complex(-1,-1), True)
        self.assertRaises(TypeError, self.db.blobopen, u("main"), "foo", "x", rowid, True, False)
        self.assertRaises(apsw.SQLError, self.db.blobopen, "main", "foo", "x", rowid+27, False)
        self.assertRaises(apsw.SQLError, self.db.blobopen, "foo", "foo" , "x", rowid, False)
        self.assertRaises(apsw.SQLError, self.db.blobopen, "main", "x" , "x", rowid, False)
        self.assertRaises(apsw.SQLError, self.db.blobopen, "main", "foo" , "y", rowid, False)
        blobro=self.db.blobopen("main", "foo", "x", rowid, False)
        # sidebar: check they can't be manually created
        self.assertRaises(TypeError, type(blobro))
        # check vals
        self.assertEqual(blobro.length(), 98765)
        self.assertEqual(blobro.length(), 98765)
        self.assertEqual(blobro.read(0), BYTES(""))
        zero=BYTES(r"\x00")
        step=5 # must be exact multiple of size
        assert(blobro.length()%step==0)
        for i in range(0,98765,step):
            x=blobro.read(step)
            self.assertEqual(zero*step, x)
        x=blobro.read(10)
        self.assertEqual(x, BYTES(""))
        blobro.seek(0,1)
        self.assertEqual(blobro.tell(), 98765)
        blobro.seek(0)
        self.assertEqual(blobro.tell(), 0)
        self.assertEqual(len(blobro.read(11119999)), 98765)
        blobro.seek(2222)
        self.assertEqual(blobro.tell(), 2222)
        blobro.seek(0,0)
        self.assertEqual(blobro.tell(), 0)
        self.assertEqual(blobro.read(), BYTES(r"\x00"*98765))
        blobro.seek(-3,2)
        self.assertEqual(blobro.read(), BYTES(r"\x00"*3))
        # check types
        self.assertRaises(TypeError, blobro.read, "foo")
        self.assertRaises(TypeError, blobro.tell, "foo")
        self.assertRaises(TypeError, blobro.seek)
        self.assertRaises(TypeError, blobro.seek, "foo", 1)
        self.assertRaises(TypeError, blobro.seek, 0, 1, 2)
        self.assertRaises(ValueError, blobro.seek, 0, -3)
        self.assertRaises(ValueError, blobro.seek, 0, 3)
        # can't seek before begining or after end of file
        self.assertRaises(ValueError, blobro.seek, -1, 0)
        self.assertRaises(ValueError, blobro.seek, 25, 1)
        self.assertRaises(ValueError, blobro.seek, 25, 2)
        self.assertRaises(ValueError, blobro.seek, 100000, 0)
        self.assertRaises(ValueError, blobro.seek, -100000, 1)
        self.assertRaises(ValueError, blobro.seek, -100000, 2)
        # close testing
        blobro.seek(0,0)
        self.assertRaises(apsw.ReadOnlyError, blobro.write, b("kermit was here"))
        # you get the error on the close too, and blob is always closed - sqlite ticket #2815
        self.assertRaises(apsw.ReadOnlyError, blobro.close)
        # check can't work on closed blob
        self.assertRaises(ValueError, blobro.read)
        self.assertRaises(ValueError, blobro.readinto, BYTES("ab"))
        self.assertRaises(ValueError, blobro.seek, 0, 0)
        self.assertRaises(ValueError, blobro.tell)
        self.assertRaises(ValueError, blobro.write, "abc")
        # readinto tests
        rowidri=self.db.cursor().execute("insert into foo values(x'112233445566778899aabbccddeeff'); select last_insert_rowid()").fetchall()[0][0]
        blobro=self.db.blobopen("main", "foo", "x", rowidri, False)
        self.assertRaises(TypeError, blobro.readinto)
        self.assertRaises(TypeError, blobro.readinto, 3)
        buffers=[]
        import array
        if sys.version_info<(3,):
            buffers.append(array.array("c", "\0\0\0\0"))
        else:
            buffers.append(array.array("b", b(r"\0\0\0\0")))

        if sys.version_info>=(2,6):
            if sys.version_info<(3,):
                buffers.append(bytearray("\0\0\0\0"))
            else:
                buffers.append(bytearray(b(r"\0\0\0\0")))
        # bytearray returns ints rather than chars so a fixup
        def _fixup(c):
            if type(c)==int:
                if py3:
                    return bytes([c])
                else:
                    return chr(c)
            return c

        for buf in buffers:
            self.assertRaises(TypeError, blobro.readinto)
            self.assertRaises(TypeError, blobro.readinto, buf, buf)
            self.assertRaises(TypeError, blobro.readinto, buf, 1, buf)
            self.assertRaises(TypeError, blobro.readinto, buf, 1, 1, buf)
            blobro.seek(0)
            blobro.readinto(buf, 1, 1)
            self.assertEqual(_fixup(buf[0]), BYTES(r"\x00"))
            self.assertEqual(_fixup(buf[1]), BYTES(r"\x11"))
            self.assertEqual(_fixup(buf[2]), BYTES(r"\x00"))
            self.assertEqual(_fixup(buf[3]), BYTES(r"\x00"))
            self.assertEqual(len(buf), 4)
            blobro.seek(3)
            blobro.readinto(buf)
            def check_unchanged():
                self.assertEqual(_fixup(buf[0]), BYTES(r"\x44"))
                self.assertEqual(_fixup(buf[1]), BYTES(r"\x55"))
                self.assertEqual(_fixup(buf[2]), BYTES(r"\x66"))
                self.assertEqual(_fixup(buf[3]), BYTES(r"\x77"))
                self.assertEqual(len(buf), 4)
            check_unchanged()
            blobro.seek(14)
            # too much requested
            self.assertRaises(ValueError, blobro.readinto, buf, 1)
            check_unchanged()
            # bounds errors
            self.assertRaises(ValueError, blobro.readinto, buf, 1, -1)
            self.assertRaises(ValueError, blobro.readinto, buf, 1, 7)
            self.assertRaises(ValueError, blobro.readinto, buf, -1, 2)
            self.assertRaises(ValueError, blobro.readinto, buf, 10000, 2)
            self.assertRaises(OverflowError, blobro.readinto, buf, 1, l("45236748972389749283"))
            check_unchanged()
        # get a read error
        blobro.seek(0)
        self.db.cursor().execute("update foo set x=x'112233445566' where rowid=?", (rowidri,))
        self.assertRaises(apsw.AbortError, blobro.readinto, buf)
        # should fail with buffer being a string
        self.assertRaises(TypeError, blobro.readinto, "abcd", 1, 1)
        self.assertRaises(TypeError, blobro.readinto, u("abcd"), 1, 1)
        if not py3:
            self.assertRaises(TypeError, blobro.readinto, buffer("abcd"), 1, 1)
        # write tests
        blobrw=self.db.blobopen("main", "foo", "x", rowid, True)
        self.assertEqual(blobrw.length(), 98765)
        blobrw.write(b("abcd"))
        blobrw.seek(0, 0)
        self.assertEqual(blobrw.read(4), BYTES("abcd"))
        blobrw.write(b("efg"))
        blobrw.seek(0, 0)
        self.assertEqual(blobrw.read(7), BYTES("abcdefg"))
        blobrw.seek(50, 0)
        blobrw.write(b("hijkl"))
        blobrw.seek(-98765, 2)
        self.assertEqual(blobrw.read(55), BYTES("abcdefg"+r"\x00"*43+"hijkl"))
        self.assertRaises(TypeError, blobrw.write, 12)
        self.assertRaises(TypeError, blobrw.write)
        self.assertRaises(TypeError, blobrw.write, u("foo"))
        # try to go beyond end
        self.assertRaises(ValueError, blobrw.write, b(" "*100000))
        self.assertRaises(TypeError, blobrw.close, "elephant")
        # coverage
        blobro=self.db.blobopen("main", "foo", "x", rowid, False)
        self.assertRaises(apsw.ReadOnlyError, blobro.write, b("abcd"))
        blobro.close(True)
        self.db.cursor().execute("insert into foo(_rowid_, x) values(99, 1)")
        blobro=self.db.blobopen("main", "foo", "x", rowid, False)
        self.assertRaises(TypeError, blobro.reopen)
        self.assertRaises(TypeError, blobro.reopen, "banana")
        self.assertRaises(OverflowError, blobro.reopen, l("45236748972389749283"))
        first=blobro.read(2)
        # check position is reset
        blobro.reopen(rowid)
        self.assertEqual(blobro.tell(), 0)
        self.assertEqual(first, blobro.read(2))
        # invalid reopen
        self.assertRaises(apsw.SQLError, blobro.reopen, l("0x1ffffffff"))
        blobro.close()


    def testBlobReadError(self):
        "Ensure blob read errors are handled well"
        cur=self.db.cursor()
        cur.execute("create table ioerror (x, blob)")
        cur.execute("insert into ioerror (rowid,x,blob) values (2,3,x'deadbeef')")
        blob=self.db.blobopen("main", "ioerror", "blob", 2, False)
        blob.read(1)
        # Do a write which cause blob to become invalid
        cur.execute("update ioerror set blob='fsdfdsfasd' where x=3")
        try:
            blob.read(1)
            1/0
        except:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.AbortError)

    def testURIFilenames(self):
        assertRaises=self.assertRaises
        assertEqual=self.assertEqual
        class TVFS(apsw.VFS):
            def __init__(self):
                apsw.VFS.__init__(self, "uritest", "")

            def xOpen(self, name, flags):
                assert isinstance(name, apsw.URIFilename)
                # The various errors
                assertRaises(TypeError, name.uri_parameter)
                assertRaises(TypeError, name.uri_parameter, 2)
                assertRaises(TypeError, name.uri_int)
                assertRaises(TypeError, name.uri_int, 7)
                assertRaises(TypeError, name.uri_int, 7, 7)
                assertRaises(TypeError, name.uri_int, 7, 7, 7)
                if sys.version_info>(2,4): # 2.3 does systemerror instead of typeerror
                    assertRaises(TypeError, name.uri_int, "seven", "seven")
                assertRaises(TypeError, name.uri_boolean, "seven")
                assertRaises(TypeError, name.uri_boolean, "seven", "seven")
                assertRaises(TypeError, name.uri_boolean, "seven", None)
                # Check values
                assert name.filename().endswith("testdb2")
                assertEqual(name.uri_parameter("notexist"), None)
                assertEqual(name.uri_parameter("foo"), "1&2=3")
                assertEqual(name.uri_int("foo", -7), -7)
                assertEqual(name.uri_int("bar", -7), 43242342)
                # https://sqlite.org/src/info/5f41597f7c
                # assertEqual(name.uri_boolean("foo", False), False)
                assertEqual(name.uri_boolean("bam", False), True)
                assertEqual(name.uri_boolean("baz", True), False)
                1/0

        testvfs=TVFS()
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, apsw.Connection, "file:testdb2?foo=1%262%3D3&bar=43242342&bam=true&baz=fal%73%65", flags=apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE | apsw.SQLITE_OPEN_URI, vfs="uritest")

    def testVFSWithWAL(self):
        "Verify VFS using WAL where possible"
        apsw.connection_hooks.append(lambda c: c.cursor().execute("pragma journal_mode=WAL"))
        try:
            self.testVFS()
        finally:
            apsw.connection_hooks.pop()

    def testVFS(self):
        "Verify VFS functionality"
        global testtimeout

        # Check basic functionality and inheritance - make an obfuscated provider

        # obfusvfs code
        def encryptme(data):
            # An "encryption" scheme in honour of MAPI and SQL server passwords
            if not data: return data
            if py3:
                return bytes([x^0xa5 for x in data])
            return "".join([chr(ord(x)^0xa5) for x in data])

        class ObfuscatedVFSFile(apsw.VFSFile):
            def __init__(self, inheritfromvfsname, filename, flags):
                apsw.VFSFile.__init__(self, inheritfromvfsname, filename, flags)

            def xRead(self, amount, offset):
                return encryptme(super(ObfuscatedVFSFile, self).xRead(amount, offset))

            def xWrite(self, data, offset):
                super(ObfuscatedVFSFile, self).xWrite(encryptme(data), offset)

        class ObfuscatedVFS(apsw.VFS):
            def __init__(self, vfsname="obfu", basevfs=""):
                self.vfsname=vfsname
                self.basevfs=basevfs
                apsw.VFS.__init__(self, self.vfsname, self.basevfs)

            def xOpen(self, name, flags):
                return ObfuscatedVFSFile(self.basevfs, name, flags)

        vfs=ObfuscatedVFS()

        query="create table foo(x,y); insert into foo values(1,2); insert into foo values(3,4)"
        self.db.cursor().execute(query)

        db2=apsw.Connection(TESTFILEPREFIX+"testdb2", vfs=vfs.vfsname)
        db2.cursor().execute(query)
        db2.close()
        waswal=self.db.cursor().execute("pragma journal_mode").fetchall()[0][0]=="wal"
        if waswal:
            self.db.cursor().execute("pragma journal_mode=delete").fetchall()
        self.db.close() # flush

        # check the two databases are the same (modulo the XOR)
        orig=read_whole_file(TESTFILEPREFIX+"testdb", "rb")
        obfu=read_whole_file(TESTFILEPREFIX+"testdb2", "rb")
        self.assertEqual(len(orig), len(obfu))
        self.assertNotEqual(orig, obfu)
        # wal isn't exactly the same
        if waswal:
            def compare(one, two):
                self.assertEqual(one[:27], two[:27])
                self.assertEqual(one[96:], two[96:])
        else:
            compare=self.assertEqual

        compare(orig, encryptme(obfu))

        # helper routines
        self.assertRaises(TypeError, apsw.exceptionfor, "three")
        self.assertRaises(ValueError, apsw.exceptionfor, 8764324)
        self.assertRaises(OverflowError, apsw.exceptionfor, l("0xffffffffffffffff10"))

        # test raw file object
        f=ObfuscatedVFSFile("", os.path.abspath(TESTFILEPREFIX+"testdb"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_READONLY, 0])
        del f # check closes
        f=ObfuscatedVFSFile("", os.path.abspath(TESTFILEPREFIX+"testdb"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_READONLY, 0])
        data=f.xRead(len(obfu), 0) # will encrypt it
        compare(obfu, data)
        f.xClose()
        f.xClose()
        f2=apsw.VFSFile("", os.path.abspath(TESTFILEPREFIX+"testdb"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_READONLY, 0])
        del f2
        f2=apsw.VFSFile("", os.path.abspath(TESTFILEPREFIX+"testdb2"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_READONLY, 0])
        data=f2.xRead(len(obfu), 0)
        self.assertEqual(obfu, data)
        f2.xClose()
        f2.xClose()

        # cleanup so it doesn't interfere with following code using the same file
        del f
        del f2
        db2.close()
        del db2
        vfs.unregister()
        gc.collect()

        ### Detailed vfs testing

        # xRandomness is tested first. The method is called once after sqlite initializes
        # and only the default vfs is called.  Consequently we have a helper test method
        # but it is only available when using testfixtures and the amalgamation
        self.db=None
        gc.collect()

        defvfs=apsw.vfsnames()[0] # we want to inherit from this one

        def testrand():
            gc.collect()
            apsw.test_reset_rng()
            vfs=RandomVFS()
            db=apsw.Connection(TESTFILEPREFIX+"testdb")
            next(db.cursor().execute("select randomblob(10)"))

        class RandomVFSUpper(apsw.VFS):
            def __init__(self):
                apsw.VFS.__init__(self, "randomupper", defvfs)

            def xRandomness1(self, n):
                return b(r"\xaa\xbb")

        class RandomVFS(apsw.VFS):
            def __init__(self):
                apsw.VFS.__init__(self, "random", "randomupper", makedefault=True)

            def xRandomness1(self, bad, number, of, arguments):
                1/0

            def xRandomness2(self, n):
                1/0

            def xRandomness3(self, n):
                return b("abcd")

            def xRandomness4(self, n):
                return u("abcd")

            def xRandomness5(self, n):
                return b("a")*(2*n)

            def xRandomness6(self, n):
                return None

            def xRandomness7(self, n):
                return 3

            def xRandomness99(self, n):
                return super(RandomVFS, self).xRandomness(n+2049)

        if hasattr(apsw, 'test_reset_rng'):
            vfsupper=RandomVFSUpper()
            vfs=RandomVFS()
            self.assertRaises(TypeError, vfs.xRandomness, "jksdhfsd")
            self.assertRaises(TypeError, vfs.xRandomness, 3, 3)
            self.assertRaises(ValueError, vfs.xRandomness, -88)

            RandomVFS.xRandomness=RandomVFS.xRandomness1
            self.assertRaisesUnraisable(TypeError, testrand)
            RandomVFS.xRandomness=RandomVFS.xRandomness2
            self.assertRaisesUnraisable(ZeroDivisionError, testrand)
            RandomVFS.xRandomness=RandomVFS.xRandomness3
            testrand() # shouldn't have problems
            RandomVFS.xRandomness=RandomVFS.xRandomness4
            self.assertRaisesUnraisable(TypeError, testrand)
            RandomVFS.xRandomness=RandomVFS.xRandomness5
            testrand() # shouldn't have problems
            RandomVFS.xRandomness=RandomVFS.xRandomness6
            testrand() # shouldn't have problems
            RandomVFS.xRandomness=RandomVFS.xRandomness7
            self.assertRaisesUnraisable(TypeError, testrand)
            RandomVFS.xRandomness=RandomVFS.xRandomness99
            testrand() # shouldn't have problems
            vfsupper.xRandomness=vfsupper.xRandomness1
            testrand() # coverage
            vfsupper.unregister()
            vfs.unregister()

        class ErrorVFS(apsw.VFS):
            # A vfs that returns errors for all methods
            def __init__(self):
                apsw.VFS.__init__(self, "errorvfs", "")

            def errorme(self, *args):
                raise apsw.exceptionfor(apsw.SQLITE_IOERR)


        class TestVFS(apsw.VFS):
            def init1(self):
                super(TestVFS, self).__init__("apswtest")

            def init99(self, name="apswtest", base=""):
                super(TestVFS, self).__init__(name, base)

            def xDelete1(self, name, syncdir):
                super(TestVFS, self).xDelete(".", False)

            def xDelete2(self, bad, number, of, args):
                1/0

            def xDelete3(self, name, syncdir):
                1/0

            def xDelete4(self, name, syncdir):
                super(TestVFS,self).xDelete("bad", "arguments")

            def xDelete99(self, name, syncdir):
                assert(type(name)== type(u("")))
                assert(type(syncdir)==type(1))
                return super(TestVFS, self).xDelete(name, syncdir)

            def xAccess1(self, bad, number, of, args):
                1/0

            def xAccess2(self, name, flags):
                1/0

            def xAccess3(self, name, flags):
                return super(TestVFS,self).xAccess("bad", "arguments")

            def xAccess4(self, name, flags):
                return (3,)

            def xAccess99(self, name, flags):
                assert(type(name) == type(u("")))
                assert(type(flags) == type(1))
                return super(TestVFS, self).xAccess(name, flags)

            def xFullPathname1(self, bad, number, of, args):
                1/0

            def xFullPathname2(self, name):
                1/0

            def xFullPathname3(self, name):
                return super(TestVFS, self).xFullPathname("bad", "args")

            def xFullPathname4(self, name):
                # parameter is larger than default buffer sizes used by sqlite
                return super(TestVFS, self).xFullPathname(name*10000)

            def xFullPathname5(self, name):
                # result is larger than default buffer sizes used by sqlite
                return "a"*10000

            def xFullPathname6(self, name):
                return 12 # bad return type

            def xFullPathname99(self, name):
                assert(type(name) == type(u("")))
                return super(TestVFS, self).xFullPathname(name)

            def xOpen1(self, bad, number, of, arguments):
                1/0

            def xOpen2(self, name, flags):
                super(TestVFS, self).xOpen(name, 3)
                1/0

            def xOpen3(self, name, flags):
                v=super(TestVFS, self).xOpen(name, flags)
                flags.append(v)
                return v

            def xOpen4(self, name, flags):
                return None

            def xOpen99(self, name, flags):
                assert(isinstance(name, apsw.URIFilename) or name is None or type(name)==type(u("")))
                assert(type(flags)==type([]))
                assert(len(flags)==2)
                assert(type(flags[0]) in (int,long))
                assert(type(flags[1]) in (int,long))
                return super(TestVFS, self).xOpen(name, flags)

            def xOpen100(self, name, flags):
                return TestFile(name, flags)

            def xDlOpen1(self, bad, number, of, arguments):
                1/0

            def xDlOpen2(self, name):
                1/0

            def xDlOpen3(self, name):
                return -1

            def xDlOpen4(self, name):
                return "fred"

            def xDlOpen5(self, name):
                return super(TestVFS, self).xDlOpen(3)

            # python 3 only test
            def xDlOpen6(self, name):
                return super(TestVFS, self).xDlOpen(b("abcd")) # bad string type

            def xDlOpen7(self, name):
                return l("0xffffffffffffffff10")

            def xDlOpen99(self, name):
                assert(type(name)==type(u("")))
                res=super(TestVFS, self).xDlOpen(name)
                if ctypes:
                    try:
                        cres=ctypes.cdll.LoadLibrary(name)._handle
                    except:
                        cres=0
                    assert(res==cres)
                return res

            def xDlSym1(self, bad, number, of, arguments):
                1/0

            def xDlSym2(self, handle, name):
                1/0

            def xDlSym3(self, handle, name):
                return "fred"

            def xDlSym4(self, handle, name):
                super(TestVFS, self).xDlSym(3,3)

            def xDlSym5(self, handle, name):
                return super(TestVFS, self).xDlSym(handle, b("abcd"))

            def xDlSym6(self, handle, name):
                return l("0xffffffffffffffff10")

            def xDlSym99(self, handle, name):
                assert(type(handle) in (int,long))
                assert(type(name) == type(u("")))
                res=super(TestVFS, self).xDlSym(handle, name)
                if not iswindows and _ctypes:
                    assert(_ctypes.dlsym (handle, name)==res)
                # windows has funky issues I don't want to deal with here
                return res

            def xDlClose1(self, bad, number, of, arguments):
                1/0

            def xDlClose2(self, handle):
                1/0

            def xDlClose3(self, handle):
                return super(TestVFS, self).xDlClose("three")

            def xDlClose99(self, handle):
                assert(type(handle) in (int,long))
                super(TestVFS,self).xDlClose(handle)

            def xDlError1(self, bad, number, of, arguments):
                1/0

            def xDlError2(self):
                1/0

            def xDlError3(self):
                return super(TestVFS, self).xDlError("three")

            def xDlError4(self):
                return 3

            def xDlError5(self):
                return b("abcd")

            def xDlError6(self):
                return None

            def xDlError99(self):
                return super(TestVFS,self).xDlError()

            def xSleep1(self, bad, number, of, arguments):
                1/0

            def xSleep2(self, microseconds):
                1/0

            def xSleep3(self, microseconds):
                return super(TestVFS, self).xSleep("three")

            def xSleep4(self, microseconds):
                return "three"

            def xSleep5(self, microseconds):
                return l("0xffffffff0")

            def xSleep6(self, microseconds):
                return l("0xffffffffeeeeeeee0")

            def xSleep99(self, microseconds):
                assert(type(microseconds) in (int, long))
                return super(TestVFS, self).xSleep(microseconds)

            def xCurrentTime1(self, bad, args):
                1/0

            def xCurrentTime2(self):
                1/0

            def xCurrentTime3(self):
                return super(TestVFS, self).xCurrentTime("three")

            def xCurrentTime4(self):
                return "three"

            def xCurrentTime5(self):
                return math.exp(math.pi)*26000

            def xCurrentTime99(self):
                return super(TestVFS, self).xCurrentTime()

            def xGetLastError1(self, bad, args):
                1/0

            def xGetLastError2(self):
                1/0

            def xGetLastError3(self):
                return super(TestVFS,self).xGetLastError("three")

            def xGetLastError4(self):
                return 3

            def xGetLastError5(self):
                return "a"*1500

            def xGetLastError99(self):
                return super(TestVFS,self).xGetLastError()

            def xNextSystemCall1(self, bad, args):
                1/0

            def xNextSystemCall2(self, name):
                return 3

            def xNextSystemCall3(self, name):
                return "foo\xf3"

            def xNextSystemCall4(self, name):
                1/0

            def xNextSystemCall99(self, name):
                return super(TestVFS,self).xNextSystemCall(name)

            def xGetSystemCall1(self, bad, args):
                1/0

            def xGetSystemCall2(self, name):
                1/0

            def xGetSystemCall3(self, name):
                return "fred"

            def xGetSystemCall4(self, name):
                return 3.7

            def xGetSystemCall99(self, name):
                return super(TestVFS,self).xGetSystemCall(name)

            def xSetSystemCall1(self, bad, args, args3):
                1/0

            def xSetSystemCall2(self, name, ptr):
                1/0

            def xSetSystemCall3(self, name, ptr):
                raise apsw.NotFoundError()

            def xSetSystemCall99(self, name, ptr):
                return super(TestVFS,self).xSetSystemCall(name, ptr)

        class TestFile(apsw.VFSFile):
            def init1(self, name, flags):
                super(TestFile, self).__init__("bogus", "arguments")

            def init2(self, name, flags):
                super(TestFile, self).__init__("bogus", 3, 4)

            def init3(self, name, flags):
                super(TestFile, self).__init__("bogus", "4", 4)

            def init4(self, name, flags):
                super(TestFile, self).__init__("bogus", "4", [4,4,4,4])

            def init5(self, name, flags):
                super(TestFile, self).__init__("", name, [l("0xffffffffeeeeeeee0"), l("0xffffffffeeeeeeee0")])

            def init6(self, name, flags):
                super(TestFile, self).__init__("", name, [l("0xffffffffa"), 0]) # 64 bit int vs long overflow

            def init7(self, name, flags):
                super(TestFile, self).__init__("", name, (6, 7))

            def init8(self, name, flags):
                super(TestFile, self).__init__("bogus", name, flags)

            def init9(self, name, flags):
                super(TestFile, self).__init__("", name, (6, "six"))

            def init10(self, name, flags):
                class badlist(list): # only allows setting an element once
                    def __init__(self, *args):
                        super(badlist, self).__init__(args)
                        self.frozen=False
                    def __setitem__(self,  key, value):
                        if self.frozen:
                            raise ValueError("container is frozen")
                        super(badlist, self).__setitem__(key, value)
                        self.frozen=True
                super(TestFile, self).__init__("", name, badlist(flags[0], flags[1]))

            def init99(self, name, flags):
                super(TestFile, self).__init__("", name, flags)

            def xRead1(self, bad, number, of, arguments):
                1/0

            def xRead2(self, amount, offset):
                1/0

            def xRead3(self, amount, offset):
                return 3

            def xRead4(self, amount, offset):
                return u("a")*amount

            def xRead5(self, amount, offset):
                return super(TestFile, self).xRead(amount-1, offset)

            def xRead99(self, amount, offset):
                return super(TestFile, self).xRead(amount, offset)

            def xWrite1(self, bad, number, of, arguments):
                1/0

            def xWrite2(self, buffy, offset):
                1/0

            def xWrite99(self, buffy, offset):
                return super(TestFile, self).xWrite(buffy, offset)

            def xUnlock1(self, bad, number, of, arguments):
                1/0

            def xUnlock2(self, level):
                1/0

            def xUnlock99(self, level):
                return super(TestFile, self).xUnlock(level)

            def xLock1(self, bad, number, of, arguments):
                1/0

            def xLock2(self, level):
                1/0

            def xLock99(self, level):
                return super(TestFile, self).xLock(level)

            def xTruncate1(self, bad, number, of, arguments):
                1/0

            def xTruncate2(self, size):
                1/0

            def xTruncate99(self, size):
                return super(TestFile, self).xTruncate(size)

            def xSync1(self, bad, number, of, arguments):
                1/0

            def xSync2(self, flags):
                1/0

            def xSync99(self, flags):
                return super(TestFile, self).xSync(flags)

            def xSectorSize1(self, bad, number, of, args):
                1/0

            def xSectorSize2(self):
                1/0

            def xSectorSize3(self):
                return "three"

            def xSectorSize4(self):
                return l("0xffffffffeeeeeeee0")

            def xSectorSize99(self):
                return super(TestFile, self).xSectorSize()

            def xDeviceCharacteristics1(self, bad, number, of, args):
                1/0

            def xDeviceCharacteristics2(self):
                1/0

            def xDeviceCharacteristics3(self):
                return "three"

            def xDeviceCharacteristics4(self):
                return l("0xffffffffeeeeeeee0")

            def xDeviceCharacteristics99(self):
                return super(TestFile, self).xDeviceCharacteristics()

            def xFileSize1(self, bad, number, of, args):
                1/0

            def xFileSize2(self):
                1/0

            def xFileSize3(self):
                return "three"

            def xFileSize4(self):
                return l("0xffffffffeeeeeeee0")

            def xFileSize99(self):
                res=super(TestFile, self).xFileSize()
                if res<100000:
                    return int(res)
                return res

            def xCheckReservedLock1(self, bad, number, of, args):
                1/0

            def xCheckReservedLock2(self):
                1/0

            def xCheckReservedLock3(self):
                return "three"

            def xCheckReservedLock4(self):
                return l("0xffffffffeeeeeeee0")

            def xCheckReservedLock99(self):
                return super(TestFile,self).xCheckReservedLock()

            def xFileControl1(self, bad, number, of, args):
                1/0

            def xFileControl2(self, op, ptr):
                1/0

            def xFileControl3(self, op, ptr):
                return "banana"

            def xFileControl99(self, op, ptr):
                if op==1027:
                    assert(ptr==1027)
                elif op==1028:
                    if ctypes:
                        assert(True is ctypes.py_object.from_address(ptr).value)
                else:
                    return super(TestFile, self).xFileControl(op, ptr)
                return True

        # check initialization
        self.assertRaises(TypeError, apsw.VFS, "3", 3)
        self.assertRaises(ValueError, apsw.VFS, "never", "klgfkljdfsljgklfjdsglkdfs")
        self.assertTrue("never" not in apsw.vfsnames())
        TestVFS.__init__=TestVFS.init1
        vfs=TestVFS()
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, apsw.VFSNotImplementedError, testdb)
        del vfs
        gc.collect()
        TestVFS.__init__=TestVFS.init99
        vfs=TestVFS()

        # Should work without any overridden methods
        testdb()

        ## xDelete
        self.assertRaises(TypeError, vfs.xDelete, "bogus", "arguments")
        TestVFS.xDelete=TestVFS.xDelete1
        err=[apsw.IOError, apsw.IOError][iswindows]
        self.assertRaises(err, self.assertRaisesUnraisable, err, testdb)
        TestVFS.xDelete=TestVFS.xDelete2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xDelete=TestVFS.xDelete3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestVFS.xDelete=TestVFS.xDelete4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xDelete=TestVFS.xDelete99
        testdb()

        ## xAccess
        self.assertRaises(TypeError, vfs.xAccess, "bogus", "arguments")
        TestVFS.xAccess=TestVFS.xAccess1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xAccess=TestVFS.xAccess2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestVFS.xAccess=TestVFS.xAccess3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xAccess=TestVFS.xAccess4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xAccess=TestVFS.xAccess99
        if iswindows:
            self.assertRaises(apsw.IOError, vfs.xAccess, u("<bad<filename:"), apsw.SQLITE_ACCESS_READWRITE)
        else:
            self.assertEqual(False, vfs.xAccess(u("<bad<filename:"), apsw.SQLITE_ACCESS_READWRITE))
            self.assertEqual(True, vfs.xAccess(u("."), apsw.SQLITE_ACCESS_EXISTS))
        # unix vfs doesn't ever return error so we have to indirect through one of ours
        errvfs=ErrorVFS()
        errvfs.xAccess=errvfs.errorme
        vfs2=TestVFS("apswtest2", "errorvfs")
        self.assertRaises(apsw.IOError, self.assertRaisesUnraisable, apsw.IOError, testdb, vfsname="apswtest2")
        del vfs2
        del errvfs
        gc.collect()

        ## xFullPathname
        self.assertRaises(TypeError, vfs.xFullPathname, "bogus", "arguments")
        self.assertRaises(TypeError, vfs.xFullPathname, 3)
        TestVFS.xFullPathname=TestVFS.xFullPathname1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xFullPathname=TestVFS.xFullPathname2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestVFS.xFullPathname=TestVFS.xFullPathname3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xFullPathname=TestVFS.xFullPathname4
        if not iswindows:
            # SQLite doesn't give an error even though the vfs is silently truncating
            # the full pathname.  See SQLite ticket 3373
            self.assertRaises(apsw.CantOpenError, testdb) # we get cantopen on the truncated fullname
        TestVFS.xFullPathname=TestVFS.xFullPathname5
        self.assertRaises(apsw.TooBigError, self.assertRaisesUnraisable, apsw.TooBigError, testdb)
        TestVFS.xFullPathname=TestVFS.xFullPathname6
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xFullPathname=TestVFS.xFullPathname99
        testdb()

        ## xOpen
        self.assertRaises(TypeError, vfs.xOpen, 3)
        self.assertRaises(TypeError, vfs.xOpen, 3, 3)
        self.assertRaises(TypeError, vfs.xOpen, None, (1,2))
        self.assertRaises(TypeError, vfs.xOpen, None, [1,2,3])
        self.assertRaises(TypeError, vfs.xOpen, None, ["1",2])
        self.assertRaises(TypeError, vfs.xOpen, None, [1,"2"])
        self.assertRaises(OverflowError, vfs.xOpen, None, [l("0xffffffffeeeeeeee0"), 2])
        self.assertRaises(OverflowError, vfs.xOpen, None, [l("0xffffffff0"), 2])
        self.assertRaises(OverflowError, vfs.xOpen, None, [1, l("0xffffffff0")])
        self.assertRaises(apsw.CantOpenError, self.assertRaisesUnraisable, apsw.CantOpenError,
                                         testdb, filename="notadir/notexist/nochance") # can't open due to intermediate directories not existing
        TestVFS.xOpen=TestVFS.xOpen1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xOpen=TestVFS.xOpen2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xOpen=TestVFS.xOpen3
        self.assertRaises(apsw.CantOpenError, self.assertRaisesUnraisable, TypeError, testdb)
        TestVFS.xOpen=TestVFS.xOpen4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, AttributeError, testdb)
        TestVFS.xOpen=TestVFS.xOpen99
        testdb()

        if hasattr(apsw.Connection(":memory:"), "enableloadextension") and os.path.exists(LOADEXTENSIONFILENAME):
            ## xDlOpen
            self.assertRaises(TypeError, vfs.xDlOpen, 3)
            if py3:
                self.assertRaises(TypeError, vfs.xDlOpen, b(r"\xfb\xfc\xfd\xfe\xff\xff\xff\xff"))
            else:
                self.assertRaises(UnicodeDecodeError, vfs.xDlOpen, b(r"\xfb\xfc\xfd\xfe\xff\xff\xff\xff"))
            TestVFS.xDlOpen=TestVFS.xDlOpen1
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlOpen=TestVFS.xDlOpen2
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
            TestVFS.xDlOpen=TestVFS.xDlOpen3
            # skip testing xDlOpen3 as python is happy to convert -1 to void ptr!
            TestVFS.xDlOpen=TestVFS.xDlOpen4
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlOpen=TestVFS.xDlOpen5
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            if py3:
                TestVFS.xDlOpen=TestVFS.xDlOpen6
                self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlOpen=TestVFS.xDlOpen7
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, OverflowError, testdb)
            TestVFS.xDlOpen=TestVFS.xDlOpen99
            testdb()

            ## xDlSym
            self.assertRaises(TypeError, vfs.xDlSym, 3)
            self.assertRaises(TypeError, vfs.xDlSym, 3, 3)
            self.assertRaises(TypeError, vfs.xDlSym, "three", "three")
            TestVFS.xDlSym=TestVFS.xDlSym1
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlSym=TestVFS.xDlSym2
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
            TestVFS.xDlSym=TestVFS.xDlSym3
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlSym=TestVFS.xDlSym4
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            if py3:
                TestVFS.xDlSym=TestVFS.xDlSym5
                self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, TypeError, testdb)
            TestVFS.xDlSym=TestVFS.xDlSym6
            self.assertRaises(apsw.ExtensionLoadingError, self.assertRaisesUnraisable, OverflowError, testdb)
            TestVFS.xDlSym=TestVFS.xDlSym99
            testdb()

            ## xDlClose
            self.assertRaises(TypeError, vfs.xDlClose, "three")
            self.assertRaises(OverflowError, vfs.xDlClose, l("0xffffffffffffffff10"))
            TestVFS.xDlClose=TestVFS.xDlClose1
            self.assertRaisesUnraisable(TypeError, testdb)
            TestVFS.xDlClose=TestVFS.xDlClose2
            self.assertRaisesUnraisable(ZeroDivisionError, testdb)
            TestVFS.xDlClose=TestVFS.xDlClose3
            self.assertRaisesUnraisable(TypeError, testdb)
            TestVFS.xDlClose=TestVFS.xDlClose99
            testdb()

            ## xDlError
            self.assertRaises(TypeError, vfs.xDlError, "three")
            TestVFS.xDlError=TestVFS.xDlError1
            self.assertRaisesUnraisable(TypeError, testdb)
            TestVFS.xDlError=TestVFS.xDlError2
            self.assertRaisesUnraisable(ZeroDivisionError, testdb)
            TestVFS.xDlError=TestVFS.xDlError3
            self.assertRaisesUnraisable(TypeError, testdb)
            TestVFS.xDlError=TestVFS.xDlError4
            self.assertRaisesUnraisable(TypeError, testdb)
            if py3:
                TestVFS.xDlError=TestVFS.xDlError5
                self.assertRaisesUnraisable(TypeError, testdb)
            TestVFS.xDlError=TestVFS.xDlError6 # should not error
            testdb()
            TestVFS.xDlError=TestVFS.xDlError99
            testdb()

        ## xSleep
        testtimeout=True
        self.assertRaises(TypeError, vfs.xSleep, "three")
        self.assertRaises(TypeError, vfs.xSleep, 3, 3)
        TestVFS.xSleep=TestVFS.xSleep1
        self.assertRaisesUnraisable(TypeError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep2
        self.assertRaisesUnraisable(ZeroDivisionError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep3
        self.assertRaisesUnraisable(TypeError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep4
        self.assertRaisesUnraisable(TypeError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep5
        self.assertRaisesUnraisable(OverflowError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep6
        self.assertRaisesUnraisable(OverflowError, testdb, mode="delete")
        TestVFS.xSleep=TestVFS.xSleep99
        testdb(mode="delete")
        testtimeout=False

        ## xCurrentTime
        self.assertRaises(TypeError, vfs.xCurrentTime, "three")
        TestVFS.xCurrentTime=TestVFS.xCurrentTime1
        self.assertRaisesUnraisable(TypeError, testdb)
        TestVFS.xCurrentTime=TestVFS.xCurrentTime2
        self.assertRaisesUnraisable(ZeroDivisionError, testdb)
        TestVFS.xCurrentTime=TestVFS.xCurrentTime3
        self.assertRaisesUnraisable(TypeError, testdb)
        TestVFS.xCurrentTime=TestVFS.xCurrentTime4
        self.assertRaisesUnraisable(TypeError, testdb)
        TestVFS.xCurrentTime=TestVFS.xCurrentTime5
        testdb()
        TestVFS.xCurrentTime=TestVFS.xCurrentTime99
        testdb()

        ## xGetLastError
        xgle=getattr(apsw, 'test_call_xGetLastError', None)
        if xgle:
            # check it
            self.assertRaises(TypeError, xgle, 3, "seven")
            # cause an error
            self.assertRaises(apsw.CantOpenError, vfs.xOpen, u("."), [apsw.SQLITE_OPEN_READWRITE|apsw.SQLITE_OPEN_MAIN_DB,0])
            # check it works
            res=xgle("apswtest", 512)
            self.assertEqual(type(res), type(()))
            self.assertEqual(len(res), 2)
            self.assertRaises(TypeError, vfs.xGetLastError, "three")
            TestVFS.xGetLastError=TestVFS.xGetLastError1
            res=self.assertRaisesUnraisable(TypeError, xgle, "apswtest", 512)
            self.assertEqual(res[1], 0)
            TestVFS.xGetLastError=TestVFS.xGetLastError2
            res=self.assertRaisesUnraisable(ZeroDivisionError, xgle, "apswtest", 512)
            self.assertEqual(res[1], 0)
            TestVFS.xGetLastError=TestVFS.xGetLastError3
            res=self.assertRaisesUnraisable(TypeError, xgle, "apswtest", 512)
            self.assertEqual(res[1], 0)
            TestVFS.xGetLastError=TestVFS.xGetLastError4
            res=self.assertRaisesUnraisable(TypeError, xgle, "apswtest", 512)
            self.assertEqual(res[1], 0)
            TestVFS.xGetLastError=TestVFS.xGetLastError5
            res=xgle("apswtest", 512)
            self.assertEqual(res[1], 1)
            self.assertEqual(res[0], b("a")*512)
            res=xgle("apswtest", 1024)
            self.assertEqual(res[1], 1)
            self.assertEqual(res[0], b("a")*1024)
            res=xgle("apswtest", 1500)
            self.assertEqual(res[1], 0)
            self.assertEqual(res[0], b("a")*1500)
            class VFS2(apsw.VFS):
                def __init__(self):
                    apsw.VFS.__init__(self, "apswtest2", "apswtest")
            vfs2=VFS2()
            if not py3:
                res=xgle("apswtest2", 128)
                self.assertEqual(res[1], 1)
            del vfs2
            del VFS2
            gc.collect()

        ## System call stuff
        if "unix" in apsw.vfsnames() and "APSW_NO_MEMLEAK" not in os.environ:
            class VFS2(apsw.VFS):
                def __init__(self):
                    apsw.VFS.__init__(self, "apswtest2", "apswtest")
            vfs2=VFS2()

            ## xNextSystemCall
            self.assertRaises(TypeError, vfs.xNextSystemCall, 0)
            items=[None]
            while True:
                n=vfs.xNextSystemCall(items[-1])
                if n is None:
                    break
                items.append(n)
            items=items[1:]
            self.assertNotEqual(0, len(items))
            self.assertTrue("open" in items)

            if not py3:
                self.assertRaises(UnicodeDecodeError, vfs.xNextSystemCall, "foo\xf3")

            TestVFS.xNextSystemCall=TestVFS.xNextSystemCall1
            self.assertRaisesUnraisable(TypeError, vfs2.xNextSystemCall, "open")
            TestVFS.xNextSystemCall=TestVFS.xNextSystemCall2
            self.assertRaisesUnraisable(TypeError, vfs2.xNextSystemCall, "open")
            if not py3:
                TestVFS.xNextSystemCall=TestVFS.xNextSystemCall3
                self.assertRaisesUnraisable(UnicodeDecodeError, vfs2.xNextSystemCall, "open")
            TestVFS.xNextSystemCall=TestVFS.xNextSystemCall4
            self.assertEqual(None, self.assertRaisesUnraisable(ZeroDivisionError, vfs2.xNextSystemCall, "open"))
            TestVFS.xNextSystemCall=TestVFS.xNextSystemCall99
            vfs2.xNextSystemCall("open")

            ## xGetSystemCall
            self.assertRaises(TypeError, vfs.xGetSystemCall)
            self.assertRaises(TypeError, vfs.xGetSystemCall, 3)
            self.assertEqual(None, vfs.xGetSystemCall("a name that won't exist"))
            self.assertTrue(isinstance(vfs.xGetSystemCall("open"), (int,long)))

            TestVFS.xGetSystemCall=TestVFS.xGetSystemCall1
            self.assertRaisesUnraisable(TypeError, vfs2.xGetSystemCall, "open")
            TestVFS.xGetSystemCall=TestVFS.xGetSystemCall2
            self.assertRaisesUnraisable(ZeroDivisionError, vfs2.xGetSystemCall, "open")
            TestVFS.xGetSystemCall=TestVFS.xGetSystemCall3
            self.assertRaisesUnraisable(TypeError, vfs2.xGetSystemCall, "open")
            TestVFS.xGetSystemCall=TestVFS.xGetSystemCall4
            self.assertRaisesUnraisable(TypeError, vfs2.xGetSystemCall, "open")
            TestVFS.xGetSystemCall=TestVFS.xGetSystemCall99
            self.assertTrue(vfs2.xGetSystemCall("open")>0)

            ## xSetSystemCall
            fallback=apsw.VFS("fallback",  base="") # undo any damage we do
            try:
                self.assertRaises(TypeError,  vfs.xSetSystemCall)
                self.assertRaises(TypeError,  vfs.xSetSystemCall, 3, 4)
                self.assertRaises((TypeError, ValueError),  vfs.xSetSystemCall, "a\0b", 4)
                self.assertRaises(TypeError,  vfs.xSetSystemCall, "none", 3.7)
                realopen=vfs.xGetSystemCall("open")
                self.assertEqual(False, vfs.xSetSystemCall("doesn't exist", 0))
                self.assertEqual(True, vfs.xSetSystemCall("open", realopen+1))
                self.assertEqual(realopen+1, vfs.xGetSystemCall("open"))
                self.assertEqual(True, vfs.xSetSystemCall("open", realopen))
                TestVFS.xSetSystemCall=TestVFS.xSetSystemCall1
                self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, vfs2.xSetSystemCall, "open", realopen)
                TestVFS.xSetSystemCall=TestVFS.xSetSystemCall2
                self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, vfs2.xSetSystemCall, "open", realopen)
                TestVFS.xSetSystemCall=TestVFS.xSetSystemCall3
                self.assertEqual(False, vfs2.xSetSystemCall("doesn't exist", 0))
                TestVFS.xSetSystemCall=TestVFS.xSetSystemCall99
                self.assertEqual(True, vfs2.xSetSystemCall("open", realopen))
            finally:
                # undocumented - this resets all calls to their defaults
                fallback.xSetSystemCall(None, 0)
                fallback.unregister()

        ##
        ## VFS file testing
        ##

        ## init
        TestVFS.xOpen=TestVFS.xOpen100

        TestFile.__init__=TestFile.init1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init5
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, OverflowError, testdb)
        TestFile.__init__=TestFile.init6
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, OverflowError, testdb)
        TestFile.__init__=TestFile.init7
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init8
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ValueError, testdb)
        TestFile.__init__=TestFile.init9
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.__init__=TestFile.init10
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ValueError, testdb)
        TestFile.__init__=TestFile.init99
        testdb() # should work just fine

        # cause an open failure
        self.assertRaises(apsw.CantOpenError, TestFile, ".", [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])

        ## xRead
        t=TestFile(os.path.abspath(TESTFILEPREFIX+"testfile"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])
        self.assertRaises(TypeError, t.xRead, "three", "four")
        self.assertRaises(OverflowError, t.xRead, l("0xffffffffeeeeeeee0"), 1)
        self.assertRaises(OverflowError, t.xRead, 1, l("0xffffffffeeeeeeee0"))
        TestFile.xRead=TestFile.xRead1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xRead=TestFile.xRead2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xRead=TestFile.xRead3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xRead=TestFile.xRead4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xRead=TestFile.xRead5
        self.assertRaises(apsw.IOError, testdb)
        TestFile.xRead=TestFile.xRead99
        testdb()

        ## xWrite
        if sys.version_info>=(2,4): # py2.3 has bug
            self.assertRaises(TypeError, t.xWrite, "three", "four")
        self.assertRaises(OverflowError, t.xWrite, "three", l("0xffffffffeeeeeeee0"))
        self.assertRaises(TypeError, t.xWrite, u("foo"), 0)
        TestFile.xWrite=TestFile.xWrite1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xWrite=TestFile.xWrite2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xWrite=TestFile.xWrite99
        testdb()

        ## xUnlock
        self.assertRaises(TypeError, t.xUnlock, "three")
        self.assertRaises(OverflowError, t.xUnlock, l("0xffffffffeeeeeeee0"))
        # doesn't care about nonsensical levels - assert fails in debug build
        # t.xUnlock(-1)
        # python 3.4 garbage collection changes mean these get called during cleanup which
        # causes confusing messages in wal mode
        if not (apsw.connection_hooks and list(sys.version_info)>=[3,4]):
            TestFile.xUnlock=TestFile.xUnlock1
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
            TestFile.xUnlock=TestFile.xUnlock2
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xUnlock=TestFile.xUnlock99
        testdb()

        ## xLock
        self.assertRaises(TypeError, t.xLock, "three")
        self.assertRaises(OverflowError, t.xLock, l("0xffffffffeeeeeeee0"))
        # doesn't care about nonsensical levels - assert fails in debug build
        # t.xLock(0xffffff)
        TestFile.xLock=TestFile.xLock1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xLock=TestFile.xLock2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xLock=TestFile.xLock99
        testdb()

        ## xTruncate
        if sys.version_info>=(2,4): # work around py2.3 bug
            self.assertRaises(TypeError, t.xTruncate, "three")
        self.assertRaises(OverflowError, t.xTruncate, l("0xffffffffeeeeeeee0"))
        if not iswindows:
            # windows is happy to truncate to -77 bytes
            # see https://sqlite.org/cvstrac/tktview?tn=3415
            self.assertRaises(apsw.IOError, t.xTruncate, -77)
        TestFile.xTruncate=TestFile.xTruncate1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xTruncate=TestFile.xTruncate2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xTruncate=TestFile.xTruncate99
        testdb()

        ## xSync
        if sys.version_info>=(2,4): # work around py2.3 bug
            self.assertRaises(TypeError, t.xSync, "three")
        self.assertRaises(OverflowError, t.xSync, l("0xffffffffeeeeeeee0"))
        TestFile.xSync=TestFile.xSync1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xSync=TestFile.xSync2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xSync=TestFile.xSync99
        testdb()

        ## xSectorSize
        self.assertRaises(TypeError, t.xSectorSize, 3)
        TestFile.xSectorSize=TestFile.xSectorSize1
        self.assertRaisesUnraisable(TypeError, testdb)
        TestFile.xSectorSize=TestFile.xSectorSize2
        self.assertRaisesUnraisable(ZeroDivisionError, testdb)
        TestFile.xSectorSize=TestFile.xSectorSize3
        self.assertRaisesUnraisable(TypeError, testdb)
        TestFile.xSectorSize=TestFile.xSectorSize4
        self.assertRaisesUnraisable(OverflowError, testdb)
        TestFile.xSectorSize=TestFile.xSectorSize99
        testdb()

        ## xDeviceCharacteristics
        self.assertRaises(TypeError, t.xDeviceCharacteristics, 3)
        TestFile.xDeviceCharacteristics=TestFile.xDeviceCharacteristics1
        self.assertRaisesUnraisable(TypeError, testdb)
        TestFile.xDeviceCharacteristics=TestFile.xDeviceCharacteristics2
        self.assertRaisesUnraisable(ZeroDivisionError, testdb)
        TestFile.xDeviceCharacteristics=TestFile.xDeviceCharacteristics3
        self.assertRaisesUnraisable(TypeError, testdb)
        TestFile.xDeviceCharacteristics=TestFile.xDeviceCharacteristics4
        self.assertRaisesUnraisable(OverflowError, testdb)
        TestFile.xDeviceCharacteristics=TestFile.xDeviceCharacteristics99
        testdb()

        ## xFileSize
        self.assertRaises(TypeError, t.xFileSize, 3)
        TestFile.xFileSize=TestFile.xFileSize1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xFileSize=TestFile.xFileSize2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
        TestFile.xFileSize=TestFile.xFileSize3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
        TestFile.xFileSize=TestFile.xFileSize4
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, OverflowError, testdb)
        TestFile.xFileSize=TestFile.xFileSize99
        testdb()

        ## xCheckReservedLock
        self.assertRaises(TypeError, t.xCheckReservedLock, 8)
        if not iswindows:
            # we don't do checkreservedlock test on windows as the
            # various files that need to be copied and finagled behind
            # the scenes are locked
            TestFile.xCheckReservedLock=TestFile.xCheckReservedLock1
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
            TestFile.xCheckReservedLock=TestFile.xCheckReservedLock2
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, testdb)
            TestFile.xCheckReservedLock=TestFile.xCheckReservedLock3
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, testdb)
            TestFile.xCheckReservedLock=TestFile.xCheckReservedLock4
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, OverflowError, testdb)
        TestFile.xCheckReservedLock=TestFile.xCheckReservedLock99
        db=testdb()

        ## xFileControl
        self.assertRaises(TypeError, t.xFileControl, "three", "four")
        self.assertRaises(OverflowError, t.xFileControl, 10, l("0xffffffffeeeeeeee0"))
        self.assertRaises(TypeError, t.xFileControl, 10, "three")
        self.assertEqual(t.xFileControl(2000, 3000), False)
        fc1=testdb(TESTFILEPREFIX+"testdb", closedb=False).filecontrol
        fc2=testdb(TESTFILEPREFIX+"testdb2", closedb=False).filecontrol
        TestFile.xFileControl=TestFile.xFileControl1
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, fc1, "main", 1027, 1027)
        TestFile.xFileControl=TestFile.xFileControl2
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, ZeroDivisionError, fc2, "main", 1027, 1027)
        TestFile.xFileControl=TestFile.xFileControl3
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, fc2, "main", 1027, 1027)
        TestFile.xFileControl=TestFile.xFileControl99
        del fc1
        del fc2
        # these should work
        testdb(closedb=False).filecontrol("main", 1027, 1027)
        if ctypes:
            objwrap=ctypes.py_object(True)
            testdb(closedb=False).filecontrol("main", 1028, ctypes.addressof(objwrap))
        # for coverage
        class VFSx(apsw.VFS):
            def __init__(self):
                apsw.VFS.__init__(self, "filecontrol", "apswtest")
        vfs2=VFSx()
        testdb(vfsname="filecontrol", closedb=False).filecontrol("main", 1027, 1027)
        del vfs2


        ## xClose
        t.xClose()
        # make sure there is no problem closing twice
        t.xClose()
        del t
        gc.collect()

        t=apsw.VFSFile("", os.path.abspath(TESTFILEPREFIX+"testfile2"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])
        t.xClose()
        # check all functions detect closed file
        for n in dir(t):
            if n not in ('xClose', 'excepthook') and not n.startswith("__"):
                self.assertRaises(apsw.VFSFileClosedError, getattr(t, n))

    def testWith(self):
        "Context manager functionality"
        # we need py 2.5 for with stuff
        if sys.version_info<(2,5):
            return
        prefix="\n"
        if sys.version_info<(2,6):
            prefix="from __future__ import with_statement\n"

        def run(s, **kwargs):
            # ensure indentation matches first line
            s=s.strip("\n")
            s=s.rstrip(" ")
            s=(len(s)-len(s.lstrip(" ")))*" "+prefix+s
            l=locals().copy()
            l["self"]=self
            for k,v in kwargs.items():
                l[k]=v
            # now remove indentation
            s=s.split("\n")
            p=len(s[0])-len(s[0].lstrip(" "))
            s="\n".join([s[p:] for s in s])
            execwrapper(s, globals(), l)

        # Does it work?
        # the autocommit tests are to make sure we are not in a transaction
        self.assertEqual(True, self.db.getautocommit())
        self.assertTableNotExists("foo1")
        run("with self.db as db: db.cursor().execute('create table foo1(x)')")
        self.assertTableExists("foo1")
        self.assertEqual(True, self.db.getautocommit())

        # with an error
        self.assertEqual(True, self.db.getautocommit())
        self.assertTableNotExists("foo2")
        try:
            run("""
            with self.db as db:
                db.cursor().execute('create table foo2(x)')
                1/0
                """)
        except ZeroDivisionError:
            pass
        self.assertTableNotExists("foo2")
        self.assertEqual(True, self.db.getautocommit())

        # nested - simple - success
        run("""
        with self.db as db:
           self.assertEqual(False, self.db.getautocommit())
           db.cursor().execute('create table foo2(x)')
           with db as db2:
              self.assertEqual(False, self.db.getautocommit())
              db.cursor().execute('create table foo3(x)')
              with db2 as db3:
                 self.assertEqual(False, self.db.getautocommit())
                 db.cursor().execute('create table foo4(x)')
        """)
        self.assertEqual(True, self.db.getautocommit())
        self.assertTableExists("foo2")
        self.assertTableExists("foo3")
        self.assertTableExists("foo4")

        # nested - simple - failure
        try:
            run("""
        self.db.cursor().execute('begin; create table foo5(x)')
        with self.db as db:
           self.assertEqual(False, self.db.getautocommit())
           db.cursor().execute('create table foo6(x)')
           with db as db2:
              self.assertEqual(False, self.db.getautocommit())
              db.cursor().execute('create table foo7(x)')
              with db2 as db3:
                 self.assertEqual(False, self.db.getautocommit())
                 db.cursor().execute('create table foo8(x)')
                 1/0
        """)
        except ZeroDivisionError:
            pass
        self.assertEqual(False, self.db.getautocommit())
        self.db.cursor().execute("commit")
        self.assertEqual(True, self.db.getautocommit())
        self.assertTableExists("foo5")
        self.assertTableNotExists("foo6")
        self.assertTableNotExists("foo7")
        self.assertTableNotExists("foo8")

        # improve coverage and various corner cases
        self.db.__enter__()
        self.assertRaises(TypeError, self.db.__exit__, 1)
        for i in range(10):
            self.db.__exit__(None, None, None)

        # make an exit fail
        self.db.__enter__()
        self.db.cursor().execute("commit")
        # deliberately futz with the outstanding transaction
        self.assertRaises(apsw.SQLError, self.db.__exit__, None, None, None)
        self.db.__exit__(None, None, None) # extra exit should be harmless

        # exectracing
        traces=[]
        def et(con, sql, bindings):
            if con==self.db:
                traces.append(sql)
            return True

        self.db.setexectrace(et)
        try:
            run("""
                 with self.db as db:
                   db.cursor().execute('create table foo2(x)')
                """)
        except apsw.SQLError: # table already exists so we should get an error
            pass

        # check we saw the right things in the traces
        self.assertTrue(len(traces)==3)
        for s in traces:
            self.assertTrue("SAVEPOINT" in s.upper())

        def et(*args):
            return BadIsTrue()
        self.db.setexectrace(et)
        try:
            run("""
                 with self.db as db:
                   db.cursor().execute('create table etfoo2(x)')
                """)
        except ZeroDivisionError:
            pass
        self.assertTableNotExists("etfoo2")
        def et(*args):
            return False
        self.db.setexectrace(et)
        try:
            run("""
                 with self.db as db:
                   db.cursor().execute('create table etfoo2(x)')
                """)
        except apsw.ExecTraceAbort:
            pass
        self.db.setexectrace(None)
        self.assertTableNotExists("etfoo2")

        # test blobs with context manager
        self.db.cursor().execute("create table blobby(x); insert into blobby values(x'aabbccddee')")
        rowid=self.db.last_insert_rowid()
        blob=self.db.blobopen('main', 'blobby', 'x', rowid, 0)
        run("""
          with blob as b:
                self.assertEqual(id(blob), id(b))
                b.read(1)
          """, blob=blob)
        # blob gives ValueError if you do operations on closed blob
        self.assertRaises(ValueError, blob.read)

        self.db.cursor().execute("insert into blobby values(x'aabbccddee')")
        rowid=self.db.last_insert_rowid()
        blob=self.db.blobopen('main', 'blobby', 'x', rowid, 0)
        try:
            run("""
              with blob as b:
                  self.assertEqual(id(blob), id(b))
                  1/0
                  b.read(1)
                  """, blob=blob)
        except ZeroDivisionError:
            # blob gives ValueError if you do operating on closed blob
            self.assertRaises(ValueError, blob.read)

        # backup code
        if not hasattr(self.db, "backup"): return # experimental
        db2=apsw.Connection(":memory:")
        run("""
          with db2.backup("main", self.db, "main") as b:
             while not b.done:
                b.step(1)
          self.assertEqual(b.done, True)
          self.assertDbIdentical(self.db, db2)
          """, db2=db2)

    def fillWithRandomStuff(self, db, seed=1):
        "Fills a database with random content"
        db.cursor().execute("create table a(x)")
        for i in range(1,11):
            db.cursor().execute("insert into a values(?)", ("aaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"*i*8192,))

    def assertDbIdentical(self, db1, db2):
        "Ensures databases are identical"
        c1=db1.cursor()
        c2=db2.cursor()
        self.assertEqual(
            list(c1.execute("select * from sqlite_master order by _ROWID_")),
            list(c2.execute("select * from sqlite_master order by _ROWID_"))
            )
        for table in db1.cursor().execute("select name from sqlite_master where type='table'"):
            table=table[0]
            self.assertEqual(
                list(c1.execute("select * from [%s] order by _ROWID_" % (table,))),
                list(c2.execute("select * from [%s] order by _ROWID_" % (table,))),
                )
        for table in db2.cursor().execute("select name from sqlite_master where type='table'"):
            table=table[0]
            self.assertEqual(
                list(c1.execute("select * from [%s] order by _ROWID_" % (table,))),
                list(c2.execute("select * from [%s] order by _ROWID_" % (table,))),
                )

    def testBackup(self):
        "Verify hot backup functionality"
        # bad calls
        self.assertRaises(TypeError, self.db.backup, "main", "main", "main", "main")
        self.assertRaises(TypeError, self.db.backup, "main", 3, "main")
        db2=apsw.Connection(":memory:")
        db2.close()
        self.assertRaises(ValueError, self.db.backup, "main", db2, "main")
        # can't copy self
        self.assertRaises(ValueError, self.db.backup, "main", self.db, "it doesn't care what is here")

        # try and get inuse error
        dbt=apsw.Connection(":memory:")
        vals={"stop": False, "raised": False}
        def wt():
            # worker thread spins grabbing and releasing inuse flag
            while not vals["stop"]:
                try:
                    dbt.setbusytimeout(100)
                except apsw.ThreadingViolationError:
                    # this means main thread grabbed inuse first
                    pass
        t=ThreadRunner(wt)
        t.start()
        b4=time.time()
        # try to get inuse error for 30 seconds
        try:
            try:
                while not vals["stop"] and time.time()-b4<30:
                    self.db.backup("main", dbt, "main").close()
            except apsw.ThreadingViolationError:
                vals["stop"]=True
                vals["raised"]=True
        finally:
            vals["stop"]=True

        # standard usage
        db2=apsw.Connection(":memory:")
        self.fillWithRandomStuff(db2)

        b=self.db.backup("main", db2, "main")
        self.assertRaises(TypeError, b.step, '3')
        try:
            b.step(1)
            self.assertTrue(b.remaining > 0)
            self.assertTrue(b.pagecount > 0)
            while not b.done:
                b.step(1)
        finally:
            b.finish()
        self.assertDbIdentical(self.db, db2)
        self.db.cursor().execute("drop table a")

        # don't clean up
        b=self.db.backup("main", db2, "main")
        try:
            while not b.done:
                b.step(1)
        finally:
            b.finish()

        self.assertDbIdentical(self.db, db2)
        del b
        del db2
        fname=self.db.filename
        self.db=None
        gc.collect()

        # check dest db can't be used for anything else
        db2=apsw.Connection(":memory:")
        c=db2.cursor()
        c.execute("create table x(y); insert into x values(3); select * from x")
        self.db=apsw.Connection(":memory:")
        self.fillWithRandomStuff(self.db)
        self.assertRaises(apsw.ThreadingViolationError, db2.backup, "main", self.db, "main")
        c.close()
        b=db2.backup("main", self.db, "main")
        # double check cursor really is dead
        self.assertRaises(apsw.CursorClosedError, c.execute, "select 3")
        # with the backup object existing, all operations on db2 should fail
        self.assertRaises(apsw.ThreadingViolationError, db2.cursor)
        # finish and then trying to step
        b.finish()
        self.assertRaises(apsw.ConnectionClosedError, b.step)

        # make step and finish fail with locked error
        self.db=apsw.Connection(fname)
        def lockerr():
            db2=apsw.Connection(self.db.filename)
            db2.cursor().execute("begin exclusive")
            db3=apsw.Connection(self.db.filename)
            b=db3.backup("main", self.db, "main")
            # if step gets busy then so does finish, but step has to be called at least once
            self.assertRaises(apsw.BusyError, b.step)
            return b

        b=lockerr()
        b.close(True)
        del b
        b=lockerr()
        self.assertRaises(apsw.BusyError, b.close, False)
        del b

        b=lockerr()
        self.assertRaises(apsw.BusyError, b.finish)
        b.finish() # should be ok the second time
        del b

        b=lockerr()
        self.assertRaises(TypeError, b.close, "3")
        self.assertRaises(apsw.BusyError, b.close, False)
        b.close()  # should also be ok
        del b

        def f():
            b=lockerr()
            del b
            gc.collect()
        self.assertRaisesUnraisable(apsw.BusyError, f)

        # coverage
        b=lockerr()
        self.assertRaises(TypeError, b.__exit__, 3)
        self.assertRaises(apsw.BusyError, b.__exit__, None, None, None)
        b.__exit__(None, None, None)

    def testLog(self):
        "Verifies logging functions"
        self.assertRaises(TypeError, apsw.log)
        self.assertRaises(TypeError, apsw.log, 1)
        self.assertRaises(TypeError, apsw.log, 1, 2)
        self.assertRaises(TypeError, apsw.log, 1, 2, 3)
        self.assertRaises(TypeError, apsw.log, 1, None)
        apsw.log(apsw.SQLITE_MISUSE, "Hello world") # nothing should happen
        self.assertRaises(TypeError, apsw.config, apsw.SQLITE_CONFIG_LOG, 2)
        self.assertRaises(TypeError, apsw.config, apsw.SQLITE_CONFIG_LOG)
        # Can't change once SQLite is initialised
        self.assertRaises(apsw.MisuseError, apsw.config, apsw.SQLITE_CONFIG_LOG, None)
        # shutdown
        self.db=None
        gc.collect()
        apsw.shutdown()
        try:
            apsw.config(apsw.SQLITE_CONFIG_LOG, None)
            apsw.log(apsw.SQLITE_MISUSE, "Hello world")
            called=[0]
            def handler(code, message, called=called):
                called[0]+=1
                self.assertEqual(code, apsw.SQLITE_MISUSE)
                self.assertEqual(message, u(r"a \u1234 unicode ' \ufe54 string \u0089"))
            apsw.config(apsw.SQLITE_CONFIG_LOG, handler)
            apsw.log(apsw.SQLITE_MISUSE, u(r"a \u1234 unicode ' \ufe54 string \u0089"))
            self.assertEqual(called[0], 1)
            def badhandler(code, message, called=called):
                called[0]+=1
                self.assertEqual(code, apsw.SQLITE_NOMEM)
                self.assertEqual(message, u(r"Xa \u1234 unicode ' \ufe54 string \u0089"))
                1/0
            apsw.config(apsw.SQLITE_CONFIG_LOG, badhandler)
            self.assertRaisesUnraisable(ZeroDivisionError, apsw.log, apsw.SQLITE_NOMEM, u(r"Xa \u1234 unicode ' \ufe54 string \u0089"))
            self.assertEqual(called[0], 2)
        finally:
            gc.collect()
            apsw.shutdown()
            apsw.config(apsw.SQLITE_CONFIG_LOG, None)


    def testReadonly(self):
        "Check Connection.readonly()"
        self.assertEqual(self.db.readonly("main"), False)
        c=apsw.Connection(TESTFILEPREFIX+"testdb", flags=apsw.SQLITE_OPEN_READONLY)
        self.assertEqual(c.readonly("main"), True)
        self.assertRaises(apsw.SQLError, self.db.readonly, "sdfsd")
        class foo:
            def __str__(self): 1/0
        self.assertRaises(TypeError, self.db.readonly, foo())

    def testFilename(self):
        "Check connections and filenames"
        self.assertTrue(self.db.filename.endswith("testdb"))
        self.assertTrue(os.sep in self.db.filename)
        self.assertEqual(self.db.filename, self.db.db_filename("main"))
        self.db.cursor().execute("attach '%s' as foo" % (TESTFILEPREFIX+"testdb2",))
        self.assertEqual(self.db.filename+"2", self.db.db_filename("foo"))

    def testShell(self, shellclass=None):
        "Check Shell functionality"
        # The windows stdio library is hopelessly broken when used
        # with codecs.  Sadly Python before version 3 tried to use it
        # and you get a dismal mess - complaints about BOMs lacking on
        # zero length files, arbitrary truncation, inability to read
        # and write from the file and far too much other nonsense.  I
        # wasted enough time trying to work around it but give up. We
        # just don't test the shell in Windows before Python 3.  Feel
        # free to waste your own time trying to fix this.
        if iswindows and not py3:
            return

        if shellclass is None:
            shellclass=apsw.Shell

        # Python 3.3.0 crashes in csv module - fixed in 3.3.1
        if sys.version_info>=(3,3,0) and sys.version_info<(3,3,1):
            return

        # I originally tried to use stringio for this but it barfs
        # badly over non-ascii stuff and there was no way to make all
        # the python versions simultaneously happy
        import codecs
        fh=[codecs.open(TESTFILEPREFIX+"test-shell-"+t, "w+b", encoding="utf8") for t in ("in", "out", "err")]
        kwargs={"stdin": fh[0], "stdout": fh[1], "stderr": fh[2]}
        def reset():
            for i in fh:
                i.truncate(0)
                i.seek(0)

        def isempty(x):
            self.assertEqual(get(x), "")

        def isnotempty(x):
            self.assertNotEqual(len(get(x)), 0)

        def cmd(c):
            assert fh[0].tell()==0
            fh[0].truncate(0)
            fh[0].seek(0)
            fh[0].write(c)
            fh[0].seek(0)

        def get(x):
            x.seek(0)
            return x.read()


        # Make one
        shellclass(stdin=fh[0], stdout=fh[1], stderr=fh[2])

        # Lets give it some harmless sql arguments and do a sanity check
        s=shellclass(args=[TESTFILEPREFIX+"testdb", "create table x(x)", "insert into x values(1)"], **kwargs)
        self.assertTrue(s.db.filename.endswith("testdb"))
        # do a dump and check our table is there with its values
        s.command_dump([])
        self.assertTrue("x(x)" in get(fh[1]))
        self.assertTrue("(1);" in get(fh[1]))

        # empty args
        self.assertEqual( (None, [], []), s.process_args(None))

        # input description
        reset()
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "wt", "syntax error")
        try:
            shellclass(args=[TESTFILEPREFIX+"testdb", ".read %stest-shell-1" % (TESTFILEPREFIX,) ], **kwargs)
        except shellclass.Error:
            self.assertTrue("test-shell-1" in get(fh[2]))
            isempty(fh[1])

        # Check single and double dash behave the same
        reset()
        try:
            shellclass(args=["-init"], **kwargs)
        except shellclass.Error:
            isempty(fh[1])
            self.assertTrue("specify a filename" in get(fh[2]))

        reset()
        s=shellclass(**kwargs)
        try:
            s.process_args(["--init"])
        except shellclass.Error:
            self.assertTrue("specify a filename" in str(sys.exc_info()[1]))

        # various command line options
        # an invalid one
        reset()
        try:
            shellclass(args=["---tripledash"], **kwargs)
        except shellclass.Error:
            isempty(fh[1])
            self.assertTrue("-tripledash" in get(fh[2]))
            self.assertTrue("--tripledash" not in get(fh[2]))

        ###
        ### --init
        ###
        reset()
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "wt", "syntax error")
        try:
            shellclass(args=["-init", TESTFILEPREFIX+"test-shell-1"], **kwargs)
        except shellclass.Error:
            # we want to make sure it read the file
            isempty(fh[1])
            self.assertTrue("syntax error" in get(fh[2]))
        reset()
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "wt", "select 3;")
        shellclass(args=["-init", TESTFILEPREFIX+"test-shell-1"], **kwargs)
        # we want to make sure it read the file
        isempty(fh[2])
        self.assertTrue("3" in get(fh[1]))

        ###
        ### --header
        ###
        reset()
        s=shellclass(**kwargs)
        s.process_args(["--header"])
        self.assertEqual(s.header, True)
        s.process_args(["--noheader"])
        self.assertEqual(s.header, False)
        s.process_args(["--noheader", "-header", "-noheader", "--header"])
        self.assertEqual(s.header, True)
        # did they actually turn on?
        isempty(fh[1])
        isempty(fh[2])
        s.process_args([TESTFILEPREFIX+"testdb", ".mode column", "select 3"])
        isempty(fh[2])
        self.assertTrue("3" in get(fh[1]))
        self.assertTrue("----" in get(fh[1]))

        ###
        ### --echo, --bail, --interactive
        ###
        reset()
        for v in ("echo", "bail", "interactive"):
            s=shellclass(**kwargs)
            b4=getattr(s,v)
            s.process_args(["--"+v])
            # setting should have changed
            self.assertNotEqual(b4, getattr(s,v))
            isempty(fh[1])
            isempty(fh[2])

        ###
        ### --batch
        ###
        reset()
        s=shellclass(**kwargs)
        s.interactive=True
        s.process_args(["-batch"])
        self.assertEqual(s.interactive, False)
        isempty(fh[1])
        isempty(fh[2])

        ###
        ### --separator, --nullvalue, --encoding
        ###
        for v,val in ("separator", "\n"), ("nullvalue", "abcdef"), ("encoding", "iso8859-1"):
            reset()
            s=shellclass(args=["--"+v, val], **kwargs)
            # We need the eval because shell processes backslashes in
            # string.  After deliberating that is the right thing to
            # do
            if v=="encoding":
                self.assertEqual((val,None), getattr(s,v))
            else:
                self.assertEqual(val, getattr(s,v))
            isempty(fh[1])
            isempty(fh[2])
            self.assertRaises(shellclass.Error, shellclass, args=["-"+v, val, "--"+v], **kwargs)
            isempty(fh[1])
            self.assertTrue(v in get(fh[2]))

        ###
        ### --version
        ###
        reset()
        self.assertRaises(SystemExit, shellclass, args=["--version"], **kwargs)
        # it writes to stdout
        isempty(fh[2])
        self.assertTrue(apsw.sqlitelibversion() in get(fh[1]))

        ###
        ### --help
        ###
        reset()
        self.assertRaises(SystemExit, shellclass, args=["--help"], **kwargs)
        # it writes to stderr
        isempty(fh[1])
        self.assertTrue("-version" in get(fh[2]))

        ###
        ### Items that correspond to output mode
        ###
        reset()
        shellclass(args=["--python", "--column", "--python", ":memory:", "create table x(x)", "insert into x values(x'aa')", "select * from x;"], **kwargs)
        isempty(fh[2])
        self.assertTrue('b"' in get(fh[1]) or "buffer(" in get(fh[1]))

        ###
        ### Is process_unknown_args called as documented?
        ###
        reset()
        class s2(shellclass):
            def process_unknown_args(self, args):
                1/0
        self.assertRaises(ZeroDivisionError, s2, args=["--unknown"], **kwargs)
        isempty(fh[1])
        self.assertTrue("division" in get(fh[2])) # py2 says "integer division", py3 says "int division"

        class s3(shellclass):
            def process_unknown_args(_, args):
                self.assertEqual(args[0:2], ["myoption", "myvalue"])
                return args[2:]
        reset()
        self.assertRaises(s3.Error, s3, args=["--python", "--myoption", "myvalue", "--init"], **kwargs)
        isempty(fh[1])
        self.assertTrue("-init" in get(fh[2]))

        ###
        ### Some test data
        ###
        reset()
        s=shellclass(**kwargs)
        s.cmdloop()
        def testnasty():
            reset()
            # py 3 barfs with any codepoints above 0xffff whining
            # about surrogates not being allowed.  If only it
            # implemented unicode properly.
            cmd(u("create table if not exists nastydata(x,y); insert into nastydata values(null,'xxx\\u1234\\uabcdyyy\r\n\t\"this \\is nasty\u0001stuff!');"))
            s.cmdloop()
            isempty(fh[1])
            isempty(fh[2])
            reset()
            cmd(".bail on\n.header OFF\nselect * from nastydata;")
            s.cmdloop()
            isempty(fh[2])
            isnotempty(fh[1])

        ###
        ### Output formats - column
        ###
        reset()
        x='a'*20
        cmd(".mode column\n.header ON\nselect '"+x+"';")
        s.cmdloop()
        isempty(fh[2])
        # colwidth should be 2 more
        sep='-'*(len(x)+2) # apostrophes quoting string in column header
        out=get(fh[1]).replace("\n", "")
        self.assertEqual(len(out.split(sep)), 2)
        self.assertEqual(len(out.split(sep)[0]), len(x)+2) # plus two apostrophes
        self.assertEqual(len(out.split(sep)[1]), len(x)+2) # same
        self.assertTrue("  " in out.split(sep)[1]) # space padding
        # make sure truncation happens
        reset()
        cmd(".width 5\nselect '"+x+"';\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("a"*6 not in get(fh[1]))
        # right justification
        reset()
        cmd(".header off\n.width -3 -3\nselect 3,3;\n.width 3 3\nselect 3,3;")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        self.assertTrue(v.startswith("  3    3"))
        v=v.split("\n")
        self.assertNotEqual(v[0], v[1])
        self.assertEqual(len(v[0]), len(v[1]))
        # explain mode doesn't truncate
        reset()
        cmd(".header on\ncreate table %s(x);create index %s_ on %s(x);\n.explain\nexplain select * from %s where x=7;\n" % (x,x,x,x))
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(x in get(fh[1]))
        # check null and blobs
        reset()
        nv="ThIsNuLlVaLuE"
        cmd(".nullvalue %s\nselect null, x'aaee';\n" % (nv,))
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(nv in get(fh[1]))
        # do not output blob as is
        self.assertTrue(u("\xaa") not in get(fh[1]))
        # undo explain
        reset()
        cmd(".explain OFF\n")
        s.cmdloop()
        testnasty()

        ###
        ### Output formats - csv
        ###
        reset()
        # mode change should reset separator
        cmd(".separator F\n.mode csv\nselect 3,3;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("3,3" in get(fh[1]))
        # tab sep
        reset()
        cmd(".separator '\\t'\nselect 3,3;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("3\t3" in get(fh[1]))
        # back to comma
        reset()
        cmd(".mode csv\nselect 3,3;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("3,3" in get(fh[1]))
        # quoting
        reset()
        cmd(".header ON\nselect 3 as [\"one\"], 4 as [\t];\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue('"""one""",\t' in get(fh[1]))
        # custom sep
        reset()
        cmd(".separator |\nselect 3 as [\"one\"], 4 as [\t];\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("3|4\n" in get(fh[1]))
        self.assertTrue('"one"|\t\n' in get(fh[1]))
        # testnasty() - csv module is pretty much broken

        ###
        ### Output formats - html
        ###
        reset()
        cmd(".mode html\n.header OFF\nselect 3,4;\n")
        s.cmdloop()
        isempty(fh[2])
        # should be no header
        self.assertTrue("<th>" not in get(fh[1]).lower())
        # does it actually work?
        self.assertTrue("<td>3</td>" in get(fh[1]).lower())
        # check quoting works
        reset()
        cmd(".header ON\nselect 3 as [<>&];\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("<th>&lt;&gt;&amp;</th>" in get(fh[1]).lower())
        # do we output rows?
        self.assertTrue("<tr>" in get(fh[1]).lower())
        self.assertTrue("</tr>" in get(fh[1]).lower())
        testnasty()

        ###
        ### Output formats - insert
        ###
        reset()
        all="3,3.1,'3.11',null,x'0311'"
        cmd(".mode insert\n.header OFF\nselect "+all+";\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(all in get(fh[1]).lower())
        # empty values
        reset()
        all="0,0.0,'',null,x''"
        cmd("select "+all+";\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(all in get(fh[1]).lower())
        # header, separator and nullvalue should make no difference
        save=get(fh[1])
        reset()
        cmd(".header ON\n.separator %\n.nullvalue +\nselect "+all+";\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertEqual(save, get(fh[1]))
        # check the table name
        self.assertTrue(get(fh[1]).lower().startswith('insert into "table" values'))
        reset()
        cmd(".mode insert funkychicken\nselect "+all+";\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(get(fh[1]).lower().startswith("insert into funkychicken values"))
        testnasty()

        ###
        ### Output formats - json
        ###
        reset()
        all="3,2.2,'string',null,x'0311'"
        cmd(".mode json\n.header ON\n select "+all+";")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1]).strip()
        v=v[:-1] # remove trailing comma
        havejson=False
        try:
            import json
            havejson=True
        except ImportError:
            try:
                import simplejson as json
                havejson=True
            except ImportError:
                pass
        if havejson:
            out=json.loads(v)
            self.assertEqual(out,
                             {
                                 "3": 3,
                                 "2.2": 2.2,
                                 "'string'": "string",
                                 "null": None,
                                 "x'0311'": "AxE="
                                 })
        # a regular table
        reset()
        cmd("create table jsontest([int], [float], [string], [null], [blob]);insert into jsontest values("+all+");select * from jsontest;")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1]).strip()[:-1]
        if havejson:
            out=json.loads(v)
            self.assertEqual(out,
                             {
                                 "int": 3,
                                 "float": 2.2,
                                 "string": "string",
                                 "null": None,
                                 "blob": "AxE="
                                 })
        testnasty()

        ###
        ### Output formats - line
        ###
        reset()
        cmd(".header OFF\n.nullvalue *\n.mode line\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        out=get(fh[1]).replace(" ","")
        self.assertTrue("a=3\n" in out)
        self.assertTrue("b=*\n" in out)
        self.assertTrue("c=0.0\n" in out)
        self.assertTrue("d=a\n" in out)
        self.assertTrue("e=<Binarydata>\n" in out)
        self.assertEqual(7, len(out.split("\n"))) # one for each col plus two trailing newlines
        # header should make no difference
        reset()
        cmd(".header ON\n.nullvalue *\n.mode line\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertEqual(out, get(fh[1]).replace(" ",""))
        # wide column name
        reset()
        ln="kjsfhgjksfdjkgfhkjsdlafgjkhsdkjahfkjdsajfhsdja"*12
        cmd("select 3 as %s, 3 as %s1;" % (ln,ln))
        s.cmdloop()
        isempty(fh[2])
        self.assertEqual(get(fh[1]), " %s = 3\n%s1 = 3\n\n" % (ln,ln))
        testnasty()

        ###
        ### Output formats - list
        ###
        reset()
        cmd(".header off\n.mode list\n.nullvalue (\n.separator &\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertEqual(get(fh[1]), '3&(&0.0&a&<Binary data>\n')
        reset()
        # header on
        cmd(".header on\n.mode list\n.nullvalue (\n.separator &\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(get(fh[1]).startswith("a&b&c&d&e\n"))
        testnasty()

        ###
        ### Output formats - python
        ###
        reset()
        cmd(".header off\n.mode python\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa44bb' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        v=eval(get(fh[1]))
        self.assertEqual(len(v), 1) # 1 tuple
        self.assertEqual(v, ( (3, None, 0.0, 'a', b(r"\xaa\x44\xbb")), ))
        reset()
        cmd(".header on\n.mode python\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa44bb' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        v=eval("("+get(fh[1])+")") # need parentheses otherwise indent rules apply
        self.assertEqual(len(v), 2) # headers and row
        self.assertEqual(v, ( ("a", "b", "c", "d", "e"), (3, None, 0.0, 'a', b(r"\xaa\x44\xbb")), ))
        testnasty()

        ###
        ### Output formats - TCL
        ###
        reset()
        cmd(".header off\n.mode tcl\n.separator -\n.nullvalue ?\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa44bb' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertEqual(get(fh[1]), '"3"-"?"-"0.0"-"a"-"\\xAAD\\xBB"\n')
        reset()
        cmd(".header on\nselect 3 as a, null as b, 0.0 as c, 'a' as d, x'aa44bb' as e;\n")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue('"a"-"b"-"c"-"d"-"e"' in get(fh[1]))
        testnasty()

        # What happens if db cannot be opened?
        s.process_args(args=["/"])
        reset()
        cmd("select * from sqlite_master;\n.bail on\nselect 3;\n")
        self.assertRaises(apsw.CantOpenError, s.cmdloop)
        isempty(fh[1])
        self.assertTrue("unable to open database file" in get(fh[2]))

        # echo testing - multiple statements
        s.process_args([":memory:"]) # back to memory db
        reset()
        cmd(".bail off\n.echo on\nselect 3;\n")
        s.cmdloop()
        self.assertTrue("select 3;\n" in get(fh[2]))
        # multiline
        reset()
        cmd("select 3;select 4;\n")
        s.cmdloop()
        self.assertTrue("select 3;\n" in get(fh[2]))
        self.assertTrue("select 4;\n" in get(fh[2]))
        # multiline with error
        reset()
        cmd("select 3;select error;select 4;\n")
        s.cmdloop()
        self.assertTrue("select 3;\n" in get(fh[2]))
        # apsw can't tell where erroneous command ends so all processing on the line stops
        self.assertTrue("select error;select 4;\n" in get(fh[2]))
        # is timing info output correctly?
        reset()
        timersupported=False
        try:
            cmd(".bail on\n.echo off\n.timer on\n.timer off\n")
            s.cmdloop()
            timersupported=True
        except s.Error:
            pass

        if timersupported:
            reset()
            # create something that should take some time to execute
            s.db.cursor().execute("create table xyz(x); begin;")
            s.db.cursor().executemany("insert into xyz values(?)", randomintegers(4000))
            s.db.cursor().execute("end")
            reset()
            # this takes .6 seconds on my machine so we should
            # definitely have non-zero timing information
            cmd(".timer ON\nselect max(x),min(x),max(x+x),min(x-x) from xyz union select x+max(x),x-min(x),3,4 from xyz union select x,x,x,x from xyz union select x,x,x,x from xyz;select 3;\n")
            s.cmdloop()
            isnotempty(fh[1])
            isnotempty(fh[2])
        reset()
        cmd(".bail off\n.timer off")
        s.cmdloop()

        # command handling
        reset()
        cmd(".nonexist 'unclosed")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("no closing quotation" in get(fh[2]).lower())
        reset()
        cmd(".notexist       ")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue('Unknown command "notexist"' in get(fh[2]))

        ###
        ### Commands - backup and restore
        ###

        reset()
        cmd(".backup with too many parameters")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".backup ") # too few
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".restore with too many parameters")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".restore ") # too few
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        # bogus filenames
        for i in ('/', '"main" /'):
            for c in (".backup ", ".restore "):
                reset()
                cmd(c+i)
                s.cmdloop()
                isempty(fh[1])
                isnotempty(fh[2])

        def randomtable(cur, dbname=None):
            name=list("abcdefghijklmnopqrstuvwxtz")
            random.shuffle(name)
            name="".join(name)
            fullname=name
            if dbname:
                fullname=dbname+"."+fullname
            cur.execute("begin;create table %s(x)" % (fullname,))
            cur.executemany("insert into %s values(?)" % (fullname,), randomintegers(400))
            cur.execute("end")
            return name

        # Straight forward backup.  The gc.collect() is needed because
        # non-gc cursors hanging around will prevent the backup from
        # happening.
        n=randomtable(s.db.cursor())
        contents=s.db.cursor().execute("select * from "+n).fetchall()
        reset()
        cmd(".backup %stestdb2" % (TESTFILEPREFIX,) )
        gc.collect()
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd("drop table "+n+";")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        self.assertTrue(os.path.isfile("%stestdb2" % (TESTFILEPREFIX,)))
        reset()
        cmd(".restore %stestdb2" % (TESTFILEPREFIX,))
        gc.collect()
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        newcontents=s.db.cursor().execute("select * from "+n).fetchall()
        # no guarantee of result order
        contents.sort()
        newcontents.sort()
        self.assertEqual(contents, newcontents)

        # do they pay attention to the dbname
        s.db.cursor().execute("attach ':memory:' as memdb")
        n=randomtable(s.db.cursor(), "memdb")
        contents=s.db.cursor().execute("select * from memdb."+n).fetchall()
        reset()
        gc.collect()
        cmd(".backup memdb %stestdb2" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        s.db.cursor().execute("detach memdb; attach ':memory:' as memdb2")
        reset()
        gc.collect()
        cmd(".restore memdb2 %stestdb2" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        newcontents=s.db.cursor().execute("select * from memdb2."+n).fetchall()
        # no guarantee of result order
        contents.sort()
        newcontents.sort()
        self.assertEqual(contents, newcontents)

        ###
        ### Commands - bail
        ###
        reset()
        cmd(".bail")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".bail on\n.mode list\nselect 3;\nselect error;\nselect 4;\n")
        self.assertRaises(apsw.Error, s.cmdloop)
        self.assertTrue("3" in get(fh[1]))
        self.assertTrue("4" not in get(fh[1]))
        reset()
        cmd(".bail oFf\n.mode list\nselect 3;\nselect error;\nselect 4;\n")
        s.cmdloop()
        self.assertTrue("3" in get(fh[1]))
        self.assertTrue("4" in get(fh[1]))

        ###
        ### Commands - databases
        ###
        reset()
        cmd(".databases foo")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        # clean things up
        s=shellclass(**kwargs)
        reset()
        cmd(".header oFF\n.databases")
        s.cmdloop()
        isempty(fh[2])
        for i in "main", "name", "file":
            self.assertTrue(i in get(fh[1]))
        reset()
        cmd("attach '%stestdb' as quack;\n.databases" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[2])
        for i in "main", "name", "file", "testdb", "quack":
            self.assertTrue(i in get(fh[1]))
        reset()
        cmd("detach quack;")
        s.cmdloop()
        isempty(fh[2])
        for i in "testdb", "quack":
            self.assertTrue(i not in get(fh[1]))

        ###
        ### Commands - dump
        ###
        reset()
        cmd("create     table foo(x); create table bar(x);\n.dump foox")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".dump foo")
        s.cmdloop()
        isempty(fh[2])
        for i in "foo", "create table", "begin", "commit":
            self.assertTrue(i in get(fh[1]).lower())
        self.assertTrue("bar" not in get(fh[1]).lower())
        # can we do virtual tables?
        reset()
        if self.checkOptionalExtension("fts3", "create virtual table foo using fts3()"):
            reset()
            cmd("CREATE virtual TaBlE    fts3     using fts3(colA FRED  , colB JOHN DOE);\n"
                "insert into fts3 values('one', 'two');insert into fts3 values('onee', 'two');\n"
                "insert into fts3 values('one', 'two two two');")
            s.cmdloop()
            isempty(fh[1])
            isempty(fh[2])
            reset()
            cmd(".dump")
            s.cmdloop()
            isempty(fh[2])
            v=get(fh[1])
            for i in "pragma writable_schema", "create virtual table fts3", "cola fred", "colb john doe":
                self.assertTrue(i in v.lower())
        # analyze
        reset()
        cmd("drop table bar;create table bar(x unique,y);create index barf on bar(x,y);create index barff on bar(y);insert into bar values(3,4);\nanalyze;\n.dump bar")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        for i in "analyze bar", "create index barf":
            self.assertTrue(i in v.lower())
        self.assertTrue("autoindex" not in v.lower()) # created by sqlite to do unique constraint
        self.assertTrue("sqlite_sequence" not in v.lower()) # not autoincrements
        # repeat but all tables
        reset()
        cmd(".dump")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        for i in "analyze bar", "create index barf":
            self.assertTrue(i in v.lower())
        self.assertTrue("autoindex" not in v.lower()) # created by sqlite to do unique constraint
        # foreign keys
        reset()
        cmd("create table xxx(z references bar(x));\n.dump")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        for i in "foreign_keys", "references":
            self.assertTrue(i in v.lower())
        # views
        reset()
        cmd("create view noddy as select * from foo;\n.dump noddy")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        for i in "drop view", "create view noddy":
            self.assertTrue(i in v.lower())
        # issue82 - view ordering
        reset()
        cmd("create table issue82(x);create view issue82_2 as select * from issue82; create view issue82_1 as select count(*) from issue82_2;\n.dump issue82%")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        s.db.cursor().execute("drop table issue82 ; drop view issue82_1 ; drop view issue82_2")
        reset()
        cmd(v)
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        # autoincrement
        reset()
        cmd("create table abc(x INTEGER PRIMARY KEY AUTOINCREMENT); insert into abc values(null);insert into abc values(null);\n.dump")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        for i in "sqlite_sequence", "'abc', 2":
            self.assertTrue(i in v.lower())
        # user version
        self.assertTrue("user_version" not in v)
        reset()
        cmd("pragma user_version=27;\n.dump")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        self.assertTrue("pragma user_version=27;" in v)
        s.db.cursor().execute("pragma user_version=0")
        # some nasty stuff
        reset()
        cmd(u("create table nastydata(x,y); insert into nastydata values(null,'xxx\\u1234\\uabcd\\U00012345yyy\r\n\t\"this \\is nasty\u0001stuff!');"
              'create table "table"([except] int); create table [](""); create table [using]("&");'
              ))
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".dump")
        s.cmdloop()
        isempty(fh[2])
        v=get(fh[1])
        self.assertTrue("nasty" in v)
        self.assertTrue("stuff" in v)
        # sanity check the dumps
        reset()
        cmd(v) # should run just fine
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        # drop all the tables we made to do another dump and compare with before
        for t in "abc", "bar", "foo", "fts3", "xxx", "noddy", "sqlite_sequence", "sqlite_stat1", \
                "issue82", "issue82_1", "issue82_2":
            reset()
            cmd("drop table %s;drop view %s;" % (t,t))
            s.cmdloop() # there will be errors which we ignore
        reset()
        cmd(v)
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        # another dump
        reset()
        cmd(".dump")
        s.cmdloop()
        isempty(fh[2])
        v2=get(fh[1])
        v=re.sub("-- Date:.*", "", v)
        v2=re.sub("-- Date:.*", "", v2)
        self.assertEqual(v, v2)
        # clean database
        reset()
        s=shellclass(args=[':memory:'], **kwargs)
        cmd(v)
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(v2+"\n.dump")
        s.cmdloop()
        isempty(fh[2])
        v3=get(fh[1])
        v3=re.sub("-- Date:.*", "", v3)
        self.assertEqual(v, v3)
        # trailing comments
        reset()
        cmd("""create table xxblah(b -- ff
) -- xx
; create index xxfoo on xxblah(b -- ff
) -- xx
; create view xxbar as select * from xxblah -- ff
;
insert into xxblah values(3);
.dump
""")
        s.cmdloop()
        isempty(fh[2])
        dump=get(fh[1])
        reset()
        cmd("drop table xxblah; drop view xxbar;")
        s.cmdloop()
        isempty(fh[2])
        isempty(fh[1])
        reset()
        cmd(dump)
        s.cmdloop()
        isempty(fh[2])
        isempty(fh[1])
        self.assertEqual(s.db.cursor().execute("select * from xxbar").fetchall(), [(3,)])
        # check index
        reset()
        cmd("drop index xxfoo;")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])

        ###
        ### Command - echo
        ###
        reset()
        cmd(".echo")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".echo bananas")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".echo on on")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd(".echo off\nselect 3;")
        s.cmdloop()
        self.assertTrue("3" in get(fh[1]))
        self.assertTrue("select 3" not in get(fh[2]))
        reset()
        cmd(".echo on\nselect 3;")
        s.cmdloop()
        self.assertTrue("3" in get(fh[1]))
        self.assertTrue("select 3" in get(fh[2]))
        # more complex testing is done earlier including multiple statements and errors

        ###
        ### Command - encoding
        ###
        for i in ".encoding one two", ".encoding", ".encoding utf8 another":
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
        reset()
        cmd(".encoding this-does-not-exist")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("no known encoding" in get(fh[2]).lower())
        # use iso8859-1 to make sure data is read correctly - it
        # differs from utf8
        us=u(r"unitestdata \xaa\x89 34")
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "w", "iso8859-1", "insert into enctest values('%s');\n" % (us,))
        gc.collect()
        reset()
        cmd(".encoding iso8859-1\ncreate table enctest(x);\n.echo on\n.read %stest-shell-1\n.echo off" % (TESTFILEPREFIX,) )
        s.cmdloop()
        self.assertEqual(s.db.cursor().execute("select * from enctest").fetchall()[0][0],
                         us)
        self.assertTrue(us in get(fh[2]))
        reset()
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "w", "iso8859-1", us+"\n")
        cmd("drop table enctest;create table enctest(x);\n.import %stest-shell-1 enctest" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[2])
        isempty(fh[1])
        self.assertEqual(s.db.cursor().execute("select * from enctest").fetchall()[0][0],
                         us)
        reset()
        cmd(".output %stest-shell-1\n.mode list\nselect * from enctest;" % (TESTFILEPREFIX,))
        s.cmdloop()
        self.assertEqual(read_whole_file(TESTFILEPREFIX+"test-shell-1", "rb").strip(), # skip eol
                         us.encode("iso8859-1"))
        reset()
        cmd(".output stdout\nselect '%s';\n" % (us,))
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue(us in get(fh[1]))

        ### encoding specifying error handling - see issue 108
        reset()
        cmd(".encoding utf8:replace")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        # non-existent error
        reset()
        cmd(".encoding cp437:blahblah")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        self.assertTrue("blahblah" in get(fh[2]))
        # check replace works
        reset()
        us=u(r"\N{BLACK STAR}8\N{WHITE STAR}")
        write_whole_file(TESTFILEPREFIX+"test-shell-1", "w", "utf8", "insert into enctest values('%s');" % (us,) )
        cmd(".encoding utf8\n.read %stest-shell-1\n.encoding cp437:replace\n.output %stest-shell-1\nselect * from enctest;\n.encoding utf8\n.output stdout" % (TESTFILEPREFIX, TESTFILEPREFIX))
        s.cmdloop()
        isempty(fh[2])
        isempty(fh[1])
        self.assertTrue("?8?"  in read_whole_file(TESTFILEPREFIX+"test-shell-1", "r", "cp437"))

        ###
        ### Command - exceptions
        ###
        reset()
        cmd("syntax error;")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        self.assertTrue(len(get(fh[2]).split("\n"))<5)
        reset()
        cmd(".exceptions on\nsyntax error;")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        self.assertTrue(len(get(fh[2]).split("\n"))>10)
        self.assertTrue("sql = " in get(fh[2]))
        # deliberately leave exceptions on


        ###
        ### Command - exit & quit
        ###
        for i in ".exit", ".quit":
            reset()
            cmd(i)
            self.assertRaises(SystemExit, s.cmdloop)
            isempty(fh[1])
            isempty(fh[2])
            reset()
            cmd(i+" jjgflk")
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])

        ###
        ### Command explain and header are tested above
        ###
        # pass


        ###
        ### Command find
        ###
        reset()
        cmd(".find one two three")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        cmd("create table findtest([x\" x],y); insert into findtest values(3, 'xx3'); insert into findtest values(34, 'abcd');")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".find 3")
        s.cmdloop()
        isempty(fh[2])
        for text,present in (
            ("findtest", True),
            ("xx3", True),
            ("34", False)
            ):
            if present:
                self.assertTrue(text in get(fh[1]))
            else:
                self.assertTrue(text not in get(fh[1]))
        reset()
        cmd(".find does-not-exist")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".find ab_d")
        s.cmdloop()
        isempty(fh[2])
        for text,present in (
            ("findtest", True),
            ("xx3", False),
            ("34", True)
            ):
            if present:
                self.assertTrue(text in get(fh[1]))
            else:
                self.assertTrue(text not in get(fh[1]))
        reset()
        cmd(".find 3 table-not-exist")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])

        ###
        ### Command help
        ###
        reset()
        cmd(".help\n.help all\n.help import backup")
        s.cmdloop()
        isempty(fh[1])
        for i in ".import", "Reads data from the file":
            self.assertTrue(i in get(fh[2]))
        reset()
        cmd(".help backup notexist import")
        s.cmdloop()
        isempty(fh[1])
        for i in "Copies the contents", "No such command":
            self.assertTrue(i in get(fh[2]))
        # screw up terminal width
        origtw=s._terminal_width
        def tw(*args): return 7
        s._terminal_width=tw
        reset()
        cmd(".bail on\n.help all\n.bail off")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])

        ###
        ### Command - import
        ###
        # check it fundamentally works
        reset()
        cmd(".encoding utf16\ncreate table imptest(x real, y char);\n"
            "insert into imptest values(3.1, 'xabc');\n"
            "insert into imptest values(3.2, 'xabfff\"ffffc');\n"
            ".output %stest-shell-1\n.mode csv\nselect * from imptest;\n"
            ".output stdout" % (TESTFILEPREFIX,) )
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        # make sure encoding took
        if sys.version_info>=(3,0):
            self.assertTrue(b("xab") not in read_whole_file(TESTFILEPREFIX+"test-shell-1", "rb"))
        else:
            self.assertTrue("xab" not in read_whole_file(TESTFILEPREFIX+"test-shell-1", "rb"))
        data=s.db.cursor().execute("select * from imptest; delete from imptest").fetchall()
        self.assertEqual(2, len(data))
        reset()
        cmd(".import %stest-shell-1 imptest" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        newdata=s.db.cursor().execute("select * from imptest; drop table imptest").fetchall()
        data.sort()
        newdata.sort()
        self.assertEqual(data, newdata)
        # error handling
        for i in ".import", ".import one", ".import one two three", ".import nosuchfile nosuchtable", ".import nosuchfile sqlite_master":
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
        # wrong number of columns
        reset()
        cmd("create table imptest(x,y);\n.mode tabs\n.output %stest-shell-1\nselect 3,4;select 5,6;select 7,8,9;" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".output stdout\n.import %stest-shell-1 imptest" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        reset()
        # check it was done in a transaction and aborted
        self.assertEqual(0, s.db.cursor().execute("select count(*) from imptest").fetchall()[0][0])

        ###
        ### Command - autoimport
        ###

        # errors
        for i in ".autoimport", ".autoimport 1 2 3", ".autoimport nosuchfile", ".autoimport %stest-shell-1 sqlite_master" % (TESTFILEPREFIX,):
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])

        # check correct detection with each type of separator and that types are not mangled
        c=s.db.cursor()
        for row in (
                ('a,b', '21/1/20', '00'),
                ('  ', '1/1/20', 10),
                ('a"b', '1/1/01', '00'),
                ('+40', '01123', '2010 100 15'),
                ('2010//10//13', '2010/10/13  12', 2),
                ('2010/13/13 12:13', '13/13/2010 12:93', '13/2010/13'),
                ("+3", " 3", 3),
                ("03.03", "03.03.20", "03"),
                (
                  (None, 2, 5.5),
                  (None, 4, 99),
                  ),
                ):

            c.execute("""drop table if exists aitest ; create table aitest("x y", ["], "3d")""")
            if isinstance(row[0], tuple):
                f=c.executemany
            else:
                f=c.execute
            f("insert into aitest values(?,?,?)", row)
            fname=TESTFILEPREFIX+"test-shell-1"
            for sep in "\t", "|", ",", "X":
                reset()
                cmd(".mode csv\n.headers on\n.output %stest-shell-1\n.separator \"%s\"\nselect * from aitest;\n.output stdout\n.separator X\ndrop table if exists \"test-shell-1\";\n.autoimport %stest-shell-1" %
                    (TESTFILEPREFIX, sep, TESTFILEPREFIX))
                s.cmdloop()
                isnotempty(fh[1])
                isempty(fh[2])
                self.assertTablesEqual(s.db, "aitest", s.db, "test-shell-1")

        # Change encoding back to sensible
        reset()
        cmd(".encoding utf8")
        s.cmdloop()

        # Check date detection
        for expect, fmt, sequences in (
            ("1999-10-13", "%d-%d:%d",
             (
                    (1999, 10, 13),
                    (13, 10, 1999),
                    (10, 13, 1999),
             )
            ),
            ("1999-10-13T12:14:17", "%d/%d/%d/%d/%d/%d",
             (
                    (1999, 10, 13, 12, 14, 17),
                    (13, 10, 1999, 12, 14, 17),
                    (10, 13, 1999, 12, 14, 17),
             )
            ),
            ("1999-10-13T12:14:00", "%dX%dX%dX%dX%d",
             (
                    (1999, 10, 13, 12, 14),
                    (13, 10, 1999, 12, 14),
                    (10, 13, 1999, 12, 14),
             )
            )
            ):
            for seq in sequences:
                write_whole_file(TESTFILEPREFIX+"test-shell-1", "wt", ("a,b\nrow,"+(fmt%seq)+"\n"))
                reset()
                cmd("drop table [test-shell-1];\n.autoimport %stest-shell-1" % (TESTFILEPREFIX,))
                s.cmdloop()
                isempty(fh[2])
                imp=c.execute("select b from [test-shell-1] where a='row'").fetchall()[0][0]
                self.assertEqual(imp, expect)

        # Check diagnostics when unable to import
        for err, content in (
            ("current encoding", b(r"\x81\x82\x83\tfoo\n\x84\x97\xff\tbar")),
            ("known type", "abcdef\nhiojklmnop\n"),
            ("more than one", 'ab,c\tdef\nqr,dd\t\n'),
            ("ambiguous data format", "a,b\n1/1/2001,3\n2001/4/4,4\n"),
            ):
            if py3:
                if isinstance(content, bytes):
                    continue
            write_whole_file(TESTFILEPREFIX+"test-shell-1", "wt", content)
            reset()
            cmd("drop table [test-shell-1];\n.autoimport %stest-shell-1" % (TESTFILEPREFIX,))
            s.cmdloop()
            errmsg=get(fh[2])
            self.assertTrue(err in errmsg)

        ###
        ### Command - indices
        ###
        for i in ".indices", ".indices one two":
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
        reset()
        cmd("create table indices(x unique, y unique); create index shouldseethis on indices(x,y);")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])
        reset()
        cmd(".indices indices")
        s.cmdloop()
        isempty(fh[2])
        for i in "shouldseethis", "autoindex":
            self.assertTrue(i in get(fh[1]))

        ###
        ### Command - load
        ###
        if hasattr(APSW, "testLoadExtension"):
            lf=LOADEXTENSIONFILENAME
            for i in ".load", ".load one two three":
                reset()
                cmd(i)
                s.cmdloop()
                isempty(fh[1])
                isnotempty(fh[2])
            reset()
            cmd(".load nosuchfile")
            s.cmdloop()
            isempty(fh[1])
            self.assertTrue("nosuchfile" in get(fh[2]) or "ExtensionLoadingError" in get(fh[2]))
            reset()
            cmd(".mode list\n.load "+lf+" alternate_sqlite3_extension_init\nselect doubleup(2);")
            s.cmdloop()
            isempty(fh[2])
            self.assertTrue("4" in get(fh[1]))
            reset()
            cmd(".mode list\n.load "+lf+"\nselect half(2);")
            s.cmdloop()
            isempty(fh[2])
            self.assertTrue("1" in get(fh[1]))

        ###
        ### Command - mode
        ###
        # already thoroughly tested in code above
        for i in ".mode", ".mode foo more", ".mode invalid":
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])

        ###
        ### command nullvalue & separator
        ###
        # already tested in code above
        for i in ".nullvalue", ".nullvalue jkhkl lkjkj", ".separator", ".separator one two":
            reset()
            cmd(i)
            b4=s.nullvalue, s.separator
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
            self.assertEqual(b4, (s.nullvalue, s.separator))

        ###
        ### command output
        ###
        for i in ".output", ".output too many args", ".output "+os.sep:
            reset()
            cmd(i)
            b4=s.stdout
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
            self.assertEqual(b4, s.stdout)

        ###
        ### Command prompt
        ###
        # not much to test until pty testing is working
        for i in ".prompt", ".prompt too many args":
            reset()
            cmd(i)
            b4=s.prompt,s.moreprompt
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
            self.assertEqual(b4, (s.prompt, s.moreprompt))

        ###
        ### Command read
        ###
        # pretty much thoroughly tested above
        write_whole_file(TESTFILEPREFIX+"test-shell-1.py", "wt", """
assert apsw
assert shell
shell.write(shell.stdout, "hello world\\n")
""")
        for i in ".read", ".read one two", ".read "+os.sep:
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])

        reset()
        cmd(".read %stest-shell-1.py" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("hello world" in get(fh[1]))

        # restore tested with backup

        ###
        ### Command - schema
        ###
        # make sure it works
        reset()
        cmd(".schema")
        s.cmdloop()
        isempty(fh[2])
        isnotempty(fh[1])
        reset()
        cmd("create table schematest(x);create index unrelatedname on schematest(x);\n.schema schematest foo notexist foo")
        s.cmdloop()
        isempty(fh[2])
        for i in "schematest", "unrelatedname":
            self.assertTrue(i in get(fh[1]))

        # separator done earlier

        ###
        ### Command - show
        ###
        # set all settings to known values
        resetcmd=".echo off\n.explain off\n.headers off\n.mode list\n.nullvalue ''\n.output stdout\n.separator |\n.width 1 2 3\n.exceptions off"
        reset()
        cmd(resetcmd)
        s.cmdloop()
        isempty(fh[2])
        isempty(fh[1])
        reset()
        cmd(".show")
        s.cmdloop()
        isempty(fh[1])
        isnotempty(fh[2])
        baseline=get(fh[2])
        for i in ".echo on", ".explain", ".headers on", ".mode column", ".nullvalue T",".separator %", ".width 8 9 1", ".exceptions on":
            reset()
            cmd(resetcmd)
            s.cmdloop()
            isempty(fh[1])
            if not get(fh[2]).startswith(".echo off"):
                isempty(fh[2])
            reset()
            cmd(i+"\n.show")
            s.cmdloop()
            isempty(fh[1])
            # check size has not changed much
            self.assertTrue(abs(len(get(fh[2]))-len(baseline))<14)

        # output
        reset()
        cmd(".output %stest-shell-1\n.show" % (TESTFILEPREFIX,))
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("output: "+TESTFILEPREFIX+"test-shell-1" in get(fh[2]))
        reset()
        cmd(".output stdout\n.show")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("output: stdout" in get(fh[2]))
        self.assertTrue(not os.path.exists("stdout"))
        # errors
        reset()
        cmd(".show one two")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("at most one parameter" in get(fh[2]))
        reset()
        cmd(".show notexist")
        s.cmdloop()
        isempty(fh[1])
        self.assertTrue("notexist: " not in get(fh[2]))

        ###
        ### Command tables
        ###
        reset()
        cmd(".tables")
        s.cmdloop()
        isempty(fh[2])
        isnotempty(fh[1])
        reset()
        cmd("create table tabletest(x);create index tabletest1 on tabletest(x);create index noway on tabletest(x);\n.tables tabletest\n.tables")
        s.cmdloop()
        isempty(fh[2])
        self.assertTrue("tabletest" in get(fh[1]))
        self.assertTrue("tabletest1" not in get(fh[1]))
        self.assertTrue("noway" not in get(fh[1]))

        ###
        ### Command timeout
        ###
        for i in (".timeout", ".timeout ksdjfh", ".timeout 6576 78987"):
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
        for i in (".timeout 1000", ".timeout 0", ".timeout -33"):
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isempty(fh[2])

        # timer is tested earlier

        ###
        ### Command width
        ###
        # does it work?
        reset()
        cmd(".width 10 10 10 0")
        s.cmdloop()
        isempty(fh[1])
        isempty(fh[2])

        def getw():
            reset()
            cmd(".show width")
            s.cmdloop()
            isempty(fh[1])
            return [int(x) for x in get(fh[2]).split()[1:]]

        self.assertEqual([10,10,10,0], getw())
        # some errors
        for i in ".width", ".width foo", ".width 1 2 3 seven 3":
            reset()
            cmd(i)
            s.cmdloop()
            isempty(fh[1])
            isnotempty(fh[2])
            self.assertEqual([10,10,10,0], getw())
        for i,r in ("9 0 9", [9,0,9]), ("10 -3 10 -3", [10,-3,10,-3]), ("0", [0]):
            reset()
            cmd(".width "+i)
            s.cmdloop()
            isempty(fh[1])
            isempty(fh[2])
            self.assertEqual(r, getw())

        ###
        ### Unicode output with all output modes
        ###
        colname=u(r"\N{BLACK STAR}8\N{WHITE STAR}")
        val=u('xxx\\u1234\\uabcdyyy this\" is nasty\u0001stuff!')
        noheadermodes=('insert',)
        # possible ways val can be represented (eg csv doubles up double quotes)
        outputs=(val, val.replace('"', '""'), val.replace('"', '&quot;'), val.replace('"', '\\"'))
        for mode in [x[len("output_"):] for x in dir(shellclass) if x.startswith("output_")]:
            reset()
            cmd(".separator |\n.width 999\n.encoding utf8\n.header on\n.mode %s\nselect '%s' as '%s';" % (mode, val, colname))
            s.cmdloop()
            isempty(fh[2])
            # modes too complicated to construct the correct string
            if mode in ('python', 'tcl'):
                continue
            # all others
            if mode not in noheadermodes:
                self.assertTrue(colname in get(fh[1]))
            cnt=0
            for o in outputs:
                cnt+=o in get(fh[1])
            self.assertTrue(cnt)

        # clean up files
        for f in fh:
            f.close()

    # This one uses the coverage module
    def _testShellWithCoverage(self):
        "Check Shell functionality (with coverage)"
        # We currently allow coverage module to not exist which helps
        # with debugging
        try:
            import coverage
        except ImportError:
            coverage=None

        import imp
        # I had problems with the compiled bytecode being around
        for suff in "c","o":
            try:
                os.remove("tools/shell.py"+suff)
            except:
                pass

        if coverage: coverage.start()
        covshell=imp.load_source("shell_coverage", "tools/shell.py")
        try:
            self._originaltestShell(shellclass=covshell.Shell)
        finally:
            if coverage:
                coverage.stop()
                coverage.annotate(morfs=[covshell])
                os.rename("tools/shell.py,cover", "shell.py.gcov")

    # Note that faults fire only once, so there is no need to reset
    # them.  The testing for objects bigger than 2GB is done in
    # testLargeObjects
    def testzzFaultInjection(self):
        "Deliberately inject faults to exercise all code paths"
        if not hasattr(apsw, "faultdict"):
            return

        def dummy(*args):
            1/0

        def dummy2(*args):
            return 7

        # The 1/0 in these tests is to cause a ZeroDivisionError so
        # that an exception is always thrown.  If we catch that then
        # it means earlier expected exceptions were not thrown.

        ## UnknownSQLiteErrorCode
        apsw.faultdict["UnknownSQLiteErrorCode"]=True
        try:
            self.db.cursor().execute("select '")
            1/0
        except:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.Error)
            self.assertTrue("254" in str(value))

        ## AsWriteBufferFails
        if not py3:
            apsw.faultdict["AsWriteBufferFails"]=True
            try:
                for row in self.db.cursor().execute("select x'1234ccddeeff'"):
                    pass
                1/0
            except MemoryError:
                pass

        ## ConnectionCloseFail
        if "APSW_NO_MEMLEAK" not in os.environ:
            apsw.faultdict["ConnectionCloseFail"]=True
            try:
                db=apsw.Connection(":memory:")
                db.cursor().execute("select 3")
                db.close(True)
                1/0
            except apsw.IOError:
                pass

        ## ConnectionCloseFail in destructor
        if "APSW_NO_MEMLEAK" not in os.environ:
            # test
            apsw.faultdict["ConnectionCloseFail"]=True
            def f():
                db=apsw.Connection(":memory:")
                db.cursor().execute("select 3")
                del db
                gc.collect()
            self.assertRaisesUnraisable(apsw.ConnectionNotClosedError, f)

        ## BlobAllocFails
        apsw.faultdict["BlobAllocFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("create table foo(ablob); insert into foo (ROWID, ablob) values (1,x'aabbccddeeff')")
            blob=db.blobopen("main", "foo", "ablob", 1, False)
            1/0
        except MemoryError:
            pass

        ## CursorAllocFails
        apsw.faultdict["CursorAllocFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("select 3")
            1/0
        except MemoryError:
            pass

        ## DBConfigFails
        apsw.faultdict["DBConfigFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.config(apsw.SQLITE_DBCONFIG_ENABLE_TRIGGER, -1)
            1/0
        except apsw.NoMemError:
            pass

        ## RollbackHookExistingError
        apsw.faultdict["RollbackHookExistingError"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setrollbackhook(dummy)
            db.cursor().execute("create table foo(a); begin ; insert into foo values(3); rollback")
            1/0
        except MemoryError:
            pass

        ## CommitHookExceptionAlready
        apsw.faultdict["CommitHookExistingError"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setcommithook(dummy)
            db.cursor().execute("begin; create table foo(a); insert into foo values(3); commit")
            1/0
        except MemoryError:
            pass

        ## AuthorizerExistingError
        apsw.faultdict["AuthorizerExistingError"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setauthorizer(dummy)
            db.cursor().execute("create table foo(a)")
            1/0
        except MemoryError:
            pass

        ## SetAuthorizerNullFail
        apsw.faultdict["SetAuthorizerNullFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setauthorizer(None)
            1/0
        except apsw.IOError:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.IOError)

        ## SetAuthorizerFail
        apsw.faultdict["SetAuthorizerFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setauthorizer(dummy)
            1/0
        except:
            pass

        ## CollationNeededNullFail
        apsw.faultdict["CollationNeededNullFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.collationneeded(None)
            1/0
        except apsw.IOError:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.IOError)

        ## CollationNeededFail
        apsw.faultdict["CollationNeededFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.collationneeded(dummy)
            1/0
        except:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.IOError)

        ##EnableLoadExtensionFail
        apsw.faultdict["EnableLoadExtensionFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.enableloadextension(True)
            1/0
        except:
            pass

        ## SetBusyHandlerNullFail
        apsw.faultdict["SetBusyHandlerNullFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setbusyhandler(None)
            1/0
        except apsw.IOError:
            pass

        ## SetBusyHandlerFail
        apsw.faultdict["SetBusyHandlerFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.setbusyhandler(dummy)
            1/0
        except apsw.IOError:
            pass

        ## UnknownValueType
        apsw.faultdict["UnknownValueType"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("dummy", dummy)
            db.cursor().execute("select dummy(4)")
            1/0
        except:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.Error)
            self.assertTrue("123456" in str(value))

        ## UnknownColumnType
        apsw.faultdict["UnknownColumnType"]=True
        try:
            db=apsw.Connection(":memory:")
            for row in db.cursor().execute("select 3"):
                pass
            1/0
        except:
            klass,value=sys.exc_info()[:2]
            self.assertTrue(klass is apsw.Error)
            self.assertTrue("12348" in str(value))

        ## SetContextResultUnicodeConversionFails
        apsw.faultdict["SetContextResultUnicodeConversionFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("foo", lambda x: u("another unicode string"))
            for row in db.cursor().execute("select foo(3)"):
                pass
            1/0
        except MemoryError:
            pass

        ## SetContextResultStringUnicodeConversionFails
        if sys.version_info<(3,0):
            apsw.faultdict["SetContextResultStringUnicodeConversionFails"]=True
            try:
                db=apsw.Connection(":memory:")
                db.createscalarfunction("foo", lambda x: "another string"*10000)
                for row in db.cursor().execute("select foo(3)"):
                    pass
                1/0
            except MemoryError:
                pass

        ## SetContextResultAsReadBufferFail
        apsw.faultdict["SetContextResultAsReadBufferFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("foo", lambda x: b("another string"))
            for row in db.cursor().execute("select foo(3)"):
                pass
            1/0
        except MemoryError:
            pass

        ## GFAPyTuple_NewFail
        apsw.faultdict["GFAPyTuple_NewFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("foo", dummy)
            for row in db.cursor().execute("select foo(3)"):
                pass
            1/0
        except MemoryError:
            pass

        ## Same again
        apsw.faultdict["GFAPyTuple_NewFail"]=True
        try:
            db=apsw.Connection(":memory:")
            def foo():
                return None, dummy2, dummy2
            db.createaggregatefunction("foo", foo)
            for row in db.cursor().execute("create table bar(x);insert into bar values(3); select foo(x) from bar"):
                pass
            1/0
        except MemoryError:
            pass

        ## CBDispatchExistingError
        apsw.faultdict["CBDispatchExistingError"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createscalarfunction("foo", dummy)
            db.cursor().execute("select foo(3)")
            1/0
        except MemoryError:
            pass

        ## CBDispatchFinalError
        apsw.faultdict["CBDispatchFinalError"]=True
        try:
            def f():
                db=apsw.Connection(":memory:")
                def foo():
                    return None, dummy, dummy2
                db.createaggregatefunction("foo", foo)
                for row in db.cursor().execute("create table bar(x);insert into bar values(3); select foo(x) from bar"):
                    pass
                1/0
            self.assertRaisesUnraisable(Exception, f)
        except ZeroDivisionError:
            pass

        ## Virtual table code
        class Source:
            def Create(self, *args):
                return "create table foo(x,y)", Table()
            Connect=Create
        class Table:
            def __init__(self):
                self.data=[ #("rowid", "x", "y"),
                            [0, 1, 2],
                            [3, 4, 5]]
            def Open(self):
                return Cursor(self)

            def BestIndex(self, *args): return None

            def UpdateChangeRow(self, rowid, newrowid, fields):
                for i, row in enumerate(self.data):
                    if row[0]==rowid:
                        self.data[i]=[newrowid]+list(fields)

            def FindFunction(self, *args):
                return lambda *args: 1

        class Cursor:
            def __init__(self, table):
                self.table=table
                self.row=0
            def Eof(self):
                return self.row>=len(self.table.data)
            def Rowid(self):
                return self.table.data[self.row][0]
            def Column(self, col):
                return self.table.data[self.row][1+col]
            def Filter(self, *args):
                self.row=0
            def Next(self):
                self.row+=1
                def Close(self): pass

        ## VtabCreateBadString
        apsw.faultdict["VtabCreateBadString"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createmodule("nonsense", None)
            db.cursor().execute("create virtual table foo using nonsense(3,4)")
            1/0
        except MemoryError:
            pass

        ## VtabUpdateChangeRowFail
        apsw.faultdict["VtabUpdateChangeRowFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createmodule("foo", Source())
            db.cursor().execute("create virtual table foo using foo();update foo set x=3 where y=2")
            1/0
        except MemoryError:
            pass

        ## VtabUpdateBadField
        apsw.faultdict["VtabUpdateBadField"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createmodule("foo", Source())
            db.cursor().execute("create virtual table foo using foo();update foo set x=3 where y=2")
            1/0
        except MemoryError:
            pass

        ## VtabRenameBadName
        apsw.faultdict["VtabRenameBadName"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createmodule("foo", Source())
            db.cursor().execute("create virtual table foo using foo(); alter table foo rename to bar")
            1/0
        except MemoryError:
            pass

        ## VtabRenameBadName
        apsw.faultdict["CreateModuleFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.createmodule("foo", Source())
            1/0
        except apsw.IOError:
            pass

        ## FindFunctionAllocFailed
        apsw.faultdict["FindFunctionAllocFailed"]=True
        try:
            db=apsw.Connection(":memory:")
            db.overloadfunction("xyz", 2)
            db.createmodule("foo", Source())
            db.cursor().execute("create virtual table foo using foo()")
            db.cursor().execute("select xyz(x,y) from foo")
            1/0
        except MemoryError:
            pass

        ## BlobDeallocException
        def f():
            db=apsw.Connection(":memory:")
            db.cursor().execute("create table foo(b);insert into foo(rowid,b) values(2,x'aabbccddee')")
            blob=db.blobopen("main", "foo", "b", 2, False) # open read-only
            # deliberately cause problem
            try:  blob.write(b('a'))
            except apsw.ReadOnlyError:   pass
            # garbage collect
            del blob
            gc.collect()

        self.assertRaisesUnraisable(apsw.ReadOnlyError, f)

        ## BlobWriteAsReadBufFails
        apsw.faultdict["BlobWriteAsReadBufFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("create table foo(b);insert into foo(rowid,b) values(2,x'aabbccddee')")
            blob=db.blobopen("main", "foo", "b", 2, True)
            blob.write(b("aaaaaa"))
            1/0
        except MemoryError:
            pass

        ## GetDescriptionFail
        apsw.faultdict["GetDescriptionFail"]=True
        try:
            db=apsw.Connection(":memory:")
            c=db.cursor()
            c.execute("create table foo(b);insert into foo(rowid,b) values(2,x'aabbccddee');select * from foo")
            c.getdescription()
            1/0
        except MemoryError:
            pass

        ## DoBindingUnicodeConversionFails
        apsw.faultdict["DoBindingUnicodeConversionFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("select ?", (u("abc"),))
            1/0
        except MemoryError:
            pass

        ## DoBindingStringConversionFails
        if sys.version_info<(3,0):
            apsw.faultdict["DoBindingStringConversionFails"]=True
            try:
                db=apsw.Connection(":memory:")
                db.cursor().execute("select ?", ("abc"*10000,))
                1/0
            except MemoryError:
                pass

        ## DoBindingAsReadBufferFails
        apsw.faultdict["DoBindingAsReadBufferFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("select ?", (b("abcd"),))
            1/0
        except MemoryError:
            pass

        ## DoExecTraceBadSlice
        apsw.faultdict["DoExecTraceBadSlice"]=True
        try:
            db=apsw.Connection(":memory:")
            c=db.cursor()
            c.setexectrace(dummy)
            c.execute("select ?; select ?; select ?", (1,2,3))
            1/0
        except MemoryError:
            pass

        ## EnableSharedCacheFail
        apsw.faultdict["EnableSharedCacheFail"]=True
        try:
            apsw.enablesharedcache(True)
            1/0
        except apsw.NoMemError:
            pass

        ## InitializeFail
        apsw.faultdict["InitializeFail"]=True
        try:
            apsw.initialize()
            1/0
        except apsw.NoMemError:
            pass

        ## ShutdownFail
        apsw.faultdict["ShutdownFail"]=True
        try:
            apsw.shutdown()
            1/0
        except apsw.NoMemError:
            pass

        ### vfs routines

        class FaultVFS(apsw.VFS):
            def __init__(self, name="faultvfs", inherit="", makedefault=False):
                super(FaultVFS, self).__init__(name, inherit, makedefault=makedefault)

            def xGetLastErrorLong(self):
                return "a"*1024

            def xOpen(self, name, flags):
                return FaultVFSFile(name, flags)

        class FaultVFSFile(apsw.VFSFile):
            def __init__(self, name, flags):
                super(FaultVFSFile,self).__init__("", name, flags)

        vfs=FaultVFS()

        ## xFullPathnameConversion
        apsw.faultdict["xFullPathnameConversion"]=True
        self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, MemoryError,  apsw.Connection, TESTFILEPREFIX+"testdb", vfs="faultvfs")

        ## xDlError
        db=apsw.Connection(":memory:", vfs="faultvfs")
        if hasattr(db, 'enableloadextension'):
            db.enableloadextension(True)
            ## xDlErrorAllocFail
            apsw.faultdict["xDlErrorAllocFail"]=True
            self.assertRaises(apsw.ExtensionLoadingError,
                              self.assertRaisesUnraisable, MemoryError,
                              db.loadextension, "non-existent-file-name")
            ## xDlErrorUnicodeFail
            apsw.faultdict["xDlErrorUnicodeFail"]=True
            self.assertRaises(apsw.ExtensionLoadingError,
                              self.assertRaisesUnraisable, MemoryError,
                              db.loadextension, "non-existent-file-name")
        del db
        gc.collect()
        ## xRandomnessAllocFail
        if hasattr(apsw, 'test_reset_rng'):
            # we need to be default vfs
            vfs2=FaultVFS("faultvfs2", apsw.vfsnames()[0], makedefault=True)
            apsw.test_reset_rng()
            apsw.faultdict["xRandomnessAllocFail"]=True
            # doesn't matter which vfs opens the file
            self.assertRaisesUnraisable(MemoryError, apsw.Connection(":memory:").cursor().execute, "select randomblob(10)")
            del vfs2
            gc.collect()

        ## xCurrentTimeFail
        apsw.faultdict["xCurrentTimeFail"]=True
        self.assertRaisesUnraisable(apsw.SQLError, apsw.Connection(":memory:", vfs="faultvfs").cursor().execute, "select date('now')")

        ## xGetLastErrorAllocFail
        if hasattr(apsw, 'test_call_xGetLastError'):
            apsw.faultdict["xGetLastErrorAllocFail"]=True
            vfs2=FaultVFS("faultvfs2", "faultvfs")
            vfs.xGetLastError=vfs.xGetLastErrorLong
            self.assertRaisesUnraisable(MemoryError, apsw.test_call_xGetLastError, "faultvfs2", 128)
            vfs.xGetLastError=super(FaultVFS, vfs).xGetLastError

        ## APSWVFSDeallocFail
        apsw.faultdict["APSWVFSDeallocFail"]=True
        def foo():
            vfs2=FaultVFS("faultvfs2", "faultvfs")
            del vfs2
            gc.collect()
        self.assertRaisesUnraisable(apsw.IOError, foo)

        ## APSWVFSBadVersion
        apsw.faultdict["APSWVFSBadVersion"]=True
        self.assertRaises(ValueError, apsw.VFS, "foo", "")
        self.assertTrue("foo" not in apsw.vfsnames())

        ## APSWVFSRegistrationFails
        apsw.faultdict["APSWVFSRegistrationFails"]=True
        self.assertRaises(apsw.NoMemError, apsw.VFS, "foo", "")
        self.assertTrue("foo" not in apsw.vfsnames())

        ## xReadReadBufferFail
        try:
            # This will fail if we are using auto-WAL so we don't run
            # the rest of the test in WAL mode.
            apsw.Connection(TESTFILEPREFIX+"testdb", vfs="faultvfs").cursor().execute("create table dummy1(x,y)")
            openok=True
        except apsw.CantOpenError:
            if len(apsw.connection_hooks)==0:
                raise
            openok=False

        # The following tests cause failures when making the
        # connection because a connection hook turns on wal mode which
        # causes database reads which then cause failures
        if openok:
            apsw.faultdict["xReadReadBufferFail"]=True
            def foo():
                apsw.Connection(TESTFILEPREFIX+"testdb", vfs="faultvfs").cursor().execute("select * from dummy1")
            self.assertRaises(apsw.SQLError, self.assertRaisesUnraisable, TypeError, foo)

            ## xUnlockFails
            apsw.faultdict["xUnlockFails"]=True
            # Used to wrap in self.assertRaises(apsw.IOError, ...) but SQLite no longer passes on the error.
            # See https://sqlite.org/cvstrac/tktview?tn=3946
            self.assertRaisesUnraisable(apsw.IOError, apsw.Connection(TESTFILEPREFIX+"testdb", vfs="faultvfs").cursor().execute, "select * from dummy1")

            ## xSyncFails
            apsw.faultdict["xSyncFails"]=True
            self.assertRaises(apsw.IOError, self.assertRaisesUnraisable, apsw.IOError, apsw.Connection(TESTFILEPREFIX+"testdb", vfs="faultvfs").cursor().execute, "insert into dummy1 values(3,4)")

            ## xFileSizeFails
            apsw.faultdict["xFileSizeFails"]=True
            self.assertRaises(apsw.IOError, self.assertRaisesUnraisable, apsw.IOError, apsw.Connection(TESTFILEPREFIX+"testdb", vfs="faultvfs").cursor().execute, "select * from dummy1")

        ## xCheckReservedLockFails
        apsw.faultdict["xCheckReservedLockFails"]=True
        self.assertRaises(apsw.IOError, self.assertRaisesUnraisable, apsw.IOError, testdb, vfsname="faultvfs")

        ## xCheckReservedLockIsTrue
        apsw.faultdict["xCheckReservedLockIsTrue"]=True
        testdb(vfsname="faultvfs")

        ## xCloseFails
        t=apsw.VFSFile("", os.path.abspath(TESTFILEPREFIX+"testfile"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])
        apsw.faultdict["xCloseFails"]=True
        self.assertRaises(apsw.IOError, t.xClose)
        del t
        # now catch it in the destructor
        def foo():
            t=apsw.VFSFile("", os.path.abspath(TESTFILEPREFIX+"testfile"), [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])
            apsw.faultdict["xCloseFails"]=True
            del t
            gc.collect()
        self.assertRaisesUnraisable(apsw.IOError, foo)

        ## vfspyopen_fullpathnamemallocfailed
        del FaultVFS.xOpen # remove overriding fault xOpen method so we get default implementation
        apsw.faultdict["vfspyopen_fullpathnamemallocfailed"]=True
        self.assertRaises(MemoryError, vfs.xOpen, "doesn't matter", apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE)
        # and again in file open
        apsw.faultdict["vfspyopen_fullpathnamemallocfailed"]=True
        self.assertRaises(MemoryError, apsw.VFSFile, "", "/doesn't matter", [apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE,0])

        ## vfsnamesfails
        apsw.faultdict["vfsnamesfails"]=True
        self.assertRaises(MemoryError, apsw.vfsnames)

        ## StatementCacheAllocFails
        apsw.faultdict["StatementCacheAllocFails"]=True
        try:
            apsw.Connection(":memory:")
            1/0
        except MemoryError:
            pass

        ## TransferBindingsFail
        apsw.faultdict["TransferBindingsFail"]=True
        try:
            db=apsw.Connection(":memory:")
            db.cursor().execute("create table foo(x,y); insert into foo values(3,4)")
            db.cursor().execute("create index fooxy on foo(x,y)")
            for row in db.cursor().execute("select * from foo"):
                pass
            db.cursor().execute("drop index fooxy")
            for row in db.cursor().execute("select * from foo"):
                pass
            1/0
        except apsw.NoMemError:
            pass

        ## OverloadFails
        apsw.faultdict["OverloadFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.overloadfunction("foo", 1)
            1/0
        except apsw.NoMemError:
            pass

        ## ConnectionEnterExecFailed
        apsw.faultdict["ConnectionEnterExecFailed"]=True
        try:
            db=apsw.Connection(":memory:")
            db.__enter__()
            1/0
        except apsw.NoMemError:
            pass

        ## BackupInitFails
        apsw.faultdict["BackupInitFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.backup("main", apsw.Connection(":memory:"), "main")
            1/0
        except apsw.NoMemError:
            pass

        ## BackupNewFails
        apsw.faultdict["BackupNewFails"]=True
        try:
            db=apsw.Connection(":memory:")
            db.backup("main", apsw.Connection(":memory:"), "main")
            1/0
        except MemoryError:
            pass

        ## FormatSQLValueResizeFails
        apsw.faultdict["FormatSQLValueResizeFails"]=True
        try:
            apsw.format_sql_value(u("fsdkljfl'fdsfds"))
            1/0
        except SystemError:
            pass

        ## FormatSQLValueAsReadBufferFails
        apsw.faultdict["FormatSQLValueAsReadBufferFails"]=True
        try:
            apsw.format_sql_value(b("abcd"))
            1/0
        except MemoryError:
            pass

        ## FormatSQLValuePyUnicodeFromUnicodeFails
        apsw.faultdict["FormatSQLValuePyUnicodeFromUnicodeFails"]=True
        try:
            apsw.format_sql_value(b("abcd"))
            1/0
        except MemoryError:
            pass

        ## WalAutocheckpointFails
        apsw.faultdict["WalAutocheckpointFails"]=True
        try:
            apsw.Connection(":memory:").wal_autocheckpoint(77)
            1/0
        except apsw.IOError:
            pass

        ## WalCheckpointFails
        apsw.faultdict["WalCheckpointFails"]=True
        try:
            apsw.Connection(":memory:").wal_checkpoint()
            1/0
        except apsw.IOError:
            pass

    # This test is run last by deliberate name choice.  If it did
    # uncover any bugs there isn't much that can be done to turn the
    # checker off.
    def testzzForkChecker(self):
        "Test detection of using objects across fork"
        # need to free up everything that already exists
        self.db.close()
        gc.collect()
        # install it
        apsw.fork_checker()
        # return some objects
        def getstuff():
            db=apsw.Connection(":memory:")
            cur=db.cursor()
            for row in cur.execute("create table foo(x);insert into foo values(1);insert into foo values(x'aabbcc'); select last_insert_rowid()"):
                blobid=row[0]
            blob=db.blobopen("main", "foo", "x", blobid, 0)
            db2=apsw.Connection(":memory:")
            if hasattr(db2, "backup"):
                backup=db2.backup("main", db, "main")
            else:
                backup=None
            return (db,cur,blob,backup)
        # test the objects
        def teststuff(db, cur, blob, backup):
            if db:
                db.cursor().execute("select 3")
            if cur:
                cur.execute("select 3")
            if blob:
                blob.read(1)
            if backup:
                backup.step()

        # Sanity check
        teststuff(*getstuff())
        # get some to use in parent
        parent=getstuff()
        # to be used (and fail with error) in child
        child=getstuff()

        def childtest(*args):
            # we can't use unittest methods here since we are in a different process
            val=args[0]
            args=args[1:]
            # this should work
            teststuff(*getstuff())
            # ignore the unraiseable stuff sent to sys.excepthook
            def eh(*args): pass
            sys.excepthook=eh
            # call with each seperate item to check
            try:
                for i in range(len(args)):
                    a=[None]*len(args)
                    a[i]=args[i]
                    try:
                        teststuff(*a)
                    except apsw.ForkingViolationError:
                        pass
            except apsw.ForkingViolationError:
                # we get one final exception "between" line due to the
                # nature of how the exception is raised
                pass
            # this should work again
            teststuff(*getstuff())
            val.value=1

        import multiprocessing
        val=multiprocessing.Value("i", 0)
        p=multiprocessing.Process(target=childtest, args=[val]+list(child))
        p.start()
        p.join()
        self.assertEqual(1, val.value) # did child complete ok?
        teststuff(*parent)



testtimeout=False # timeout testing adds several seconds to each run
def testdb(filename=TESTFILEPREFIX+"testdb2", vfsname="apswtest", closedb=True, mode=None, attachdb=None):
    "This method causes all parts of a vfs to be executed"
    gc.collect() # free any existing db handles
    for suf in "", "-journal", "x", "x-journal":
        deletefile(filename+suf)

    db=apsw.Connection("file:"+filename+"?psow=0", vfs=vfsname, flags=openflags)
    if mode:
        db.cursor().execute("pragma journal_mode="+mode)
    db.cursor().execute("create table foo(x,y); insert into foo values(1,2); insert into foo values(date('now'), date('now'))")
    if testtimeout:
        # busy
        db2=apsw.Connection(filename, vfs=vfsname)
        if mode:
            db2.cursor().execute("pragma journal_mode="+mode)
        db.setbusytimeout(1100)
        db2.cursor().execute("begin exclusive")
        try:
            db.cursor().execute("begin immediate")
            1/0 # should not be reached
        except apsw.BusyError:
            pass
        db2.cursor().execute("end")

    # cause truncate to be called
    # see sqlite test/pager3.test where this (public domain) code is taken from
    # I had to add the pragma journal_mode to get it to work
    c=db.cursor()
    for row in c.execute("pragma journal_mode=truncate"):
        pass

    c.execute("""
                 create table t1(a unique, b);
                 insert into t1 values(1, 'abcdefghijklmnopqrstuvwxyz');
                 insert into t1 values(2, 'abcdefghijklmnopqrstuvwxyz');
                 update t1 set b=b||a||b;
                 update t1 set b=b||a||b;
                 update t1 set b=b||a||b;
                 update t1 set b=b||a||b;
                 update t1 set b=b||a||b;
                 update t1 set b=b||a||b;
                 create temp table t2 as select * from t1;
                 begin;
                 create table t3(x);""")
    try:
        c.execute("insert into t1 select 4-a, b from t2")
    except apsw.ConstraintError:
        pass
    c.execute("rollback")

    if attachdb:
        c.execute("attach '%s' as second" % (attachdb,))

    if hasattr(APSW, "testLoadExtension"):
        # can we use loadextension?
        db.enableloadextension(True)
        try:
            db.loadextension("./"*128+LOADEXTENSIONFILENAME+"xxx")
        except apsw.ExtensionLoadingError:
            pass
        db.loadextension(LOADEXTENSIONFILENAME)
        assert(1==next(db.cursor().execute("select half(2)"))[0])

    # Get the routine xCheckReservedLock to be called.  We need a hot journal
    # which this code adapted from SQLite's pager.test does
    if not iswindows:
        c.execute("create table abc(a,b,c)")
        for i in range(20):
            c.execute("insert into abc values(1,2,?)", (randomstring(200),))
        c.execute("begin; update abc set c=?", (randomstring(200),))

        write_whole_file(filename+"x", "wb", read_whole_file(filename, "rb"))
        write_whole_file(filename+"x-journal", "wb", read_whole_file(filename+"-journal", "rb"))

        f=open(filename+"x-journal", "ab")
        f.seek(-1032, 2) # 1032 bytes before end of file
        f.write(b(r"\x00\x00\x00\x00"))
        f.close()

        hotdb=apsw.Connection(filename+"x", vfs=vfsname)
        if mode:
            hotdb.cursor().execute("pragma journal_mode="+mode)
        hotdb.cursor().execute("select sql from sqlite_master")
        hotdb.close()

    if closedb:
        db.close()
    else:
        return db


if not iswindows:
    # note that a directory must be specified otherwise $LD_LIBRARY_PATH is used
    LOADEXTENSIONFILENAME="./testextension.sqlext"
else:
    LOADEXTENSIONFILENAME="testextension.sqlext"

MEMLEAKITERATIONS=1000
PROFILESTEPS=250000


def setup(write=write):
    """Call this if importing this test suite as it will ensure tests
    we can't run are removed etc.  It will also print version
    information."""

    print_version_info(write)

    if hasattr(apsw, "config"):
        apsw.config(apsw.SQLITE_CONFIG_MEMSTATUS, True) # ensure memory tracking is on
    apsw.initialize() # manual call for coverage
    memdb=apsw.Connection(":memory:")
    if not getattr(memdb, "enableloadextension", None):
        del APSW.testLoadExtension

    forkcheck=False
    if hasattr(apsw, "fork_checker") and hasattr(os, "fork"):
        try:
            import multiprocessing
            # sometimes the import works but doing anything fails
            val=multiprocessing.Value("i", 0)
            forkcheck=True
        except ImportError:
            pass

    # we also remove forkchecker if doing multiple iterations
    if not forkcheck or "APSW_TEST_ITERATIONS" in os.environ:
        del APSW.testzzForkChecker

    # These tests are of experimental features
    if not hasattr(memdb, "backup"):
        del APSW.testBackup
    if not hasattr(apsw, "config"):
        del APSW.testConfig
    if not hasattr(memdb, "limit"):
        del APSW.testLimits
    if not hasattr(memdb, "setprofile"):
        del APSW.testProfile
    if not hasattr(memdb, "createmodule"):
        del APSW.testVtables
        del APSW.testVTableExample

    # We can do extension loading but no extension present ...
    if getattr(memdb, "enableloadextension", None) and not os.path.exists(LOADEXTENSIONFILENAME):
        write("Not doing LoadExtension test.  You need to compile the extension first\n")
        if sys.platform.startswith("darwin"):
            write("  gcc -fPIC -bundle -o "+LOADEXTENSIONFILENAME+" -I. -Isqlite3 src/testextension.c\n")
        else:
            write("  gcc -fPIC -shared -o "+LOADEXTENSIONFILENAME+" -I. -Isqlite3 src/testextension.c\n")
        del APSW.testLoadExtension
        sys.stdout.flush()

    # coverage testing of the shell
    if "APSW_PY_COVERAGE" in os.environ:
        APSW._originaltestShell=APSW.testShell
        APSW.testShell=APSW._testShellWithCoverage

    del memdb

# This can't be a member of APSW class above because Python 2.3
# unittest gets confused and tries to execute it!
test_types_vals=("a simple string",  # "ascii" string
          "0123456789"*200000, # a longer string
          u(r"a \u1234 unicode \ufe54 string \u0089"),  # simple unicode string
          u(r"\N{BLACK STAR} \N{WHITE STAR} \N{LIGHTNING} \N{COMET} "), # funky unicode or an episode of b5
          u(r"\N{MUSICAL SYMBOL G CLEF}"), # http://www.cmlenz.net/archives/2008/07/the-truth-about-unicode-in-python
          97, # integer
          2147483647,   # numbers on 31 bit boundary (32nd bit used for integer sign), and then
          -2147483647,  # start using 32nd bit (must be represented by 64bit to avoid losing
          long(2147483648),  # detail)
          long(-2147483648),
          long(2147483999),
          long(-2147483999),
          992147483999,
          -992147483999,
          9223372036854775807,
          -9223372036854775808,
          b("a set of bytes"),      # bag of bytes initialised from a string, but don't confuse it with a
          b("".join(["\\x%02x" % (x,) for x in range(256)])), # string
          b("".join(["\\x%02x" % (x,) for x in range(256)])*20000),  # non-trivial size
          None,  # our good friend NULL/None
          1.1,  # floating point can't be compared exactly - assertAlmostEqual is used to check
          10.2, # see Appendix B in the Python Tutorial
          1.3,
          1.45897589347E97,
          5.987987/8.7678678687676786,
          math.pi,
          True,  # derived from integer
          False
          )


if __name__=='__main__':
    setup()

    def runtests():
        def set_wal_mode(c):
            # Note that WAL won't be on for memory databases.  This
            # execution returns the active mode
            c.cursor().execute("PRAGMA journal_mode=WAL").fetchall()

        b4=apsw.connection_hooks[:]
        try:
            if "APSW_TEST_WALMODE" in os.environ:
                apsw.connection_hooks.append(set_wal_mode)
                sys.stderr.write("WAL: ")

            if os.getenv("PYTRACE"):
                import trace
                t=trace.Trace(count=0, trace=1, ignoredirs=[sys.prefix, sys.exec_prefix])
                t.runfunc(unittest.main)
            else:
                unittest.main()
        finally:
            apsw.connection_hooks=b4

    v=os.environ.get("APSW_TEST_ITERATIONS", None)
    if v is None:
        try:
            runtests()
        except SystemExit:
            exitcode=sys.exc_info()[1].code
    else:
        # we run all the tests multiple times which has better coverage
        # a larger value for MEMLEAKITERATIONS slows down everything else
        MEMLEAKITERATIONS=5
        PROFILESTEPS=1000
        v=int(v)
        for i in range(v):
            write("Iteration "+str(i+1)+" of "+str(v)+"\n")
            try:

                runtests()
            except SystemExit:
                exitcode=sys.exc_info()[1].code

    # Free up everything possible
    del APSW
    del ThreadRunner
    del randomintegers

    # clean up sqlite and apsw
    gc.collect() # all cursors & connections must be gone
    apsw.shutdown()
    apsw.config(apsw.SQLITE_CONFIG_LOG, None)
    if hasattr(apsw, "_fini"):
        apsw._fini()
        gc.collect()
    del apsw

    exit=sys.exit

    # modules
    del unittest
    del os
    del math
    del random
    del time
    del threading
    del Queue
    del traceback
    del re
    gc.collect()

    if py3: # doesn't handle modules being deleted very well
        exit(exitcode)

    # In py3 gc and sys can end up being None even though we take care not to delete them
    for k in list(sys.modules.keys()):
        if k not in ('gc', 'sys', '__main__'):
            try:
                del sys.modules[k]
            except:
                pass

    del sys

    if gc:
        gc.collect()

    del gc
    exit(exitcode)
