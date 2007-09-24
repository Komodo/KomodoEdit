<?php

require_once('./_phpgencix.inc');

if ($argc < 2 ||
    in_array($argv[1], array('--help', '-help', '-h', '-?')) ||
    !is_dir($argv[1])) {

    echo "Extract function summaries from sources of PHP\n\n";
    echo "Usage:      $argv[0] <php source dir>\n";
    echo "            --help, -help, -h, -?      - to get this help\n";
    die;
}

preg_match('/[\w]+-([45]\.[\d])/', $argv[1], $matches);

$php_ver = $matches[1];

echo "generating cix for PHP $php_ver\n";
echo "gathering files to scan...\n";

$files = get_parsefiles($argv[1]);
$files_obj = new phpSrcParser($argv[1], $files, true);
echo $files_obj->get_func_data($php_ver);

//print_r($files_obj->func_data['functions']);
$cix_generator = new phpCixGenerator($files_obj->func_data);

$meta = array("name"=>"PHP $php_ver", "description"=>"PHP $php_ver sources from PHP.net");
$output_dir = './generated';
$cix_generator->gen_cix("php-$php_ver", $meta, $output_dir);


?>
