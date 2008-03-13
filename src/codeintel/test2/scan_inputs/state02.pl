use strict;
use warnings;

state $g1 = 1;

sub foo {
    state $l2 = 2;
    if (shift) {
	state $l3 = 3;
    }
}

if ($g1) {
    state $l4 = 4;
}
