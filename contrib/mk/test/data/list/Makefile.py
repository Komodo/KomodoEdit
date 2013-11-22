from mklib import Task

class foo(Task):
    "do some foo"
    deps = ["foo"]
class bar(Task):
    # no description here
    def deps(self):
        yield "a.txt"
        yield "b.txt"
class baz(Task):
    default = True
class quux(Task):
    def deps(self):
        return ["p.txt", "q.txt"]


