#!/bin/sh
# Copyright (c) 2000-2006 ActiveState Software Inc.
#
# Komodo "AS Package" simple install script
#
# To install Komodo, run:
#   ./install.sh
# To see additional install options, run:
#   ./install.sh -h

dname=`dirname $0`
LD_LIBRARY_PATH="$dname/INSTALLDIR/lib/mozilla:"$LD_LIBRARY_PATH
export LD_LIBRARY_PATH
$dname/INSTALLDIR/lib/python/bin/python -E $dname/support/_install.py "$@"


