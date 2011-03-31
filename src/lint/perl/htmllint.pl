#!/usr/bin/perl -w
use strict;
use warnings;

use HTML::Lint;
local $/ = undef;
my $data = <STDIN>;
#print $data;
my $lint = HTML::Lint->new;
$lint->parse($data);
foreach my $error ( $lint->errors ) {
    print $error->as_string, "\n";
}
