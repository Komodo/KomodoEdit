# Variable $baz should be at the global scope.

$quux = 'abc';
sub foo {
    my $bar = 1;
    $baz = 2;
}

#foo();
#print "QUUX: $quux\n";
#print "BAZ: $baz\n";
#print "BAR: $bar\n";
