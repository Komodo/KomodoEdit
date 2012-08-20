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

"""Shared stuff for ludditelib modules."""

__revision__ = "$Id$"
__version_info__ = (1, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

import re
import sys


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
    guid = None

    # On Windows, try pythoncom.CreateGuid().
    if sys.platform == "win32":
        try:
            import pythoncom
        except ImportError:
            pass
        else:
            guid = str(pythoncom.CreateGuid())

    # Try Ka-Ping Yee's uuid.py module.
    if guid is None:
        from ludditelib import uuid
        guid = str(uuid.uuid4())
    
    # Fallback to PyXPCOM.
    if guid is None:
        from xpcom import components
        uuidGenerator = components.classes["@mozilla.org/uuid-generator;1"] \
            .getService(components.interfaces.nsIUUIDGenerator)
        guid = str(uuidGenerator.generateUUID())

    return guid
