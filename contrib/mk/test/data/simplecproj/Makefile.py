import os
import glob
import shutil
from mklib import Task, File

class prog(Task):
    default = True
    deps = ["prog.o"]
    results = ["prog"]
    def make(self):
        print "link it"
        shutil.copy("prog.o", "prog")

class prog_o(Task):
    deps = ["prog.c"]
    results = ["prog.o"]
    def make(self):
        print "compile it"
        shutil.copy("prog.c", "prog.o")

class prog_c(File):
    path = "prog.c"
    deps = ["prog.h"]



class clean(Task):
    def make(self):
        for path in ("prog", "prog.o"):
            if os.path.exists(path):
                os.remove(path)

class distclean(Task):
    deps = ["clean"]
    def make(self):
        for path in ("prog.c", "prog.h"):
            if os.path.exists(path):
                os.remove(path)
