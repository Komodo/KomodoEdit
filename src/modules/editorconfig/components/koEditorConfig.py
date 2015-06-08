#!python
# Copyright (c) 2014-2014 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""The main PyXPCOM module for .editorconfig"""

from xpcom.components import interfaces as Ci
from xpcom.components import classes as Cc
from editorconfig import get_properties, EditorConfigError

import logging
import json

log = logging.getLogger("editorconfig")
log.setLevel(10)

class koEditorConfig:

    _com_interfaces_ = [Ci.koIEditorConfig]
    _reg_desc_ = "EditorConfig"
    _reg_clsid_ = "{2cf77db4-c923-4a37-bfea-91764163ff84}"
    _reg_contractid_ = "@activestate.com/editorconfig/koEditorConfig;1"

    def get_properties(self, filename, interpret = True):
        try:
            options = get_properties(filename)
        except exceptions.ParsingError:
            log.warning("Error parsing an .editorconfig file")
            return ""
        except exceptions.PathError:
            log.error("Invalid filename specified")
            return ""
        except exceptions.EditorConfigError:
            log.error("An unknown EditorConfig error occurred")
            return ""
        
        if interpret:
            items = {}
            for key, value in options.iteritems():
                if value.isdigit():
                    value = int(value)
                elif value == "true" or value == "false":
                    value = value == "true"
                    
                if key == "indent_style":
                    items["useTabs"] = value == "tab"
                elif key == "indent_size":
                    if value != "tab":
                        items["indentWidth"] = value
                elif key == "tab_width":
                    items["tabWidth"] = value
                elif key == "end_of_line":
                    items["endOfLine"] = value.upper()
                elif key == "charset":
                    items["encodingDefault"] = value
                elif key == "trim_trailing_whitespace":
                    items["cleanLineEnds"] = value
                elif key == "insert_final_newline":
                    items["ensureFinalEOL"] = value
                elif key == "max_line_length":
                    # not exactly the same, we're just setting the guide line
                    items["editAutoWrapColumn"] = value
                else:
                    items[key] = value
        else:
            items = options.items();
        
        return json.dumps(items)
