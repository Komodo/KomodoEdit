
all: rmtree.exe rmtreew.exe

rmtree.obj: rmtree.c
	cl /nologo rmtree.c /c

rmtree.exe: rmtree.obj
        link /nologo /subsystem:console /out:rmtree.exe rmtree.obj

rmtreew.exe: rmtree.c
        link /nologo /subsystem:windows /out:rmtreew.exe rmtree.obj

setup:
	IF NOT EXIST foo; mkdir foo
        IF NOT EXIST foo\afile; echo bar > foo\afile
        attrib +R foo\afile
	IF NOT EXIST foo\adir; mkdir foo\adir
	IF NOT EXIST foo\adir\anotherfile; echo bar > foo\adir\anotherfile

test: setup
        rmtree.exe foo
testw: setup
        rmtreew.exe foo

