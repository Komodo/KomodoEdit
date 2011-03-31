#!/usr/bin/perl -w
use strict;
use warnings;

use HTML::Tidy;
local $/ = undef;
my $data = <STDIN>;
#print $data;
my $tidy = HTML::Tidy->new;
$tidy->parse("input", $data);
foreach my $error ( $tidy->messages ) {
    print $error->as_string, "\n";
}
