<?php

class DB
{
    function &factory($type)
    {
        $classname = "DB_${type}";
    }

}

?>
