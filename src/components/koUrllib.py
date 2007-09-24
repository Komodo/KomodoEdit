#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""
Exposes some of Python's urllib module to other languages.
"""

import urllib
from xpcom import components

class koUrllib:
    _com_interfaces_ = [components.interfaces.koIUrllib]
    _reg_clsid_ = "{31f8c3d6-a751-49dd-a0c7-fd4b36bf06f6}"
    _reg_contractid_ = "@activestate.com/koUrllib;1"
    _reg_desc_ = "Makes urlib routines available outside of Python"

    def quote(self, path, safe):
        return urllib.quote(path, safe)

    def unquote(self, path):
        return urllib.unquote(path)
