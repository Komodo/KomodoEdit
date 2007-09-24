#!/usr/bin/env python
# Copyright (c) 2006 activestate.com
# See the file LICENSE.txt for licensing information.

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
    
