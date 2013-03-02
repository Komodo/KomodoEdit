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

This file creates an HTML file which is embedded in an iframe by iconpicker.xul.

This was originally done as dynamically created content, but
JavaScript security made it impossible for that to work in installer
builds (for some strange reason it worked in dev builds.

It is invoked by the Conscript file in this directory.  It takes two
arguments: the first is the name of the file to write to.  The second
is the relative path to the directory where the icons are stored.

"""

header = """<html>
<body>
<style>img { padding: 4px; }
img.hide { display: none; }
</style>
"""

footer = """</body>
</html>"""

imgtemplate = """
<img ondblclick="parent.ValidatedPickIcon('chrome://openoffice/skin/icons/%(fname)s');"
     onclick="parent.Pick_Icon('chrome://openoffice/skin/icons/%(fname)s');"
     src="chrome://openoffice/skin/icons/%(fname)s"
     alt="%(fname)s" />
"""

import sys, os
print sys.argv
target = sys.argv[1]
fp = open(target, 'w')
where = os.path.dirname(target)
here = os.getcwd()
content = []
extensions = ['.png', '.gif']
try:
    #os.chdir(where)
    #print os.getcwd()
    fp.write(header)
    icons = os.path.normpath(os.path.join(os.getcwd(), sys.argv[2]))
    print "icons are in ",icons
    for f in sorted(os.listdir(icons)):
        extension = os.path.splitext(f)[-1].lower()
        if extension in extensions:
            content.append(imgtemplate % {'fname': f})
    fp.write('\n'.join(content))
    fp.write(footer)
finally:
    os.chdir(here)
