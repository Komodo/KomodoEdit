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

# luddite_lexer.py -- lexer for Luddite, using PLY
#
# See http://systems.cs.uchicago.edu/ply for more information on
# PLY, the lexer/parser framework this code uses.
#
# Author(s):
#   Eric Promislow <ericp@activestate.com>
#

import sys
from ludditelib import lex
import copy

tokens = (
    'ARROW',
    'MINUS',
    'PLUS',
    'COMMA',
    'COLON',
    'SCOLON',
    'OPAREN',
    'CPAREN',
    'OBRACKET',
    'CBRACKET',
#    'OBRACE',
#    'CBRACE',
    'EQUALS',
    'NUMBER',
    'LB_NAME',
    'LB_STRING',
    'LB_REGEX',
    'HT_ACCEPT',
    'HT_ALL',
    'HT_CLEAR_DELIMITER',
    'HT_DELIMITER',
    'HT_FAMILY',
    'HT_FOLD',
    'HT_KEEP_DELIMITER',
    'HT_KEYWORDS',
    'HT_KEYWORD_STYLE',
    'HT_INCLUDE',
    'HT_INITIAL',
    'HT_LANGUAGE',
    'HT_X_NAMESPACE',
    'HT_NOKEYWORD',
    'HT_PAINT',
    'HT_PATTERN',
    'HT_PUBLIC_ID',
    'HT_REDO',
    'HT_REJECT',
    'HT_SET_DELIMITER',
    'HT_SET_OPPOSITE_DELIMITER',
    'HT_SKIP',
    'HT_STATE',
    'HT_SUBLANGUAGE',
    'HT_SYSTEM_ID',
    'HT_TOKEN_CHECK',
    'HT_START_STYLE',
    'HT_END_STYLE',
    'HT_UPTO',
    'HT_SPUSH_CHECK',
    'HT_SPOP_CHECK',
    'HT_AT_EOL',
    'LB_NL',
    'HT_SSTACK_SET',
    )

t_ARROW = r'=>'
t_MINUS = r'-'
t_PLUS = r'\+'
t_COMMA = r','
t_COLON = r':'
t_SCOLON = r';'
t_OPAREN = r'\('
t_CPAREN = r'\)'
t_OBRACKET = r'\['
t_CBRACKET = r'\]'
#t_OBRACE = r'{'
#t_CBRACE = r'}'
t_EQUALS = r'='

reserved = {
    'accept' : 'HT_ACCEPT',
    'all' : 'HT_ALL',
    'at_eol' : 'HT_AT_EOL',
    'clear_delimiter' : 'HT_CLEAR_DELIMITER',
    'delimiter' : 'HT_DELIMITER',
    'family' : 'HT_FAMILY',
    'fold' : 'HT_FOLD',
    'keep_delimiter' : 'HT_KEEP_DELIMITER',
    'keywords' : 'HT_KEYWORDS',
    'keyword_style' : 'HT_KEYWORD_STYLE',
    'include' : 'HT_INCLUDE',
    'initial' : 'HT_INITIAL',
    'language' : 'HT_LANGUAGE',
    # Calling this "HT_NO_KEYWORD" will confuse PLY
    'namespace' : 'HT_X_NAMESPACE',
    'no_keyword' : 'HT_NOKEYWORD',
    'paint' : 'HT_PAINT',
    'pattern' : 'HT_PATTERN',
    'public_id' : 'HT_PUBLIC_ID',
    'publicid' : 'HT_PUBLIC_ID',       # Same keyword
    'redo' : 'HT_REDO',
    'reject' : 'HT_REJECT',
    'set_delimiter' : 'HT_SET_DELIMITER',
    'set_opposite_delimiter' : 'HT_SET_OPPOSITE_DELIMITER',
    'skip' : 'HT_SKIP',
    'state' : 'HT_STATE',
    'sublanguage' : 'HT_SUBLANGUAGE',
    'sub_language' : 'HT_SUBLANGUAGE',  # Same keyword
    'systemid' : 'HT_SYSTEM_ID',         # Same keyword
    'system_id' : 'HT_SYSTEM_ID',
    'token_check' : 'HT_TOKEN_CHECK',
    'start_style' : 'HT_START_STYLE',
    'end_style' : 'HT_END_STYLE',
    'upto' : 'HT_UPTO',
    'spush_check' : 'HT_SPUSH_CHECK',
    'spop_check' : 'HT_SPOP_CHECK',
    'sstack_set' : 'HT_SSTACK_SET',
    }

# These are right from the docs, work for Luddite

def t_LB_NAME(t):
    r'[a-zA-Z][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value,'LB_NAME')    # Check for reserved words
    return t

def t_NUMBER(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print "Number %s is too large!" % t.value
        t.value = 0
    return t

# Define a rule so we can track line numbers

# Sometimes we return this, but in lists we don't.

def t_LB_NL(t): # Newline
    r'\r?\n'
    t.lineno += 1
    return t

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print "Illegal character '%s'" % t.value[0]
    t.skip(1)

# Comments

def t_comment(t):
    r'\#.*'
    t.skip(len(t.value))

def t_nl_escape(t):
    r'\\\r?\n'
    t.lineno += 1
    t.skip(len(t.value))

def t_LB_STRING(t):
    r'''((?:'[^'\\]*(?:\\.|[^'\\])*')|(?:"[^"\\]*(?:\\.|[^"\\])*"))'''
    return t

def t_LB_REGEX(t):
    r'/(\\.|[^\\/])*/i?'
    return t

class Lexer:
    def __init__(self):
        self.lexer = lex.lex(debug=0)

    def token(self):
        tok = self.lexer.token()
        return tok
    
    def input(self, s):
        self.lexer.input(s)
    
    def _test(self):
        tok = None
        while 1:
            prev_tok = tok
            tok = self.token()
            if not tok:
                break
            print tok

def get_input(fname, searchPath=['.']):
        # Read in the file contents.
        fin = None
        if fname == '-':
            fin = sys.stdin
        else:
            for p in searchPath:
                try:
                    fpath = p + "/" + fname
                    fin = open(fpath, 'r')
                    # print "**************** Opening file " + fpath + "..."
                    break
                except:
                    # print "Can't open file " + fpath
                    pass
            if fin is None:
                print "Can't find file " + fname
                return None
        s = fin.read()
        fin.close()
        return s


def do_main(fname):
    s = get_input(fname)
    lw = Lexer()
    lw.input(s)
    return lw._test()

def main(argv):
    global searchPath
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-I", "--include", action="append", dest="path", 
                      help="add to search path")
    (options, args) = parser.parse_args()
    if options.path:
        searchPath += options.path
    
    if len(args) != 1:
        import py_compile
        raise py_compile.PyCompileError("Incorrect number of arguments: %r" % argv[1:])
    return do_main(args[0])

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
