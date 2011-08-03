<?php

// Demonstrate PHP CILE parsing bug (see bug 34214).
$class = array(0,1,2);
foreach($class as $variable)
    echo $variable;

?>