#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""XBL support for codeintel"""

import logging

from codeintel2.common import *
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin



#---- globals

lang = "XBL"
log = logging.getLogger("codeintel.xbl")



#---- language support

class XBLLexer(UDLLexer):
    lang = lang

class XBLBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    m_lang = "XML"
    css_lang = "CSS"
    csl_lang = "JavaScript"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    cpln_stop_chars = "'\" (;},~`!@#%^&*()-=+{}]|\\;,.<>?/"


#class XBLCILEDriver(UDLCILEDriver):
#    lang = lang
#    csl_lang = "JavaScript"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=XBLLexer(),
                      buf_class=XBLBuffer,
                      import_handler_class=None,
                      cile_driver_class=None,
                      is_cpln_lang=True)

