# This module provides utility functions for Python macro authors.
# it is populated at runtime with a few toplevel variables as
# documented in the Macro API documentation.

from xpcom import components, ServerException, COMException, nsError

def doCommand(commandId):
    _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
        .getService(components.interfaces.nsIObserverService)
    _observerSvc.notifyObservers(None, 'command-docommand', commandId)

def findPart(partType, name, where='*'):
    """Find a component in the Toolbox, Projects, etc.
    
        "partType" is one of "command", "snippet", "macro", "template",
            "file", "folder", "URL", "DirectoryShortcut", "Dialog", "menu",
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
    _partSvc = components.classes["@activestate.com/koPartService;1"]\
        .getService(components.interfaces.koIPartService)
    return _partSvc.findPartForRunningMacro(partType, name, where)


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
