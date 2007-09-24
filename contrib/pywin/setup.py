#!/usr/bin/env python
#
# Setup script for the wnd library
# $Id$
#
# Usage: python setup.py install
#

from distutils.core import setup

try:
    # add download_url syntax to distutils
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None
except:
    pass

DESCRIPTION="Wnd - a Python-only gui framework for win32 systems."

LONG_DESCRIPTION="""\
This module wraps ctypes to interact with the Win32 API.
"""

setup(
    name="wnd",
    version="0.1.20",
    author="J&uumlaut;rgen Urner",
    author_email="jurner@users.sourceforge.net",
    url="http://sourceforge.net/projects/wnd/",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    download_url="http://sourceforge.net/project/showfiles.php?group_id=136533&package_id=151234",
    license="Python (MIT style)",
    packages=["wnd"],
    platforms="Python 2.5 and later.",
    classifiers=[
        "Development Status :: 1 - Early",
        "Operating System :: Windows",
        "Topic :: UI :: Windows",
        ]
    )
