<?php

// Generic namespace definition (indentation is optional)

namespace MyGenericProject;
    const CONNECT_OK = 1;
    class Connection { /* ... */ }
    function connect() { /* ... */  }

namespace AnotherGenericProject;
    const CONNECT_OK = 0;
    const CONNECT_FAIL = 1;
    class DBConnection { /* ... */ }
    function dbconnect() { /* ... */  }

namespace Multiple\Name\Spaces;
    const CONNECT_OK = 0;
    function connected() { /* ... */  }

?>
