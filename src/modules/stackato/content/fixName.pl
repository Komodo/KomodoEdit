use strict;
use warnings;

while(<>) {
    my $x = $_;
    if ($x =~ m/^(.*)(="[\w\d]*-[\w\d\-]+")(.*)/msx) {
	my $a = $1;
	my $b = $2;
	my $c = $3;
	$b =~ s/-/_/g;
	$x = "$a$b$c";
    }
    print $x;
}
