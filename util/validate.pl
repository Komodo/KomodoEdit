#!perl -w
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


use XML::Parser;
my $file = shift;
die "Can't find file \"$file\""  unless -f $file;

my $parser = new XML::Parser(Namespaces => 1);
$parser->parsefile($file);
