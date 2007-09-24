package Foo;
use strict;

sub new {
    my $class = shift;
    my $self = bless {}, $class;
    return $self;
}

1;