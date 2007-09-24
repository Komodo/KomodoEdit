#!/usr/bin/env python

"""
Simple desktop integration for Python. This module provides desktop environment
detection and resource opening support for a selection of common and
standardised desktop environments.

Copyright (C) 2005 Paul Boddie <paul@boddie.org.uk>

Licensed under the Academic Free License version 2.1 - see docs/LICENCE.txt.

--------

Desktop Detection
-----------------

To detect a specific desktop environment, use the get_desktop function.
To detect whether the desktop environment is standardised (according to the
proposed DESKTOP_LAUNCH standard), use the is_standard function.

Opening URLs
------------

To open a URL in the current desktop environment, relying on the automatic
detection of that environment, use the desktop.open function as follows:

desktop.open("http://www.python.org")

To override the detected desktop, specify the desktop parameter to the open
function as follows:

desktop.open("http://www.python.org", "KDE") # Insists on KDE
desktop.open("http://www.python.org", "GNOME") # Insists on GNOME

Without overriding using the desktop parameter, the open function will attempt
to use the "standard" desktop opening mechanism which is controlled by the
DESKTOP_LAUNCH environment variable as described below.

The DESKTOP_LAUNCH Environment Variable
---------------------------------------

The DESKTOP_LAUNCH environment variable must be shell-quoted where appropriate,
as shown in some of the following examples:

DESKTOP_LAUNCH="kdialog --msgbox"       Should present any opened URLs in
                                        their entirety in a KDE message box.
                                        (Command "kdialog" plus parameter.)
DESKTOP_LAUNCH="my\ opener"             Should run the "my opener" program to
                                        open URLs.
                                        (Command "my opener", no parameters.)
DESKTOP_LAUNCH="my\ opener --url"       Should run the "my opener" program to
                                        open URLs.
                                        (Command "my opener" plus parameter.)

Details of the DESKTOP_LAUNCH environment variable convention can be found here:
http://lists.freedesktop.org/archives/xdg/2004-August/004489.html
"""

__version__ = "0.2.1"

import os
import sys
import subprocess
import commands

def get_desktop():

    """
    Detect the current desktop environment, returning the name of the
    environment. If no environment could be detected, None is returned.
    """

    if os.environ.has_key("KDE_FULL_SESSION") or \
        os.environ.has_key("KDE_MULTIHEAD"):
        return "KDE"
    elif os.environ.has_key("GNOME_DESKTOP_SESSION_ID") or \
        os.environ.has_key("GNOME_KEYRING_SOCKET"):
        return "GNOME"
    elif sys.platform == "darwin":
        return "Mac OS X"
    elif hasattr(os, "startfile"):
        return "Windows"
    else:
        return None

def is_standard():

    """
    Return whether the current desktop supports standardised application
    launching.
    """

    return os.environ.has_key("DESKTOP_LAUNCH")

def _wait(pid, block):

    """
    Perform a blocking Wait for the given process identifier, 'pid', if the
    'block' flag is set to a true value. Return the process identifier.
    """

    if block:
        os.waitpid(pid, os.P_WAIT)
    return pid

def open(url, desktop=None, wait=0):

    """
    Open the 'url' in the current desktop's preferred file browser. If the
    optional 'desktop' parameter is specified then attempt to use that
    particular desktop environment's mechanisms to open the 'url' instead of
    guessing or detecting which environment is being used.

    Suggested values for 'desktop' are "standard", "KDE", "GNOME", "Mac OS X",
    "Windows" where "standard" employs a DESKTOP_LAUNCH environment variable to
    open the specified 'url'. DESKTOP_LAUNCH should be a command, possibly
    followed by arguments, and must have any special characters shell-escaped. 

    The process identifier of the "opener" (ie. viewer, editor, browser or
    program) associated with the 'url' is returned by this function. If the
    process identifier cannot be determined, None is returned.

    An optional 'wait' parameter is also available for advanced usage and, if
    'wait' is set to a true value, this function will wait for the launching
    mechanism to complete before returning (as opposed to immediately returning
    as is the default behaviour).
    """

    # Attempt to detect a desktop environment.

    detected = get_desktop()

    # Start with desktops whose existence can be easily tested.

    if (desktop is None or desktop == "standard") and is_standard():
        arg = "".join([os.environ["DESKTOP_LAUNCH"], commands.mkarg(url)])
        return _wait(subprocess.Popen(arg, shell=1).pid, wait)

    elif (desktop is None or desktop == "Windows") and detected == "Windows":
        # NOTE: This returns None in current implementations.
        return os.startfile(url)

    # Test for desktops where the overriding is not verified.

    elif (desktop or detected) == "KDE":
        cmd = ["kfmclient", "exec", url]

    elif (desktop or detected) == "GNOME":
        cmd = ["gnome-open", url]

    elif (desktop or detected) == "Mac OS X":
        cmd = ["open", url]

    # Finish with an error where no suitable desktop was identified.

    else:
        raise OSError, "Desktop not supported (neither DESKTOP_LAUNCH nor os.startfile could be used)"

    return _wait(subprocess.Popen(cmd).pid, wait)

# vim: tabstop=4 expandtab shiftwidth=4
