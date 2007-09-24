#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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
#       copyrighter.AddCopyright(filepath, beVerbose=0, runRecursivly=0, noChange=0, doUpdateOnly=0, doMakeFileBackup=0
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
#  - Mar 2, 2006
#    Add update capabilities for the ActivePython source.
#    Can now check all lines of a file, or a optional number of lines
#  - Feb 24, 2006
#    Add program control options: recursive, dry-run, no-backups, update-only
#    Tweak regex and global variables for better updating
#    Add additional verbose logging and logging formatting
#

import os, sys, time, re, shutil


#---- globals
# Options that are set through the command line
verbose           = 0   # Show me what is happening in detail
doNotMakesChanges = 0   # Run, but don't make any changes to files
performUpdateOnly = 0   # Only perform updates on existing files with copyright
makeFileBackup    = 0   # Make a backup of a file if it will be changed
linesCheckUpTo    = None  # Check first n lines for copyright information
maxLineLength     = 1000  # Any line read in that is longer than this is ignored

# Default runtime settings
out = sys.stdout
logpadding = ''         # Used for pretty printing (verbose)

# The copyright message:
#   *Should* be able to make this an arbitrary number of lines.
# Note: The additional lines are only added to files where these is no
#       existing ActiveState copyright found. Does not apply when the
#       update only ( -u ) argument is used.
_new_copyright_year         = str(time.localtime()[0])
_new_copyright_company_name = "ActiveState Software Inc"
_copyright = [
    "Copyright (c) %s %s." % (_new_copyright_year, _new_copyright_company_name),
    "See the file LICENSE.txt for licensing information.",
]

# These are used to check if a file already has some type of ActiveState copyright
_oldCopyrightStartMark = "Copyright"
_oldCopyrightCompanyNames = [ "ActiveState", "Sophos" ]

#
# Old Copyright Examples this code will replace
#
#    "Copyright (c) 2000-2001 ActiveState Corporation.",
#    "Copyright (c) 2004 ActiveState Corp, a division of Sophos Plc.",
#    "Copyright (c) 2000-2001 ActiveState SRL.",
#    "Copyright (C) 2000-2005 ActiveState Corp.",
#    "Copyright (c) 2004 Sophos Inc.",
#    "Copyright (c) 2004 Sophos.",
#    '<div class="footer" align="center">Copyright &copy; 2000-__CURRENT_YEAR__ ActiveState Corp."'

#
# Regex's for finding copyright information in a file
#
# reOldCopyrightedPartialMatch:
#      Will be used to see if a file line has some form of ActiveState
#      copyright message.
# reNewCopyrightedPartialMatch:
#      If a file line has some form of ActiveState copyright (see above),
#      then this checks to see if it's already got the right company name.
# reCopyrightMatches:
#      Will be used to break up the copyright line and is used in
#      constructing what the new copyright message will look like.
#
reOldCopyrightedPartialMatch = []
reNewCopyrightedPartialMatch = re.compile("(?P<year_end>\d*|__CURRENT_YEAR__)\s+%s" % (_new_copyright_company_name))
reCopyrightMatches = []
for companyName in _oldCopyrightCompanyNames:
    reCopyrightMatches.append(re.compile(r"""^(?P<prefix>.*)(Copyright)\s+(?P<copyright_symbol>\(c\)|\&copy\;)\s+(?P<year_start>\d+)(-)*?(?P<year_end>\d*|__CURRENT_YEAR__)\s+(.*)(%s).*?(?P<suffix>[^\w\d.]*)$""" % \
                                        (companyName),
                                        re.IGNORECASE) )
    reOldCopyrightedPartialMatch.append(re.compile("%s.*%s" % (_oldCopyrightStartMark, companyName), re.IGNORECASE))

# If verbose is on, warn when these strings are encountered in a file, yet
# did not match any of the above copyright regex's.
reWarnOnSeeingThese = [ re.compile(r"^.*ActiveState Corp.*$", re.IGNORECASE),
                        re.compile(r"^.*Sophos.*$", re.IGNORECASE) ]


#---- support functions

def P4Edit(filename):
    #XXX should probably do error checking an raise an exception
    if not doNotMakesChanges:
        return os.system('p4 edit "%s"' % filename)


def P4Revert(filename):
    #XXX should probably do error checking an raise an exception
    if not doNotMakesChanges:
        return os.system('p4 revert "%s"' % filename)


def CheckCopyrighted(filename):
    """Return (copyrighted, updateLineNumbers)
        copyrighted == 'correctly' if file is correctly copyrighted.
        copyrighted == 'incorrectly' if file is incorrectly copyrighted.
            updateLineNumbers will contain a list of lines that need fixing.
        copyrighted = '' where no copyright was found

       Note: Depending upon the global variable linesCheckUpTo, may only check
             the first linesCheckUpTo lines of the file for a copyright message.
    """
    updateLineNumbers = []
    copyrighted = ""
    lineNumber = 0
    # read in the file
    fin = open(filename, "r")
    try:
        line = fin.readline()
        while line and (not linesCheckUpTo or lineNumber < linesCheckUpTo):
            if len(line) > maxLineLength:
                if verbose > 1:
                    out.write("%s** WARNING: %s:%s Line is too long, ignoring it.\n\n" % \
                              (logpadding, filename, lineNumber+1))
            else:
                # see if can find a copyright at all
                for rePartialCopyrightMatch in reOldCopyrightedPartialMatch:
                    if rePartialCopyrightMatch.search(line):
                        if reNewCopyrightedPartialMatch.search(line):
                            # first line of copyright is correct
                            if not copyrighted:
                                copyrighted = "correctly"  # an exact match
                        else:
                            # a match, but it's an incorrect match
                            copyrighted = "incorrectly"
                            updateLineNumbers.append(lineNumber+1)
                        break
                else:
                    if verbose:
                        for reWarnMatch in reWarnOnSeeingThese:
                            if reWarnMatch.search(line):
                                out.write("%s** CHECK: %s -l %s %s\n" % \
                                          (logpadding, filename, lineNumber+1, \
                                           line))
            lineNumber += 1     # Increment before break to give proper line number
            line = fin.readline()
        if verbose:
            if copyrighted == "incorrectly":
                out.write(logpadding +
                          "Found *incorrect* ActiveState copyright in '%s' at "\
                          "lines %r.\n" % (filename, updateLineNumbers))
            elif copyrighted == "correctly":
                if verbose > 1:
                    out.write(logpadding +
                              "Found correct ActiveState copyright in '%s' at "\
                              "line %r.\n" % (filename, updateLineNumbers))
            else:
                if verbose > 1:
                    out.write(logpadding +
                              "No ActiveState copyright found in '%s'\n" % filename)
        return (copyrighted, updateLineNumbers)
    finally:
        fin.close()



#---- Copyrighter handling map and functions

class Copyrighter:
    def __init__(self, filename, startLine=0):
        self.filename = filename
        self.backupSuffix = ".copyright.orig"
        self.startLine = startLine  # line at which to start copyright
        self.commentStart = ''
        self.commentEnd = ''
        self.commentSpansMultipleLines = False

    def PatchIfNecessary(self):
        global _copyright, verbose
        copyrighted, lineNumbers = CheckCopyrighted(self.filename)
        if copyrighted == "correctly":
            if verbose > 1:
                out.write(logpadding +
                    "Skipping '%s'. It is already copyrighted "\
                    "correctly.\n" % self.filename)
        elif copyrighted == "incorrectly":
            failed, failedLine, failedLineNumber = \
                    self._PrepareAndUpdate(lineNumbers)
            if (failed):
                out.write(
                    "%s *** ERROR: Line %d. Could not update copyright: %s" \
                    % (logpadding, failedLineNumber, failedLine))
        elif not performUpdateOnly:
            failed = self._PrepareAndPatch()
            if (failed):
                out.write(logpadding +
                    "*** ERROR: '%s' could not be copyrighted properly.You "\
                    "must manually resolve this.\n\n" % self.filename)

    def _PrepareAndPatch(self):
        # create a backup
        if not doNotMakesChanges and makeFileBackup:
            bakFilename = self.filename + self.backupSuffix
            if os.path.isfile(bakFilename):
                os.unlink(bakFilename)
            shutil.copy2(self.filename, bakFilename)
        # read in the file 
        fin = open(self.filename, "r")
        # Why read all lines, we only want the first few.
        lines = fin.readlines()
        fin.close()
        # p4 edit and patch the file
        P4Edit(self.filename)
        out.write(logpadding +
                  "Patching '%s' with the copyright message...\n" %\
                  self.filename)
        failed = 0
        if not doNotMakesChanges:
            fout = open(self.filename, "w")
        else:
            fout = None
        for i in range(len(lines)):
            if i == self.startLine:
                failed = self._AddCopyright(fout)
                if failed:
                    break
            if not doNotMakesChanges:
                fout.write(lines[i])
        if not doNotMakesChanges:
            fout.close()
        if failed:
            P4Revert(self.filename)
        return failed

    def _PrepareAndUpdate(self, lineNumbers):
        # create a backup
        updatingLine = ''
        updatingLineNumber = -1
        if not doNotMakesChanges and makeFileBackup:
            bakFilename = self.filename + self.backupSuffix
            if os.path.isfile(bakFilename):
                os.unlink(bakFilename)
            shutil.copy2(self.filename, bakFilename)
        # read in the file 
        fin = open(self.filename, "r")
        lines = fin.readlines()
        fin.close()
        # p4 edit and patch the file
        P4Edit(self.filename)
        failed = False
        for lineNumber in lineNumbers:
            failed = self._UpdateCopyright(lines, lineNumber)
            if failed:
                updatingLine = lines[lineNumber - 1]
                updatingLineNumber = lineNumber
                P4Revert(self.filename)
                break
        else:
            if verbose > 1:
                out.write(logpadding +
                          "Updated copyright message in '%s'...\n" %
                          self.filename)
        if not doNotMakesChanges:
            fout = open(self.filename, "w")
            for line in lines:
                fout.write(line)
            fout.close()
        return failed, updatingLine, updatingLineNumber

    def _UpdateCopyright(self, lines, lineNumber):
        """This will update license information if a license already exists.
        It will update the license and use any existing copyright dates as appropriate.
        """
        re_match = None
        #lastLineNumber  = lineNumber + 2
        #if lastLineNumber >= len(lines):
        #    lastLineNumber = len(lines) - 1
        #for checkLineNumber in range(firstLineNumber, lastLineNumber+1):
        checkLine = lines[lineNumber - 1]
        #if not re_match:
        for reExpression in reCopyrightMatches:
            re_match = reExpression.search(checkLine)
            if re_match:
                break
        if re_match and checkLine.find(_new_copyright_company_name) == -1:
            # Modify this to contain our new copyright string
            newLine = re_match.group("prefix")     # The comment tag (optional)
            if re_match.group("year_start") and re_match.group("year_start") != _new_copyright_year:   # Year first copyrighted.
                new_copyright_year = _new_copyright_year
                if re_match.group("year_end") == '__CURRENT_YEAR__':
                    new_copyright_year = re_match.group("year_end")
                newLine += _copyright[0].replace(_new_copyright_year,
                                                 "%s-%s" % (re_match.group("year_start").strip(),
                                                 new_copyright_year))
            else:
                newLine += _copyright[0]
            if re_match.group("copyright_symbol") == r'&copy;':
                newLine = newLine.replace('(c)', '&copy;')
            #suffix = re_match.group("suffix").strip()
            #if suffix and self.commentEnd:
            #    commentEndPos = suffix.rfind(self.commentEnd)
            #    if commentEndPos >= 0:
            #        newLine += " " + suffix[commentEndPos:]
            if re_match.group("suffix"):
                newLine += re_match.group("suffix")
                # The end comment tag (optional)
            #else:
            #    out.write( "*" * 80  + "\n" )
            #    out.write( "Unknown suffix: '%s'\n" % (re_match.group("suffix").strip()) )
            #    out.write( "*" * 80  + "\n" )
            lines[lineNumber] = newLine + "\n"
            if verbose:
                out.write(logpadding + "- %s" % (checkLine))
                out.write(logpadding + "+ %s" % (lines[lineNumber]))
        return (re_match == None)

    def _AddCopyright(self, fout):
        """Place copyright in comment at the start of the file."""
        linesToAdd = []
        for i in range(len(_copyright)):
            line = []
            # line prefix
            if not self.commentSpansMultipleLines or i == 0:
                line.append("%s " % (self.commentStart))
            else:
                line.append("   ")
            # copyright line
            line.append(_copyright[i])
            # line suffix
            if self.commentEnd and \
               (not self.commentSpansMultipleLines or i == len(_copyright)-1):
                line.append(" %s" % (self.commentEnd))
            # Make the line
            line.append("\n")
            linesToAdd.append("".join(line))
        linesToAdd.append("\n")
        if not doNotMakesChanges:
            fout.write("".join(linesToAdd))
        if verbose:
            joiner = logpadding + "+ "
            out.write(logpadding + "+ " + joiner.join(linesToAdd))
        return 0



class NullCopyrighter(Copyrighter):
    def PatchIfNecessary(self):
        if verbose > 1:
            out.write(logpadding +"Skipping patching '%s'...\n" % self.filename)
    def _PrepareAndPatch(self):
        pass


class CCopyrighter(Copyrighter):
    def __init__(self, filename, startLine=0):
        Copyrighter.__init__(self, filename, startLine)
        self.commentStart = '/*'
        self.commentEnd = '*/'
        self.commentSpansMultipleLines = True

class ScriptCopyrighter(Copyrighter):
    def __init__(self, filename, startLine=0):
        """Place copyright in script-style comment at start of file."""
        # startLine==1 to skip the shebang line, if it has one
        fin = open(filename, "r")
        firstLine = fin.readline()
        fin.close()
        if firstLine.startswith("#!"):
            startLine = 1
        else:
            startLine = 0
        Copyrighter.__init__(self, filename, startLine)
        self.commentStart = '#'

    def insertCommentedLine(self, lines, lineNumber, newLine):
        lines.insert(lineNumber, "# %s\n" % (newLine))

class NtBatchCopyrighter(Copyrighter):
    def __init__(self, filename, startLine=0):
        Copyrighter.__init__(self, filename, startLine)
        self.commentStart = '@rem'

    def insertCommentedLine(self, lines, lineNumber, newLine):
        lines.insert(lineNumber, "@rem %s\n" % (newLine))

class XmlCopyrighter(Copyrighter):
    """Place copyright in XML-style comment at start of file."""
    def __init__(self, filename, startLine=0):
        # startLine==1 to skip the XML magic number line
        #  (with some expceptions)
        #XXX This assumes that the XML magic number line *ends* on the first
        #    line. I.e. there is no checking if this comment gets plopped
        #    into the inside of a tag.
        if filename.lower().endswith(".dtd") or \
           filename.lower().endswith(".kpf"):
            startLine = 0
        else:
            startLine = 1
        Copyrighter.__init__(self, filename, startLine)
        self.commentStart = '<!--'
        self.commentEnd = '-->'
        self.commentSpansMultipleLines = True


_copyrighterMap = {
    # filename regular expression : copyrighter class
    "^.*\.js$" : CCopyrighter,
    "^.*\.cpp$" : CCopyrighter,
    "^.*\.c$" : CCopyrighter,
    "^.*\.cxx$" : CCopyrighter,
    "^.*\.h$" : CCopyrighter,
    "^.*\.idl$" : CCopyrighter,
    "^.*\.idl_template$" : CCopyrighter,
    "^.*\.css$" : CCopyrighter,
    "^.*\.xs$" : CCopyrighter,
    "^.*\.rc$" : CCopyrighter,
    "^.*\.rc.in$" : CCopyrighter,

    "^.*\.py$" : ScriptCopyrighter,
    "^.*\.rb$" : ScriptCopyrighter,
    "^.*\.pl$" : ScriptCopyrighter,
    "^.*\.PL$" : ScriptCopyrighter,
    "^.*\.pm$" : ScriptCopyrighter,
    "^.*\.tcl$" : ScriptCopyrighter,
    "^.*\.sh$" : ScriptCopyrighter,
    "^.*\.mak$" : ScriptCopyrighter,
    "^[mM]akefile.*$" : ScriptCopyrighter,
    "^Setup.in$" : ScriptCopyrighter,
    "^Conscript$" : ScriptCopyrighter,
    "^conscript$" : ScriptCopyrighter,
    "^Construct$" : ScriptCopyrighter,

    "^.*\.xml$" : XmlCopyrighter,
    "^.*\.dtd$" : XmlCopyrighter,
    "^.*\.xsl$" : XmlCopyrighter,
    "^.*\.xul$" : XmlCopyrighter,
    "^.*\.rdf$" : XmlCopyrighter,
    "^.*\.dtd$" : XmlCopyrighter,
    "^.*\.html$" : XmlCopyrighter,
    "^.*\.htm$" : XmlCopyrighter,
    "^.*\.kpf$" : XmlCopyrighter,

    "^.*\.bat$" : NtBatchCopyrighter,

    "^.*\.exe$" : NullCopyrighter,
    "^.*\.dll$" : NullCopyrighter,
    "^.*\.jpg$" : NullCopyrighter,
    "^.*\.rtf$" : NullCopyrighter,
    "^.*\.png$" : NullCopyrighter,
    "^.*\.gif$" : NullCopyrighter,
    "^.*\.ico$" : NullCopyrighter,
    "^.*\.xpm$" : NullCopyrighter,
    "^.*\.bmp$" : NullCopyrighter,
    "^.*\.xls$" : NullCopyrighter,
    "^.*\.ppt$" : NullCopyrighter,
    "^.*\.doc$" : NullCopyrighter,
    "^.*\.xpt$" : NullCopyrighter,
    "^.*\.tar\.gz$" : NullCopyrighter,
    "^.*\.frm$" : NullCopyrighter,
    "^.*\.frx$" : NullCopyrighter,
    "^.*\.vbs$" : NullCopyrighter,
    "^.*\.vbp$" : NullCopyrighter,
    "^.*\.vsd$" : NullCopyrighter,
    "^.*\.psp$" : NullCopyrighter,
    "^.*\.psd$" : NullCopyrighter,
    "^.*\.msi$" : NullCopyrighter,
    "^.*\.[1-8]$" : NullCopyrighter,    # man pages typically
    # have to skip .txt because they have arbitrary syntax
    "^.*\.txt$" : NullCopyrighter,    
    "^.*\.stx$" : NullCopyrighter,    
    "^TODO$" : NullCopyrighter,    
    "^README$" : NullCopyrighter,    
    "^MANIFEST$" : NullCopyrighter,    
    "^Changes$" : NullCopyrighter,    

    # hacks for weirdly-named Komodo files
    "^.*\.properties$" : NullCopyrighter,    
    "^ko$" : NullCopyrighter,    
    "^cons$" : NullCopyrighter,    
}


def AddCopyright(filename, beVerbose=0, runRecursivly=0, noChange=0, doUpdateOnly=0, doMakeFileBackup=0, doLinesCheckTo=10, maxLineLen=1000):
    """Add copyright to file if know how, else complain.
    If the file already has a copyright, ensure it is the correct one."""
    global _copyrighterMap, verbose, doNotMakesChanges, logpadding
    global performUpdateOnly, makeFileBackup, linesCheckUpTo, maxLineLength
    verbose = beVerbose
    doNotMakesChanges = noChange
    performUpdateOnly = doUpdateOnly
    makeFileBackup = doMakeFileBackup
    linesCheckUpTo = doLinesCheckTo
    maxLineLength = maxLineLen
    if verbose > 1:
        out.write(logpadding + "-"*40 + "\n")
        out.write(logpadding + "Checking file '%s'...\n" % filename)
    if not os.path.exists(filename):
        out.write(logpadding + "*** ERROR: file path does not exist '%s'\n" % (filename))
        return
    if not os.path.isfile(filename):
        if os.path.isdir(filename) and runRecursivly:
            if verbose > 1:
                out.write(logpadding + "* Directory: Rescursing through '%s'...\n" % (filename))
            oldlogpadding = logpadding
            logpadding = logpadding + "  "
            for child in os.listdir(filename):
                child_filename = os.path.join(filename, child)
                AddCopyright(child_filename, beVerbose, runRecursivly, noChange, doUpdateOnly, doMakeFileBackup, doLinesCheckTo, maxLineLen)
            logpadding = oldlogpadding
        else:
            if verbose > 1:
                out.write(logpadding + "* WARNING: this is not a file, ignoring it '%s'.\n" % (filename))
        return
    # Else we have a file, lets see if it matches our criteria
    for regexStr, copyrighterClass in _copyrighterMap.items():
        filenameMatch = re.compile(regexStr).search(os.path.basename(filename))
        if filenameMatch:
            copyrighterClass(filename).PatchIfNecessary()
            break
    else:
        if verbose > 1:
            out.write(logpadding + "* WARNING: Unknown file extension, ignoring this file '%s'.\n" % (filename))


#---- script mainline

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-b", "--backup", dest="backup_files",
                      action="store_true", help="Make a backup of any file that will change.")
    parser.add_option("-d", "--dry-run", dest="dry_run",
                      action="store_true", help="Do not make any changes.")
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
    (opts, args) = parser.parse_args()
    if opts.extra_verbose:
        verboseType = 2
    elif opts.verbose:
        verboseType = 1
    else:
        verboseType = 0
    if not opts.max_line_length:
        opts.max_line_length = maxLineLength
    if verboseType:
        out.write("*" * 40 + "\n")
        out.write("Settings\n")
        out.write("  Verbose:         %r\n" % (opts.verbose))
        out.write("  Extra verbose:   %r\n" % (opts.extra_verbose))
        out.write("  Backup:          %r\n" % (opts.backup_files))
        out.write("  Lines:           %r\n" % (opts.num_lines))
        out.write("  Max Line length: %r\n" % (opts.max_line_length))
        out.write("  Recursive:       %r\n" % (opts.recursive))
        out.write("  Dry run:         %r\n" % (opts.dry_run))
        out.write("  Only update:     %r\n" % (opts.update_only))
    if args:
        for filename in args:
            AddCopyright(filename, verboseType, opts.recursive, opts.dry_run, opts.update_only, opts.backup_files, opts.num_lines, opts.max_line_length)
    else:
        parser.print_help()
