#!/usr/bin/env python

import os
import re
import shutil

from codeintel2.tree import pretty_tree_from_tree
import ciElementTree

# P4 edit file
def p4update(filename, content):
    print os.popen("p4 edit %s" % (filename)).read()
    file(filename, "w").write(content)
    diff = os.popen("p4 diff %s" % (filename)).read()
    if len(diff.splitlines()) <= 1 and diff.find("not opened on this client") < 0:
        print "No change, reverting: %s" % os.popen("p4 revert %s" % (filename)).read()

def update_documentation_sentences(tree):
    # Replace unnecessary spaces in doc text
    for node in tree.getiterator():
        doc = node.get("doc")
        if doc:
            # Replace one or more space(s) followed by a dot with just a dot.
            node.set("doc", re.sub("\s+\.", ".", doc))

# Main function
def main():
    # More robust for determining the perforce script location
    cix_filename = "javascript.cix"
    scriptpath = os.path.dirname(__file__)
    if not scriptpath:
        scriptpath = "."
    scriptpath = os.path.abspath(scriptpath)
    cix_directory = scriptpath
    # Get main codeintel directory, 3 up from this script location!
    for i in range(3):
        cix_directory = os.path.dirname(cix_directory)
    cix_filename = os.path.join(cix_directory, "lib", "codeintel2", "stdlibs", cix_filename)

    # Generate the cix files
    for filename in ("ecmaToCodeintel.py", "dom0_to_cix.py", "dom2_to_cix.py"):
        p = os.popen("python %s" % (os.path.join(scriptpath, filename))).read()
    # Combine the libraries
    cixtree = ciElementTree.parse(os.path.join(scriptpath, "javascript.cix"))
    cixscope = cixtree.find("file/scope")

    # Note: XMLHttpRequest cix comes from the Mozilla implementation in:
    #       nsIXMLHttpRequest.idl
    for domname in ("XMLHttpRequest", "dom0", "dom2"):
        #cixscope.append(ciElementTree.Comment(" %s structure " % (domname)))
        et = ciElementTree.parse("%s.cix" % (os.path.join(scriptpath, domname)))
        for scope in et.findall("//file/scope"):
            for child in scope.getchildren():
                # Ensure we remove from the dom tree first, otherwise
                # we generate double elements
                scope.remove(child)
                cixscope.append(child)

    pretty_tree_from_tree(cixtree.getroot())

    update_documentation_sentences(cixtree)

    p4update(cix_filename, ciElementTree.tostring(cixtree.getroot()))

    # Update libraries
    for dirname, filename in (("dojo", "dojo_json_to_cix.py"),
                              ("MochiKit", "mochikit_to_cix.py"),
                              ("prototype", "prototype_to_cix.py"),
                              ("yui", "yui_to_cix.py")):
        library_script_path = os.path.join(scriptpath, dirname, filename)
        p = os.popen("python %s -u" % (library_script_path)).read()

# When run from command line
if __name__ == '__main__':
    main()
