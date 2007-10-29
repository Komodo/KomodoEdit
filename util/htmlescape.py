#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****
#
# Contributors:
#   Trent Mick (TrentM@ActiveState.com)

"""
    htmlescape - escape the given content for inclusion in HTML

    Usage:
        htmlescape [options...]

    General Options:
        -h, --help          dump this help and exit
        -V, --version       dump this script's version and exit
        -v, --verbose       verbose output

        -a, --attribute     also escape double-quote (") for inclusion in
                            an HTML/XML attribute

    Convert the given content (passed in on stdin) for inclusion in HTML
    and write it out to stdout. The '&', '<' and '>' characters are
    converted to their appropriate entity references.
    
    Examples:
        htmlescape.py < content.txt > content.htmlsnippet
"""

import os
import sys
import getopt
import cgi
import logging


#---- exceptions

class HTMLEscapeError(Exception):
    pass


#---- global data

_version_ = (0, 1, 0)
log = logging.getLogger("htmlescape")



#---- internal routines and classes
#TODO: prefix internal routines and classes with an underscore (as per
#      section "Naming Conventions" in http://www.python.org/peps/pep-0008.html)


#---- public module interface
#TODO: add an appropriate public module interface

def htmlescape(content, attribute=0):
    """Escape HTML entity references in the given content.
    
        "content" is the content the escape
        "attribute" (optional) is a boolean indicating if double-quote (")
            should be escaped as well. Default is false.
    """
    return cgi.escape(content, quote=attribute)


#---- mainline

def main(argv):
    logging.basicConfig()

    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "Vvha",
            ["version", "verbose", "help", "attribute"])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `htmlescape --help'.")
        return 1
    attribute = 0
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(part) for part in _version_])
            print "htmlescape %s" % ver
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-a", "--attribute"):
            attribute = 1

    if args:
        log.error("incorrect number of arguments: there should not be any")

    try:
        content = sys.stdin.read()
        escaped = htmlescape(content, attribute)
        sys.stdout.write(escaped)
    except HTMLEscapeError, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1
    except KeyboardInterrupt:
        log.debug("user abort")
        pass


if __name__ == "__main__":
    sys.exit( main(sys.argv) )

