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