<?php

// PHP references allow you to make two variables to refer to the same content.


// Basic reference assignment
$b = "string variable";
$a =& $b;


// Pass by reference
function foo(&$var)
{
   $var++;
}

$c=5; 
foo($c);


// Function returning a reference:
//   In this example, the property of the object returned by the find_var
//   function would be set, not the copy, as it would be without using
//   reference syntax.
function &find_var($param)
{
    return $found_var;
}

$foo =& find_var($bar);
$foo->x = 2;


// Class reference assignment?
//$bar =& new fooclass();


// Variable in a class using a reference.
// From bug: http://bugs.activestate.com/show_bug.cgi?id=73819
class Controller {
    function Controller()
    {	
        $this->load =& load_class('Loader');
    }
}

// Statically typed pass by reference
function sendNow(Customer &$customer) { }


?>
