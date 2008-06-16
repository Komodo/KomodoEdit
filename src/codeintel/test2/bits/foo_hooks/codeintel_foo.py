#!/usr/bin/env python
# Copyright (c) 2006-2008 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""A hook handler for testing. See test_hooks.py."""

import os
import sys
import logging
from pprint import pprint, pformat

from codeintel2.common import *
from codeintel2.hooks import HookHandler
import ciElementTree as ET

try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

log = logging.getLogger("codeintel.foo")
#log.setLevel(logging.DEBUG)




#---- main functionality

class FooHookHandler(HookHandler):
    name = "foo"
    langs = ["Python"]

    def post_db_load_blob(self, blob):
        # Add this to the module top-level:
        #   class Foo(object):
        #       def foo(self):
        #           pass
        foo_class = ET.SubElement(blob, "scope", ilk="class", name="Foo",
                               classrefs="object", line="0")
        foo_method = ET.SubElement(foo_class, "scope", ilk="function",
                                name="foo", signature="foo()", line="0")
        self_arg = ET.SubElement(foo_method, "variable", citdl="Foo",
                              ilk="argument", name="self")



#---- internal support stuff




#---- registration

def register(mgr):
    mgr.add_hook_handler(FooHookHandler(mgr))

