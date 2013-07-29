#! /usr/bin/env python3

def sortwords(*wordlist, case_sensitive=False):
    pass

def compare(a, b, *, key=None):
    pass

def f(a: int=1):
    print(a)

class Haulable(object):
    pass

class PackAnimal(object):
    pass

class Distance(object):
    pass

class Pack(object):
    def sub(self) -> int:
        return "any kind of object anyway"

    def haul(self, item: Haulable, *vargs: PackAnimal) -> Distance:
        pass

print(Pack().sub())
