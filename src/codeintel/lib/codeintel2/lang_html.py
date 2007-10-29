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

"""HTML support for CodeIntel"""

import os
import sys
import logging
import re
import traceback
from pprint import pprint

from codeintel2.common import *
from codeintel2.langintel import LangIntel
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin
from codeintel2.lang_xml import XMLLangIntel


try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

lang = "HTML"
log = logging.getLogger("codeintel.html")



#---- language support

class HTMLLexer(UDLLexer):
    lang = lang


class HTMLLangIntel(XMLLangIntel):
    lang = lang

class HTMLBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    m_lang = "HTML"
    csl_lang = "JavaScript"
    css_lang = "CSS"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    # - TODO: might want to drop '-' because causes problem with CSS and XML
    #   (ditto for other XML-y langs)
    cpln_stop_chars = "'\" (;},~`!@#%^&*()-=+{}]|\\;,.<>?/"



class HTMLCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"




#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=HTMLLexer(),
                      buf_class=HTMLBuffer,
                      langintel_class=HTMLLangIntel,
                      cile_driver_class=HTMLCILEDriver,
                      is_cpln_lang=True)

