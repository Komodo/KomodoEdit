# Copyright (c) 2006 ActiveState Software Inc.

"""Shared stuff for ludditelib modules."""

__revision__ = "$Id$"
__version_info__ = (1, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import re


class LudditeError(Exception):
    pass



def is_source_tree_layout():
    """Return True iff this luddite is being run in the Komodo source
    tree layout.
    """
    from os.path import dirname, join, exists, abspath
    up_one_dir = dirname(dirname(abspath(__file__)))
    return exists(join(up_one_dir, "luddite.py"))
    


#---- some GUID support
# This stuff should be unnecessary when the deprecated "compile" and
# "package" commands are dropped.

def norm_guid(g):
    if not g.startswith("{"):
        g = "{"+g
    if not g.endswith("}"):
        g += "}"
    return g

guid_pat = re.compile(r"^{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
                        "-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}}?$")

def generate_guid():
    """Return a GUID/UUID in the typical
        {12345678-90ab-cdef-1234-567890abcdef}
    format (*with* the braces).
    """
    try:
        import uuid
    except ImportError:
        from ludditelib import uuid
    guid = str(uuid.uuid4())
    return guid
