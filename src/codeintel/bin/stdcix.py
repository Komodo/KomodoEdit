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
#
# Contributors:
#   Trent Mick (TrentM@ActiveState.com)

"""
    stdcix - generate a CIX file for a base language installation

    Usage:
        stdcix [options...] <language>

    Options:
        -h, --help              print this help and exit
        -V, --version           print version and exit
        -v, --verbose           verbose output; use twice for debug output

        -o <file>               file to which to write generated CIX, default
                                is stdout

    This script encapsulates the knowledge to build a std CIX file for
    a particular language installation (at least for Python). Sometimes the
    process cannot be the typical scanning source code at run (the job of
    the CILEs) because some important modules are binary and occasionally
    certain objects are important enough to merit special custom type
    assignments.

    To update the current "shipping" standard Python CIX:
        p4 edit lib/codeintel/python.cix
        python bin/stdcix.py -o lib/codeintel/python.cix Python
        p4 submit lib/codeintel/python.cix

    To update the current "shipping" standard Perl CIX:
        p4 edit lib/codeintel/perl.cix
        python bin/stdcix.py -o lib/codeintel/perl.cix Perl
        p4 submit lib/codeintel/perl.cix
"""
#TODO:
# - Should the <file> for modules defined in .pyd's be the .pyd file or
#   the python.cix file. It is the latter, currently.
# - Should specifying a particular language installation be allowed?
#   necessary?
# - Perhaps differentiate generating <major>.<minor>-specific CIX output
#   version version-neutral CIX output.
# - Define hard-coded hints
# - (run w/ python 2.3)
# - fill out methods of builtin types, classes, etc

import os
from os.path import join, dirname, exists, isfile, isdir, basename
import sys
import getopt
import logging
import time
import types
import inspect
import re
from pprint import pprint
import textwrap
import subprocess
import urllib

from elementtree.ElementTree import Element, SubElement, ElementTree
import sys
sys.path.append('../lib')
from codeintel2.util import parsePyFuncDoc, parseDocSummary
import which # should be in codeintel/support dir



#---- exceptions

class Error(Exception):
    pass


#---- global data

_version_ = (0, 4, 0)
log = logging.getLogger("stdcix")



#---- internal routines and classes

def _xml_unescape(s):
    from xml.sax.saxutils import unescape
    u = unescape(s, {"&quot;": '"'})
    if re.search("&\w+;", u):
        raise Error("XXX missed XML-unescaping something in: %r" % u)
    return u

# Add .text and .tail values to an Element tree to make the output
# pretty. (Only have to avoid "doc" tags: they are the only ones with
# text content.)
def prettify(elem, level=0, indent='  ', youngestsibling=0):
    if elem and elem.tag != "doc":
        elem.text = '\n' + (indent*(level+1))
    for i in range(len(elem)):
        prettify(elem[i], level+1, indent, i==len(elem)-1)
    elem.tail = '\n' + (indent*(level-youngestsibling))

def banner(text, ch='=', length=78):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix


#---- Perl CIX generation

def genPerlStdCIX(filename, stream):
    log.debug("genPerlStdCIX(filename=%r, stream=%r)", filename, stream)

    root = Element("codeintel", version="2.0")
    cixfile = SubElement(root, "file", lang="Perl",
                         mtime=str(int(time.time())),
                         path=os.path.basename(filename))

    # Process Perl's built-ins out of perlfunc.pod.
    if 1:
        p4path = "//depot/main/Apps/Gecko/src/Core/pod/perlfunc.pod"
        cmd = "p4 print -q %s" % p4path
        i,o,e = os.popen3(cmd)
        lines = o.read().splitlines(0)
        i.close(); o.close(); retval = e.close()
        if retval:
            raise Error("error running: %s" % cmd)
    else:
        lines = open("perlfunc.pod", 'r').read().splitlines(0)

    # Parse the "Alphabetical Listing of Perl Functions" into a list of
    # 'blocks' where each block is one command-"=item" block.
    start = lines.index("=head2 Alphabetical Listing of Perl Functions")
    blocks = []
    block = None
    level = 0
    def parseItem(line):
        sig = line.split(None, 1)[1]
        name = re.split("[ \t\n(/]", sig, 1)[0]
        return name, sig
    for i, line in enumerate(lines[start:]):
        if line.startswith("=over"):
            level += 1
        if line.startswith("=back"):
            level -= 1
            if level == 0: # done the 'Alphabetical Listing' section
                if block: blocks.append(block)
                break
    
        if level > 1:
            if block:
                block["lines"].append(line)
        elif block is None and not line.startswith("=item"):
            continue
        elif block is None and line.startswith("=item"):
            block = {}
            name, sig = parseItem(line)
            block = {
                "name": name,
                "sigs": [sig],
                "lines": []
            }
        elif line.startswith("=item"):
            name, sig = parseItem(line)
            if name == block["name"]:
                block["sigs"].append(sig)
            else:
                blocks.append(block)
                block = {
                    "name": name,
                    "sigs": [sig],
                    "lines": []
                }
        else:
            if not block["lines"] and not line.strip():
                pass # drop leading empty lines
            elif not line.strip() and block["lines"] and \
               not block["lines"][-1].strip():
                pass # collapse multiple blank lines
            else:
                block["lines"].append(line)
    #pprint(blocks)

    # Process the blocks into a list of command info dicts.
    def podrender(pod):
        rendered = pod
        rendered = re.sub("F<(.*?)>", r"\1", rendered)
        rendered = re.sub("I<(.*?)>", r"*\1*", rendered)
        def quoteifspaced(match):
            if ' ' in match.group(1):
                return "'%s'" % match.group(1)
            else:
                return match.group(1)
        rendered = re.sub("C<(.*?)>", quoteifspaced, rendered)
        def linkrepl(match):
            content = match.group(1)
            if content.startswith("/"): content = content[1:]
            if "/" in content:
                page, section = content.split("/", 1)
                content = "%s in '%s'" % (section, page)
            else:
                content = "'%s'" % content
            return content
        rendered = re.sub("L<(.*?)>", linkrepl, rendered)
        return rendered

    # These perl built-ins are grouped in perlfunc.pod.
    commands = []
    WIDTH = 60 # desc field width
    syscalls = """
        getpwnam getgrnam gethostbyname getnetbyname getprotobyname 
        getpwuid getgrgid getservbyname gethostbyaddr getnetbyaddr 
        getprotobynumber getservbyport getpwent getgrent gethostent
        getnetent getprotoent getservent setpwent setgrent sethostent 
        setnetent setprotoent setservent endpwent endgrent endhostent
        endnetent endprotoent endservent
    """.split()
    calltip_skips = "sub use require".split()
    for block in blocks:
        name, sigs, lines = block["name"], block["sigs"], block["lines"]
        if name == "-X": # template for -r, -w, -f, ...
            pattern = re.compile(r"^    (-\w)\t(.*)$")
            tlines = [line for line in lines if pattern.match(line)]
            for tline in tlines:
                tname, tdesc = pattern.match(tline).groups()
                tsigs = [s.replace("-X", tname) for s in sigs]
                command = {"name": tname, "sigs": tsigs,
                           "desc": textwrap.fill(tdesc, WIDTH)}
                commands.append(command)
        elif name in ("m", "q", "qq", "qr", "qx", "qw", "s", "tr", "y"):
            operators = {
                "m":  """\
                    m/PATTERN/cgimosx
                    /PATTERN/cgimosx

                    Searches a string for a pattern match, and in scalar
                    context returns true if it succeeds, false if it fails.
                      """,
                "q":  """\
                    q/STRING/
                    'STRING'

                    A single-quoted, literal string.
                      """,
                "qq": """\
                    qq/STRING/
                    "STRING"

                    A double-quoted, interpolated string.
                      """,
                "qr": """\
                    qr/STRING/imosx

                    Quotes (and possibly compiles) STRING as a regular
                    expression.
                      """,
                "qx": """\
                    qx/STRING/
                    `STRING`

                    A string which is (possibly) interpolated and then
                    executed as a system command.
                      """,
                "qw": """\
                    qw/STRING/

                    Evaluates to a list of the words extracted out of STRING,
                    using embedded whitespace as the word delimiters.
                      """,
                "s":  """\
                    s/PATTERN/REPLACEMENT/egimosx

                    Searches a string for a pattern, and if found, replaces
                    that pattern with the replacement text and returns the
                    number of substitutions made. Otherwise it returns the
                    empty string.
                      """,
                "tr": """\
                    tr/SEARCHLIST/REPLACEMENTLIST/cds
                    y/SEARCHLIST/REPLACEMENTLIST/cds

                    Transliterates all occurrences of the characters found in
                    the search list with the corresponding character in the
                    replacement list. It returns the number of characters
                    replaced or deleted.
                      """,
                "y":  """\
                    tr/SEARCHLIST/REPLACEMENTLIST/cds
                    y/SEARCHLIST/REPLACEMENTLIST/cds

                    Transliterates all occurrences of the characters found in
                    the search list with the corresponding character in the
                    replacement list. It returns the number of characters
                    replaced or deleted.
                      """,
            }
            sigs = []
            desclines = None
            for line in operators[name].splitlines(0):
                if desclines is not None:
                    desclines.append(line.strip())
                elif not line.strip():
                    desclines = []
                else:
                    sigs.append(line.strip())
            command = {"name": name, "sigs": sigs,
                       "desc": textwrap.fill(' '.join(desclines), WIDTH)}
            commands.append(command)
        elif name in syscalls:
            desc = "Performs the same function as the '%s' system call." % name
            desc = textwrap.fill(desc, WIDTH)
            getterListContext = {
                "getpw":    "\n"
                            "  ($name,$passwd,$uid,$gid,$quota,$comment,\n"
                            "   $gcos,$dir,$shell,$expire) = %s",
                "getgr":    "\n  ($name,$passwd,$gid,$members) = %s",
                "gethost":  "\n  ($name,$aliases,$addrtype,$length,@addrs) = %s",
                "getnet":   "\n  ($name,$aliases,$addrtype,$net) = %s",
                "getproto": "\n  ($name,$aliases,$proto) = %s",
                "getserv":  "\n  ($name,$aliases,$port,$proto) = %s",
            }
            getterScalarContext = {
                "getgrent":         "$name = %s",
                "getgrgid":         "$name = %s",
                "getgrnam":         "$gid = %s",
                "gethostbyaddr":    "$name = %s",
                "gethostbyname":    "$addr = %s",
                "gethostent":       "$name = %s",
                "getnetbyaddr":     "$name = %s",
                "getnetbyname":     "$net = %s",
                "getnetent":        "$name = %s",
                "getprotobyname":   "$num = %s",
                "getprotobynumber": "$name = %s",
                "getprotoent":      "$name = %s",
                "getpwent":         "$name = %s",
                "getpwnam":         "$uid = %s",
                "getpwuid":         "$name = %s",
                "getservbyname":    "$num = %s",
                "getservbyport":    "$name = %s",
                "getservent":       "$name = %s",
            }
            for prefix, template in getterListContext.items():
                if name.startswith(prefix):
                    desc += template % sigs[0]
                    if name in getterScalarContext:
                        desc += "\nin list context or:\n  "\
                                + getterScalarContext[name] % sigs[0]
            command = {"name": name, "desc": desc, "sigs": sigs}
            commands.append(command)
        elif name == "shmread":
            desc = """\
                Reads the System V shared memory segment ID
                starting at position POS for size SIZE by attaching to it,
                copying out, and detaching from it.
            """
            desc = ' '.join([ln.strip() for ln in desc.splitlines(0)])
            command = {"name": name, "sigs": sigs,
                       "desc": textwrap.fill(desc, WIDTH)}
            commands.append(command)
        elif name == "shmwrite":
            desc = """\
                Writes the System V shared memory segment ID
                starting at position POS for size SIZE by attaching to it,
                copying in, and detaching from it.
            """
            desc = ' '.join([ln.strip() for ln in desc.splitlines(0)])
            command = {"name": name, "sigs": sigs,
                       "desc": textwrap.fill(desc, WIDTH)}
            commands.append(command)
        elif name in calltip_skips:
            continue # just drop the sub calltip: annoying
        else:
            # Parsing the description from the full description:
            # Pull out the first sentence up to a maximum of three lines
            # and one paragraph. If the first *two* sentences fit on the
            # first line, then use both.
            desc = ""
            sentencePat = re.compile(r"([^\.]+(?:\. |\.$))")
            if name in ("dbmclose", "dbmopen"):
                # Skip the first paragraph: "[This function...superceded by"
                lines = lines[lines.index('')+1:]
            elif name == "do":
                # Skip the first sentence: "Not really a function."
                end = sentencePat.match(lines[0]).span()[1]
                lines[0] = lines[0][end:].lstrip()
            for i, line in enumerate(lines):
                if not line.strip(): break
                sentences = sentencePat.findall(line)
                if not sentences:
                    desc += line + ' '
                    continue
                elif i == 0 and len(sentences) > 1:
                    desc += ' '.join([s.strip() for s in sentences[:2]])
                else:
                    desc += sentences[0].strip()
                break
            command = {"name": name, "sigs": sigs,
                       "desc": textwrap.fill(podrender(desc), WIDTH)}
            commands.append(command)
    #for command in commands:
    #    print
    #    print banner(command["name"], '-')
    #    print '\n'.join(command["sigs"])
    #    print
    #    print command["desc"]
    
    # Generate the CIX for each function.
    module_elt = SubElement(cixfile, "scope", ilk="blob", name="*") # "built-ins" module
    for command in commands:
        name, sigs, desc = command["name"], command["sigs"], command["desc"]
        func_elt = SubElement(module_elt, "scope", ilk="function", name=name)
        if sigs:
            func_elt.set("signature", '\n'.join(sigs))
        if desc:
            doclines = desc.split('\n')[:3]
            #doclines = parseDocSummary(doclines)
            doc = '\n'.join(doclines)
            func_elt.set("doc", doc)

    # Generate the CIX.
    prettify(root)
    tree = ElementTree(root)
    stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    tree.write(stream)



#---- public interface

def stdcix(language, filename=None, stream=sys.stdout):
    generator_from_language = {
        "Perl": genPerlStdCIX,
    }
    try:
        generator = generator_from_language[language]
    except KeyError:
        raise Error("unsupported language: %r" % language)
    if filename is None: filename = language.lower()+'.cix'
    cix = generator(filename, stream)
    return cix



#---- mainline

def main(argv):
    logging.basicConfig()

    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "Vvhl:o:",
            ["version", "verbose", "help", "language=",])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `python bin/stdcix.py --help'.")
        return 1
    filename = None
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(part) for part in _version_])
            print "stdcix %s" % ver
            return
        elif opt in ("-v", "--verbose"):
            if log.level == logging.NOTSET:
                log.setLevel(logging.INFO)
            elif log.level == logging.INFO:
                log.setLevel(logging.DEBUG)
        elif opt == "-o":
            filename = optarg
    if filename:
        stream = open(filename, 'w')
    else:
        filename = None
        stream = sys.stdout
    if len(args) == 0:
        log.error("no language given: you must specify one as the first arg")
        return 1
    elif len(args) == 1:
        language = args[0]
    else:
        log.error("too many arguments: just specify the language")
        return 1

    try:
        try:
            stdcix(language, filename, stream)
        except Error, ex:
            log.error(str(ex))
            if log.isEnabledFor(logging.DEBUG):
                print
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1
        except KeyboardInterrupt:
            log.debug("user abort")
            pass
    finally:
        if stream is not sys.__stdout__:
            stream.close()

if __name__ == "__main__":
    sys.exit( main(sys.argv) )

