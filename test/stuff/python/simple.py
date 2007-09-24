# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# This sample Python program shows you some of the features in Komodo
# to help work with your Python code.

#---- Code Folding:
#   You can collapse and expand blocks of code. Click the "-" and "+"
#   signs in the light grey bar on the left.

#for i in range(10000):
#    print "a"
    
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

def testCallDispatch():
    print "testCallDispatch"

testCallDispatch()

def doException():
    raise Exception('testing')

try:    
    doException()
except:
    pass

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

for i in range(10):
    print "i is now ", i
    
# See Komodo's online help for much more information on:
#    - managing projects
#    - keyboard shortcuts
#    - remote debugging; and more
# Just press <F1>, or select Help from the Help menu.
