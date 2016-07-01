#!/usr/bin/env python
# Copyright (c) 2015 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""Handlebars support for codeintel"""

import logging

from codeintel2.common import *
from codeintel2.langintel import LangIntel
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin

if _xpcom_:
    from xpcom.server import UnwrapObject

#---- globals

lang = "Handlebars"
log = logging.getLogger("codeintel.handlebars")


#---- language support

class HandlebarsLexer(UDLLexer):
    lang = lang

class HandlebarsBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    tpl_lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    # - dropping '-' because causes problem with CSS (bug 78312)
    # - dropping '!' because causes problem with CSS "!important" (bug 78312)
    cpln_stop_chars = "'\" (;},~`@#%^&*()=+{}]|\\;,.<>?/"


class HandlebarsLangIntel(LangIntel):
    lang = lang
    
    def trg_from_pos(self, buf, pos, implicit=True, DEBUG=False):
        return None

class HandlebarsCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"
    tpl_lang = lang
    css_lang = "CSS"

#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=HandlebarsLexer(),
                      buf_class=HandlebarsBuffer,
                      langintel_class=HandlebarsLangIntel,
                      import_handler_class=None,
                      cile_driver_class=HandlebarsCILEDriver,
                      is_cpln_lang=True)
