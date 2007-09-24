<?php
require 'soap.php';

/**
  * simpleFunc
  *
  * an example doc string in php
  **/
function simpleFunc($ttt) {
}

class SimpleClass {
    var $x;
    function foo() {
    }
}

class SimpleClass2 extends SimpleClass {
    var $x;
   /*
    * foo
    *
    * since php functions can retrieve arguments dynamically, base arguments
    * could appear in the comments, but not in the code
    * 
    * @param string $x
    * @param integer $y
    * @param MyClass $z
    *
    * @return string
    *
   */
    function foo() {
        $args = func_get_args();
        parent::foo();
    }
}

interface TestInterface {
   public
   function printHello();
}

interface TestMethodsInterface {
   public function printHello();
}

/**
  * AbstractClass
  *
  * an example doc string in php
  **/
abstract class AbstractClass {
   abstract
   public function test($x, $y, $z = NULL);
   /*
    *
    * @param string $x
    * @param integer $y
    * @param MyClass $z
    *
    * @return string
    *
   */
   abstract public function test2($x, $y, $z = NULL);
}

class MyClass extends AbstractClass
    implements TestInterface, TestMethodsInterface {

    var $oldStyleVar;
    public $newStyleVar;
    private $Hello = "Hello, World!\n";
    protected $Bar = "Hello, Foo!\n";
    protected $Foo = "Hello, Bar!\n";
    static $my_static = 5;

    function __construct() {
        print "In BaseClass constructor\n";
    }
   
    function __destruct() {
        print "Destroying " . $this->name . "\n";
    }

    public function printHello() {
        print "MyClass::printHello() " . $this->Hello;
        print "MyClass::printHello() " . $this->Bar;
        print "MyClass::printHello() " . $this->Foo;
    }

    public function test($x,
                         $y,
                         $z = NULL) {
    }
    
    public function test2($x, $y, $z = NULL) {
    }

    private
    function aPrivateMethod() {
        echo "Foo::aPrivateMethod() called.\n";
    }

    protected
    function aProtectedMethod() {
        echo "Foo::aProtectedMethod() called.\n";
        $this->aPrivateMethod();
    }

    final function bar() {
        // ...
    }
}

final class MyClass2 extends MyClass {
    protected $Foo;
           
    function __construct() {
        parent::__construct();
        print "In SubClass constructor\n";
    }
    
    public function printHello() {
        MyClass::printHello();                          /* Should print */
        print "MyClass2::printHello() " . $this->Hello; /* Shouldn't print out anything */
        print "MyClass2::printHello() " . $this->Bar;  /* Shouldn't print (not declared)*/
        print "MyClass2::printHello() " . $this->Foo;  /* Should print */
    }
    
    public function aPublicMethod() {
        echo "Bar::aPublicMethod() called.\n";
        $this->aProtectedMethod();
    }
}

$obj = new MyClass();
print $obj->Hello;  /* Shouldn't print out anything */
print $obj->Bar;    /* Shouldn't print out anything */
print $obj->Foo;    /* Shouldn't print out anything */
$obj->printHello(); /* Should print */

$obj = new MyClass2();
print $obj->Hello;  /* Shouldn't print out anything */
print $obj->Bar;    /* Shouldn't print out anything */
print $obj->Foo;    /* Shouldn't print out anything */
$obj->printHello();


?>