# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Utilities for writing and using Makefile.py's, a Python take on Makefile's.

Some of the inspiration for this tool comes from `rake` in the Ruby world,
although this was a personal project before I'd heard of rake.
"""

__author__ = "Trent Mick"
__version_info__ = (0, 7, 2)
__version__ = '.'.join(map(str, __version_info__))

from mklib.makefile import include
from mklib.tasks import Task, File, TaskGroup, Alias
from mklib.configuration import Configuration
