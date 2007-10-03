#!/usr/bin/env python

"""Replace NEW* refs in .wxs files with appropriate entries.

Supported markers:
    NEWGUID
    NEWFILE
    NEWDIRECTORY
    NEWCOMPONENT
    NEWREMOVEFILE
"""
#TODO: Add support for determining appropriate Name for <Directory>'s from
#      a LongName.

import os
from ntpath import basename as win_basename
import sys
import re
from os.path import exists, dirname, abspath, normpath, join
from glob import glob
import shutil
import logging
from pprint import pprint

try:
    from xml.etree import cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        from elementtree import ElementTree as ET

import wax


class Error(Exception):
    pass


def new_guid():
    if sys.platform == "win32":
        import pythoncom
        guid = str(pythoncom.CreateGuid())
        guid = guid[1:-1] # strip of the {}'s
    else:
        guid = os.popen("uuidgen").read().strip().upper()
    return guid

def newguid(path):
    fin = open(path, 'r')
    original = content = fin.read()
    fin.close()
    if "NEWGUID" not in content:
        return

    print "%s: replace 'NEWGUID' with new guids" % path
    pattern = re.compile("NEWGUID(-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})?")
    match = pattern.search(content)
    while match:
        start, end = match.span()
        guid = new_guid()
        print "...replace '%s' with '%s'" % (content[start:end], guid)
        content = content[:start] + guid + content[end:]
        match = pattern.search(content)

    if content == original:
        print "...no changes, leaving alone"
    else:
        bakpath = path+".bak"
        print "...backing up original to '%s'" % bakpath
        if exists(bakpath):
            os.remove(bakpath)
        shutil.copy2(path, bakpath)
        fout = open(path, 'w')
        fout.write(content)
        fout.close()

def get_wxs_paths():
    assert "feature-core.wxs.in" in os.listdir('.'),\
        "You must run this from the dir with 'feature-core.wxs.in'."
    # Include the .wxs files from *all* active Komodo branches.
    active_branches = ["Komodo-4.2", "komodo", "openkomodo"]
    base = normpath(join(dirname(abspath(__file__)),
                         "..", "..", "..", "..", ".."))
    active_wix_dirs = [join(base, b, "src", "install", "wix")
                       for b in active_branches]
    wxs_paths = []
    for d in active_wix_dirs:
        if not exists(d):
            #TODO: Determine if this is still necessary and try to drop
            #      this requirement.
            raise Error("'%s' does not exist: to run this script you need "
                        "all active Komodo branches synced" % d)
        wxs_paths += glob(join(d, "*.wxs"))
        wxs_paths += glob(join(d, "*.wxs.in"))
    return wxs_paths

def newfile(path, guru):
    original = open(path, 'r').read()
    if "NEWFILE" not in original:
        return
    print "%s: replacing 'NEWFILE' with appropriate values..." % path
    new_lines = []
    last_directory_line = None  # e.g. <Directory Id="directory70" Name="dbgp">
    markers_found = False
    for i, line in enumerate(original.splitlines(0)):
        if "NEWFILE" not in line:
            new_lines.append(line)
        else:
            markers_found = True
            assert line.lstrip().startswith("<File ")
            indent = line[:line.index('<')]

            if line.rstrip().endswith("/>"):
                tail_hack = None
            elif line.rstrip().endswith(">"):
                tail_hack = ">" # just the one char
                line = line.rstrip()[:-1] + "/>"
            else:
                tail_hack = ""
                line = line.rstrip() + "/>"

            elem = ET.fromstring(line)
            src = elem.get("src")
            if src is None:
                raise Error("<File> attribute on line %d must have 'src' "
                            "attribute" % (i+1))
            attrib = {
                "src": src,
                "Id": guru.get_file_id(),
                "Vital": "yes",
            }
            name, longname = guru.get_path_names(win_basename(src))
            attrib["Name"] = name
            if longname is not None:
                attrib["LongName"] = longname
            print "... updating <File/> for %s" % (longname or name)
            file_tag = ET.tostring(ET.Element("File", **attrib))

            if tail_hack is None:
                pass
            elif tail_hack == ">":
                file_tag = file_tag.rstrip()[:-2] + ">"
            elif tail_hack == "":
                file_tag = file_tag.rstrip()[:-2]
            else:
                raise Error("unexpected tail hack: %r" % tail_hack)

            new_lines.append(indent + file_tag)
        if line.lstrip().startswith("<Directory "):
            last_directory_line = line
    
    if markers_found:
        open(path, 'w').write('\n'.join(new_lines) + '\n')


def new_tag_id(tag, path, guru):
    marker = "NEW" + tag.upper()

    fin = open(path, 'r')
    try:
        original = fin.read()
    except:
        fin.close()

    if marker not in original:
        return
    print "%s: replacing '%s' with appropriate values..." % (marker, path)
    new_lines = []
    markers_found = False
    for i, line in enumerate(original.splitlines(0)):
        if marker not in line:
            new_lines.append(line)
        else:
            markers_found = True
            assert line.lstrip().startswith('<'+tag)
            indent = line[:line.index('<')]
            if line.lstrip().endswith("/>"):
                elem = ET.fromstring(line.strip())
            else:
                #print repr(line.strip() + ('\n</%s>' % tag))
                elem = ET.fromstring(line.strip() + ('\n</%s>' % tag))
            assert elem.attrib["Id"] == marker
            guru_func = getattr(guru, "get_%s_id" % tag.lower())
            elem.attrib["Id"] = guru_func()
            print "... updating <%s> with id '%s'" % (tag, elem.attrib["Id"])
            new_line = ET.tostring(elem).split('\n', 1)[0]
            new_lines.append(indent + new_line)

    if markers_found:
        fout = open(path, 'w')
        try:
            fout.write('\n'.join(new_lines) + '\n')
        finally:
            fout.close()

def main():
    logging.basicConfig()
    logging.getLogger("wax").setLevel(logging.ERROR) # don't want wax warnings
    guru = wax.Guru(get_wxs_paths())
    for path in sys.argv[1:]:
        newguid(path)
        newfile(path, guru)
        new_tag_id("Directory", path, guru)
        new_tag_id("Component", path, guru)
        new_tag_id("RemoveFile", path, guru)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print "Usage: %r <file.wxs[.in]> [<file2.wxs[.in]>...]"
        sys.exit(1)
    main()

