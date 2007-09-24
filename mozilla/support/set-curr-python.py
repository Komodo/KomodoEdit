#!/usr/bin/python

"""  Set the current Python to the given version.

  Usage:
    sudo set-curr-python.py <pyver>

  where "<pyver>" is "<major>.<minor>" for a Python installed under
  '/Library/Frameworks'.

  Note: We are talking about a non-system framework Python install. I.e. a
  Python installed in '/Library/Frameworks' and '/usr/local/bin'.
"""

import sys
import os


class Error(Exception):
    pass


def set_curr_python(pyver):
    pyver_dir = "/Library/Frameworks/Python.framework/Versions/"+pyver
    if not os.path.exists(pyver_dir):
        raise Error("'%s' does not exist: you must install Python %s"
                    % (pyver_dir, pyver))
    
    curr_link = "/Library/Frameworks/Python.framework/Versions/Current"
    print "ln -s %s %s" % (pyver, curr_link)
    os.remove(curr_link)
    os.symlink(pyver, curr_link)
    
    for name in ("python", "pythonw", "python-config", "pydoc"):
        bin_path = os.path.join("/usr/local/bin", name)
        print "reset '%s'" % bin_path
        fmwk_path = os.path.join(pyver_dir, "bin", name)
        if os.path.exists(bin_path):
            os.remove(bin_path)
        if os.path.exists(fmwk_path):
            os.symlink(fmwk_path, bin_path)


def main(argv):
    if len(argv[1:]) != 1:
        sys.stderr.write("set-curr-python: error: incorrect number "
                         "of arguments\n\n")
        sys.stderr.write(__doc__)
        return 1
    set_curr_python(argv[1])
    return 0

if __name__ == "__main__":
    sys.exit( main(sys.argv) )
