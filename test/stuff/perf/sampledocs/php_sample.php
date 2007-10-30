<!-- ***** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1
 
 The contents of this file are subject to the Mozilla Public License
 Version 1.1 (the "License"); you may not use this file except in
 compliance with the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/
 
 Software distributed under the License is distributed on an "AS IS"
 basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 License for the specific language governing rights and limitations
 under the License.
 
 The Original Code is Komodo code.
 
 The Initial Developer of the Original Code is ActiveState Software Inc.
 Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 ActiveState Software Inc. All Rights Reserved.
 
 Contributor(s):
   ActiveState Software Inc
 
 Alternatively, the contents of this file may be used under the terms of
 either the GNU General Public License Version 2 or later (the "GPL"), or
 the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.
 
 ***** END LICENSE BLOCK ***** -->

<!--      This sample PHP script shows you some of the features in Komodo
     to help you work you with your PHP code. -->
     
<?php

#---- Code Folding:
# You can collapse and expand blocks of code. Click the "-" and "+"
# signs in the light grey bar on the left.

class foo {
    var $a;
    var $b;
    function display() {
        echo "This is class foo\n";
        echo "a = ".$this->a."\n";
        echo "b = ".$this->b."\n";
    }
    function mul() {
        return $this->a*$this->b;
    }
};

class bar extends foo {
    var $c;
    function display() {  /* alternative display function for class bar */
        echo "This is class bar\n";
        echo "a = ".$this->a."\n";
        echo "b = ".$this->b."\n";
        echo "c = ".$this->c."\n";
    }
};

$foo1 = new foo;
$foo1->a = 2;
$foo1->b = 5;
$foo1->display();
echo $foo1->mul()."\n";

echo "-----\n";

$bar1 = new bar;
$bar1->a = 4;
$bar1->b = 3;
$bar1->c = 12;
$bar1->display();
echo $bar1->mul()."\n";


#---- Background Syntax Checking:
#    If you have PHP version 4.05 or greater installed, Komodo
#    periodically checks your code for syntax errors as you type.
#    Komodo underlines syntax errors in red and green "squiggles". For
#    example, remove the "$" from the "x" variable in the following
#    line of code. The red squiggle indicates the error. Put your
#    cursor on the squiggle to see the actual error message in the
#    status bar.

$x = 1;


#---- Syntax Coloring:
#    Komodo detects keywords and applies syntax coloring.  In the code
#    above, note how "echo" is a different color from "$bar1", which
#    is a different color from ""\n"".

#---- AutoCompletion and CallTips:

#    Komodo helps you code faster by presenting you with available
#    methods and properties of standard PHP functions. Komodo also
#    shows you the list of parameters you can pass to a function you
#    are calling.
#
#   For example, on a blank line below this comment block, slowly
#   re-enter the following code below the original:
#        print_r($bar1);
#   When you type the "i" in "print_r", Komodo lists functions
#   starting with "pri".  This list has several options in it, you
#   can move through the list with your up and down arrow keys. When
#   you press "Tab", Komodo completes the rest of the function name
#   for you. This is called AutoCompletion.  PHP AutoCompletion is supported
#   for classes, user functions, built in functions, and variables.
#
#   Completion is also available for user defined functions, classes and
#   variables contained within the current file and any included php file.
#   A couple examples include:
#       $foobar = new {completion appears}
#       $foobar->{completion appears}
#
#   When you type the open parenthesis "(", Komodo lists the
#   parameters for how to call print_r(). This is called
#   CallTips.

print_r($bar1);


#---- Debugging
#    You can use Komodo to debug your PHP scripts. For example, try
#    the following steps:
#
#    1. Set a breakpoint on the "class bar extends foo {" line: click
#       in the dark grey vertical bar on the left.
#
#    2. Start debugging: from the Debug menu, select Start.
#
#    3. Go to your breakpoint: on the Debug toolbar, click "Go".  (To
#       view and hide the toolbars, click the "grippies" on the left
#       of each toolbar.)
#
#    4. Step through the "class foo {": clicking any of the "Step"
#       buttons.  You can watch the program output on the Output pane
#       below and watch the variables in the Variables tab of the
#       Output pane.
#
#    5. Select a variable with your mouse and drag it to the Watched
#       Variables pane to watch it.

?>
<!--
See Komodo's online help for much more information on:
    - managing projects
    - keyboard shortcuts
    - XML support; and more
Just press <F1>, or select Help from the Help menu. 
-->
