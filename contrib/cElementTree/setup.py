#!/usr/bin/env python
#
# Setup script for the cElementTree accelerator
# $Id$
#
# Usage: python setup.py install
#

from distutils.core import setup, Extension
from distutils import sysconfig
import sys, os

# --------------------------------------------------------------------
# identification

NAME = "cElementTree"
VERSION = "1.0.5-20051216"
DESCRIPTION = "A fast C implementation of the ElementTree API."
AUTHOR = "Fredrik Lundh", "fredrik@pythonware.com"
HOMEPAGE = "http://www.effbot.org/zone/celementtree.htm"
DOWNLOAD = "http://effbot.org/downloads#celementtree"

# --------------------------------------------------------------------
# expat library

sources = [
    "expat/xmlparse.c",
    "expat/xmlrole.c",
    "expat/xmltok.c",
    ]

includes = [
    "expat",
    ]

defines = [
    ("XML_STATIC", None),
    ]

if sys.platform == "win32":
    # fake devstudio compilation to make sure winconfig.h is used
    defines.append(("COMPILED_FROM_DSP", None))
else:
    # determine suitable defines (based on Python's setup.py file)
    config_h = sysconfig.get_config_h_filename()
    config_h_vars = sysconfig.parse_config_h(open(config_h))
    for feature_macro in ["HAVE_MEMMOVE", "HAVE_BCOPY"]:
        if config_h_vars.has_key(feature_macro):
            defines.append((feature_macro, "1"))
    defines.append(("XML_NS", "1"))
    defines.append(("XML_DTD", "1"))
    if sys.byteorder == "little":
        defines.append(("BYTEORDER", "1234"))
    else:
        defines.append(("BYTEORDER", "4321"))
    defines.append(("XML_CONTEXT_BYTES", "1024"))


# --------------------------------------------------------------------
# distutils declarations

ext_modules = []

ext_modules.append(
    Extension(
        "cElementTree", ["cElementTree.c"] + sources,
        define_macros=defines,
        include_dirs=includes,
        )
    )

try:
    # add classifiers and download_url syntax to distutils
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None
except:
    pass

setup(
    author=AUTHOR[0],
    author_email=AUTHOR[1],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: XML",
        ],
    description=DESCRIPTION,
    download_url=DOWNLOAD,
    ext_modules = ext_modules,
    license="Python (MIT style)",
    long_description=DESCRIPTION,
    name=NAME,
    platforms="Python 2.1 and later.",
    url=HOMEPAGE,
    version=VERSION,
    )
