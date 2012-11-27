"""
This file is used by the build system to generate a pickled version of the
default prefs.xml file. We want a pickled version because it loads 10x faster
than the xml version - bug 96273.
"""

import os

from xpcom import _xpcom  # Necessary to initialize xpcom.
from xpcom import components
from xpcom.server import UnwrapObject

prefs = components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService).prefs
defaultPrefs = UnwrapObject(prefs)
# Walk up the chain until we find the top-most parent - as that's the default
# prefs.
while defaultPrefs.parent:
    defaultPrefs = defaultPrefs.parent

koDirSvc = components.classes["@activestate.com/koDirs;1"].\
    getService(components.interfaces.koIDirs)
filename = os.path.join(koDirSvc.supportDir, "prefs.xml")

# Serialize it.
defaultPrefs.serializeToFileFast(filename + "c")
