#!/usr/bin/perl
# Copyright (c) 2000-2006 ActiveState Software Inc.

# Use this sample script to explore some of Komodo's Perl features.

# Turn on strict mode to make Perl check for common mistakes.
use strict;

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

#    More:
#    - Press 'F1' to view the Komodo User Guide.
#    - Select Help|Tutorial|Perl Tutorial for more about Komodo and Perl.

