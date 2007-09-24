#!/usr/bin/env python
# Copyright (c) 2001-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import sys
import urlparse
from xpcom import components
import logging


log = logging.getLogger("koUrlUtils")


class koUrlUtils:
    _com_interfaces_ = [components.interfaces.koIUrlUtils]
    _reg_clsid_ = "{0f5df15b-88fd-4b3e-b8cc-e8f001d845fd}"
    _reg_contractid_ = "@activestate.com/koUrlUtils;1"
    _reg_desc_ = "Dumping ground for URL-related utility functions"

    def sameURL(self, url1, url2):
        if url1 and url2 and url1.startswith('file:///') and url2.startswith('file:///'):
            path1 = os.path.normpath(os.path.normcase(urlparse.urlparse(url1)[2]))
            path2 = os.path.normpath(os.path.normcase(urlparse.urlparse(url2)[2]))

            if sys.platform.startswith("win"):
                return path1 == path2            
            else:
                try:
                    return os.path.samefile(path1, path2)
                except Exception, e:
                    log.debug("Could not compare files: %r [%r]", e, e.args)
                    return path1 == path2
        else:
            return url1 == url2
