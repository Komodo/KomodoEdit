#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""XML support for CodeIntel"""

import logging
from codeintel2.common import *
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin

#---- globals

lang = "XSLT"
log = logging.getLogger("codeintel.xslt")

class XSLTLexer(UDLLexer):
    lang = lang

class XSLTBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    m_lang = "XML"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    cpln_stop_chars = ">'\" "



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=XSLTLexer(),
                      buf_class=XSLTBuffer,
                      import_handler_class=None,
                      cile_driver_class=None,
                      is_cpln_lang=True)

