#!/usr/bin/perl -w
use strict;

use LWP::UserAgent;

# Create a user agent object
my $ua = LWP::UserAgent->new;
$ua->agent("$0/0.1 " . $ua->agent);
# $ua->agent("Mozilla/8.0") # pretend we are very capable browser :)

# Initialize proxy settings from environment variables
$ua->env_proxy;

# Create a request
my $req = HTTP::Request->new(GET => 'http://www.ActiveState.com');
$req->header('Accept' => 'text/html');

# Pass request to the user agent and get a response back
my $res = $ua->request($req);

# Check the outcome of the response
if ($res->is_success) {
    print $res->content;
}
else {
    print "Error: " . $res->status_line . "\n";
}
