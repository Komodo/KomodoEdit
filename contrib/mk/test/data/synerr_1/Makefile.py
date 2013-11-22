from mklib import Task

class foo(Task):
    "do some foo"
    default = True
    deps = "b"

