#!python
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

"""Compile the given Python script and gather and print error/warning data.

Usage:
    python pycompile.py <filename>

Output on stdout is a prettily formatted list of Python dicts, one dict for
each syntax error and tabnanny warning. For example:
    [{'description': 'exceptions.SyntaxError: invalid syntax',
      'filename': 't.py',
      'lineno': 9,
      'offset': 6,   # may be None if not known (e.g. tabnanny warnings)
      'severity': 'ERROR',
      'text': 'foo =\n'}]

Output on stderr include warnings from the warnings framework:
    t.py:7: SyntaxWarning: import * only allowed at module level
      def foo():

Dev Notes:
- This script should work with Python >= 1.5.2, <= 3.0. We use the 2to3
  converter to make a version of this script for Python >=3.0.
"""

import sys
import re
import pprint
import __builtin__


class PyCompileError(Exception):
    pass


#---- internal support routines

def _splitlines(s, keepends=0):
    r"""Python 2.2's .splitlines() string method for Python >= 1.5.2.
        >>> _splitlines("a\nb\n\nc", 1)
        ['a\n', 'b\n', '\n', 'c']
        >>> _splitlines("a\nb\n\nc")
        ['a', 'b', '', 'c']
        >>> _splitlines('a\r\nb\nc', 1)
        ['a\r\n', 'b\n', 'c']
    """
    # Implementation notes:
    #    I am copying Python 2.2's splitlines algorithm. I am sure there
    #    is an easier way.
    lines = []

    i = j = 0 # line delimiters
    length = len(s)
    while i < length:
        # move i to end of line
        while i < length and s[i] != '\n' and s[i] != '\r':
            i = i + 1
        # handle EOL
        eol = i
        if i < length:
            if s[i] == '\r' and i+i < length and s[i+1] == '\n':
                i = i + 2
            else:
                i = i + 1
            if keepends:
                eol = i
        # append new line segment and move on to next
        lines.append( s[j:eol] )
        j = i
    if j < length:
        lines.append( s[j:length] )
    return lines



#---- mainline

def main(argv):
    if len(argv[1:]) != 1:
        raise PyCompileError("Incorrect number of arguments: %r" % argv[1:])

    # Read in the file contents.
    filename = argv[1]
    fin = open(filename, 'r')
    s = fin.read()
    fin.close()

    # Get around a bug in python's compile() code on Unix that does not
    # like lines ending in CRLF.
    if not sys.platform[:3] == "win":
        s = s.replace('\r\n', '\n')

    # Get around bug in python's compile() code that requires terminal newlines
    s = s + '\n' 

    results = []

    # Run tabnanny on it if available.
    try:
        import tabnanny
    except ImportError:
        pass
    else:
        import StringIO
        o = StringIO.StringIO()
        oldStdout = sys.stdout
        sys.stdout = o
        try:
            tabnanny.check(filename)
        except IndentationError, e:
            pass # ignore these, we'll catch them later
        sys.stdout = oldStdout
        lineRe = re.compile("^(?P<fname>.*?) (?P<line>\d+) '(?P<content>.*)'$")
        for line in _splitlines(o.getvalue()):
            match = lineRe.match(line)
            if match:
                r = {}
                r["filename"] = filename
                r["description"] = "Ambiguous indentation (mixed tabs and spaces?)"
                r["lineno"] = int(match.group("line"))
                r["offset"] = None
                r["severity"] = "WARNING"
                r["text"] = match.group("content")
                results.append(r)
            else:
                errmsg = "Warning: could not parse tabnanny "\
                         "output line: %r\n" % line
                #XXX Silently drop it for now because stderr is used for
                #    data as well.

    # Compile it.
    try:
        dummy = __builtin__.compile(s, filename, 'exec')
    except SyntaxError, ex:
        r = {}
        r["filename"] = filename
        # Prefix the description with the name of the exception class.
        # This is what Python does when it prints tracebacks.
        eClassName = ex.__class__.__name__
        r["description"] = "%s: %s" % (eClassName, ex.msg)
        r["lineno"] = ex.lineno
        # ex.offset is sometime unreliable. For example ex.offset for the
        # syntax error in this code:
        #      foo = """
        #      line1
        #      line2
        # is 21. Looking at ex.text shows us the problem:
        #      'foo = """\012line1\012line2'
        # We need to recalculate the offset if there are newlines in ex.text.
        if '\n' in ex.text:
            lines = _splitlines(ex.text, 1)
            for line in lines[:-1]:
                ex.offset = ex.offset - len(line)
            ex.text = lines[-1]
        r["offset"] = ex.offset
        try:
            if isinstance(ex, TabError):
                r["severity"] = "WARNING"
            else:
                r["severity"] = "ERROR"
        except NameError:
            # Python 1.5.2 doesn't have TabError
            r["severity"] = "ERROR"
        r["text"] = ex.text
        results.append(r)

    # Print the results.
    pprint.pprint(results)
    

if __name__ == "__main__":
    sys.exit( main(sys.argv) )

