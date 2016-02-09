#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""AngularJS support for CodeIntel"""

import logging

from codeintel2.common import _xpcom_
from codeintel2.lang_html5 import HTML5Lexer, HTML5LangIntel, HTML5Buffer, HTML5CILEDriver

if _xpcom_:
    from xpcom.server import UnwrapObject


#---- globals

lang = "AngularJS"
log = logging.getLogger("codeintel.angularjs")
#log.setLevel(logging.DEBUG)


#---- language support

class AngularJSLexer(HTML5Lexer):
    lang = "AngularJS"

class AngularJSLangIntel(HTML5LangIntel):
    lang = lang

class AngularJSBuffer(HTML5Buffer):
    lang = lang

class AngularJSCILEDriver(HTML5CILEDriver):
    lang = lang


#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=AngularJSLexer(),
                      buf_class=AngularJSBuffer,
                      langintel_class=AngularJSLangIntel,
                      cile_driver_class=AngularJSCILEDriver,
                      is_cpln_lang=True)

