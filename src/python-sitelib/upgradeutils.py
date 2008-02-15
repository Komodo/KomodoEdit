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
Helper code to assist with the Komodo upgrade process.
"""

import uriparse

def upgrade_mapped_uris_for_prefset(prefset):
    """Upgrade the mappedPaths preference."""

    # Komodo 4.3.0b1:
    # Update the mapped URI's to always be URI's, not just local file paths.
    # http://bugs.activestate.com/show_bug.cgi?id=74611

    if prefset.hasPrefHere("mappedPaths"):
        mapped_uris_modified = False
        encpathlist = prefset.getStringPref("mappedPaths")
        mapped_paths = encpathlist.split('::')
        new_mapped_paths = []
        for path in mapped_paths:
            data = path.split('##', 1)
            if len(data) == 2:
                # Update the path to be a URI.
                toURI = uriparse.pathToURI(data[1])
                if toURI != data[1]:
                    #print "upgraded mapped uri path from %r to %r" % (
                    #         data[1], toURI)
                    path = data[0] + '##' + toURI
                    mapped_uris_modified = True
            new_mapped_paths.append(path)
        if mapped_uris_modified:
            encpathlist = '::'.join(new_mapped_paths)
            prefset.setStringPref("mappedPaths", encpathlist)
