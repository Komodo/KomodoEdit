# Copyright (c) 2007 ActiveState Software Inc.

"""LangInfo definitions for some document languages."""

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

class XHTMLLLangInfo(LangInfo):
    name = "XHTML"
    conforms_to_bases = ["XML", "HTML"]
    exts = ['.xhtml']
    #TODO: How does an XHTML file with .html ext get assigned this lang?
    #      presumably _classify_from_content() will provide this.

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
    # doctype:
    #   <!DOCTYPE window PUBLIC "-//MOZILLA//DTD XUL V1.0//EN" "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul" [ ... ]>


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



