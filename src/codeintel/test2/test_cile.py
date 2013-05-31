#!/usr/bin/env python
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

"""Test scanning of scan_inputs/... with Code Intelligence Language Engines

This test suite scans each file in scan_inputs with the appropriate C.I.
Language Engine and compares the CIX results with the associated file in
scan_outputs. For example, if scan_inputs has a foo.py, then the Python
Language Engine will be used to scan it and the resulting CIX content will
be compared with scan_outputs/foo.py.cix. If it matches, then the test
passes.

XXX Talk about .options and .error mechanism, if necessary.

Adding a test case:
1. Add a file to be scanned to scan_inputs.
2. Add a file containing the expected CIX output as
   scan_outputs/<filename>.cix
Note: Plain-old line-by-line comparison is used, so even though inter-tag
whitespace is generally insigificant for XML data (i.e. CIX), testing will
consider it significant. That is generally okay, because a Language
Engine should not be randomly changing the whitespace that it spits out.
"""

import sys
import os
from os.path import join, dirname, splitext, basename, exists, isfile, \
                    abspath, normpath
import io
import re
import unittest
import difflib
import pprint
import shutil
import StringIO
import pprint
import warnings
import traceback

try:
    import cElementTree as ET # effbot's C module
except ImportError:
    import elementtree.ElementTree as ET # effbot's pure Python module

from citestsupport import CodeIntelTestCase
from testlib import TestSkipped

from codeintel2.tree import pretty_tree_from_tree, tree_from_cix
from codeintel2.util import indent, guess_lang_from_path, safe_lang_from_lang
from codeintel2.manager import Manager
from codeintel2.common import CodeIntelError



#---- globals

gInputsDir = join(dirname(__file__), "scan_inputs")
gOutputsDir = join(dirname(__file__), "scan_outputs")
gTmpDir = join(dirname(__file__), "scan_actual")

# For constraining diff output
gMaxDiffOutput = 10000
gMaxNumLines = 20
gMaxLineLength = 120


#----- test cases

class ScanInputsTestCase(CodeIntelTestCase):
    def setUp(self):
        CodeIntelTestCase.setUp(self)
        if not os.path.exists(gTmpDir):
            os.mkdir(gTmpDir)


def _diffContext(diff, n=3):
    """Filter the given difflib.ndiff lines to just have n lines of context.
    
    Note: This algorithm is not at all efficient.
    """
    nlines = len(diff)
    clines = set() # set of lines to include
    for i, line in enumerate(diff):
        if line[0] != ' ':
            clines |= set(range(max(0, i-n), min(i+n+1, nlines)))
    context = []
    clines = list(clines)
    clines.sort()
    last = -1
    for i in clines:
        if i != last+1:
            context.append("      ...\n")
        context.append(("%4d: "%i) + diff[i])
        last = i
    if clines[-1] != nlines-1:
        context.append("      ...\n")
    return context


def _testOneInputFile(self, fpath, tags=None):
    _debug = False  # Set to true to dump status info for each test run.

    infile = os.path.join(gInputsDir, fpath) # input
    outfile = os.path.join(gOutputsDir, fpath+'.cix') # expected output
    tmpfile = os.path.join(gTmpDir, fpath+'.cix') # actual output
    if not os.path.exists(os.path.dirname(tmpfile)):
        os.makedirs(os.path.dirname(tmpfile))
    errfile = os.path.join(gOutputsDir, fpath+'.error')  # expected error
    # An options file is a set of kwargs for the buf.scan()
    # method call. One key-value pair per-line like this:
    #   key=value
    # Whitespace is stripped off the value.
    optsfile = os.path.join(gInputsDir, fpath+'.options') # input options
    
    if _debug:
        print
        print "*"*50, "codeintel '%s'" % fpath

    # Set standard options:
    opts = {"mtime": "42"}

    # Determine input options to use, if any.
    #XXX Not used. Drop it.
    if os.path.exists(optsfile):
        for line in open(optsfile, 'r').read().splitlines(0):
            name, value = line.split('=', 1)
            value = value.strip()
            try: # allow value to be a type other than string
                value = eval(value)
            except Exception:
                pass
            opts[name] = value
        if _debug:
            print "*"*50, "options"
            pprint.pprint(opts)

    # Scan the file, capturing stdout and stderr and any possible
    # error.
    # - To allow testing from different dirs (resulting in changing
    #   path strings, we normalize the <file path="..."> value and any
    #   <scope ilk="blob" src="..."> attributes).
    oldStdout = sys.stdout
    oldStderr = sys.stderr
    sys.stdout = StringIO.StringIO()
    sys.stderr = StringIO.StringIO()
    try:
        try:
            lang = None
            if tags and "python3" in tags:
                lang = "Python3"
            buf = self.mgr.buf_from_path(infile, lang=lang)
            buf.scan(**opts)
            tree = buf.tree

            # Normalize paths.
            relnorm_infile = infile[len(dirname(gInputsDir))+1:]
            absnorm_infile = infile
            relnorm_infile = relnorm_infile.replace('\\', '/')
            absnorm_infile = absnorm_infile.replace('\\', '/')
            for file_elem in tree:
                file_elem.set("path", relnorm_infile)
                for blob_elem in file_elem:
                    if blob_elem.get("ilk") != "blob": continue
                    norm_src = normpath(blob_elem.get("src"))
                    norm_src = norm_src.replace('\\', '/')
                    if norm_src in (relnorm_infile, absnorm_infile):
                        blob_elem.set("src", relnorm_infile)

            tree = pretty_tree_from_tree(tree)
            # Due to the dynamic nature of the ciler errors (which often
            # includes the source code line numbers), it's difficult to check
            # that the errors are identical, so we work around this by just
            # taking the first 30 characters of the error.
            cile_error = tree[0].get("error")
            if cile_error and fpath.endswith(".js"):
                tree[0].set("error", len(cile_error) < 30 and cile_error or (cile_error[:30] + "..."))
            cix = ET.tostring(tree)

        except CodeIntelError, ex:
            error = traceback.format_exc()
        else:
            error = None
            if isinstance(cix, unicode):
                with io.open(tmpfile, mode="wt", encoding="utf-8") as fout:
                    fout.write(cix)
            else:
                with open(tmpfile, mode="wt") as fout:
                    fout.write(cix)
    finally:
        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
        sys.stdout = oldStdout
        sys.stderr = oldStderr
    if _debug:
        print "*"*50, "stdout"
        print stdout
        print "*"*50, "stderr"
        print stderr
        print "*"*50, "error"
        print str(error)
        print "*" * 50

    # Verify that the results are as expected.
    if os.path.exists(outfile) and error:
        self.fail("scanning '%s' raised an error but success was "
                  "expected:\n%s" % (_encode_for_stdout(fpath), indent(error)))
    elif os.path.exists(outfile):
        # Convert the <file path="..."/> to the native directory separator.
        def to_native_sep(match):
            path = match.group(2).replace("\\", os.sep).replace("/", os.sep)
            return match.group(1)+path+match.group(3)
        path_pat = re.compile(r'(<file .*?path=")(.*?)(".*?>)', re.S)

        # Note that we don't really care about line endings here, so we read
        # both files in universal newlines mode (i.e. translate to \n)
        with io.open(outfile, mode='rt', encoding='utf-8') as fout:
            expected = path_pat.sub(to_native_sep, fout.read())
        with io.open(tmpfile, mode='rt', encoding='utf-8') as ftmp:
            actual = path_pat.sub(to_native_sep, ftmp.read())
        
        if expected != actual:
            do_fail = True
            # Useful temporary thing while XML output format is changing.
            #if os.stat("../support/xmldiff.py"):
            #    rc = os.system('python ../support/xmldiff.py "%s" "%s"' % (outfile, tmpfile))
            #    if rc == 0:
            #        do_fail = False
            if do_fail:
                diff = list(difflib.ndiff(expected.splitlines(1),
                                          actual.splitlines(1)))
                diff = _diffContext(diff, 2)
                if diff:
                    error_str = "%r != %r:\n --- %s\n +++ %s\n%s" \
                                % (outfile, tmpfile, outfile, tmpfile,
                                   ''.join(diff))
                    if gMaxDiffOutput > 0 and gMaxNumLines > 0:
                        if len(error_str) > gMaxDiffOutput:
                            error_lines = error_str.split("\n")
                            if len(error_lines) > gMaxNumLines:
                                error_lines = error_lines[:gMaxNumLines] + ["..."]
                            if gMaxLineLength > 0:
                                error_str = "\n".join([len(x) > gMaxLineLength and x[:gMaxLineLength] or x
                                                   for x in error_lines])
                            else:
                                error_str = "\n".join(error_lines)
                    self.fail(_encode_for_stdout(error_str))
    elif os.path.exists(errfile):
        # There is no reference output file. This means that processing
        # this file is expected to fail.
        expectedError = open(errfile, 'r').read()
        actualError = str(error)
        self.failUnlessEqual(actualError.strip(), expectedError.strip())
    else:
        self.fail("No reference output file or error file for '%s'." % infile)

    # Ensure next test file gets a clean codeintel.
    toDelete = []
    for modname in sys.modules:
        if modname == "codeintel" or modname.startswith("codeintel."):
            toDelete.append(modname)
    for modname in toDelete:
        del sys.modules[modname]

def _fillScanInputsTestCase():
    for dpath, dnames, fnames in os.walk(gInputsDir):
        # Don't descend into SCC control dirs.
        scc_dirs = [".svn", "CVS", ".hg", ".git"]
        for scc_dir in scc_dirs:
            if scc_dir in dnames:
                dnames.remove(scc_dir)

        if dpath == gInputsDir and "unicode" in dnames:
            # The scan_inputs/unicode is where the unicode test files
            # are placed. Don't descend into here. They are handled elsewhere.
            dnames.remove("unicode")
        if ".svn" in dpath.split(os.sep):
            # Skip subversion directories.
            continue
        for fname in fnames:
            fpath = os.path.join(dpath, fname)[len(gInputsDir)+len(os.sep):]
            if not isfile(join(dpath, fname)):
                # With our Unicode testing we may have a directory that
                # Python's os.walk() doesn't recognize as a dir, defaults to
                # a file and hands it to us here. Skip those.
                continue
            if fname == ".DS_Store": continue
            if fpath.endswith(".swp"): continue
            if fpath.endswith("~"): continue
            if fpath.endswith("__pycache__"): continue
            if fpath.endswith(".pyc"): continue
            if fpath.endswith(".pyo"): continue
            if fpath.endswith(".pod"): continue
            if fpath.endswith(".options"): continue # skip input option files
            if fpath.endswith(".tags"): continue # skip tags files
            lang = guess_lang_from_path(fpath)
            # Manual hack to detect as Python 3.
            if lang == "Python" and "py3" in fpath:
                lang = "Python3"
            safe_lang = safe_lang_from_lang(lang)

            # Set tags for this test case.
            tags = [safe_lang]
            tagspath = join(dpath, fname + ".tags") # ws-separate set of tags
            if exists(tagspath):
                tags += open(tagspath, 'r').read().split()

            def makeTestFunction(fpath_, tags_):
                testFunction \
                    = lambda self, fpath=fpath_: _testOneInputFile(self, fpath_, tags=tags_)
                testFunction.tags = tags_
                return testFunction

            name = "test_path:"+fpath
            setattr(ScanInputsTestCase, name, makeTestFunction(fpath, tags))

    _addUnicodeScanInputTests()

def _addUnicodeScanInputTests():
    fs_encoding = sys.getfilesystemencoding().lower()
    unicode_markers = {
        "russian": u'\u043b\u0449', # 'ko' on russian keyboard
        "latin-1": u'k\xf2m\xf3d\xf4',
    }
    if fs_encoding not in ("mbcs", "utf-8"):
        unicode_marker = unicode_markers["latin-1"]
    else:
        unicode_marker = unicode_markers["russian"]
    
    # Generate some unicode (in file paths and content) tests for all
    # the CILEs.
    ext_from_lang = {
        "perl": ".pl", "python": ".py", "php": ".php", "tcl": ".tcl",
        "javascript": ".js", "ruby": ".rb",
    }
    content_and_cix_from_lang = {
        "perl": (
            r"sub foo { print 'hi\n'; }",
            u"""\
<codeintel version="2.0">
  <file lang="Perl" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.pl">
    <scope ilk="blob" lang="Perl" name="foo" src="scan_inputs/unicode/&#1083;&#1097;/foo.pl">
      <scope ilk="function" line="1" lineend="1" name="foo" signature="foo()" />
    </scope>
  </file>
</codeintel>
"""),
        "python": (
            r"def foo(): print 'hi'",
            u"""\
<codeintel version="2.0">
  <file lang="Python" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.py">
    <scope ilk="blob" lang="Python" name="foo" src="scan_inputs/unicode/&#1083;&#1097;/foo.py">
      <scope ilk="function" line="1" lineend="1" name="foo" signature="foo()" />
    </scope>
  </file>
</codeintel>
"""),
        "php": (
            r"<?php function foo() { echo 'hi\n'; } ?>",
            u"""\
<codeintel version="2.0">
  <file lang="PHP" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.php">
    <scope ilk="blob" lang="PHP" name="foo.php" src="scan_inputs/unicode/&#1083;&#1097;/foo.php">
      <scope ilk="function" line="1" lineend="1" name="foo" signature="foo()" />
    </scope>
  </file>
</codeintel>
"""),
        "ruby": (
            r"""
def foo
    puts 'hi\n'
end
""",
            u"""\
<codeintel version="2.0">
  <file lang="Ruby" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.rb">
    <scope ilk="blob" lang="Ruby" name="foo" src="scan_inputs/unicode/&#1083;&#1097;/foo.rb">
      <scope ilk="function" line="2" lineend="4" name="foo" signature="foo" />
    </scope>
  </file>
</codeintel>
"""),
        "tcl": (
            r'proc foo {} { puts "hi\n"; }',
            u"""\
<codeintel version="2.0">
  <file lang="Tcl" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.tcl">
    <scope ilk="blob" lang="Tcl" name="foo" src="scan_inputs/unicode/&#1083;&#1097;/foo.tcl">
      <scope ilk="function" line="1" lineend="1" name="foo" signature="foo {}" />
    </scope>
  </file>
</codeintel>
"""),
        "javascript": (
            r"function foo { dump('hi\n'); }",
            u"""\
<codeintel version="2.0">
  <file lang="JavaScript" mtime="42" path="scan_inputs/unicode/&#1083;&#1097;/foo.js">
    <scope ilk="blob" lang="JavaScript" name="foo.js" src="scan_inputs/unicode/&#1083;&#1097;/foo.js">
      <scope ilk="function" line="1" lineend="1" name="foo" signature="foo()" />
    </scope>
  </file>
</codeintel>
"""),
    }
    
    u_inputs_dir = join(gInputsDir, "unicode", unicode_marker)
    u_outputs_dir = join(gOutputsDir, "unicode", unicode_marker)
    for d in (u_inputs_dir, u_outputs_dir):
        if not exists(d):
            os.makedirs(d)
    for lang in ["perl", "python", "php", "tcl", "javascript", "ruby"]:
        ext = ext_from_lang[lang]
        inpath = join(u_inputs_dir, "foo"+ext)
        outpath = join(u_outputs_dir, "foo"+ext+".cix")

        # Unicode chars in the file path.
        content, cix = content_and_cix_from_lang[lang]
        open(inpath, 'wt').write(content)
        with io.open(outpath, mode="wt", encoding="utf-8") as fout:
            fout.write(cix)

        subpath = join("unicode", unicode_marker, basename(inpath))
        testFunction \
            = lambda self, subpath=subpath: _testOneInputFile(self, subpath)
        testFunction.tags = ["unicode", lang]
        name = "test_path:"+subpath.encode('ascii', 'backslashreplace')
        setattr(ScanInputsTestCase, name, testFunction)

def _encode_for_stdout(s):
    if sys.stdout.encoding:
        return s.encode(sys.stdout.encoding, 'backslashreplace')
    else:
        # This is the case when the normal sys.stdout has been
        # replaced by something else, such as a Python file object.
        return s.encode('ascii', 'backslashreplace')


#---- mainline

def test_cases():
    _fillScanInputsTestCase()
    yield ScanInputsTestCase


if __name__ == "__main__":
    unittest.main()

