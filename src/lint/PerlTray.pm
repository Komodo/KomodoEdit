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

package PerlTray;
use strict;
use Exporter ();
use vars qw($AUTOLOAD @EXPORT_OK @EXPORT);

=head ABOUT THIS FILE

The purpose of this file is to allow programs indended for PerlTray
deployment to be syntax-checked in Komodo.  This file should not be
used by PerlTray programs in a Perl Dev Kit environment.

See bug http://bugs.activestate.com/show_bug.cgi?id=27963
("No Syntaxcheck when using PerlTray")

=cut

@EXPORT = qw(Balloon DisplayMenu Download Execute MessageBox
            CAPTION
            MB_OK MB_OKCANCEL MB_YESNOCANCEL MB_YESNO MB_RETRYCANCEL
            MB_CANCELTRYCONTINUE MB_ICONERROR MB_ICONQUESTION MB_ICONINFORMATION
            MB_ICONWARNING MB_DEFBUTTON2 MB_DEFBUTTON3
            IDOK IDCANCEL IDYES IDNO IDTRYAGAIN IDCONTINUE
            RegisterHotKey SetAnimation SetIcon SetTimer Click DoubleClick
            PopupMenu Shutdown Singleton TimeChange Timer ToolTip );

@EXPORT_OK = qw(extract_bound_file exe get_bound_file);

sub AUTOLOAD {
    die "Invalid attempt to call $AUTOLOAD with stub file, not the true PerlTray.pm";
}

1;