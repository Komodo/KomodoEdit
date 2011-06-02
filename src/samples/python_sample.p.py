#!/usr/bin/env python

# Use this sample script to explore some of Komodo's Python features.

# Incremental search:
#   - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
#   - Begin typing the characters you want to find. 
#   - As you type, the cursor moves to the first match after the current
#     cursor position. Press 'Esc' to cancel.

# Code Folding:
#   - Click the "+" and "-" symbols in the left margin.
#   - Use View|Fold to collapse or expand all blocks.

def printStrings(mylist):
    '''This function will print all the items in list that are a string type'''
    import types
    for element in mylist:
        if type(element) == types.StringType:
            print "element %s is a string" % element
    print

mylist = ["hello", 42, "there", 3.14159]
printStrings(mylist)

# Background Syntax Checking:
#   - Syntax errors are underlined in red.
#   - Syntax warnings are underlined in green.
#   - Configure Python Preferences to customize errors and warnings.
#   - Position the cursor over the underline to view the error or warning
#     message.

# Syntax Coloring:
#   - Language elements are colored according to the Fonts and Colors
#     preference.

# AutoComplete:
#   - On a blank line below, enter "print string.".
#   - When you type the period after "string", Komodo lists the available
#     methods in the string module.
#   - Press 'Tab' to complete the method.

# CallTips:
#   - On a blank line below, enter "print string.split("
#   - When you type the opening parenthesis "(", Komodo lists the
#     parameters for how to call string.split().

import string
print string.split("hello there pete", " ")

#---- Abbreviations:
#     - Snippets from the Abbreviations folder in projects and toolboxes
#       can be inserted by typing the snippet name followed by
#       'Ctrl'+'T' ('Cmd'+'T' on OS X). The Samples folder in the
#       Toolbox contains some default abbreviation snippets to get you
#       started.
#    
#     Try this below with the 'class' Python snippet. A class block is
#     created with "Tabstop" placeholders for the class name and body
#     code.

# More:
#   - Press 'F1' to view the Komodo User Guide.
#   - Select Help|Tutorial|Python Tutorial for more about Komodo and Python.
