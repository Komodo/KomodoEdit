# client1.pm 
# Test bug 31500

use File::Basename;
use strict;
use if;
use utf8;
use modules::Settings;

require modules::if;
use bigrat::smallcow;
require constant;

our($VERSION, @ISA, @EXPORT, @EXPORT_OK, $Verbose, $Keep, $Maxlen,
    $CheckForAutoloader, $CheckModTime);
$VERSION = "1.04";
@ISA = qw(Exporter);
@EXPORT = qw(&autosplit &autosplit_lib_modules);
@EXPORT_OK = qw($Verbose $Keep $Maxlen $CheckForAutoloader $CheckModTime);

my $x = modules::Settings->new();

sub hereForTesting {
    print "Nothing\n";
    $< = 1;
    $& = 5;
    $> = 7;
}
