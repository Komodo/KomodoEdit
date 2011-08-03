use strict;
use Digest::MD5;

my $dig1 = Digest::MD5->new;
my $dig2 = new Digest::MD5;

print "diffs: [$dig1], [$dig2]\n";

use LWP::UserAgent;

my $a1 = LWP::UserAgent->new;
print $a1->request;

my $a2 = new LWP::UserAgent;

use SOAP::Lite;
my $s1 = SOAP::Lite->new;

use HTTP::Request;
my $req = HTTP::Request->new(GET => "http://www.wired.com");
my $res = $req->add_part;

my $req2 = new HTTP::Request(GET => 'http://www.wired.com');
$res = $req2->
