#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Mason support for codeintel"""

import logging

from codeintel2.common import *
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin

#---- globals

lang = "Mason"
log = logging.getLogger("codeintel.mason")



#---- language support

class MasonLexer(UDLLexer):
    lang = lang

class MasonBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    tpl_lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "Perl"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    #TODO: adjust for Perl, if necessary
    cpln_stop_chars = "'\" (;},~`!@#%^&*()-=+{}]|\\;,.<>?/"



class MasonCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"
    ssl_lang = "Perl"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=MasonLexer(),
                      buf_class=MasonBuffer,
                      import_handler_class=None,
                      cile_driver_class=MasonCILEDriver,
                      is_cpln_lang=True)

