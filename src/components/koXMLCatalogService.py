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

"""XMLCatalogService - ..."""

from xpcom import components, COMException, ServerException, nsError
from codeintel2.lang_xml import getService

class XMLCatalogService:
    _com_interfaces_ = [components.interfaces.koIXMLCatalogService]
    _reg_clsid_ = "{86d67309-70fe-11db-9e86-000d935d3368}"
    _reg_contractid_ = "@activestate.com/koXMLCatalogService;1"
    _reg_desc_ = "..."

    def __init__(self):
        self.datasethandler = getService()

    def getPublicIDList(self):
        publicid = []
        for c in self.datasethandler.resolver.catalogMap.values():
            publicid.extend(c.public.keys())
        publicid.sort()
        return publicid
    
    def getSystemIDList(self):
        sysid = []
        for c in self.datasethandler.resolver.catalogMap.values():
            sysid.extend(c.system.keys())
        sysid.sort()
        return sysid
    
    def getNamespaceList(self):
        return self.datasethandler.resolver.getWellKnownNamspaces().keys()
    
