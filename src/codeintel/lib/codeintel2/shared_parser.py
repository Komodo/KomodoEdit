# Copyright (c) 2006 ActiveState Software Inc.
#
# Contributors:
#   Eric Promislow (EricP@ActiveState.com)
#

""" Many CILE parsers have to allow for tokens to arrive with
either native Scintilla types, or UDL types (and there might be
more in the future.

This module defines the abstraction layer over the UDL types.

Some routines can't fulfill a request just by looking at the type,
and need to examine the actual text of the token.  But a common
UDL layer can't do that, as each SSL language has different properties.
So callbacks that return to the SSL CILE are used for that purpose.

See ruby_parser.py for examples on writing callbacks for
get_builtin_type, is_interpolating_string, and
tokenStyleToContainerStyle (if any of these are called, that is).

"""
import re

from SilverCity import Ruby, ScintillaConstants

GENERIC_TYPE_UNKNOWN = 0
GENERIC_TYPE_NUMBER = 1
GENERIC_TYPE_STRING = 2
GENERIC_TYPE_REGEX = 3

class CommonClassifier:
    _quote_patterns = {}    

    def get_quote_patterns(self, tok, callback=None):
        ttype = tok.style
        if self._quote_patterns.has_key(ttype):
            return [self._quote_patterns[ttype]]
        elif callback:
            return callback(tok)
        else:
            return self._quote_patterns.values()

    def is_identifier_or_keyword(self, tok):
        return self.is_identifier(tok, True)


class UDLClassifier(CommonClassifier):
    def get_builtin_type(self, tok, callback):
        if self.is_number(tok):
            return callback(tok, GENERIC_TYPE_NUMBER)
        elif self.is_string(tok):
            return callback(tok, GENERIC_TYPE_STRING)
        elif tok.style == ScintillaConstants.SCE_UDL_SSL_REGEX:
            return callback(tok, GENERIC_TYPE_REGEX)
        else:
            return callback(tok, GENERIC_TYPE_UNKNOWN)

    def is_any_operator(self, tok):
        return tok.style == ScintillaConstants.SCE_UDL_SSL_OPERATOR

    def is_comment(self, tok):
        return tok.style in (ScintillaConstants.SCE_UDL_SSL_COMMENT,
                             ScintillaConstants.SCE_UDL_SSL_COMMENTBLOCK)

    def is_comment_structured(self, tok, callback):
        return self.is_comment(tok) and callback and callback(tok)

    def is_identifier(self, tok, allow_keywords=False):
        return (tok.style == ScintillaConstants.SCE_UDL_SSL_IDENTIFIER or
            (allow_keywords and
             tok.style == ScintillaConstants.SCE_UDL_SSL_WORD))

    def is_index_op(self, tok, pattern=None):
        if tok.style != ScintillaConstants.SCE_UDL_SSL_OPERATOR:
            return False
        elif not pattern:
            return True
        return len(tok.text) > 0 and pattern.search(tok.text)

    # Everything gets lexed as a string, so we need to look at its structure.
    # We call back to the main CILE parser, which knows more about which kinds
    # of strings can interpolate other values.  This routine assumes all regexes
    # can interpolate.

    def is_interpolating_string(self, tok, callback):
        if tok.style == ScintillaConstants.SCE_UDL_SSL_REGEX:
            return callback(tok, GENERIC_TYPE_REGEX)
        elif not self.is_string(tok):
            return False
        else:
            return callback(tok, GENERIC_TYPE_STRING)
    
    def is_keyword(self, tok, target):
        return tok.style == ScintillaConstants.SCE_UDL_SSL_WORD and tok.text == target

    def is_number(self, tok):
        return tok.style == ScintillaConstants.SCE_UDL_SSL_NUMBER

    def is_operator(self, tok, target):
        return tok.style == ScintillaConstants.SCE_UDL_SSL_OPERATOR and tok.text == target

    def is_string(self, tok):
        return tok.style == ScintillaConstants.SCE_UDL_SSL_STRING

    def is_string_qw(self, tok, callback=None):
        return (tok.style == ScintillaConstants.SCE_UDL_SSL_STRING and
                callback and callback(tok))

    def is_symbol(self, tok, callback=None):
        return (tok.style == ScintillaConstants.SCE_UDL_SSL_STRING and
                callback and callback(tok))

    def is_variable(self, tok):
        return tok.style in (ScintillaConstants.SCE_UDL_SSL_VARIABLE,
                             ScintillaConstants.SCE_UDL_SSL_IDENTIFIER)

    # Types of variables
    def is_variable_array(self, tok, callback=None):
        if not self.is_variable(tok):
            return False
        else:
            return callback and callback(tok)

    def is_variable_scalar(self, tok, callback=None):
        if not self.is_variable(tok):
            return False
        else:
            return callback and callback(tok)

    def tokenStyleToContainerStyle(self, tok, callback):
        return callback(tok, tok.style == ScintillaConstants.SCE_UDL_SSL_VARIABLE)

    # Accessors for where we'd rather work with a style than call a predicate fn

    @property
    def style_identifier(self):
        return ScintillaConstants.SCE_UDL_SSL_IDENTIFIER

    @property
    def style_operator(self):
        return ScintillaConstants.SCE_UDL_SSL_OPERATOR

    @property
    def style_word(self):
        return ScintillaConstants.SCE_UDL_SSL_WORD
