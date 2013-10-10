<?php

$someclass = array(0,1,2);
foreach($someclass as $variable) {
    echo $variable;
}

foreach (sum() as $key => $value) {
    echo $value * 2;
}

foreach (array(1, 2, 3, 4) as &$value2) {
    echo $value2 * 4;
}

foreach (array(1, 2, 3, 4) as &$value2) {
    echo $value2 * 4;
}

$dir = new DirectoryIterator($path);
foreach ($dir as $item) {
    // $item is a DirectoryIterator
}

?>
