#!/usr/bin/perl

# Use this sample script to explore some of Komodo's Perl features.

# Turn on strict mode to make Perl check for common mistakes.
use strict;

#---- Incremental search:
#    - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
#    - Begin typing the characters you want to find. 
#    - As you type, the cursor moves to the first match after the current
#      cursor position. Press 'Esc' to cancel.

#---- Code Folding:
#    - Click the "+" and "-" symbols in the left margin.
#    - Use View|Fold to collapse or expand all blocks.

#---- Syntax Coloring:
#    - Language elements are colored according to the Fonts and Colors
#      preference.

sub fruits_i_like {
        foreach my $fruit (@_) {
                if ($fruit ne "apples") {
                        print "I like $fruit\n";
                }
        }
}

my @fruits = qw(apples pears oranges);
fruits_i_like(@fruits);

#---- Background Syntax Checking:
#     - Syntax errors are underlined in red.
#     - Syntax warnings are underlined in green.
#     - Configure Perl preferences to customize errors and warnings.
#     - Position the cursor over the underline to view the error or warning message.

"hello there";

sub print_total {
        my $sum = 0;
        foreach my $price (@_) {
            $sum += $price;
        }
        print "The sum of the prices is $sum\n";
}
my @prices = (5.50, 6.25, 7.00, 3.15);
print_total(@prices);

#---- Autocomplete and calltips
#     - Add a 'use'-statement.
#     - Re-enter a call to "print_total()".

#---- Abbreviations:
#     - Snippets from the Abbreviations folder in projects and toolboxes
#       can be inserted by typing the snippet name followed by
#       'Ctrl'+'T' ('Cmd'+'T' on OS X). The Samples folder in the
#       Toolbox contains some default abbreviation snippets to get you
#       started.
#    
#     Try this below with the 'fore' Perl snippet. An empty foreach
#     block is created with "Tabstop" placeholders for the variable and
#     expression.

#    More:
#    - Press 'F1' to view the Komodo User Guide.
#    - Select Help|Tutorial|Perl Tutorial for more about Komodo and Perl.

