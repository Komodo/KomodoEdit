#!tclsh
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
