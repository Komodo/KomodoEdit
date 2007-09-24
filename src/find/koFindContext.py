#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Implement the Komodo Find Context hierarchy.

from xpcom import components, ServerException, nsError
import sys, os, re, types


#---- globals

# context types
FCT_CURRENT_DOC = components.interfaces.koIFindContext.FCT_CURRENT_DOC
FCT_SELECTION = components.interfaces.koIFindContext.FCT_SELECTION
FCT_ALL_OPEN_DOCS = components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS
FCT_IN_FILES = components.interfaces.koIFindContext.FCT_IN_FILES

_names = {
    FCT_CURRENT_DOC: "the current document",
    FCT_SELECTION: "the selection",
    FCT_ALL_OPEN_DOCS: "all open documents",
    FCT_IN_FILES: "files",
}



class KoFindContext:
    _com_interfaces_ = [components.interfaces.koIFindContext]
    _reg_desc_ = "Find Context"
    _reg_clsid_ = "{D6C80051-0A3D-46bc-80E3-DA4413D83EFB}"
    _reg_contractid_ = "@activestate.com/koFindContext;1"

    def get_name(self):
        try:
            return _names[self.type]
        except (AttributeError, KeyError):
            raise ServerException, nsError.NS_ERROR_NOT_INITIALIZED


class KoRangeFindContext(KoFindContext):
    _com_interfaces_ = [components.interfaces.koIRangeFindContext]
    _reg_desc_ = "Range Find Context"
    _reg_clsid_ = "{EE524C16-BB91-43ec-B213-C7FE5697876A}"
    _reg_contractid_ = "@activestate.com/koRangeFindContext;1"


class KoFindInFilesContext(KoFindContext):
    _com_interfaces_ = [components.interfaces.koIFindInFilesContext]
    _reg_desc_ = "Find In Files Context"
    _reg_clsid_ = "{11CDB7B7-24B4-4C5E-A1EA-8CE9A866536D}"
    _reg_contractid_ = "@activestate.com/koFindInFilesContext;1"


