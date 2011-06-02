<!-- Use this sample script to explore some of Komodo's PHP features. -->

<?php

# Incremental search:
#   - Use 'Ctrl'+'I' ('Cmd'+'I' on OS X) to start an incremental search.
#   - Begin typing the characters you want to find. 
#   - As you type, the cursor moves to the first match after the current
#     cursor position. Press 'Esc' to cancel.

# Code Folding:
#   - Click the "+" and "-" symbols in the left margin.
#   - Use View|Fold to collapse or expand all block

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


# Background Syntax Checking:
#   - Syntax errors are underlined in red.
#   - Syntax warnings are underlined in green.
#   - Configure PHP Preferences to customize errors and warnings.
#   - Position the cursor over the underline to view the error or warning
#     message.

$x = 1;


# Syntax Coloring:
#   - Language elements are colored according to the Fonts and Colors
#     preference.

# AutoComplete:
#   - On a blank line below, enter "pri".
#   - When you type the "i", Komodo lists functions starting with "pri".
#   - Press 'Tab' to complete the function name.

# Abbreviations:
#   - Snippets from the Abbreviations folder in projects and toolboxes
#     can be inserted by typing the snippet name followed by
#     'Ctrl'+'T' ('Cmd'+'T' on OS X). The Samples folder in the
#     Toolbox contains some default abbreviation snippets to get you
#     started.
#    
#     Try this below with the 'class' PHP snippet. An empty class
#     block is created with "Tabstop" placeholders in handy places.

# CallTips
#   - On a blank line below, type "print_r", followed by an open parenthesis
#     "(".
#   - Komodo lists the parameters for calling print_r().

print_r($bar1);

# More:
#   - Press 'F1' to view the Komodo User Guide.
#   - Select Help|Tutorial|PHP Tutorial for more about Komodo and PHP.
?>

