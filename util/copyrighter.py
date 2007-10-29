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

# Adds and/or updates the copyright notices in files.
#
# Usage from the command line:
#    Basic:
#      python copyrighter.py [files...]
#    Advanced (run python copyrighter.py -h) to get argument meanings:
#      python copyrighter.py -bdruv [files...]
#
# Usage from python:
#    import copyrighter
#    for file in files:
#       copyrighter.AddCopyright(filepath)
#       # or run with additional arguments
#       copyrighter.AddCopyright(filepath, runRecursivly=0, noChange=0, doUpdateOnly=0, doMakeFileBackup=0
#    # or chose a particular Copyrighter function
#    copyrighter.XmlCopyrighter("foo.kpf").PatchIfNecessary()   # where .kpf is an XML format
#
# Notes:
#  * The filename suffix must match a predefined set of suffixes in order
#    to work correctly, unmatched suffixes will be ignored.
#  * You could simple update the copyright notices every year running:
#      # python copywriter.py -r -u -v --dry-run *  # Just to be sure first
#      # python copywriter.py -r -u -v *
#
# Author:
#  - Original author is unknown
#  - Todd Whiteman
#
# History:
#  - Oct 17, 2007
#    Update for working on relicensing the openkomodo source code as MPL.
#  - Mar 2, 2006
#    Add update capabilities for the ActivePython source.
#    Can now check all lines of a file, or a optional number of lines
#  - Feb 24, 2006
#    Add program control options: recursive, dry-run, no-backups, update-only
#    Tweak regex and global variables for better updating
#    Add additional verbose logging and logging formatting
#

import os
import sys
import time
import re
import shutil
import logging

__version__ = "0.2"

#---- setup logging
logging.basicConfig()
log = logging.getLogger("c")
logpadding = ''         # Used for pretty printing directory depths

#---- globals
# Options that are set through the command line
saveChanges       = 0   # Run, but don't make any changes to files unless this is set to 1/True
performUpdateOnly = 0   # Only perform updates on existing files with copyright
makeFileBackup    = 0   # Make a backup of a file if it will be changed
linesCheckUpTo    = None  # Check first n lines for copyright information
maxLineLength     = 1000  # Any line read in that is longer than this is ignored


# The copyright message:
#   *Should* be able to make this an arbitrary number of lines.
# Note: The additional lines are only added to files where these is no
#       existing ActiveState copyright found. Does not apply when the
#       update only ( -u ) argument is used.
_g_copyright_year = str(time.localtime()[0])
_g_company_name = "ActiveState Software Inc"
_g_mpl_copyright = """***** BEGIN LICENSE BLOCK *****
Version: MPL 1.1/GPL 2.0/LGPL 2.1

The contents of this file are subject to the Mozilla Public License
Version 1.1 (the "License"); you may not use this file except in
compliance with the License. You may obtain a copy of the License at
http://www.mozilla.org/MPL/

Software distributed under the License is distributed on an "AS IS"
basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
License for the specific language governing rights and limitations
under the License.

The Original Code is Komodo code.

The Initial Developer of the Original Code is %(company_name)s.
Portions created by %(company_name)s are Copyright (C) 2000-%(copyright_year)s
%(company_name)s. All Rights Reserved.

Contributor(s):
  %(company_name)s

Alternatively, the contents of this file may be used under the terms of
either the GNU General Public License Version 2 or later (the "GPL"), or
the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
in which case the provisions of the GPL or the LGPL are applicable instead
of those above. If you wish to allow use of your version of this file only
under the terms of either the GPL or the LGPL, and not to allow others to
use your version of this file under the terms of the MPL, indicate your
decision by deleting the provisions above and replace them with the notice
and other provisions required by the GPL or the LGPL. If you do not delete
the provisions above, a recipient may use your version of this file under
the terms of any one of the MPL, the GPL or the LGPL.

***** END LICENSE BLOCK *****
""" % ( { "copyright_year": _g_copyright_year,
          "company_name": _g_company_name,
        } )
_g_mpl_copyright_lines = _g_mpl_copyright.splitlines(0)


#
# Copyright files have comment lines that start like this:
#
#    "Copyright (c) 2000-2001 ActiveState Corporation.",
#    "Copyright (c) 2004 ActiveState Software Inc.",
#    '<div class="footer" align="center">Copyright &copy; 2000-__CURRENT_YEAR__ ActiveState Software Inc."'

#
# Regex's for finding copyright information in a file
#

class CopyrightUpdater:

    name = None
    rxLines = None
    backupSuffix = ".copyright.orig"

    def backup(self, filepath):
        bakFilename = filepath + self.backupSuffix
        if os.path.isfile(bakFilename):
            os.unlink(bakFilename)
        shutil.copy2(filepath, bakFilename)

    def handle(self, fileinfo, lines, lineNo):
        return False

    def determineNewlineFromLine(self, line):
        if line.endswith("\r\n"):
            return "\r\n"
        else:
            return line[-1]

class ActiveStateCopyrighter(CopyrightUpdater):

    name = "ActiveState"
    # Copyright (c) 2006 ActiveState Software Inc.
    rxASCopyright = re.compile(r"""^(?P<prefix>.*)(Copyright)\s+(?P<copyright_symbol>\(c\)|\&copy\;)\s+(?P<year_start>\d+)?(-|,)?(?P<year_end>\d*|__CURRENT_YEAR__)\s*(.*)(%s|activestate.com|ActiveState Corp|ActiveState Tool Corporation).*?(?P<suffix>[^\w\d.]*)$""" % (_g_company_name), re.IGNORECASE)
    # See LICENSE.txt for license details.
    rxLicenseRef  = re.compile(r"""^(?P<prefix>.*)(See the file LICENSE.txt for licensing information"""
                                               """|See LICENSE.txt for license details)"""
                                """.*?(?P<suffix>[^\w\d.]*)$""", re.IGNORECASE)

    mplBriefLicense = """The contents of this file are subject to the Mozilla Public License Version
1.1 (the "License"); you may not use this file except in compliance with
the License. You may obtain a copy of the License at
http://www.mozilla.org/MPL/
"""
    rxMPLBriefLicense = [ re.compile("^.*?%s.*?$" % (re.escape(x))) for x in mplBriefLicense.splitlines(0) ]

    def __init__(self):
        self.replacedFiles = set()

    def report(self, print_filenames=False):
        print("  Updated to use MPL: %d" % (len(self.replacedFiles)))
        if print_filenames:
            for name in sorted(self.replacedFiles):
                print("      %r" % (name, ))

    def replace(self, fileCommenter, lines, lineFrom, lineTo):
        """This will update existing license information with a new one."""
        filename = fileCommenter.filename

        # Work out the newline style from the line we replace.
        newline = self.determineNewlineFromLine(lines[lineFrom])

        # Modify this to contain our new copyright string.
        licenseLines = fileCommenter.commentLines(_g_mpl_copyright_lines,
                                                  newline)
        removed, added = fileCommenter.replaceLines(lines, licenseLines,
                                                    lineFrom, lineTo,
                                                    newline)

        log.info("%sUpdating license to MPL: %r", logpadding, filename)
        log.debug("\n- %s", "- ".join(removed))
        log.debug("\n+ %s", "+ ".join(added))
        if saveChanges:
            if makeFileBackup:
                self.backup(filename)
            file(filename, "w").writelines(lines)
        self.replacedFiles.add(fileCommenter.filename)

    def handle(self, fileCommenter, lines, lineNo):
        match = self.rxASCopyright.match(lines[lineNo])
        if match:
            prefix = match.group("prefix").strip()
            if prefix and fileCommenter.commentStart not in prefix:
                if prefix[0] in "\"'":
                    # in a string, not updating this!
                    log.warn("string license in: %r => %r",
                             fileCommenter.filename, lines[lineNo])
                    return False
            lineTo = lineNo+1
            if len(lines) > lineTo:
                line = lines[lineTo]
                if self.rxLicenseRef.match(line):
                    lineTo += 1
                else:
                    for i in range(len(self.rxMPLBriefLicense)):
                        if len(lines) <= (lineTo + i):
                            break
                        line = lines[lineTo + i]
                        rxLine = self.rxMPLBriefLicense[i]
                        if not rxLine.match(line):
                            break
                    else:
                        lineTo += len(self.rxMPLBriefLicense)
                        #print "  lineTo: %r" % (lines[lineTo], )
                self.replace(fileCommenter, lines, lineNo, lineTo)
            return True
        return False

class UnknownCopyrighter(CopyrightUpdater):
    name = "Unknown"
    rxPartialMatch = re.compile("^.*?(Copyright|\(c\)|__author__|License:).*?(?P<name>([\w\d]+\s+)+).*?$",
                                re.IGNORECASE)

    def __init__(self):
        self.unrecognizedLicenseFiles = set()

    def report(self, print_filenames=False):
        print("  Unknown copyrights: %d" % (len(self.unrecognizedLicenseFiles)))
        if print_filenames:
            for name in sorted(self.unrecognizedLicenseFiles):
                print("      %r" % (name, ))

    def handle(self, fileCommenter, lines, lineNo):
        if self.rxPartialMatch.match(lines[lineNo]):
            # Warn about this style
            self.unrecognizedLicenseFiles.add(fileCommenter.filename)
            log.info("%sSkipping unknown license : %r in %r",
                     logpadding, lines[lineNo], fileCommenter.filename)
            return True

class MPLCopyrighter(CopyrightUpdater):

    name = "MPL"
    # Use the first 11 lines of the mpl
    rxLines = [ re.compile(r"^.*%s.*$" % (re.escape(x))) for x in _g_mpl_copyright_lines[:2] ]

    def __init__(self):
        self.addedFiles = set()
        self.alreadyPatchedFiles = set()

    def report(self, print_filenames=False):
        print("  Added new license : %d" % (len(self.addedFiles)))
        if print_filenames:
            for name in sorted(self.addedFiles):
                print("      %r" % (name, ))
        print("  Already MPL'd     : %d" % (len(self.alreadyPatchedFiles)))
        if print_filenames:
            for name in sorted(self.alreadyPatchedFiles):
                print("      %r" % (name, ))

    def handle(self, fileCommenter, lines, lineNo):
        for i in range(len(self.rxLines)):
            if lineNo >= len(lines):
                break
            rxLine = self.rxLines[i]
            if not rxLine.match(lines[lineNo]):
                break
            lineNo += 1
        else:
            log.info("%sNA: Already under MPL %r",
                     logpadding, fileCommenter.filename)
            self.alreadyPatchedFiles.add(fileCommenter.filename)
            return True
        return False

    def add(self, fileCommenter):
        """Place copyright in comment at the start of the file."""
        lines = file(fileCommenter.filename, "r").readlines()
        # Work out the newline style from the line we just read.
        if lines:
            newline = self.determineNewlineFromLine(lines[0])
        else:
            newline = "\n"
        insertLineNo = 0
        if len(lines) > 0:
            insertLineNo = fileCommenter.skipSpecialLines(lines, 0)
        log.info("%sAdding MPL at line %d in %r",
                  logpadding, insertLineNo, fileCommenter.filename)

        if saveChanges:
            if makeFileBackup:
                self.backup(filename)
            licenseLines = fileCommenter.commentLines(_g_mpl_copyright_lines,
                                                      newline)
            # We add a separator newline if there is data immediately before.
            if insertLineNo > 0 and lines[insertLineNo-1].strip():
                licenseLines.insert(0, newline)
            # We add a separator newline if there is data immediately after.
            if insertLineNo < len(lines) and lines[insertLineNo].strip():
                licenseLines.append(newline)
            lines[insertLineNo:insertLineNo] = licenseLines
            file(fileCommenter.filename, "w").writelines(lines)
        self.addedFiles.add(fileCommenter.filename)


# The copyrighter that handles adding a license to unlicensed files.
_g_AddCopyrightHandler = MPLCopyrighter()

_g_CopyrightHandlers = [
    ActiveStateCopyrighter(),
    _g_AddCopyrightHandler,
    UnknownCopyrighter(),
]

# If verbose is on, warn when these strings are encountered in a file, yet
# did not match any of the above copyright regex's.
_g_rx_WarnOnSeeingThese = [ re.compile(r"^.*ActiveState Corp.*$", re.IGNORECASE),
                            re.compile(r"^.*Sophos.*$", re.IGNORECASE) ]


#---- support functions

def Revert(filename):
    #XXX should probably do error checking an raise an exception
    if saveChanges:
        return os.system('svn revert "%s"' % filename)


#---- Copyrighter handling map and functions

class CopyrighterFileHandler:

    commentStart = ''
    commentEnd = ''
    commentSpansMultipleLines = False
    commentLineDelimiter = ''
    alternativeSingleLineCommentStyle = ''

    def __init__(self, filename):
        self.filename = filename

    def skipSpecialLines(self, lines, lineNo):
        return lineNo

    def commentLines(self, lines, newline="\n"):
        commentedLines = []
        for i in range(len(lines)):
            line = []
            # line prefix
            if not self.commentSpansMultipleLines or i == 0:
                line.append("%s " % (self.commentStart))
            elif self.commentLineDelimiter:
                line.append(self.commentLineDelimiter)
            #else:
            #    line.append("   ")
            # copyright line
            line.append(lines[i])
            # line suffix
            if self.commentEnd and \
               (not self.commentSpansMultipleLines or i == len(lines)-1):
                line.append(" %s" % (self.commentEnd))
            # Make the line
            line.append(newline)
            commentedLines.append("".join(line))
        return commentedLines

    def replaceLines(self, lines, newlines, lineFrom, lineTo, newline):
        if not self.commentSpansMultipleLines:
            lines[lineFrom:lineTo] = newlines
            return lines[lineFrom:lineTo], newlines

        inMiddleOfComment = False
        singleLineCommentStyle = False

        line = lines[lineFrom].strip()
        if line and not line.startswith(self.commentStart):
            # See it's using an alternative comment style
            inMiddleOfComment = True
            if self.alternativeSingleLineCommentStyle:
                for line in lines[lineFrom:lineTo]:
                    if not line.strip().startswith(self.alternativeSingleLineCommentStyle):
                        break
                else:
                    singleLineCommentStyle = True
                    inMiddleOfComment = False
            # If there is a start comment on the previous line and it's
            # empty, we simply remove the previous line too.
            if lineFrom > 0:
                prevLine = lines[lineFrom -1].strip()
                #print "  Previous line: %r" % (prevLine, )
                if prevLine.startswith(self.commentStart) and not \
                   prevLine.endswith(self.commentStart):
                    leftOver = prevLine[len(self.commentStart):]
                    # The previous line is the start of the comment, if there
                    # is nothing worth saving on that line, then we eat it
                    # as well, making the license piece the start of a comment.
                    if not leftOver or leftOver == "*":
                        lineFrom -= 1
                        inMiddleOfComment = False
        if inMiddleOfComment:
            print "Expected comment style %r, got %r in %r" % (
                    self.commentStart, line[:10] + "...", self.filename)

        # If the last line we replace does not end the comment, we need
        # to keep the comment going on the next line!
        if not singleLineCommentStyle and \
           not lines[lineTo-1].strip().endswith(self.commentEnd):
            #print "Comment trails on in %r" % (self.filename, )
            #print "  %r" % (lines[lineTo-1], )
            #print "  %r" % (lines[lineTo], )
            #print "  %r" % (lines[lineTo+1], )
            #print "  %r" % (lines[lineTo+2], )
            if lineTo < len(lines):
                nextLine = lines[lineTo].lstrip()
                newlines.append(newline)
                newlines.append("%s%s%s" % (self.commentStart,
                                    self.commentLineDelimiter, nextLine))
                lineTo += 1
        oldlines = lines[lineFrom:lineTo]
        lines[lineFrom:lineTo] = newlines
        return oldlines, newlines

    def PatchIfNecessary(self):
        matchedCopyrightHandler = None
        lineNo = 0
        # read in the file
        lines = open(self.filename, "r").readlines()
        num_lines = len(lines)
        while lineNo < num_lines and (not linesCheckUpTo or lineNo < linesCheckUpTo):
            line = lines[lineNo]
            if len(line) > maxLineLength:
                log.info("%s%s:%s Line is too long, ignoring it.",
                         logpadding, self.filename, lineNo+1)
            else:
                # see if can find a copyright handler for this
                for copyrightHandler in _g_CopyrightHandlers:
                    if copyrightHandler.handle(self, lines, lineNo):
                        matchedCopyrightHandler = copyrightHandler
                        break
                else:
                    for reWarnMatch in _g_rx_WarnOnSeeingThese:
                        if reWarnMatch.search(line):
                            log.warn("%sCHECK: %s -l %s %s\n",
                                      logpadding, self.filename, lineNo+1,
                                      line)
                if matchedCopyrightHandler:
                    break
            lineNo += 1
        if not matchedCopyrightHandler and not performUpdateOnly:
            _g_AddCopyrightHandler.add(self)


_g_null_copywriter = set()
class NullCopyrighter(CopyrighterFileHandler):
    def PatchIfNecessary(self):
        # These types of files do not get updated.
        log.debug("%sSkipping patching '%s'...\n", logpadding, self.filename)
        _g_null_copywriter.add(self.filename)

class CCopyrighter(CopyrighterFileHandler):
    commentStart = '/*'
    commentEnd = '*/'
    commentSpansMultipleLines = True
    commentLineDelimiter = " * "
    alternativeSingleLineCommentStyle = "//"

class ScriptCopyrighter(CopyrighterFileHandler):
    commentStart = '#'
    def skipSpecialLines(self, lines, lineNo):
        if lines[lineNo].startswith("#!"):
            return lineNo + 1
        return lineNo

class NtBatchCopyrighter(CopyrighterFileHandler):
    commentStart = '@rem'
    def skipSpecialLines(self, lines, lineNo):
        if lines[lineNo].startswith('@echo off'):
            self.commentStart = 'rem'
            return lineNo + 1
        return lineNo

class XmlCopyrighter(CopyrighterFileHandler):
    commentStart = '<!--'
    commentEnd = '-->'
    commentSpansMultipleLines = True
    commentLineDelimiter = " "
    def skipSpecialLines(self, lines, lineNo):
        if lines[lineNo].startswith('<?xml version'):
            if lines[lineNo].find(">") > 0:
                return lineNo + 1
            while lines[lineNo].find(">") == -1:
                lineNo += 1
            return lineNo
        return lineNo


class PHPCopyrighter(XmlCopyrighter):
    """PHP comments styles are defined by the location in the script.

    They must be html comments outside of the "<?php" sections and
    script comments ("#" or "//") inside these php blocks.
    """
    def skipSpecialLines(self, lines, lineNo):
        i = lineNo
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            if not line:
                continue
            if line.startswith("#!"):
                # Skip the hash bang
                lineNo = i
            elif (line.startswith("<?php") or line.startswith("<?")) and \
                 not line.find(">") > 0:
                # Use php script comments
                lineNo = i
                self.commentStart = '#'
                self.commentEnd = ''
                self.commentSpansMultipleLines = False
                self.commentLineDelimiter = ''
                break
            else:
                break
        return lineNo

_copyrighterMap = {
    # filename regular expression : copyrighter class
    re.compile(r"^.*\.js$") : CCopyrighter,
    re.compile(r"^.*\.cpp$") : CCopyrighter,
    re.compile(r"^.*\.c$") : CCopyrighter,
    re.compile(r"^.*\.cxx$") : CCopyrighter,
    re.compile(r"^.*\.h$") : CCopyrighter,
    re.compile(r"^.*\.idl$") : CCopyrighter,
    re.compile(r"^.*\.idl_template$") : CCopyrighter,
    re.compile(r"^.*\.css$") : CCopyrighter,
    re.compile(r"^.*\.xs$") : CCopyrighter,
    re.compile(r"^.*\.rc$") : CCopyrighter,
    re.compile(r"^.*\.rc\.in$") : CCopyrighter,

    re.compile(r"^.*\.py$") : ScriptCopyrighter,
    re.compile(r"^.*\.rb$") : ScriptCopyrighter,
    re.compile(r"^.*\.pl$") : ScriptCopyrighter,
    re.compile(r"^.*\.PL$") : ScriptCopyrighter,
    re.compile(r"^.*\.pm$") : ScriptCopyrighter,
    re.compile(r"^.*\.tcl$") : ScriptCopyrighter,
    re.compile(r"^.*\.sh$") : ScriptCopyrighter,
    re.compile(r"^.*\.mak$") : ScriptCopyrighter,
    re.compile(r"^[mM]akefile.*$") : ScriptCopyrighter,
    re.compile(r"^Setup\.in$") : ScriptCopyrighter,
    re.compile(r"^Conscript$") : ScriptCopyrighter,
    re.compile(r"^conscript$") : ScriptCopyrighter,
    re.compile(r"^Construct$") : ScriptCopyrighter,
    re.compile(r"^.*\.ksf$") : ScriptCopyrighter,
    re.compile(r"^.*\.kkf$") : ScriptCopyrighter,
    re.compile(r"^.*\.udl$") : ScriptCopyrighter,
    # Komodo properties file.
    re.compile(r"^.*\.properties$") : ScriptCopyrighter,
    # Bk build script
    re.compile(r"^bk$") : ScriptCopyrighter,

    re.compile(r"^.*\.php$") : PHPCopyrighter,
    re.compile(r"^.*\.inc$") : PHPCopyrighter,

    re.compile(r"^.*\.xml$") : XmlCopyrighter,
    re.compile(r"^.*\.dtd$") : XmlCopyrighter,
    re.compile(r"^.*\.xsl$") : XmlCopyrighter,
    re.compile(r"^.*\.xul$") : XmlCopyrighter,
    re.compile(r"^.*\.rdf$") : XmlCopyrighter,
    re.compile(r"^.*\.dtd$") : XmlCopyrighter,
    re.compile(r"^.*\.html$") : XmlCopyrighter,
    re.compile(r"^.*\.htm$") : XmlCopyrighter,
    re.compile(r"^.*\.xhtml$") : XmlCopyrighter,
    re.compile(r"^.*\.rhtml$") : XmlCopyrighter,
    re.compile(r"^.*\.kpf$") : XmlCopyrighter,
    re.compile(r"^.*\.cix$") : XmlCopyrighter,
    re.compile(r"^.*\.rng$") : XmlCopyrighter,
    # komodo wix files
    re.compile(r"^.*\.wxs.in$") : XmlCopyrighter,
    re.compile(r"^.*\.wxi$") : XmlCopyrighter,
    # MacOSX plist settings.
    re.compile(r"^.*\.plist$") : XmlCopyrighter,
    re.compile(r"^.*\.plist.in$") : XmlCopyrighter,

    re.compile(r"^.*\.bat$") : NtBatchCopyrighter,

    re.compile(r"^.*\.pyc$") : NullCopyrighter,
    re.compile(r"^.*\.tip$") : NullCopyrighter,
    re.compile(r"^.*\.exe$") : NullCopyrighter,
    re.compile(r"^.*\.dll$") : NullCopyrighter,
    re.compile(r"^.*\.jpg$") : NullCopyrighter,
    re.compile(r"^.*\.rtf$") : NullCopyrighter,
    re.compile(r"^.*\.png$") : NullCopyrighter,
    re.compile(r"^.*\.gif$") : NullCopyrighter,
    re.compile(r"^.*\.ico$") : NullCopyrighter,
    re.compile(r"^.*\.xpm$") : NullCopyrighter,
    re.compile(r"^.*\.xcf$") : NullCopyrighter,
    re.compile(r"^.*\.bmp$") : NullCopyrighter,
    re.compile(r"^.*\.xls$") : NullCopyrighter,
    re.compile(r"^.*\.ppt$") : NullCopyrighter,
    re.compile(r"^.*\.doc$") : NullCopyrighter,
    re.compile(r"^.*\.pdf$") : NullCopyrighter,
    re.compile(r"^.*\.frm$") : NullCopyrighter,
    re.compile(r"^.*\.frx$") : NullCopyrighter,
    re.compile(r"^.*\.vbs$") : NullCopyrighter,
    re.compile(r"^.*\.vbp$") : NullCopyrighter,
    re.compile(r"^.*\.vsd$") : NullCopyrighter,
    re.compile(r"^.*\.dsp$") : NullCopyrighter,
    re.compile(r"^.*\.dsw$") : NullCopyrighter,
    re.compile(r"^.*\.psp$") : NullCopyrighter,
    re.compile(r"^.*\.psd$") : NullCopyrighter,
    re.compile(r"^.*\.nib$") : NullCopyrighter,
    re.compile(r"^.*\.xib$") : NullCopyrighter,
    re.compile(r"^.*\.json$") : NullCopyrighter,
    re.compile(r"^.*\.list$") : NullCopyrighter,
    re.compile(r"^.*\.pbxproj$") : NullCopyrighter,
    re.compile(r"^.*\.[1-8]$") : NullCopyrighter,    # man pages typically
    # have to skip .txt because they have arbitrary syntax
    re.compile(r"^.*\.txt$") : NullCopyrighter,
    re.compile(r"^.*\.stx$") : NullCopyrighter,
    re.compile(r"^TODO$") : NullCopyrighter,
    re.compile(r"^README$") : NullCopyrighter,
    re.compile(r"^MANIFEST$") : NullCopyrighter,
    re.compile(r"^Changes$") : NullCopyrighter,
    re.compile(r"^.*\.manifest$") : NullCopyrighter,
    re.compile(r"^.*\.xpt$") : NullCopyrighter,
    re.compile(r"^.*\.jar$") : NullCopyrighter,
    re.compile(r"^.*\.zip$") : NullCopyrighter,
    re.compile(r"^.*\.msi$") : NullCopyrighter,
    re.compile(r"^.*\.tar\.(gz|bz2)$") : NullCopyrighter,
    re.compile(r"^.*\.tgz$") : NullCopyrighter,
    re.compile(r"^tgzsrc$") : NullCopyrighter,

    # ignore patch and patch output files
    re.compile(r"^.*\.patch$") : NullCopyrighter,
    re.compile(r"^.*\.orig$") : NullCopyrighter,

    # hacks for weirdly-named Komodo files
    re.compile(r"^ko$") : NullCopyrighter,
    re.compile(r"^cons$") : NullCopyrighter,
}

_g_skipped_paths = set()
_g_unknown_files = set()

# Files with basenames matching these are skipped. The difference between
# these and the and _g_rx_skip_paths_matching is that there is no report
# (when using the "-f" option) generated for the skipping of these files.
_g_rx_skip_basenames = [
    re.compile(r"^CVS$"),
    re.compile(r"^\.svn$"),
    re.compile(r"^\.hg$"),
    re.compile(r"^\.consign$"),
    re.compile(r"^\.cvsignore$"),
    re.compile(r"^\.htaccess$"),
    re.compile(r"^\.htaccess$"),
    # Skip images
    re.compile(r"^.*\.png$"),
    re.compile(r"^.*\.gif$"),
    re.compile(r"^.*\.bmp$"),
    re.compile(r"^.*\.ico$"),
    re.compile(r"^.*\.jpg$"),
    re.compile(r"^.*\.xpm$"),
    re.compile(r"^.*\.exe$"),
    re.compile(r"^.*\.jar$"),
    re.compile(r"^.*\.zip$"),
]

# Use "/" as the path separator, which will be replaced by the real path
# separator on the platform which the script is run.
_g_rx_skip_paths_matching = [
    re.compile(r"^.*src/codeintel/play.*$"),
    re.compile(r"^.*src/codeintel/support/gencix/javascript/dojo/simplejson.*$"),
    re.compile(r"^.*src/codeintel/support/gencix/javascript/ECMAScript.xml$"),   # Unknown license.
    re.compile(r"^.*src/codeintel/test2/bits.*$"),
    re.compile(r"^.*src/codeintel/test2/scan_inputs.*$"),
    re.compile(r"^.*src/codeintel/test2/scan_outputs.*$"),
    re.compile(r"^.*src/codeintel/support/gencix/ruby/test.*$"),
    re.compile(r"^.*src/editor/catalogs.*$"),
    re.compile(r"^.*src/install/wix/aswixui.*$"), # leaving for Trent to look into
    re.compile(r"^.*src/SciMoz/npmac.cpp$"),   # mozilla copied file, customized by Shane
    re.compile(r"^.*src/samples.*$"),
    re.compile(r"^.*src/scintilla.*$"),
    re.compile(r"^.*src/sdk/share.*$"),
    re.compile(r"^.*src/silvercity.*$"),
    re.compile(r"^.*src/templates/.*?/.*$"), # All sub dirs under src/templates
    re.compile(r"^.*src/udl/skel/.*?/templates.*$"),
    re.compile(r"^.*src/udl/skel/MXML/mxml.dtd$"),   # Adobe MXML DTD
    # Trent's MIT licensed files.
    re.compile(r"^.*which.py$"),
    re.compile(r"^.*cmdln.py$"),
    re.compile(r"^.*applib.py$"),
    re.compile(r"^.*preprocess.py$"),
    re.compile(r"^.*platinfo.py$"),
    re.compile(r"^.*content.types$"),
    re.compile(r"^.*util/fixapplepython23.py$"),  # Came from python sources.
    re.compile(r"^.*util/desktop.py$"),
    re.compile(r"^.*util/markdown.py$"),
    re.compile(r"^.*util/p4lib.py$"),
]

# These matches are always updated, even if the path matches on of the
# _g_rx_skip_paths_matching regex's above.
_g_rx_skip_paths_matching_exceptions = [
    re.compile(r"^.*Conscript$"),  # We want to MPL all the Conscript files.
    re.compile(r"^.*src/samples/toolbox.p.kpf$"),
]

def AddCopyright(filename, runRecursivly=0, doSaveChanges=0, doUpdateOnly=0, doMakeFileBackup=0, doLinesCheckTo=10, maxLineLen=1000):
    """Add copyright to file if know how, else complain.
    If the file already has a copyright, ensure it is the correct one."""
    global _copyrighterMap, saveChanges, logpadding
    global performUpdateOnly, makeFileBackup, linesCheckUpTo, maxLineLength
    saveChanges = doSaveChanges
    performUpdateOnly = doUpdateOnly
    makeFileBackup = doMakeFileBackup
    linesCheckUpTo = doLinesCheckTo
    maxLineLength = maxLineLen

    if not os.path.exists(filename):
        log.error("%sFile path does not exist %r", logpadding, filename)
        return

    for rxPath in _g_rx_skip_basenames:
        if rxPath.match(os.path.basename(filename)):
            log.debug("%sPath: Skipping %r", logpadding, filename)
            return

    if not os.path.isfile(filename):
        if os.path.isdir(filename) and runRecursivly:
            log.debug("%sDirectory: Rescursing through %r...",
                      logpadding, filename)
            oldlogpadding = logpadding
            logpadding = logpadding + "  "
            for child in os.listdir(filename):
                child_filename = os.path.join(filename, child)
                AddCopyright(child_filename, runRecursivly, doSaveChanges, doUpdateOnly, doMakeFileBackup, doLinesCheckTo, maxLineLen)
            logpadding = oldlogpadding
        else:
            log.info("%sNot a file, ignoring %r", logpadding, filename)
        return

    unixPath = filename
    if sys.platform.startswith("win"):
        unixPath = path.replace(os.sep, "/")
    for rxPath in _g_rx_skip_paths_matching:
        if rxPath.match(unixPath):
            for rxPathException in _g_rx_skip_paths_matching_exceptions:
                if rxPathException.match(unixPath):
                    break
            else:
                _g_skipped_paths.add(filename)
                log.debug("%sSkipping %r", logpadding, filename)
                return

    log.debug("%sChecking %r", logpadding, filename)
    # Else we have a file, lets see if it matches our criteria
    for regex, commenter in _copyrighterMap.items():
        filenameMatch = regex.search(os.path.basename(filename))
        if filenameMatch:
            commenter(filename).PatchIfNecessary()
            break
    else:
        _g_unknown_files.add(filename)
        log.info("%sUnknown file type, ignoring '%s'.",
                 logpadding, filename)


#---- script mainline

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-b", "--backup", dest="backup_files",
                      action="store_true", help="Make a backup of any file that will change.")
    parser.add_option("-s", "--save", dest="save",
                      action="store_true", help="Save the changes made. Defaults to a dry-run.")
    parser.add_option("-l", "--lines", dest="num_lines",
                      action="store", type="int",
                      help="Checks first n number of lines for copyright message.")
    parser.add_option("-m", "--max-line-length", dest="max_line_length",
                      action="store", type="int",
                      help="Lines longer than this are ignored.")
    parser.add_option("-r", "--recursive", dest="recursive",
                      action="store_true", help="Recursively search directories.")
    parser.add_option("-u", "--update", dest="update_only",
                      action="store_true", help="Only update files that have existing license information.")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true", help="Verbose printing of actions")
    parser.add_option("-e", "--extra-verbose", dest="extra_verbose",
                      action="store_true", help="Extra verbose printing of actions")
    parser.add_option("-f", "--show-files-changed", dest="show_files_changed",
                      action="store_true", help="Print files changed in each category.")
    (opts, args) = parser.parse_args()
    if opts.extra_verbose:
        log.setLevel(logging.DEBUG)
    elif opts.verbose:
        log.setLevel(logging.INFO)
    if not opts.max_line_length:
        opts.max_line_length = maxLineLength

    log.debug("Settings:")
    log.debug("  Verbose:         %r", opts.verbose)
    log.debug("  Extra verbose:   %r", opts.extra_verbose)
    log.debug("  Backup:          %r", opts.backup_files)
    log.debug("  Lines:           %r", opts.num_lines)
    log.debug("  Max Line length: %r", opts.max_line_length)
    log.debug("  Recursive:       %r", opts.recursive)
    log.debug("  Dry run:         %r", not opts.save)
    log.debug("  Only update:     %r", opts.update_only)
    log.debug("  Show file changes: %r", opts.show_files_changed)
    log.debug("")

    if args:
        for filename in args:
            AddCopyright(filename, opts.recursive, opts.save, opts.update_only, opts.backup_files, opts.num_lines, opts.max_line_length)

        print "Results:"

        print("  Skipped paths     : %d" % (len(_g_skipped_paths)))
        if opts.show_files_changed:
            for name in sorted(_g_skipped_paths):
                print("      %-5s: %r" % (os.path.isdir(name) and "dir" or "file", name, ))

        for licenseHandler in _g_CopyrightHandlers:
            licenseHandler.report(opts.show_files_changed)

        print("  Ignored file types: %d" % (len(_g_null_copywriter)))
        if opts.show_files_changed:
            for name in sorted(_g_null_copywriter):
                print("      %r" % (name, ))

        print("  Unknown file types: %d" % (len(_g_unknown_files)))
        if opts.show_files_changed:
            for name in sorted(_g_unknown_files):
                print("      %r" % (name, ))
    else:
        parser.print_help()
