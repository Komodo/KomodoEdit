<?php


class one extends PDO {
    public $obj;
    
    function __construct($xx) {
    parent::__construct('', 'user');
        // Ensure $this->obj is recognized as a DOMDocument.
        $this->obj = new DOMDocument('1.0', 'utf-8');
    }
    
    function foo() {
        $this->obj->blah();
    }
}

?>
