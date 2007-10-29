#!/usr/bin/env python -w
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

# Run "copyrighter.pl" over the Komodo tree.
#
# This script should be used to run this because it encodes which files
# in the Komodo tree should *not* be copyrighted, i.e. third party files.
#
# Usage:
#   1. cd <komodo root dir>
#   2. ensure you don't have an files opened from Perforce
#   3. python util/run_copyrighter.py <start directory>
#

import os, sys, getopt, glob


#---- LIST OF KOMODO FILES THAT SHOULD NOT BE COPYRIGHTED
# Just list the file basename. This script will ensure these
# are not inspecific (i.e. ensure there are not two "platform.py"s).
#
# If there *are* conflicts then this script will have to be extended
# to handle that.
#

thingsToSkip = [
    # NOTE: must use Unix-like dir separators
    "cons.pl",
    "platform.py",
    "util/lxr/...",
    "util/installer/...",
    "bin/tm*.py",
    "bin/p4x",
    "bin/p4d2p.pl",
    "src/chrome/komodo/content/doc/ActivePerl/...",
    "src/chrome/komodo/content/doc/python/...",
    "src/chrome/komodo/content/python/kjpylint/...",
    "src/chrome/komodo/content/python/dav*.py",
    "src/chrome/komodo/content/python/qp_xml.py",
    "src/chrome/komodo/content/perl/Net/Cmd.pm",
    "src/chrome/komodo/content/perl/Net/FTP.pm",
    "src/chrome/komodo/content/perl/ASRemote/*.pm",
    "src/debugger/xmlrpc/...",
    "src/editor/idle/*.py",   # except __init__.py
    "src/popen/include/...",
    "src/scintilla/...",
    "src/tidy/...",
    "src/silo/...",
    "src/xmltok/...",
    "src/xslt/...",  # because it is huge and out of my control
    "src/doc/footer.html",  # because this isn't a real .html file
    "src/doc/header.html",  # because this isn't a real .html file
    "src/doc/rdfgen/demo/...",
    "prebuilt/...",
    "internal-docs/...",  # not for release so not point
    "MSI/*.vbs",            # because I don't know how to comment these
    "src/pyxpcom/xpcom/test/output/...",
]



#---- globals

dryrun = 0
verbose = 0
out = sys.stdout    # should write all output to this handle



#---- support routines

def P4Have(fileName):
    """Return true iff the given filename is in the current P4 client view"""
    i,o,e = os.popen3('p4 have "%s"' % fileName)
    output = o.read()
    i.close()
    o.close()
    e.close()
    if output:
        return 1
    else:
        return 0


def AddP4Files(files, dirname, names):
    """add the names of the files in "names" that are in Perforce to 'files'"""
    global verbose, out
    if verbose:
        out.write("Checking '%s' for files in Perforce...\n" % dirname)
    namesInP4 = [ os.path.normpath(os.path.join(dirname, name))\
        for name in names\
        if P4Have(os.path.join(dirname, name)) ]
    files += namesInP4



#---- script mainline

# handle command line
try:
    optlist, args = getopt.getopt(sys.argv[1:], "v",\
        ["verbose"])
except getopt.GetoptError, msg:
    out.write("%s: error in options: %s\n" % (sys.argv[0], msg))
    sys.exit(1)
for opt, optarg in optlist:
    if opt in ("-v", "--verbose"):
        verbose = 1
if len(args) != 1:
    out.write("%s: error: must be exactly one argument (the start "\
        "dir name) " % sys.argv[0])
startDir = args[0]

# make sure in correct dir
landmark = "Construct"
if not os.path.isfile(landmark):
    out.write("error: Could not file '%s'. You are not in the Komodo "\
        "root dir.\n" % landmark)
    sys.exit(1)

# get the list of files in the Komodo tree
out.write("Get list of files in Perforce (this is slow)...\n")
files = []
os.path.walk(startDir, AddP4Files, files)

# parse out those files that should be skipped
filesToSkip = []
filesToProcess = []
baseNamesToSkip = {}
for file in files:
    dirname = os.path.dirname(file)
    basename = os.path.basename(file)
    for thing in thingsToSkip:
        # 'thing' could be a file basename
        if thing.lower() == basename.lower():
            filesToSkip.append(file)
            if baseNamesToSkip.has_key(basename.lower()):
                out.write("*** error: A file with the basename '%s' has already "\
                    "been found." % basename)
                sys.exit(1)
            elif verbose:
                out.write("Skipping '%s' (matches basename '%s')...\n" %\
                    (file, thing))
            break
        # 'thing' could be a p4-like recursive dir reference: 'blah/...'
        elif thing.endswith("/..."):
            if file.startswith(os.path.dirname(thing) + os.sep): 
                filesToSkip.append(file)
                if verbose:
                    out.write("Skipping '%s' (under '%s')...\n" % (file, thing))
                break
        # 'thing' could be a glob
        elif os.path.normpath(file) in glob.glob(thing):
            filesToSkip.append(file)
            if verbose:
                out.write("Skipping '%s' (in glob '%s')...\n" % (file, thing))
            break
    else:
        filesToProcess.append(file)


# ensure that none of the files to skip already has an ActiveState
# copyright applied
if verbose:
    out.write("\n\n")
out.write("Ensuring none of the files to skip already have AS copyright...\n")
for filename in filesToSkip:
    if verbose:
        out.write("Ensuring '%s' does not have the AS copyright...\n" %\
            filename)
    fin = open(filename, "r")
    for line in fin.readlines():
        if line.find("Copyright") != -1 and line.find("ActiveState") != -1:
            out.write("* warning: File to skip ('%s') already has copyright "\
                "applied. You should undo this manually.\n" % filename)


# process the remaining files
if verbose:
    out.write("\n\n")
out.write("Processing the files that should be copyrighted...\n")
import copyrighter
for filename in filesToProcess:
    copyrighter.AddCopyright(filename, verbose)


