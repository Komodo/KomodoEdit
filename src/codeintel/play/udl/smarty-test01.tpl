<?php
 
/**
 * Project: Guestbook Sample Smarty Application
 * Author: Monte Ohrt <monte [AT] ohrt [DOT] com>
 * Date: March 14th, 2005
 * File: index.php
 * Version: 1.0
 */

// define our application directory  
define('GUESTBOOK_DIR', '/web/www.example.com/smarty/guestbook/');
// define smarty lib directory
define('SMARTY_DIR', '/usr/local/lib/php/Smarty/');
// include the setup script
include(GUESTBOOK_DIR . 'libs/guestbook_setup.php');

// create guestbook object
$guestbook =& new Guestbook;

// set the current action
$_action = isset($_REQUEST['action']) ? $_REQUEST['action'] : 'view';

switch($_action) {
    case 'add':
        // adding a guestbook entry
        $guestbook->displayForm();
        break;
    case 'submit':
        // submitting a guestbook entry
        $guestbook->mungeFormData($_POST);
        if($guestbook->isValidForm($_POST)) {
            $guestbook->addEntry($_POST);
            $guestbook->displayBook($guestbook->getEntries());
        } else {
            $guestbook->displayForm($_POST);
        }
        break;
    case 'view':
    default:
        // viewing the guestbook
        $guestbook->displayBook($guestbook->getEntries());        
        break;   
}

?>
<zip mo ="abc" ><sx se=abc/def/ghi ak="abc '">
moo<%= moose =%>    
</gawk>
</zip>  
{if}
The index.php file acts as the application controller. It handles all incoming browser requests and directs what actions to take. It will define our application directories, include the setup script, and direct an action depending on the action value from the $_REQUEST super-global. We will have three basic actions: add when a user wants to add an entry to the guestbook, submit when a user submits an entry, and view when the user displays the guestbook. The default action is view.
/web/www.example.com/smarty/guestbook/libs/guestbook_setup.php
{endif}
{foreach}
blah
{foreachelse}  
<?php

/**
 * Project: Guestbook Sample Smarty Application
 * Author: Monte Ohrt <monte [AT] ohrt [DOT] com>
 * Date: March 14th, 2005
 * File: guestbook_setup.php
 * Version: 1.0
 */

require(GUESTBOOK_DIR . 'libs/sql.lib.php');
require(GUESTBOOK_DIR . 'libs/guestbook.lib.php');
require(SMARTY_DIR . 'Smarty.class.php');
require('DB.php'); // PEAR DB

// database configuration
class GuestBook_SQL extends SQL {
    function GuestBook_SQL() {
        // dbtype://user:pass@host/dbname
        $dsn = "mysql://guestbook:foobar@localhost/GUESTBOOK";
        $this->connect($dsn) || die('could not connect to database');
    }       
}

// smarty configuration
class Guestbook_Smarty extends Smarty { 
    function Guestbook_Smarty() {
        $this->template_dir = GUESTBOOK_DIR . 'templates';
        $this->compile_dir = GUESTBOOK_DIR . 'templates_c';
        $this->config_dir = GUESTBOOK_DIR . 'configs';
        $this->cache_dir = GUESTBOOK_DIR . 'cache';
    }
}
      
?>
