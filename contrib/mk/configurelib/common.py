# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Shared bits of configurelib."""

__all__ = ["log", "ConfigureError"]

import sys
import logging



#---- logging

log = logging.getLogger("configure")



#---- exceptions

class ConfigureError(Exception):
    pass



#---- utility stuff


