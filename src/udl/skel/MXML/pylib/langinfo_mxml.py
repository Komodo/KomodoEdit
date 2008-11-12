# Copyright (c) 2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""LangInfo definitions for MXML."""

import re
from langinfo import LangInfo


class MXMLLangInfo(LangInfo):
    """XML-based UI markup language used with Adobe's Flex system.
    
    http://en.wikipedia.org/wiki/MXML
    """
    name = "MXML"
    conforms_to_bases = ["XML"]
    exts = ['.mxml']

