#!/usr/bin/env python

"""
Generate feature-*.wxs.in from feature-*.template.in and feature-*.ini

This reads feature-*.ini for the set of files to ship in a feature, plus the
template XML input, to generate a .wxs.in containing all files we intend to
ship.  This mainly exists so we can list our files in a more readable format.
"""

import collections
import hashlib
import imp
import os.path
import sys

# ElementTree doesn't preserve enough processing instructions :(
from xml.dom import minidom

def readFileList(filename, config=set()):
    """ Read in the file list, given the current configuration
    @param filename {str} The ini file listing to read from
    @param config {set} The configuration
    @returns {set of str} The files that should be included
    """
    config = set(config)
    plat = sys.platform
    if plat.startswith("linux"):
        plat = "linux" # strip version
    config.add(plat)
    config.add("default")

    valid = True
    results = set()

    f = open(os.path.abspath(filename), "r")
    try:
        for line in f:
            line = line.split("#", 1)[0].split(";", 1)[0].strip()
            if not line:
                continue
            if line[0] == "[" and line[-1] == "]":
                valid = True
                section = line[1:-1]
                for part in section.split("."):
                    if not part in config:
                        print "Skipping section %s: feature %s fail" % (section, part)
                        valid = False
                        break
                else:
                    print "Adding section %s" % (section,)
            else:
                if valid:
                    results.add(line)
        return sorted(results)

    finally:
        f.close()

def buildTree(files):
    """ Build a dict tree of the files
    @param files {iterable of str} The files to include
    @returns {dict of dict/None} The filesystem tree; each directory is
        represented by a dict, where the keys are the file names, and the values
        are either more dicts (subdirectories), or str (files).  In the case of
        files, the values are the full path to the source file."""

    result = dict()
    for f in files:
        parts = f.split("/")
        if parts[1] == "INSTALLDIR":
            # drop the feature-core/INSTALLDIR bits
            parts = parts[2:]
        leaf = parts.pop()
        directory = result
        for part in parts:
            if part not in directory:
                directory[part] = dict()
            directory = directory[part]
        directory[leaf] = f
    return result

def makeShortName(parent, name, tagName):
    """Create a 8.3 short name for a given long name
    @param parent {minidom.Element} The parent node
    @param name {str} The long name to adjust
    @param tagName {str} The sibling tag name to check
    @returns {str} The new short name, or None if the name is already short
    """
    # XXX TODO make this generate valid short names
    base, ext = os.path.splitext(name)
    trimmed = base.translate(None, r'\?|><:/*"+,;=[] ')
    if len(base) <= 8 and len(ext) <= 4 and (trimmed == base):
        # this is a valid short name
        return None
    ext = ext[:4] # extension up to 3 characters plus leading dot

    siblings = set()
    for child in parent.childNodes:
        if not isinstance(child, minidom.Element):
            continue
        if child.tagName != tagName:
            continue
        siblings.add(child.getAttribute("Name"))

    for prefixLength in range(min([6, len(base)]), 0, -1):
        prefix = trimmed[:prefixLength]
        for i in range(0, 9999):
            short = "%s_%i" % (prefix, i)
            if len(short) > 8:
                break
            short = ("%s%s" % (short, ext)).upper()
            if short not in siblings:
                return short
    raise RuntimeError("Failed to get short name for %s" % (name,))


def buildXML(doc, tree):
    """ Update the XML DOM tree with the new files
    @param dom {xml.dom.minidom.Document} The DOM template to modify
    @param tree {dict} The file tree, as returned from buildTree()
    @returns None
    """
    featureRef = doc.getElementsByTagName("FeatureRef")[0]
    featureId = featureRef.getAttribute("Id")
    root = doc.getElementsByTagName("DirectoryRef")[0]
    features = set()

    for child in featureRef.childNodes:
        if not isinstance(child, minidom.Element) or child.tagName != "ComponentRef":
            continue
        features.add(child.getAttribute("Id"))

    def genId(kind, path):
        """ Generate an Id attribute for a path """
        result = "%s.%s." % (featureId, kind)
        for c in path:
            if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.":
                result += c
            else:
                result += "_"
        if len(result) > 72:
            # identifier too long
            result = "%s.%s.%s" % (featureId, kind, hashlib.sha1(path).hexdigest())
        return result

    def doDir(subdir, parent, path):
        has_python = False
        for k, v in sorted(subdir.items()):
            subPath = "%s/%s" % (path, k)
            if isinstance(v, dict):
                # sub-directory
                compId = None
                for child in parent.childNodes:
                    if not (isinstance(child, minidom.Element) and \
                            child.tagName == "Directory"):
                        continue
                    name = child.getAttribute("LongName") or child.getAttribute("Name")
                    if name == k:
                        elem = child
                        component = elem.firstChild
                        while isinstance(component, minidom.Text):
                            component = component.nextSibling
                        if isinstance(component, minidom.Element) and \
                                component.tagName == "Component":
                            compId = component.getAttribute("Id")
                        break
                else:
                    elem = doc.createElement("Directory")
                    shortName = makeShortName(parent, k, "Directory")
                    if shortName is None:
                        elem.setAttribute("Name", k)
                    else:
                        elem.setAttribute("LongName", k)
                        elem.setAttribute("Name", shortName)
                    elem.setAttribute("Id", genId("dir", subPath))
                    parent.appendChild(elem)
                    component = doc.createElement("Component")
                    compId = genId("comp", subPath)
                    component.setAttribute("Id", compId)
                    component.setAttribute("DiskId", "1")
                    component.setAttribute("Guid", "$(autowix.guid)")
                    elem.appendChild(component)
                    comment = doc.createComment(" %s " % (subPath,))
                    parent.appendChild(comment)

                if compId and not compId in features:
                    ref = doc.createElement("ComponentRef")
                    ref.setAttribute("Id", compId)
                    featureRef.appendChild(ref)
                    features.add(compId)

                doDir(v, parent=elem, path=subPath)
            else:
                # file
                if v.endswith(".py"):
                    has_python = True
                component = parent.firstChild
                while isinstance(component, minidom.Text):
                    component = component.nextSibling
                assert isinstance(component, minidom.Element), "<Component/> is not an element"
                assert component.tagName == "Component", "<Component/> has wrong tag"
                elem = doc.createElement("File")
                elem.setAttribute("Id", genId("file", subPath))
                shortName = makeShortName(component, k, "File")
                if shortName is None:
                    elem.setAttribute("Name", k)
                else:
                    elem.setAttribute("LongName", k)
                    elem.setAttribute("Name", shortName)
                elem.setAttribute("Vital", "yes")
                elem.setAttribute("src", v.replace("/", "\\"))
                component.appendChild(elem)

        if has_python:
            # if we have python files, we need to get rid of *.pyo / *.pyc
            component = parent.firstChild
            while isinstance(component, minidom.Text):
                component = component.nextSibling
            assert isinstance(component, minidom.Element), "<Component/> is not an element"
            assert component.tagName == "Component", "<Component/> has wrong tag"
            for ext in "pyo", "pyc":
                remove = doc.createElement("RemoveFile")
                remove.setAttribute("On", "uninstall")
                remove.setAttribute("Name", "*.%s" % (ext,))
                remove.setAttribute("Id", genId("rm%s" % (ext,), path))
                component.appendChild(remove)

    prefix=""
    if root.getAttribute("Id") == "ChromeDir":
        # skip to lib/mozilla/chrome
        prefix = "lib/mozilla/chrome"
    for part in filter(bool, prefix.split("/")):
        tree = tree.get(part, {})
    doDir(tree, root, prefix)

def main(template, filelist, outfile, config={}):
    config_values = set()
    for k in dir(config):
        v = getattr(config, k, None)
        if v in (1, True):
            config_values.add(k)

    files = readFileList(filelist, config_values)
    tree = buildTree(files)

    doc = minidom.parse(template)
    buildXML(doc, tree)
    f = open(outfile, "w")
    try:
        #doc.writexml(f, addindent="  ")
        f.write(doc.toprettyxml(indent="  "))
    finally:
        f.close()

if __name__ == '__main__':
    abspath = os.path.abspath
    config_path = abspath(os.path.join(abspath(__file__), "../../../.."))
    file, pathname, description = imp.find_module("bkconfig", [config_path])
    config = imp.load_module("bkconfig", file, pathname, description)
    main(*sys.argv[1:], config=config)
