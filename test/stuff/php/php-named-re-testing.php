<?php
// namedBlockRE testing for PHP 5
function test($a) {
}

function multiline($a,
					$b,
					$c) {
}

abstract class fail {
    abstract function f1();
    abstract public function f2();
    abstract protected function f3();
    abstract private function f4();
	abstract static function f5();
}

class fail {
	function f0() {}
/* test */	function fa() {}
	final function f1() {}
    abstract function f2();
    public function f3() {}
    abstract public function f4();
    protected function f5() {}
    abstract protected function f6();
    private function f7() {}
    abstract private function f8();
	static function f9() {}
	static public function f10() {}
	static private function f11() {}
    static protected function f12() {}
	static abstract function f13();
	static abstract public function f14();
	static abstract private function f15();
    static abstract protected function f16();
	static final function f17() {}
	static final public function f18() {}
	static final private function f19() {}
    static final protected function f20() {}
	function multiline($a,
						$b,
						$c) {
		echo "hello";
		echo "hello";
		echo "hello";
		echo "hello";
		echo "hello";
		echo "hello";
		echo "hello";
	}
}

interface if_a {
	abstract function f_a();
}

	

interface if_b {
	abstract function f_b();
}



interface if_c implements if_a, if_b {
	abstract function f_c();
}



interface if_d extends if_a implements if_b {
	abstract function f_d();
}



interface if_e {
	abstract function f_d();
}

interface if_f extends if_e implements if_a, if_b, if_c, if_d, if_e {
}



class base {
	function test($class) {
		echo "is_a(" . get_class($this) . ", $class) ". (is_a($this, $class) ? "yes\n" : "no\n");
	}
}

class class_base extends base {
	function f_a() {}
	function f_b() {}
	function f_c() {}
	function f_d() {}
	function f_e() {}
}

class class_a extends base implements if_a {
	function f_a() {}
	function f_b() {}
	function f_c() {}
	function f_d() {}
	function f_e() {}
}


class class_b extends base implements if_a, if_b {
	function f_a() {}
	function f_b() {}
	function f_c() {}
	function f_d() {}
	function f_e() {}
}

class class_e extends base implements if_a, if_b, if_c, if_d {
	function f_a() {}
	function f_b() {}
	function f_c() {}
	function f_d() {}
	function f_e() {}
}


?>