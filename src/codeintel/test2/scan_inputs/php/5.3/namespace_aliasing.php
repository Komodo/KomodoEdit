<?php

namespace foo;

use My\Full\Classname as Another;

// this is the same as use 'My\Full\NSname as NSname'
use My\Full\NSname;

// importing a global class
// this is also the same as 'use \ArrayObject as ArrayObject'
use \ArrayObject;

$obj1 = new foo\Another; // instantiates object of class foo\Another
$obj2 = new Another; // instantiates object of class My\Full\Classname
$obj3 = new My\Full\Classname; // instantiates object of class My\Full\Classname
$obj4 = new \My\Full\Classname; // instantiates object of class My\Full\Classname
NSname\subns\func(); // calls function My\Full\NSname\subns\func
$a1 = new ArrayObject(array(1)); // instantiates object of class ArrayObject
// without the "use \ArrayObject" we would instantiate an object of class foo\ArrayObject
$a2 = new \ArrayObject(array(1)); // instantiates object of class ArrayObject

?>
