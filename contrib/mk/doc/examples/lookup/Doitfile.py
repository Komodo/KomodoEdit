from doitlib.task import Task

class hi(Task):
    default = True
    def doit(self):
        print "hi"
