#!/usr/bin/env python
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

import os
import sys
import urlparse
from xpcom import components
import logging


log = logging.getLogger("koUrlUtils")


# 2009-02-03: No Komodo core code is currently using this class.
class koUrlUtils:
    _com_interfaces_ = [components.interfaces.koIUrlUtils]
    _reg_clsid_ = "{0f5df15b-88fd-4b3e-b8cc-e8f001d845fd}"
    _reg_contractid_ = "@activestate.com/koUrlUtils;1"
    _reg_desc_ = "Dumping ground for URL-related utility functions"
            
    if sys.platform == "win32":
        def _fixPath(self, url):
            path = urlparse.urlparse(url)[2]
            # URLs come from different sources, and sometimes use "|" instead of ":"
            # Also Python's urlparse.urlparse puts a '/' at the start of paths,
            # for URIs that start with the correct "file:///C:...",
            # and behave correctly for two-slashes ("file://C:...")
            if len(path) > 3 and path[0] == '/' and path[2] in ":|":
                # e.g. map "/C|" to "C:"
                # Assume path[1] is a letter
                path = path[1] + ":" + path[3:]
            return os.path.normpath(os.path.normcase(path))
    else:
        def _fixPath(self, url):
            # No need to normcase OSX paths,
            # because os.path.samefile will correctly ignore case.
            return os.path.normpath(urlparse.urlparse(url)[2])

    def sameURL(self, url1, url2):
        if url1 and url2 and url1.startswith('file:///') and url2.startswith('file:///'):
            path1 = self._fixPath(url1)
            path2 = self._fixPath(url2)
            
            if sys.platform.startswith("win"):
                return path1 == path2            
            else:
                try:
                    return os.path.samefile(path1, path2)
                except Exception, e:
                    log.debug("Could not compare files: %r [%r]", e, e.args)
                    return path1 == path2
        else:
            return url1 == url2
