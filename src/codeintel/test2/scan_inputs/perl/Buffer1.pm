# Exercise the CIX generator to verify that we're producing
# expected output.

# Start with some code in the main, 
# then some explicit packages, and then pop back to main

# package main;

$var1 = 'string';
my $var2 = 3;

use LWP::UserAgent;

our $var3 = LWP::UserAgent->new();

use vars qw(var4 var5);

# Get this

sub sub1 {
}

# Get f

sub f {
    my $code = shift;
    $code->(4);
}

# Skip the sub here
f(sub { print 3 * $_[0], "\n" });

# Do not skip the sub here (private function)
my $closure = sub { my $a = shift; my $closure = 7; print $a + $closure, "\n"; };
f($closure);

package Buffer1;

use Digest::MD5 qw(md5 md5_hex md5_base64);

sub sub2($) {
    my $text = shift;
    my $digest = md5_base64($text);
    $digest;
}


package Buffer2::Part2::Part3;

sub sub3($$;$%) {
}

sub Other::Package::sub4 {
}

{
    package Buffer1::InnerPart1;
    sub sub4 {
        print "abc\n";
    }
}

package main;

sub sub5 {
}

{
    package Buffer1::InnerPart2;
    sub sub6 {
        print "def\n";
    }
}
