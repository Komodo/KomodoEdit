#!/usr/bin/env python
# Copyright (C) 2004-[[%date:%Y]] ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""[[%tabstop1:koFoo]] - [[%tabstop:...]]"""

import logging

from xpcom import components, COMException, ServerException, nsError

log = logging.getLogger("[[%tabstop1]]")


class [[%tabstop1]]:
    _com_interfaces_ = [components.interfaces.[[%tabstop:...]]]
    _reg_clsid_ = "{[[%guid]]}"
    _reg_contractid_ = "@activestate.com/[[%tabstop1]];1"
    _reg_desc_ = "..."


