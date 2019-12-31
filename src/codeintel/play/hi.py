"""hi.py - say hi"""
from __future__ import print_function
import sys, getopt

__version__ = "1.0.0"

class Greeter(object):
    "a helper class for greeting people"
    def __init__(self, name=None):
        self.name = name
    def greet(self):
        if self.name:
            print("hi,", self.name)
        else:
            print("hi there")

def hi(name=None):
    g = Greeter(name)
    g.greet()

def main(argv):
    try:
        opts, args = getopt.getopt(argv[1:], "hn:")
    except getopt.GetoptError as ex:
        print("illegal options: %s" % ex)
    name = None
    for opt, optarg in opts:
        if opt == "-h":
            print(__doc__)
        elif opt == "-n":
            name = optarg
    return hi(name)

if __name__ == "__main__":
    sys.exit( main(sys.argv) )
