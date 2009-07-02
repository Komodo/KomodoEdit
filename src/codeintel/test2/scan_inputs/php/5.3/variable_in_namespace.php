<?php

namespace test {
    function inner() {
        # 'foo' is still a local variable of the function.
        $foo = 1;
    }
    # 'test_x' gets added to the global variables, not to the namespace!
    $test_x = 1;
}

?>
