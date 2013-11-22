# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""A library for writing configure.py script for configuring project
builds (i.e. a Python-take on autoconf/configure.in).
"""

__revision__ = "$Id: __init__.py 199 2007-10-22 21:25:26Z trentm $"
__author__ = "Trent Mick"
__version_info__ = (0, 8, 2)
__version__ = '.'.join(map(str, __version_info__))

from configurelib.runner import main
from configurelib.common import ConfigureError
from configurelib.configvars import ConfigVar, Profile
