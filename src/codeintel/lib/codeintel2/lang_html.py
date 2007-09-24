#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

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

