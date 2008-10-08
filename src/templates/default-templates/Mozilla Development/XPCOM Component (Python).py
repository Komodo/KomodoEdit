#!/usr/bin/env python
# Copyright (c) [[%date:%Y]] [[%tabstop1:MyCompany.com]]
# See the file LICENSE.txt for licensing information.

"""[[%tabstop2:MyPythonComponent]] - ..."""

from xpcom import components, COMException, ServerException, nsError

class [[%tabstop2]]:
    _com_interfaces_ = [components.interfaces.[[%tabstop:]]I[[%tabstop2]]]
    _reg_clsid_ = "{[[%guid]]}"
    _reg_contractid_ = "@[[%tabstop1]]/[[%tabstop2]];1"
    _reg_desc_ = "[[%tabstop:...]]"
