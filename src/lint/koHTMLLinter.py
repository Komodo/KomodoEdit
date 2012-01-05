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


from xpcom import components, ServerException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import UnwrapObject
from koLintResult import KoLintResult, getProxiedEffectivePrefs
from koLintResults import koLintResults
from xpcom.server.enumerator import *
import os, sys, re
import StringIO  # Do not use cStringIO!  See html5 class for an explanation
import eollib
import html5lib
from html5lib.constants import E as html5libErrorDict
import process

import logging
logging.basicConfig()
log = logging.getLogger("KoHTMLLinter")
#log.setLevel(logging.DEBUG)

#---- component implementation

class _CommonHTMLLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    
    def __init__(self):
        self._koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._lintersByLangName = {
            "CSS": self._koLintService.getLinterForLanguage("CSS"),
            "JavaScript": self._koLintService.getLinterForLanguage("JavaScript"),
            }
     
    _nonNewlineMatcher = re.compile(r'[^\r\n]')
    def _spaceOutNonNewlines(self, markup):
        return self._nonNewlineMatcher.sub(' ', markup)
        
    def _linterByName(self, langName, currentLinters):
        if langName in currentLinters:
            return currentLinters[langName]
        if langName not in self._lintersByLangName:
            try:
                linter = self._koLintService.getLinterForLanguage(langName)
                self._lintersByLangName[langName] = linter
            except:
                log.error("No linter for language %s", langName)
                linter = None
            self._lintersByLangName[langName] = linter
            currentLinters[langName] = linter
        return self._lintersByLangName[langName]

    def _getMappedName(self, name):
        return self._mappedNames and self._mappedNames.get(name, name) or name

    def _blankOutOneLiners(self, code):
        if "\n" in code.strip():
            return code
        return self._spaceOutNonNewlines(code)

    # Allow script and style tags to be wrapped with one of
    # <![CDATA[ ... ]]> or <!-- .. -->
    # Allow for bits of template code inside a style or script tag as well.

    _leading_ignorables_re = re.compile(r'\A((?:<!\[CDATA\[|<!--|\s+)*)(.*?)((?:\]\]>|-->|\s+)*)\Z', re.DOTALL)
    _non_ws_re = re.compile('\\S')

    def _get_unwrappedText(self, currText, koDoc, i, startPt, endPt, lim):
        parts = list(self._leading_ignorables_re.match(currText).groups())
        if (self._non_ws_re.search(parts[0])
            and i > 0
            and koDoc.languageForPosition(startPt - 1).startswith("HTML")):
            parts[0] = self._spaceOutNonNewlines(parts[0])
        if (self._non_ws_re.search(parts[2])
            and (i == lim - 1
                 or (i < lim - 1
                     and koDoc.languageForPosition(endPt).startswith("HTML")))):
            parts[2] = self._spaceOutNonNewlines(parts[2])
        return parts

    _return_re = re.compile(r'\breturn\b')
    _function_re = re.compile(r'\bfunction\b')
    _doctype_re = re.compile("<!doctype\s+html\s*?(.*?)\s*>",
                             re.IGNORECASE|re.DOTALL)
    def _lint_common_html_request(self, request, udlMapping=None, linters=None,
                                  squelchTPLPatterns=None,
                                  startCheck=None):
        self._mappedNames = udlMapping
        lintersByName = {}
        # Copy working set of linters into a local var
        lintersByName.update(self._lintersByLangName)
        if linters:
            lintersByName.update(linters)
        koDoc = request.koDoc  # koDoc is a proxied object
        koDoc_language = koDoc.language
        jsShouldBeWrapped = koDoc_language == "XBL"
        jsWrapOneLiners = koDoc_language in ("HTML", "HTML5", "XUL")
        transitionPoints = koDoc.getLanguageTransitionPoints(0, koDoc.bufferLength)
        languageNamesAtTransitionPoints = [koDoc.languageForPosition(pt)
                                           for pt in transitionPoints[:-2]]
        if not languageNamesAtTransitionPoints:
            languageNamesAtTransitionPoints = [koDoc.languageForPosition(0)]
        # We need to lint the utf-8 representation to keep coordinates
        # in sync with Scintilla
        # request.content contains a Unicode representation, even if the
        # buffer's encoding is utf-8 -- content is an AString
        textAsBytes = request.content.encode("utf-8")
        uniqueLanguageNames = dict([(k, None) for k in languageNamesAtTransitionPoints])
        if udlMapping:
            for targetName in udlMapping.values():
                try:
                    uniqueLanguageNames[targetName] = []
                except TypeError:
                    log.debug("udlMapping:%s, targetName:%r", udlMapping, targetName)
        uniqueLanguageNames = uniqueLanguageNames.keys()
        #log.debug("transitionPoints:%s", transitionPoints)
        #log.debug("uniqueLanguageNames:%s", uniqueLanguageNames)
        bytesByLang = dict([(k, []) for k in uniqueLanguageNames])
        lim = len(transitionPoints)
        endPt = 0
        htmlAllowedNames = ("HTML", "HTML5", "CSS", "JavaScript", "XML")
        currStartTag = None
        squelching = False
        firstInsertedReplacement = False
        prevSegmentLangName = "HTML"
        for i in range(1, lim):
            startPt = endPt
            endPt = transitionPoints[i]
            if startPt == endPt:
                continue
            currText = textAsBytes[startPt:endPt]
            origLangName = koDoc.languageForPosition(startPt)
            langName = self._getMappedName(origLangName)
            #log.debug("segment: raw lang name: %s, lang:%s, %d:%d [[%s]]",
            #          koDoc.languageForPosition(startPt),
            #          langName, startPt, endPt, currText)
            for name in bytesByLang.keys():
                if squelchTPLPatterns and origLangName == squelchTPLPatterns[0]:
                    if not squelching and squelchTPLPatterns[1].match(currText):
                        squelching = True
                        firstInsertedReplacement = False
                    elif squelching and squelchTPLPatterns[2].match(currText):
                        squelching = False
                elif squelching and prevSegmentLangName == "JavaScript":
                    # If we have something like
                    # var jsvar = <%= value %>
                    # pull out the atomic server-side code, and insert
                    # something that looks good to the js linter.
                    if not firstInsertedReplacement:
                        firstInsertedReplacement = True
                        # Give JS etc. something to work with.
                        # This might cause other false positives though.
                        replText = "0" + self._spaceOutNonNewlines(currText[1:])
                    else:
                        replText = self._spaceOutNonNewlines(currText)
                    bytesByLang[name].append(replText)
                elif origLangName == "CSS" and langName == name:
                    subparts = self._get_unwrappedText(currText, koDoc, i, startPt, endPt, lim)
                    if ("{" not in subparts[1]
                        and i > 0
                        and i < lim - 1
                        and koDoc.languageForPosition(startPt - 1).startswith("HTML")
                        and koDoc.languageForPosition(endPt).startswith("HTML")):
                        # This won't pick up things like
                        # <tag style="margin <?php echo ':' ?> 1px;">
                        bytesByLang[name].append("bogusTag { %s }" % subparts[1])
                        #TODO:  Adjust the amount of whitespace to minimize
                        # the displacement of the actual CSS code.
                    else:
                        bytesByLang[name].append("".join(subparts))
                elif origLangName == "JavaScript" and langName == name:
                    # Convert uncommented cdata marked section markers
                    # into spaces.
                    #
                    subparts = self._get_unwrappedText(currText, koDoc, i, startPt, endPt, lim)
                    bytesByLang[name].append(subparts[0])
                    if jsShouldBeWrapped:
                        actualCode = self._blankOutOneLiners(subparts[1])
                        thisJSShouldBeWrapped = actualCode.strip()
                    else:
                        actualCode = subparts[1]
                        thisJSShouldBeWrapped = \
                            (jsWrapOneLiners
                             and "\n" not in subparts[1]
                             and self._return_re.search(subparts[1])
                             and not self._function_re.search(subparts[1]))
                            # heuristic, wrap on-handlers in html*
                    if thisJSShouldBeWrapped:
                        bytesByLang[name].append("(function() { ")
                    bytesByLang[name].append(actualCode)
                    
                    if thisJSShouldBeWrapped:
                        bytesByLang[name].append(" })();")
                    bytesByLang[name].append(subparts[2])
                elif (name == langName
                    or ((name.startswith("HTML") or name == "XML")
                        and langName in htmlAllowedNames)):
                    bytesByLang[name].append(currText)
                else:
                    bytesByLang[name].append(self._spaceOutNonNewlines(currText))
            if origLangName in ("JavaScript", "HTML", "HTML5", "XML"):
                prevSegmentLangName = origLangName
        
        for name in bytesByLang.keys():
            bytesByLang[name] = "".join(bytesByLang[name]).rstrip()
            #log.debug("Lint doc(%s):[\n%s\n]", name, bytesByLang[name])

        python_encoding_name = request.encoding.python_encoding_name
        if python_encoding_name not in ('ascii', 'utf-8'):
            charsByLang = {}
            for name, byteSubset in bytesByLang.items():
                try:
                    charsByLang[name] = byteSubset.decode("utf-8").encode(python_encoding_name)
                except:
                    log.exception("Can't encode into encoding %s", python_encoding_name)
                    charsByLang[name] = byteSubset
        else:
            charsByLang = bytesByLang

        lintResultsByLangName = {}
        for langName, textSubset in charsByLang.items():
            if startCheck and langName in startCheck:
                startPtn, insertion = startCheck[langName]
                if not startPtn.match(textSubset):
                    textSubset = insertion + textSubset
            if langName.startswith("HTML"):
                # Is there an explicit doctype?
                m = self._doctype_re.match(textSubset)
                if m:
                    if not m.group(1):
                        langName = "HTML5"
                    else:
                        langName = "HTML"
                elif langName == "HTML" and self.lang == "HTML5":
                    # Use the correct aggregator class.
                    langName = "HTML5"
                elif koDoc_language not in ("HTML", "HTML5"):
                    # For HTML markup langs and templating langs, use the
                    # default HTML decl to see if they want HTML5 - bug 88884.
                    prefset = getProxiedEffectivePrefs(request)
                    if "HTML 5" in prefset.getStringPref("defaultHTMLDecl"):
                        langName = "HTML5"
            linter = self._linterByName(langName, lintersByName)
            if linter:
                try:
                    # UnwrapObject so we don't run the textSubset text
                    # through another xpcom decoder/encoder
                    newLintResults = UnwrapObject(linter).lint_with_text(request, textSubset)
                    if newLintResults and newLintResults.getNumResults():
                        lintResultSet = lintResultsByLangName.get(langName)
                        if lintResultSet:
                           lintResultSet.addResults(newLintResults)
                        else:
                            lintResultsByLangName[langName] = newLintResults
                except AttributeError:
                    log.exception("No lint_with_text method for linter for language %s", langName)
            else:
                pass
                #log.debug("no linter for %s", langName)
        # If we get results from more than one language, tag each one
        numLintResultSets = len(lintResultsByLangName.keys())
        if numLintResultSets == 0:
            return koLintResults()
        elif numLintResultSets == 1:
            return lintResultsByLangName.values()[0]
        else:
            finalLintResults = koLintResults()
            for langName, lintResultSet in lintResultsByLangName.items():
                for lintResult in lintResultSet.getResults():
                    lintResult.description = langName + ": " + lintResult.description
                finalLintResults.addResults(lintResultSet)
            return finalLintResults            

class _Common_HTMLAggregator(_CommonHTMLLinter):
    def __init__(self):
        _CommonHTMLLinter.__init__(self)
        self._koLintService_UW = UnwrapObject(self._koLintService)

    # Do all the language-separation in the aggregator.  Then each HTML
    # terminal linter will concern itself only with the full document,
    # and won't have to pick out sublanguages.
    def lint(self, request, udlMapping=None, linters=None,
             squelchTPLPatterns=None,
             startCheck=None):
        return self._lint_common_html_request(request, udlMapping, linters,
                                              squelchTPLPatterns, startCheck)

    def lint_with_text(self, request, text):
        if not text:
            #log.debug("no text")
            return
        # Your basic aggregator....
        linters = self._koLintService_UW.getTerminalLintersForLanguage(self.lang)
        finalLintResults = koLintResults()
        for linter in linters:
            newLintResults = UnwrapObject(linter).lint_with_text(request, text)
            if newLintResults and newLintResults.getNumResults():
                if finalLintResults.getNumResults():
                    finalLintResults = finalLintResults.addResults(newLintResults)
                else:
                    finalLintResults = newLintResults
        return finalLintResults

class KoHTMLCompileLinter(_Common_HTMLAggregator):
    _reg_desc_ = "Komodo HTML Aggregate Linter"
    _reg_clsid_ = "{DBF1E5E0-91C7-43da-870B-DB1859017102}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Aggregator;1"
    _reg_categories_ = [
         ("category-komodo-linter-aggregator", 'HTML'),
         ]
    lang = "HTML"

class KoHTML5CompileLinter(_Common_HTMLAggregator):
    _reg_desc_ = "Komodo HTML5 Aggregate Linter"
    _reg_clsid_ = "{06828f1d-7d2d-4cf7-8ed0-4d9259b875f0}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML5&type=Aggregator;1"
    _reg_categories_ = [
         ("category-komodo-linter-aggregator", 'HTML5'),
         ]

    lang = "HTML5"
        

class CommonTidyLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]

    def lint_with_text(self, request, text):
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref("lintHTMLTidy"):
            return
        cwd = request.cwd

        text = eollib.convertToEOLFormat(text, eollib.EOL_LF)
        datalines = text.split('\n')

        # get the tidy config file
        configFile = prefset.getStringPref('tidy_configpath')
        if configFile and not os.path.exists(configFile):
            log.debug("The Tidy configuration file does not exist, please "
                     "correct your settings in the preferences for HTML.")
            configFile = None
            
        errorLevel = prefset.getStringPref('tidy_errorlevel')
        accessibility = prefset.getStringPref('tidy_accessibility')
        
        #Character encodings
        #-------------------
        #  -raw              to output values above 127 without conversion to entities
        #  -ascii            to use US-ASCII for output, ISO-8859-1 for input
        #  -latin1           to use ISO-8859-1 for both input and output
        #  -iso2022          to use ISO-2022 for both input and output
        #  -utf8             to use UTF-8 for both input and output
        #  -mac              to use MacRoman for input, US-ASCII for output
        #  -win1252          to use Windows-1252 for input, US-ASCII for output
        enc = '-raw'
        if request.encoding.python_encoding_name == 'utf-8':
            enc = '-utf8'
        elif request.encoding.python_encoding_name == 'latin-1' or \
             request.encoding.python_encoding_name.startswith('iso8859'):
            enc = '-latin1'
        elif request.encoding.python_encoding_name == 'cp1252':
            enc = '-win1252'
            
        koDirs = components.classes["@activestate.com/koDirs;1"].\
                      getService(components.interfaces.koIDirs)
        argv = [os.path.join(koDirs.supportDir, "html", "tidy"),
                '-errors', '-quiet', enc, '--show-errors', '100']
        argv += getattr(self, "html5_tidy_argv_additions", [])

        if accessibility != '0':
            argv += ['-access', accessibility]
        if configFile:
            argv += ['-config', configFile]
        
        cwd = cwd or None
        # Ignore stdout, as tidy dumps a cleaned up version of the input
        # file on it, which we don't care about.
        #log.debug("Running tidy argv: %r", argv)
        #print ("Running tidy argv: %s" % (" ".join(argv)))
        p = process.ProcessOpen(argv, cwd=cwd)
        stdout, stderr = p.communicate(text)
        lines = stderr.splitlines(1)

        # Tidy stderr output looks like this:
        #    Tidy (vers 4th August 2000) Parsing console input (stdin)
        #    line 12 column 1 - Error: <body> missing '>' for end of tag
        #    line 14 column 2 - Warning: <tr> isn't allowed in <body> elements
        # <snip>
        #    line 674 column 5 - Warning: <img> lacks "alt" attribute
        #    
        #    stdin: Doctype given is "-//W3C//DTD HTML 4.0 Transitional//EN"
        #    stdin: Document content looks like HTML 4.01 Transitional
        #    41 warnings/errors were found!
        #    
        #    This document has errors that must be fixed before
        #    using HTML Tidy to generate a tidied up version.
        #    
        #    The table summary attribute should be used to describe
        # <snip ...useful suggestion paragraph that we should consider using>
        # Quickly strip out uninteresting lines.
        lines = [l for l in lines if l.startswith('line ')]
        lines = self.filterLines(lines)
        results = koLintResults()
        resultRe = re.compile("""^
            line\s(?P<line>\d+)
            \scolumn\s(?P<column>\d+)
            \s-\s(?P<desc>.*)$""", re.VERBOSE)
        for line in lines:
            if enc == '-utf8':
                line = unicode(line,'utf-8')
            resultMatch = resultRe.search(line)
            if not resultMatch:
                log.warn("Could not parse tidy output line: %r", line)
                continue

            #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
            try:
                lineStart = int(resultMatch.group("line"))
                columnStart = int(resultMatch.group("column"))
            except ValueError:
                # Tidy sometimes spits out an invalid line (don't know why).
                # This catches those lines, and ignores them.
                continue

            description = resultMatch.group("desc")
            # We keep the "Error:"/"Warning:" on the description because
            # currently we do not get green squigglies for warnings.
            if description.startswith("Error:"):
                severity = KoLintResult.SEV_ERROR
            elif description.startswith("Warning:") or \
                 description.startswith("Access:"):
                if errorLevel == 'errors':
                    # ignore warnings
                    continue
                severity = KoLintResult.SEV_WARNING
            elif description.startswith("Info:"):
                # Ignore Info: lines.
                continue
            else:
                severity = KoLintResult.SEV_ERROR

            # Set the end of the lint result to the '>' closing the tag.
            i = lineStart
            columnEnd = -1
            while i < len(datalines):
                # first pass -- go to first >, even if in attribute name
                if i == lineStart:
                    curLine = datalines[i-1][columnStart:]
                    offset = columnStart
                else:
                    curLine = datalines[i-1]
                    offset = 0
                end = curLine.find('>')
                if end != -1:
                    columnEnd = end + offset + 2
                    break
                i = i + 1
            if columnEnd == -1:
                columnEnd=len(datalines[i-1]) + 1
            lineEnd = i
            
            # Move back to the first non-blank line for errors
            # that appear on blank lines.  In empty and
            # near-empty buffers this result will end up at
            # the first line (which is 1-based in the lint system)
            if lineStart == lineEnd and \
               columnEnd <= columnStart:
                while lineStart > 0 and len(datalines[lineStart - 1]) == 0:
                    lineStart -= 1
                if lineStart == 0:
                    lineStart = 1
                lineEnd = lineStart
                columnStart = 1
                columnEnd = len(datalines[lineStart-1]) + 1

            result = KoLintResult(description=description,
                                  severity=severity,
                                  lineStart=lineStart,
                                  lineEnd=lineEnd,
                                  columnStart=columnStart,
                                  columnEnd=columnEnd)

            results.addResult(result)
        return results
    

class KoHTMLTidyLinter(CommonTidyLinter):
    _reg_clsid_ = "{47b1aa81-d872-4b24-8338-de80ec3967a1}"
    _reg_contractid_ = "@activestate.com/koHTMLTidyLinter;1"
    _reg_desc_ = "HTML Tidy Linter"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=tidy'),
         ]

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def filterLines(self, lines):
        return lines

class KoHTML5TidyLinter(CommonTidyLinter):
    _reg_desc_ = "Komodo HTML 5 Tidy Linter"
    _reg_clsid_ = "{06b2f705-849d-462f-aafb-bb2e4dfd6d37}"
    _reg_contractid_ = "@activestate.com/koHTML5TidyLinter;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML5&type=tidy'),
         ]

    
    html5_tidy_argv_additions = [
        "--new-blocklevel-tags", "section,header,footer,hgroup,nav,dialog,datalist,details,figcaption,figure,meter,output,progress",
        "--new-pre-tags", "article,aside,summary,mark",
        "--new-inline-tags", "video,audio,canvas,source,embed,ruby,rt,rp,keygen,menu,command,time",
    ]

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def filterLines(self, lines):
        return [line for line in lines if "is not approved by W3C" not in line]


class _invokePerlLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def _lint_with_text(self, request, text, perlHTMLCheckerPrefName,
                        perlLinterBasename, args):
        if not text:
            #log.debug("<< no text")
            return
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref(perlHTMLCheckerPrefName):
            return
        perlLintDir = os.path.join(components.classes["@activestate.com/koDirs;1"].\
                                    getService(components.interfaces.koIDirs).supportDir,
                                   "lint",
                                   "perl")
        perlWrapperFileName = os.path.join(perlLintDir, perlLinterBasename);
        perlExe = prefset.getStringPref("perlDefaultInterpreter")
        if not perlExe:
            perlExe = components.classes["@activestate.com/koAppInfoEx?app=Perl;1"] \
                     .getService(components.interfaces.koIAppInfoEx) \
                     .executablePath
            if not perlExe:
                log.debug("html lint with Perl: No perl interpreter found.")
                return
        cmd = [perlExe, perlWrapperFileName]
        cwd = request.cwd or None
        try:
            p = process.ProcessOpen(cmd, cwd=cwd)
            stdout, stderr = p.communicate(text)
            warnLines = stdout.splitlines() # Don't need the newlines.
        except:
            log.exception("Error perl/html linting, cmd: %s, pwd:%s", cmd, cwd)
            return
            
                
        # 'jslint' error reports come in this form:
        # jslint error: at line \d+ column \d+: explanation
        results = koLintResults()
        if perlLinterBasename == "htmltidy.pl":
            hasStatus = True
            msgRe = re.compile(r'''^input \s+ \( (?P<lineNo>\d+)
                               : (?P<columnNo>\d+) \)
                               \s+ (?P<status>Warning|Info|Error)
                               : \s* (?P<desc>.*)$''', re.VERBOSE)
        else:
            hasStatus = False
            msgRe = re.compile(r'''^\s+ \( (?P<lineNo>\d+)
                               : (?P<columnNo>\d+) \)
                               \s+
                               (?P<desc>.*)$''', re.VERBOSE)
        datalines = text.splitlines()
        numDataLines = len(datalines)
        for msgLine in warnLines:
            m = msgRe.match(msgLine)
            if m:
                status = hasStatus and m.group("status") or None
                if status == "Info":
                    # These are rarely useful
                    continue
                lineNo = int(m.group("lineNo"))
                #columnNo = int(m.group("columnNo"))
                # build lint result object
                result = KoLintResult()
                # if the error is on the last line, work back to the last
                # character of the first nonblank line so we can display
                # the error somewhere
                if lineNo >= len(datalines):
                   lineNo = len(datalines) - 1
                if len(datalines[lineNo]) == 0:
                    while lineNo > 0 and len(datalines[lineNo - 1]) == 0:
                        lineNo -= 1
                if lineNo == 0:
                    lineNo = 1
                result.columnStart =  1
                result.columnEnd = len(datalines[lineNo - 1]) + 1
                result.lineStart = result.lineEnd = lineNo
                if status == "Error":
                    result.severity = result.SEV_ERROR
                else:
                    result.severity = result.SEV_WARNING
                result.description = m.group("desc")
                results.addResult(result)

        return results
        
class KoHTMLPerl_HTMLLint_Linter(_invokePerlLinter):
    """
    Check HTML code by using Perl's HTML-Lint module
    """
    _reg_clsid_ = "{1603484f-7723-4a65-b0f5-b4f77c563d25}"
    _reg_desc_ = "Komodo HTML Linter Using Perl's HTML::Lint"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Perl:HTML::Lint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=Perl:HTML::Lint'),
         ]

    def lint_with_text(self, request, text):
        return self._lint_with_text(request, text,
                                    "lintHTML_CheckWith_Perl_HTML_Lint",
                                    "htmllint.pl", [])
        
class KoHTMLPerl_HTMLTidy_Linter(_invokePerlLinter):
    """
    Check HTML code by using Perl's HTML-Tidy module
    """
    _reg_clsid_ = "{6d9817fc-7b64-435b-9152-7183a9d3ffcc}"
    _reg_desc_ = "Komodo HTML Linter Using Perl's HTML::Tidy"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Perl:HTML::Tidy;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=Perl:HTML::Tidy'),
         ]

    def lint_with_text(self, request, text):
        return self._lint_with_text(request, text,
                                    "lintHTML_CheckWith_Perl_HTML_Tidy",
                                    "htmltidy.pl", [])

    
# HTML5 can use the generic aggregator
 
class KoHTML5_html5libLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_clsid_ = "{913f43fc-d46b-4d2a-a821-0b925ca9a65b}"
    _reg_contractid_ = "@activestate.com/koHTML5_html5libLinter;1"
    _reg_desc_ = "HTML5 html5lib Linter"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML5&type=html5lib'),
         ]

    problem_word_ptn = re.compile(r'([ &<]?\w+\W*)$')
    leading_ws_ptn = re.compile(r'(\s+)')
    dictType = type({})

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not text:
            return
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref('lintHTML5Lib'):
            return
        textLines = text.splitlines()
        try:
            # Use StringIO, not CStringIO!
            # CStringIO.StringIO(latin1 str).read() => ucs2 string 
            # StringIO.StringIO(latin1 str).read() => latin1 string 
            inputStream = StringIO.StringIO(text)
            parser = html5lib.HTMLParser()
            try:
                doc = parser.parse(inputStream,
                                   encoding=request.encoding.python_encoding_name)
            finally:
                inputStream.close()
            errors = parser.errors
            #log.debug("**** Errors: \n%s\n", errors)
            results = koLintResults()
            groupedErrors = {}
            # Gather the grouped results by line/col/errorName, favoring dicts
            for posnTuple, errorName, params in parser.errors:
                lineNo = int(posnTuple[0]) - 1
                endColNo = int(posnTuple[1]) + 1
                key = "%d:%d:%s" % (lineNo, endColNo, errorName)
                if key not in groupedErrors:
                    groupedErrors[key] = [lineNo, endColNo, errorName, params]
                elif type(params) == self.dictType:
                    groupedErrors[key][3] = params
                else:
                    #log.debug("Ignoring additional params: %s", params)
                    pass
            for lineNo, endColNo, errorName, params in groupedErrors.values():
                #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
                if lineNo >= len(textLines) or len(textLines[lineNo]) == 0:
                    lineNo = len(textLines) - 1
                    while lineNo >= 0 and len(textLines[lineNo]) == 0:
                        lineNo -= 1
                    if lineNo < 0:
                        log.warn("No text to display for bug %s", errorName)
                        continue
                result = KoLintResult()
                result.lineStart = result.lineEnd = lineNo + 1
                result.columnStart = 1
                result.columnEnd = 1 + len(textLines[lineNo])
                result.description = self._buildErrorMessage(errorName, params)
                #TODO: Distinguish errors from warnings...
                result.severity = result.SEV_ERROR
                
                results.addResult(result)
        except ServerException:
            log.exception("ServerException")
            raise
        except:
            # non-ServerException's are unexpected internal errors
            log.exception("unexpected internal error")
            raise
        return results
    
    def _buildErrorMessage(self, errorName, params):
        if errorName in html5libErrorDict:
            errorTemplate = html5libErrorDict[errorName]
            try:
                return errorTemplate % params
            except (TypeError, KeyError):
                pass
        else:
            errorTemplate = errorName
        return "%s: %s" % (errorTemplate, params)
