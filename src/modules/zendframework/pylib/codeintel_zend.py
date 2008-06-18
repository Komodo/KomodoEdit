#!/usr/bin/env python
# Copyright (c) 2006-2008 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""A hook handler for supporting Zend Framework."""

import os
import sys
import logging

from codeintel2.common import *
from codeintel2.hooks import HookHandler
import ciElementTree as ET

try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

log = logging.getLogger("codeintel.Zend")
#log.setLevel(logging.DEBUG)




#---- main functionality

class ZendFrameworkHookHandler(HookHandler):
    name = "ZendFramework"
    langs = ["PHP"]

    def post_db_load_blob(self, blob):
        filepath = blob.get("src", "")
        if filepath.endswith(".phtml") and filepath.find("/views/scripts/") > 0:
            # Wrap the blob data in an implicit Zend view:
            #   class implicit_zend_view extends Zend_View {
            #     function implicit_render() {
            #       ... data ...
            #     }
            #   }
            child_nodes = blob.getchildren()
            implicit_view_class = ET.SubElement(blob, "scope", ilk="class",
                                                name="(Zend_View)",
                                                classrefs="Zend_View",
                                                attributes="__fabricated__ __hidden__",
                                                line="0")
            view_method = ET.SubElement(implicit_view_class, "scope",
                                        ilk="function",
                                        name="(render)",
                                        signature="",
                                        attributes="__fabricated__ __hidden__",
                                        line="0")
            for child in child_nodes:
                blob.remove(child)
                view_method.append(child)



#---- internal support stuff




#---- registration

def register(mgr):
    mgr.add_hook_handler(ZendFrameworkHookHandler(mgr))

