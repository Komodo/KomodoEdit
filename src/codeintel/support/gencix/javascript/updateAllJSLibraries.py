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
