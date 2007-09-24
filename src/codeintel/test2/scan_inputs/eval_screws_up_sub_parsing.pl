# Sample Perl code demonstrating parsing bug in Perl CILE. The
# eval results in the 'run' and 'jump' subs getting missed and the
# function "arguments" getting assigned to 'kick', such that is has
# three arguments. This seriously breaks parsing of CPAN.pm, for
# example.

sub kick {
    eval { require Data::Dumper };
    my ($target) = @_;
}

sub run {
    my ($command) = @_;
}

sub jump {
    my $howhigh = shift;
}


