<?php
/*  
  +----------------------------------------------------------------------+
  | PHP Version 4                                                        |
  +----------------------------------------------------------------------+
  | Copyright (c) 2005 The PHP Group                                     |
  +----------------------------------------------------------------------+
  | This source file is subject to version 3.0 of the PHP license,       |
  | that is bundled with this package in the file LICENSE, and is        |
  | available through the world-wide-web at the following url:           |
  | http://www.php.net/license/3_0.txt.                                  |
  | If you did not receive a copy of the PHP license and are unable to   |
  | obtain it through the world-wide-web, please send a note to          |
  | license@php.net so we can mail you a copy immediately.               |
  +----------------------------------------------------------------------+
  | Authors:    anatoly techtonik <techtonik@php.net>                    |
  +----------------------------------------------------------------------+
 
  $Id: genfuncsummary.php,v 1.4 2005/04/05 19:37:57 techtonik Exp $
*/


// Extract function summaries from sources of PHP and it's extensions
//
// Example of block looked in .c, .cpp, .h and .ec files
//
// /* {{{ proto string zend_version(void)
//   Get the version of the Zend Engine */
//

if ($argc != 2 ||
      in_array($argv[1], array('--help', '-help', '-h', '-?')) ||
      !is_dir($argv[1])) {

    echo "Extract function summaries from sources of PHP\n\n";
    echo "Usage:      $argv[0] <php source dir>\n";
    echo "            --help, -help, -h, -?      - to get this help\n";
    die;

}

// find all source files recursively - returns array with filenames
function get_parsefiles($srcpath) {
   $parsefiles = array();
   $srcdir = dir($srcpath);
   while (false !== ($file = $srcdir->read())) {
       $filepath = $srcpath."/".$file;
       if (is_dir($filepath) && $file !== "." && $file !== "..") {
           $parsefiles = array_merge($parsefiles, get_parsefiles($filepath));
           continue;
       }
       if (preg_match('/\.(c|cpp|h|ec)$/i', $file)) {
           $parsefiles[] = $filepath;
       }
   }
   $srcdir->close();
   return $parsefiles;
}

$parsefiles = get_parsefiles($argv[1]);
sort($parsefiles);

// check for PHP3 sources
if (is_file($argv[1]."/language-scanner.lex")) {  // only in PHP3 sources
    $parsefiles[] = $argv[1]."/language-scanner.lex";
}

// make unified directory separator - /
if (DIRECTORY_SEPARATOR == '\\') {
    $parsefiles = array_map( create_function('$a', 'return str_replace("\\\\", "/", $a);'), $parsefiles );
}

// proto regex
$proto_regex  = "`^\s*/\*\s+\{{3}\s+proto\s+(\S+)\s+?(.+)$(.+)\*/`msU";
// matches[1] - return value from function prototype
// matches[2] - rest of prototype starting with function name to sort by
// matches[3] - description with newlines to be stripped and identation to be added

// prototype blocks
foreach ($parsefiles as $key => $file) {
    $file_contents = file_get_contents($file);
    $m = preg_match_all($proto_regex, $file_contents, $matches);
    if ($m) {
        // output source file name
        #echo preg_replace("|^[./]+|", "# ", $file)."\n";
        $preturn = array();
	$prest = array();
        $pdesc = array();
        foreach($matches[1] as $mk => $mv) {
           $preturn[] = $matches[1][$mk];
           $prest[]   = $matches[2][$mk];
           $pdesc[]   = "     " . preg_replace("`\s+`msU", " ", trim($matches[3][$mk]));
        }
        array_multisort($prest, $preturn, $pdesc);
        foreach($preturn as $k => $v) {
            echo $preturn[$k] . " " . $prest[$k] . " \n" . $pdesc[$k] . "  \n";
        }
    } else {
        unset($parsefiles[$key]);
    }
}


/****[ Original algorithm of genfunclist.sh ] *****/

# | Authors:    Gabor Hoitsy <goba@php.net>                              |

/* 

for i in `find $1 -name "*.[ch]" -print -o -name "*.ec" -print | xargs egrep -li "\{\{\{ proto" | sort` ; do
 echo $i | sed -e "s|$1|# php-src|"
 $awkprog -f $awkscript < $i | sort +1 | $awkprog -F "---" '{ print $1; print $2; }' | sed -e's/^[[:space:]]+//' -e's/[[:space:]]+/     /'
done
if test -f $1/language-scanner.lex # only in PHP3
then
  $awkprog -f funcsummary.awk < $1/language-scanner.lex | sort +1 | $awkprog -F "---" '{ print $1; print $2; }'
fi

*/

/****[ Original funcsummary.awk ] *****/
//
///^[[:space:]]*\/\*[[:space:]]*\{\{\{[[:space:]]*proto/ { 
//	split($0,proto,"proto[[:space:]]+|\\*/[[:space:]]*$");
//	parse=1; 
//	same=1;
//	lc=0;
//}
///\*\// {
//	if(parse) {
//		lines="";
//		for(i=0;i<lc;i++) {
//			lines = sprintf("%s %s ",lines,line[i]);
//		}
//		if(!same) {
//			split($0,temp,"\\*/[[:space:]]*$");
//			lines = sprintf("%s %s ",lines,temp[1]);
//		}
//		printf("%s --- %s\n",proto[2],lines);
//		parse=0;
//	}
//	next;
//}
//{	
//	if(parse && !same) { 
//		split($0,temp,"\\*/[[:space:]]*$");
//		line[lc++]=temp[1];
//		
//	} 
//	same=0;
//}


?>
