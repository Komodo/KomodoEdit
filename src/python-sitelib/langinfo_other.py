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

