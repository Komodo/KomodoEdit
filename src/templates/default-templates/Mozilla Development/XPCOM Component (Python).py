#!/usr/bin/env python
# Copyright (c) 2006 [[%ask2:Domain Name:MyCompany.com]]
# See the file LICENSE.txt for licensing information.

"""[[%ask1:Component Name:MyPythonComponent]] - ..."""

from xpcom import components, COMException, ServerException, nsError

class [[%ask1]]:
    _com_interfaces_ = [components.interfaces.i[[%ask1]]]
    _reg_clsid_ = "{[[%guid]]}"
    _reg_contractid_ = "@[[%ask2]]/[[%ask1]];1"
    _reg_desc_ = "..."


