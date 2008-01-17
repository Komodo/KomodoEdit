#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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

    type = None

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

    startIndex = None
    endIndex = None

class KoFindInFilesContext(KoFindContext):
    _com_interfaces_ = [components.interfaces.koIFindInFilesContext]
    _reg_desc_ = "Find In Files Context"
    _reg_clsid_ = "{11CDB7B7-24B4-4C5E-A1EA-8CE9A866536D}"
    _reg_contractid_ = "@activestate.com/koFindInFilesContext;1"

    cwd = None

