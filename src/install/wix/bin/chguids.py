#!python

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
# Change all GUIDs in the give files.
# 
# Note: WiX (MSI?) requires uppercase A-F hex letters.
#

import os
import sys
import re
from os.path import exists
import shutil

def new_guid():
    import pythoncom
    guid = str(pythoncom.CreateGuid())
    guid = guid[1:-1] # strip of the {}'s
    return guid


def main():
    for filepath in sys.argv[1:]:
        print "changing GUIDs in '%s':" % filepath

        fin = open(filepath, 'r')
        original = content = fin.read()
        fin.close()
        # E.g.: Guid="32A46AA4-051B-4574-A6B2-E7B3C7666CB6"
        pattern = re.compile('Guid="([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"')
        for match in pattern.finditer(content):
            start, end = match.start(1), match.end(1)
            guid = new_guid()
            assert (end-start) == len(guid)
            print "  s/%s/%s/" % (content[start:end], guid)
            content = content[:start] + guid + content[end:]

        if content == original:
            print "  no changes, leaving alone"
        else:
            bakpath = filepath+".bak"
            print "  backing up original to '%s'" % bakpath
            if exists(bakpath):
                os.chmod(bakpath, 0777)
                os.remove(bakpath)
            shutil.copy2(filepath, bakpath)

            try:
                fout = open(filepath, 'w')
            except EnvironmentError, ex:
                print "  p4 edit %s" % filepath
                os.system("p4 edit %s" % filepath)
                fout = open(filepath, 'w')
            fout.write(content)
            fout.close()

main()    

