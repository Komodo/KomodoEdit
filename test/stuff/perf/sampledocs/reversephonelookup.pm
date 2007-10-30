# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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
