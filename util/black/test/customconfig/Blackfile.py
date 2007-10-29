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

# Blackfile for project "customconfig"
#
# This project demonstrates how to add custom configuration items to a
# project. Black defines a class hierarchy of configuration items from
# which a project can subclass to define project-specific items.
#

import sys, os
import black.configure, black.configure.std


#---- custom configuration classes

class PerlH(black.configure.Datum):
    """A configuration Datum (i.e. piece of information) that determines
    the absolute path to Perl.h in the perl installation."""
    def __init__(self):
        # You must give, at minimum, a "name" to your configuration item.
        black.configure.Datum.__init__(self, "perlH",
            desc="the full path to the main Perl header")

    def _Determine_Do(self):
        # You must override _Determine_Do() to determine the value for your
        # configuration item. _Determine_Do must:
        #   - Set "self.applicable". This is a boolean indicating if the
        #     configuration item applies to the current state. For example,
        #     an item to determine where MSVC is installed is only applicable
        #     if the current platform is Windows.
        #   - Set "self.value" iff self.applicable is true.
        #   - Set "self.determined" to true on completion.
        #
        # You can access other configuration items via the global dictionary
        # "black.configure.items". Two methods are of interest. Determine()
        # returns the value of "self.applicable" for that item. Get() returns
        # "self.value" for that item (None if the item is not applicable).
        item = black.configure.items["perlInstallDir"]
        # can't find Perl.h if Perl is not installed
        self.applicable = item.Determine()
        if self.applicable:
            perlInstallDir = item.Get()
            if sys.platform.startswith("win"):
                self.value = os.path.join(perlInstallDir, "lib", "CORE",
                                          "Perl.h")
            else:
                # presuming Perl 5.6 (although could check with
                # "perlVersion")
                self.value = os.path.join(perlInstallDir, "lib", "5.6.0",
                                          "i686-linux-thread-multi", "CORE",
                                          "perl.h")
        self.determined = 1

    def _Determine_Sufficient(self):
        # You can optionally define this method (called after
        # _Determine_Do() if the item is found to be applicable) to verify
        # that the determined value is sufficient/valid. Typically a
        # black.configure.ConfigureError is raised if the determined value
        # was insufficient.
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s.\n" % self.desc)
        elif not os.path.isfile(self.value):
            # if a value was found then ensure that it exists 
            raise black.configure.ConfigureError(
                "'%s' does not exist.\n" % self.value)


configuration = {
    # It is good practice to define a name and version for a project.
    "version": "0.1",
    "name": "customconfig",

    # Determine some system information about a Perl installation that
    # might be useful for building later.
    "perlVersion": black.configure.std.PerlVersion(),
    "perlInstallDir": black.configure.std.PerlInstallDir(),

    # use your custom PerlH configuration item.
    "perlH" : PerlH(),
}


