#!python
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

"""
A library of find and replace utilities for Komodo.

Public Interface:
    find(), findall(), replace(), replaceall()

See usage() below for information on the command line interface or
just do this:
    python findlib.py --help

See the test() doc string at the bottom for illustrative usage tests.
"""

import os, sys, re

#---- globals

verbosity = 0     # <0 == quiet, 0 == normal, >0 == verbose
out = sys.stdout



#---- exceptions raise by this module

class FindError(Exception):
    pass



#---- support routines

def _GetReFlags(pattern, **options):
    flags = 0
    if options.has_key("case"):
        case = options["case"]
        if case == "insensitive":
            flags |= re.IGNORECASE
        elif case == "sensitive":
            pass
        elif case == "smart":
            # Smart case-sensitivity is modelled after the options in Emacs
            # where by a search is case-insensitive if the seach string is
            # all lowercase. I.e. if the search string has an case
            # information then the implication is that a case-sensitive
            # search is desired.
            if pattern == pattern.lower():
                flags |= re.IGNORECASE
            else:
                pass
        else:
            raise FindError("unrecognized case-sensitivity "\
                            "option: '%s'" % case)
    else:
        flags |= re.IGNORECASE
    flags |= re.MULTILINE
    return flags


def _MassageSearchToken(pattern, **options):
    # modify the search token as required for the search type
    if options.has_key("patternType"):
        patternType = options["patternType"]
    else:
        patternType = "simple"

    if patternType == "simple":
        pattern = re.escape(pattern)
    elif patternType == "wildcard":
        pattern = re.escape(pattern)
        pattern = pattern.replace("\\?", "\w")
        pattern = pattern.replace("\\*", "\w*")
    elif patternType == "regex-python":
        pass
    else:
        raise FindError("unrecognized find type: '%s'" %\
                        options["patternType"])
    
    if options.has_key("matchWord") and options["matchWord"]:
        # Bug 33698: "Match whole word" doesn't work as expected
        # Before this the transformation was "\bPATTERN\b" where \b means:
        #   matches a boundary between a word char and a non-word char
        # However what is really wanted (and what VS.NET does) is to match
        # if there is NOT a word character to either immediate side of the
        # pattern.
        pattern = r"(?<!\w)" + pattern + r"(?!\w)"

    return pattern


def _Find(text, start, end, pattern, flags):
    """Return the match result (a Match object) from doing this search."""
    theRegex = re.compile(pattern, flags)
    return theRegex.search(text, start, end)


def _FindAll(text, start, end, pattern, flags):
    """Return the list of match results (a list of Match object) from
    doing this search.
    """
    theRegex = re.compile(pattern, flags)
    results = []
    while 1:
        match = theRegex.search(text, start, end)
        if match:
            # If this match matched no characters (e.g. possible with
            # patterns like "^", "$", "(...)*"), then advance the start
            # offset by one character to ensure that this match does not
            # happen again (because that would cause an infinite loop.
            # XXX I *think* this is a valid fix, i.e. the result is what the
            #     user expects.
            results.append(match)
            if match.start() - match.end() == 0:
                start = match.end() + 1
                if start > end:
                    break
            else:
                start = match.end()
        else:
            break
    return results


def _CountAll(text, start, end, pattern, flags):
    theRegex = re.compile(pattern, flags)
    allhits = theRegex.findall(text[start:end])
    return len(allhits)

def _ReplaceAll(text, start, end, pattern, replacement, flags):
    theRegex = re.compile(pattern, flags)
    return text[:start] + theRegex.sub(replacement, text[start:end]) + text[end:]



#---- public functionality

class FindResult:
    def __init__(self, start, end, value):
        # zero-based indeces into the search text demarking the find result
        self.start = start
        self.end = end
        # the string found (not sure if this is really necessary, but should
        # be useful for debugging)
        self.value = value
    def __str__(self):
        return "%d-%d: found '%s'" %\
               (self.start, self.end, self.value)


class ReplaceResult:
    def __init__(self, start, end, value, replacement):
        # zero-based indeces into the search text demarking the find result
        self.start = start
        self.end = end
        # the string found (not sure if this is really necessary, but should
        # be useful for debugging)
        self.value = value
        # the string with which to replace the value
        self.replacement = replacement

    def __str__(self):
        return "%d-%d: replace '%s' with '%s'" %\
               (self.start, self.end, self.value, self.replacement)


def find(text, pattern, startOffset=0, **options):
    """Return the result of searching for the first "pattern" in "text".
    The return value is either a FindResult instance or None.
    The options dictionary may have to following values:
        patternType: simple* | wildcard | regex-python
        matchWord: 0* | 1
        searchBackward: 0* | 1
        case: insensitive* | sensitive | smart
    (*) indicates the default
    """
    global verbosity
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)
    searchBackward = options.has_key("searchBackward") and options["searchBackward"]
    
    if verbosity > 0:
        print "find: text=%r pattern=%r startOffset=%d flags=%s"\
              % (text, pattern, startOffset, flags)
    if not searchBackward:
        match = _Find(text, startOffset, len(text), pattern, flags)
    else:
        # to search backwards, find all the result from the start up the
        # the desired starting position and take the last one
        matches = _FindAll(text, 0, startOffset, pattern, flags)
        if matches:
            match = matches[-1]
        else:
            match = None

    if match:
        result = FindResult(start=match.start(), end=match.end(),
                            value=match.group())
    else:
        result = None
    return result


def findall(text, pattern, **options):
    """Return the results of searching for all occurrences of
    "pattern" in "text".

    The return value is either a list of FindResult instance or [].
    The options dictionary may have to following values:
        patternType: simple* | wildcard | regex-python
        matchWord: 0* | 1
        case: insensitive* | sensitive | smart
    (*) indicates the default
    """
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)

    matches = _FindAll(text, 0, len(text), pattern, flags)

    results = []
    for match in matches:
        result = FindResult(start=match.start(), end=match.end(),
                            value=match.group())
        results.append(result)
    return results


def replace(text, pattern, replacement, startOffset=0, **options):
    """Return a result indicating how to replace the first "pattern" in
    "text" with "replacement".

    The return value is either a ReplaceResult instance or None.
    The options dictionary may have to following values:
        patternType: simple* | wildcard | regex-python
        matchWord: 0* | 1
        searchBackward: 0* | 1
        case: insensitive* | sensitive | smart
    (*) indicates the default
    """
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)
    searchBackward = options.has_key("searchBackward") and options["searchBackward"]

    # Unless we are using a regex pattern type we automatically escape
    # all backslashes.
    if not options.get("patternType", "").startswith("regex"):
        replacement = replacement.replace('\\', '\\\\')

    # Check for a return a nicer error message for an unescaped trailing
    # slash than what sre would return:
    #   sre_constants.error: bogus escape (end of line)
    numTrailingSlashes = 0
    for i in range(len(replacement)-1, -1, -1):
        if replacement[i] == '\\':
            numTrailingSlashes += 1
        else:
            break
    if numTrailingSlashes % 2:
        raise FindError("the trailing backslash must be escaped")

    if not searchBackward:
        match = _Find(text, startOffset, len(text), pattern, flags)
    else:
        # to search backwards, find all the result from the start up the
        # the desired starting position and take the last one
        matches = _FindAll(text, 0, startOffset, pattern, flags)
        if matches:
            match = matches[-1]
        else:
            match = None

    if match:
        result = ReplaceResult(start=match.start(), end=match.end(),
                               value=match.group(),
                               replacement=match.expand(replacement))
    else:
        result = None
    return result


def replaceall(text, pattern, replacement, **options):
    """Return a results indicating how to replace all occurrences of
    "pattern" in "text" with "replacement".

    The return value is either a list of ReplaceResult instances or [].
    The options dictionary may have to following values:
        patternType: simple* | wildcard | regex-python
        matchWord: 0* | 1
        case: insensitive* | sensitive | smart
    (*) indicates the default
    """
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)

    # Unless we are using a regex pattern type we automatically escape
    # all backslashes.
    if not options.get("patternType", "").startswith("regex"):
        replacement = replacement.replace('\\', '\\\\')

    # Check for a return a nicer error message for an unescaped trailing
    # slash than what sre would return:
    #   sre_constants.error: bogus escape (end of line)
    numTrailingSlashes = 0
    for i in range(len(replacement)-1, -1, -1):
        if replacement[i] == '\\':
            numTrailingSlashes += 1
        else:
            break
    if numTrailingSlashes % 2:
        raise FindError("the trailing backslash must be escaped")

    matches = _FindAll(text, 0, len(text), pattern, flags)

    results = []
    for match in matches:
        result = ReplaceResult(start=match.start(), end=match.end(),
                               value=match.group(),
                               replacement=match.expand(replacement))
        results.append(result)
    return results

def validatePattern(pattern, **options):
    """validate the pattern and options.  This is used in find in files
       to validate the search prior to kicking off the thread"""
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)
    return re.compile(pattern, flags)
    
def findallex(text, pattern, **options):
    """Find all occurrences of pattern in the given text.

        "text" is the text to work on
        "pattern" is the pattern to look for
        "options" may have to following keys:
                patternType: simple* | wildcard | regex-python
                matchWord: 0* | 1
                case: insensitive* | sensitive | smart
            (*) indicates the default

    This substitute for findall() is part of faster alternative tailored
    to usage in Komodo.

    Returns a list of re MatchObject's.
    """
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)

    matches = _FindAll(text, 0, len(text), pattern, flags)
    return matches


def replaceallex(text, pattern, replacement, skipZone=None,
                 wantMatches=0, **options):
    """Replace all occurrences of pattern in the given text.

        "text" is the text to work on
        "pattern" is the pattern to look for
        "replacment" is the replacement string
        "skipZone" (optional) is a list of 2-tuples giving an index range to
            skip in the search for replacement hits. Currently only the
            following sets are allowed:
                None or []              no part of text is skipped
                [(<start>, <end>)]      text[<start>:<end>] is skipped
                [(0, <start>),
                 (<end>, len(text))]    all BUT text[<start>:<end>] is skipped
        "wantMatches" is a boolean indicating if the list of matches should
            be returned (see below). This slows things down considerably.
        "options" may have to following keys:
                patternType: simple* | wildcard | regex-python
                matchWord: 0* | 1
                case: insensitive* | sensitive | smart
            (*) indicates the default

    This substitute for replaceall() is a MUCH faster alternative tailored
    to usage in Komodo.

    Returns a 3-tuple:
        1. the replacement text if there are changes, otherwise None; and
        2. the number of replacements
        3. a list of re MatchObject's iff "wantMatches", otherwise None
    """
    flags = _GetReFlags(pattern, **options)
    pattern = _MassageSearchToken(pattern, **options)

    # Unless we are using a regex pattern type we automatically escape
    # all backslashes.
    if not options.get("patternType", "").startswith("regex"):
        replacement = replacement.replace('\\', '\\\\')

    # Check for and return a nicer error message for an unescaped trailing
    # slash than what sre would return:
    #   sre_constants.error: bogus escape (end of line)
    numTrailingSlashes = 0
    for i in range(len(replacement)-1, -1, -1):
        if replacement[i] == '\\':
            numTrailingSlashes += 1
        else:
            break
    if numTrailingSlashes % 2:
        raise FindError("the trailing backslash must be escaped")

    # get "matches"
    if wantMatches:
        # If the match objects _are_ wanted then we _are_ redundantly regex
        # matching each hit in "text", but the presumption is that this
        # is faster than doing it once and then generating the replacement
        # text from the list of matches.
        if not skipZone:
            matches = _FindAll(text, 0, len(text), pattern, flags)
        elif len(skipZone) == 1:
            # e.g., skipZone = [(13, 26)]
            matches = (_FindAll(text, 0, skipZone[0][0],
                                pattern, flags) +
                       _FindAll(text, skipZone[0][1], len(text),
                                pattern, flags))
        else:
            # e.g., skipZone = [(0, 25), (300, 543)] # where 543 == len(text)
            assert len(skipZone) == 2
            matches = _FindAll(text, skipZone[0][1], skipZone[1][0],
                               pattern, flags)
    else:
        matches = None

    # get "numRepls"
    if matches:
        numRepls = len(matches)
    else:
        if not skipZone:
            numRepls = _CountAll(text, 0, len(text), pattern, flags)
        elif len(skipZone) == 1:
            # e.g., skipZone = [(13, 26)]
            numRepls = (_CountAll(text, 0, skipZone[0][0],
                                  pattern, flags) +
                        _CountAll(text, skipZone[0][1], len(text),
                                  pattern, flags))
        else:
            # e.g., skipZone = [(0, 25), (300, 543)] # where 543 == len(text)
            assert len(skipZone) == 2
            numRepls = _CountAll(text, skipZone[0][1], skipZone[1][0],
                                 pattern, flags)

    # get "repl"
    if not skipZone:
        repl = _ReplaceAll(text, 0, len(text), pattern, replacement, flags)
    elif len(skipZone) == 1:
        # e.g., skipZone = [(13, 26)]
        pivot = skipZone[0][0]
        topHalf = text[:pivot]
        bottomHalf = text[pivot:]
        repl = (_ReplaceAll(topHalf, 0, skipZone[0][0],
                            pattern, replacement, flags) +
                _ReplaceAll(bottomHalf, skipZone[0][1]-pivot, len(bottomHalf),
                            pattern, replacement, flags))
    else:
        # e.g., skipZone = [(0, 25), (300, 543)] # where 543 == len(text)
        assert len(skipZone) == 2
        repl = _ReplaceAll(text, skipZone[0][1], skipZone[1][0],
                           pattern, replacement, flags)
    if repl == text:
        repl = None
        
    return repl, numRepls, matches


#---- command line mainline

def usage():
    usage = """Usage:
    findlib [options] find <pattern> [<files>...]
    findlib [options] findall <pattern> [<files>...]
    findlib [options] replace <pattern> <replacement> [<files>...]
    findlib [options] replaceall <pattern> <replacement> [<files>...]

    Options:
        -v, --verbose       verbose output
        --test              run the self-test

        --simple, --wildcard, --regex-python
                            search token type (default is "simple")
        -w, --word          match whole words only
        --case=sensitive|insensitive|smart
                            case sensitivity, default is insensitive, "smart"
                            indicate to be case sensitive iff there are any
                            uppercase chars in search token
    Options for find() and replace() only:
        --backward          search backwards through the given files
        --offset=<num>      a character offset at which to begin searching,
                            default is 0
"""
    out.write(usage)


def main(argv):
    """command line interface (primarily) for testing this module"""
    # parse options
    import getopt
    try:
        optlist, args = getopt.getopt(argv[1:], 'hvw',\
            ['help', 'verbose', 'test',
             'simple', 'wildcard', 'regex-python',
             'word',
             'case=', 'backward', 'offset=' ])
    except getopt.GetoptError, msg:
        out.write("%s: error in options: %s\n" % (argv[0], msg))
        out.write("Try 'python findlib.py --help'.\n")
        return 1
    global verbosity
    options = {}
    startOffset = 0
    for opt,optarg in optlist:
        if opt in ('-v', '--verbose'):
            verbosity = 1
        elif opt in ('-h', '--help'):
            usage()
            return 0
        elif opt == "--test":
            return test()
        elif opt in ("--simple", "--wildcard", "--regex-python"):
            if options.has_key("patternType"):
                out.write("Can only specify one of --simple, --wildcard, "\
                          "--regex-python.\n")
                usage()
                return 1
            else:
                options["patternType"] = opt[2:]
        elif opt in ('-w', '--word'):
            options["matchWord"] = 1 
        elif opt == "--case":
            recognized = ("sensitive", "insensitive", "smart")
            if optarg not in recognized:
                out.write("Unrecognized case-sensitivity type '%s'. It "\
                          "must be one of %s.\n" % (optarg, recognized))
                usage()
                return 1
            else:
                options["case"] = optarg
        elif opt == "--backward":
            options["searchBackward"] = 1
        elif opt == "--offset":
            startOffset = int(optarg)

    # parse arguments
    try:
        action = args[0]
        if action in ("find", "findall"):
            pattern = args[1]
            filenames = args[2:]
        elif action in ("replace", "replaceall"):
            pattern, replacement = args[1:3]
            filenames = args[3:]
        else:
            raise FindError("Urecognized action: %s" % action)
    except (IndexError, ValueError):
        print "Error: incorrect args: %s" % args
        usage()
        if verbosity > 0:
            raise   # re-raise
        else:
            return 1

    # do the work
    for filename in filenames:
        i = open(filename, "r")
        text = i.read()
        i.close()
        
        results = []
        if action == "find":
            result = find(text, pattern, startOffset, **options)
            results.append(result)
        elif action == "replace":
            result = replace(text, pattern, replacement,
                             startOffset, **options)
            results.append(result)
        elif action == "findall":
            results = findall(text, pattern, startOffset, **options)
        elif action == "replaceall":
            results = replaceall(text, pattern, replacement, **options)
        for result in results:
            print "%s: %s" % (filename, result)

    return 0


def test():
    r"""
    Simple usage of 'find' and 'findall':

        >>> import findlib
        >>> result = findlib.find("hello there", "he")
        >>> print result
        0-2: found 'he'
        >>> results = findlib.findall("hello there", "he")
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'he'
        7-9: found 'he'
        >>>

    Simple usage of 'replace' and 'replaceall':

        >>> result = findlib.replace("Hello there", "he", "foo")
        >>> print result
        0-2: replace 'He' with 'foo'
        >>> results = findlib.replaceall("Hello there", "he", "foo")
        >>> for result in results:
        ...     print result
        ...
        0-2: replace 'He' with 'foo'
        7-9: replace 'he' with 'foo'
        >>>

    Specify a starting offset:

        >>> import findlib
        >>> result = findlib.find("Hello there", "he", 4)
        >>> print result
        7-9: found 'he'
        >>>

    Using some options (case-sensitivity):

        >>> import findlib
        >>> options = {}
        >>> options["case"] = "sensitive"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        7-9: found 'he'
        >>>
        >>> options["case"] = "insensitive"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        7-9: found 'he'
        >>> options["case"] = "smart"
        >>> results = findlib.findall("Hello there", "he", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        7-9: found 'he'
        >>> results = findlib.findall("Hello there", "He", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'He'
        >>>

    Using some options (wildcard and regex-python searches):

        >>> import findlib
        >>> options = {}
        >>> options["patternType"] = "simple"
        >>> results = findlib.findall("fe fi fo fum", "f", **options)
        >>> for result in results:
        ...     print result
        ...
        0-1: found 'f'
        3-4: found 'f'
        6-7: found 'f'
        9-10: found 'f'
        >>> options["patternType"] = "wildcard"
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        9-11: found 'fu'
        >>> options["matchWord"] = 1
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        >>> options["patternType"] = "regex-python"
        >>> options["matchWord"] = 0
        >>> results = findlib.findall("fe fi fo fum", "f[eu]m?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        9-12: found 'fum'

    Searching backwards:

        >>> import findlib
        >>> options = {}
        >>> options["patternType"] = "wildcard"
        >>> options["searchBackward"] = 0
        >>> results = findlib.findall("fe fi fo fum", "f?", **options)
        >>> for result in results:
        ...     print result
        ...
        0-2: found 'fe'
        3-5: found 'fi'
        6-8: found 'fo'
        9-11: found 'fu'
        >>> options["searchBackward"] = 1
        >>> result = findlib.find("fe fi fo fum", "f?", 11, **options)
        >>> print result
        9-11: found 'fu'

    Finding and replacing with \ characters:
    (http://bugs.activestate.com/show_bug.cgi?id=19447)

        >>> import findlib
        >>> results = findlib.findall('quoted \\"string\\" here', '\\')
        >>> for result in results:
        ...     print result
        ...
        7-8: found '\'
        15-16: found '\'

        >>> print findlib.find('quoted \\"string\\" here', '\\')
        7-8: found '\'

        >>> print findlib.replace('quoted \\"string\\" here', '\\', '')
        7-8: replace '\' with ''

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', 'a')
        7-9: replace '\\' with 'a'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\')
        7-9: replace '\\' with '\'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\\\a\\')
        7-9: replace '\\' with '\a\'

        >>> print findlib.replace('quoted \\\\"string\\\\" here', '\\\\', '\\\\\\')
        7-9: replace '\\' with '\\\'

        >>> print findlib.replace('quoted "string" here', '(str)ing', '\\1', patternType="regex-python")
        8-14: replace 'string' with 'str'

        >>> print findlib.replace('quoted "string" here', '(str)ing', '\\g<1>', patternType="regex-python")
        8-14: replace 'string' with 'str'

        >>> print findlib.replace('quoted "string" here', '(?P<var>str)ing', '\\g<var>', patternType="regex-python")
        8-14: replace 'string' with 'str'

    XXX find, replace, and replaceall in all of the above
    """
    import doctest, findlib
    return doctest.testmod(findlib)


if __name__ == "__main__":
    sys.exit( main(sys.argv) )

