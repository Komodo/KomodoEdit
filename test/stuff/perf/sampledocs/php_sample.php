<!-- Copyright (c) 2000-2006 ActiveState Software Inc.
     See the file LICENSE.txt for licensing information.

     This sample PHP script shows you some of the features in Komodo
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
