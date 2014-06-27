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

r"""Make a Komodo changelog, given an svn revision range."""

__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import dirname, join, abspath, exists
import sys
import re
from pprint import pprint
import logging
import optparse



#---- exceptions

class Error(Exception):
    pass



#---- module API

def changelog_text(start_rev, end_rev):
    """Return a text-formatted changelog for the given revision range."""
    changelog = "Komodo Changelog (build %s)\n\n" % end_rev
    dir = dirname(dirname(abspath(__file__)))
    changelog += _capture_stdout(
        ["svn", "log", "-r", "%s:%s" % (end_rev, start_rev), dir])
    
    return changelog

def changelog_markdown(start_buildnum, end_buildnum):
    """Return a Markdown-formatted changelog for the given revision range."""
    import gitutils
    text = ("## Komodo Changelog (build %s, previous build %s)\n\n" %
            (end_buildnum, start_buildnum))
    dir = dirname(dirname(abspath(__file__)))
    start_rev = gitutils.revision_from_buildnum(start_buildnum)
    end_rev = gitutils.revision_from_buildnum(end_buildnum)
    num_revisions = end_buildnum - start_buildnum
    changelog = _capture_stdout(
        ["git", "log", "%s..%s" % (start_rev, end_rev), dir])
    # remove author emails
    changelog = re.sub(r"(Author:\s+.*?)(<.*?>)", r"\1", changelog)
    changelog = _markdown_br_fix(changelog)
    changelog = _markdown_hr_fix(changelog)
    changelog = _markdown_urlize(changelog)
    text += changelog
    return text

def changelog_html(start_buildnum, end_buildnum):
    """Return an HTML-formatted changelog for the given revision range."""
    sys.path.insert(0, join(dirname(dirname(abspath(__file__))),
                            "contrib", "smallstuff"))
    try:
        import markdown2
    finally:
        del sys.path[0]

    if isinstance(start_buildnum, (str, unicode)):
        start_buildnum = int(start_buildnum)
    if isinstance(end_buildnum, (str, unicode)):
        end_buildnum = int(end_buildnum)

    text = changelog_markdown(start_buildnum, end_buildnum)
    return markdown2.markdown(text,
        extras=["link-patterns"],
        link_patterns=[
            (re.compile("((komodo\s+)?bug\s*#?(?P<id>\d+))", re.I),
             r'http://bugs.activestate.com/show_bug.cgi?id=\g<id>'),
            (re.compile("((moz(illa)?\s+)?bug\s*#?(?P<id>\d+))", re.I),
             r'http://bugzilla.mozilla.org/show_bug.cgi?id=\g<id>'),
            (re.compile(r"\bcommit ([a-f0-9]{40})\b"),
             r'%s/commit/\1' % _git_base_url()),
        ])


#---- internal support stuff

def _git_base_url():
    stdout = _capture_stdout(['git', 'remote', "-v"])
    for line in stdout.splitlines(0):
        if line.startswith("origin"):
            root = line.split()[1].strip()
            root = root.replace("ssh://git@", "https://", 1)
            root = root.rsplit(".git", 1)[0]   # reomve ".git"
            return root
    # guess the root from filesystem
    if exists(abspath(join(dirname(__file__), "..", "src", "dbgp"))):
        return "https://github.com/Komodo/KomodoIDE"
    return "https://github.com/Komodo/KomodoEdit"

def _capture_stdout(argv, ignore_retval=False):
    import subprocess
    p = subprocess.Popen(argv, stdout=subprocess.PIPE,
                         universal_newlines=True)
    stdout = p.stdout.read()
    retval = p.wait()
    if retval and not ignore_retval:
        raise Error("error running '%s'" % ' '.join(argv))
    return stdout

_url_pat = re.compile("(?<!<)(https?://[^\s]+(?<!\.|>))")
def _markdown_urlize(text):
    return _url_pat.sub(r"<\1>", text)

def _markdown_hr_fix(text):
    needs_fix_re = re.compile(r'(?<!\n\n)^(?P<hr>-+)$', re.M)
    return needs_fix_re.sub('\n\g<hr>', text)

def _markdown_br_fix(text):
    """Ensure EOLs in SVN log checkin messages are changed to Markdown
    br tags, i.e. two spaces at end of line.
    """
    def br_sub(match):
        lines = match.group(1).splitlines(0)
        return '\n'.join([ln + '  ' for ln in lines])
    msg_re = re.compile(r'(?<= lines\n\n)(.*?)(?=\n^-----)', re.M|re.S)
    return msg_re.sub(br_sub, text)

# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)


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
    parser.add_option("--html", dest="format", action="store_const",
                      const="html",
                      help="product HTML output instead of text (the default)")
    parser.add_option("--markdown", dest="format", action="store_const",
                      const="markdown",
                      help="product Markdown output instead of text (the default)")
    parser.set_defaults(log_level=logging.INFO, format="text")
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    if len(args) != 2:
        raise Error("incorrect number of argments (see `%s --help')"
                    % sys.argv[0])
    start_rev, end_rev = args
    if opts.format == "text":
        print changelog_text(start_rev, end_rev)
    elif opts.format == "html":
        print changelog_html(start_rev, end_rev)
    elif opts.format == "markdown":
        print changelog_markdown(start_rev, end_rev)
    else:
        raise Error("unknown format: %r" % opts.format)


if __name__ == "__main__":
    _setup_logging()
    main(sys.argv)
