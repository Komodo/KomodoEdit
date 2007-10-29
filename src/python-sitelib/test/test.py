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

"""
    process.py Regression Test Suite Harness

    Usage:
        python test.py [<options>...] [<tests>...]

    Options:
        -x <testname>, --exclude=<testname>
                        Exclude the named test from the set of tests to be
                        run.  This can be used multiple times to specify
                        multiple exclusions.
        -v, --verbose   run tests in verbose mode with output to stdout
        -q, --quiet     don't print anything except if a test fails
        -h, --help      print this text and exit

    This will find all modules whose name is "test_*" in the test
    directory, and run them.  Various command line options provide
    additional facilities.

    If non-option arguments are present, they are names for tests to run.
    If no test names are given, all tests are run.

    Test Setup Options:
        -c, --clean     Don't setup, just clean up the test workspace.
        -n, --no-clean  Don't clean up after setting up and running the
                        test suite.
"""

import os
import sys
import getopt
import glob
import time
import types
import tempfile
import unittest

import testsupport


#---- exceptions

class TestError(Exception):
    pass


#---- globals

gVerbosity = 2


#---- utility routines

def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)


def _getAllTests(testDir):
    """Return a list of all tests to run."""
    testPyFiles = glob.glob(os.path.join(testDir, "test_*.py"))
    modules = [f[:-3] for f in testPyFiles if f and f.endswith(".py")]

    packages = []
    for f in glob.glob(os.path.join(testDir, "test_*")):
        if os.path.isdir(f) and "." not in f:
            if os.path.isfile(os.path.join(testDir, f, "__init__.py")):
                packages.append(f)

    return modules + packages


def _setUp():
    testsupport.setup()

def _tearDown():
    pass


def test(testModules, testDir=os.curdir, exclude=[]):
    """Run the given regression tests and report the results."""
    # Determine the test modules to run.
    if not testModules:
        testModules = _getAllTests(testDir)
    testModules = [t for t in testModules if t not in exclude]

    # Aggregate the TestSuite's from each module into one big one.
    allSuites = []
    for moduleFile in testModules:
        module = __import__(moduleFile, globals(), locals(), [])
        suite = getattr(module, "suite", None)
        if suite is not None:
            allSuites.append(suite())
        else:
            if gVerbosity >= 2:
                print "WARNING: module '%s' did not have a suite() method."\
                      % moduleFile
    suite = unittest.TestSuite(allSuites)

    # Run the suite.
    runner = unittest.TextTestRunner(sys.stdout, verbosity=gVerbosity)
    result = runner.run(suite)


#---- mainline

def main(argv):
    testDir = os.path.dirname(sys.argv[0])

    # parse options
    global gVerbosity
    try:
        opts, testModules = getopt.getopt(sys.argv[1:], 'hvqx:cn',
            ['help', 'verbose', 'quiet', 'exclude=',
             'clean', 'no-clean'])
    except getopt.error, ex:
        print "%s: ERROR: %s" % (argv[0], ex)
        print __doc__
        sys.exit(2)  
    exclude = []
    setupOpts = {}
    justClean = 0
    clean = 1
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        elif opt in ("-v", "--verbose"):
            gVerbosity += 1
        elif opt in ("-q", "--quiet"):
            gVerbosity -= 1
        elif opt in ("-x", "--exclude"):
            exclude.append(optarg)
        elif opt in ("-c", "--clean"):
            justClean = 1
        elif opt in ("-n", "--no-clean"):
            clean = 0

    retval = None
    if not justClean:
        _setUp(**setupOpts)
    try:
        if not justClean:
            retval = test(testModules, testDir=testDir, exclude=exclude)
    finally:
        if clean:
            _tearDown(**setupOpts)
    return retval

if __name__ == '__main__':
    sys.exit( main(sys.argv) )

