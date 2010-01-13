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
from os.path import islink, realpath, join

def _walk_avioiding_cycles(top, topdown=True, onerror=None, followlinks=False):
    seen_rpaths = {top: 1}
    for root, dirs, files in os.walk(top, topdown, onerror, followlinks):
        # We modify the original "dirs" list, so that os.walk will then ignore
        # the directories we've removed.
        for dir in dirs[:]:  # a copy, so we can modify in-place.
            dirpath = join(root, dir)
            if islink(dirpath):
                rpath = realpath(dirpath)
                if rpath in seen_rpaths:
                    #print "Found cyclical path: %s to %s" % (dirpath, rpath)
                    dirs.remove(dir)
                    continue
                seen_rpaths[rpath] = 1
        yield (root, dirs, files)

def walk_avioiding_cycles(top, topdown=True, onerror=None, followlinks=False):
    """Modified os.walk, one that will keep track of followed symlinks in order
    to avoid cyclical links."""

    if not followlinks:
        return os.walk(top, topdown, onerror, followlinks)
    else:
        # Can only avoid cycles if topdown is True.
        if not topdown:
            raise Exception("walk_avioiding_cycles can only avoid cycles when "
                            "topdown is True")
        return _walk_avioiding_cycles(top, topdown, onerror, followlinks)
