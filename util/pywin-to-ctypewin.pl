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

use strict;
use warnings;

my $file = shift;
local $/;

my $contents;
if ($file) {
    open my $fh, "<", $file or die "Can't open $file; $!";
    binmode $fh;
    $contents = <$fh>;
    close $fh;
} else {
    $contents = <STDIN>;
}

my $ws_re = qr/[\s\r\n]*/;
my $PAD = "****\n\t\t\t\t\t";
$contents =~ s{win32api\.CloseHandle}{wnd.komodo.close_handle}msxg;
$contents =~ s{win32gui\.GetActiveWindow}{wnd.komodo.get_active_window}msxg;
$contents =~ s{win32gui\.SetForegroundWindow}{wnd.komodo.set_foreground_window}msxg;

$contents =~ s{win32event\.CreateEvent${ws_re}
               \($ws_re
               None${ws_re},${ws_re}
               1${ws_re},${ws_re}
               0${ws_re},${ws_re}
               (.*?)\)}
              {wnd.komodo.create_event($1)}msxg;
$contents =~ s{win32event\.CreateEvent\(}{wnd.komodo.create_event($PAD}msxg;
$contents =~ s{win32event\.SetEvent}{wnd.komodo.set_event}msxg;
$contents =~ s{win32event\.ResetEvent}{wnd.komodo.reset_event}msxg;

$contents =~ s{win32event\.CreateMutex${ws_re}
               \($ws_re
               None${ws_re},${ws_re}
               0${ws_re},${ws_re}
               (.*?)\)}
              {wnd.komodo.create_mutex($1)}msxg;
$contents =~ s{win32event\.CreateMutex\(}{wnd.komodo.create_mutex\($PAD}msxg;

$contents =~ s{win32event\.ReleaseMutex}{wnd.komodo.release_mutex}msxg;
$contents =~ s{win32event\.WAIT_OBJECT_0}{wnd.komodo.WAIT_OBJECT_0}msxg;
$contents =~ s{win32event\.WaitForSingleObject${ws_re}
               \(${ws_re}(\w+),${ws_re}
               win32event\.INFINITE}{wnd.komodo.wait_for_single_object($1}msxg;
$contents =~ s{win32event\.WaitForSingleObject}{wnd.komodo.wait_for_single_object}msxg;

$contents =~ s{win32event\.WaitForMultipleObjects}{wnd.komodo.wait_for_multiple_objects}msxg;

print $contents;