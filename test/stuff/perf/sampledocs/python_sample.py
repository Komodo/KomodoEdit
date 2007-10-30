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
# This sample Python program shows you some of the features in Komodo
# to help work with your Python code.

#---- Code Folding:
#   You can collapse and expand blocks of code. Click the "-" and "+"
#   signs in the light grey bar on the left.

mylist = ["hello", 42, "there", 3.14159]
for element in mylist:
    if type(element) == type(""):
        print "element %s is a string" % element
print


#---- Background Syntax Checking:
#    Komodo periodically checks for syntax errors in your Python code
#    as you type.  Komodo underlines syntax errors in red and green
#    "squiggles".  For example, uncomment the following line of
#    code. The red squiggle indicates the error. Put your cursor on
#    the squiggle to see the actual error message in the status bar.

#my_variable =

#---- Syntax Coloring:
#    Komodo detects keywords and applies syntax coloring.  In the code
#    below, note how "print" is a different color from "string.split",
#    which is a different color from ""hello there pete"".

#---- AutoCompletion and CallTips
#   Komodo helps you code faster by listing the available methods and
#   properties of Python modules and objects. Komodo also lists the
#   parameters you can pass to a method you are calling.
#
#   For example, on a blank line below this comment block, slowly
#   re-enter the following code below the original print
#   string.split("hello there pete", " ") When you type the period
#   Komodo lists the methods in the string module to choose from. Move
#   through the list with your up and down arrows.  To select a method
#   name, press "Tab". Komodo fills in the rest of the method.  This
#   is called AutoCompletion.
#
#   When you type the open parenthesis "(", Komodo lists the
#   parameters for how to call string.split(). This is called
#   CallTips.

import string
print string.split("hello there pete", " ")


#---- Debugging
#    You can use Komodo to debug your Python programs. For example,
#    try the following steps:
#
#    1. Set a breakpoint on the "sum = 0.0" line: click in the dark
#       grey vertical bar on the left.
#
#    2. Start debugging: from the Debug menu, select Start.
#
#    3. Go to your breakpoint: on the Debug toolbar, click "Go".  (To
#       view and hide the toolbars, click the "grippies" on the left
#       of each toolbar.)
#
#    4. Step through the for loop: click any of the "Step" buttons.
#       You can watch the program output on the Output pane below and
#       watch the variables in the Variables tab of the Output pane.
#
#    5. Select a variable with your mouse and drag it to the Watched
#       Variables pane to watch it.

prices = [5.50, 6.25, 7.00, 3.15]
sum = 0.0
for price in prices:
    sum = sum + price
print "the sum of the prices is", sum


# See Komodo's online help for much more information on:
#    - managing projects
#    - keyboard shortcuts
#    - remote debugging; and more
# Just press <F1>, or select Help from the Help menu.
