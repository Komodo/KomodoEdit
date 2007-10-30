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

"""Analyze the logs from a "rrun.py kodev-test" run."""

import sys
from os.path import *
from pprint import pprint
from glob import glob
import operator



class Error(Exception):
    pass



#---- public stuff

def analyze_test_logs():
    log_dir = join(dirname(dirname(abspath(__file__))), "log")
    
    results = []
    for log_path in glob(join(log_dir, "kodev-test-*.log")):
        results.append(PlatResults(log_path))
    if not results:
        raise Error("no log files found")
    
    retval = 0
    for result in results:
        retval += len(result.errors)
        retval += len(result.failures)
    
    if retval == 0:
        print "OK"
    else:
        error_in_all = []
        for error in results[0].errors:
            for result in results[1:]:
                if error not in result.errors:
                    break
            else:
                error_in_all.append(error)
        failure_in_all = []
        for failure in results[0].failures:
            for result in results[1:]:
                if failure not in result.failures:
                    break
            else:
                failure_in_all.append(failure)
        if error_in_all or failure_in_all:
            print "all platforms:"
            for error in error_in_all:
                print "  [ERROR] "+error
            for failure in failure_in_all:
                print "  [ FAIL] "+failure
        for result in sorted(results, key=operator.attrgetter("platname"),
                             reverse=True):
            errors = [e for e in result.errors if e not in error_in_all]
            failures = [e for e in result.failures if e not in failure_in_all]
            if not errors and not failures:
                continue
            print "%s (%s):" % (result.platname, result.hostname)
            for error in errors:
                print "  [ERROR] "+error
            for failure in failures:
                print "  [ FAIL] "+failure

    return retval


#---- internal support stuff


class PlatResults(object):
    def __init__(self, log_path):
        self.log_path = log_path
        self.hostname = splitext(basename(log_path))[0].split('-')[-1]
        self.platname = _platname_from_hostname(self.hostname)
        self.errors = []
        self.failures = []
        self._analyze()

    def _analyze(self):
        lines = open(self.log_path, 'r').readlines()
        prev_line = None
        for line in lines:
            if line.startswith("ERROR:") and prev_line and prev_line.startswith("="):
                self.errors.append(line[len("ERROR:"):].strip())
            elif line.startswith("FAIL:") and prev_line and prev_line.startswith("="):
                self.failures.append(line[len("FAIL:"):].strip())
            prev_line = line

def _platname_from_hostname(hostname):
    return {
        "belt": "win32-x86",
        "anole": "macosx-x86",
        "gila": "linux-libcpp5-x86",
        "skink": "linux-libcpp6-x86",
        "sphinx": "macosx-powerpc",
    }[hostname]



#---- mainline

if __name__ == "__main__":
    retval = analyze_test_logs()
    sys.exit(retval)