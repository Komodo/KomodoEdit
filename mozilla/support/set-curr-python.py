#!/usr/bin/python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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
    
    for name in ("python", "pythonw", "python-config", "pydoc", "idle", "smtpd.py"):
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
