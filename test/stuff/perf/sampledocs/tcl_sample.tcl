#!tclsh
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# This sample Tcl program shows you some of the features in Komodo to
# help work with your Tcl code.

#---- Code Folding:
#    You can collapse and expand blocks of code. Click the "-" and "+"
#    signs in the light grey bar on the left.

proc moreFeather {} {
    global feather
    if {![info exists feather]} {
	set feather 0
    } else {
	incr feather; # default to 1
    }
    ::set ::var "I'm a string"
}
moreFeather

#---- Syntax Coloring:
#    Komodo detects keywords and applies syntax coloring.  In the code
#    above, note how "set" is a different color from "var", which is a
#    different color from ""I'm a string"".

#---- Background Syntax Checking: (requires ASPN Tcl license)
#    Komodo periodically checks for syntax errors in your Tcl code as
#    you type.  Komodo underlines syntax errors in red and green
#    "squiggles".  The green "squiggle" on the following line of code
#    indicates a Tcl warning. Put your cursor on the squiggle to see
#    the actual warning message in the status bar.

set val [expr $feather + 5]    ; # braces should be used for expressions

#    Uncomment the following line to see a Tcl error:
#string is alpha

#---- AutoCompletion and CallTips
#    Komodo helps you code faster by presenting you with available
#    methods for the command in Tcl. Komodo also shows you the list of
#    arguments you can pass to a function you are calling.
#
#    For example, on a blank line below this comment block, slowly
#    re-enter the following code below the original:
#        string is alpha
#
#    When you type the "r" in "string", Komodo lists the methods that
#    start with "str".  If you keep typing, when you get to "string
#    is", the list reduces to just the available methods. You can move
#    through the list with your up and down arrow keys.  When you
#    press "Tab", Komodo completes the rest of the method name for
#    you.  This is called AutoCompletion.
#
#    As you type a space after "string is alpha", Komodo lists the
#    arguments for how to call string. This is called CallTips.  For
#    another example of CallTips, start typing "if". Komodo lists the
#    arguments for how to call if.
#

#---- Debugging: (requires ASPN Tcl license)
#    You can debug your Tcl scripts with Komodo. For example, try the
#    following steps:
#
#    1. Set a breakpoint on the "moreFeather" line by clicking in the
#       dark grey vertical bar on the left.
#
#    2. Start debugging: from the Debug menu, select Start.
#
#    3. Go to your breakpoint: on the Debug toolbar, click "Go". 
#       (To view and hide the toolbars, click the "grippies" on the
#       left of each toolbar.)
#
#    4. Step into "moreFeather": Click on the "Step Into" button.
#       You can watch the program output on the Output pane below and
#       watch the variables in the Variables tab of the Output pane.
#
#    5. Select a variable with your mouse and drag it to the Watched
#       Variables pane to watch it.

set values [list 5 7 10 15]
moreFeather
set sum [expr {$feather + 2}]
foreach val $values {
    incr sum $val
    puts "The sum is now $sum"
}
puts "The final sum is $sum"

#---- See Komodo's online help for much more information on:
#    - managing projects
#    - keyboard shortcuts
#    - XML support; and more
# Just press <F1>, or select Help from the Help menu.
