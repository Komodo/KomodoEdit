use strict;
use warnings;

while (<>) {
    s@^( +)(?=<)@' ' x (length($1) / 2)@e;
    print;
}
