#!/usr/bin/env python

"""A Code Intelligence Language Engine for the ${lang} language.

A "Language Engine" is responsible for scanning content of
its language and generating CIX output that represents an outline of
the code elements in that content. See the CIX (Code Intelligence XML)
format:
    http://community.activestate.com/faq/codeintel-cix-schema
    
Module Usage:
    from cile_${safe_lang_lower} import scan
    mtime = os.stat("bar.${safe_lang_lower}")[stat.ST_MTIME]
    content = open("bar.${safe_lang_lower}", "r").read()
    scan(content, "bar.${safe_lang_lower}", mtime=mtime)
"""

__version__ = "1.0.0"

import os
import sys
import time
import optparse
import logging
import pprint
import glob

# Note: c*i*ElementTree is the codeintel system's slightly modified
# cElementTree. Use it exactly as you would the normal cElementTree API:
#   http://effbot.org/zone/element-index.htm
import ciElementTree as ET

from codeintel2.common import CILEError



#---- exceptions

class ${safe_lang}CILEError(CILEError):
    pass



#---- global data

log = logging.getLogger("cile.${safe_lang_lower}")
#log.setLevel(logging.DEBUG)



#---- public module interface

def scan_buf(buf, mtime=None, lang="${lang}"):
    """Scan the given ${safe_lang}Buffer return an ElementTree (conforming
    to the CIX schema) giving a summary of its code elements.
    
    @param buf {${safe_lang}Buffer} is the ${lang} buffer to scan
    @param mtime {int} is a modified time for the file (in seconds since
        the "epoch"). If it is not specified the _current_ time is used.
        Note that the default is not to stat() the file and use that
        because the given content might not reflect the saved file state.
    """
    # Dev Notes:
    # - This stub implementation of the ${lang} CILE return an "empty"
    #   summary for the given content, i.e. CIX content that says "there
    #   are no code elements in this ${lang} content".
    # - Use the following command (in the extension source dir) to
    #   debug/test your scanner:
    #       codeintel scan -p -l ${lang} <example-${lang}-file>
    #   "codeintel" is a script available in the Komodo SDK.
    log.info("scan '%s'", buf.path)
    if mtime is None:
        mtime = int(time.time())

    # The 'path' attribute must use normalized dir separators.
    if sys.platform.startswith("win"):
        path = buf.path.replace('\\', '/')
    else:
        path = buf.path
        
    tree = ET.Element("codeintel", version="2.0",
                      xmlns="urn:activestate:cix:2.0")
    file = ET.SubElement(tree, "file", lang=lang, mtime=str(mtime))
    blob = ET.SubElement(file, "scope", ilk="blob", lang=lang,
                         name=os.path.basename(path))

    # Dev Note:
    # This is where you process the ${lang} content and add CIX elements
    # to 'blob' as per the CIX schema (cix-2.0.rng). Use the
    # "buf.accessor" API (see class Accessor in codeintel2.accessor) to
    # analyze. For example:
    # - A token stream of the content is available via:
    #       buf.accessor.gen_tokens()
    #   Use the "codeintel html -b <example-${lang}-file>" command as
    #   a debugging tool.
    # - "buf.accessor.text" is the whole content of the file. If you have
    #   a separate tokenizer/scanner tool for ${lang} content, you may
    #   want to use it.

    return tree


