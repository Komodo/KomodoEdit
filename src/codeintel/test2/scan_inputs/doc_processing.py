
"""
    This is the summary line for this module. So is this.
    
    And this is other:
        information
    that is not part of the summary.
"""

# Stress test the function docstring -> function signature/calltip doc
# processing. (Note: these are similar to the
# test_misc.py::test__parsePyFuncDoc() test cases.)

def read(s=None):
    "read([s]) -- Read s characters, or the rest of the string"
    pass

def b2a_qp(data, quotetabs=0, istext=1, header=0):
    """b2a_qp(data, quotetabs=0, istext=1, header=0) -> s; 
 Encode a string using quoted-printable encoding. 

On encoding, when istext is set, newlines are not encoded, and white 
space at end of lines is.  When istext is not set, \r and \n (CR/LF) are 
both encoded.  When quotetabs is set, space and tabs are encoded."""
    pass

def new_module(name):
    """new_module(name) -> module
    Create a new module.  Do not enter it in sys.modules.
    The module name must include the full package name, if any.
    """

def getaddrinfo(host, port, family=None, socktype=None, proto=None,
                flags=None):
    """getaddrinfo(host, port [, family, socktype, proto, flags])
    -> list of (family, socktype, proto, canonname, sockaddr)

    Resolve host and port into addrinfo struct.
    """

def MessageBeep(x=None):
    """MessageBeep(x) - call Windows MessageBeep(x). x defaults to MB_OK."""

def logreader(filename):
    """logreader(filename) --> log-iterator
    Create a log-reader for the timing information file."""
    pass

def resolution():
    """resolution() -> (performance-counter-ticks, update-frequency)"""
    pass

def gethostbyname(host):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    pass

def replace(str, old, new, maxsplit=None):
    """replace (str, old, new[, maxsplit]) -> string

    Return a copy of string str with all occurrences of substring
    old replaced by new. If the optional argument maxsplit is
    given, only the first maxsplit occurrences are replaced.
    """
    pass

def joinfields(list, sep=None):
    """join(list [,sep]) -> string
       joinfields(list [,sep]) -> string

    Return a string composed of the words in list, with
    intervening occurrences of sep.  Sep defaults to a single
    space.

    (join and joinfields are synonymous)
    """

join = joinfields

def QueryValueEx(key, value_name):
    """value,type_id = QueryValueEx(key, value_name) - Retrieves the type and data for a specified value name associated with an open registry key.

    key is an already open key, or any one of the predefined HKEY_* constants.
    value_name is a string indicating the value to query
    """
    pass

