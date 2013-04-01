#!/bin/sh
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
# Komodo "AS Package" simple install script
#
# To install Komodo, run:
#   ./install.sh
# To see additional install options, run:
#   ./install.sh -h

dname=`dirname $0`
# use the python2.7 (or whatever) binary here, because `python` can be a shell
# script, and that will give us the wrong result
exe_type=`file "$dname"/INSTALLDIR/lib/python/bin/python*.*`
case `uname -m` in
    x86_64)
        machine_arch=".*64-bit"
        wanted_arch="x86_64";;
    i?86)
        machine_arch=".*32-bit"
        wanted_arch="x86";;
    *)
        # I dunno what you're doing, hopefully you're smart enough
        KOMODO_FORCE_ARCH=1;;
esac
print_arch_warning ( ) { true; }
if [ -z "$KOMODO_FORCE_ARCH" -a "0" -eq `expr "$exe_type" : "$machine_arch"` ] ; then
    print_arch_warning ( ) {
        cat >&1 <<-EOF
	[31;1m
	This Komodo binary may not be correct for your computer's architecture.
	You can download the $wanted_arch Komodo version at:
	http://www.activestate.com/komodo-edit/downloads
	[0m
	EOF
        }
fi
print_arch_warning
LD_LIBRARY_PATH="$dname/INSTALLDIR/lib/mozilla:"$LD_LIBRARY_PATH
export LD_LIBRARY_PATH
$dname/INSTALLDIR/lib/python/bin/python -E $dname/support/_install.py "$@"
print_arch_warning
