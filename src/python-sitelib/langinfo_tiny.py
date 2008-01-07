# Copyright (c) 2007 ActiveState Software Inc.

"""LangInfo definitions for some "tiny" languages.

Examples are one-off file types (specific to some software project or something),
specific config files, etc.
"""

from langinfo import LangInfo


class ConsignLangInfo(LangInfo):
    """.consign files used by the Cons build tool."""
    name = "Cons cache"
    conforms_to_bases = ["Text"]
    filename_patterns = [".consign"]

