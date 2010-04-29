#!python
# Copyright (c) 2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# A service that provides file diffing facilities. Mostly a wrapper around
# certain parts of the python difflibex module.

import os
import sys
import logging

from xpcom import components

import difflibex

#log = logging.getLogger("koDiffService")


#---- component implementation

class KoDiffService(object):
    _com_interfaces_ = [components.interfaces.koIDiffService]
    _reg_clsid_ = "{d968bb67-1d39-4e8e-861c-6d4b2b1f0153}"
    _reg_contractid_ = "@activestate.com/koDiffService;1"
    _reg_desc_ = "Komodo Diff Service"

    def diffFilepaths(self, left_filepath, right_filepath):
        return difflibex.diff_multiple_local_filepaths([left_filepath],
                                                       [right_filepath])

    def diffDirectories(self, left_dirpath, right_dirpath):
        return difflibex.diff_local_directories(left_dirpath, right_dirpath)

    def diffMultipleFilepaths(self, left_filepaths, right_filepaths):
        return difflibex.diff_multiple_local_filepaths(left_filepaths,
                                                       right_filepaths)
