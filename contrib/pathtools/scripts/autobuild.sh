#!/bin/sh
# autobuild.sh: Monitors the source directory for documentation file changes
#               and builds it continuously in the background.
#
# Public domain.
#

bin/python scripts/nosy.py .
