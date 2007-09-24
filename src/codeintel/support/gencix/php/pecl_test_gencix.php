<?php

// file created: Fri 10 Nov 2006 12:50:10 PM PST

/*
    * script for scanning pecl extensions
    * 
*/

require_once('./_phpgencix.inc');

if ($argc < 2 || in_array($argv[1], array('--help', '-help', '-h', '-?')) || !is_dir($argv[1])) {

    echo "Extract function summaries from sources of PHP\n\n";
    echo "Usage:      $argv[0] <source dir>\n";
    echo "            --help, -help, -h, -?      - to get this help\n";
    die;
}

$cwd = $argv[1];

$dh = opendir($cwd);

while(!false == ($file = readdir($dh))) {
    if(is_dir("$cwd/$file") && file_exists("$cwd/$file/config.m4")) {
        // probably a pecl extension
        //echo "$cwd/$file\n";
        $files = get_parsefiles("$cwd/$file");
        $peclScanner = new phpSrcParser($file, $files, false);
        $peclScanner->get_func_data();
        $cix_gen = new phpCixGenerator($peclScanner->func_data);
        $cix_gen->gen_cix($peclScanner->label);
    }
}

?>