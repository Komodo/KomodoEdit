#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.

"""RHTML support for CodeIntel"""

import os
from os.path import (isfile, isdir, exists, dirname, abspath, splitext,
                     join, basename)
import sys
from cStringIO import StringIO
import logging
import re
import traceback
from pprint import pprint
from glob import glob

from codeintel2.common import *
from codeintel2.lang_ruby_common import RubyCommonBufferMixin
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin
from codeintel2.citadel import CitadelEvaluator



#---- globals

lang = "RHTML"
log = logging.getLogger("codeintel.rhtml")
#log.setLevel(logging.DEBUG)

#---- language support

class RHTMLLexer(UDLLexer):
    lang = lang
    

# Dev Notes:
# - DO_NOT_PUT_IN_FILLUPS = '!'
# - curr_calltip_arg_range (will need to pass in trigger when get to
#    this point)
class RHTMLBuffer(UDLBuffer, XMLParsingBufferMixin, RubyCommonBufferMixin):
    def __init__(self, mgr, accessor, env=None, path=None):
        UDLBuffer.__init__(self, mgr, accessor, env, path)
        self.check_for_rails_app_path(path)
        
    lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "Ruby"
    tpl_lang = "RHTML"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    # - TODO: adjust for Ruby, if necessary
    # - TODO: adjust for RHTML, if necessary
    cpln_stop_chars = "'\" (;},~`!@#%^&*()-=+{}]|\\;,.<>?/"
    

class RHTMLCILEDriver(UDLCILEDriver):
    lang = lang
    ssl_lang = "Ruby"
    csl_lang = "JavaScript"



#---- internal support stuff

def _isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def _isdigit(char):
    return "0" <= char <= "9"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=RHTMLLexer(),
                      buf_class=RHTMLBuffer,
                      cile_driver_class=RHTMLCILEDriver,
                      is_cpln_lang=True)

