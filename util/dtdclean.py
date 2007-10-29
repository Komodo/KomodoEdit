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

"""
    Clean DTD references from an XML file.

    Command Line Usage:
        dtdclean [<options>...] <xmlfile> <dtdfile>

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.
        -v, --verbose   Give verbose output for errors.

        -f, --force     Allow overwriting of existing files.
        -i              Do in-place replacement of <xmlfile>. This
                        implies "--force".
        -o <outfile>    Write output to the given file. By default
                        output if dumped to stdout.
"""

import os
import sys
import getopt
import types
import re
import pprint


#---- exceptions

class DTDCleanError(Exception):
    pass



#---- global data

_version_ = (0, 1, 0)



#---- internal logging facility

class Logger:
    DEBUG, INFO, WARN, ERROR, FATAL = range(5)
    def __init__(self, name, level=None, streamOrFileName=sys.stderr):
        self.name = name
        if level is None:
            self.level = self.WARN
        else:
            self.level = level
        if type(streamOrFileName) == types.StringType:
            self.stream = open(streamOrFileName, 'w')
            self._opennedStream = 1
        else:
            self.stream = streamOrFileName
            self._opennedStream = 0
    def __del__(self):
        if self._opennedStream:
            self.stream.close()
    def _getLevelName(self, level):
        levelNameMap = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARN: "WARN",
            self.ERROR: "ERROR",
            self.FATAL: "FATAL",
        }
        return levelNameMap[level]
    def setLevel(self, level):
        self.level = level
    def isEnabled(self, level):
        return level >= self.level
    def isDebugEnabled(self): return self.isEnabled(self.DEBUG)
    def isInfoEnabled(self): return self.isEnabled(self.INFO)
    def isWarnEnabled(self): return self.isEnabled(self.WARN)
    def isErrorEnabled(self): return self.isEnabled(self.ERROR)
    def isFatalEnabled(self): return self.isEnabled(self.FATAL)
    def log(self, level, msg, *args):
        if level < self.level:
            return
        message = "%s: %s: " % (self.name, self._getLevelName(level).lower())
        message = message + (msg % args) + "\n"
        self.stream.write(message)
        self.stream.flush()
    def debug(self, msg, *args):
        self.log(self.DEBUG, msg, *args)
    def info(self, msg, *args):
        self.log(self.INFO, msg, *args)
    def warn(self, msg, *args):
        self.log(self.WARN, msg, *args)
    def error(self, msg, *args):
        self.log(self.ERROR, msg, *args)
    def fatal(self, msg, *args):
        self.log(self.FATAL, msg, *args)

log = Logger("dtdclean", Logger.WARN)



#---- internal support stuff

def _getDTDEntities(dtdfile):
    # Parse lines like this:
    #   <!ENTITY window.title               "Web Services Bookmarks">
    patterns = [
        re.compile(r'^\s*<!ENTITY\s+(?P<name>[\w\.]+)\s+"(?P<value>.*?)"\s*>\s*$'),
        re.compile(r"^\s*<!ENTITY\s+(?P<name>[\w\.]+)\s+'(?P<value>.*?)'\s*>\s*$")
    ]

    entities = {}
    for line in open(dtdfile, 'r').readlines():
        match = None
        for pattern in patterns:
            match = pattern.search(line)
            if match: break

        if match:
            log.debug("found dtd entity on line: %r", line)
            name = match.group("name")
            value = match.group("value")
            if name in entities:
                raise DTDCleanError("it looks like the entity '%s' is "\
                                    "defined twice in %r" % (name, dtdfile))
            entities[name] = value
        elif line.find("ENTITY") != -1:
            msg = "A line containing 'ENTITY' did not successfully parse "\
                  "as a DTD entity. This looks suspicious: line=%r" % line
            raise DTDCleanError(msg)
        else:
            log.debug("skip dtd line: %r", line)
        
    return entities



#---- module API

def dtdclean(xmlfile, dtdfile, outfile=sys.stdout, force=0):
    """Clean the given XML file of given DTD references.

    "xmlfile" is the XML file to clean of DTD references.
    "dtdfile" is the DTD file of references to clean.
    "outfile" is a filename or stream to which to write the cleaned XML
        output (defaults to sys.stdout).
    "force" is boolean to allow overwriting an existing file (default is
        false).

    The <!DOCTYPE...> reference the <dtdfile> is removed, if possible.
    """
    log.info("dtdclean(xmlfile=%r, dtdfile=%r)", xmlfile, dtdfile)

    # Get the set of DTD references.
    entities = _getDTDEntities(dtdfile)
    log.debug("DTD entities: %s", pprint.pformat(entities))

    # Get the content to process (must get this before preping the
    # outfile, because we may be doing inplace replacement).
    fin = open(xmlfile, 'r')
    xmlContent = fin.read()
    fin.close()

    # Prep 'fout', the output steam.
    if type(outfile) in types.StringTypes:
        if os.path.exists(outfile):
            if force:
                os.chmod(outfile, 0777)
                os.remove(outfile)
            else:
                raise DTDCleanError("'%s' already exists, use '--force' to "\
                                    "allow overwrite" % outfile)
        fout = open(outfile, 'w')
    else:
        fout = outfile

    # Clean the XML content.
    cleanContent = xmlContent
    for name, value in entities.items():
        ref = "&"+name+";"
        cleanContent = cleanContent.replace(ref, value)

    # Warn if there are still DTD references remaining in the cleaned
    # content.
    remaining = re.findall(r"&[\w\.]+;", cleanContent)
    remaining = [r for r in remaining if r not in ("&amp;", "&gt;", "&lt;")]
    if remaining:
        log.warn("Not all DTD references were cleaned from '%s'. "\
                 "The following remain: %s", xmlfile, remaining)

    # Drop the <!DOCTYPE...> reference to the DTD file, e.g.:
    #   <!DOCTYPE window SYSTEM "chrome://komodo/locale/webservices/bmedit.dtd">
    pattern = re.compile(r'^\s*<!DOCTYPE\s+\w+\s+\w+\s+".*?%s"\s*>\s*$'\
                         % re.escape(os.path.basename(dtdfile)), re.M)
    match = pattern.search(cleanContent)
    if match:
        log.info("drop DOCTYPE ref to '%s': %r", os.path.basename(dtdfile),
                 cleanContent[match.start():match.end()])
        cleanContent = cleanContent[:match.start()] + cleanContent[match.end():]
    else:
        log.warn("did not find a reference to '%s' in '%s'",
                 os.path.basename(dtdfile), xmlfile)

    # Write out the new content.
    fout.write(cleanContent)
    if fout != outfile:
        fout.close()



#---- mainline

def main(argv):
    # Process options.
    try:
        optlist, args = getopt.getopt(argv[1:], "hVvo:if",
            ["help", "version", "verbose", "force"])
    except getopt.GetoptError, msg:
        sys.stderr.write("dtdclean: error: %s. Your invocation was: %s\n"\
                         % (msg, argv))
        sys.stderr.write("See 'dtdclean --help'.\n")
        return 1
    opts = [opt for opt, optarg in optlist]
    if "-o" in opts and "-i" in opts:
        sys.stderr.write("dtdclean: error: cannot specify both '-i' and "\
                         "'-o' options\n")
        return 1

    force = 0
    inplace = 0
    outfile = sys.stdout
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return 0
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(i) for i in _version_])
            sys.stderr.write("dtdclean %s\n" % ver)
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(log.DEBUG)
            verbose = 1
        elif opt in ("-f", "--force"):
            force = 1
        elif opt == "-o":
            outfile = optarg
        elif opt == "-i":
            inplace = 1
            force = 1

    # Process arguments.
    if len(args) != 2:
        sys.stderr.write("dtdclean: error: incorrect number of "\
                         "arguments: argv=%r\n" % argv)
        return 1
    xmlfile, dtdfile = args
    if inplace:
        outfile = xmlfile

    try:
        dtdclean(xmlfile, dtdfile, outfile, force)
    except DTDCleanError, ex:
        if log.isDebugEnabled():
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write("dtdclean: error: %s\n" % str(ex))

if __name__ == "__main__":
    __file__ = sys.argv[0]
    sys.exit( main(sys.argv) )


