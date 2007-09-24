#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.

"""The codeintel test suite entry point."""

import os
from os.path import exists
import sys
import logging

import testlib
import citestsupport


log = logging.getLogger("test")

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
    retval = testlib.harness(setup_func=setup)
    sys.exit(retval)

