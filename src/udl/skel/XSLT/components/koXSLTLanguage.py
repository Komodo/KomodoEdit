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

from xpcom import components
from koLanguageServiceBase import *
from koXMLLanguageBase import koXMLLanguageBase, KoGenericXMLLinter

import os
import logging

log = logging.getLogger("koXSLTLanguage")

def registerLanguage(registery):
    registery.registerLanguage(koXSLTLanguage())
    
class koXSLTLanguage(koXMLLanguageBase):
    name = "XSLT"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7F76A3CE-7FE1-4363-99EB-4AAAFA79BC88}"
    _reg_categories_ = [("komodo-language", name)]

    lexresLangName = name
    lang_from_udl_family = {'M': 'XML'}

    accessKey = 's'
    primary = 0
    defaultExtension = ".xsl"

    systemIdList = ["http://www.w3.org/1999/XSL/Transform"]
    namespaces = ["http://www.w3.org/1999/XSL/Transform"]
    
    namedBlockRE = r'(\<xsl:template.*?\>)'
    namedBlockDescription = 'XSL Templates'

    sample = """<?xml version="1.0"?> 

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="xml" indent="yes"/>

<!-- Syntax Coloring:
    Komodo detects keywords and applies syntax coloring.  In the code
    below, note how "template" is a different color from "match",
    which is a different color from ""Class"". -->

<xsl:template match="Class">
    <html>
            <xsl:apply-templates select="Order"/>
    </html>
</xsl:template>

"""


class KoXSLTCompileLinter(KoGenericXMLLinter):
    _reg_desc_ = "Komodo XSLT Compile Linter"
    _reg_clsid_ = "{390b2ce2-9df8-41a7-8e35-d2a4d76618d6}"
    _reg_contractid_ = "@activestate.com/koLinter?language=XSLT;1"
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_categories_ = [
         ("category-komodo-linter", 'XSLT'),
         ]
