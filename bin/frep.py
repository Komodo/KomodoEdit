#!/usr/bin/env python
#
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
# Notes on logging levels and verbosity
# -------------------------------------
# 
# How loud this script is depends on these options (the last one given wins):
#     (none given)        default verbosity (logging.INFO level)
#     -v, --verbose       more verbose (logging.INFO-1 level)
#     -q, --quiet         less verbose (logging.WARN level)
#     -d, --debug         debugging output (logging.DEBUG level)
# 
# Full tracebacks on errors are shown on the command-line with -d|--debug.
# '-v|--verbose' is useful for some commands that have normal and more
# verbose output modes.
#
# TODOs for frep.py
# -----------------
# - EOL tests (should use universal newlines?) I'm okay with not
#   supporting mixed newlines.
# - unicode content tests
# - unicode path tests
# - 'frep foo bar.txt' for one input file only: output differs from grep
#   (prefixing with filename). Should frep copy grep here?

"""A Python script for doing find-and-replace stuff (a la grep/sed).
Primarily this exists to exercise the backend for Komodo's Find/Replace
functionality.
    
Example Usage:
  # grep-like
  frep foo *.pl            # grep for 'foo' in .pl files
  frep -r foo .            # grep for 'foo' in all text files (recursively)
  frep /f[ei]/i *.txt      # grep for 'fe', 'fi' (ignore case) in .txt files
  frep -l foo *.txt        # list .txt files matching 'foo'

  # sed-like
  frep s/foo/bar/ *.txt    # replace 'foo' with 'bar' in .txt files
  frep -u|--undo           # list replacements that can be undone
  frep -u ID               # undo replacement with id 'ID'

  # find-like
  frep . -i "foo*"         # list paths matching "foo*"
  frep . -i lang:Perl      # list Perl paths
  frep . -x lang:Python    # list all but Python paths

Undo notes:
  A replacement will log an id that can be used for subsequent undo.
  By default only the last 5 replacements are remembered. As well, the
  undo is far from perfect: if any of the changed files have been
  subsequently changed the undo might fail (or at least fail to undo
  that particular file).
"""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import (expanduser, join, basename, splitext, exists, dirname,
                     abspath, islink, normpath)
import time
import sys
import re
import traceback
import datetime
import optparse
import logging
from pprint import pprint, pformat
from glob import glob
import cPickle as pickle
import codecs
from hashlib import md5
import difflib


while islink(__file__):
    __file__ = normpath(join(dirname(__file__), os.readlink(__file__)))
ko_dir = dirname(dirname(abspath(__file__)))
try:
    import textinfo
except ImportError:
    sys.path.insert(0, join(ko_dir, "src", "python-sitelib"))
    import textinfo
try:
    import findlib2
    from findlib2 import Hit, StartJournal, SkipUnknownLangPath, \
        SkipLargeFilePath, ReplaceDiff, ReplaceHitGroup, Journal
except ImportError:
    sys.path.insert(0, join(ko_dir, "src", "find"))
    import findlib2
    from findlib2 import Hit, StartJournal, SkipUnknownLangPath, \
        SkipLargeFilePath, ReplaceDiff, ReplaceHitGroup, Journal



#---- exceptions

class FrepError(Exception):
    pass



#---- globals

log = logging.getLogger("frep")




#---- internal support stuff

# Recipe: query_custom_answers (1.0)
def _query_custom_answers(question, answers, default=None):
    """Ask a question via raw_input() and return the chosen answer.
    
    @param question {str} Printed on stdout before querying the user.
    @param answers {list} A list of acceptable string answers. Particular
        answers can include '&' before one of its letters to allow a
        single letter to indicate that answer. E.g., ["&yes", "&no",
        "&quit"]. All answer strings should be lowercase.
    @param default {str, optional} A default answer. If no default is
        given, then the user must provide an answer. With a default,
        just hitting <Enter> is sufficient to choose. 
    """
    prompt_bits = []
    answer_from_valid_choice = {
        # <valid-choice>: <answer-without-&>
    }
    clean_answers = []
    for answer in answers:
        if '&' in answer and not answer.index('&') == len(answer)-1:
            head, sep, tail = answer.partition('&')
            prompt_bits.append(head.lower()+tail.lower().capitalize())
            clean_answer = head+tail
            shortcut = tail[0].lower()
        else:
            prompt_bits.append(answer.lower())
            clean_answer = answer
            shortcut = None
        if default is not None and clean_answer.lower() == default.lower():
            prompt_bits[-1] += " (default)"
        answer_from_valid_choice[clean_answer.lower()] = clean_answer
        if shortcut:
            answer_from_valid_choice[shortcut] = clean_answer
        clean_answers.append(clean_answer.lower())

    # This is what it will look like:
    #   Frob nots the zids? [Yes (default), No, quit] _
    # Possible alternatives:
    #   Frob nots the zids -- Yes, No, quit? [y] _
    #   Frob nots the zids? [*Yes*, No, quit] _
    #   Frob nots the zids? [_Yes_, No, quit] _
    #   Frob nots the zids -- (y)es, (n)o, quit? [y] _
    prompt = " [%s] " % ", ".join(prompt_bits)
    leader = question + prompt
    if len(leader) + max(len(c) for c in answer_from_valid_choice) > 78:
        leader = question + '\n' + prompt.lstrip()
    leader = leader.lstrip()

    valid_choices = answer_from_valid_choice.keys()
    admonishment = "Please respond with '%s' or '%s'." \
                   % ("', '".join(clean_answer[:-1]), clean_answer[-1])

    while 1:
        sys.stdout.write(leader)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in answer_from_valid_choice:
            return answer_from_valid_choice[choice]
        else:
            sys.stdout.write(admonishment+"\n")

# Recipe: query_yes_no_quit (1.0)
def _query_yes_no_quit(question, default="yes"):
    """Ask a yes/no/quit question via raw_input() and return their answer.
    
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no", "quit" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes", "no" or "quit".
    """
    valid = {"yes":"yes",   "y":"yes",    "ye":"yes",
             "no":"no",     "n":"no",
             "quit":"quit", "qui":"quit", "qu":"quit", "q":"quit"}
    if default == None:
        prompt = " [y/n/q] "
    elif default == "yes":
        prompt = " [Y/n/q] "
    elif default == "no":
        prompt = " [y/N/q] "
    elif default == "quit":
        prompt = " [y/n/Q] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes', 'no' or 'quit'.\n")


class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

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

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
         do: level: ...
    Spacing. Lower case. Skip " level:" if INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


def _optparse_undo_arg(option, opt_str, value, parser):
    """Add optparse option callback that will gobble the next token if
    it looks like an arg to -u|--undo (8 letter chars, or "last").

    Based on recipe zero_or_one_arg (0.1).

    After parsing, 'options.undo' will be:
        None        option was not specified
        True        option was specified, no argument
        <string>    option was specified, the value is the argument string
    """
    value = True
    if parser.rargs:
        arg = parser.rargs[0]
        if arg == "last" or re.match("^[a-z]{8}$", arg):
            value = arg
            del parser.rargs[0]
    setattr(parser.values, option.dest, value)

def _chomp(s):
    return s.rstrip('\r\n')

def _safe_print(u):
    s = u.encode(sys.stdout.encoding or "utf-8", 'replace')
    print s

_bool_from_str = {
    "true": True, "True": True,
    "false": False, "False": False,
}
def _value_from_str(s):
    try:
        return int(s)
    except ValueError:
        if s in _bool_from_str:
            return _bool_from_str[s]
        else:
            return s


#---- mainline

def main_list_journals(opts):
    for mtime, id, summary in Journal.journals():
        dt = datetime.datetime.fromtimestamp(mtime)
        if log.isEnabledFor(logging.DEBUG):
            print "-- [%s, %s] %s" % (id, dt, summary)
            j = Journal.load(id)
            for record in j:
                print repr(record)
                for hit in record.rhits:
                    print "  %r" % hit
        else:
            print "%s  %s (at %s)" % (id, summary, dt)

def main_find(paths, includes, excludes, opts):
    for path in findlib2.find(paths, includes=includes, excludes=excludes):
        print path

def main_find_matching_files(regex, paths, includes, excludes, opts):
    for event in findlib2.grep(regex, paths, files_with_matches=True,
                               includes=includes, excludes=excludes):
        if isinstance(event, Hit):
            print event.path

def main_grep(regex, paths, includes, excludes, opts):
    grepper = findlib2.grep(regex, paths, includes=includes, 
                            excludes=excludes)
    for group in findlib2.grouped_by_path(grepper):
        if not isinstance(group[0], Hit):
            assert len(group) == 1
            log.debug(group[0])
            continue

        last_line_nums = None
        for hit in group:
            # Skip reporting a hit if it is on a line (or lines) that
            # has already been printed (a la grep).
            start, end = hit.line_num_range
            line_nums = set(range(start, end+1))
            if last_line_nums and line_nums.issubset(last_line_nums):
                continue
            last_line_nums = line_nums

            lines = list(hit.lines)
            if len(lines) > 1:
                if opts.show_line_number:
                    start, end = hit.line_num_range
                    _safe_print("%s:%d-%d:" % (hit.path, start+1, end+1))
                else:
                    _safe_print("%s:" % hit.path)
                for line in lines:
                    _safe_print("  " + _chomp(line))
            else:
                if opts.show_line_number:
                    _safe_print("%s:%d:%s" % (hit.path, hit.line_num_range[0]+1,
                                              _chomp(lines[0])))
                else:
                    _safe_print("%s:%s" % (hit.path, _chomp(lines[0])))


def main_replace(regex, repl, paths, includes, excludes, confirm, argv, opts):
    start_time = time.time()
    num_repls = 0
    dry_run_str = (opts.dry_run and " (dry-run)" or "")
    show_diffs = log.isEnabledFor(logging.INFO-1) # if '-v|--verbose'

    # The confirmation mode is one of:
    #   None        no confirmation of replacements
    #   "each"      confirm each path
    #   "all"       confirm all changes in one batch
    confirm_mode = None  # None or "each" or "all"
    if confirm:
        confirm_mode = "all"

    if confirm_mode == "all":
        rgroups = []
    journal = None
    try:
        for event in findlib2.replace(
                        regex, repl, paths,
                        first_on_line=opts.first_on_line,
                        includes=includes, excludes=excludes):
            if isinstance(event, StartJournal):
                journal = event.journal
                continue
            elif isinstance(event, SkipLargeFilePath):
                log.debug("Skip `%s' (file too large: %d).", event.path, event.size)
                continue
            elif isinstance(event, SkipUnknownLangPath):
                log.debug("Skip `%s' (don't know lang).", event.path)
                continue
            elif not isinstance(event, Hit):
                log.debug(event)
                continue
            assert isinstance(event, ReplaceHitGroup)

            if not confirm_mode:
                if show_diffs and event.diff:
                    _safe_print(event.diff)
                if not opts.dry_run:
                    event.commit()
                num_repls += event.length
                if not show_diffs:
                    s_str = (event.length > 1 and "s" or "")
                    log.info("%s: %s replacement%s%s", event.nicepath, 
                             event.length, s_str, dry_run_str)

            elif confirm_mode == "each":
                _safe_print(event.diff)
                answer = _query_yes_no_quit(
                    "Make replacements in `%s'?" % event.nicepath,
                    default="yes")
                if answer == "yes":
                    if not opts.dry_run:
                        event.commit()
                    num_repls += event.length
                    s_str = (event.length > 1 and "s" or "")
                    log.info("%s: %s replacement%s%s", event.nicepath, 
                             event.length, s_str, dry_run_str)
                elif answer == "no":
                    continue
                elif answer == "quit":
                    break

            elif confirm_mode == "all":
                s_str = (event.length > 1 and "s" or "")
                log.info("%s: %s replacement%s pending", event.nicepath, 
                         event.length, s_str)
                rgroups.append(event)

        if confirm_mode == "all" and rgroups:
            while True:
                print
                answer = _query_custom_answers(
                    "Make replacements (%d changes in %d files)?"
                        % (sum(g.length for g in rgroups), len(rgroups)),
                    ["&yes", "&no", "&diff"],
                    "yes")
                if answer == "yes":
                    log.info("Making replacements.")
                    for rgroup in rgroups:
                        #TODO: consider logging each replacement as it is made
                        if not opts.dry_run:
                            rgroup.commit()
                            num_repls += event.length
                    break
                elif answer == "no":
                    log.info("Skipping all replacements. No changes were made.")
                    break
                elif answer == "diff":
                    #TODO: pipe this to `less` if available
                    _safe_print('')
                    for rgroup in rgroups:
                        _safe_print(rgroup.diff)
    finally:
        if journal:
            journal.close()

    if num_repls:
        if log.isEnabledFor(logging.DEBUG):
            print
            s_str = (num_repls > 1 and "s" or "")
            if confirm_mode:
                log.debug("Made %d replacement%s%s.", num_repls,
                          s_str, dry_run_str)
            else:
                log.debug("Made %d replacement%s in %.2fs%s.", num_repls,
                          s_str, (time.time() - start_time), dry_run_str)
        if len(journal):
            log.info("Use `frep --undo %s' to undo.", journal.id)

def main_undo(opts):
    """Undo the given replacement."""
    dry_run_str = (opts.dry_run and " (dry-run)" or "")
    
    journal_id = opts.undo
    if journal_id == "last":
        for mtime, id, summary in Journal.journals():
            log.debug("last replace id is `%s'", id)
            journal_id = id
            break
        else:
            raise FrepError("there is no last replacement journal to undo")

    for rec in findlib2.undo_replace(journal_id, dry_run=opts.dry_run):
        if not isinstance(rec, findlib2.JournalReplaceRecord):
            log.debug(rec)
            continue
        s_str = (len(rec.rhits) > 1 and "s" or "")
        log.info("%s: undo %s replacement%s%s", rec.nicepath,
                 len(rec.rhits), s_str, dry_run_str)


def main(argv):
    if "--test" in argv:  # Quick self-test.
        import doctest
        nerrors, ntests = doctest.testmod()
        return nerrors

    usage = "usage: %prog PATTERN FILES..."
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output")
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.INFO-1,
        help="more verbose output")
    parser.add_option("-d", "--debug", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="verbose debugging output")
    parser.add_option("-w", "--word", action="store_true",
        help="restrict pattern match to whole words")
    parser.add_option("-l", "--list", action="store_true",
        help="list matching files (instead of the matches within them)")
#TODO: Need to handle grouping contiguous blocks for this. Use the
#      Provided hit.lines_with_context(n) for this.
#    parser.add_option("-C", "--context", type="int", metavar="NUM",
#         help="Print NUM lines of context.")
    parser.add_option("-r", "--recursive", action="store_true",
        help="find files recursively")
    parser.add_option("-n", dest="show_line_number", action="store_true",
        help="show line numbers for each hit")
    parser.add_option("-u", "--undo", metavar="[ID]", dest="undo",
        action="callback", callback=_optparse_undo_arg,
        help="Without an argument this will list replacements that can "
             "be undone (the last 5, most recent first). Specify a "
             "replacement id to undo it.")
    parser.add_option("-i", "--include", dest="includes",
        action="append", metavar="PATTERN",
        help="Path patterns to include. Alternatively, the argument can "
             "be of the form FIELD:VALUE to filter based on textinfo "
             "attributes of a file; for example, '-i lang:Python'.")
    parser.add_option("-x", "--exclude", dest="excludes",
        action="append", metavar="PATTERN",
        help="Path patterns to exclude. Alternatively, the argument can "
             "be of the form FIELD:VALUE to filter based on textinfo "
             "attributes of a file; for example, '-x encoding:ascii'.")
    parser.add_option("-f", "--force", dest="confirm", action="store_false",
        help="Make replacements without confirmation.")
    parser.add_option("-c", "--confirm", action="store_true",
        help="Confirm replacements before making any changes on disk "
             "(the default).")
    parser.add_option("--first-on-line", action="store_true",
        help="When replacing, only replace first instance on a line. (This "
             "is to support Vi's replacement without 'g' flag.)")
    parser.add_option("--dry-run", action="store_true",
        help="Do a dry-run replacement.")
    parser.set_defaults(log_level=logging.INFO, recursive=False,
        show_line_number=False, word=False, list=False, context=0,
        includes=[], excludes=[], confirm=True, first_on_line=False,
        dry_run=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)
    findlib2.log.setLevel(opts.log_level)

    # The -u|--undo actions don't use and args. Handle them first.
    if opts.undo is True:
        return main_list_journals(opts)
    elif opts.undo is not None:
        return main_undo(opts)

    # Process includes and excludes.
    path_includes = []
    textinfo_includes = []
    for i in opts.includes:
        if '=' in i:
            field, value = i.split('=', 1)
            textinfo_includes.append( (field, _value_from_str(value)) )
        elif ':' in i:
            field, value = i.split(':', 1)
            textinfo_includes.append( (field, _value_from_str(value)) )
        else:
            path_includes.append(i)
    path_excludes = []
    textinfo_excludes = []
    for i in opts.excludes:
        if '=' in i:
            field, value = i.split('=', 1)
            textinfo_excludes.append( (field, _value_from_str(value)) )
        elif ':' in i:
            field, value = i.split(':', 1)
            textinfo_excludes.append( (field, _value_from_str(value)) )
        else:
            path_excludes.append(i)

    # Validate and prepare the args.
    if len(args) < 1:
        log.error("incorrect number of arguments (see `%s --help')", argv[0])
        return 1
    elif len(args) == 1:
        # GNU find-like functionality uses one arg.
        action = "find"
        path_patterns = args
        recursive = True    # -r is implied for find functionality
    else:
        pattern_str, path_patterns = args[0], args[1:]
        regex, repl = findlib2.regex_info_from_str(
            pattern_str, word_match=opts.word, universal_newlines=True)
        action = (repl is None and "grep" or "replace")
        if opts.list:
            if action == "replace":
                raise FrepError("cannot use -l|--list for a replacement")
            action = "grep-list"
        recursive = opts.recursive

    # Dispatch to the appropriate action.
    paths = findlib2.paths_from_path_patterns(
                path_patterns, recursive=recursive,
                follow_symlinks=True,
                includes=path_includes, excludes=path_excludes)
    if log.isEnabledFor(logging.DEBUG):
        def log_it_first(paths):
            for path in paths:
                log.debug("considering '%s'...", path)
                yield path
        paths = log_it_first(paths)
    if action == "find":
        return main_find(paths, textinfo_includes, textinfo_excludes, opts)
    if action == "grep-list":
        return main_find_matching_files(regex, paths,
            textinfo_includes, textinfo_excludes, opts)
    elif action == "grep":
        return main_grep(regex, paths,
            textinfo_includes, textinfo_excludes, opts)
    elif action == "replace":
        return main_replace(regex, repl, paths,
            textinfo_includes, textinfo_excludes, opts.confirm,
            argv, opts)
    else:
        raise FrepError("unexpected action: %r" % action)


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
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            exc_str = str(exc_info[1])
            sep = ('\n' in exc_str and '\n' or ' ')
            where_str = ""
            tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
            in_str = (tb_func != "<module>"
                      and " in %s" % tb_func
                      or "")
            where_str = "%s(%s#%s%s)" % (sep, tb_path, tb_lineno, in_str)
            log.error("%s%s", exc_str, where_str)
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.INFO-1):
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)

