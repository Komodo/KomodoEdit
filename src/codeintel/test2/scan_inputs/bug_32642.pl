# Because of the strange (insane?) use of the here doc as the argument to
# somefunction(), $myvar and &myfunc do not get picked up by the Perl CILE.

if (somefunction(<<EndOfText)
some here doc content
EndOfText
    eq 'whatever') {
}

my $myvar;

sub myfunc {
};
