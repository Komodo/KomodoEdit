# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""This is a pretty trivial program that is not used anymore.

It survives mostly as an example of how to generate UUIDs from the 
command line, lest we forget...

Otherwise it can be deleted with impunity.
"""

import os
import sys

uuid=os.popen( "uuidgen" ).read().strip()
print sys.stdin.read().replace( "__NEW_UUID__", uuid )

