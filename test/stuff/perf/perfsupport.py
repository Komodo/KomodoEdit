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

import os, sys, time
import which
from memutils import getpidsforprocess

def startKomodo(args=[]):
    # start up Komodo with the testFile
    # - spawn komodo and wait to startup
    verbose = 1
    komodoExe = which.which("komodo")
    out = sys.stdout
    pidsBefore = getpidsforprocess('mozilla')

    argv = [os.path.basename(komodoExe), '-v', '']
    os.spawnv(os.P_NOWAIT, komodoExe, argv)
    if verbose:
        out.write("Wait for '%s %s' to start up.\n" % (komodoExe,
                                                       ' '.join(args)))
    time.sleep(20)
    # - determine process PID and prefix for Win32 PDH logging
    pidsAfter = getpidsforprocess('mozilla')
    newPids = [pid for pid in pidsAfter if pid not in pidsBefore]
    if len(newPids) == 0:
        raise "No new Mozilla PIDs were found. The same Komodo was probably already running."
    elif len(newPids) > 1:
        raise "More that one Mozilla process was started by spawning Komodo!"
    else:
        pid = newPids[0]
    return pid
