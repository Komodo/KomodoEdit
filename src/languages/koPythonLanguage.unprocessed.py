#!python
# Copyright (c) 2001-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Python-specific Language Services implementations."""

import os
import sys, re
import keyword
import cStringIO, StringIO  # cStringIO doesn't work well with unicode strings! 
import pprint
import tokenize
import token

import logging
from xpcom import components, ServerException
from koLanguageServiceBase import *
import sciutils


def registerLanguage(registery):
    registery.registerLanguage(KoPythonLanguage())
    

#---- globals

log = logging.getLogger("koPythonLanguage")
#log.setLevel(logging.DEBUG)

#---- internal support routines

def classifyws(s, tabwidth):
    # taken from IDLE
    # Look at the leading whitespace in s.
    # Return pair (# of leading ws characters,
    #              effective # of leading blanks after expanding
    #              tabs to width tabwidth)
    foundTabs = 0
    raw = effective = 0
    for ch in s:
        if ch == ' ':
            raw = raw + 1
            effective = effective + 1
        elif ch == '\t':
            foundTabs = 1
            raw = raw + 1
            effective = (effective / tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective, foundTabs

def isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def isdigit(char):
    return "0" <= char <= "9"

def getLastLogicalLine(text):
    lines = text.splitlines(0) or ['']
    logicalline = lines.pop()
    while lines and lines[-1].endswith('\\'):
        logicalline = lines.pop()[:-1] + ' ' + logicalline
    return logicalline


class IndentSearcher:
    # taken from IDLE
    # .run() chews over the Text widget, looking for a block opener
    # and the stmt following it.  Returns a pair,
    #     (line containing block opener, line containing stmt)
    # Either or both may be None.

    def __init__(self, text, tabwidth):
        # if we can, do things fast by using regular python string
        # classes, and not unicode classes
        try:
            self.text = cStringIO.StringIO(str(text))
        except:
            self.text = StringIO.StringIO(text)
        self.tabwidth = tabwidth
        self.i = self.finished = 0
        self.blkopenline = self.indentedline = None
        self.numOpenBrackets = 0

    def readline(self):
        line = self.text.readline()
        return line

    def tokeneater(self, type, token, start, end, line,
                   INDENT=tokenize.INDENT,
                   NAME=tokenize.NAME,
                   OPENERS=('class', 'def', 'for', 'if', 'try', 'while'),
                   OP=tokenize.OP,
                   BRACKETS_OPEN='([{',
                   BRACKETS_CLOSE=')]}'):
        #tokenize.printtoken(type, token, start, end, line)
        #print "self.numOpenBrackets: %r" % (self.numOpenBrackets)
        if self.numOpenBrackets == 0:
            if type == NAME and token in OPENERS:
                self.blkopenline = line
            elif type == INDENT and self.blkopenline:
                self.indentedline = line
                # this stops the tokenizer, we have enough info for indent
                # detection at this point
                raise tokenize.StopTokenizing()
            elif type == OP and token in BRACKETS_OPEN:
                self.numOpenBrackets += 1
        elif type == OP:
            if token in BRACKETS_OPEN:
                self.numOpenBrackets += 1
            elif token in BRACKETS_CLOSE:
                self.numOpenBrackets -= 1

    def run(self):
        save_tabsize = tokenize.tabsize
        tokenize.tabsize = self.tabwidth
        try:
            try:
                tokenize.tokenize(self.readline, self.tokeneater)
            except tokenize.TokenError:
                # since we cut off the tokenizer early, we can trigger
                # spurious errors
                pass
        finally:
            tokenize.tabsize = save_tabsize
        return self.blkopenline, self.indentedline



#---- Language Service component implementations

class KoPythonLexerLanguageService(KoLexerLanguageService):
    def __init__(self):
        KoLexerLanguageService.__init__(self)
        self.setLexer(components.interfaces.ISciMoz.SCLEX_PYTHON)
        kwlist = set(keyword.kwlist)
        kwlist.update(['None', 'as', 'with', 'True', 'False'])
        self.setKeywords(0, list(kwlist))
        self.setProperty('tab.timmy.whinge.level', '1') # XXX make a user-accesible pref
        # read lexPython.cxx to understand the meaning of the levels.
        self.supportsFolding = 1


class KoPythonLanguage(KoLanguageBase):
    name = "Python"
    _reg_desc_ = "%s Language" % (name)
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{D90FF5C7-1FD4-4535-A0D2-47B5BDC3E7FE}"

    accessKey = 'y'
    primary = 1
    shebangPatterns = [
        re.compile(ur'\A#!.*python.*$', re.IGNORECASE | re.MULTILINE),
    ]
    namedBlockRE = "^[ \t]*?(def\s+[^\(]+\([^\)]*?\):|class\s+[^:]*?:)"
    namedBlockDescription = 'Python functions and classes'
    defaultExtension = ".py"
    # XXX read url from some config file
    downloadURL = 'http://www.ActiveState.com/Products/ActivePython'
    commentDelimiterInfo = { "line": [ "#" ]  }
    _indent_open_chars = ':{[('
    _lineup_open_chars = "([{" 
    _lineup_close_chars = ")]}"
    _dedenting_statements = [u'raise', u'return', u'pass', u'break', u'continue']
    supportsSmartIndent = "python"
    sample = """import math
class Class:
    \"\"\" this is a docstring \"\"\"
    def __init__(self, arg): # one line comment
        self.x = arg + math.cos(arg + arg)
        s = 'a string'
"""

    styleStdin = sci_constants.SCE_P_STDIN
    styleStdout = sci_constants.SCE_P_STDOUT
    styleStderr = sci_constants.SCE_P_STDERR

    def __init__(self):
        KoLanguageBase.__init__(self)
        # Classes that want to define their own variable styles need to
        # let the base class initialize the style info first, and then
        # fill in the details this way.
        self._style_info._variable_styles = [sci_constants.SCE_P_IDENTIFIER]
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)

    def getVariableStyles(self):
        return self._style_info._variable_styles

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoPythonLexerLanguageService()
        return self._lexer

    # The new autocomplete/calltip functionality based on the codeintel
    # system.
    def get_codeintelcompleter(self):
        if self._codeintelcompleter is None:
            self._codeintelcompleter =\
                components.classes["@activestate.com/koPythonCodeIntelCompletionLanguageService;1"]\
                .getService(components.interfaces.koICodeIntelCompletionLanguageService)
            self._codeintelcompleter.initialize(self)
            # Ensure the service gets finalized when Komodo shutsdown.
            finalizeSvc = components.classes["@activestate.com/koFinalizeService;1"]\
                .getService(components.interfaces.koIFinalizeService)
            finalizeSvc.registerFinalizer(self._codeintelcompleter)
        return self._codeintelcompleter

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter =\
                components.classes["@activestate.com/koAppInfoEx?app=Python;1"]\
                .getService(components.interfaces.koIAppInfoEx)
        return self._interpreter
    
    def guessIndentation(self, scimoz, tabWidth):
        return self._guessIndentation(scimoz, tabWidth, self._style_info)

    def _guessIndentation(self, scimoz, tabWidth, style_info):
        # style_info not used, here for compatibility
        text = scimoz.text
        # the logic used here (and the code, with minor mods)
        # is taken out of IDLE's AutoIndent extension.
        opener, indented = IndentSearcher(text, tabWidth).run()
        if opener and indented:
            raw, indentsmall, foundTabsInOpener = classifyws(opener, tabWidth)
            raw, indentlarge, foundTabsInIndented = classifyws(indented, tabWidth)
            foundTabs = foundTabsInOpener or foundTabsInIndented
        else:
            indentsmall = indentlarge = 0
            foundTabs = 0
        # Ensure our guess is not a negative value
        guess = max(0, indentlarge - indentsmall)
        return guess, foundTabs

    def test_scimoz(self, scimoz):
        CommenterTestCase.lang = self
        testCases = [
            CommenterTestCase,
        ]
        sciutils.runSciMozTests(testCases, scimoz)

class KoPythonCodeIntelCompletionLanguageService(KoCodeIntelCompletionLanguageService):
    _com_interfaces_ = [components.interfaces.koICodeIntelCompletionLanguageService]
    _reg_desc_ = "Python CodeIntel Calltip/AutoCompletion Service"
    _reg_clsid_ = "{1D90B399-84E8-41E0-A8B1-63D6F0E48752}"
    _reg_contractid_ = "@activestate.com/koPythonCodeIntelCompletionLanguageService;1"

    # basically, any non-identifier char
    completionFillups = "~`!@#$%^&*()-=+{}[]|\\;:'\",.<>?/ "

    def getTriggerType(self, scimoz, position=None, implicit=1):
        """If the given position is a _likely_ trigger point, return the
        trigger type. Otherwise return the None.
        
            "position" (optional) is the position at which to check for a
                trigger point. If pos is None, then it defaults to the current
                cursor position.
            "implicit" (optional) is a boolean indicating if this trigger
                is being implicitly checked (i.e. as a side-effect of
                typing). Defaults to true.
        
        (See koILanguage.idl::koICodeIntelCompletionLanguageService for
        details.)
        
        Python-specific return values:
            None            not at a trigger point
            "autocomplete-object-members"
            "calltip-call-signature"
        
        Not yet implemented:
            "autocomplete-available-imports"
            "autocomplete-module-members"
            "autocomplete-available-classes"
            "calltip-base-signature"
        """
        DEBUG = 0  # not using 'logging' system, because want to be fast
        if DEBUG:
            print "\n----- getTriggerType(scimoz, position=%r, implicit=%r) -----"\
                  % (position, implicit)

        if position is None:
            position = scimoz.currentPos
        lastPos = position - 1
        lastChar = scimoz.getWCharAt(lastPos)
        if DEBUG:
            print "  lastPos: %s" % lastPos
            print "  lastChar: %r" % lastChar

        # All Python trigger points occur at one of these characters:
        # '.' (period), '(' (open paren). (XXX Add ' ' (space) when
        # "autocomplete-available-imports" is re-added.)
        if lastChar not in ".(":
            if DEBUG:
                print "getTriggerType: no: %r is not in '.('" % lastChar
            return None

        # We should never trigger in some styles (strings, comments, etc.).
        styleMask = (1 << scimoz.styleBits) - 1
        styleNum = scimoz.getStyleAt(lastPos) & styleMask
        if DEBUG:
            sciUtilsSvc = components.classes["@activestate.com/koSciUtils;1"].\
                          getService(components.interfaces.koISciUtils)
            styleName = sciUtilsSvc.styleNameFromNum("Python", styleNum)
            print "  style: %s (%s)" % (styleNum, styleName)
        if (implicit and styleNum in self._noImplicitCompletionStyles
            or styleNum in self._noCompletionStyles):
            if DEBUG:
                print "getTriggerType: no: completion is suppressed "\
                      "in style at %s: %s (%s)"\
                      % (lastPos, styleNum, styleName)
            return None

        #XXX Disabled for now.
        #if lastChar == ' ':
        #    # Typing a space is very common so lets have a quick out before
        #    # doing the more correct processing:
        #    if lastPos-1 < 0 or scimoz.getWCharAt(lastPos-1) not in "tm":
        #        return None
        #
        #    # Triggering examples ('_' means a space here):
        #    #   import_                 from_
        #    # Non-triggering examples:
        #    #   from FOO import_        Ximport_
        #    # Not bothering to support:
        #    #;  if FOO:import_          FOO;import_
        #    workingText = scimoz.getTextRange(max(0,lastPos-200), lastPos)
        #    line = getLastLogicalLine(workingText).strip()
        #    if line in ("import", "from"):
        #        return "autocomplete-available-imports"

        if lastChar == '.': # must be "autocomplete-object-members" or None
            # If the first non-whitespace character preceding the '.' in the
            # same statement is an identifer character then trigger, if it
            # is a ')', then _maybe_ we should trigger (yes if this is
            # function call paren).
            #
            # Triggering examples:
            #   FOO.            FOO .                       FOO; BAR.
            #   FOO().          FOO.BAR.                    FOO(BAR, BAZ.
            #   FOO().BAR.      FOO("blah();", "blam").     FOO = {BAR.
            #   FOO(BAR.        FOO[BAR.
            #   ...more cases showing possible delineation of expression
            # Non-triggering examples:
            #   FOO..
            #   FOO[1].         too hard to determine sequence element types
            # Not sure if want to support:
            #   "foo".          do we want to support literals? what about
            #                   lists? tuples? dicts?
            workingText = scimoz.getTextRange(max(0,lastPos-200), lastPos)
            line = getLastLogicalLine(workingText).rstrip()
            if line:
                ch = line[-1]
                if isident(ch) or isdigit(ch) or ch == ')':
                    return "autocomplete-object-members"
            else:
                ch = None
            if DEBUG:
                print "getTriggerType: no: non-ws char preceding '.' is not "\
                      "an identifier char or ')': %r" % ch
            return None

        elif lastChar == '(':
            # If the first non-whitespace character preceding the '(' in the
            # same statement is an identifer character then trigger calltip,
            #
            # Triggering examples:
            #   FOO.            FOO (                       FOO; BAR(
            #   FOO.BAR(        FOO(BAR, BAZ(               FOO = {BAR(
            #   FOO(BAR(        FOO[BAR(
            # Non-triggering examples:
            #   FOO()(      a function call returning a callable that is
            #               immediately called again is too rare to bother
            #               with
            #   def foo(    might be a "calltip-base-signature", but this
            #               trigger is not yet implemented
            #   class Foo(  is an "autocomplete-available-classes" trigger,
            #               but this is not yet implemented
            workingText = scimoz.getTextRange(max(0,lastPos-200), lastPos)
            line = getLastLogicalLine(workingText).rstrip()
            if line:
                ch = line[-1]
                if isident(ch) or isdigit(ch):
                    # If this is:
                    #   def foo(
                    # then this might be the (as yet unimplemented)
                    # "calltip-base-signature" trigger or it should not be a
                    # trigger point.
                    #
                    # If this is:
                    #   class Foo(
                    # then this should be the (as yet unimplemented)
                    # "autocomplete-available-classes" trigger.
                    lstripped = line.lstrip()
                    if lstripped.startswith("def"):
                        if DEBUG: print "getTriggerType: no: point is function declaration"
                    elif lstripped.startswith("class") and '(' not in lstripped:
                        # Second test is necessary to not exclude:
                        #   class Foo(bar(<|>
                        if DEBUG: print "getTriggerType: no: point is class declaration"
                    else:
                        return "calltip-call-signature"
                else:
                    if DEBUG:
                        print "getTriggerType: no: non-ws char preceding "\
                              "'(' is not an identifier char: %r" % ch
            else:
                if DEBUG: print "getTriggerType: no: no chars preceding '('"
            return None

    def getCallTipHighlightSpan(self, enteredRegion, calltip):
        #log.debug("getCallTipHighlightSpan(enteredRegion=%r, calltip=%r)",
        #          enteredRegion, calltip)
    
        # Get a list of arg names (and start:end spans) in the calltip.
        #XXX Should use tokenize, as below, to properly handle default values
        #    that can have commas. Keep the old code around though, because
        #    it might be handy as a starter for other langs. A more
        #    language-general mechanism for Komodo would be to use scintilla
        #    style info.
        signature = calltip.splitlines(0)[0]
        i = signature.find('(')+1
        argsStr = signature[i:signature.rfind(')')]
        argNames = []
        argSpans = []
        state = "arg"
        for element in re.split("(,\s*)", argsStr):
            if state == "arg":
                argNames.append( element )
                argSpans.append( (i, i+len(element)) )
                state = "separator"
            elif state == "separator":
                state = "arg"
            i += len(element)
        #pprint.pprint(argNames)
        #pprint.pprint(argSpans)
        
        # Walk the entered region to determine to which arg the end of the
        # region corresponds.
        import tokenize
        import token
        argIndex = 0
        blockStack = [] # if inside a tuple, string, etc., then no comma counting
        blocks = {
            # Map a block start token to its block end token.
            '(': ')',
            '[': ']',
            '{': '}',
        }
        readline = StringIO.StringIO(enteredRegion).readline
        try:
            for item in tokenize.generate_tokens(readline):
                (typ, tok, (srow, scol), (erow, ecol), line) = item
                #print "token: %s %s '%s'" % (typ, token.tok_name[typ], tok)
                if typ == token.OP:
                    if tok == ',':
                        if not blockStack:
                            #print "XXX next arg"
                            argIndex += 1
                    elif tok in blocks:
                        blockStack.append(tok)
                        #print "XXX push: stack=%s" % blockStack
                    elif blockStack and tok == blocks[blockStack[-1]]:
                        blockStack.pop()
                        #print "XXX pop: stack=%s" % blockStack
                    elif not blockStack and tok == ')':
                        #print "XXX end of code region"
                        argIndex = -1
                        break
                elif typ == token.ERRORTOKEN:
                    # Something like the following:
                    #       ",
                    # will return ERRORTOKEN on the '"'. If we don't stop
                    # the subsequent ',' will be tokenized as an OP.
                    break
        except tokenize.TokenError, ex:
            pass

        if argIndex == -1:
            span = (-1, -1)
        else:
            span = argSpans[ min(argIndex, len(argSpans)-1) ]
        return span

    def triggerPrecedingCompletionUI(self, path, scimoz, startPos,
                                     ciCompletionUIHandler):
        line = scimoz.lineFromPosition(startPos)+1 # want 1-based line
        offset, styledText, styleMask = self._getSciMozContext(scimoz, startPos)
        # Find the start of the current "logical" line. This is as far back as
        # we will look.
        limitPos = sciutils.getPythonLogicalLineStartPosition(
            offset, styledText, startPos, self._noImplicitCompletionStyles,
            styleMask, context=5)

        pos = startPos
        while pos > limitPos:
            triggerType = self.getTriggerType(scimoz, pos, implicit=0)
            if triggerType:
                log.debug("triggerPrecedingCompletionUI: possible '%s' "
                          "trigger at %d", triggerType, pos)
                try:
                    #XXX If we stop using getAdjustedCurrentScope() and
                    #    instead get the scope from path/line the
                    #    CodeIntelCompletionUIHandler will have to be
                    #    updated to use the proper CI-path so that CIDB
                    #    lookups work.
                    file_id, table, id = self.codeIntelSvc.getAdjustedCurrentScope(scimoz, pos)
                    completions = self._getCompletions(
                        path, line, triggerType, offset, styledText,
                        styleMask, pos, explicit=1, scopeFileId=file_id,
                        scopeTable=table, scopeId=id, content=scimoz.text)
                except Exception, ex:
                    return "error determining '%s' completions at %d,%d: %s"\
                           % (triggerType, scimoz.lineFromPosition(pos)+1,
                              scimoz.getColumn(pos)+1, ex)
                if completions:
                    # If this is an autocomplete trigger, then we may need to
                    # move the cursor back within the "range" of the
                    # completion list. E.g.: in this case
                    #       foo.bar(blam<|>
                    #           `- trigger pos is here
                    # we would need to move the cursor back to the end of
                    # "bar" (at least):
                    #       foo.bar<|>(blam
                    # otherwise, the autocomplete UI cannot work.
                    if triggerType.startswith("autocomplete"):
                        curPos = scimoz.currentPos
                        i = pos
                        while i < curPos:
                            ch = scimoz.getWCharAt(i)
                            if not isident(ch) and not isdigit(ch):
                                scimoz.currentPos = scimoz.anchor = i
                                break
                            i += 1
                    self._dispatchCompletions(triggerType, completions,
                                              pos, 1, ciCompletionUIHandler)
                    break
            pos -= 1

    def _massageCompletions(self, types, members, dropSpecials=True):
        """Massage the given list of Python completions for use in the
        Scintilla completion list. Some transformations are done on the given
        list:
        - add the appropriate pixmap marker for each completion
        - optionally drop special names (those starting and ending with
          double-underscore, e.g. '__init__')
        
            "types" is a list of CodeIntel type names.
            "members" is a list of member names.
            "dropSpecials" (default true) is a boolean indicating if
                special names should be dropped from the list.
        """
        # Indicate the appropriate pixmap for each entry.
        # c.f. http://scintilla.sf.net/ScintillaDoc.html#SCI_REGISTERIMAGE
        cicui = components.interfaces.koICodeIntelCompletionUIHandler
        type2aciid = {
            "class": cicui.ACIID_CLASS,
            "function": cicui.ACIID_FUNCTION,
            "module": cicui.ACIID_MODULE,
            "variable": cicui.ACIID_VARIABLE,
        }
        completions = []
        for type, member in zip(types, members):
            if dropSpecials and member.startswith("__") \
               and member.endswith("__"):
                continue
            if type:
                completions.append(member + "?%d" % type2aciid[type])
            else: # type may be None to indicate type-not-known
                completions.append(member)

        return completions

    def _getCompletions(self, path, line, completionType, offset, styledText,
                        styleMask, triggerPos, explicit=0, scopeFileId=0,
                        scopeTable=None, scopeId=0, content=None):
        """Return a list of completions for the given possible trigger point.

            "completionType" is one of the possible retvals from
                getTriggerType()
            "explicit" (optional, default false) is a boolean indicating if
                the completion list was explicitly triggered.
            "scopeFileId", "scopeTable" and "scopeId" (optional) can be
                passed in to express the scope more accurately than "path"
                and "line" -- if, say, the caller is adjusting for recent
                edits not in the database.
            "content" (optional) is the file content. This may be used, if
                passed in, for fallback "dumb" completion handling.

        If this is NOT a valid trigger point (i.e. getTriggerType() was
        mistaken), then return None.
        
        XXX For now, raise an error if there is some error determining the
        completions.
        """
        log.debug("_getCompletions(path=%r, line=%r, %r, offset=%d, "
                  "styledText, styleMask, triggerPos=%d, explicit=%r, "
                  "scopeFileId=%r, scopeTable=%r, scopeId=%r, content)",
                  path, line, completionType, offset, triggerPos, explicit,
                  scopeFileId, scopeTable, scopeId)

        if completionType == "autocomplete-object-members":
            if explicit:
                # Specifically do NOT ignore comment and string styles.
                #XXX How about only do this if the current trigger pos is
                #    in one of these styles: to minimize the impact.
                #    Should ideally use this to bound the "context" to
                #    that area.
                stylesToIgnore = []
            else:
                #XXX Technically "stylesToIgnore" is supposed to be a list,
                #    but currently only the "in" operator is used so this
                #    dict should be faster.
                stylesToIgnore = self._noImplicitCompletionStyles
            expr = sciutils.getSimplifiedLeadingPythonExpr(
                offset, styledText, triggerPos, stylesToIgnore, styleMask)
            expr = expr[:-1]  # drop trailing '.'
            types, members = self.codeIntelSvc.getMembers("Python",
                path, line, expr, explicit,
                scopeFileId, scopeTable, scopeId, content)

            completions = self._massageCompletions(types, members,
                dropSpecials=True)
            completions.sort(lambda a,b: cmp(a.upper(), b.upper()))

        elif completionType == "calltip-call-signature":
            if explicit:
                stylesToIgnore = []
            else:
                stylesToIgnore = self._noImplicitCompletionStyles
            expr = sciutils.getSimplifiedLeadingPythonExpr(
                offset, styledText,
                triggerPos-1,  # have to be before '('
                stylesToIgnore, styleMask)
            completions = self.codeIntelSvc.getCallTips("Python", path, line,
                expr, explicit, scopeFileId, scopeTable, scopeId, content)

        else:
            raise ValueError("cannot determine completion: unexpected "
                             "trigger type '%s'" % completionType)

        return completions

    def _dispatchCompletions(self, completionType, completions, triggerPos,
                             explicit, ciCompletionUIHandler):
        if completionType.startswith("autocomplete"):
            cstr = self.completionSeparator.join(completions)
            #XXX Might want to include relevant string info leading up to
            #    the trigger char so the Completion Stack can decide
            #    whether the completion info is still relevant.
            ciCompletionUIHandler.setAutoCompleteInfo(cstr, triggerPos)
        elif completionType.startswith("calltip"):
            calltip = completions[0]
            ciCompletionUIHandler.setCallTipInfo(calltip, triggerPos, explicit)
        else:
            raise ValueError("cannot dispatch completions: unexpected "
                             "completion type '%s'" % completionType)

    def _handleRequest(self, request):
        (path, line, completionType, offset, styledText, styleMask,
         triggerPos, scopeFileId, scopeTable, scopeId, content,
         ciCompletionUIHandler) = request
        log.debug("_handleRequest(path=%r, line=%r, '%s', offset=%d, "
                  "styledText, styleMask, triggerPos=%d)", path, line,
                  completionType, offset, triggerPos)
        completions = self._getCompletions(path, line, completionType, offset,
                                           styledText, styleMask, triggerPos,
                                           scopeFileId=scopeFileId,
                                           scopeTable=scopeTable,
                                           scopeId=scopeId,
                                           content=content)
        if completions:
            self._dispatchCompletions(completionType, completions,
                                      triggerPos, 0, ciCompletionUIHandler)

    def test_scimoz(self, scimoz):
        # Make sure we are initialized. We may not be if Code Intel
        # completion is not enabled.
        if not self._noImplicitCompletionStyles:
            contractID = "@activestate.com/koLanguage?language=Python;1"
            langSvc = components.classes[contractID].getService()
            self.initialize(langSvc)
        
        # Setup test cases. (unittest.py sucks: this is the only way to get
        # info to the tests)
        TriggerTestCase.cicSvc = self
        testCases = [TriggerTestCase]
        sciutils.runSciMozTests(testCases, scimoz)



#---- test suites
#
# Run via "Test | SciMoz Tests" in a Komodo dev build.
#

class CommenterTestCase(sciutils.SciMozTestCase):
    """Test Python auto-(un)commenting."""
    # Set in test_scimoz() driver to the koPythonLanguage instance.
    lang = None

    def test_simple(self):
        self.assertAutocommentResultsIn(self.lang,
            "foo<|>bar",
            "#foo<|>bar")
        self.assertAutouncommentResultsIn(self.lang,
            "#foo<|>bar",
            "foo<|>bar")

    def test_non_ascii_issues(self):
        self.assertAutocommentResultsIn(self.lang,
            u"foo \xe9 bar<|>",
            u"#foo \xe9 bar<|>")
        self.assertAutouncommentResultsIn(self.lang,
            u"#foo \xe9 bar<|>",
            u"foo \xe9 bar<|>")


class TriggerTestCase(sciutils.SciMozTestCase):
    """Test suite for getTriggerType() on the Python CodeIntel
    Completion Language Service
    """
    cicSvc = None

    def assertTriggerIs(self, buffer, expectedTriggerInfo):
        self._setupSciMoz(buffer, "Python")
        actualTriggerInfo = self.cicSvc.getTriggerType(self.scimoz)
        self.assertEqual(actualTriggerInfo, expectedTriggerInfo,
                         "unexpected trigger type for edit case: "
                         "expected %r, got %r, edit case %r"
                         % (expectedTriggerInfo, actualTriggerInfo, buffer))
    def assertTriggerIsNot(self, buffer, notExpectedTriggerInfo):
        self._setupSciMoz(buffer, "Python")
        actualTriggerInfo = self.cicSvc.getTriggerType(self.scimoz)
        self.assertNotEqual(actualTriggerInfo, notExpectedTriggerInfo,
                            "unexpected trigger type for edit case: "
                            "did not want %r but got it, edit case %r"
                            % (actualTriggerInfo, buffer))

    def test_autocomplete_object_members(self):
        self.assertTriggerIs("'FOO.<|>'", None)
        self.assertTriggerIs("FOO.<|>", "autocomplete-object-members")
        self.assertTriggerIs("FOO.BAR.<|>", "autocomplete-object-members")
        self.assertTriggerIs(".<|>", None)
        self.assertTriggerIs(r"FOO\\n  .<|>", "autocomplete-object-members")
        self.assertTriggerIs("FOO().BAR.<|>", "autocomplete-object-members")
        self.assertTriggerIs("FOO('blah').BAR.<|>", "autocomplete-object-members")
    #XXX Disabled for now.
    #def test_autocomplete_available_imports(self):
    #    self.assertTriggerIs("import <|>", "autocomplete-available-imports")
    #    self.assertTriggerIs("from <|>", "autocomplete-available-imports")
    #    self.assertTriggerIs("Ximport <|>", None)
    #    self.assertTriggerIs("Xfrom <|>", None)
    #    self.assertTriggerIsNot(r"from FOO\\n   import <|>", "autocomplete-available-imports")
    def test_calltip_call_signature(self):
        self.assertTriggerIs("FOO(<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO.BAR(<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO().BAR(<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO('blah').BAR(<|>", "calltip-call-signature")
        self.assertTriggerIs("def foo(<|>", None)
        self.assertTriggerIs("class Foo(<|>", None)
        self.assertTriggerIs("class Foo(bar(<|>", "calltip-call-signature")
#    def test_autocomplete_module_members(self):
#        self.assertTriggerIs("from FOO import <|>", "autocomplete-module-members")
#        self.assertTriggerIs("from FOO import BAR, <|>", "autocomplete-module-members")
#        self.assertTriggerIs("from FOO.BAZ import <|>", "autocomplete-module-members")
#        self.assertTriggerIs("from FOO.BAZ import BAR, <|>", "autocomplete-module-members")
#        self.assertTriggerIs(r"from FOO\\n   import <|>", "autocomplete-module-members")
#    def test_autocomplete_available_classes(self):
#        self.assertTriggerIs("class FOO(<|>", "autocomplete-available-classes")
#        self.assertTriggerIs("class FOO(BAR, <|>", "autocomplete-available-classes")
#    def test_calltip_base_signature(self):
#        self.assertTriggerIs("""
#class FOO(BAR):
#def BAZ(<|>
#""", "calltip-base-signature")




