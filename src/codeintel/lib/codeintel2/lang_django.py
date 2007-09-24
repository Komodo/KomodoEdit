#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Django support for codeintel"""

import logging

from codeintel2.common import *
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin

#---- globals

lang = "Django"
log = logging.getLogger("codeintel.django")



#---- language support

class DjangoLexer(UDLLexer):
    lang = lang

class DjangoBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    tpl_lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "Python"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    # - TODO: adjust for Python
    cpln_stop_chars = "'\" (;},~`!@#%^&*()-=+{}]|\\;,.<>?/"


class DjangoCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"
    tpl_lang = "Django"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=DjangoLexer(),
                      buf_class=DjangoBuffer,
                      import_handler_class=None,
                      cile_driver_class=DjangoCILEDriver,
                      is_cpln_lang=True)

