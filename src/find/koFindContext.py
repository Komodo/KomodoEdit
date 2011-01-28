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

"""Komodo find contexts (i.e. in what to search)"""

from os.path import basename
import logging

from xpcom import components, ServerException, nsError
from xpcom.server import UnwrapObject
import uriparse



#---- globals

log = logging.getLogger("find")

# context types
FCT_CURRENT_DOC = components.interfaces.koIFindContext.FCT_CURRENT_DOC
FCT_SELECTION = components.interfaces.koIFindContext.FCT_SELECTION
FCT_ALL_OPEN_DOCS = components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS
FCT_IN_FILES = components.interfaces.koIFindContext.FCT_IN_FILES
FCT_IN_COLLECTION = components.interfaces.koIFindContext.FCT_IN_COLLECTION

_names = {
    FCT_CURRENT_DOC: "the current document",
    FCT_SELECTION: "the selection",
    FCT_ALL_OPEN_DOCS: "all open documents",
    FCT_IN_FILES: "files",
    FCT_IN_COLLECTION: "collection",
}



class KoFindContext(object):
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


class KoCollectionFindContext(KoFindContext):
    _com_interfaces_ = [components.interfaces.koICollectionFindContext]
    _reg_desc_ = "Find In Collection Context"
    _reg_clsid_ = "{d4ad4818-2ea0-4512-99b8-7581bdccbfe6}"
    _reg_contractid_ = "@activestate.com/koCollectionFindContext;1"

    def __init__(self):
        self.type = FCT_IN_COLLECTION
        self.items = []

    @property
    def desc(self):
        bits = []
        for type, item in self.items:
            if type == "path":
                bits.append(basename(item))
            elif type == "file":
                bits.append(basename(item.url))
            elif type == "container":
                part_type = item.type
                if part_type == "project":
                    bits.append(basename(item.url))
                elif part_type == "folder":
                    bits.append(item.getStringAttribute("name"))
                elif part_type == "livefolder":
                    bits.append(basename(item.liveDirectory))
                else:
                    log.warn("unexpected container koIPart type: %r",
                             part_type)
        return ", ".join(bits)
    
    def add_koIContainer(self, container):
        self.items.append(("container", container))
    def add_file(self, file):
        self.items.append(("file", file))
    def add_path(self, path):
        self.items.append(("path", path))

    @property
    def paths(self):
        """Generate all paths for this collection."""
        for type, item in self.items:
            if type == "path":
                yield item
            elif type == "file":
                path = _local_path_from_url(item.url)
                if path is not None:
                    yield path
            elif type == "container":
                container = UnwrapObject(item)
                for path in container.genLocalPaths():
                    yield path                


#---- internal support stuff

def _local_path_from_url(url):
    try:
        #TODO: The docs for URIToLocalPath say an UNC ends up as a file://
        #      URL, which is not the case. Fix those docs.
        return uriparse.URIToLocalPath(url)
    except ValueError:
        # The url isn't a local path.
        return None