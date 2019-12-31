from __future__ import print_function
from mklib import Task
class answer(Task):
    default = True
    results = ["answer.txt"]
    def make(self):
        print("creating answer.txt")
        open("answer.txt", 'w')
