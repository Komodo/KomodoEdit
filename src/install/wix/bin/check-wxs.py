#!/usr/bin/env python

"""
This script checks that we're not accidentally imaging files that are not being
shipped.
"""

import imp
import os
import os.path
import sys
from xml.dom import minidom

def readFileList(feature, config):
    """ Read a feature-*.ini file and return the files we expect to ship
    @param feature {str} The base name of the file, e.g. "feature-core"
    @param config {set} The configuration
    @returns (set, set) Extra and missing files, respectively
    """
    config = set(config)
    plat = sys.platform
    if plat.startswith("linux"):
        plat = "linux" # strip version
    config.add(plat)
    config.add("default")

    enabled = set() # files we are shipping in this configuration
    disabled = set() # files we are not shipping in this configuration

    target = enabled

    f = open("%s.ini" % (feature,), "r")
    try:
        for line in f:
            line = line.split("#", 1)[0].split(";", 1)[0].strip()
            if not line:
                continue
            if line[0] == "[" and line[-1] == "]":
                target = enabled
                section = line[1:-1]
                for part in section.split("."):
                    if not part in config:
                        target = disabled
                        break
            else:
                target.add(line)

    finally:
        f.close()

    return enabled, disabled

def readWxsTemplate(feature):
    join = os.path.join

    doc = minidom.parse("%s.template.in" % (feature,))
    root = doc.getElementsByTagName("DirectoryRef")[0]
    path = feature
    if root.getAttribute("Id") == "INSTALLDIR":
        path = join(path, "INSTALLDIR")

    files = set()

    def doDir(elem):
        for child in elem.childNodes:
            if not isinstance(child, minidom.Element):
                continue
            if child.tagName == "Directory":
                doDir(child)
            elif child.tagName == "Component":
                for grandchild in child.childNodes:
                    if not isinstance(grandchild, minidom.Element):
                        continue
                    if grandchild.tagName != "File":
                        continue
                    files.add(grandchild.getAttribute("Source").replace(os.sep, "/"))

    doDir(root)
    return files

def checkFiles(feature, enabled, disabled):
    """ Check the file system for extra and missing files
    @param feature {str} The feature name, e.g. "feature-core"
    @param real_enabled {set of str} The files that should be enabled
    @param real_disabled {set of str} The files that might exist
    @returns (set, set) Extra and missing files, respectively
    """
    lower_enabled = set(x.lower() for x in enabled)
    lower_disabled = set(x.lower() for x in disabled)
    extra = set() # files that are found but not in any listing
    for dirpath, dirs, files in os.walk(feature):
        for f in files:
            path = os.path.join(dirpath, f).replace(os.sep, "/")
            lowerPath = path.lower()
            if lowerPath in lower_enabled:
                lower_enabled.remove(lowerPath)
            elif lowerPath in lower_disabled:
                lower_disabled.remove(lowerPath)
            else:
                extra.add(path)

    # it's okay for disabled files to be missing; ignore them.
    return extra, set(x for x in enabled if x.lower() in lower_enabled)

def main(features, config={}):
    config_values = set()
    for k in dir(config):
        v = getattr(config, k, None)
        if v in (1, True):
            config_values.add(k)

    extra = set()
    missing = set()
    for feature in features:
        enabled, disabled = readFileList(feature, config_values)
        enabled.update(readWxsTemplate(feature))
        sub_extra, sub_missing = checkFiles(feature, enabled, disabled)
        extra.update(sub_extra)
        missing.update(sub_missing)

    msg = []
    if extra:
        msg.append("Extra files:\n%s" % ("\n".join("\t%s" % (f,) for f in extra)))
    if missing:
        msg.append("Missing files:\n%s" % ("\n".join("\t%s" % (f,) for f in missing)))
    if extra or missing:
        raise Exception("""\
The Komodo install manifests are out of date; please update the appropriate
feature-*.ini in "src/install/wix".

%s
""" % ("\n\n".join(msg,)))
    print "Features %s appears to have correct manifests" % (", ".join(features))


if __name__ == '__main__':
    abspath = os.path.abspath
    config_path = abspath(os.path.join(abspath(__file__), "../../../.."))
    file, pathname, description = imp.find_module("bkconfig", [config_path])
    config = imp.load_module("bkconfig", file, pathname, description)
    main(sys.argv[1:], config=config)
