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

# This module provides utility functions for Python macro authors.
# it is populated at runtime with a few toplevel variables as
# documented in the Macro API documentation.

from xpcom import components, ServerException, COMException, nsError

def doCommand(commandId):
    _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
        .getService(components.interfaces.nsIObserverService)
    # komodo.window is injected in projectUtils.evalPythonMacro()
    # Use a try block in case this code is run in some other context
    try:
        win = window
    except NameError:
        win = None
    _observerSvc.notifyObservers(win, 'command-docommand', commandId)

projectPartTypes = ['file', 'folder', 'Dialog'] # Dialog?
def findPart(partType, name, where='*'):
    """Find a component in the Toolbox, Projects, etc.
    
        "partType" is one of "command", "snippet", "macro", "template",
            "file", "folder", "URL", "Dialog", "menu",
            or "toolbar".
        "name" is the name of the component to look for.
        "where" is one of the following:
            "toolbox": search in the Toolbox
            "shared toolbox": search in the Shared Toolbox (if enabled)
            "toolboxes": search in both of the above
            "container": search in the same tree as the running macro
            "*": search in all of the above
    
    If multiple components are found with the same name, the first one wins.
    If none are found, None is returned.
    """

    _toolboxSvc = components.classes["@activestate.com/koToolbox2Service;1"]\
        .getService(components.interfaces.koIToolbox2Service)
    runningMacro = _toolboxSvc.runningMacro
    if partType in projectPartTypes:
        _partSvc = components.classes["@activestate.com/koPartService;1"]\
                   .getService(components.interfaces.koIPartService)
        return _partSvc.findPart(partType, name, where, runningMacro)
    else:
        XXX # @@@@ Implement this
        NewTools
        return _toolboxSvc.findToolByTypeAndName(partType, name, where)


def getWordUnderCursor():
    """Return the word under the cursor in the current buffer."""
    import re
    from komodo import editor
    
    wordCharPattern = re.compile("\w")
    def isWordCharacter(ch):
        return wordCharPattern.match(ch) is not None
    
    # Retrieve the current word under the cursor
    origCurrentPos = editor.currentPos
    origAnchor = editor.anchor
    
    editor.anchor = editor.currentPos # get rid of the selection
    if (editor.currentPos and
        # There is part of a word to our left
        isWordCharacter(editor.getWCharAt(editor.currentPos-1))):
        editor.wordLeft()
    
    # Using several wordPartRights instead of one wordRight because the
    # latter is whitespace swallowing.
    sentinel = editor.currentPos
    while (editor.currentPos < editor.textLength and
           # There is part of a word to our right
           isWordCharacter(editor.getWCharAt(editor.currentPos))):
        editor.wordPartRightExtend()
        if sentinel == editor.currentPos:
            break

    word = editor.selText
    editor.currentPos = origCurrentPos
    editor.anchor = origAnchor
    return word
    

def interpolate(s, bracketed=0):
    """Interpolate shortcuts in the given string.

        "s" is the string to interpolate
        "bracketed" (optional) is a boolean indicating if plain (e.g. %F)
            or bracketed (e.g. [[%F]]) interpolation shortcuts are being
            used.
    
    Limitations: Some interpolation shortcuts cannot be used from Python.
    These include '%P' and '%ask' and the ':orask' modifier on other
    shortcuts. A ValueError is raised if they are used.
    """
    iSvc = components.classes["@activestate.com/koInterpolationService;1"]\
           .getService(components.interfaces.koIInterpolationService)
    if bracketed:
        strings = []
        bracketedStrings = [s]
    else:
        strings = [s]
        bracketedStrings = []
    from komodo import document, editor, view
    fileName = lineNum = word = selection = projectFile = prefSet = None
    if document: fileName = document.displayPath
    if editor:
        lineNum = editor.lineFromPosition(editor.currentPos) + 1
        selection = editor.selText
        word = getWordUnderCursor()
    if view:
        prefSet = view.prefs

    try:
        queries, i1strings = iSvc.Interpolate1(strings, bracketedStrings,
                                               fileName, lineNum, word,
                                               selection, projectFile,
                                               prefSet)
    except COMException, ex:
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
                       getService(components.interfaces.koILastErrorService)
        errmsg = lastErrorSvc.getLastErrorMessage()
        raise ValueError("could not interpolate string: %s (this might be "
                         "a Python macro interpolate() limitation)" % errmsg)
    if queries:
        raise ValueError("cannot interpolate '%ask' codes or ':ask' "
                         "modifiers with Komodo's Python macro API's "
                         "interpolate()")
    return i1strings[0]
