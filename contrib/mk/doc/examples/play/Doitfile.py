from doitlib.task import Task
class answer(Task):
    default = True
    deps = ["answer.txt"]
    def doit(self):
        print "do answer"
