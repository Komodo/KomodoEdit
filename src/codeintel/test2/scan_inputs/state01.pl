use strict;
use warnings;

my $g1 = 1;

sub foo {
    my $l2 = 2;
    if (shift) {
	my $l3 = 3;
    }
}

if ($g1) {
    my $l4 = 4;
}
