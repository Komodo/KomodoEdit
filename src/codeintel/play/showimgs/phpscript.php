<?php

interface MyInterface {
   public function printHello();
}

abstract class AbstractClass {
   abstract public function abstractMethod($x, $y, $z = NULL);
}

class MyClass extends AbstractClass implements TestInterface {
    public $publicVar;
    protected $protectedVar;
    private $privateVar;
    static $staticVar;

    public function publicMethod() { }
    protected function protectedMethod() { }
    private function privateMethod() { }
    final function finalMethod() { }
}

?>