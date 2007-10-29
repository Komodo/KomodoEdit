#!/usr/bin/env python

""" xmldiff -- a quick-and-dirty reasonable XML Diff utility that
uses Python 2.4 and ElementTree (http://effbot.org/zone/element-index.htm)

Usage: python xmldiff [-i tag@attr]* file1 file2

Outputs diffs, exits with a status of:
0 - no reportable diffs
1 - reportable diffs, but processing continued
2 - reached a diff where processing couldn't continue

Written by: Eric Promislow, ActiveState Software Inc.  <ericp@activestate.com>
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

The contents of this file are may be used under the terms of either
the Mozilla Public License Version 1.1 (obtainable at http://www.mozilla.org/MPL/),
the GNU General Public License Version 2 or later (the "GPL"), or
the GNU Lesser General Public License Version 2.1 or later (the "LGPL").

"""

import re
import os.path
import sys

import elementtree.ElementTree as ET

class Compare:
    def compare(self, f1, f2, ignores):
        e1 = ET.parse(f1).getroot()
        e2 = ET.parse(f2).getroot()
        self.ignores = ignores
        self.rc = 0
        self._do_diff(e1, e2)
        
    def fix_ws(self, s):
        s1 = re.sub(r'\r?\n', ' ', s)
        s2 = re.sub(r'\t', ' ', s1)
        s3 = re.sub(r'\s+', ' ', s2).strip()
        return s3
    
    def err(self, rc):
        if self.rc < rc:
            self.rc = rc

    def _do_diff(self, e1, e2):
        if (e1.tag != e2.tag):
            print "**** tag name diff:\n< %s\n> %s\n" % (e1.tag, e2.tag)
            self.err(2)
            return
        k1 = e1.attrib.keys()
        k2 = e2.attrib.keys()
        for k in k1:
            if not k in k2:
                print "**** tag %s, missing attr:\n< %s\n" % (e1.tag, k)
                self.err(1)
            elif e1.attrib[k] != e2.attrib[k] and not self.ignores.has_key("%s@%s" % (e1.tag, k)):
                print "**** tag %s@%s: attr-mismatch:\n< %s\n> %s" % (e1.tag, k, e1.attrib[k], e2.attrib[k])
                self.err(1)
        for k in k2:
            if not k in k1:
                print "**** tag %s, extra attr:\n> %s\n" % (e1.tag, k)
                self.err(1)
        for pyattr in ['text', 'tail']:
            ta = [getattr(e1, pyattr, None), getattr(e2, pyattr, None)]
            for i in (0, 1):
                t = ta[i]
                if t is None: ta[i] = ""
                else: ta[i] = ta[i].strip()
            t1 = ta[0]
            t2 = ta[1]
            if t1 != t2:
                t1a = self.fix_ws(t1)
                t2a = self.fix_ws(t2)
                if t1a != t2a:
                    print "**** tag %s: %s:\n< [%s]\n> [%s]" % (pyattr, e1.tag, t1, t2)
                    self.err(1)
        c1 = e1.getchildren()
        c2 = e2.getchildren()
        if len(c1) != len(c2):
            print "**** tag %s: child-miscount:\n< [%d]\n> [%d]" % (e1.tag, len(c1), len(c2))
            self.err(2)
        else:
            for i in range(len(c1)):
                self._do_diff(c1[i], c2[i])
        
if __name__ == "__main__":
    argv = sys.argv
    cmd = argv[0]
    del argv[0]
    ignores = {}
    while len(argv) > 0:
        if argv[0].startswith('-i'):
            if len(argv[0]) > 2:
                ignores[argv[0][2:]] = None
                del argv[0]
            else:
                ignores[argv[1]] = None
                del argv[1]
                del argv[0]
        else:
            break
    cls = Compare()
    cls.compare(argv[0], argv[1], ignores)
    sys.exit(cls.rc)