#!python
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

# The implementation of the Komodo Run Command Service 

import os
import sys
import re
import tempfile
import threading
import process
import types
import urllib
import select
import logging

from xpcom import components, nsError, ServerException, COMException, _xpcom

import which
from koTreeView import TreeView
import koprocessutils
import runutils

from zope.cachedescriptors.property import Lazy as LazyProperty

#---- globals

log = logging.getLogger("run")
#log.setLevel(logging.DEBUG)

#---- run service components

class KoInterpolationQuery:
    _com_interfaces_ = components.interfaces.koIInterpolationQuery
    _reg_desc_ = "Interpolation Query"
    _reg_clsid_ = "{6F169CEE-D4E1-477f-9AFA-69E82D139714}"
    _reg_contractid_ = "@activestate.com/koInterpolationQuery;1"

    def __init__(self, id, code, question, mruName=None, answer=None,
                 necessary=0, isPassword=False):
        self.id = id
        self.code = code
        self.question = question
        self.mruName = mruName
        self.answer = answer
        # A query is "necessary" if (1) it comes from an "ask" or
        # "askpass" code or (2) it comes from an "orask" modifier for
        # which no value could be automatically determined.
        self.necessary = necessary
        self.isPassword = isPassword

    def __repr__(self):
        answer_str = (self.answer and (" %s" % self.answer) or "")
        return "<KoInterpolationQuery %r: %s?%s>" \
               % (self.id, self.question, answer_str)


#---- global regexes

_eol_re = re.compile(r'(?:\r?\n|\r)')
_eol_re_capture = re.compile(r'(\r?\n|\r)')
_last_eol_cr_re = re.compile(r'.*[\r\n]+', re.S)
_ws_re_capture = re.compile(r'([ \t]+)')


class KoInterpolationService:
    _com_interfaces_ = components.interfaces.koIInterpolationService
    _reg_desc_ = "Interpolation Service"
    _reg_clsid_ = "{C94C3130-A07E-4840-877B-E03D2F4BC872}"
    _reg_contractid_ = "@activestate.com/koInterpolationService;1"

    _codemapAdditions = {}

    @LazyProperty
    def lastErrorSvc(self):
        return components.classes["@activestate.com/koLastErrorService;1"]\
                         .getService(components.interfaces.koILastErrorService)
    @LazyProperty
    def _koDirSvc(self):
        return components.classes["@activestate.com/koDirs;1"].\
                getService(components.interfaces.koIDirs)
    @LazyProperty
    def _prefSvc(self):
        return components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService)
    @LazyProperty
    def _prefs(self):
        return self._prefSvc.prefs

    def _GetInterpreter(self, interp, lang, prefSet):
        """Return the full path to the given interpreter or raise a suitable
        ValueError.
        """
        appInfo = components.classes["@activestate.com/koAppInfoEx?app=%s;1" % (lang)]. \
                             getService(components.interfaces.koIAppInfoEx)
        exepath = appInfo.getExecutableFromPrefs(prefSet or self._prefSvc.effectivePrefs)
        if not exepath:
            raise ValueError("This command string includes '%%(%s)', but "\
                             "no '%s' interpreter could be found. You can "\
                             "configure this by visiting the %s "\
                             "preferences panel in Edit->Preferences."\
                             % (interp, interp, lang))
        else:
            return exepath

    def _getGuid(self):
        uuidGenerator = components.classes["@mozilla.org/uuid-generator;1"].getService(components.interfaces.nsIUUIDGenerator)
        guid = uuidGenerator.generateUUID()
        # must convert nsIDPtr to string first
        return str(guid)[1:-1] # strip off the {}'s

    def _getBrowser(self):
        browser = self._prefs.getStringPref('browser')
        errorMsg = ""
        if not browser:
            # XXX this may not be the best way to fix getting a default
            # browser, but we have no method for that if the pref
            # is not set
            koWebbrowser = components.classes['@activestate.com/koWebbrowser;1'].\
                       getService(components.interfaces.koIWebbrowser)
            try:
                browsers = koWebbrowser.get_possible_browsers()
            except Exception, ex:
                #TODO: I suspect this is a KeyError, but not sure.
                log.exception(ex)
                errorMsg = "The command string includes %(browser), but Komodo failed to find the list of installed browsers. You can configure a default browser in Komodo's 'Web' Preference panel. Go to 'Edit | Preferences'."
            else:
                if browsers:
                    # Check that we have a valid browser path
                    if os.path.exists(os.path.abspath(browsers[0])):
                        browser = browsers[0]
                    else:
                        errorMsg = "The command string includes %(browser), but the default browser is incorrectly set. Reset your default browser settings within your browser, or configure a default browser in Komodo's 'Web' Preference panel."
            if errorMsg or not browser:
                if not errorMsg:
                    errorMsg = "The command string includes %(browser), but there is no default browser set. You can configure a default browser in Komodo's 'Web' Preference panel. Go to 'Edit | Preferences'."
                raise ValueError(errorMsg)
        
        if ' ' in browser and browser[0] != '"':
            browser = '"%s"' % browser
        return browser
        
    def _getCodeMap(self, fileName=None, lineNum=None, word=None,
                    selection=None, projectFile=None, prefSet=None):
        # Define the interpolation mapping.
        #   This is a mapping from interpolation code to the replacement
        #   value in the command. The "replacement" may be one of the
        #   following:
        #      - None; '%<code>' is left as is
        #      - a string; replaces '%<code>' in the command
        #      - a ValueError; exception string will be passed back through
        #        XPCOM and displayed as an error to the user
        #      - a callable object which either returns None or a string, or
        #        raises a ValueError
        codeMap = {
            '%': '%',
            'b': ValueError("The command string includes %b, but there is no current file"),
            'f': ValueError("The command string includes %f, but there is no current file"),
            'F': ValueError("The command string includes %F, but there is no current file"),
            'd': ValueError("The command string includes %d, but there is no current file"),
            'D': ValueError("The command string includes %D, but there is no current file"),
            'L': ValueError("The command string includes %L, but there is no current file"),
            'w': ValueError("The command string includes %w, but there is no selection or word under cursor"),
            'W': ValueError("The command string includes %W, but there is no selection or word under cursor"),
            's': ValueError("The command string includes %s, but there is no selection"),
            'S': ValueError("The command string includes %S, but there is no selection"),
            'P': ValueError("The command string includes %P, but there is no active project"),
            'p': ValueError("The command string includes %p, but there is no active project"),
            'i': ValueError("The command string includes %i, but there is no active project"),
            'nodejs': lambda  interp='node',    lang='NodeJS':  self._GetInterpreter(interp, lang, prefSet),
            'perl':   lambda  interp='perl',    lang='Perl':    self._GetInterpreter(interp, lang, prefSet),
            'php':    lambda  interp='php',     lang='PHP':     self._GetInterpreter(interp, lang, prefSet),
            'python': lambda  interp='python',  lang='Python':  self._GetInterpreter(interp, lang, prefSet),
            'python3': lambda interp='python3', lang='Python3': self._GetInterpreter(interp, lang, prefSet),
# #if PLATFORM == 'win' or PLATFORM == 'darwin'
            'pythonw': lambda interp='pythonw', lang='Python':  self._GetInterpreter(interp, lang, prefSet),
# #endif
            'ruby':   lambda  interp='ruby',    lang='Ruby':    self._GetInterpreter(interp, lang, prefSet),
            'tclsh':  lambda  interp='tclsh',   lang='Tcl':     self._GetInterpreter(interp, lang, prefSet),
            'wish':   lambda  interp='wish',    lang='Tcl':     self._GetInterpreter(interp, lang, prefSet),
            'guid':   self._getGuid,
            'browser': self._getBrowser,

            # The code are handled specially in _doInterpolate1().
            'ask': None,
            'askpass': None,
            'date': None,
            'pref': None,
            'path': None,
            'debugger': None,
            }
        # Alternative Node.js aliases.
        codeMap['node'] = codeMap["nodejs"]
        codeMap['node.js'] = codeMap["nodejs"]
        from os.path import basename, dirname, splitext
        if fileName is not None:
            codeMap['b'] = splitext(basename(fileName))[0]
            codeMap['f'] = basename(fileName)
            codeMap['F'] = fileName
            codeMap['d'] = basename(dirname(fileName))
            codeMap['D'] = dirname(fileName)
        if lineNum > 0:
            codeMap['L'] = str(lineNum)
        if word:
            codeMap['w'] = word
            codeMap['W'] = word
        if projectFile:
            codeMap['P'] = projectFile
            codeMap['p'] = dirname(projectFile)
            partSvc = components.classes["@activestate.com/koPartService;1"]\
                      .getService(components.interfaces.koIPartService)
            project = partSvc.currentProject
            if project:
                codeMap['i'] = project.liveDirectory
        if selection:
            codeMap['w'] = selection
            codeMap['s'] = selection
            # urlib quote does not support unicode strings
            if isinstance(selection, unicode):
                try:
                    selection = selection.encode()
                except UnicodeEncodeError:
                    selection = selection.encode('utf-8')
            codeMap['S'] = urllib.quote_plus(selection)
            codeMap['W'] = urllib.quote_plus(selection)

        # Add extensible items:
        for code, handler in self._codemapAdditions.items():
            if code in codeMap:
                log.warn("overriding interpolation code %r", code)
            codeMap[code] = lambda: self._interpolationCallbackHandler(handler,
                                            code, fileName, lineNum, word,
                                            selection, projectFile, prefSet)

        return codeMap

    def addCode(self, code, callback):
        self._codemapAdditions[code] = callback

    def removeCode(self, code):
        self._codemapAdditions.pop(code, None)

    def _interpolationCallbackHandler(self, handler, code, fileName, lineNum,
                                      word, selection, projectFile, prefSet):
        try:
            result = handler.interpolationCallback(code, fileName, lineNum, word,
                                                   selection, projectFile, prefSet)
        except Exception as ex:
            result = "<%r ERROR: %s>" % (code, str(ex))
        return result

    special_modifiers = ("lowercase", "uppercase", "capitalize",
                         "dirname", "basename")

    def _getCodeRes(self, codeMap, bracketed):
        """Return a list of regular expressions suitable for parsing
        code blocks out of strings.
        
        Want a regex that will match things like the following:
            %s  %a  %S  %(S) %(perl) %(python:orask) %perl
            %(python:orask:Which Python)
            %(w:else:Spam and Eggs)
            %(ask:Search for) %(ask:Search for:default value) %ask
        or, iff "bracketed":
            [[%s]] [[%(perl)]] [[%ask:Search for]]
        """
        allCharCodes = [re.escape(k) for k in codeMap.keys()]
        # Ensure python3 is listed before python - bug 95070.
        if "python3" in allCharCodes:
            allCharCodes.remove("python3")
            allCharCodes.insert(0, "python3")

        # Break complex regexes into their named parts, and then reassemble below
        # Makes it more readable than dealing with large regexes, and reduces duplication.
        mainPart = r"""
            (?P<code>%s)            # the code
            (?P<backref>\d+)?       # an optional back ref num
            (:(?P<field1>[^:]*?)    # an optional field 1
                (:(?P<field2>.*?))? # an optional field 2
            )?
            (:(?P<modifier>%s))?    # special modifiers
        """ % ('|'.join(allCharCodes), '|'.join(self.special_modifiers))
        start_group = '%('   # percent character followed by an outer capture-group
        end_group = ')'
        start_paren = r'\('  # match an explicit paren
        end_paren = r'\)'
        codeReStrs = [
            # Parse codes _with_ parentheses:
            #   %(w), %(ask:Search for:default value)
            start_group + start_paren + mainPart + end_paren + end_group,
            # Parse codes _without_ parentheses:
            #   %w, %ask:Search:default
            start_group + mainPart + end_group,
        ]
        if bracketed:
            # Parse bracketed codes _with_ parentheses:
            #   [[%(w)]]  [[%(ask:Search for:default value)]]
            # Parse bracketed codes _without_ parentheses:
            #   [[%w]]  [[%ask:Search for:default value]]
            start_bracket = r'\[\[\s*'
            end_bracket = r'\s*\]\]'
            codeReStrs = [start_bracket + ptn + end_bracket for ptn in codeReStrs]
        return [re.compile(s, re.VERBOSE) for s in codeReStrs]

    def _doInterpolate1(self, s, codeMap, codeRes, prefSet, queries,
                        backrefs, indentReplacement=False):
        """Do the first step interpolation on string "s". Return the result
        and add queries to "queries".

        "s" is the string to interpolate.
        "codeMap" is a mapping of the interpolation codes to their
            replacement.
        "codeRes" is a list of regular expressions for parsing out
            interpolation code blocks.
        "prefSet" is a koIPreferenceSet instance used for processing
            %(pref) interpolation codes. It can be None to indicate that
            the global preference set should be used.
        "queries" is a list of existing KoInterpolationQuery objects
            from interpolation codes in previous strings in the same set
            of strings to interpolate. New queries from "s" should be
            appended to this list.
        "backrefs" is a dictionary of interp code back references. This
            dict a mapping from the code name and backref number to the
            value for that code. The value is either a replacement
            string or a KoInterpolationQuery id.
            {"w1": "foo",
             "guid1": "8BE89689-2A82-433b-9D88-726737ED2547",
             "ask1": "%(__query1__)"}
        
        A note on "queries": The list of queries is ultimately returned
        to the JavaScript code using this service to present a query dialog
        to the user. Queries can result from either the %(ask) code or
        the ":orask" modifier on any of the other codes. Normally the latter,
        ":orask", case will only result in a query if no value could be
        determined for the main code, e.g. %(F:orask) with no current file.
        However, we would like these orask's to _also_ generate a query even
        if a value was determined for them _iff_ some other code requires
        a query.
        """
        #print "_doInterpolate1(s=%r, codeMap, codeRes, prefSet, "\
        #      "queries=%r, backrefs=%r)" % (s, queries, backrefs)
        idx = 0
        i1s = ""  # the interpolated result
        while s and idx < len(s):
            # Find the _first_ match with the available regexes.
            # Otherwise "%(f)" is found first in "echo %f %(f)" and the
            # first "%f" is never matched.
            match = None
            for codeRe in codeRes:
                m = codeRe.search(s, idx)
                if m and (match is None or m.start() < match.start()):
                    match = m
            if match is None:
                #print "_doInterpolate1: %r did not match" % s[idx:]
                i1s += s[idx:] # tack on the remainder
                break
            #print "_doInterpolate1: %r matched: %r groups=%r"\
            #      % (s[idx:], s[match.start():match.end()], match.groupdict())

            i1s += s[idx:match.start()]

            # Value is the result of interpreting the interpolate code.
            value = ""
            # The meaning of "field1" and "field2" depends on the "code".
            hit = match.groupdict()
            code = hit["code"]
            modifier = hit["modifier"]
            field1 = hit["field1"]
            field2 = hit["field2"]
            if field1 in self.special_modifiers:
                modifier = field1
                field1 = None
            if field2 in self.special_modifiers:
                modifier = field2
                field2 = None
            defaultValue = ""
            defaultAnswer = ""
            question = ""
            if hit["backref"]:
                backref = code+hit["backref"]
            else:
                backref = None
            if code in ("ask", "askpass"):
                question = field1
                defaultAnswer = field2
            elif code == "date":
                format = field1
                if field2 is not None:
                    # Allow %(date:%H:%M:%S) to yield a format="%H:%M:%S".
                    format += ":"+field2
            elif code =="pref":
                prefName = field1
                defaultValue = field2
            elif code =="path":
                pathValue = field1
            elif code =="debugger":
                name = field1
            else:
                alternative = field1
                if alternative == "orask":
                    question = field2
                elif alternative == "else":
                    default = field2 or ""
                elif alternative is not None:
                    errmsg = "Unexpected alternative '%s' in '%s'"\
                             % (alternative, s[match.start():match.end()])
                    self.lastErrorSvc.setLastError(nsError.NS_ERROR_INVALID_ARG,
                                                errmsg)
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, errmsg)


            if backref and backref in backrefs:
                # This is a back-reference. Use the value of the
                # original reference.
                value = backrefs[backref]

            elif code in ("ask", "askpass"):
                # The "ask" code means that we will ask the user always.
                value = "%%(__query%d__)" % len(queries)
                if question:
                    mruName = str(question)
                else:
                    question = "Value %d" % len(queries)
                    mruName = "default"
                if code == "askpass":
                    mruName = None # never store passwords in an MRU

                # Interpolate the default answer. Only limitation is that
                # queries in the default answer are not allowed (i.e. no
                # %ask, %askpass or, "orask" modifier).
                if defaultAnswer and len(defaultAnswer) >= 2 \
                   and "%" in defaultAnswer:
                    answerCodeRes = self._getCodeRes(codeMap, False)
                    answerQueries = []
                    answerBackrefs = {}
                    iDefaultAnswer = self._doInterpolate1(
                        defaultAnswer, codeMap, answerCodeRes, prefSet,
                        answerQueries, answerBackrefs)
                    if not answerQueries: # Queries in query default not allowed.
                        defaultAnswer = iDefaultAnswer
                    
                    
                q = KoInterpolationQuery(id=value, code=code, question=question,
                                         mruName=mruName,
                                         answer=defaultAnswer,
                                         necessary=1,
                                         isPassword=(code == "askpass"))
                queries.append( q )
                
            elif code == "pref":
                if prefSet is None:
                    prefSet = self._prefSvc.effectivePrefs
                if prefSet.hasPref(prefName):
                    prefType = prefSet.getPrefType(prefName)
                    if prefType == "string":
                        value = prefSet.getStringPref(prefName)
                    elif prefType == "long":
                        value = '%d' % prefSet.getLongPref(prefName)
                    elif prefType == "double":
                        value = '%f' % prefSet.getDoublePref(prefName)
                    elif prefType == "boolean":
                        value = '%d' % prefSet.getBooleanPref(prefName)
                    else:
                        errmsg = "Unable to handle pref type '%s' for '%s'"\
                                 % (prefType, prefName)
                        self.lastErrorSvc.setLastError(nsError.NS_ERROR_INVALID_ARG,
                                                    errmsg)
                        raise ServerException(nsError.NS_ERROR_INVALID_ARG, errmsg)
                elif defaultValue:
                    value = defaultValue
                else:
                    errmsg = "Unable to get value for pref '%s'"\
                             % (prefName)
                    self.lastErrorSvc.setLastError(nsError.NS_ERROR_INVALID_ARG,
                                                errmsg)
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, errmsg)

            elif code == "path":
                if pathValue in ("userDataDir",
                                 "roamingUserDataDir",
                                 "commonDataDir",
                                 "userCacheDir",
                                 "supportDir",
                                 "sdkDir",
                                 "docDir",
                                 "installDir",
                                 "mozBinDir",
                                 "binDir",
                                 "komodoPythonLibDir",
                                 ):
                    value = getattr(self._koDirSvc, pathValue)
                else:
                    errmsg = "Unable to get path for '%s'"\
                             % (pathValue)
                    self.lastErrorSvc.setLastError(nsError.NS_ERROR_INVALID_ARG,
                                                errmsg)
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, errmsg)

            elif code == "date":
                import time
                if format is None:
                    format = self._prefs.getStringPref("defaultDateFormat")
                t = time.localtime(time.time())
                value = time.strftime(format, t)

            elif alternative == "orask":
                # The "orask" alternative means we only ask if no value in
                # the given context could be determined. We generate a
                # "query" in either case, but the query is only "necessary"
                # if no value could be determined.
                value = "%%(__query%d__)" % len(queries)
                if question:
                    mruName = str(question)
                else:
                    question = "Value %d" % len(queries)
                    mruName = "default"

                answer = codeMap[code]
                if callable(answer):
                    answer = answer()
                elif isinstance(answer, Exception):
                    answer = None
                necessary = answer is None

                q = KoInterpolationQuery(id=value, code=code, question=question,
                                         mruName=mruName, answer=answer,
                                         necessary=necessary,
                                         isPassword=False)
                queries.append( q )

            else:
                replacement = codeMap[code]
                if replacement is None:
                    if alternative == "else":
                        replacement = default
                    else:
                        replacement = s[match.start():match.end()]
                if callable(replacement):
                    replacement = replacement()
                elif isinstance(replacement, Exception):
                    if alternative == "else":
                        replacement = default
                    else:
                        raise replacement
                if indentReplacement:
                    value =  self._indentLines(replacement, s, match.start())
                else:
                    value = replacement

            idx = match.end()
            if backref:
                backrefs[backref] = value
            if modifier:
                if modifier == "lowercase":
                    value = value.lower()
                elif modifier == "uppercase":
                    value = value.upper()
                elif modifier == "capitalize":
                    value = value.capitalize()
                elif modifier == "dirname":
                    value = os.path.dirname(value)
                elif modifier == "basename":
                    value = os.path.basename(value)
            i1s += value
        return i1s

    def _indentLines(self, replacement, source, idx):
        """
        If we interpolate multiple lines into a context like
        if (test) {
            [[%s]]
        }
        then we need to make sure every line in the replacement of %s
        is indented, not just the first.
        
        Terminology: find the current indentation on the current line in *source*
        Apply it to every line but the first in *replacement*
        """
        m = _eol_re_capture.search(replacement)
        if m is None:
            # No newlines in the replacement, so nothing to do
            return replacement
        eol = m.group(1)

        # Replacement and source could have different eol's
        m = _last_eol_cr_re.match(source[:idx])
        if m is None:
            line_start = 0
        else:
            line_start = m.end()
        m = _ws_re_capture.match(source[line_start:idx])
        if m is None:
            # No leading white space on this line in the source
            return replacement
        ws = m.group(1)
        lines = re.split(_eol_re, replacement)
        lines = [lines[0]] + [ws + x for x in lines[1:]]
        return eol.join(lines)

    def Interpolate1(self, strings, bracketedStrings, fileName, lineNum, word, selection,
                     projectFile, prefSet):
        try:
            #print "Interpolate1(strings=%r, fileName=%r, lineNum=%r, word=%r, "\
            #      "selection=%r, projectFile, prefSet, bracketed=%r)"\
            #      % (strings, fileName, lineNum, word, selection, bracketed)
            codeMap = self._getCodeMap(fileName, lineNum, word, selection, projectFile, prefSet)
            codeRes = None
            bracketedCodeRes = None
            if strings:
                codeRes = self._getCodeRes(codeMap, 0)
            if bracketedStrings:
                bracketedCodeRes = self._getCodeRes(codeMap, 1)
    
            # Walk through the given strings replacing codes with their
            # values. Code blocks with one of the "ask" modifiers are tagged
            # and returned in the list of returned KoInterpolationQuery's.
            queries = []
            backrefs = {}
            try:
                i1strings = []
                for s in strings:
                    i1s = self._doInterpolate1(s, codeMap, codeRes, prefSet,
                                               queries, backrefs,
                                               indentReplacement=False)
                    i1strings.append(i1s)
                    i1strings.append(i1s) # see NOTE in koIRunService on doubling strings
                for s in bracketedStrings:
                    i1s = self._doInterpolate1(s, codeMap, bracketedCodeRes, prefSet,
                                               queries, backrefs,
                                               indentReplacement=True)
                    i1strings.append(i1s)
                    i1strings.append(i1s) # see NOTE in koIRunService on doubling strings
            except ValueError, ex:
                log.exception(ex)
                self.lastErrorSvc.setLastError(nsError.NS_ERROR_INVALID_ARG,
                                            ex.args[0])
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      ex.args[0])
    
            # If any queries are necessary then we pass them all back. If none
            # of them are necessary then we can interpolate them all and pass
            # none of them back.
            necessaryQueries = [q for q in queries if q.necessary]
            if necessaryQueries:
                return queries, i1strings
            else:
                i2strings = self.Interpolate2(i1strings, queries)
                return [], i2strings
        except Exception, e:
            log.exception(e)
            raise

    def Interpolate2(self, i1strings, queries):
        #print "Interpolate2(i1strings=%r, queries=%r)"\
        #      % (i1strings, queries)
        # Precondition: all queries have an answer.
        try:
            for q in queries: assert q.answer is not None
    
            i2strings = []
            for i1string in i1strings[0:len(i1strings):2]: # skip duplicates
                forUse = forDisplay = i1string
                for q in queries:
                    answer = q.answer
                    if q.code in ('S', 'W'):
                        # These are codes that are supposed to URL-escape selected
                        # values. Extend that same functionality to such values
                        # entered in the Interpolation Query dialog.
                        # urlib quote does not support unicode strings
                        if isinstance(answer, unicode):
                            try:
                                answer = answer.encode()
                            except UnicodeEncodeError:
                                answer = answer.encode('utf-8')
                        answer = urllib.quote_plus(answer)
                    forUse = forUse.replace(q.id, answer)
                    if q.isPassword:
                        forDisplay = forDisplay.replace(q.id, '*'*len(answer))
                    else:
                        forDisplay = forDisplay.replace(q.id, answer)
                i2strings += [forUse, forDisplay]
    
            return i2strings
        except Exception, e:
            log.exception(e)
            raise

    def GetBlockOffsets(self, s, bracketed):
        codeMap = self._getCodeMap()
        codeRes = self._getCodeRes(codeMap, bracketed)

        offsets = []
        idx = 0
        while idx < len(s):
            for codeRe in codeRes:
                match = codeRe.search(s, idx)
                if match:
                    offsets += [match.start(), match.end()]
                    break
            else:
                break # no more code blocks
            idx = match.end()

        #print "GetBlockOffsets(s=%r): %r" % (s, offsets)
        return offsets
        


class KoRunService:
    _com_interfaces_ = components.interfaces.koIRunService
    _reg_desc_ = "Run Service"
    _reg_clsid_ = "{8BE89689-2A82-433b-9D88-726737ED2547}"
    _reg_contractid_ = "@activestate.com/koRunService;1"

    def __init__(self):
        if sys.platform.startswith("win"):
            if os.environ.has_key("SHELL"):
                shell = os.environ["SHELL"]
            elif os.environ.has_key("ComSpec"):
                shell = os.environ["ComSpec"]
            else:
                #XXX Would be nice to get full path here so can use
                #    os.spawn* calls.
                shell = "command.com"
            shellArgs = ["/C"]
        elif sys.platform == "darwin":
            shell = "/bin/sh"
            shellArgs = []
        else:
            shell = "xterm"
            shellArgs = ["-e", "/bin/sh"]
        self.shellArgs = [shell] + shellArgs
            
    @LazyProperty
    def lastErrorSvc(self):
        return components.classes["@activestate.com/koLastErrorService;1"]\
                .getService(components.interfaces.koILastErrorService)
    @LazyProperty
    def _observerSvc(self):
        return components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)

    def Encode(self, command, cwd, env, insertOutput,
               operateOnSelection, doNotOpenOutputWindow, runIn,
               parseOutput, parseRegex, showParsedOutputList):
        """Encode the command (with all options) into a string.

        This will be displayed in the "Recent Commands" MRU so important
        information should be first. Plan:
            <command> <dict with options>
                - escape '{' and '}' in <command>
        """
        encoded = command.replace('{', '\\{')\
                         .replace('}', '\\}')
        # Add an option to the optdict if its value is other than the
        # default.
        optdict = {}
        if cwd:
            optdict['cwd'] = cwd
        if env:
            optdict['env'] = env
        if insertOutput:
            optdict['insertOutput'] = insertOutput
        if operateOnSelection:
            optdict['operateOnSelection'] = operateOnSelection
        if doNotOpenOutputWindow:
            optdict['doNotOpenOutputWindow'] = doNotOpenOutputWindow
        if runIn != 'command-output-window':
            optdict['runIn'] = runIn
        if parseOutput:
            optdict['parseOutput'] = parseOutput
        if parseRegex:
            optdict['parseRegex'] = parseRegex
        if showParsedOutputList:
            optdict['showParsedOutputList'] = showParsedOutputList
        if optdict:
            encoded += ' ' + repr(optdict)
        return encoded

    def Decode(self, encoded):
        """Decode an encoded command (see .Encode()).
        
        Want to support old encoding style (from Komodo 1.x) for
        backward compatibility.  From the old docs the form is:
           [<options letters] <command>
        Options letters are (these are the same as thier accesskeys in
        run.xul):
           i == insertOutput 
           l == operateOnSelection
        """
        optdict = { # defaults
            'cwd': '',
            'env': '',
            'insertOutput': 0,
            'operateOnSelection': 0,
            'doNotOpenOutputWindow': 0,
            'runIn': 'command-output-window',
            'parseOutput': 0,
            'parseRegex': '',
            'showParsedOutputList': 0,
        }

        # First see if this is possibly an old-style encoding.
        oldStyleRe = re.compile(
            "^\[(?P<insertOutput>i)?(?P<operateOnSelection>l)?\] "\
            "(?P<command>.*)$")
        match = oldStyleRe.match(encoded)
        if match:
            if match.group('insertOutput') is not None:
                optdict['insertOutput'] = 1
            if match.group('operateOnSelection') is not None:
                optdict['operateOnSelection'] = 1
            command = match.group('command')

        # New-style encoding
        else:
            parts = encoded.split(' {', 1)
            if len(parts) == 1:
                command = parts[0]
                optdictstr = '{}'
            else:
                command, optdictstr = parts
                optdictstr = '{' + optdictstr
            command = command.replace('\\{', '{')\
                             .replace('\\}', '}')
            try:
                optupdate = eval(optdictstr)
            except SyntaxError, ex:
                # This likely means that we are trying to decode an old
                # style encoded command as if it were a new-style
                # encoded command and the encoded command includes '{'
                # and/or '}' chars.
                command = encoded
            else:
                optdict.update(optupdate)

        return (command, optdict['cwd'], optdict['env'],
                optdict['insertOutput'], optdict['operateOnSelection'],
                optdict['doNotOpenOutputWindow'], optdict['runIn'],
                optdict['parseOutput'], optdict['parseRegex'],
                optdict['showParsedOutputList'])

    def _getEnvDictFromString(self, env):
        """Convert this:
            "VAR1=value1\nVAR2=value2\n..."
        to this:
            {"VAR1": "value1", "VAR2": "value2", ...}
        """
        envDict = {}
        for piece in env.split('\n'):
            if not piece: continue
            equalSign = piece.find('=')
            if equalSign == -1:
                log.warn("no '=' in env string line (skipping): %r" % piece)
                continue
            envDict[piece[:equalSign]] = piece[equalSign+1:]
        return envDict

    def _mergeEnvWithParent(self, envDict):
        """Merge the given environment variables with parent process' environ.

        Note: koIUserEnviron is used to avoid picking up the current
              Komodo process' environment changes from getting in the way.
        """
        userEnvSvc = components.classes["@activestate.com/koUserEnviron;1"].getService()
        userEnvDict = {}
        for piece in userEnvSvc.GetEnvironmentStrings():
            equalSign = piece.find('=')
            userEnvDict[piece[:equalSign]] = piece[equalSign+1:]
        userEnvDict.update(envDict)
        return userEnvDict

    def RunInTerminal(self, command, cwd, env, terminal, termListener,
                      input=None):
        """Run the given command connected to the given terminal.

        Optionally an "input" string can be provided. If it is then the
        terminal's stdin is *not* used. Instead the given input string
        is passed to the child and that pipe is closed.

        A termination listener, "termListener", can ge registered to
        receive notification when the child terminates and with what
        exit value.
        """
        #print "KoRunService.RunInTerminal(command=%r, cwd=%r, env=%r, "\
        #      "terminal=%r, termListener=%r, input=%r)"\
        #      % (command, cwd, env, terminal, termListener, input)
        if not cwd: # Allow cwd="".
            cwd = None
        if cwd and cwd.startswith('~'):
            cwd = os.path.expanduser(cwd)
        if not env:
            env = ""
        envDict = self._getEnvDictFromString(env)
        envDict = self._mergeEnvWithParent(envDict)
        # The process library requires that all env strings be ASCII
        # or all Unicode. We'll just make them all Unicode for now.
        #XXX This unicode conversion may not be necessary since
        #    _SaferCreateProcess in process.py.
        uEnvDict = {}
        for key, val in envDict.items():
            #XXX Linux may have trouble with all unicode env
            #    strings. Perhaps have all ASCII on Linux.
            uEnvDict[unicode(key)] = unicode(val)
        envDict = uEnvDict

        try:
            p = runutils.KoTerminalProcess(command, cwd=cwd, env=envDict)
        except process.ProcessError, ex:
            self.lastErrorSvc.setLastError(ex.errno, str(ex))
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))
        if terminal:
            p.linkIOWithTerminal(terminal)
        if input:
            p.write_stdin(input, closeAfterWriting=True)

        # If the user provides a termination listener (interface
        # koIRunTerminationListener), then the thread will notify
        # the termination of the child. A thread will be setup for
        # handling this even when there is no termListener, as we
        # have to ensure that the process does not get blocked on
        # stdout/stderr writes.
        p.waitAsynchronously(termListener)
        return p

    def _WaitAndCleanUp(self, child, command, scriptFileName=None,
                        inputFileName=None):
        # We use communicate to ensure the process does not block up on
        # a stdout/stderr channel.
        child.communicate()
        retval = child.wait()

        if scriptFileName:
            try:
                os.unlink(scriptFileName)
            except OSError, ex:
                log.warn("Could not remove temporary script file '%s': %s"\
                           % (scriptFileName, ex))
        if inputFileName:
            try:
                os.unlink(inputFileName)
            except OSError, ex:
                log.warn("Could not remove temporary input file '%s': %s"\
                           % (inputFileName, ex))
        
        # Put appropriate message on the status bar.
        sm = components.classes["@activestate.com/koStatusMessage;1"]\
                .createInstance(components.interfaces.koIStatusMessage)
        sm.category = "run_command"
        sm.msg = "'%s' returned %s." % (command, retval)
        sm.timeout = 3000
        if retval == 0:
            sm.highlight = 0
        else:
            sm.highlight = 1
        try:
            self.notifyObservers(sm, 'status_message', None)
        except COMException, e:
            # do nothing: Notify sometimes raises an exception if (???)
            # receivers are not registered?
            pass

    @components.ProxyToMainThreadAsync
    def notifyObservers(self, subject, topic, data):
        self._observerSvc.notifyObservers(subject, topic, data)

    def Run(self, command, cwd, env, console, input=None):
        """Run the command string in a new (console) window

        "console" is a boolean indicating whether the child should be
            spawned with a new console window or not.
        
        Optionally an "input" string can be provided. If it is then the
        command is run via "command < input", where the input is placed
        in a temporary file.
        """
        #print "KoRunService.Run(command=%r, cwd=%r, env=%r, "\
        #      "console=%r, input=%r)"\
        #      % (command, cwd, env, console, input)
        if not cwd: # Allow cwd="".
            cwd = None
        if cwd and cwd.startswith('~'):
            cwd = os.path.expanduser(cwd)
        if not env:
            env = ""
        envDict = self._getEnvDictFromString(env)
        envDict = self._mergeEnvWithParent(envDict)
        # The process library requires that all env strings be ASCII
        # or all Unicode. We'll just make them all Unicode for now.
        #XXX This unicode conversion may not be necessary since
        #    _SaferCreateProcess in process.py.
        uEnvDict = {}
        for key, val in envDict.items():
            uEnvDict[unicode(key)] = unicode(val)
        envDict = uEnvDict

        # Keep a pure 'command' for reporting status to the user.
        actualCommand = command

        if input:
            # Put the input into a temp file.
            inputFileName = tempfile.mktemp()
            inputFile = open(inputFileName, "w")
            inputFile.write(input)
            inputFile.close()
            if ' ' in inputFileName:
                actualCommand += ' < "%s"' % inputFileName
            else:
                actualCommand += ' < %s' % inputFileName
        else:
            inputFileName = None

        if console:
            scriptFileName = runutils.createConsoleLaunchScript(actualCommand, cwd, envDict)
            actualCommand = self.shellArgs + [scriptFileName]
            
            #print "RUN: actualCommand is '%s'" % actualCommand
            #print "RUN: -------- %s is as follows -------" % scriptFileName
            #fin = open(scriptFileName, 'r')
            #for line in fin.readlines():
            #    print line,
            #fin.close()
            #print "RUN: ---------------------------------"
            child = process.ProcessOpen(actualCommand, cwd=cwd, env=envDict,
                                        flags=process.CREATE_NEW_CONSOLE,
                                        # Leave the handles alone, it's external
                                        stdin=None, stdout=None, stderr=None)
        else:
            scriptFileName = None
            child = process.ProcessOpen(actualCommand, cwd=cwd, env=envDict,
                                        flags=None, stdin=None)
        # The return value is passed to the status bar when the child
        # terminates. A separate thread is created to handle that so
        # this call can return immediately.
        t = threading.Thread(target=self._WaitAndCleanUp,
                             kwargs={'child': child,
                                     'command': command,
                                     'scriptFileName': scriptFileName,
                                     'inputFileName': inputFileName})
        t.setDaemon(True)
        t.start()

    def RunAndCaptureOutput(self, command, cwd, env, input=None):
        """Run the command and return the output.

        Optionally an "input" string can be provided. If it is then
        the given input string is passed to the child and that pipe is
        closed.
        """
        #print "KoRunService.RunAndCaptureOutput(command=%r, cwd=%r, "\
        #      "env=%r, input=%r)" % (command, cwd, env, input)
        if not cwd: # Allow cwd="".
            cwd = None
        if cwd and cwd.startswith('~'):
            cwd = os.path.expanduser(cwd)
        if not env:
            env = ""
        envDict = self._getEnvDictFromString(env)
        envDict = self._mergeEnvWithParent(envDict)
        # The process library requires that all env strings be ASCII
        # or all Unicode. We'll just make them all Unicode for now.
        #XXX This unicode conversion may not be necessary since
        #    _SaferCreateProcess in process.py.
        uEnvDict = {}
        for key, val in envDict.items():
            uEnvDict[unicode(key)] = unicode(val)
        envDict = uEnvDict

        try:
            child = process.ProcessOpen(command, cwd=cwd, env=envDict)
            output, error = child.communicate(input)
            return (child.returncode, output, error)
        except process.ProcessError, ex:
            self.lastErrorSvc.setLastError(ex.errno, str(ex))
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

    def _WaitAndNotify(self, child, command, input):
        child.communicate(input)

        # Notify any listener of child termination.
        try:
            #XXX Dunno if need to pass 'child' in the notification here.
            self.notifyObservers(child, 'run_terminated', command)
        except COMException, e:
            # Do nothing: Notify sometimes raises an exception if (???)
            # no receiver are registered?
            pass

    def RunAndNotify(self, command, cwd, env, input=None):
        """Run the given command, returning the process object
        immediately, and notify (via nsIObserver) when the process
        terminates.
        """
        #print "KoRunService.RunAndNotify(command=%r, cwd=%r, "\
        #      "env=%r, input=%r)" % (command, cwd, env, input)
        if not cwd: # Allow cwd="".
            cwd = None
        if cwd and cwd.startswith('~'):
            cwd = os.path.expanduser(cwd)
        if not env:
            env = ""
        envDict = self._getEnvDictFromString(env)
        envDict = self._mergeEnvWithParent(envDict)
        # The process library requires that all env strings be ASCII
        # or all Unicode. We'll just make them all Unicode for now.
        #XXX This unicode conversion may not be necessary since
        #    _SaferCreateProcess in process.py.
        uEnvDict = {}
        for key, val in envDict.items():
            uEnvDict[unicode(key)] = unicode(val)
        envDict = uEnvDict

        try:
            child = runutils.KoRunProcess(command, cwd=cwd, env=envDict)
        except process.ProcessError, ex:
            self.lastErrorSvc.setLastError(ex.errno, str(ex))
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

        t = threading.Thread(target=self._WaitAndNotify,
                             kwargs={'child': child,
                                     'command': command,
                                     'input': input})
        t.setDaemon(True)
        t.start()
        return child

    def _WaitAndCallback(self, child, command, callbackHandler, thread, input):
        stdout, stderr = child.communicate(input)
        returncode = child.wait()

        # Notify callback of process termination.
        if callbackHandler is not None:
            class CallbackRunnable(object):
                """Used to fire callback on the original thread."""
                _com_interfaces_ = [components.interfaces.nsIRunnable]
                def __init__(self, handler, command, returncode, stdout, stderr):
                    self.handler = handler
                    self.args = (command, returncode, stdout, stderr)
                    self.result = None
                def run(self, *args):
                    self.result = self.handler.callback(*self.args)
                    # Null out values.
                    self.handler = None
                    self.args = None
            threadMgr = components.classes["@mozilla.org/thread-manager;1"]\
                            .getService(components.interfaces.nsIThreadManager)
            runnable = CallbackRunnable(callbackHandler, command, returncode, stdout, stderr)
            try:
                thread.dispatch(runnable, components.interfaces.nsIThread.DISPATCH_SYNC)
            except COMException, e:
                log.warn("RunAsync: callback failed: %s, command %r",
                         str(e), command)

    def RunAsync(self, command, callbackHandler=None, cwd=None, env=None, input=None):
        """Run the given command, returning the process object immediately, and
        later call the callback object when the process terminates.
        """
        #print "KoRunService.RunAsync(command=%r, callback=%r, cwd=%r, "\
        #      "env=%r, input=%r)" % (command, callback, cwd, env, input)
        if not cwd: # Allow cwd="".
            cwd = None
        elif cwd.startswith('~'):
            cwd = os.path.expanduser(cwd)
        if not env:
            env = ""
        envDict = self._getEnvDictFromString(env)
        envDict = self._mergeEnvWithParent(envDict)
        # The process library requires that all env strings be ASCII
        # or all Unicode. We'll just make them all Unicode for now.
        #XXX This unicode conversion may not be necessary since
        #    _SaferCreateProcess in process.py.
        uEnvDict = {}
        for key, val in envDict.items():
            uEnvDict[unicode(key)] = unicode(val)
        envDict = uEnvDict

        try:
            child = runutils.KoRunProcess(command, cwd=cwd, env=envDict)
        except process.ProcessError, ex:
            self.lastErrorSvc.setLastError(ex.errno, str(ex))
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

        threadMgr = components.classes["@mozilla.org/thread-manager;1"]\
                        .getService(components.interfaces.nsIThreadManager)
        t = threading.Thread(target=self._WaitAndCallback,
                             kwargs={'child': child,
                                     'command': command,
                                     'callbackHandler': callbackHandler,
                                     'thread': threadMgr.currentThread,
                                     'input': input})
        t.setDaemon(True)
        t.start()
        return child


class KoRunEnvView(TreeView):
    _com_interfaces_ = [components.interfaces.koIRunEnvView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{0E3559E7-093D-47d1-ABC6-717FADB0D6C8}"
    _reg_contractid_ = "@activestate.com/koRunEnvView;1"
    _reg_desc_ = "Komodo Run Command Environment Variables Tree View"

    def __init__(self):
        TreeView.__init__(self, debug=0)
        self._data = {}
        # A list of the current variable names (i.e. self._data.keys())
        # giving the order in the table.
        self._order = []
        # A string key indicating by which column the env table is
        # sorted.
        self._sortedBy = None

    def get_rowCount(self):
        return len(self._data.keys())

    def getCellText(self, row, column):
        """Get the value for the specified cell.
        "row" is an index into the current order (self._order).
        "col" is an 'id' of the <treecol> element. Here
            "env-variable" or "env-value".
        """
        try:
            variable = self._order[row]
        except IndexError:
            log.error("no %sth row of data" % row)
            return ""

        cell = None
        if column.id == "env-variable":
            cell = variable
        elif column.id == "env-value":
            cell = self._data[variable]
        else:
            log.error("unknown run environment variables column id: '%s'" % column.id)
            return ""

        if type(cell) not in (types.StringType, types.UnicodeType):
            cell = str(cell)
        return cell

    def Set(self, variable, value):
        if sys.platform.startswith("win"):
            variable = variable.upper()
        self._tree.beginUpdateBatch()
        if not self._data.has_key(variable):
            self._order.append(variable)
            self._sortedBy = None
            self._tree.rowCountChanged(len(self._data)-2, 1)
        self._data[variable] = value
        self._tree.invalidate()  #XXX invalidating too much here?
        self._tree.endUpdateBatch()

    def Delete(self, index):
        del self._data[self._order[index]]
        del self._order[index]
        self._tree.beginUpdateBatch()
        self._tree.invalidate()  #XXX invalidating too much here?
        self._tree.endUpdateBatch()

    def Have(self, variable):
        """Return true iff have a datum with the given variable name."""
        if sys.platform.startswith("win"):
            variable = variable.upper()
        return self._data.has_key(variable)

    def Index(self, variable):
        if sys.platform.startswith("win"):
            variable = variable.upper()
        try:
            return self._order.index(variable)
        except ValueError:
            return -1

    def GetVariable(self, index):
        return self._order[index]
    def GetValue(self, index):
        return self._data[self._order[index]]

    def Sort(self, sortBy):
        """Sort the current data by the given key. If already sorted by this
        key then reverse the sorting order."""
        if self._sortedBy == sortBy:
            self._order.reverse()
        else:
            if sortBy == 'env-variable':
                self._order.sort()
            elif sortBy == 'env-value':
                self._order.sort(lambda a,b,data=self._data,sortBy=sortBy:
                                    cmp(data[a], data[b])
                                )
            else:
                log.error("Cannot sort results by: '%s'" % sortBy)
                return
        self._sortedBy = sortBy
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def GetEnvironmentStrings(self):
        vars = ["%s=%s" % item for item in self._data.items()]
        return "\n".join(vars)

    def SetEnvironmentStrings(self, s):
        self._data = {}
        for envvar in s.split('\n'):
            if envvar: # skip empty lines
                var, val = envvar.split('=', 1)
                self._data[var] = val
        self._order = self._data.keys()
        self._sortedBy = None
        if self._tree:
            self._tree.beginUpdateBatch()
            self._tree.invalidate()
            self._tree.endUpdateBatch()

