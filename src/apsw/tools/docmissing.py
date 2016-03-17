# python
#
# See the accompanying LICENSE file.
#
# Find things that haven't been documented and should be or have been
# but don't exist.

import glob, sys

import apsw

retval=0

classes={}

for filename in glob.glob("doc/*.rst"):
    for line in open(filename, "rtU"):
        line=line.strip().split()

        if len(line)>=2:
            if line[0]==".." and line[1] in ("method::", "automethod::", "attribute::"):
                funcname=line[2].split("(")[0].strip()

                if "." in funcname:
                    klass, funcname=funcname.split(".",1)
                else:
                    klass="apsw"
                if klass not in classes:
                    classes[klass]=[]
                classes[klass].append(funcname)


# ok, so we know what was documented.  Now lets see what exists

con=apsw.Connection(":memory:")
cur=con.cursor()
cur.execute("create table x(y); insert into x values(x'abcdef1012');select * from x")
blob=con.blobopen("main", "x", "y", con.last_insert_rowid(), 0)
vfs=apsw.VFS("aname", "")
vfsfile=apsw.VFSFile("", ":memory:", [apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_CREATE|apsw.SQLITE_OPEN_READWRITE, 0])

# virtual tables aren't real - just check their size hasn't changed
assert len(classes['VTModule'])==2
del classes['VTModule']
assert len(classes['VTTable'])==13
del classes['VTTable']
assert len(classes['VTCursor'])==6
del classes['VTCursor']

for name, obj in ( ('Connection', con),
                   ('Cursor', cur),
                   ('blob', blob),
                   ('VFS', vfs),
                   ('VFSFile', vfsfile),
                   ('apsw', apsw),
                   ):
    if name not in classes:
        retval=1
        print "class", name,"not found"
        continue

    for c in classes[name]:
        if not hasattr(obj, c):
            # it is legit for these to be missing from code (currently because code is broken)
            if (name+"."+c) in ("apsw.async_control", "apsw.async_initialize", "apsw.async_run", "apsw.async_shutdown"):
                continue
            retval=1
            print "%s.%s in documentation but not object" % (name, c)
    for c in dir(obj):
        if c.startswith("__"): continue
        if name=="apsw":
            # ignore constants and modules
            if type(getattr(apsw, c)) in (type(3), type(sys)):
                continue
            # ignore debugging thingies
            if c.startswith("test_") or c in ("faultdict", "_fini"):
                continue
            # ignore the exceptions
            if isinstance(getattr(apsw, c), type) and issubclass(getattr(apsw,c), Exception):
                continue
            # ignore classes !!!
            if c in ("Connection", "VFS", "VFSFile", "zeroblob", "Shell", "URIFilename"):
                continue
            # ignore mappings !!!
            if c.startswith("mapping_"):
                continue
        if c not in classes[name]:
            if "%s.%s" % (name, c)  not in ("Cursor.next",):
                retval=1
                print "%s.%s on object but not in documentation" % (name, c)

sys.exit(retval)
