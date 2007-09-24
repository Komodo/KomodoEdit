# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Utility functions for dealing with scimoz & indentation
# that are used both by koLanguageServiceBase and koLanguageCommandHandler

def makeIndentFromWidth(scimoz, width):
    """ returns a string consisting of however many tabs and spaces
    are needed to make a width of `width`, using the useTabs pref
    and the scimoz tabWidth
    """
    if scimoz.useTabs:
        tabWidth = scimoz.tabWidth
        # guard against a misconfigured scimoz with a tabWidth
        # of 0, which would cause a divide by zero error
        if tabWidth == 0: tabWidth = 8
        numtabs, numspaces = divmod(width, scimoz.tabWidth)
        return '\t'*numtabs + ' '*numspaces
    else:
        return ' '*width

import koXMLTreeService

def startTagInfo_from_endTagPos(scimoz, endTagPos):
    # DOM lines and columns seem to be 1-based
    endTagLine = scimoz.lineFromPosition(endTagPos)
    endTagCol = scimoz.getColumn(endTagPos)
    tree = koXMLTreeService.getService().getTreeForContent(scimoz.text)
    node = tree.locateNode(endTagLine, endTagCol)
    if node is None:
        return
    startTagNode = node.start
    startTagLine, startTagCol = startTagNode[0] - 1, startTagNode[1]
    startTag_LineStartPos = scimoz.positionFromLine(startTagLine)
    return (startTagLine, startTagCol, startTag_LineStartPos)

def adjustClosingXMLTag(scimoz):
    """ This function is called when a ">" from an XML end tag
    is inserted, and it will shift the current line either back
    or forwards so that the tag is aligned with the matching start tag.
    It will only do so if the end tag is the only thing to the left of
    the current position on the current line.
    """
    beforeText = scimoz.getTextRange(0, scimoz.currentPos)
    # (for now, assuming no intervening space)
    leftCloseIndex = beforeText.rfind('</')
    if leftCloseIndex == -1:
        # no idea what to do in this case, just bail
        return
    leftCloseIndex = len(beforeText[0:leftCloseIndex].encode('utf-8')) # bug 69731
    startTagInfo = startTagInfo_from_endTagPos(scimoz, leftCloseIndex)
    if startTagInfo is None:
        return
    startTagLine, startTagCol, startTag_LineStartPos = startTagInfo
    if beforeText[startTag_LineStartPos:startTag_LineStartPos+startTagCol].strip():
        return
    
    startIndentWidth = startTagCol
    indent = scimoz.indent
    if indent == 0:
        indent = 8
    indentLevel, extras = divmod(startIndentWidth, indent)
    if indentLevel and not extras:
        indentLevel -= 1
    nextIndentWidth = indentLevel * scimoz.indent
    # The first decrement is safe because scimoz.charAt(scimoz.currentPos - 1) == '<'
    # The second has to go through the API in case it's a multi-byte char
    charPos = scimoz.positionBefore(scimoz.currentPos - 1)
    lineNo = scimoz.lineFromPosition(charPos)
    startOfLine = max(0, scimoz.positionFromLine(lineNo))
    if startOfLine > leftCloseIndex:
        return
    stuffToLeft = scimoz.getTextRange(startOfLine, leftCloseIndex)
    if not stuffToLeft.strip(): # XXX Do we want to pref this?
        # we can align the comment closing before we do the newline
        indent = makeIndentFromWidth(scimoz, startTagCol)
        scimoz.targetStart = scimoz.positionFromLine(lineNo)
        scimoz.targetEnd = leftCloseIndex
        scimoz.replaceTarget(len(indent), indent)
    scimoz.chooseCaretX()
