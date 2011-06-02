#!tclsh
package require Tcl 8

# Use this sample script to explore some of Komodo's Tcl features.

# Incremental search:
#   - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
#   - Begin typing the characters you want to find. 
#   - As you type, the cursor moves to the first match after the current
#     cursor position. Press 'Esc' to cancel.

# Code Folding:
#  - Click the "+" and "-" symbols in the left margin.
#  - Use View|Fold to collapse or expand all blocks.

# Syntax Coloring:
# - Language elements are colored according to the Fonts and Colors
#   preference.

namespace eval ::zoo {
    # Some docs about moreFeather
    proc moreFeather {} {
	# Some stuff about moreFeather
	global feather
	if {![info exists feather]} {
	    set feather 0
	} else {
	    incr feather; # default to 1
	}
	::set ::var "I'm a string"
    }
}
::zoo::moreFeather


# Background Syntax Checking:
#   - Syntax errors are underlined in red.
#   - Syntax warnings are underlined in green.
#   - Configure Tcl Preferences to customize errors and warnings.
#   - Position the cursor over the underline to view the error or warning
#     message.
set val [expr $feather + 5]; 

# AutoComplete:
#   - On a blank line below, enter "str".
#   - Methods beginning with "str" are displayed.
#   - Press 'Tab' to insert the selected method.

#---- Abbreviations:
#     - Snippets from the Abbreviations folder in projects and toolboxes
#       can be inserted by typing the snippet name followed by
#       'Ctrl'+'T' ('Cmd'+'T' on OS X). The Samples folder in the
#       Toolbox contains some default abbreviation snippets to get you
#       started.
#    
#     Try this below with the 'for' Tcl snippet. An empty for loop
#     is created with "Tabstop" placeholders for the start condition,
#     test, next command and body code.

# CallTips
#   - On a blank line below, enter "if", and then press the space bar.
#   - The space triggers an argument reference for "if".


# More:
#   - Press 'F1' to view the Komodo User Guide.
#   - Select Help|Tutorial|Tcl Tutorial for more about Komodo and Tcl.

