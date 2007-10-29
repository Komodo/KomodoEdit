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
    Generate DTD references from an XML file.

    Command Line Usage:
        dtdgen [<options>...] <xmlfile> <dtdfile>

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.
        -v, --verbose   Give verbose output for errors.

        -f, --force     Allow overwriting of existing files.
        -i              Do in-place replacement of <xmlfile>. This
                        implies "--force".
        -o <outfile>    Write output to the given file. By default
                        output if dumped to stdout.
                        
    sample usage:
    
    Parse a xul file, generate the dtd, and overwrite the xul file with
    a new xul file that has entity references added.
    
    dtdgen.py --force -i /path/to/file.xul /path/to/file.dtd
"""

import os
import sys
import getopt
import types
import re
import pprint
import logging

log = logging.getLogger("dtdgen")

try:
    import cElementTree as ET # effbot's C module
except ImportError:
    logging.basicConfig()
    log.setLevel(logging.INFO)
    log.error("using element tree and not cElementTree, performace will suffer")
    if sys.version_info[:2] < (2, 5):
        import elementtree.ElementTree as ET # effbot's pure Python module
    else:
        import xml.etree.ElementTree as ET

from xml.sax.saxutils import escape

# additional fixes
entitydefs = {'%': '&#37;',
              '"': '&quot;'}

nowrite = False
#---- exceptions

class DTDGenError(Exception):
    pass



#---- global data

_version_ = (0, 1, 0)



#---- internal logging facility

chromeURI = "chrome://komodo/locale/"

# a list of attrs that we will convert to use the dtd
attrs = [
    "label", "accesskey", "tooltiptext", "title",
    
    # custom attributes for komodo
    "locktip", "desc"
]

#---- internal support stuff


specialNames = {
    '.': 'period',
    '...': 'ellipsis',
    '+': 'plus',
    '-': 'minus',
    '//': 'doubleSlash',
    '#': 'hash',
}

#---- module API

def dtdgen(xmlfile, dtdfile=sys.stderr, outfile=sys.stdout, force=0):
    """Generate a DTD from the given XML file.

    "xmlfile" is the XML file to parse for attributes.
    "dtdfile" is the DTD file of references to generate.
    "outfile" is a filename or stream to which to write the new XML
        output (defaults to sys.stdout).
    "force" is boolean to allow overwriting an existing file (default is
        false).

    A <!DOCTYPE...> reference to the <dtdfile> is added, if possible.
    """
    log.info("dtdgen(xmlfile=%r, dtdfile=%r)", xmlfile, dtdfile)
    entities, xmlContent = dtdcollect(xmlfile, dtdfile)
    dtdwrite(dtdfile, entities, force)
    xmlwrite(outfile, xmlContent, force)

def dtdcollect(xmlfile, dtdfile):
    global nowrite
    log.info("dtdcollect(xmlfile=%r, dtdfile=%r)", xmlfile, dtdfile)

    entities = {}

    # read the xml text so we can do replacements
    fin = open(xmlfile, 'r')
    xmlContent = fin.read()
    fin.close()
    
    # first, parse the xml file
    tree = ET.parse(xmlfile)
    
    # iterate through the nodes, looking for attributes we care about
    for node in tree.getiterator():
        id = node.attrib.get("id", None)
        if not id:
            id = node.attrib.get("label", None)
        if id in specialNames:
            id = specialNames[id]
        for attr in attrs:
            entityVal = node.attrib.get(attr, None)
            if not entityVal:
                continue
            if attr == "accesskey" and id:
                try:
                    words = [w for w in re.split("[\W_]+", id) if w]
                    if len(words[0]) > 1 and not words[0][1].isupper():
                        # lowercase the first letter
                        words[0] = words[0][0].lower()+words[0][1:]
                    entityName = words[0] + "".join([w[0].upper()+w[1:] for w in words[1:]])
                except IndexError, e:
                    print "failure on name %s" % entityVal
                    raise
            elif entityVal in specialNames:
                entityName = specialNames[entityVal]
            else:
                try:
                    words = [w for w in re.split("[\W_]+", entityVal) if w]
                    if len(words[0]) > 1 and not words[0][1].isupper():
                        # lowercase the first letter
                        words[0] = words[0][0].lower()+words[0][1:]
                    entityName = words[0] + "".join([w[0].upper()+w[1:] for w in words[1:]])
                except IndexError, e:
                    print "failure on name %s" % entityVal
                    raise
            
            if entityName[0].isdigit():
                # cannot have digit as first char
                entityId = "%s.%s" % (attr, entityName)
            else:
                if entityName[0] == "1":
                    raise Exception()
                entityId = "%s.%s" % (entityName, attr)
            node.set(attr, "&%s;" % entityId)
            #print "%s=%s" % (entityId, entityVal)

            entities[entityId]=entityVal
            entityAttr = "%s=(\"|')%s\\1" % (attr, re.escape(entityVal))
            entityRef = "%s=\"&%s;\"" % (attr, entityId)
            
            # XXX SLOWWWWWW
            # XXX need our patched element tree so we can simply replace in
            # the correct location of the document, otherwise errors ARE
            # possible (and happen in komodo.xul) due to duplicate attrib
            # values in some elements
            xmlContent = re.subn(entityAttr, entityRef, xmlContent, 1)[0]

    # add the doctype data to the content
    if type(dtdfile) in types.StringTypes:
        # XXX make big assumptions here....
        chrome = "%s%s" % (chromeURI, os.path.basename(dtdfile))
        basename = os.path.splitext(os.path.basename(chrome))[0]
        m = re.search("(<!DOCTYPE.*?>)", xmlContent)
        if m:
            start, end = m.span(1)
            doctype = m.group(1)[:-1]
            doctype = "%s [\n  <!ENTITY %% %sDTD SYSTEM \"%s\">\n  %%%sDTD;\n]>" % \
                        (doctype, basename, chrome, basename)
        else:
            m = re.search("(<?xml.*?>)", xmlContent)
            if m:
                start, end = m.span(1)
                start = end
                m = re.search("(?:{(.*?)})?(.*)", tree.getroot().tag)
                rootTagName = m.group(2)
                rootNS = m.group(1)
                if not rootNS:
                    rootNS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul"
                doctype = """
<!DOCTYPE %s SYSTEM "%s" [
  <!ENTITY %% %sDTD SYSTEM "%s">
  %%%sDTD;
]>
""" % (rootTagName, rootNS, basename, chrome, basename)
            else:
                # probably HTML, we don't handle it yet
                raise Exception("Cannot handle non-xml files without a doctype declaration")

        xmlContent = xmlContent[:start] + doctype + xmlContent[end:]

    return entities, xmlContent

def dtdwrite(dtdfile, entities, force=False):
    if not entities:
        return
    dtdEntities = ['<!ENTITY %s "%s">' % (id, escape(val, entitydefs)) for id, val in entities.items()]
    dtdEntities.sort()
    dtdFileData = "\n".join(dtdEntities)+"\n"
    if type(dtdfile) in types.StringTypes:
        if os.path.exists(dtdfile):
            if force:
                os.remove(dtdfile)
            else:
                raise DTDGenError("dtd '%s' already exists, use '--force' to "\
                                    "allow overwrite" % dtdfile)
        dtdf = open(dtdfile, 'w')
    else:
        dtdf = dtdfile
    dtdf.write(dtdFileData)
    if dtdf != dtdfile:
        dtdf.close()


def xmlwrite(outfile, xmlContent, force=False):
    if nowrite:
        return

    if type(outfile) in types.StringTypes:
        if os.path.exists(outfile):
            if force:
                os.remove(outfile)
            else:
                raise DTDGenError("outfile '%s' already exists, use '--force' to "\
                                    "allow overwrite" % outfile)
        fout = open(outfile, 'w')
    else:
        fout = outfile

    # Write out the new content.
    fout.write(xmlContent)
    if fout != outfile:
        fout.close()



#---- mainline

def main(argv):
    global nowrite
    global chromeURI
    logging.basicConfig()
    log.setLevel(logging.INFO)

    # Process options.
    try:
        optlist, args = getopt.getopt(argv[1:], "hVvo:ifdc:",
            ["help", "version", "verbose", "force", "dry-run", "chrome"])
    except getopt.GetoptError, msg:
        log.error("%s. Your invocation was: %s\n"\
                         % (msg, argv))
        log.error("See 'dtdgen --help'.\n")
        return 1
    opts = [opt for opt, optarg in optlist]
    if "-o" in opts and "-i" in opts:
        log.error("cannot specify both '-i' and "\
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
            sys.stderr.write("dtdgen %s\n" % ver)
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
            verbose = 1
        elif opt in ("-f", "--force"):
            force = 1
        elif opt == "-o":
            outfile = optarg
        elif opt in ("-c", "--chrome"):
            chromeURI = optarg
        elif opt == "-i":
            inplace = 1
            force = 1
        elif opt in ("-d", "--dry-run"):
            nowrite = True

    # Process arguments.
    if len(args) < 1:
        log.error("incorrect number of arguments: argv=%r\n" % argv)
        return 1
    xmlfile, dtdfile = args
    if os.path.isdir(xmlfile):
        if not os.path.isdir(dtdfile):
            print "second argument must be the path to the locale directory"
            sys.exit(-1)
        for root, dirs, files in os.walk(xmlfile):
            print 20*'-'
            print root
            for dname in dirs:
                if dname == "test":
                    del dirs[dirs.index(dname)]
            pathparts = os.path.split(root)
            if pathparts[1]:
                dtdbase = pathparts[1]
            else:
                pathparts = pathparts[0].split(os.sep)
                if pathparts[-1] == 'content':
                    dtdbase = pathparts[-2]
                else:
                    dtdbase = pathparts[-1]
            dtdname = os.path.join(dtdfile, "%s.dtd" % dtdbase)
            dtdEntities= {}
            for name in files:
                basename = os.path.basename(name)
                name, ext = os.path.splitext(basename)
                if ext not in [".xul", ".xml"]:
                    continue
                if basename.startswith("test"):
                    continue
                name, tagext = os.path.splitext(name)
                infile = outfile = os.path.join(root, basename)
                entities, content = dtdcollect(infile, dtdname)
                if entities:
                    dtdEntities.update(entities)
                    xmlwrite(outfile, content, force=True)
            dtdwrite(dtdname, dtdEntities, force=True)
                
    else:
        if inplace:
            outfile = xmlfile
    
        try:
            dtdgen(xmlfile, dtdfile, outfile, force)
        except DTDGenError, ex:
            log.exception(ex)

if __name__ == "__main__":
    __file__ = sys.argv[0]
    sys.exit( main(sys.argv) )


