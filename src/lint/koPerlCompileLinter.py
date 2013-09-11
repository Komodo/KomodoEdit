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

from xpcom import components, nsError, ServerException
from koLintResult import KoLintResult
from koLintResults import koLintResults
import os, re, sys
import tempfile
import process
import koprocessutils
import logging

from zope.cachedescriptors.property import LazyClassAttribute


log = logging.getLogger("koPerlCompileLinter")
#log.setLevel(logging.DEBUG)

def _combineTextParts(pendingLines, basePart=None):
    if pendingLines:
        if basePart:
            return "\n".join(pendingLines) + "\n" + basePart
        else:
            return "\n".join(pendingLines)
    elif basePart:
        return basePart
    else:
        return ""

def PerlWarnsToLintResults(warns, perlfilename, actualFileName, perlcode):
    perllines = perlcode.split('\n')

    # preprocess the perl warnings
    #   - copy up '(Missing semicolon on previous line?)' to previous line
    #   - remove 'perlfilename'
    #XXX it would be nice to find all hints and copy them up
    newwarns = []
    for line in warns:
        # get rid if eols
        line = line[:-1]
        
        # handle multi-line string literals
        if newwarns and newwarns[-1] and newwarns[-1][-1] == "\r" :
            #XXX we should print an EOL symbol
            newwarns[-1] = newwarns[-1][:-1] + '\r' + line
        ## this code is not handling hints correctly. In any case, hints make
        ## the error messages too long for the status bar
        #elif line.find('(Missing semicolon on previous line?)') != -1:
        #      newwarns[-1] = newwarns[-1] + " " + line[1:]
        else:
            newline = line
            newwarns.append(newline)
    warns = newwarns

    results = []
    if type(perlfilename) == unicode:
        perlfilename = perlfilename.encode('utf-8')
    escPerlName = re.escape(perlfilename)
    # Fix bug 96303 (again): Replace any runs of non-ascii characters with unescaped '.*'
    # The other parts of the filename do get escaped.
    perlfilename_ascii_parts = re.split(r'([^\x00-\x7f]+)', perlfilename)
    escaped_even_parts = [re.escape(part) for part in perlfilename_ascii_parts[0::2]]
    escPerlName = ".*?".join(escaped_even_parts)
    warnRe = re.compile(r'(?P<description>.*) at %s line (?P<lineNum>\d+)(?P<hint>.*)' % escPerlName)
    successRe = re.compile(r'%s syntax OK' % escPerlName)
    compilationFailedRe = re.compile(r'Compilation failed in require at %s' % escPerlName)
    compilationErrorsRe = re.compile(r'%s had compilation errors\.' % escPerlName)
    beginFailedRe = re.compile(r'BEGIN failed--compilation aborted')

    pendingLines = []
    sawSyntaxOK = False
    sawSyntaxBad = False
    for warn in warns:
        if successRe.match(warn):
            sawSyntaxOK = True
            continue
        match = warnRe.search(warn)
        if match:
            if compilationFailedRe.match(warn) or beginFailedRe.match(warn) or compilationErrorsRe.match(warn):
                sawSyntaxBad = True
                if results:
                    # Don't bother displaying this
                    continue
            lineNum = int(match.group('lineNum'))
            varName = match.groupdict().get('varName', None)
            lr = KoLintResult()
            
            lr.description = _combineTextParts(pendingLines, match.group('description') + match.group('hint')).replace(perlfilename, actualFileName)
            pendingLines = []
            while lr.description.endswith("\n"):
                lr.description = lr.description[:-1]
                
            lr.lineStart = lineNum 
            lr.lineEnd = lineNum
            if varName:
                lr.columnStart = perllines[lr.lineStart-1].find(varName) + 1
                if lr.columnStart == -1:
                    lr.columnEnd = -1
                else:
                    lr.columnEnd = lr.columnStart + len(varName) + 1
            else:
                lr.columnStart = 1
                lr.columnEnd = len(perllines[lr.lineStart-1]) + 1
            results.append(lr)
        else:
            pendingLines.append(warn)
    if pendingLines and results:
        results[-1].description = _combineTextParts(pendingLines, results[-1].description).replace(perlfilename, actualFileName)

# XXX
#
# Whatever is caught by the next else block is (according to Aaron) additional information
# re: the last error.  It should be added to the lint warning, but isn't because the
# status bar display isn't smart enough and it looks ugly.
#  Todo: 1) add the extra info to the lint description (possibly add a new attribute to LintResults
#           with this 'metadata'
#        2) Update the status bar display and tooltip display to display the right info.
#  I'm commenting this block out because log.warn's impact speed. --david
#        
#        else:
#            if not (successRe.search(warn) or failureRe.search(warn)):
#                log.warn("Skipping Perl warning: %r", warn)


    # under some conditions, Perl will spit out messages after the
    # "syntax Ok", so check the entire output.
    
    if results:
        if sawSyntaxOK and not sawSyntaxBad:
            severity = KoLintResult.SEV_WARNING
        elif sawSyntaxBad and not sawSyntaxOK:
            severity = KoLintResult.SEV_ERROR
        elif successRe.search("\n".join(warns)):
            severity = KoLintResult.SEV_WARNING
        else:
            severity = KoLintResult.SEV_ERROR
    lintResults = koLintResults()
    for lr in results:
        lr.severity = severity
        lintResults.addResult(lr)

    return lintResults
            

def RemoveDashDFromShebangLine(line):
    """Remove a possible -d perl option from the given shebang line.
    Return the resultant string.

    Note that this is probably not going to handle esoteric uses of quoting
    and escaping on the shebang line.

        >>> from koPerlCompileLinter import RemoveDashDFromShebangLine as rd
        >>> rd("foo")
        'foo'
        >>> rd("#!perl -d")
        '#!perl '
        >>> rd("#!perl -d:foo")
        '#!perl '
        >>> rd("#!perl -cd")
        '#!perl -c'
        >>> rd("#!perl -0")
        '#!perl -0'
        >>> rd("#!perl -01d")
        '#!perl -01'
        >>> rd("#!perl -Mmymodule")
        '#!perl -Mmymodule'
        >>> rd("#!perl -dMmymodule")
        '#!perl -Mmymodule'
        >>> rd("#!perl -Vd")
        '#!perl -V'
        >>> rd("#!perl -V:d")
        '#!perl -V:d'
        >>> rd("#!/bin/sh -- # -*- perl -*- -p")
        '#!/bin/sh -- # -*- perl -*- -p'
        >>> rd("#!/bin/sh -- # -*- perl -*- -pd")
        '#!/bin/sh -- # -*- perl -*- -p'
    """
    # ensure this is a shebang line
    if not line.startswith("#!"):
        return line

    result = ""
    remainder = line
    # parsing only begins from where "perl" is first mentioned
    splitter = re.compile("(perl)", re.I)
    try:
        before, perl, after = re.split(splitter, remainder, 1)
    except ValueError:
        # there was no "perl" in shebang line
        return line
    else:
        result += before + perl
        remainder = after

    # the remainder are perl arguments
    tokens = re.split("(-\*|- |\s+)", remainder)
    while len(tokens) > 0:
        token = tokens[0]
        if token == "":
            tokens = tokens[1:]
        elif token in ("-*", "- "):
            # "-*" and "- " are ignored for Emacs-style mode lines
            result += token
            tokens = tokens[1:]
        elif re.match("^\s+$", token):
            # skip whitespace
            result += token
            tokens = tokens[1:]
        elif token == "--":
            # option processing stops at "--"
            result += "".join(tokens)
            tokens = []
        elif token.startswith("-"):
            # parse an option group
            # See "perl -h". Those options with arguments (some of them
            # optional) must have 'd' in those arguments preserved.
            stripped = "-"
            token = token[1:]
            while len(token) > 0: 
                ch = token[0]
                if ch in ('0', 'l'):
                    # -0[octal]
                    # -l[octal]
                    stripped += ch
                    token = token[1:]
                    while len(token) > 0:
                        ch = token[0]
                        if ch in "01234567":
                            stripped += ch
                            token = token[1:]
                        else:
                            break
                elif ch == 'd':
                    # -d[:debugger]
                    if len(token) > 1 and token[1] == ":":
                        # drop the "d:foo"
                        token = ""
                    else:
                        # drop the 'd'
                        token = token[1:]
                elif ch in ('D', 'F', 'i', 'I', 'm', 'M', 'x'):
                    # -D[number/list]
                    # -F/pattern/
                    # -i[extension]
                    # -Idirectory
                    # -[mM][-]module
                    # -x[directory]
                    stripped += token
                    token = ""
                elif ch == 'V':
                    # -V[:variable]
                    if len(token) > 1 and token[1] == ":":
                        stripped += token
                        token = ""
                    else:
                        stripped += ch
                        token = token[1:]
                else:
                    stripped += ch
                    token = token[1:]
            if stripped != "-":
                result += stripped
            tokens = tokens[1:]
        else:
            # this is a non-option group token, skip it
            result += token
            tokens = tokens[1:]
    remainder = ""

    return result

class _CommonPerlLinter(object):

    @LazyClassAttribute
    def sysUtils(self):
        return components.classes["@activestate.com/koSysUtils;1"].\
                    getService(components.interfaces.koISysUtils)
    @LazyClassAttribute
    def _koVer(self):
        return components.classes["@activestate.com/koInfoService;1"].\
                   getService().version
    @LazyClassAttribute
    def _perlTrayDir(self):
        supportDir = components.classes["@activestate.com/koDirs;1"].\
                    getService(components.interfaces.koIDirs).supportDir
        return os.path.join(supportDir, "perl", "perltray").replace('\\', '/')
    @LazyClassAttribute
    def appInfoEx(self):
        return components.classes["@activestate.com/koAppInfoEx?app=Perl;1"].\
                    getService(components.interfaces.koIPerlInfoEx)

    def isPerlCriticInstalled(self, forceCheck):
        return self.appInfoEx.isPerlCriticInstalled(False)
    
    def getPerlCriticVersion(self):
        return self.appInfoEx.getPerlCriticVersion()

    def _writeTempFile(self, cwd, text):
        tmpFileName = None
        if cwd:
            # Try to create the tempfile in the same directory as the perl
            # file so that @INC additions using FindBin::$Bin work as
            # expected.
            # XXX Would really prefer to build tmpFileName from the name of
            #     the file being linted but the Linting system does not
            #     pass the file name through.
            tmpFileName = os.path.join(cwd, ".~ko-%s-perllint~" % self._koVer)
            try:
                fout = open(tmpFileName, 'wb')
                fout.write(text)
                fout.close()
            except (OSError, IOError), ex:
                tmpFileName = None
        if not tmpFileName:
            # Fallback to using a tmp dir if cannot write in cwd.
            try:
                tmpFileName = tempfile.mktemp()
            except OSError, ex:
                # Sometimes get this error but don't know why:
                # OSError: [Errno 13] Permission denied: 'C:\\DOCUME~1\\trentm\\LOCALS~1\\Temp\\~1324-test'
                errmsg = "error determining temporary filename for "\
                         "Perl content: %s" % ex
                raise ServerException(nsError.NS_ERROR_UNEXPECTED, errmsg)
            fout = open(tmpFileName, 'wb')
            fout.write(text)
            fout.close()
        return tmpFileName
    
    # PerlNET requires a 'use namespace...' directive as well,
    # which we don't want to remove because it's too generic a name.
    # So don't bother removing 'use PerlNET'
    _use_perltray_module = re.compile(r"\buse PerlTray\b")



    def _selectPerlExe(self, prefset):
        """Determine the Perl interpreter to use.
        
        Return value is the absolute path to the perl intepreter. Raises
        an exception if a suitable one cannot be found.
        """
        # use pref'd default if one has been chosen
        perlExe = prefset.getStringPref("perlDefaultInterpreter")

        #XXX Is this still necessary now that we are using process.py?
        #    It existed because popen2 cannot handle unicode paths.
        try:
            perlExe = str(perlExe)
        except UnicodeError:
            errmsg = "Path to Perl interpreter cannot contain Unicode characters."
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

        if perlExe:
            # "wPerl.exe" on Windows causes problems, although at one point
            # this is what we encouraged users to use. We want to just use
            # "perl.exe" even if the preference states to use "wPerl.exe"
            if sys.platform.startswith("win"):
                dirName, baseName = os.path.split(perlExe)
                if os.path.splitext(baseName)[0].lower() == "wperl":
                    perlExe = os.path.join(dirName, "perl.exe")
                    if not os.path.isfile(perlExe):
                        perlExe = None
        if not perlExe:
            perlExe = self.sysUtils.Which("perl")
        if not perlExe or not os.path.isfile(perlExe):
            errmsg = "No Perl interpreter could be found for syntax checking."
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

        return perlExe

_begin_to_init_re = re.compile(r'\bBEGIN(?=(?:\s|#.*\n?)*\{)')
# Python takes a long time matching this when it fails, so do a quicker
# pattern when we have more than 10000 characters.
_begin_to_init_faster_re = re.compile(r'\bBEGIN(?=\s*\{)')
_init_matcher_cutoff = 10000
class KoPerlCompileLinter(_CommonPerlLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Perl Compile Linter"
    _reg_clsid_ = "{8C9C11E9-528C-11d4-AC25-0090273E6A60}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Perl;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Perl&type=Standard'), #
         ]

    def lint(self, request):
        """Lint the given Perl content.
        
        Raise an exception if there is a problem.
        """
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        cwd = request.cwd
        prefset = request.prefset
        # Remove a possible "-d" in the shebang line, this will tell Perl to
        # launch the debugger which, if the PDK is installed, is the PDK
        # debugger.  Be careful to handle single-line files correctly.
        splitText = text.split("\n", 1)
        firstLine = RemoveDashDFromShebangLine(splitText[0])
        if len(splitText) > 1:
            text = "\n".join([firstLine, splitText[1]])
        else:
            text = firstLine
        if prefset.getBooleanPref("perl_lintOption_disableBeginBlocks"):
            if len(text) > _init_matcher_cutoff:
                # Use a faster pattern when we have lots of text.
                text = _begin_to_init_faster_re.sub("INIT", text)
            else:
                text = _begin_to_init_re.sub("INIT", text)
        # Save perl buffer to a temporary file.

        tmpFileName = self._writeTempFile(cwd, text)
        try:
            perlExe = self._selectPerlExe(prefset)
            lintOptions = prefset.getStringPref("perl_lintOption")
            option = '-' + lintOptions
            perlExtraPaths = prefset.getStringPref("perlExtraPaths")
            if perlExtraPaths:
                if sys.platform.startswith("win"):
                    perlExtraPaths = perlExtraPaths.replace('\\', '/')
                perlExtraPaths = [x for x in perlExtraPaths.split(os.pathsep) if x.strip()]
            argv = [perlExe]
            for incpath in perlExtraPaths:
                argv += ['-I', incpath]
            if prefset.getBooleanPref("perl_lintOption_includeCurrentDirForLinter"):
                argv += ['-I', '.']
                
            # bug 27963: Fix instances of <<use PerlTray>> from code
            # to make them innocuous for the syntax checker.
            # 'use PerlTray' in comments or strings will trigger a false positive
            if sys.platform.startswith("win") and self._use_perltray_module.search(text):
                argv += ['-I', self._perlTrayDir]

            argv.append(option)
            argv.append(tmpFileName)
            cwd = cwd or None # convert '' to None (cwd=='' for new files)
            env = koprocessutils.getUserEnv()
            # We only need stderr output.

            p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
            _, stderr = p.communicate()
            lintResults = PerlWarnsToLintResults(stderr.splitlines(1),
                                                 tmpFileName, 
                                                 request.koDoc.displayPath,
                                                 text)
        finally:
            os.unlink(tmpFileName)

        return lintResults

class KoPerlCriticLinter(_CommonPerlLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Perl Critic Linter"
    _reg_clsid_ = "{3a940bcc-1cee-4345-92d3-cbf6f746dceb}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Perl&type=PerlCritic;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Perl&type=Critic'),
         ]

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)        
        
    def lint_with_text(self, request, text):
        prefset = request.prefset
        criticLevel = prefset.getStringPref('perl_lintOption_perlCriticLevel')
        if criticLevel == 'off':
            return
        
        if not self.isPerlCriticInstalled(False):
            # This check is necessary in case Perl::Critic and/or criticism were uninstalled
            # between Komodo sessions.  appInfoEx.isPerlCriticInstalled caches the state
            # until the pref is changed.
            return
        
        # Bug 82713: Since linting isn't done on the actual file, but a copy,
        # Perl-Critic will complain about legitimate package declarations.
        # Find them, and append an annotation to turn the Perl-Critic feature off.
        # This will also tag comments, strings, and POD, but that won't affect
        # lint results.
        # This is no longer needed with Perl-Critic 1.5, which
        # goes by the filename given in any #line directives
        perlCriticVersion = self.getPerlCriticVersion()
        currFile = request.koDoc.file
        baseFileName = None
        if currFile:
            baseFileName = currFile.baseName[0:-len(currFile.ext)]
            if perlCriticVersion < 1.500:
                munger = re.compile(r'''^\s*(?P<package1>package \s+ (?:[\w\d_]+::)*) 
                                         (?P<baseFileName>%s)
                                         (?P<space1>\s*;)
                                         (?P<space2>\s*)
                                         (?P<rest>(?:\#.*)?)$''' % (baseFileName,),
                                re.MULTILINE|re.VERBOSE)
                text = munger.sub(self._insertPerlCriticFilenameMatchInhibitor, text)
        elif perlCriticVersion >= 1.500 and currFile:
            text = "#line 1 " + currFile.baseName + "\n" + text

        cwd = request.cwd or None # convert '' to None (cwd=='' for new files)
        tmpFileName = self._writeTempFile(cwd, text)
        try:
            perlExe = self._selectPerlExe(prefset)
            lintOptions = prefset.getStringPref("perl_lintOption")
            option = '-' + lintOptions
            if perlCriticVersion <= 1.100 or not baseFileName:
                pcOption = '-Mcriticism=' + criticLevel
            else:
                settings = { '-severity': criticLevel,
                             'as-filename': baseFileName }
                perlcritic_checking_rcfile = prefset.getStringPref("perlcritic_checking_rcfile")
                if perlcritic_checking_rcfile and os.path.exists(perlcritic_checking_rcfile):
                    settings['-profile'] = perlcritic_checking_rcfile
                pcOption = "-Mcriticism (" + ", ".join(["'%s' => '%s'" % (key, value) for key, value in settings.items()]) + ")"
            perlExtraPaths = prefset.getStringPref("perlExtraPaths")
            if perlExtraPaths:
                if sys.platform.startswith("win"):
                    perlExtraPaths = perlExtraPaths.replace('\\', '/')
                perlExtraPaths = [x for x in perlExtraPaths.split(os.pathsep) if x.strip()]
            argv = [perlExe]
            for incpath in perlExtraPaths:
                argv += ['-I', incpath]
            if 'T' in lintOptions and prefset.getBooleanPref("perl_lintOption_includeCurrentDirForLinter"):
                argv += ['-I', '.']
                
            # bug 27963: Fix instances of <<use PerlTray>> from code
            # to make them innocuous for the syntax checker.
            # 'use PerlTray' in comments or strings will trigger a false positive
            if sys.platform.startswith("win") and self._use_perltray_module.search(text):
                argv += ['-I', self._perlTrayDir]

            argv.append(option)
            argv.append(pcOption)
            argv.append(tmpFileName)
            env = koprocessutils.getUserEnv()
            # We only need stderr output.

            p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
            _, stderr = p.communicate()
            lintResults = PerlWarnsToLintResults(stderr.splitlines(1),
                                                 tmpFileName,
                                                 request.koDoc.displayPath,
                                                 text)
        finally:
            os.unlink(tmpFileName)

        return lintResults
            
    def _insertPerlCriticFilenameMatchInhibitor(self, matchObj):
        currDict = matchObj.groupdict()
        currDict['moduleOff'] = ' ##no critic(RequireFilenameMatchesPackage)'
        return "%(package1)s%(baseFileName)s%(space1)s%(moduleOff)s%(space2)s" % currDict

#---- script mainline testing 

def _test():
    import doctest, koPerlCompileLinter
    return doctest.testmod(koPerlCompileLinter)

if __name__ == "__main__":
    _test()
