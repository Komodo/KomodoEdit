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
    rst2html - convert the given RST document to HTML

    Usage:
        rst2html [options...] [<input-rst-file>]

    General Options:
        -h, --help          dump this help and exit
        -V, --version       dump this script's version and exit
        -v, --verbose       verbose output

        -o <output file>    specify an output HTML file, by default the
                            basename of the given input file plus .html is
                            used
        -b, --browse        open the created HTML file in your browser

    The Python community has created light-weight document markup syntax
    called reStructuredText (RST for short) and tools to use it. One of the
    main points of this system is to convert an approachably edittable
    text document to HTML for publishing. However, this convertion step
    is a big pain because it involves a lot of digging in the relevant
    Python package: docutils.  This script makes that easier.

    If an input ReST file is not given then input is taken from stdin and
    dumped to stdout (unless -o is used).

    You can learn more about RST here:
        <http://docutils.sourceforge.net/docs/rst/quickstart.html>

    Examples:
        python rst2html.py foo.txt     # makes foo.html
"""
# Dev Notes:
# - Perhaps docutils-<version>/tools/html.py is a better candidate that this.
#   It provides a plethora of options (good and bad).

__revision__ = "$Id$"
__version_info__ = (0, 3, 0)
__version__ = '.'.join(map(str, __version_info__))


import os
import sys
import getopt
try:
    import logging
except ImportError:
    sys.stdout.write("""\
rst2html: error: This module requires the 'logging' Python package.
This package is a standard part of Python 2.3. You can either upgrade:
    http://www.activestate.com/Products/ActivePython/
or get the logging package for your version of Python here:
    http://www.red-dove.com/python_logging.html#download
""")
    sys.exit(1)

try:
    import docutils
    import docutils.utils
    import docutils.core
except ImportError:
    sys.stdout.write("""\
rst2html: error: This module requires the 'docutils' Python package.
You can get it here:
    http://sourceforge.net/project/showfiles.php?group_id=38414&package_id=30576
With more information here:
    http://docutils.sourceforge.net/
""")
    sys.exit(1)



#---- exceptions

class RST2HTMLError(Exception):
    pass


#---- global data

log = logging.getLogger("rst2html")



#---- internal routines and classes
#TODO: prefix internal routines and classes with an underscore (as per
#      section "Naming Conventions" in http://www.python.org/peps/pep-0008.html)
def _isSamePath(rstfile, htmlfile):
    nrstfile = os.path.normpath(os.path.normcase(rstfile))
    nhtmlfile = os.path.normpath(os.path.normcase(htmlfile))
    if nrstfile == nhtmlfile:
        return 1


def _url_from_local_path(local_path):
    # HACKy: This isn't super-robust.
    from os.path import abspath, normpath
    url = normpath(abspath(local_path))
    if sys.platform == "win32":
        url = "file:///" + url.replace('\\', '/')
    else:
        url = "file://" + url
    return url


#---- public module interface

def rstfile2html(rstfile, htmlfile=None):
    """Convert the given RST file to html.
    
        "rstfile" is a path to a RST-format file.
        "htmlfile" (optional) is a path to use for the output HTML file.
            If not specified it is generated from "rstfile": replace the
            extension with ".html"
    
    Raises ValueError if the "rstfile" and "htmlfile" are the same path,
    i.e. if the "rstfile" would be overwritten. Can also raise
    EnvironmentError or any of the docutils exceptions.
    
    Returns the path to the htmlfile created.
    """
    if htmlfile is None:
        htmlfile = os.path.splitext(rstfile)[0] + ".html"
    if _isSamePath(rstfile, htmlfile):
        raise ValueError("'%s' would be overwritten, aborting", rstfile)

    docutils.core.publish_file(source_path=rstfile,
                               destination_path=htmlfile,
                               reader_name='standalone',
                               parser_name='restructuredtext',
                               writer_name='html')
    
    # HACK in the CSS used for specs.tl.activestate.com.
    content = open(htmlfile, 'r').read()
    if "</head>" in content:
        css_link = '<link rel="stylesheet" type="text/css" '\
                   'href="http://specs.tl.activestate.com/style.css"/>'
        content = content.replace("</head>", "\n%s\n</head>" % css_link)
        open(htmlfile, 'w').write(content)
    else:
        log.warn("could not find '</head>' in '%s' at which to add CSS link",
                 htmlfile)

    return htmlfile


def rst2html(rst, htmlfile=None):
    """Convert the given RST to html.
    
        "rst" (string) is the ReST content.
        "htmlfile" (optional) is the target HTML file path. This is just
            used for determining relative paths, the file is not actually
            written by this method.
    
    Returns the generated HTML.
    """
    html = docutils.core.publish_string(
                source=rst,
                destination_path=htmlfile,
                reader_name='standalone',
                parser_name='restructuredtext',
                writer_name='html')

    return html


#---- mainline

def main(argv):
    logging.basicConfig()

    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "Vvho:b",
            ["version", "verbose", "help", "browse"])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `rst2html --help'.")
        return 1
    htmlfile = None
    browse = 0
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            print "rst2html %s" % __version__
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt == "-o":
            htmlfile = optarg
        elif opt in ("-b", "--browse"):
            browse = 1

    # Parse arguments
    if len(args) == 0:
        rststream = sys.stdin
        rstfile = None
    elif len(args) == 1:
        rststream = None
        rstfile = args[0]
    else:
        log.error("incorrect number of arguments: %s", args)
        log.error("Try `rst2html --help'.")

    try:
        if rstfile:
            htmlfile = rstfile2html(rstfile, htmlfile)
        elif rststream:
            rst = rststream.read()
            html = rst2html(rst, htmlfile)
            if htmlfile:
                fout = open(htmlfile, 'w')
                fout.write(html)
                fout.close()
            else:
                sys.stdout.write(html)
    except (RST2HTMLError, ValueError, EnvironmentError), ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1
    except KeyboardInterrupt:
        log.debug("user abort")
        pass
    else:
        if browse:
            import webbrowser
            url = _url_from_local_path(htmlfile)
            webbrowser.open_new(url)

if __name__ == "__main__":
    sys.exit( main(sys.argv) )

