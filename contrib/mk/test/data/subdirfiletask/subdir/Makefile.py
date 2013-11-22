from os.path import join
from mklib import Task, File
from mklib.sh import touch

class answer(Task):
    "touch answer.txt"
    results = ["answer.txt"]
    def make(self):
        touch(join(self.dir, "answer.txt"))

class answer_txt(File):
    path = "answer.txt"
    deps = ["question.txt"]

