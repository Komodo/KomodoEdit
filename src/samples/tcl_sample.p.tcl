#!tclsh
# Copyright (c) 2000-2006 ActiveState Software Inc.
package require Tcl 8

# Use this sample script to explore some of Komodo's Tcl features.

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


# CallTips
#   - On a blank line below, enter "if", and then press the space bar.
#   - The space triggers an argument reference for "if".


# More:
#   - Press 'F1' to view the Komodo User Guide.
#   - Select Help|Tutorial|Tcl Tutorial for more about Komodo and Tcl.
