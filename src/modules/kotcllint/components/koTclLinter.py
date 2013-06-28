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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2008
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

import os
from os.path import join, abspath, dirname
import sys
import re
import logging

from xpcom import components, nsError, ServerException

import process
import koprocessutils
from koLintResult import KoLintResult
from koLintResults import koLintResults

try:
    from koLintResult import getProxiedEffectivePrefs
    gHaveGetProxiedEffectivePrefs = True
except ImportError:
    # getProxiedEffectivePrefs was removed in Komodo 8.
    gHaveGetProxiedEffectivePrefs = False


log = logging.getLogger("koTclLinter")
#log.setLevel(logging.DEBUG)

endWordSet = ";} \t\n"

tcllintprefs = """
  tcllint_argAfterArgs
  tcllint_argsNotDefault
  tcllint_badBoolean
  tcllint_badByteNum
  tcllint_badColorFormat
  tcllint_badCursor
  tcllint_badFloat
  tcllint_badIndex
  tcllint_badIndexExpr
  tcllint_badInt
  tcllint_badKey
  tcllint_badList
  tcllint_badLevel
  tcllint_badMode
  tcllint_badOption
  tcllint_badPixel
  tcllint_badResource
  tcllint_badSwitch
  tcllint_badVersion
  tcllint_badWholeNum
  tcllint_badNatNum
  tcllint_badArrayIndex
  tcllint_mismatchOptions
  tcllint_noExpr
  tcllint_noScript
  tcllint_noSwitchArg
  tcllint_nonDefAfterDef
  tcllint_nonPortChannel
  tcllint_nonPortCmd
  tcllint_nonPortColor
  tcllint_nonPortCursor
  tcllint_nonPortFile
  tcllint_nonPortOption
  tcllint_nonPortVar
  tcllint_numArgs
  tcllint_numListElts
  tcllint_obsoleteCmd
  tcllint_parse
  tcllint_procNumArgs
  tcllint_tooManyFieldArg
  tcllint_warnDeprecated
  tcllint_warnExportPat
  tcllint_warnExpr
  tcllint_warnExtraClose
  tcllint_warnIfKeyword
  tcllint_warnNamespacePat
  tcllint_warnPattern
  tcllint_warnReserved
  tcllint_warnRedefine
  tcllint_warnUndefProc
  tcllint_warnUnsupported
  tcllint_warnVarRef
  tcllint_winAlpha
  tcllint_winBeginDot
  tcllint_winNotNull
  tcllint_warnInternalCmd
  tcllint_invalidUsage
  tcllint_warnBehaviourCmd
  tcllint_warnBehaviour
  tcllint_internalError
  tcllint_warnReadonlyVar
  tcllint_arrayReadAsScalar
  tcllint_warnUndefFunc
  tcllint_badMathOp
  tcllint_nonPublicVar
  tcllint_warnUndefinedVar
  tcllint_warnGlobalVarColl
  tcllint_warnShadowVar
  tcllint_warnUpvarNsNonsense
  tcllint_warnGlobalNsNonsense
  tcllint_warnUndefinedUpvar
  tcllint_badTraceOp
  tcllint_serverAndPort
  tcllint_socketArgOpt
  tcllint_socketAsync
  tcllint_socketBadOpt
  tcllint_socketServer
  tcllint_badCharMap
  tcllint_warnEscapeChar
  tcllint_warnNotSpecial
  tcllint_warnQuoteChar
  tcllint_errBadBrktExp
  tcllint_warnY2K
  tcllint_badRegexp
  tcllint_warnAIPattern
  tcllint_warnMemoryCmd
  tcllint_badBinaryFmt
  tcllint_badFormatFmt
  tcllint_badSerialMode
  tcllint_pkgBadExactRq
  tcllint_pkgVConflict
  tcllint_pkgTclConflict
  tcllint_pkgUnchecked
  tcllint_badColormap
  tcllint_badEvent
  tcllint_badGeometry
  tcllint_badGridRel
  tcllint_badGridMaster
  tcllint_badPalette
  tcllint_badPriority
  tcllint_badScreen
  tcllint_badSticky
  tcllint_badTab
  tcllint_badTabJust
  tcllint_badVirtual
  tcllint_badVisual
  tcllint_badVisualDepth
  tcllint_nonPortBitmap
  tcllint_nonPortKeysym
  tcllint_noVirtual
  tcllint_noEvent
  tcllint_warnConsoleCmd
  tcllint_warnTkCmd
  tcllint_badBindSubst
  tcllint_blt_badIntRange
  tcllint_blt_badSignal
  tcllint_blt_badSignalInt
  tcllint_expect_warnAmbiguous
  tcllint_incrTcl_classNumArgs
  tcllint_incrTcl_procOutScope
  tcllint_incrTcl_procProtected
  tcllint_incrTcl_badMemberName
  tcllint_incrTcl_classOnly
  tcllint_incrTcl_warnUnsupported
  tcllint_incrTcl_nsOnly
  tcllint_incrTcl_nsOrClassOnly
  tcllint_tclX_badProfileOpt
  tcllint_tclX_optionRequired
  tcllint_tclX_badLIndex
  tcllint_tclX_badTlibFile
  tcllint_oratcl_badConnectStr
  tcllint_oratcl_badSubstChar
  tcllint_oratcl_badOnOff
  tcllint_oratcl_missingColon
  tcllint_sybtcl_badSubstChar
  tcllint_xmlAct_badXMLaction
""".split()


class KoTclCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Tcl Linter"
    _reg_clsid_ = "{842EC3B2-B79B-44a2-9417-04CEA5C02BF1}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Tcl;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Tcl'),
         ]

    def __init__(self):
        self._tclProRe = re.compile(r'^[^:]+:(\d+) \((\w+)\) (.*)$')
        nsXulAppInfo = components.classes["@mozilla.org/xre/app-info;1"].\
                            getService(components.interfaces.nsIXULAppInfo)
        nsXulRuntime = nsXulAppInfo.QueryInterface(components.interfaces.nsIXULRuntime)
        self._platformDir = join(dirname(dirname(os.path.abspath(__file__))),
                                 "platform",
                                 nsXulRuntime.OS)
        if nsXulRuntime.OS == "Linux":
            self._platformDir += "_" + os.uname()[4]
        log.debug("Using kotcllint from directory: %r", self._platformDir)
        self._initialize_prefs()

    def _initialize_prefs(self):
        """Create the tcl preferences when they don't already exist"""
        globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs
        for pref in tcllintprefs:
            if not globalPrefs.hasBooleanPref(pref):
                globalPrefs.setBooleanPref(pref, False)
        if not globalPrefs.hasBooleanPref('force_tcllint_version'):
            globalPrefs.setBooleanPref('force_tcllint_version', False)
        if not globalPrefs.hasStringPref('tcllint_version'):
            globalPrefs.setStringPref('tcllint_version', '8.4')
        if not globalPrefs.hasStringPref('tcllint_extra'):
            globalPrefs.setStringPref('tcllint_extra', '')
        if not globalPrefs.hasStringPref('tclExtraPaths'):
            globalPrefs.setStringPref('tclExtraPaths', '')

    def _getLinterArgv(self, prefset):
        if sys.platform.startswith('win'):
            executable = 'kotcllint.exe'
        else:
            executable = 'kotcllint'
        linter = os.path.join(self._platformDir, executable)
        linterArgv = [linter, '-onepass']
        if prefset.getBooleanPref('force_tcllint_version'):
            version = str(prefset.getStringPref('tcllint_version'))
            linterArgv.extend(['-use', 'Tcl'+version])
        for pref in tcllintprefs:
            if prefset.getBooleanPref(pref):
                tclmessage = pref[len('tcllint_'):].replace('_', '::')
                linterArgv.extend(['-suppress', tclmessage])
        extra = prefset.getStringPref('tcllint_extra')
        if extra:
            linterArgv.extend(extra.split())
        return linterArgv

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def lint_with_text(self, request, text):
        """Lint the given Tcl content.
        
        Raise an exception if there is a problem.
        """
        if gHaveGetProxiedEffectivePrefs:
            prefset = getProxiedEffectivePrefs(request)
        else:
            # Komodo 8 sets the prefet on the request.
            prefset = request.prefset
        argv = self._getLinterArgv(prefset)
        env = koprocessutils.getUserEnv()

        # if there is no setting for the dev kit environment, use
        # the shared directory for it.  This enables site wide
        # use of *.pdx and *.pcx files for debugging

        if "TCLDEVKIT_LOCAL" not in env:
            koDirs = components.classes["@activestate.com/koDirs;1"].\
                getService(components.interfaces.koIDirs)
            sharedDir = os.path.join(koDirs.commonDataDir, "tcl")
            env["TCLDEVKIT_LOCAL"] = sharedDir

        if prefset.hasPref("tclExtraPaths"):
            tclExtraPaths = prefset.getStringPref("tclExtraPaths")
            # If TCLLIBPATH is set, then it must contain a valid Tcl
            # list giving directories to search during auto-load
            # operations. Directories must be specified in Tcl format,
            # using "/" as the path separator, regardless of platform.
            # This variable is only used when initializing the
            # auto_path variable.  Also escape spaces in paths.
            tclExtraPaths = tclExtraPaths.replace('\\', '/')
            tclExtraPaths = tclExtraPaths.replace(' ', '\ ')
            TCLLIBPATH = ' '.join(tclExtraPaths.split(os.pathsep))
            env["TCLLIBPATH"] = TCLLIBPATH

        cwd = request.cwd or None
        print 'argv: %r' % (argv, )
        p = process.ProcessOpen(argv, cwd=cwd, env=env)
        lOutput, lErrOut = p.communicate(text)
        lOutput = lOutput.splitlines(1)
        #print '======'
        #print lOutput
        #print '======'
        #print lErrOut
        #print '<<<<<<'

        if not lOutput and lErrOut:
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, lErrOut)
        
        if not lOutput:
            # this should never happen unless the tcl linter is broken, or
            # not executable on linux.
            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                  "No output from Tcl linter available")
        
        if lOutput[0].startswith("TclPro") or \
           lOutput[0].startswith("scanning"):
            # The open source TclPro has the header stripped,
            # so we need to check for both "TclPro" and "scanning"
            lInput = text.split('\n')
            return self._TclPro_lint(lInput, lOutput)
        else:
            errmsg = "unrecognized lint output format:\n%s" % lOutput[0]
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, errmsg)

    def _TclPro_lint(self, lInput, lOutput):
        # TclPro output has the following header info:
        ###################
        #TclPro -- Version 1.4.1
        #Copyright (C) Ajuba Solutions 1998-2001. All rights reserved.
        #This product is registered to: <user name>
        #
        #scanning: <filename>
        #checking: <filename>
        #<filename>:<lineNo> (<errorName>) <errorText>
        #<commandWithError>
        #<caret at col in command where error is>
        #[repeat above three until no more errors]
        ###################
        # The 'checking' line exists when the -onepass option isn't used
        i = 1
        lastCol = -1
        lastLine = -1
        results = koLintResults()
        numLines = len(lOutput)
        while i < numLines:
            match = re.search(self._tclProRe, lOutput[i])
            if not match:
                # We expect the first few lines to not match, while we
                # skip the header lines
                i += 1
                # But if too many lines aren't matching, then we must have
                # unrecognizable input
                if i > 8:
                    log.warn("couldn't recognize Tcl linter output format")
                    break
                continue
            if i+2 >= numLines:
                log.error("unexpected return data format: short data")
                return
            cmd = lOutput[i+1].rstrip()
            col = lOutput[i+2].find('^')
            if col == -1:
                if i+3 == numLines:
                    log.error("unexpected return data format: short data")
                    return
                col = lOutput[i+3].find('^')
                if col == -1:
                    log.warn("No column indicator following line %d:%r", i, lOutput[i])
                    i += 1
                    continue
                cmd = lOutput[i+2].rstrip()
                parseLineOffset = 1
            else:
                parseLineOffset = 0
            lineNo = match.group(1)
            # lInput is zero-based, whereas text display lines start at one,
            # so we adjust lineNo down one here.
            lineNo = int(lineNo) - 1
            if lineNo != lastLine:
                lastLine = lineNo
                lastCol = 0

            if col == -1:
                col = len(lInput[lineNo].rstrip())
            startCol = lInput[lineNo].find(cmd, lastCol)
            if startCol == -1:
                # It's possible that we are throwing multiple warnings on
                # the same command.  Let's check again, starting at col 0.
                # If something was found, ignore multiple warnings in the
                # same line, otherwise log a problem
                if lastCol == 0 or \
                   lInput[lineNo].find(cmd, 0) == -1:
                    # Looks like we can't figure something out...
                    log.debug('undecipherable lint output: %s,%s "%s" in "%s" last %s' \
                              % (lineNo+1, col, cmd, lInput[lineNo], lastCol))
                i += parseLineOffset + 3
                continue

            #print 'TclLint: %s,%s "%s" in "%s"' \
            #      % (lineNo+1, startCol, cmd, lInput[lineNo])

            result = KoLintResult()
            msg = match.group(2)
            result.description = match.group(3).strip()
            result.lineStart = lineNo+1
            # All our warnings stay on one line
            result.lineEnd = result.lineStart
            cmdLen = len(cmd)
            if msg.startswith("warn") or msg.startswith("nonPort"):
                result.severity = result.SEV_WARNING
                # In the warning case, go to the next char that we think
                # ends the word (not precise), starting at the caret.
                endCol = col
                while endCol < cmdLen and cmd[endCol] not in endWordSet:
                    # might want to handle \ escapes
                    endCol += 1
                # readjust for where the command started
                endCol += startCol
                # and bump up the startCol to where the caret indicated
                startCol += col
            else:
                result.severity = result.SEV_ERROR
                # In the error case, highlight the entire command
                # The linter should only give one error per command
                endCol = startCol + cmdLen
            # Adjust by 1 as columns start at 1 for the text display
            result.columnStart = startCol + 1
            result.columnEnd = endCol + 1
            results.addResult(result)

            # Set lastCol to properly handle multiple similar code-blocks
            # with errors on the same line.
            lastCol = startCol+1
            i += 3
            # end while
        return results

