<?php

namespace test;
define('MESSAGE', 'Message!');                              # Global namespace
define('test\HELLO', 'Hello hello!');                       # \test namespace
define(__NAMESPACE__ . '\GOODBYE', 'Goodbye cruel world!'); # \test namespace
define('\a\b\SOMETHING', 'This is sure something!');        # \a\b namespace
define('a\b\OTHER', 'Other thing!');                        # \a\b namespace

echo \MESSAGE . "\n";
echo \test\HELLO . "\n";
echo HELLO . "\n";
echo \test\GOODBYE . "\n";
echo \a\b\SOMETHING . "\n";
echo \a\b\OTHER . "\n";

?>
