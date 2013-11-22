
"""Hello, World for 'do'."""

from doitlib.task import Task


class default(Task):
    default = True
    deps = ["hello", "bye"]

class hello(Task):
    "say hi"
    def doit(self):
        print "Hello, World!"

class bye(Task):
    "say bye"
    def doit(self):
        print "Bye bye."
