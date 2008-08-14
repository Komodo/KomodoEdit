# Copyright (c) 2000-2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components

_uuidGenerator = None
def generateUUID():
    global _uuidGenerator
    if _uuidGenerator is None:
        _uuidGenerator = components.classes["@mozilla.org/uuid-generator;1"].getService(components.interfaces.nsIUUIDGenerator)
    guid = _uuidGenerator.generateUUID()
    # must convert nsIDPtr to string first
    return str(guid)[1:-1] # strip off the {}'s
