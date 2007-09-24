#!/usr/bin/env python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""[[%ask1:Component Name:koFoo]] - ..."""

import logging

from xpcom import components, COMException, ServerException, nsError

log = logging.getLogger("[[%ask1]]")


class [[%ask1]]:
    _com_interfaces_ = [components.interfaces....]
    _reg_clsid_ = "{[[%guid]]}"
    _reg_contractid_ = "@activestate.com/[[%ask1]];1"
    _reg_desc_ = "..."


