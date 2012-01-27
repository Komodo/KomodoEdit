#!/usr/bin/env python3

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
        if type(element) is str:
            print("element %s is a string" % element)
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
#   - On a blank line below, enter "import textwrap" followed by "s = textwrap.".
#   - When you type the period after "textwrap", Komodo lists the available
#     methods in the textwrap module.
#   - Press 'Tab' to complete the "dedent" method.

# CallTips:
#   - Type the opening parenthesis at the end of "s = textwrap.dedent"
#   - When you type the opening parenthesis "(", Komodo lists the
#     parameters for how to call textwrap.dedent().

import textwrap
s = textwrap.dedent("   abc\n   def\n  ghi\n")
print("Wrapped text:\n%s" % s)

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

# #if WITH_DEBUGGING
# Debugging:
#   1. Set a breakpoint by clicking the left margin on line 59 ("sum = 0.0").
#   2. Press 'F5' to invoke the debugger; click "OK" to accept the default.
#   3. Press 'F11' to step into "sum = 0.0".
#   4. View variables and output on the Debug tab.
#   5. See the "Debug" menu for additional debug commands.
#   6. Press 'Shift'+'F5' to stop.

def printTotal(priceList):
    '''Prints a total of all prices in the list'''
    sum = 0.0
    for price in prices:
        sum = sum + price
    print("the sum of the prices is", sum)

prices = [5.50, 6.25, 7.00, 3.15]
printTotal(prices)

# Interactive Shell:
#   1. Select lines 57 to 65, and then press 'Ctrl'+'C'.
#   2. Select Tools|Interactive Shell|Start New Python Shell.
#   3. Press 'Ctrl'+'V'.
#   4. Press 'Enter'. The output is displayed in the Python Shell beneath
#      the code snippet.
# #endif

# #if WITH_CODE_BROWSER
# Code Browsing:
#   1. If necesssary, enable Komodo's code intelligence (Edit|Preferences|Code Intelligence).
#   2. Select View|Tabs|Code Browser.
#   3. On the Code tab, click the plus sign next to "python_sample".
#   4. If necessary, display the Code Description pane by clicking the
#      "Show/Hide Description" button at the bottom of the Code Browser.
#   5. Select "Imports". The Code Description pane indicates that the file
#      uses the string module.
# #endif

# More:
#   - Press 'F1' to view the Komodo User Guide.
#   - Select Help|Tutorial|Python Tutorial for more about Komodo and Python.
