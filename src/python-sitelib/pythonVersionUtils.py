# Copyright (c) 2000-2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Use Python 2's tokenize module to lex both Python2 and Python3
# programs.  Count the distinct constructs in both variants,
# and return a "score" to determine which type of Python the
# buffer is using.  The first value contains the number of hits
# that can only occur in Python2 programs, the second the number
# of hits that are valid only in Python3.

# This program also allows Python3 programs to create functions
# that have the same names as builtins in Python2 that didn't make
# the cut.

# It's an error for a valid file to score hits for both Python2 and 3.

import sys
import re
import token
import tokenize

import logging
log = logging.getLogger("pythonVersionUtils")
#log.setLevel(logging.DEBUG)

class _FileWrapper(object):            
    def set_file(self, filename):
        self.f = open(filename, 'r')
        
    def set_stdin(self):
        self.f = sys.stdin
        
    def set_text(self, text):
        from cStringIO import StringIO
        self.f = StringIO(text)

    def readline(self):
        return self.f.readline()

    def close(self):
        self.f.close()

def _match_tokens(tok_gen, list):
    for item in list:
        res = safe_get_next_token(tok_gen)
        if res[0] != item[0] or res[1] != item[1]:
            return False
    return True

class _Scorekeeper(object):
    def __init__(self):
        self.py2 = 0
        self.py3 = 0
        
    def is_definitive(self):
        diff = abs(self.py2 - self.py3)
        if diff < 5:
            return False
        half_diff = diff / 2
        if diff >= 5:
            return self.py2 <= half_diff or self.py3 <= half_diff
        return False
    
    def inc_2(self):
        self.py2 += 1
        if self.is_definitive():
            raise StopIteration
        return self.is_definitive()
    
    def inc_3(self):
        self.py3 += 1
        if self.is_definitive():
            raise StopIteration
        return self.is_definitive()
        
    def score(self):
        return (self.py2, self.py3)

_octal_pattern = re.compile(r'0\d')
_terminators = (":", ";")
_ws_tokens = (tokenize.N_TOKENS, tokenize.INDENT, tokenize.DEDENT)

def at_stmt_end(token_type, token_string):
    return (token_type in (tokenize.NL, tokenize.NEWLINE)
            or (token_type == tokenize.OP and token_string in _terminators))
    
def safe_get_next_token(tokenizer):
    try:
        return tokenizer.next()
    except (tokenize.TokenError, IndentationError):
        log.debug("problem getting next token")
        raise StopIteration
    
def _calc_py2_py3_scores(textWrapper):
    sk = _Scorekeeper()
    pseudo_keywords = ('print', 'exec')
    exception_attributes = ('exc_type', 'exc_value', 'exc_traceback')
    tok_gen = tokenize.generate_tokens(textWrapper.readline)
    at_line_start = True
    while True:
        try:
            curr_token = safe_get_next_token(tok_gen)
            token_type, token_string, start_tup, end_tup, line = curr_token
            #log.debug("token_type:%d, token_string:%s, start_tup:[%d,%d], end_tup:[%d,%d], line:%s",
            #          token_type, token_string, start_tup[0], start_tup[1], end_tup[0], end_tup[1], line)
            if token_type in _ws_tokens:
                pass
            elif at_stmt_end(token_type, token_string):
                at_line_start = True
            elif at_line_start:
                at_line_start = False
                if token_type == tokenize.NAME:
                    if token_string in pseudo_keywords:
                        curr_keyword = token_string
                        curr_line = curr_token[2][0]
                        while True:
                            curr_token = safe_get_next_token(tok_gen)
                            token_type, token_string, start_tup, end_tup, line = curr_token
                            if token_type != tokenize.N_TOKENS:
                                break
                        if (start_tup[0] != curr_line
                            or not (token_type == tokenize.OP and token_string == '(')):
                            #log.debug("2-1: print/exec at line %d", start_tup[0])
                            sk.inc_2()
                            if at_stmt_end(token_type, token_string):
                                at_line_start = True
                            continue
                        if curr_keyword != 'print':
                            continue
                        # Look out for '>> fd' or arg=value
                        # Keep using the current token
                        while True:
                            if at_stmt_end(token_type, token_string):
                                at_line_start = True
                                break
                            elif token_type == tokenize.OP:
                                if token_string == "<<":
                                    sk.inc_2()
                                    break
                                elif token_string == '=':
                                    sk.inc_3()
                                    break
                            curr_token = safe_get_next_token(tok_gen)
                            token_type, token_string, start_tup, end_tup, line = curr_token
                            
                    elif token_string == "except":
                        curr_token = safe_get_next_token(tok_gen)
                        if curr_token[0] == tokenize.OP:
                            if curr_token[1] == ":":
                                continue # Common to both
                            elif curr_token[1] == "(":
                                paren_count = 1
                                while True:
                                    curr_token = safe_get_next_token(tok_gen)
                                    if curr_token[0] == tokenize.OP:
                                        if curr_token[1] == "(":
                                            paren_count += 1
                                        elif curr_token[1] == ")":
                                            paren_count -= 1
                                            if paren_count == 0:
                                                break
                            else:
                                log.debug("In except(1), can't deal with token %s", curr_token)
                                continue
                        elif curr_token[0] == tokenize.NAME:
                            pass
                        else:
                            log.debug("In except(2), can't deal with token %s", curr_token)
                            continue
                        curr_token = safe_get_next_token(tok_gen)
                        if curr_token[0] == tokenize.OP:
                            if curr_token[1] == ":":
                                continue # Common to both
                            elif curr_token[1] == ",":
                                #log.debug("2-2: except at line %d", curr_token[2][0])
                                sk.inc_2()
                        elif curr_token[0] == tokenize.NAME and curr_token[1] == 'as':
                            sk.inc_3()
                            #log.debug("3-3: except at line %d", curr_token[2][0])
                        else:
                            log.debug("In except(3), can't deal with token %s", curr_token[4])
                        continue
                    elif token_string == "raise":
                        curr_token = safe_get_next_token(tok_gen)
                        if curr_token[0] == tokenize.STRING:
                            sk.inc_2()
                            #log.debug("2-4: except at line %d", curr_token[2][0])
                        elif curr_token[0] != tokenize.NAME:
                            log.debug("In except(4), can't deal with token %s", curr_token[4])
                        else:
                            curr_token = safe_get_next_token(tok_gen)
                            if curr_token[0] == tokenize.NEWLINE:
                                pass # common
                            elif curr_token[0] != tokenize.OP:
                                pass # broken in both
                            elif curr_token[1] == ',':
                                sk.inc_2()
                                #log.debug("2-5: except at line %d", curr_token[2][0])
                    elif token_string == 'from':
                        if _match_tokens(tok_gen, ((tokenize.NAME, 'sys'),
                                          (tokenize.NAME, 'import'))):
                            curr_token = safe_get_next_token(tok_gen)
                            if curr_token[0] == tokenize.NAME:
                                if curr_token[1] == 'maxint':
                                    sk.inc_2()
                                    #log.debug("2-6: except at line %d", curr_token[2][0])
                                elif curr_token[1] == 'maxsize':
                                    sk.inc_3()
                                    #log.debug("3-7: except at line %d", curr_token[2][0])
            if token_type == tokenize.NAME:
                if token_string in ('u', 'ur'):
                    curr_token = safe_get_next_token(tok_gen)
                    if curr_token[0] == tokenize.STRING:
                        sk.inc_2()
                        #log.debug("2-8: except at line %d", curr_token[2][0])
                elif token_string == 'sys':
                    if _match_tokens(tok_gen, ((tokenize.OP, '.'),)):
                        curr_token = safe_get_next_token(tok_gen)
                        if (curr_token[0] == tokenize.NAME and curr_token[1] in exception_attributes):
                            sk.inc_2()
                            #log.debug("2-9: except at line %d", curr_token[2][0])
                elif token_string == 'os':
                    if (_match_tokens(tok_gen, ((tokenize.OP, '.'),
                                               (tokenize.NAME, 'getcwdu'),))):
                        sk.inc_2()
                        #log.debug("2-10: except at line %d", curr_token[2][0])
            elif token_type == tokenize.NUMBER:
                if token_string.endswith("L"):
                    sk.inc_2()
                    #log.debug("2-11: except at line %d", curr_token[2][0])
                elif token_string.startswith("0o") or token_string.startswith("0O"):
                    sk.inc_3()
                    #log.debug("3-12: except at line %d", curr_token[2][0])
                elif _octal_pattern.match(token_string):
                    sk.inc_2()
                    #log.debug("2-13: except at line %d", curr_token[2][0])
            elif token_type == tokenize.OP:
                if token_string in ("<>", '`'):
                    sk.inc_2()
            elif token_type == tokenize.STRING and token_string[0] in ('u', 'U'):
                sk.inc_2()
        except StopIteration:
            break
    textWrapper.close()
    return sk.score()
    
def isPython3(buffer):
    scores = getScores(buffer)
    return scores[1] > scores[0]

def _stringify(buffer):
    from koUnicodeEncoding import autoDetectEncoding
    encoded, encoding, bom = autoDetectEncoding(buffer)
    try:
        text = str(encoded)
    except UnicodeDecodeError:
        log.debug("Couldn't get a str(...) of %d chars, encoding %s",
                  len(encoded), encoding)
        return -1
    return text

def getScores(buffer):
    """Return a 2-tuple (python-2-score, python-3-score) indicating hits of
    constructs for that particular language in the given buffer. If there is
    an error calculating this returns (0, 0).
    
    TODO: This should take an encoding arg, rather than guessing again.
    """
    text = _stringify(buffer)
    if text == -1:
        return (0, 0)
    f = _FileWrapper()
    f.set_text(text)
    scores = _calc_py2_py3_scores(f)
    log.debug("Python2: %d, Python3: %d", scores[0], scores[1])
    return scores

    
if __name__ == '__main__':
    import os
    logging.basicConfig()
    f = _FileWrapper()
    if len(sys.argv) == 1:
        code = """\
def foo():
    try:
        pass
     TestSkipped:   # this causes tokenize to raise IndentationError
        pass
"""
        f.set_text(code)
        # f.set_stdin()
        print _calc_py2_py3_scores(f)
    else:
        import os
        for path in sys.argv[1:]:
            if not os.path.isfile(path):
                continue
            f.set_file(path)
            print "%s: %r" % (path, _calc_py2_py3_scores(f))
