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

# Blackfile for project "custombuild"
#
#
# Currently Black has no ability to build a project. However,
# it can invoke a custom build procedure as expressed in the
# commandOverrides['build'] variable in a project Blackfile.py.
#
# This test project demonstrates how to do this.
#
# try running the following commands:
#   > bk
#   > bk configure
#   > bk                  # notice the change
#   > bk build
#   > bk build 42
#   > bk -v build 42
#

import os
import black, black.configure.std


# Define the configuration items for this project.
configuration = {
    # It is good practice to define a name and version for a project.
    "version": "0.1",
    "name": "simple",

    "perlBinDir": black.configure.std.PerlBinDir(),
}


# The custom build procedure.
def SayHello(projectConfig, argv):
    # a custom build procedure is launched "in" the project root directory
    print "the cwd is", os.getcwd()
    # a custom build procedure is passed the command line arg vector
    print "the command line args are", argv[1:]
    # the project configuration module (i.e. bkconfig.py) is passed in so the
    # routine can determine configuration items:
    #  - invoke perl using the configured Perl bin directory
    if len(argv[1:]) > 0:
        try:
            exitValue = int(argv[1])
        except ValueError:
            exitValue = 0
    else:
        exitValue = 0
    perlExe = os.path.join(projectConfig.perlBinDir, "perl")
    retval = os.system(''' %s -e "print 'hello'; exit(%d);" ''' %\
                       (perlExe, exitValue))
    # the standard black.BlackError exception can be raised, it
    # will be presented appropriately to the user
    if retval == 0:
        return retval
    else:   
        raise black.BlackError("unexpected return value: %s" % retval)

# override the Black "build" command
commandOverrides = {
    "build": SayHello,
}
