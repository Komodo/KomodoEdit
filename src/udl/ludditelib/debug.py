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

"""Support for generating representations of lexed text for debugging."""

import os
from os.path import basename, dirname, join, exists, abspath
from glob import glob
import sys
import re
from cStringIO import StringIO
import logging
from pprint import pprint

from ludditelib.common import is_source_tree_layout

def _add_libs():
    """Get a SilverCity build on sys.path.
    Get Komodo's 'styles.py' on sys.path.
    """

    # Must be using the same Python version as Komodo's internal Python
    # because SilverCity is a binary ext.
    assert sys.version_info[:2] == (2, 7), "you must use Python 2.7.x"

    if is_source_tree_layout():
        ko_dev_dir = dirname(dirname(abspath(__file__)))
        while not exists(join(ko_dev_dir, "Construct")):
            d = dirname(ko_dev_dir)
            if d == "ko_dev_dir":
                raise RuntimeError("couldn't find SilverCity lib")
            ko_dev_dir = d
        lib_dirs = [
            glob(join(ko_dev_dir, "build", "release", "silvercity",
                      "build", "lib.*"))[0],
            join(ko_dev_dir, "src", "schemes"),
        ]
    else: # in SDK
        dist_dir = dirname(dirname(dirname(
            dirname(dirname(abspath(__file__))))))
        if exists(join(dist_dir, "bin", "is_dev_tree.txt")): # in a dev build
            # from: $mozObjDir/dist/komodo-bits/sdk/pylib/ludditelib/debug.py
            # to:   $mozObjDir/dist/bin/python/komodo
            lib_dirs = [join(dist_dir, "bin", "python", "komodo")]
        elif sys.platform == "darwin": # in a Komodo install on Mac OS X
            # from: Contents/SharedSupport/sdk/pylib/ludditelib/debug.py
            # to:   Contents/MacOS/python/komodo
            lib_dirs = [join(dist_dir, "MacOS", "python", "komodo")]
        else: # in a Komodo install on Windows or Linux
            # from: lib/sdk/pylib/ludditelib/debug.py
            # to:   lib/mozilla/python/komodo
            lib_dirs = [join(dist_dir, "lib", "mozilla", "python", "komodo")]
    for lib_dir in lib_dirs:
        sys.path.insert(0, lib_dir)

_add_libs()

import SilverCity
from SilverCity import ScintillaConstants
from SilverCity.Lexer import Lexer



#---- globals

log = logging.getLogger("luddite.debug")



#---- public routines

def lex(content, lang):
    """Lex the given content and lang and print a summary to stdout."""
    lexer = UDLLexer(lang)
    accessor = SilverCityAccessor(lexer, content)
    out = sys.stdout.write
    for token in accessor.gen_tokens():
        #pprint(token)
        out("token %(start_line)d,%(start_column)d"
            "-%(end_line)d,%(end_column)d"
            " (chars %(start_index)d-%(end_index)d):" % token)
        style_names = _style_names_from_style_num(token["style"])
        out(" %s (%d)\n" % (', '.join(style_names), token["style"]))
        out(_indent(_escaped_text_from_text(token["text"]), 2) + '\n')


def lex_to_html(content, lang, include_styling=True, include_html=True,
                title=None):
    """Return a styled HTML snippet for the given content and language.
    
        "include_styling" (optional, default True) is a boolean
            indicating if the CSS/JS/informational-HTML should be
            included.
        "include_html" (optional, default True) is a boolean indicating
            if the HTML output should be wrapped into a complete HTML
            document.
        "title" is the HTML document title to use if 'include_html' is
            True.
    """
    if title is None:
        title = "%s content" % lang

    html = StringIO()

    if include_html:
        html.write('''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>%s</title>
</head>
<body>
''' % title)

    if include_styling:
        html.write('''
<script type="application/x-javascript">
    function show_class(span) {
        var infobox = document.getElementById("infobox");
        infobox.innerHTML = span.getAttribute("class");
    }
</script>

<style>
#infobox {
    border: 4px solid #e0e0e0;
    background-color: #f0f0f0;
    padding: 10px;
    position: fixed;
    top: 5px;
    right: 5px;
}

/* token highlighting and debugging info */
div.code span:hover {
    background-color: #e0e0e0;
}

div.code span.udl-region:hover {
    background-color: #f0f0f0;
}

/* language-neutral syntax coloring */
div.code {
    font-family: "Courier New", Courier, monospace;
    font-size: small;
}

div.code .comments    { color: grey; }
div.code .keywords    { font-weight: bold; }
div.code .identifiers { color: black; }
div.code .strings     { color: blue; }
div.code .classes,
div.code .functions   { color: green; }
div.code .stderr      { background-color: red; }
div.code .stdout      { background-color: blue; }
div.code .tags        { color: red; }

</style>

<div id="infobox"></div>
''')

    #XXX escape lang name for CSS class
    html.write('<div class="code %s">\n' % lang.lower())


    lexer = UDLLexer(lang)
    accessor = SilverCityAccessor(lexer, content)
    curr_udl_region = None
    ch = last_ch = None
    for token in accessor.gen_tokens():
        css_classes = _style_names_from_style_num(token["style"])
        if css_classes and css_classes[0].startswith("SCE_UDL_"):
            udl_region = css_classes[0].split('_')[2]
            if udl_region == curr_udl_region:
                pass
            else:
                if curr_udl_region:
                    html.write('\n</span>\n')
                html.write('\n<span class="udl-region">\n')
                curr_udl_region = udl_region
        html.write('<span class="%s" onmouseover="show_class(event.target);">'
                   % ' '.join(css_classes))
        for i, ch in enumerate(token["text"]):
            if ch == "\n" and last_ch == "\r":
                # Treat '\r\n' as one char.
                continue
            #TODO: tab expansion.
            html.write(_htmlescape(ch, quote=True, whitespace=True))
            last_ch = ch
        html.write('</span>')
    if curr_udl_region:
        html.write('\n</span>\n')
    html.write('</div>\n')

    if include_html:
        html.write('''
</body>
</html>
''')

    return html.getvalue()



#---- internal Lexer stuff (mostly from codeintel)

# Lazily built cache of SCE_* style number (per language) to constant name.
_style_name_from_style_num_from_lang = {}
_sce_prefixes = ["SCE_UDL_"]

def _style_names_from_style_num(style_num):
    #XXX Would like to have python-foo instead of p_foo or SCE_P_FOO, but
    #    that requires a more comprehensive solution for all langs and
    #    multi-langs.
    style_names = []

    # Get the constant name from ScintillaConstants.
    if "UDL" not in _style_name_from_style_num_from_lang:
        name_from_num = _style_name_from_style_num_from_lang["UDL"] = {}
        for attr in dir(ScintillaConstants):
            for sce_prefix in _sce_prefixes:
                if attr.startswith(sce_prefix):
                    name_from_num[getattr(ScintillaConstants, attr)] = attr
    else:
        name_from_num = _style_name_from_style_num_from_lang["UDL"]
    const_name = _style_name_from_style_num_from_lang["UDL"][style_num]
    style_names.append(const_name)
    
    # Get a style group from styles.py.
    import styles
    if "UDL" in styles.StateMap:
        for style_group, const_names in styles.StateMap["UDL"].items():
            if const_name in const_names:
                style_names.append(style_group)
                break
    else:
        log.warn("lang 'UDL' not in styles.StateMap: won't have "
                 "common style groups in HTML output")
    
    return style_names


_re_bad_filename_char = re.compile(r'([% 	\x80-\xff])')
def _lexudl_path_escape(m):
    return '%%%02X' % ord(m.group(1))
def _urlescape(s):
    return _re_bad_filename_char.sub(_lexudl_path_escape, s)

class UDLLexer(Lexer):
    """LexUDL wants the path to the .lexres file as the first element of
    the first keywords list.
    """
    def __init__(self, lang):
        self.lang = lang
        self._properties = SilverCity.PropertySet()
        self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_UDL)
        lexres_path = _urlescape(self._get_lexres_path(lang))
        #log.debug("escaped lexres_path: %r", lexres_path)
        self._keyword_lists = [
            SilverCity.WordList(lexres_path),
        ]

    def _gen_lexres_candidate_paths(self, lang):
        if is_source_tree_layout():
            # Look for a lexres path in a local luddite build.
            udl_dir = dirname(dirname(__file__))
            yield join(udl_dir, "build", lang, "lexers", lang+".lexres")
            # Look in the Komodo-devel build tree.
            ko_dir = dirname(dirname(udl_dir))
            yield join(ko_dir, "build", "release", "udl",
                       "build", lang, "lexers", lang+".lexres")

        # We are an installed Komodo SDK layout or in the Komodo build
        # $MOZ_OBJDIR.
        else:
            import koextlib
            ko_info = koextlib.KomodoInfo()
            for ext_dir in ko_info.ext_dirs:
                yield join(ext_dir, "lexers", lang+".lexres")

    def _get_lexres_path(self, lang):
        candidates = []
        for path in self._gen_lexres_candidate_paths(lang):
            candidates.append(path)
            if exists(path):
                log.debug("using `%s' lexres file", path)
                return path
        else:
            raise RuntimeError("could not find a lexres file for %s: "
                               "none of '%s' exist"
                               % (lang, "', '".join(candidates)))



#---- internal Accessor stuff (from codeintel)

class Accessor(object):
    """Virtual base class for a lexed text accessor. This defines an API
    with which lexed text data (the text content, styling info, etc.) is
    accessed by trigger/completion/etc. handling. Actual instances will
    be one of the subclasses.
    """
    def char_at_pos(self, pos):
        raise VirtualMethodError()
    def style_at_pos(self, pos):
        raise VirtualMethodError()
    def line_and_col_at_pos(self, pos):
        raise VirtualMethodError()
    def gen_char_and_style_back(self, start, stop):
        """Generate (char, style) tuples backward from start to stop
        a la range(start, stop, -1) -- i.e. exclusive at 'stop' index.

        For SciMozAccessor this can be implemented more efficiently than
        the naive usage of char_at_pos()/style_at_pos().
        """
        raise VirtualMethodError()
    def gen_char_and_style(self, start, stop):
        """Generate (char, style) tuples forward from start to stop
        a la range(start, stop) -- i.e. exclusive at 'stop' index.

        For SciMozAccessor this can be implemented more efficiently than
        the naive usage of char_at_pos()/style_at_pos().
        """
        raise VirtualMethodError()
    def match_at_pos(self, pos, s):
        """Return True if the given string matches the text at the given
        position.
        """
        raise VirtualMethodError()
    def line_from_pos(self, pos):
        """Return the 0-based line number for the given position."""
        raise VirtualMethodError()
    def line_start_pos_from_pos(self, pos):
        """Return the position of the start of the line of the given pos."""
        raise VirtualMethodError()
    def pos_from_line_and_col(self, line, col):
        """Return the position of the given line and column."""
        raise VirtualMethodError()
    @property
    def text(self):
        """All buffer content (as a unicode string)."""
        raise VirtualMethodError()
    def text_range(self, start, end):
        raise VirtualMethodError()
    def length(self):
        """Return the length of the buffer.

        Note that whether this returns a *character* pos or a *byte* pos is
        left fuzzy so that SilverCity and SciMoz implementations can be
        efficient. All that is guaranteed is that the *_at_pos() methods
        work as expected.
        """
        raise VirtualMethodError()
    #def gen_pos_and_char_fwd(self, start_pos):
    #    """Generate (<pos>, <char>) tuples forward from the starting
    #    position until the end of the document.
    #    
    #    Note that whether <pos> is a *character* pos or a *byte* pos is
    #    left fuzzy so that SilverCity and SciMoz implementations can be
    #    efficient.
    #    """
    #    raise VirtualMethodError()
    def gen_tokens(self):
        """Generator for all styled tokens in the buffer.
        
        Currently this should yield token dict a la SilverCity's
        tokenize_by_style().
        """
        raise VirtualMethodError()
    def contiguous_style_range_from_pos(self, pos):
        """Returns a 2-tuple (start, end) giving the span of the sequence of
        characters with the style at position pos."""
        raise VirtualMethodError()


class SilverCityAccessor(Accessor):
    def __init__(self, lexer, content):
        #XXX i18n: need encoding arg?
        self.lexer = lexer
        self.content = content #XXX i18n: this should be a unicode buffer

    def reset_content(self, content):
        """A backdoor specific to this accessor to allow the equivalent of
        updating the buffer/file/content.
        """
        self.content = content
        self.__tokens_cache = None

    __tokens_cache = None
    @property
    def tokens(self):
        if self.__tokens_cache is None:
            self.__tokens_cache = self.lexer.tokenize_by_style(self.content)
        return self.__tokens_cache
        
    def char_at_pos(self, pos):
        return self.content[pos]

    def _token_at_pos(self, pos):
        #XXX Locality of reference should offer an optimization here.
        # Binary search for appropriate token.
        lower, upper = 0, len(self.tokens)  # [lower-limit, upper-limit)
        sentinel = 15
        while sentinel > 0:
            idx = ((upper - lower) / 2) + lower
            token = self.tokens[idx]
            #print "_token_at_pos %d: token idx=%d text[%d:%d]=%r"\
            #      % (pos, idx, token["start_index"], token["end_index"],
            #         token["text"])
            start, end = token["start_index"], token["end_index"]
            if pos < token["start_index"]:
                upper = idx
            elif pos > token["end_index"]:
                lower = idx + 1
            else:
                return token
            sentinel -= 1
        else:
            raise Error("style_at_pos binary search sentinel hit: there "
                        "is likely a logic problem here!")

    def style_at_pos(self, pos):
        return self._token_at_pos(pos)["style"]

    def line_and_col_at_pos(self, pos):
        #TODO: Fix this. This is busted for line 0 (at least).
        line = self.line_from_pos(pos) - 1
        # I assume that since we got the line, __start_pos_from_line exists
        col = pos - self.__start_pos_from_line[line]
        return line, col
    
    #PERF: If perf is important for this accessor then could do much
    #      better with smarter use of _token_at_pos() for these two.
    def gen_char_and_style_back(self, start, stop):
        assert -1 <= stop <= start, "stop: %r, start: %r" % (stop, start)
        for pos in range(start, stop, -1):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))
    def gen_char_and_style(self, start, stop):
        assert 0 <= start <= stop, "start: %r, stop: %r" % (start, stop)
        for pos in range(start, stop):
            yield (self.char_at_pos(pos), self.style_at_pos(pos))

    def match_at_pos(self, pos, s):
        return self.content[pos:pos+len(s)] == s
    
    __start_pos_from_line = None
    def line_from_pos(self, pos):
        r"""
            >>> sa = SilverCityAccessor(lexer,
            ...         #0         1           2         3
            ...         #01234567890 123456789 01234567890 12345
            ...         'import sys\nif True:\nprint "hi"\n# bye')
            >>> sa.line_from_pos(0)
            0
            >>> sa.line_from_pos(9)
            0
            >>> sa.line_from_pos(10)
            0
            >>> sa.line_from_pos(11)
            1
            >>> sa.line_from_pos(22)
            2
            >>> sa.line_from_pos(34)
            3
            >>> sa.line_from_pos(35)
            3
        """
        # Lazily build the line -> start-pos info.
        if self.__start_pos_from_line is None:
            self.__start_pos_from_line = [0]
            for line_str in self.content.splitlines(True):
                self.__start_pos_from_line.append(
                    self.__start_pos_from_line[-1] + len(line_str))

        # Binary search for line number.
        lower, upper = 0, len(self.__start_pos_from_line)
        sentinel = 15
        while sentinel > 0:
            line = ((upper - lower) / 2) + lower
            #print "LINE %d: limits=(%d, %d) start-pos=%d"\
            #      % (line, lower, upper, self.__start_pos_from_line[line])
            if pos < self.__start_pos_from_line[line]:
                upper = line
            elif line+1 == upper or self.__start_pos_from_line[line+1] > pos:
                return line
            else:
                lower = line
            sentinel -= 1
        else:
            raise Error("line_from_pos binary search sentinel hit: there "
                        "is likely a logic problem here!")

    def line_start_pos_from_pos(self, pos):
        token = self._token_at_pos(pos)
        return token["start_index"] - token["start_column"]
    def pos_from_line_and_col(self, line, col):
        if not self.__start_pos_from_line:
            self.line_from_pos(len(self.text)) # force init
        return self.__start_pos_from_line[line] + col

    @property
    def text(self):
        return self.content
    def text_range(self, start, end):
        return self.content[start:end]
    def length(self):
        return len(self.content)
    def gen_tokens(self):
        for token in self.tokens:
            yield token
    def contiguous_style_range_from_pos(self, pos):
        token = self._token_at_pos(pos)
        return (token["start_index"], token["end_index"] + 1)


#---- other internal stuff

# Recipe: htmlescape (1.1)
def _htmlescape(s, quote=False, whitespace=False):
    """Replace special characters '&', '<' and '>' by SGML entities.
    
    Also optionally replace quotes and whitespace with entities and <br/>
    as appropriate.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    if whitespace:
        s = s.replace(' ', "&nbsp;")
        #XXX Adding that '\n' might be controversial.
        s = re.sub(r"(\r\n|\r|\n)", "<br />\n", s)
    return s


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

# Recipe: text_escape (0.1)
def _escaped_text_from_text(text, escapes="eol"):
    r"""Return escaped version of text.

        "escapes" is either a mapping of chars in the source text to
            replacement text for each such char or one of a set of
            strings identifying a particular escape style:
                eol
                    replace EOL chars with '\r' and '\n', maintain the actual
                    EOLs though too
                whitespace
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
                eol-one-line
                    replace EOL chars with '\r' and '\n'
                whitespace-one-line
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
    """
    #TODO:
    # - Add 'c-string' style.
    # - Add _escaped_html_from_text() with a similar call sig.
    import re
    
    if isinstance(escapes, basestring):
        if escapes == "eol":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r"}
        elif escapes == "whitespace":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r",
                       '\t': "\\t", ' ': "."}
        elif escapes == "eol-one-line":
            escapes = {'\n': "\\n", '\r': "\\r"}
        elif escapes == "whitespace-one-line":
            escapes = {'\n': "\\n", '\r': "\\r", '\t': "\\t", ' ': '.'}
        else:
            raise ValueError("unknown text escape style: %r" % escapes)

    # Sort longer replacements first to allow, e.g. '\r\n' to beat '\r' and
    # '\n'.
    escapes_keys = escapes.keys()
    escapes_keys.sort(key=lambda a: len(a), reverse=True)
    def repl(match):
        val = escapes[match.group(0)]
        return val
    escaped = re.sub("(%s)" % '|'.join([re.escape(k) for k in escapes_keys]),
                     repl,
                     text)

    return escaped

def _one_line_summary_from_text(text, length=78,
        escapes={'\n':"\\n", '\r':"\\r", '\t':"\\t"}):
    r"""Summarize the given text with one line of the given length.
    
        "text" is the text to summarize
        "length" (default 78) is the max length for the summary
        "escapes" is a mapping of chars in the source text to
            replacement text for each such char. By default '\r', '\n'
            and '\t' are escaped with their '\'-escaped repr.
    """
    if len(text) > length:
        head = text[:length-3]
    else:
        head = text
    escaped = _escaped_text_from_text(head, escapes)
    if len(text) > length:
        summary = escaped[:length-3] + "..."
    else:
        summary = escaped
    return summary
