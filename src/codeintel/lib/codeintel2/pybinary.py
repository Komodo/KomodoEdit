#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Python binary file scanner for CodeIntel"""

import os
import types
import itertools
import imp
import subprocess
import sys
import cStringIO as io
import optparse


class BinaryScanError(Exception): pass


def safe_scan(path, python):
    # will eventually call "main" defined below
    proc = subprocess.Popen([python, os.path.abspath(__file__), path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env=dict(PYTHONPATH=":".join(sys.path)))
    out, err = proc.communicate()
    if err:
        raise BinaryScanError(err)
    return out
    

def scan(path):
    from gencix.python import gencix
    
    name,_ = os.path.splitext(os.path.basename(path))
    dir = os.path.dirname(path)

    root = gencix.Element('codeintel', version='2.0', name=name)
    
    gencix.docmodule(name, root, usefile=True, dir=dir)
    gencix.perform_smart_analysis(root)
    gencix.prettify(root)
    
    tree = gencix.ElementTree(root)
    
    stream = io.StringIO()
    try:
        stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(stream)
        return stream.getvalue()
    finally:
        stream.close()
    

def main(argv):
    parser = optparse.OptionParser(usage="%prog mdoulepath")
    (options, args) = parser.parse_args(args=argv)
    if len(args) != 1:
        parser.error("Incorrect number of args")
    
    mod_path = os.path.abspath(args[0])
    if not os.path.isfile(mod_path):
        parser.error("'%s' is not a file" % mod_path)
    
    cix = scan(mod_path)
    print cix


if __name__ == '__main__':
    main(sys.argv[1:])

