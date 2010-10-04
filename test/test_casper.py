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

"""Integrate Komodo's Casper-based JavaScript test cases.

Casper 101
==========

You run a casper test module like this:
    komodo --raw -casper path\to\test_module.js
    
You can specify a particular test function:
    komodo --raw -casper path\to\test_module.js#testclass.testfunc

Logging output (in JSON format):
    komodo --raw -casper path\to\test_module.js#testclass.testfunc \
        -logfile path\to\log.json

Terminating Komodo when done testing:
    komodo --raw -casper path\to\test_module.js#testclass.testfunc \
        -logfile path\to\log.json -eot

Running multiple tests in one go:
    komodo --raw -casper path\to\test_module.js#testclass.testfunc \
        path\to\another\test_module.js#anothertestclass.anothertestfunc \
        -logfile path\to\log.json -eot


Integrating into PyUnit (aka unittest.py) and testlib.py
========================================================

"bk test" calls "test/test.py" which uses "testlib.py" to make using PyUnit
nicer. Testlib effectively loads this module, looks for test cases (TestCase
subclasses) and runs them. We use two testlib hooks to control things:

"test_cases()" is called to return TestCase classes to use. We find all
Komodo JS test modules and create a PyUnit TestCase class for each JSUnit
TestCase class (also populating with "test_*" functions as appropriate.
The "test_*" functions we add are just no-op stubs.

"test_suite_class" is used by testlib to group all tests from this module
under an instance of that class and use it to run the tests. We provide
a custom CasperTestSuite that knows how to run the selected tests with
casper (as described above), read the JSON log and fake out having run
the PyUnit tests.
"""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename, splitext, \
                    normpath
from glob import glob
import unittest
import subprocess
from pprint import pprint

sys.path.insert(0, join(dirname(dirname(abspath(__file__))),
                        "contrib", "simplejson"))
try:
    import simplejson
finally:
    del sys.path[0]

import which
from testlib import TestError, TestSkipped, TestFailed

import uriparse

    

class _CasperTestCase(unittest.TestCase):
    def _run_one_casper_test(self, test):
        #print "\n  %r" % test
        raise TestSkipped("cannot yet run casper tests")



#---- code for finding test cases in test_*.js files

class CasperTest(object):
    """Dumb object to hold info about a particular JS Casper-based
    test function.
    """
    def __init__(self, path, class_name, func_name, tags=None):
        self.path = path
        self.class_name = class_name
        self.func_name = func_name
        self.tags = tags
    def __repr__(self):
        tags_str = ""
        if self.tags:
            tags_str = " [%s]" % ' '.join(self.tags)
        return "<CasperTest %s#%s.%s%s>" \
               % (basename(self.path), self.class_name, self.func_name,
                  tags_str)

def testpaths():
    """Generate the potential JS test files."""
    komodo_src_dir = dirname(dirname(abspath(__file__)))
    komodo_chrome_dir = join(komodo_src_dir, "src", "chrome", "komodo",
                             "content")
    for path in _paths_from_path_patterns([komodo_chrome_dir],
                                          includes=["test_*.js"]):
        yield path

def is_casper_testcase_subclass(elem):
    # Limitation: Doesn't currently allow deep subclasses of the Casper
    # test case classes.
    if elem.get("ilk") != "class":
        return False
    casper_test_case_class_names = [
        "Casper.UnitTest.TestCase",
        "Casper.UnitTest.TestCaseAsync",
        "Casper.UnitTest.TestCaseSerialClass",
        "Casper.UnitTest.TestCaseSerialClassAsync",
    ]
    for classref in elem.get("classrefs", "").split():
        if classref in casper_test_case_class_names:
            return True
    return False

def casper_tests_from_citree(citree):
    import ciElementTree as ET
    from codeintel2.tree import pretty_tree_from_tree

    #citree = pretty_tree_from_tree(citree)
    #ET.dump(citree)
    for blob in citree[0]:
        #print "%(ilk)s %(name)s:" % blob.attrib
        for class_elem in blob:
            if not is_casper_testcase_subclass(class_elem):
                continue
            #print "  %(ilk)s %(name)s(%(classrefs)s):" % class_elem.attrib
            for func_elem in class_elem:
                if func_elem.get("ilk") != "function":
                    continue
                if not func_elem.get("name").startswith("test_"):
                    continue
                if '__ctor__' in func_elem.get("attributes", ''):
                    # This is class constructor, not an actual test.
                    continue
                #print "    %(ilk)s %(name)s" % func_elem.attrib
                
                raw_tags = func_elem.get("tags", "").strip()
                if raw_tags:
                    tags = re.split("[,\s]+", raw_tags)
                else:
                    tags = None
                yield CasperTest(normpath(blob.get("src")),
                                 class_elem.get("name"),
                                 func_elem.get("name"),
                                 tags)

def casper_tests():
    from codeintel2.manager import Manager

    db_base_dir = join(dirname(__file__), "tmp", "db")
    mgr = Manager(db_base_dir)
    mgr.upgrade()
    mgr.initialize()
    try:
        for testpath in testpaths():
            buf = mgr.buf_from_path(testpath, lang="JavaScript")
            # Ensure the test is up to date.
            if buf.scan_time < os.stat(testpath).st_mtime:
                buf.scan()
            for test in casper_tests_from_citree(buf.tree):
                yield test
    finally:
        mgr.finalize()



#---- internal support stuff

# Recipe: paths_from_path_patterns (0.3.6)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path


# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)



#---- hooks for testlib

def test_cases():
    # The current module (we're going to define class objects on it).
    mod_name = splitext(basename(__file__))[0]
    mod = sys.modules[mod_name]
    
    # Hackily get a handle on the "classobj" type so we can dynamically
    # create classes. Note that these are old-style Python classes
    # -- unittest.TestCase is still as old-style class in Python <=2.5.
    classobj = type(_CasperTestCase)
    
    # Create:
    test_class_from_name = {}
    for test in casper_tests():
        #print test
        path_tag = splitext(basename(test.path))[0][len("test_"):]
        if test.class_name not in test_class_from_name:
            # 1. A _CasperTestCase subclass for each found test class.
            klass = classobj(test.class_name, (_CasperTestCase,),
                             {"__tags__": [path_tag]})
            setattr(mod, test.class_name, klass)
            test_class_from_name[test.class_name] = klass
        klass = test_class_from_name[test.class_name]
        
        # 2. A no-op test_* function for each test.
        #    The test function's only purpose is to "be a test" from
        #    unittest.py's point of view. The real running on Casper tests
        #    is handled by the custom CasperTestSuite below.
        func = lambda self: True
        func._casper_test_ = test
        setattr(klass, test.func_name, func)
        if test.tags:
            func.tags = test.tags

    for klass in test_class_from_name.values():
        yield klass


class CasperTestSuite(unittest.TestSuite):
    """Special test suite that groups all casper tests for running.
    
    Running a casper test involves starting up and shutting down Komodo.
    With a lot of tests this would get ridiculously slow. Grouping them
    should limit to one Komodo startup/shutdown cycle.
    """
    def __init__(self, *args, **kwargs):
        super(CasperTestSuite, self).__init__(*args, **kwargs)
        self.log_path = abspath(join(dirname(__file__), "tmp", "casper.log"))
        self.teststorun_filepath = abspath(join(dirname(__file__), "tmp", "casper.params"))
    
    def run(self, result):
        if result.shouldStop:
            return result

        print "running casper tests in komodo ..."

        if exists(self.log_path):
            os.remove(self.log_path)
        if exists(self.teststorun_filepath):
            os.remove(self.teststorun_filepath)
        if not exists(dirname(self.log_path)):
            os.makedirs(dirname(self.log_path))

        # Determine the komodo/casper command line to run the desired
        # tests.
        casper_ids = []
        for testcase in self._tests:
            test = getattr(testcase, testcase._testMethodName)._casper_test_
            id = "%s#%s.%s" % (test.path, test.class_name, test.func_name)
            casper_ids.append(id)
            testcase._casper_id = id
        file(self.teststorun_filepath, "w").write("\n".join(casper_ids))
        argv = [which.which("komodo"), "--raw", "-casper",
                "-logfile", self.log_path,
                "-testsfile", self.teststorun_filepath]
        argv += ["-eot"]

        # Run the casper tests.
        p = subprocess.Popen(argv, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        output = p.stdout.read()
        status = p.wait()

        # Handle a possible hang in casper run.
        if not exists(self.log_path):
            # Running the casper tests failed. Probably just one of the
            # tests is to blame, but we have no way to know which.
            # TODO: Improve the casper logging story so we *can* determine
            #       which. Improve casper termination to not be able to
            #       get these hangs.
            for testcase in self._tests:
                result.startTest(testcase)
                result.addError(testcase, (TestError, "casper run hung or crashed", None))
                result.stopTest(testcase)
            return result

        # Gather the casper run results.
        try:
            casper_results = simplejson.loads(open(self.log_path, 'r').read())
        except ValueError, ex:
            for testcase in self._tests:
                result.startTest(testcase)
                detail = "Error in casper JSON log output (%s): %s" \
                         % (self.log_path, ex)
                result.addError(testcase, (TestError, detail, None))
                result.stopTest(testcase)
            return result            
        casper_result_from_id = {}
        for cr in casper_results:
            path = uriparse.URIToLocalPath(cr["url"])
            id = "%s#%s.%s" % (path, cr["testcase"], cr["testfunc"])
            casper_result_from_id[id] = cr

        # Fake having run the _CasperTestCase's, from unittest.py's p.o.v.
        for testcase in self._tests:
            try:
                cr = casper_result_from_id[testcase._casper_id]
            except KeyError, ex:
                # Casper can be flaky: not logging results for some tests
                # it was meant to run.
                status = "BREAK"
                detail = "Casper did not return any result for this test."
            else:
                status = cr["result"]
                detail = "%s\n%s" % (cr["message"], cr["detail"])

            result.startTest(testcase)
            if status == "PASS":
                result.addSuccess(testcase)
            elif status == "FAILURE":
                result.addFailure(testcase, (TestFailed, detail, None))
            elif status == "BREAK":
                result.addError(testcase, (TestError, detail, None))
            else:
                result.addError(testcase, (TestError, "Unknown casper status: %r" % (status, ), None))
            result.stopTest(testcase)


test_suite_class = CasperTestSuite
