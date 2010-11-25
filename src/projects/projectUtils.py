#!/usr/bin/env python
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

import sys
import traceback

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject
import mozutils
import weakref

import logging
log = logging.getLogger("projectUtils")
#log.setLevel(logging.DEBUG)


# we use a weak value dictionary to make sure that the id map doesn't end up
# keeping references alive.
idmap = weakref.WeakValueDictionary()


def getNextId(part):
    xulid = mozutils.generateUUID()
    idmap[xulid] = part
    return xulid

def findPartById(id):
    if id in idmap:
        return idmap[id]
    return None

# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)

def wrapPythonMacro(code, functionName='_code'):
    if sys.platform.startswith("win"):
        code = code.replace("\r\n", "\n")
    return "def %s():\n%s\n\n\n" % (functionName, _indent(code))

def macro_openURI(uri):
    obsvc = components.classes["@mozilla.org/observer-service;1"].\
          getService(components.interfaces.nsIObserverService);
    obsvc.notifyObservers(None, 'open-url', uri);

def evalPythonMacro(part, domdocument, window, scimoz, document, view, code,
                    subject=None, topic="", data=""):
    lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
        .getService(components.interfaces.koILastErrorService)
    lastErrorSvc.setLastError(0, '')
    import komodo
    komodo.domdocument = domdocument
    # `.document` is DEPRECATED in Komodo 6.0.0b1, use `.koDoc`.
    komodo.koDoc = komodo.document = document
    komodo.editor = scimoz
    komodo.view = view
    komodo.window = window
    komodo.components = components
    komodo.macro = part
    komodo.openURI = macro_openURI
    macroGlobals = {}
    macroGlobals['komodo'] = komodo
    macroGlobals['window'] = window
    if topic:
        macroGlobals['subject'] = subject
        macroGlobals['topic'] = topic
        macroGlobals['data'] = data

    _partSvc = components.classes["@activestate.com/koToolbox2Service;1"]\
        .getService(components.interfaces.koIToolbox2Service)
    _partSvc.runningMacro = part

    # Put the Python macro code in a "_code()" function and eval it.
    #
    # Note: This has the potential to be problematic if the Python
    # macro uses a syntax at the top-level that isn't allowed inside
    # a Python function. For example, "from foo import *" in a function
    # with Python 2.5 generates:
    #   bar.py:2: SyntaxWarning: import * only allowed at module level
    #       def _code():
    # Not sure if that will be made an *error* in future Python versions.
    code = wrapPythonMacro(code)
    try:
        exec code in macroGlobals, macroGlobals
        retval = eval('_code()', macroGlobals, macroGlobals)
        _partSvc.runningMacro = None
        return retval
    except Exception, e:
        log.exception("Failed to exec the macro %s", part.name)
        _partSvc.runningMacro = None
        err = ''.join(traceback.format_exception(*sys.exc_info()))
        lastErrorSvc.setLastError(1, err)
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)
