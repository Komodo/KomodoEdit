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
#
# This sample Perl program shows you how Komodo's Rx Toolkit can help
# you debug regular expressions in your Perl code.

# This file illustrates matching mail headers.  The __DATA__ block, at
# the end of this file, contains a typical short email message. This
# Perl script will attempt to filter out the mail headers in this
# message using a regular expression.

use strict;
use Data::Dumper;

my %headers;
while (<DATA>) {
        if (/(.*):(.*)/) {
                $headers{$1} = $2;
        }
}
print Dumper \%headers;

# This code matches the "From" and "To" lines correctly; however, it
# is does not filter out all the mail headers.  To see for yourself:
#
#       1. Run this script: on the Debug toolbar, click "Go".
#
#       2. Open the Output pane and look at the output. This script
#          a) matched the initial "From sox@" line, which should have
#             been skipped; and
#          b) matched the "Re" from the "Subject" line too early.

# It's time to use Rx Toolkit!
#
#       1. Select the regular expression text inside the "/" delimiters:
#               (.*):(.*)
#
#       2. On the standard toolbar, click Rx.  Komodo loads the
#          regular expression into Rx Toolkit.
#
#       3. Enter a string to match your regular expression against.
#          Select the text after the __DATA__ token (at the end of
#          this file).
#
#       4. Check the "Global" modifier option to have Rx Toolkit match
#          each line of data.
#
#       5. Click "Advanced" button to see the group match variables.
#
# The green highlighting shows which parts of the data the regular
# expression matches. You can edit the regular expression in Rx
# Toolkit and see the match results immediately.
#
# a) The regular expression matched the first line even though it's
#    not a valid email header.  The match is too broad: (.*) matches
#    any character any number of times, then a colon, then (.*)
#    matches any character any number of times.  You can narrow the
#    matches by requiring some whitespace after the colon. Change the
#    regular expression to this:
#               (.*):\s+(.*)
#
# b) It picked up the "Re" from the "Subject" line as part of the
#    first group. That's because there is another ":" after the
#    "Re". We can specify that only alphanumeric characters are
#    allowed before the ":".  Change the loaded regular expression to
#    this:
#               (\w*):\s+(.*)
#
# Now paste your debugged regular expression back into your code.

# For more information on regular expressions, see "Introduction to
# Regular Expressions" in Komodo's online help.  For more information
# on Rx Toolkit see "Using Rx Toolkit" in Komodo's online help.  Just
# press <F1>, or select Help from the Help menu.  To see other
# features Komodo provides for your Perl coding, see "perl_sample.pl"
# in this sample project.


__DATA__
From sox@laundry.com Wed Mar 28 12:02:04 2001
Date: Tue, 27 Mar 2001 14:48:53 -0800
From: Steven Sox <sox@laundry.com>
To: Eric Herrington <red@herring.com>
Subject: Re: are you done yet?

> When are you going to be finished your book, man? I've still only
> read the second draft. That was two months ago!

I finally finished it last night. Thanks so much for your support over
the last couple of months. This should be a best seller, "My Head Is
Shaped Like An Egg," by Steven Sox. Sounds good, eh?

One can always hope, anyway.

Later,
Steve.
