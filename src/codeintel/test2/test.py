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

"""The codeintel test suite entry point."""

import os
from os.path import exists
import sys
import logging

import testlib
import citestsupport
import clean_tests


log = logging.getLogger("test")

default_tags = ["-knownfailure", "-xpcom"]

def _skip_setup():
    TEST_SKIP_SETUP = os.environ.get("TEST_SKIP_SETUP", "0")
    return TEST_SKIP_SETUP not in ('0', '')

def setup():
    if _skip_setup():
        log.debug("skipping test setup ($TEST_SKIP_SETUP is true)")
    elif exists(citestsupport.test_db_base_dir):
        log.debug("rm `%s'", citestsupport.test_db_base_dir)
        citestsupport.rmtree(citestsupport.test_db_base_dir)

if __name__ == "__main__":
    try:
        retval = testlib.harness(setup_func=setup,
                                 default_tags=default_tags)
        sys.exit(retval)
    finally:
        # Remove the special unicode files added by the codeintel system,
        # otherwise buildbot and/or Python utilities may break when trying to
        # remove these files.
        clean_tests.do_clean_unicode_directories()

