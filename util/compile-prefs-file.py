#!python
# Compile a Komodo preferences file for a .xmlc file using the koIPrefs.idl
# API.

import sys
from xpcom import components

factory = components \
          .classes["@activestate.com/koPreferenceSetObjectFactory;1"] \
          .getService(components.interfaces.koIPreferenceSetObjectFactory)

for fileName in sys.argv[1:]:
    print "Compiling preference file: '%s'" % fileName
    ob = factory.deserializeFile(fileName)
    ob.serializeToFileFast(fileName+"c")

