# sample code for writing a web client
# test type info returned by perlcile

use strict;

use LWP::UserAgent;
use HTTP::Request;

my $req = HTTP::Request->new(POST => 'http://www.perl.com/cgi-bin/BugGlimpse');
$req->content_type('application/x-www-form-urlencoded');
$req->content('match=www&errors=0');

my $ua = new LWP::UserAgent;   # Indirect for of 'new'
my $res = eval { $ua->request($req); };
if ($@) {
    print "Error getting bugs: $@\n";
} else {
    print "Got back ", length($res->as_string), " chars\n";
}
