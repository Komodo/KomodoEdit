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
                        curr_token = safe_get_next_token(tok_gen)
                        token_type, token_string, start_tup, end_tup, line = curr_token
                        if token_type == tokenize.OP:
                            if token_string == '=':
                                sk.inc_3() # using print as a variable, assignment
                            elif curr_keyword == "print" and token_string in ("<<", ">>"):
                                sk.inc_2()
                        else:
                            sk.inc_2() # print/exec without open paren
                            if at_stmt_end(token_type, token_string):
                                at_line_start = True
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
                            # Do nothing here, since 'except ... as' is in
                            # Python 2.6, although not earlier versions.
                            pass
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

class JavaScriptDistinguisher(object):
    # lexing states:
    ST_DEFAULT = 0
    ST_IN_STRING = 1
    ST_IN_COMMENT = 2
    ST_IN_NAME = 3
    ST_IN_NUMBER = 4
    ST_IN_OPERATOR = 5
    ST_IN_COMMENTBLOCK = 6
    _node_hash_bang_re = re.compile(r'#!/.+node\b')
    # Things that indicate JS:
    # document....(...)
    # alert....(...)
    
    # Things that indicate node.js:
    # hashbang: #!/usr/bin/env node
    # hashbang: #!/...node\b
    # require(...)
    # module.exports
    # <name>.on(string, )
    
    # If a transition goes to state -1, accept it.  True => JS, False => Node
    _stateMachine = {
        0: [
            (ST_IN_NAME, 'document', 101),
            (ST_IN_NAME, 'alert', 201),
            (ST_IN_NAME, 'require', 301),
            (ST_IN_NAME, 'module', 401),
            (ST_IN_NAME, None, 501),
        ],
        101: [(ST_IN_OPERATOR, ".", 102),],
        102: [(ST_IN_NAME, None, -1, True),],
            
        201: [(ST_IN_OPERATOR, "(", 202),],
        202: [(ST_IN_NAME, None, -1, True),
              (ST_IN_STRING, None, -1, True),
            ],
        301: [(ST_IN_OPERATOR, "(", 302),],
        302: [(ST_IN_STRING, None, -1, False),],
            
        401: [(ST_IN_OPERATOR, ".", 402),],
        402: [(ST_IN_NAME, 'exports', -1, False),],
            
        501: [(ST_IN_OPERATOR, ".", 502),],
        502: [(ST_IN_NAME, 'on', 503),],
        503: [(ST_IN_OPERATOR, "(", 504),],
        504: [(ST_IN_STRING, None, 505),],
        505: [(ST_IN_OPERATOR, ",", -1, False),],
    }
    _type_str = type("")
    _type_re = type(re.compile(""))
    
    def _transitionState(self, tokState, tokString):
        try:
            matches = self._stateMachine[self.parseState]
        except KeyError:
            log.exception("Bad parseState of %d", self.parseState)
            self.parseState = 0
            return
        initState = self.parseState
        for matcher in matches:
            matchState = matcher[0]
            if matchState == tokState:
                matchArg = matcher[1]
                if (matchArg is None
                    or (type(matchArg) == self._type_str and matchArg == tokString)
                    or (type(matchArg) == self._type_re and matchArg.match(tokString))):
                    newState = matcher[2]
                    if newState == -1:
                        # Found a match, update scores, state, return
                        self.parseState = 0
                        score = matcher[3]
                        if score:
                            self.scores[0] += 1
                        else:
                            self.scores[1] += 1
                    else:
                        self.parseState = newState
                    return
        if initState != 0:
            # We rejected this token, but check to see if it can start a new sequence.
            self.parseState = 0
            self._transitionState(tokState, tokString)
    
    def isNodeJS(self, buffer):
        if len(buffer) < 4:
            return False
        if self._node_hash_bang_re.match(buffer):
            return True
        lineNo = 1
        lim = len(buffer)
        lim3 = lim - 3
        state = self.ST_DEFAULT
        currToken = None
        i = 0
        self.scores = [0, 0]
        lineTokens = []
        self.parseState = 0
        c_next = buffer[0]
        c_next2 = buffer[1]
        while i < lim3:
            c = c_next
            c_next = c_next2
            c_next2 = buffer[i + 2]
            if c == "\n":
                lineNo += 1
                if abs(self.scores[0] - self.scores[1]) > 10:
                    break
                if lineNo >= 100:
                    break
            if state == self.ST_DEFAULT:
                if c == '/' and c_next == '/':
                    state = self.ST_IN_COMMENT
                    bufStart = i
                elif c == '/' and c_next == '*':
                    state = self.ST_IN_COMMENTBLOCK
                    bufStart = i
                    i += 1; c_next = c_next2; c_next2 = buffer[i + 3]
                elif c == '#' and c_next == '!' and lineNo <= 2:
                    state = self.ST_IN_COMMENT # Fake
                    bufStart = i
                elif c in ('\'', '"'):
                    state = self.ST_IN_STRING
                    strStart = c
                    bufStart = i + 1
                elif c.isalpha() or c == "_":
                    if not c_next.isalnum():
                        # Handle one-char names here
                        self._transitionState(self.ST_IN_NAME, c)
                    else:
                        state = self.ST_IN_NAME
                        bufStart = i
                elif c.isdigit():
                    if not c_next.isdigit():
                        # Handle one-digit numbers here
                        self._transitionState(self.ST_IN_NUMBER, c)
                    else:
                        state = self.ST_IN_NUMBER
                        bufStart = i
                elif not c.isspace():
                    self._transitionState(self.ST_IN_OPERATOR, c)
                else:
                    # Don't bother processing regex'es.  If we get out of sync
                    # with a string, we'll stop at end of line.  If the regex
                    # includes a '/*', we lose.
                    pass
            elif state == self.ST_IN_STRING:
                if c == '\\' and c_next != '\n':
                    # Before:
                    # c == buffer[i]
                    # c_next == buffer[i + 1]
                    # c_next2 == buffer[i + 2]
                    # After:
                    # c == buffer[i + 1] == c_next
                    # c_next == buffer[i + 2] = c_next2
                    # c_next2 == buffer[i + 3]
                    # i < lim3 == len(buffer) - 3, so we're ok
                    c_next = c_next2;
                    c_next2 = buffer[i + 3]
                    i += 1
                elif c == strStart:
                    currToken = buffer[bufStart: i]
                    self._transitionState(self.ST_IN_STRING, currToken)
                    state = self.ST_DEFAULT
                elif c_next == "\n":
                    currToken = buffer[bufStart: i + 1]
                    self._transitionState(self.ST_IN_STRING, currToken)
                    state = self.ST_DEFAULT
            elif state == self.ST_IN_COMMENT:
                if c_next == "\n":
                    currToken = buffer[bufStart: i + 1]
                    self._transitionState(self.ST_IN_COMMENT, currToken)
                    state = self.ST_DEFAULT
            elif state == self.ST_IN_COMMENTBLOCK:
                if c == "*" and c_next == "/":
                    currToken = buffer[bufStart: i + 2]
                    self._transitionState(self.ST_IN_COMMENTBLOCK, currToken)
                    state = self.ST_DEFAULT
                    i += 1; c_next = c_next2; c_next2 = buffer[i + 1]
            elif state == self.ST_IN_NAME and not c_next.isalnum():
                    currToken = buffer[bufStart: i + 1]
                    self._transitionState(self.ST_IN_NAME, currToken)
                    state = self.ST_DEFAULT
            elif state == self.ST_IN_NUMBER and not c_next.isdigit():
                    currToken = buffer[bufStart: i + 1]
                    self._transitionState(self.ST_IN_NUMBER, currToken)
                    state = self.ST_DEFAULT
            i += 1
        return self.scores[0] < self.scores[1] # js wins ties


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
