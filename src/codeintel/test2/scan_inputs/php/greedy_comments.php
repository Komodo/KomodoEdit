<?php

# test.php

/*
This code is just a test to find a bug
*/


/*
* Function TestFunction
* @param PDO $model
* @param DOMDocument $node
* @return DOMDocument
*/
function TestFunction($model, $node) {
    echo $model." ".$node."\n";
}

// Ciler should ignore this comment.

// Line 1 of comment.
// Line 2 of comment.
function TestFunction1() {}

/*
 * test function 2
 */
function TestFunction2( /* model argument */
                      $model, $node) {
    echo $model." ".$node."\n";
}
