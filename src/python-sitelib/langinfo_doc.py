# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""LangInfo definitions for some document languages."""

#TODO:
# - some XML langs to add:  DocBook, Atom, Dita,
#   RDF, RSS (various versions?), RelaxNG, XML Schema, XSLT.
#   ODF, UBL (these mentioned by Tim Bray, http://www.tbray.org/ongoing/When/200x/2006/01/08/No-New-XML-Languages)
#   others?

import re
from langinfo import LangInfo



class HTMLLangInfo(LangInfo):
    name = "HTML"
    conforms_to_bases = ["Text"]
    exts = ['.html', '.htm']
    magic_numbers = [
        (0, "string", "<!DOCTYPE html"),
        (0, "string", "<html"),
    ]
    # The default encoding is iso-8859-1 or utf-8 depending on the
    # Content-Type (provided by an HTTP header or defined in a <meta>
    # tag). See here for a good summary:
    #   http://feedparser.org/docs/character-encoding.html#advanced.encoding.intro
    # We'll just use UTF-8. Safer. It is the future.
    default_encoding = "utf-8"
    doctypes = [
        # <flavour>, <common-name>, <public-id>, <system-id>
        ("HTML 4.01 Strict", "HTML",
         "-//W3C//DTD HTML 4.01//EN",
         "http://www.w3.org/TR/html4/strict.dtd"),
        ("HTML 4.01 Transitional", "HTML",
         "-//W3C//DTD HTML 4.01 Transitional//EN",
         "http://www.w3.org/TR/html4/loose.dtd"),
        ("HTML 4.01 Frameset", "HTML",
         "-//W3C//DTD HTML 4.01 Frameset//EN",
         "http://www.w3.org/TR/html4/frameset.dtd"),
        ("HTML 3.2", "HTML",
         "-//W3C//DTD HTML 3.2 Final//EN", None),
        ("HTML 2.0", "HTML",
         "-//IETF//DTD HTML//EN", None),
        #TODO: HTML 5
        # c.f. http://www.elementary-group-standards.com/html/html5-doctype-is-unrecognized.html
    ]
    

class XHTMLLLangInfo(LangInfo):
    name = "XHTML"
    conforms_to_bases = ["XML", "HTML"]
    exts = ['.xhtml']
    doctypes = [
        # <flavour>, <common-name>, <public-id>, <system-id>
        ("XHTML 1.0 Strict", "html",
         "-//W3C//DTD XHTML 1.0 Strict//EN",
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"),
        ("XHTML 1.0 Transitional", "html",
         "-//W3C//DTD XHTML 1.0 Transitional//EN",
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"),
        ("XHTML 1.0 Frameset", "html",
         "-//W3C//DTD XHTML 1.0 Frameset//EN",
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd"),
    ]


class XMLLangInfo(LangInfo):
    name = "XML"
    conforms_to_bases = ["Text"]
    exts = ['.xml']
    default_encoding = "utf-8"
    magic_numbers = [
        (0, "string", "<?xml"),
    ]

class XULLangInfo(LangInfo):
    name = "XUL"
    conforms_to_bases = ["XML"]
    exts = ['.xul']
    doctypes = [
        # <flavour>, <common-name>, <public-id>, <system-id>
        (None, "window", "-//MOZILLA//DTD XUL V1.0//EN",
         "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul"),
    ]

class XBLLangInfo(LangInfo):
    """eXtensible Binding Language"""
    name = "XBL"
    conforms_to_bases = ["XML"]
    exts = ['.xbl']
    # doctype:
    #   <!DOCTYPE bindings PUBLIC "-//MOZILLA//DTD XBL V1.0//EN" "http://www.mozilla.org/xbl">
    doctypes = [
        # <flavour>, <common-name>, <public-id>, <system-id>
        (None, "bindings", "-//MOZILLA//DTD XBL V1.0//EN",
         "http://www.mozilla.org/xbl"),
    ]

class YAMLLangInfo(LangInfo):
    name = "YAML"
    conforms_to_bases = ["Text"]
    exts = ['.yaml', '.yml']
    #TODO: default encoding?

class JSONLangInfo(LangInfo):
    name = "JSON"
    conforms_to_bases = ["JavaScript"]
    exts = [".json"]

class DTDLangInfo(LangInfo):
    name = "DTD"
    conforms_to_bases = ["Text"]
    exts = [".dtd"]

class PODLangInfo(LangInfo):
    """Plain Old Documentation format common in the Perl world."""
    name = "POD"
    #TODO: does POD conform-to Perl?
    conforms_to_bases = ["Text"]
    exts = [".pod"]
    # http://search.cpan.org/~nwclark/perl-5.8.8/pod/perlpod.pod
    encoding_decl_pattern = re.compile(r"^=encoding\s+(?P<encoding>[-\w.]+)", re.M)

class RHTMLLangInfo(LangInfo):
    name = "RHTML"
    conforms_to_bases = ["Text"]
    exts = [".rhtml"]

#TODO: how to handle the ext collision with HTML?!
#class DjangoHTMLTemplateLangInfo(LangInfo):
#    name = "Django HTML Template"
#    conforms_to_bases = ["Text"]
#    exts = [".html"]



