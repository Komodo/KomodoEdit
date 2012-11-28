"""
This file is used by the build system to generate a pickled version of the
default prefs.xml file. We want a pickled version because it loads 10x faster
than the xml version - bug 96273.
"""

import os
import sys
from os.path import abspath, dirname, exists, join

# Remove the old picked version - if it exists.
modpath = abspath(__file__)
sys.path.append(dirname(dirname(dirname(modpath))))
from bkconfig import supportDir
filename = join(supportDir, "prefs.xmlc")
if exists(filename):
    os.remove(filename)

from xpcom import _xpcom  # Necessary to initialize xpcom.
from xpcom import components
from xpcom.server import UnwrapObject

# Load the Komodo preferences via xpcom.
prefs = components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService).prefs
defaultPrefs = UnwrapObject(prefs)

# Walk up the pref chain, the top-most parent is *always* the default prefs.
while defaultPrefs.parent:
    defaultPrefs = defaultPrefs.parent

# Serialize it.
defaultPrefs.serializeToFileFast(filename)
