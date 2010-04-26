#!/usr/bin/env python

import sys
import traceback

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject
import mozutils
import weakref



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

    _partSvc = components.classes["@activestate.com/koPartService;1"]\
        .getService(components.interfaces.koIPartService)
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
        _partSvc.runningMacro = None
        err = ''.join(traceback.format_exception(*sys.exc_info()))
        lastErrorSvc.setLastError(1, err)
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)
