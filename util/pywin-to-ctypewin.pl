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