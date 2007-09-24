#!/usr/bin/perl
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# This sample Perl program shows you some of the features in Komodo to
# help work with your Perl code.

# Turn on strict mode to make Perl check for common mistakes.
use strict;
#use DB;

#---- Code Folding:
#    You can collapse and expand blocks of code. Click the "-" and "+"
#    signs in the light grey bar on the left.

my @fruits = ("apples", "pears", "oranges");
foreach (@fruits) {
        if ($_ ne "apples") {
                print "I like $_\n";
        }
}


#---- Background Syntax Checking:
#    Komodo periodically checks for syntax errors in your Perl code as
#    you type.  Komodo underlines syntax errors in red and green
#    "squiggles".  The green "squiggle" on the following line of code
#    indicates a Perl warning. Put your cursor on the squiggle to see
#    the actual warning message in the status bar.

"hello there";

#    Uncomment the following line to see a Perl error:
#use foobar;    # try to use a bogus Perl module

#---- Syntax Coloring:
#    Komodo detects keywords and applies syntax coloring.  In the code
#    below, note how "my" is a different color from "@prices", which
#    is a different color from ""the sum of the prices is $sum\n"".

#---- Debugging
#    You can debug your Perl scripts with Komodo. For example, try the
#    following steps:
#
#    1. Set a breakpoint on the "my $sum = 0.0;" line by clicking in the
#       dark grey vertical bar on the left.
#
#    2. Start debugging: from the Debug menu, select Start.
#
#    3. Go to your breakpoint: on the Debug toolbar, click "Go". 
#       (To view and hide the toolbars, click the "grippies" on the
#       left of each toolbar.)
#
#    4. Step through the for loop: click any of the "Step" buttons.
#       You can watch the program output on the Output pane below and
#       watch the variables in the Variables tab of the Output pane.
#
#    5. Select a variable with your mouse and drag it to the Watched
#       Variables pane to watch it.

my @prices = (5.50, 6.25, 7.00, 3.15);
my $sum = 0.0;
for (my $i=0; $i < scalar(@prices); $i++) {
    DB::catch();
    $sum += $prices[$i];
}
print "the sum of the prices is $sum\n";


#---- Rx Toolkit (for debugging regular expressions)
#    Komodo allows you to debug regular expressions in your Perl code.
#    See the "rx_sample.pl" Perl file in this sample project for more
#    information.


#---- See Komodo's online help for much more information on:
#    - managing projects
#    - keyboard shortcuts
#    - remote debugging; and more
# Just press <F1>, or select Help from the Help menu.
