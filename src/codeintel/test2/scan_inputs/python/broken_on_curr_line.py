# Test that the Python CILE can handle breakage on the current line.

import os

class Person(Mammal):
    def __init__(self, name):
        self.name = name
        self.genus = "Homo Sapiens"

if __name__ == "__main__":
    trentm = Person("Trent Mick")
    trentm.        # current line is here, cursor is meant to be at the '.'

    print "done"

