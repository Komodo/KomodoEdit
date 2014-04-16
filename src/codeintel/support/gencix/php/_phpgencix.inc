<?php

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

require_once('./lib/JSON.php');

$json = new Services_JSON();

$c = 0;

$class_count = 0;

/*
    * get_parsefiles() scans srcpath to get files to scan
    * @param srcpath: path to php sources
    * @return array parsefiles: array of relative file paths
    * note: the only thing left over from the original script =)

*/
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

/* parser class for the c source files */

class phpSrcParser {

    public $root;
    public $label;
    public $files = array();
    public $func_data = array();
    public $files_cnt = 0;
    public $core;

    /*
        * __construct
        * @param root: the base directory of the source files
        * @param files: array of files to scan
        * @param: are we scanning core php or extensions? if true,
        *         we run _builtins() and _aliases() for more complete results
    */

    function __construct($root, $files = array(), $core=false) {
        $this->root = $root;
        $this->_label();
        $this->files = $files;
        $this->func_data['classes'] = array();
        $this->func_data['functions'] = array();
        $this->core = $core;
    }

    /*
        * get_func_data($ver) the main function
        * @param ver - the version of PHP being scanned
    */
    function get_func_data($ver=false) {
        foreach($this->files as $fpath) {
            $file = basename($fpath);
            $code = file_get_contents($fpath);
            
            $matches = array();
            preg_match_all('/{{{ proto ([\S\s]+?)\*\//', $code, $matches, PREG_SET_ORDER);
            //print_r($matches);
            
            /*$macro_matches = array();
            preg_match_all('/PHP_FUNCTION\(([\w\_]+?)\)/', $code, $macro_matches, PREG_SET_ORDER);*/

            if(count($matches) > 0) {
                $this->files_cnt++;
                foreach($matches as $match) {
                    
                    $tmp = $this->_parse($match, $fpath);
                    if (!is_array($tmp)) {
                        continue;
                    }
                    
                    if(array_key_exists('class', $tmp) && $tmp['name'] != '') { // this is a class method
                        if(!array_key_exists($tmp['class'],$this->func_data['classes'])) {
                            $this->func_data['classes'][$tmp['class']] = array('functions'=>array());
                        }
                        $class = $tmp['class'];
                        $tmp = $this->_remove_key('class', $tmp);
                        $this->func_data['classes'][$class]['functions'][$tmp['name']] = $tmp;
                    } else if($tmp['ilk'] == 'function' && $tmp['name'] != '') { // function
                        $this->func_data['functions'][$tmp['name']] = $tmp;
                    }
                }
            }
            
            /*foreach($macro_matches as $m) {
                //echo $m[1]."\n";
                if(!array_key_exists($m[1], $this->func_data['functions'])) {
                    $this->func_data['functions'][$m[1]] = array(
                        'name'=>$m[1],
                        'ilk'=>'function',
                        'signature'=>$m[1]."()",
                        'doc'=>'no doc available.',
                        'src'=>$file,
                        
                    );
                }
            }*/            
        }
        
        // only do this when scanning core php sources
        if($this->core && $ver) { 
            $this->_builtins($ver);
            $this->_aliases();
        }

        $this->_fixups($ver);

        //global $c; echo "grabbed back $c functions from the abyss???";
        return $this->_stats();
    }
    
    function _label() {
        $arr = explode('/', $this->root);
        if(substr($this->root, -1, 1) == '/') {
            array_pop($arr);
        }
        $this->label = array_pop($arr);
    }
    
    /*
        * _builtins() : a collection of hacks to work around 
    */
    
    function _builtins($ver) {
        
        $this->func_data['functions']['chown'] = array(
            'name'=>'chown', 
            'signature'=>'chown ( string filename, mixed user )',
            'doc'=>'Changes file owner',
            'ilk'=>'function',
        );
        
        $this->func_data['functions']['isset'] = array(
            'name'=>'isset', 
            'signature'=>'bool isset ( mixed var [, mixed var [, ...]] )',
            'doc'=>'Determine whether a variable is set',
            'ilk'=>'function',
        );
        
        $this->func_data['functions']['empty'] = array(
            'name'=>'empty', 
            'signature'=>'bool empty ( mixed $var )',
            'doc'=>'Determine whether a variable is considered to be empty.',
            'ilk'=>'function',
        );
        
        $this->func_data['functions']['unset'] = array(
            'name'=>'unset', 
            'signature'=>'void unset ( mixed $var [, mixed $var [, mixed $...]] )',
            'doc'=>'unset() destroys the specified variables.',
            'ilk'=>'function',
        );
        
        if(substr($ver, 0, 1) == '5') {
            $dom_classes = $this->dom_hack();
            foreach($dom_classes as $name=>$class) {
                $this->func_data['classes'][$name] = $class;    
            }
        }
        
        if(preg_match('/5\.[12]/', $ver)) {
            $this->func_data['functions']['lchown'] = array(
                'name'=>'lchown',
                'signature'=>'lchown ( string filename, mixed user )',
                'doc'=>"Attempts to change the owner of the symlink filename  to user user (specified by name or&#xa; number). Only the superuser may change the owner of a symlink.",
                'ilk'=>'function',
            );
        }
        
        $this->func_data['classes']['dir'] = array(
            'functions'=>array(
                'read'=>array(
                    'name'=>'read',
                    'signature'=>'read(void)',
                    'doc'=>'returns next item in the directory',
                    'ilk'=>'function',
                    'returns'=>'string',
                ),
                'rewind'=>array(
                    'name'=>'rewind',
                    'signature'=>'rewind(void)',
                    'doc'=>'rewinds the directory point one item',
                    'ilk'=>'function',
                ),
                'close'=>array(
                    'name'=>'close',
                    'signature'=>'close(void)',
                    'doc'=>'closes the directory object',
                    'ilk'=>'function',
                ),
            ),
            'variables'=>array(
                array('citdl'=>'string','name'=>'path'),
                array('citdl'=>'resource','name'=>'handle'),
            ),
        );

        $this->func_data['variables'] = array(
            array('name' => '_COOKIE' , 'citdl'=>'array', ),
            array('name' => '_ENV' , 'citdl'=>'array', ),
            array('name' => '_FILES' , 'citdl'=>'array', ),
            array('name' => '_GET' , 'citdl'=>'array', ),
            array('name' => '_POST' , 'citdl'=>'array', ),
            array('name' => '_REQUEST' , 'citdl'=>'array', ),
            array('name' => '_SERVER' , 'citdl'=>'array',
                  'variables' => array(
                    array('name' => "HTTP_HOST", 'citdl' => 'string', ),
                    array('name' => "HTTP_USER_AGENT", 'citdl' => 'string', ),
                    array('name' => "HTTP_ACCEPT", 'citdl' => 'string', ),
                    array('name' => "HTTP_ACCEPT_LANGUAGE", 'citdl' => 'string', ),
                    array('name' => "HTTP_ACCEPT_ENCODING", 'citdl' => 'string', ),
                    array('name' => "HTTP_ACCEPT_CHARSET", 'citdl' => 'string', ),
                    array('name' => "HTTP_KEEP_ALIVE", 'citdl' => 'string', ),
                    array('name' => "HTTP_CONNECTION", 'citdl' => 'string', ),
                    array('name' => "HTTP_COOKIE", 'citdl' => 'string', ),
                    array('name' => "HTTP_CACHE_CONTROL", 'citdl' => 'string', ),
                    array('name' => "PATH", 'citdl' => 'string', ),
                    array('name' => "SERVER_SIGNATURE", 'citdl' => 'string', ),
                    array('name' => "SERVER_SOFTWARE", 'citdl' => 'string', ),
                    array('name' => "SERVER_NAME", 'citdl' => 'string', ),
                    array('name' => "SERVER_ADDR", 'citdl' => 'string', ),
                    array('name' => "SERVER_PORT", 'citdl' => 'string', ),
                    array('name' => "REMOTE_ADDR", 'citdl' => 'string', ),
                    array('name' => "DOCUMENT_ROOT", 'citdl' => 'string', ),
                    array('name' => "SERVER_ADMIN", 'citdl' => 'string', ),
                    array('name' => "SCRIPT_FILENAME", 'citdl' => 'string', ),
                    array('name' => "REMOTE_PORT", 'citdl' => 'string', ),
                    array('name' => "GATEWAY_INTERFACE", 'citdl' => 'string', ),
                    array('name' => "SERVER_PROTOCOL", 'citdl' => 'string', ),
                    array('name' => "REQUEST_METHOD", 'citdl' => 'string', ),
                    array('name' => "QUERY_STRING", 'citdl' => 'string', ),
                    array('name' => "REQUEST_URI", 'citdl' => 'string', ),
                    array('name' => "SCRIPT_NAME", 'citdl' => 'string', ),
                    array('name' => "PHP_SELF", 'citdl' => 'string', ),
                    array('name' => "REQUEST_TIME", 'citdl' => 'string', ),
                    array('name' => "argv", 'citdl' => 'string', ),
                    array('name' => "argc", 'citdl' => 'string', ),
                  ),
            ),
            array('name' => '_SESSION' , 'citdl'=>'array', ),
            array('name' => 'HTTP_COOKIE_VARS' , 'citdl'=>'array', ),
            array('name' => 'HTTP_ENV_VARS' , 'citdl'=>'array', ),
            array('name' => 'HTTP_GET_VARS' , 'citdl'=>'array', ),
            array('name' => 'HTTP_POST_FILES' , 'citdl'=>'array', ),
            array('name' => 'HTTP_POST_VARS' , 'citdl'=>'array', ),
            array('name' => 'HTTP_SERVER_VARS' , 'citdl'=>'array', ),
            array('name' => 'HTTP_SESSION_VARS' , 'citdl'=>'array', ),
            array('name' => 'GLOBALS' , 'citdl'=>'array', ),
        );
        
        $magic_constants = array(
            array('name' => '__LINE__','citdl'=>'string', 'ilk' => 'constant'),
            array('name' => '__FILE__','citdl'=>'string', 'ilk' => 'constant'),
            array('name' => '__FUNCTION__', 'citdl'=>'string', 'ilk' => 'constant'),
            array('name' => '__CLASS__', 'citdl'=>'string', 'ilk' => 'constant'),
            array('name' => '__METHOD__', 'citdl'=>'string', 'ilk' => 'constant'),
        );
        
        $this->func_data['constants'] = array_merge(
          $this->_get_constants(),
          $magic_constants
        );

        $functions = array(
            array(
                'name' => 'include',
                'signature'=>'include(file_path)',
                'doc'=>'includes and evaluates the specified file, produces a warning on error.',
                'ilk' => 'function',
            ),
            array(
                'name' => 'require',
                'signature'=>'require(file_path)',
                'doc'=>'includes and evaluates the specified file, produces a Fatal Error on error.',
                'ilk' => 'function',
            ),
            array(
                'name' =>'include_once',
                'signature'=>'include_once(file_path)',
                'doc'=>'includes and evaluates the specified file if it hasn\'t been included before, produces a warning on error.',
                'ilk' => 'function',
            ),
            array(
                'name'=> 'require_once', 
                'signature'=>'require_once(file_path)',
                'doc'=>'includes and evaluates the specified file if it hasn\'t been included before, produces a Fatal Error on error.',
                'ilk' => 'function',
            ),
            array(
                'name'=> 'declare',
                'signature'=>'declare(directive)',
                'doc'=>'set execution directives for a block of code.',
                'ilk' => 'function',
            ),
            array(
                'name' => 'switch',
                'signature'=>'switch(var)',
                'doc'=>'evaluate a series of conditions on the same expression.',
                'ilk' => 'function',
            ),
            array(
                'name' => 'array',
                'signature'=>'array(<list>)',
                'doc'=>'create a PHP array.',
                'ilk' => 'function',
            ),
        );
        $tmp = $this->func_data['functions'];
        $this->func_data['functions'] = array_merge($functions, $tmp);
    }
    
    function _get_constants() {
      $out = array();
      $tpl = array('citdl'=>'int', 'ilk' => 'constant');
      $const_arr = get_defined_constants();
      foreach($const_arr as $name=>$val) {
        $tmp = $tpl;
        $tmp['name'] = $name;
        $tmp['citdl'] = gettype($val);
        $out[] = $tmp;
      }
      return $out;
    }

    
    /*
        * _aliases() :handle _FALIAS declarations
        * @param files = a keyed array of files to consider when looking for
        * aliases. The filename should be the array key.
        * 
    */
    
    function _aliases($files=false) {
        $_alias_files = array(
            'zend_builtin_functions.c'=>1,
            'sqlite.c'=>1,
            'posix.c'=>1,
            'basic_functions.c'=>1,
            'filestat.c'=>1,
            'session.c'=>1,
            'php_mysql.c'=>1,
        );
        
        $alias_files = array();
        
        $this->core ? $alias_files = $_alias_files : $alias_files = $files;
        
        $aliases = array();
        foreach($this->files as $file) {
            //echo $file."\n";
            if(array_key_exists(basename($file), $alias_files)) {
                $code = file_get_contents($file);
                $_aliases = array();
                $alias_rx = '_FALIAS\(([\S]+?)\,[\ \s]*?([\w]+)\,[\s]+[\w]+\)';
                preg_match_all("/$alias_rx/", $code, $_aliases, PREG_SET_ORDER);
                $aliases = array_merge($aliases, $_aliases);
            }
        }
        
        if(is_array($aliases) && count($aliases) > 0) {
            foreach($aliases as $a) {
                if($a[1] !== 'dir' && array_key_exists($a[2],$this->func_data['functions'])) {
                    $tmp = $this->func_data['functions'][$a[2]];
                    $asig = explode('(',$tmp['signature']);
                    $sig = $a[1].'('.$asig[1];
                    $alias_tmp = array(
                        'name'=>$a[1],
                        'signature'=>$sig,
                        "doc"=>$tmp['doc']."&#xa;".$a[1]." is an alias to ".$a[2],
                        'ilk'=>'function',
                    );       
                    if($tmp['returns']) {
                        $alias_tmp['returns'] = $tmp['returns'];
                    }
                    $this->func_data['functions'][$a[1]] = $alias_tmp;
                }
            }
        }
    }
    
    function _fixups($ver) {
        // Fixup lcfirst and ucfirst, bug 87426.
        $ucfirst = $this->func_data['functions']['ucfirst'];
        if (is_array($ucfirst) &&
            $ucfirst['doc'] == "Make a string's first character lowercase") {
            print "Fixing 'ucfirst' and 'lcfirst'\n";
            // Add lcfirst.
            $lcfirst = $ucfirst;
            $lcfirst['name'] = 'lcfirst';
            $lcfirst['signature'] = 'lcfirst(string str)';
            $this->func_data['functions']['lcfirst'] = $lcfirst;
            // Fixup ucfirst.
            $this->func_data['functions']['ucfirst'] = $ucfirst;
        }

        // Change PDO::prepare to return a PDOStatement - bug 103603.
        $pdoPrepare = &$this->func_data['classes']['PDO']['functions']['prepare'];
        if (is_array($pdoPrepare)) {
            print "Fixing 'PDO::prepare'\n";
            $pdoPrepare['returns'] = 'PDOStatement';
        }
    }

    function _remove_key($target, $arr) {
        $out = array();
        foreach($arr as $key=>$val) {
            if($key !== $target) {
                $out[$key] = $val;
            }
        }
        return $out;
    }
    
    
    function _parse($match, $file) {
        $tmp = false;
        // detect class membership.
        if(substr_count($match[1], '::') > 0) {
            $tmp = $this->_class_parser($match, $file);
        } else if(substr($match[0],0,3) !== 'DOM') { // plain ol' function
            $tmp = $this->_func_parser($match, $file);
        }
        return $tmp;
    }
    
    function _class_const_parser() {
      
    }

    function _class_parser($match, $file) {
        global $class_count; $class_count++;
        $rx = '([\S]+?)::(([\S]+?)\([\S\ ]*?\))([\S\s]+)';
        $c_matches = array();
        preg_match_all("/$rx/", $match[1], $c_matches, PREG_SET_ORDER);
        if (count($c_matches) == 0) {
            return NULL;
        }
        $c_matches = $c_matches[0];
        $out = array(
            'name'=>$this->_clean($c_matches[3]),
            'signature'=>$this->_clean($c_matches[2]),
            'class'=>$this->_clean($c_matches[1]),
            'doc'=>$this->_doc_clean($c_matches[4]),
            'ilk'=>'function',
            'src'=>basename($file),
        );
        
        // hackery to get the return type if there is one
        $tmp1 = explode('::', $match[1]);
        $tmp2 = explode(' ', trim($tmp1[0]));
        if(count($tmp2) > 1) {
            $tmp2 = array_reverse($tmp2);
            $ret = $tmp2[1];
            $out['returns'] = $this->_clean($ret);
        }
        return $out;
    
    }

    function _func_parser($match, $file) {        
        $rx = '([\w]+)[\s]*(([\w\_]+)\([\S\ ]+\))([\S\s]+)';
        $f_matches = array();
        preg_match_all("/$rx/", $match[1], $f_matches, PREG_SET_ORDER);
        
        if(is_array($f_matches) && (count($f_matches) > 0) && is_array($f_matches[0])) {
          $f_matches = $f_matches[0];
        }
        global $c;
        if(!is_array($f_matches) || (count($f_matches) == 0)) {
            //print_r($match);
            $rx2 = '([\w]+)\ (([\S]+?)\([\S\s]*?\))([\S\s]+)';
            $f_matches = array();
            preg_match_all("/$rx2/",$match[1], $f_matches, PREG_SET_ORDER);
            
            if (count($f_matches) > 0) {
                $f_matches = $f_matches[0]; //XXX hackery
                $c++;
            }
        }

        if(count($f_matches) == 0) {
            return NULL;
        }
        
        $out = array(
            'name'=>$this->_clean($f_matches[3]),
            'signature'=>$this->_clean($f_matches[2]),
            'returns'=>$this->_clean($f_matches[1]),
            'doc'=>$this->_doc_clean($f_matches[4]),
            'ilk'=>'function',
            'src'=>basename($file),
        );
        
        return $out;
    }
    
    /* output some stats for the current run */
    
    function _stats() {
        $out = "Scanned:\t$this->files_cnt files\n".
        "Got:\t\t".count($this->func_data['functions'])." global functions\n".
        "Got:\t\t".count($this->func_data['classes'])." global classes\n";
        return $out;
    }
    
    /* returns an xml-safe(r) string */

    function _clean($txt) {
        $txt = str_replace('*/', '', $txt);
        $txt = htmlentities(trim($txt));
        // immunize against int|false
        if(substr_count($txt, '|') > 0) {
            $tmp3 = explode('|', $txt);
            $txt = $tmp3[0];
        }
        return $txt;
    }
    
    function _doc_clean($txt) {
        $txt = $this->_clean($txt);
        $txt_arr = str_word_count($txt, 1);
        $txt = implode(' ',array_slice($txt_arr,0,20));
        $txt = str_replace("\n", '&#xA;', wordwrap($txt, 55));
        return $txt;
    }
    
    function dom_hack() {
        global $json;
        $domdata = $json->decode(file_get_contents('dom/dom.json'));
        return $this->_json_normalize($domdata);
    }
    
    function _json_normalize($data) {
        $out = array();
        if(is_object($data)) {
            $data = (array) $data;
        }
        foreach($data as $class=>$cldata) {
            $tmp = array('functions'=>array(), 'variables'=>array());
            // XXX re-factor!
            foreach($cldata->functions as $function) {
                $f = (array) $function;
                $f = $this->_remove_key('class', $f);
                $f['ilk'] = 'function';
                $tmp['functions'][] = $f;
                
            }
            
            if(isset($cldata->variables)) {
                foreach($cldata->variables as $var) {
                    $tmp['variables'][] = (array) $var;    
                }
            }
            $out[$class] = $tmp;
        }
        return $out;
    }
}

class phpCixGenerator {

    private $data = array();
    public $xml;

    function __construct($data = array()) {
        $this->data = $data;
    }
    
    function gen_cix($label, $meta, $output_dir) {
        if(!is_dir($output_dir)) { mkdir($output_dir); }
        $file = "$label.cix";
        $cix = $this->_cix_skel($file, $meta);
        $global = $cix->getElementsByTagName('scope');
        $global = $global->item(0);

        if($this->data['classes']) {
            foreach($this->data['classes'] as $name=>$class) {
                $c_attr = array('ilk'=>'class', 'name'=>$name);
    
                if($parent = get_parent_class($name)) { $c_attr['classrefs'] = $parent; }
                
                $classnode = $this->_new_domnode($cix, 'scope', $c_attr);
                foreach($class['functions'] as $method) {
                    $fnode = $this->_gen_scope($method, $cix);
                    $classnode->appendChild($fnode);
                }
                
                if(array_key_exists('variables', $class)) {
                    foreach($class['variables'] as $var) {
                        $vnode = $this->_new_domnode($cix, 'variable', $var);
                        $classnode->appendChild($vnode);
                    }
                }
                
                $global->appendChild($classnode);
            }
        }
        
        if($this->data['functions']) {
            foreach($this->data['functions'] as $function) {
                $fnode = $this->_gen_scope($function, $cix);
                $global->appendChild($fnode);
            }
        }
        
        if($this->data['constants']) {
            foreach($this->data['constants'] as $con) {
                $cnode = $this->_new_domnode($cix, 'variable', $con);
                $global->appendChild($cnode);
            }
        }
        
        if($this->data['variables']) {
            foreach($this->data['variables'] as $var) {
                //$fnode = $this->_gen_scope($var, $cix);
                $cvars = $var['variables'];
                unset($var['variables']);
                $vnode = $this->_new_domnode($cix, 'variable', $var);
                if($cvars) {
                    foreach($cvars as $cvar) {
                        $cnode = $this->_new_domnode($cix, 'variable', $cvar);
                        $vnode->appendChild($cnode);
                    }
                }
                $global->appendChild($vnode);
            }
        }
        
        if($str_cix = $cix->saveXML()) {
            $fh = fopen("./generated/$file", 'w');
            fwrite($fh, $str_cix);
            fclose($fh);
            echo "wrote $file, done.\n";
    
        } else {
            echo "error reading xml string from \$cix domNode!\n";
        }
        
    }
    
    function _gen_scope($arr, &$cix) {
        $fnode = $this->_new_domnode($cix, 'scope', $arr);
        return $fnode;
    }

    function _cix_skel($file, $attr=array()) {
        $xml = new DOMDocument('1.0', 'utf-8');
        $xml->formatOutput = true;
        $root = $xml->CreateElement("codeintel");
        
        $attr = array_merge(array('version'=>'2.0'), $attr);
        
        $root = $this->_add_attributes($xml,$root,$attr);

        $file_attr = array(
            'lang'=>'PHP',
            'mtime'=>time(),
            'path'=>$file,
        );

        $file = $this->_new_domnode($xml, 'file', $file_attr);
        $skel_array = array(
            'ilk'=>'blob',
            'lang'=>'PHP',
            'name'=>'*',
            'id'=>'global');
        
        $module = $this->_new_domnode($xml,'scope',$skel_array);
        $file->appendChild($module);
        $root->appendChild($file);
        $xml->appendChild($root);
        
        return $xml;
    }
    
    /*
        * @name _new_domnode
        * @param $top: top-level DOMDocument
        * @param $name: name of the new node
        * @param $attr: optional array of attributes
        * @param text: optional text in the node
        * @return DOMNode $node
    */

    function _new_domnode(&$top,$name,$attr=false,$text=false) {
        $node = $top->createElement($name);
        if($attr) {
            $node = $this->_add_attributes($top, $node, $attr);
        }
        if($text) {
            $tmp_txt = $top->createTextNode($this->_format_txt($text));
            $node->appendChild($tmp_txt);
        }
        return $node;
    }

    /*
       * @name _add_attributes
       * @param & $xml: top-level DOMDocument node passed in by reference
       * @param $node: the node to add attributes to
    */

    function _add_attributes(&$xml,$node,$attr) {
        if(is_array($attr) && count($attr) > 0) {
            foreach($attr as $key=>$val) {
                $tmp_attr = $xml->createAttribute($key);
                $tmp_attr->value = $val;
                $node->appendChild($tmp_attr);
            }
            return $node;
        } else {
            print_r($attr);    
        }   
    }
}

?>
