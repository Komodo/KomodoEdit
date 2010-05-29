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

    def diffURIs(self, left_uri, right_uri):
        left_koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                    createInstance(components.interfaces.koIFileEx)
        left_koFileEx.URI = left_uri
        left_content = ""
        if left_koFileEx.exists:
            left_koFileEx.open("rb")
            try:
                left_content = left_koFileEx.readfile()
            finally:
                left_koFileEx.close()

        right_koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                    createInstance(components.interfaces.koIFileEx)
        right_koFileEx.URI = right_uri
        right_content = ""
        if right_koFileEx.exists:
            right_koFileEx.open("rb")
            try:
                right_content = right_koFileEx.readfile()
            finally:
                right_koFileEx.close()

        return difflibex.diff_file_contents(left_content, right_content,
                                            left_koFileEx.path, right_koFileEx.path)

    def diffDirectories(self, left_dirpath, right_dirpath):
        return difflibex.diff_local_directories(left_dirpath, right_dirpath)

    def diffMultipleFilepaths(self, left_filepaths, right_filepaths):
        return difflibex.diff_multiple_local_filepaths(left_filepaths,
                                                       right_filepaths)

    def diffMultipleFilepathsOverridingDisplayPaths(self, left_filepaths,right_filepaths,
                                                    left_displaypaths, right_displaypaths):
        return difflibex.diff_multiple_local_filepaths(left_filepaths,
                                                       right_filepaths,
                                                       left_displaypaths,
                                                       right_displaypaths)

    def diffMultipleURIs(self, left_uris, right_uris):
        result = []
        for left_uri, right_uri in zip(left_uris, right_uris):
            result.append(self.diffURIs(left_uri, right_uri))
        return "".join(result)
