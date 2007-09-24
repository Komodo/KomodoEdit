#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""XUL support for codeintel"""

import logging

from codeintel2.common import *
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin


#---- globals

lang = "XUL"
log = logging.getLogger("codeintel.xul")



#---- language support

class XULLexer(UDLLexer):
    lang = lang

class XULBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = "XUL"
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


class XULCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=XULLexer(),
                      buf_class=XULBuffer,
                      import_handler_class=None,
                      cile_driver_class=XULCILEDriver,
                      is_cpln_lang=True)

