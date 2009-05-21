<?php

// Namespaces can also the brace syntax for defining the context.

namespace MyProject {
    const CONNECT_OK = 1;
    class Connection { /* ... */ }
    function connect() { /* ... */  }
}

namespace AnotherProject {
    const CONNECT_OK = 0;
    const CONNECT_FAIL = 1;
    class DBConnection { /* ... */ }
    function dbconnect() { /* ... */  }
}

namespace Multiple\Name\Spaces {
    const CONNECT_OK = 0;
    function connected() { /* ... */  }
}

?>
