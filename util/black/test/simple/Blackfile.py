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

# Blackfile for project "simple"
#
# This project demonstrate the most basic use of Black: using it to
# generate configuration files containing only standard (i.e. built-in to
# Black) configuration items.
#
# Try this to see how it works:
#   > bk
#   ...shows help for this "hello" project...
#   > bk configure
#   ...configures the "hello" project (bkconfig.* are created)...
# These generated configuration files can be used for whatever build
# system is used to build "simple". As well, they are used by other standard
# Black commands.

import black.configure.std, black.configure.mozilla


# Define the configuration items for this project.
configuration = {
    # It is good practice to define a name and version for a project.
    "version": "0.1",
    "name": "simple",

    # Determine some system information about a Python installation that
    # might be useful for building later.
    # NOTE: The Black configuration mechanism is currently limited in
    #       that configuration items must be named the same as the 
    #       internal name used for the configuration item. I.e.,
    #         "pythonExeName" must be used for PythonExeName() because
    #         PythonExeName().name == "pythonExeName".
    "pythonExeName": black.configure.std.PythonExeName(),
    "pythonVersion": black.configure.std.PythonVersion(),
    "pythonInstallDir": black.configure.std.PythonInstallDir(),

    # Use the standard mozilla configuration module.
    # - "bk configure" will result in the default setting of
    #   "MOZILLA_OFFICIAL" in "bkconfig.{sh|bat}"
    # - "bk help configure" will show that the "--mozilla-official"
    #   option can be used to set the MOZILLA_OFFICIAL value
    # - Try "bk configure --mozilla-official=0" and see the result in
    #   "bkconfig.{sh|bat}".
    "MOZILLA_OFFICIAL": black.configure.mozilla.SetMozillaOfficial(),
}


