import os
from os.path import join, exists
from mklib import include, Task

include("subdir/Makefile.py")

class clean(Task):
    "clean up for test"
    def make(self):
        to_del = ["answer.txt",
                  join("subdir", "answer.txt")]
        for path in to_del:
            if exists(path):
                os.remove(path)
