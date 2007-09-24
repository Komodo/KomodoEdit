package ReversePhoneLookup;

=for interface
    static ustring reversephonelookup( ustring country, int32 areacode, int32 phoneno );
    <soap namespace="http://activestate.com/"/>
=cut

sub reversephonelookup
{
    $country = shift; 
    $areacode = shift; 
    $phoneno = shift;     

    # Create a user agent object
    use LWP::UserAgent;
    $ua = new LWP::UserAgent;
    $ua->agent("AgentName/0.1 " . $ua->agent);

    # Create a request
    my $req = new HTTP::Request POST => 'http://www.thinkdirectmarketing.com/freesearch/phone10.asp';

    $req->content_type('application/x-www-form-urlencoded');
    $content = 'areacode='.$areacode.'&phoneno='.$phoneno.'&country='.$country;
    $req->content($content);

    # Pass request to the user agent and get a response back
    my $res = $ua->request($req);

    # Check the outcome of the response
    if ($res->is_success) {
        #print $res->content;
        #print "\n";
    } else {
        print "Bad luck this time\n";
    }

    my $fullstr = $res->content;
    my $badstr = "Sorry, no matches";
    my $pos = index($fullstr, $badstr);

    my $answer = "";

    if ($pos != -1)
    {
        $answer = $answer."No matches!";
    }
    else
    {
        my $beginstr = "<!-- beginning of row -->";
        $pos = index($fullstr, $beginstr);
        if ($pos == -1)
        {
            $answer = $answer."Query Failure!";         
        }
        else
        {
            # grab the entry number (always = 1)
            $endpos = index($fullstr, "</font>", $pos);
            $startpos = rindex($fullstr, ">", $endpos);
            $answer = $answer.substr($fullstr, $startpos+1, ($endpos-$startpos-1));    
            # grab the name
            $pos = $endpos+1;
            $endpos = index($fullstr, "</font>", $pos);     
            $startpos = rindex($fullstr, ">", $endpos);
            $answer = $answer.substr($fullstr, $startpos+1, ($endpos-$startpos-1));
            # grab the rest
            $pos = $endpos+1;
            $endpos = index($fullstr, "</font>", $pos);     
            $startpos = rindex($fullstr, "<Br>", $endpos);
            $answer = $answer.substr($fullstr, $startpos+4, ($endpos-$startpos-4));
            $answer =~ s/<br>//g;    
        }
    }

    return $answer;

}

#self test
unless (caller)
{
    print reversephonelookup("604", "3228838", "CANADA");
}

1;
