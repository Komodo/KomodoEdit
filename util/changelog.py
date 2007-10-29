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

r"""Make a Komodo changelog, given a p4 revision range."""

__revision__ = "$Id$"
__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import re
from pprint import pprint
import logging
import optparse



#---- exceptions

class Error(Exception):
    pass



#---- globals

p4_tree = "//depot/main/Apps/Komodo-devel"



#---- module API

def changelog_info(start_rev, end_rev):
    """Gather changelog info for the given revision range."""
    import p4lib
    p4 = p4lib.P4()
    changes = p4.changes("%s/...@%s,%s" % (p4_tree, start_rev, end_rev),
                         longOutput=True)
    return changes

def changelog_text(start_rev, end_rev):
    """Return a text-formatted changelog for the given revision range."""
    info = changelog_info(start_rev, end_rev)
    
    lines = ["Komodo Changelog (build %s)" % end_rev]
    lines.append("=" * len(lines[-1]))
    
    for change in info:
        lines += ["",
                  "Change %(change)s by %(user)s on %(date)s" % change,
                  ""]
        lines += ["    " + s for s in change["description"].splitlines(0)]
    
    return '\n'.join(lines)


def changelog_markdown(start_rev, end_rev):
    """Return a Markdown-formatted changelog for the given revision range."""
    info = changelog_info(start_rev, end_rev)
    lines = ["## Komodo Changelog (build %s)" % end_rev]
    for change in info:
        lines += ["",
                  "### [Change %(change)s](http://p4.activestate.com/p4db/changeView.cgi?CH=%(change)s) by %(user)s on %(date)s" % change,
                  ""]
        lines += ["> %s<br/>" % _bugzilla_urlize(_markdown_urlize(s))
                  for s in change["description"].splitlines(0)]
    return '\n'.join(lines)


def changelog_html(start_rev, end_rev, full_html=False):
    """Return an HTML-formatted changelog for the given revision range.
    
    @param full_html {boolean} Whether to include enclosing HTML header
        and footer content. By default false.
    """
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        import markdown
    finally:
        del sys.path[0]
    text = changelog_markdown(start_rev, end_rev)
    return markdown.markdown(text)


#---- internal support stuff

_url_pat = re.compile("(https?://[^\s]+(?<!\.|>))")
def _markdown_urlize(s):
    return _url_pat.sub(r"[\1](\1)", s)

_bug_pat = re.compile("((?P<moz>moz(illa)? )?bug #?(?P<num>\d+))", re.I)
def _bugzilla_urlize(s):
    def repl(m):
        if m.group("moz"):
            return "[%s](http://bugs.mozilla.org/show_bug.cgi?id=%s)" \
                   % (m.group(0), m.group("num"))
        else:
            return "[%s](http://bugs.activestate.com/show_bug.cgi?id=%s)" \
                   % (m.group(0), m.group("num"))
    return _bug_pat.sub(repl, s)



#---- mainline

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    """Setup logging to the console (controlled by -v|-q options)."""
    global log

    log = logging.getLogger("changelog")
    log.setLevel(logging.INFO)

    # Logging to console.
    console = logging.StreamHandler()
    defaultFmt = "%(name)s: %(lowerlevelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    console.setFormatter(fmtr)
    logging.root.addHandler(console)



def main(argv):
    usage = "usage: %prog [OPTIONS...] STARTREV ENDREV"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="changelog", usage=usage,
                                   version=version, description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("--html", action="store_true",
                      help="product HTML output instead of text (the default)")
    parser.set_defaults(log_level=logging.INFO, html=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    if len(args) != 2:
        raise Error("incorrect number of argments (see `%s --help')"
                    % sys.argv[0])
    start_rev, end_rev = args
    if opts.html:
        print changelog_html(start_rev, end_rev)
    else:
        print changelog_text(start_rev, end_rev)


if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.level <= logging.DEBUG:
            import traceback
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)
