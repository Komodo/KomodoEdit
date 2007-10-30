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

# Run a number of cases of 'measure_lint_leak.py'

import os, time

timeStamp = int(time.time())
desc = "linting-off"
runs = [
        {'desc': 'ko11-python-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.py',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko11-perl-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.pl',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko11-xml-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.xml',
         'komodo': r'C:\Program Files\Komodo-1.1\komodo.exe',
        },
        {'desc': 'ko12-python-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.py',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
        {'desc': 'ko12-perl-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.pl',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
        {'desc': 'ko12-xml-%s-%s' % (desc, timeStamp),
         'file': 'lint_leak.xml',
         'komodo': r'C:\Program Files\Komodo-1.2\komodo.exe',
        },
       ]

#logDir = r"\\crimper\apps\Komodo\stuff\trents_metric_logs\measure_lint_leak\"
cmdTemplate = r'python measure_lint_leak.py --komodo="%(komodo)s" %(file)s > measure_lint_leak.%(desc)s.log'

for run in runs:
    cmd = cmdTemplate % run
    print "running '%s'..." % cmd
    os.system(cmd)

