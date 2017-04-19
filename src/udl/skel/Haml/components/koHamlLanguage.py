#!/usr/bin/env python
# Copyright (c) 2012 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""koHamlLanguage - define the usual UDL stuff here"""

import logging
import os, sys, re
from xpcom import components, COMException, ServerException, nsError

log = logging.getLogger("koHamlLanguage")
#log.setLevel(logging.DEBUG)
from koXMLLanguageBase import koHTMLLanguageBase

class koHamlLanguage(koHTMLLanguageBase):
    name = "Haml"
    lexresLangName = name
    _reg_desc_ = "%s Language" % name
    _reg_clsid_ = "{4813db69-46ad-4e69-9be0-0d4dfa982333}"
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    
    defaultExtension = '.haml'
    primary = 0
    supportsSmartIndent = "text"  # try python?
    searchURL = "http://haml-lang.com/docs.html"

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'Haml', 'M': 'HTML', 'CSS': 'CSS', 'SSL': "Ruby"}

    sample = """
#content
  .left.column
    %h2 Welcome to our site!
    %p= print_information
  .right.column
    = render :partial => "sidebar"
"""
