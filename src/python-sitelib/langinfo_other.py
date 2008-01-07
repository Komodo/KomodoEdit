# Copyright (c) 2007 ActiveState Software Inc.

"""LangInfo definitions for languages that don't fit in the other
langinfo_*.py files.
"""

import re
from langinfo import LangInfo



class MakefileLangInfo(LangInfo):
    name = "Makefile"
    conforms_to_bases = ["Text"]
    exts = [".mak"]
    filename_patterns = [re.compile(r'^[Mm]akefile.*$')]

class CSSLangInfo(LangInfo):
    name = "CSS"
    conforms_to_bases = ["Text"]
    exts = [".css"]
    default_encoding = "utf-8"
    # http://www.w3.org/International/questions/qa-css-charset
    # http://www.w3.org/TR/CSS21/syndata.html#charset
    # http://www.w3.org/TR/CSS2/syndata.html#q23            
    # I.e., look for:
    #   @charset "<IANA defined charset name>";
    # at the start of the CSS document.
    encoding_decl_pattern = re.compile(r'\A@charset "(?P<encoding>[\w-]+)";')

class CIXLangInfo(LangInfo):
    """Komodo Code Intelligence XML dialect.

    This is used to define the code structure of scanned programming
    language content.
    """
    name = "CIX"
    conforms_to_bases = ["XML"]
    exts = [".cix"]

class DiffLangInfo(LangInfo):
    name = "diff"
    conforms_to_bases = ["Text"]
    exts = [".patch", ".diff"]

class IDLLangInfo(LangInfo):
    name = "IDL"
    conforms_to_bases = ["Text"]
    exts = [".idl"]

