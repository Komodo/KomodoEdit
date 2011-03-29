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

from xpcom import components, ServerException

from koLanguageServiceBase import *

class koLispLanguage(KoLanguageBase):
    name = "Lisp"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7B60D626-E3E9-4634-9531-854DF66B1193}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".lis"
    commentDelimiterInfo = {
        "line": [ ";" ],
    }
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_LISP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """not defun + - * / = < > <= >= princ
        eval apply funcall quote identity function complement backquote
        lambda set setq setf defun defmacro gensym make symbol intern symbol
        name symbol value symbol plist get getf putprop remprop hash make array
        aref car cdr caar cadr cdar cddr caaar caadr cadar
        caddr cdaar cdadr cddar cdddr caaaar caaadr caadar caaddr cadaar cadadr
        caddar cadddr cdaaar cdaadr cdadar cdaddr cddaar cddadr cdddar cddddr
        cons list append reverse last nth nthcdr member assoc subst sublis
        nsubst  nsublis remove length list length mapc mapcar mapl maplist
        mapcan mapcon rplaca rplacd nconc delete atom symbolp numberp
        boundp null listp consp minusp zerop plusp evenp oddp eq eql equal
        cond case and or let l if prog prog1 prog2 progn go return do dolist
        dotimes catch throw error cerror break continue errset baktrace evalhook
        truncate float rem min max abs sin cos tan expt exp sqrt
        random logand logior logxor lognot bignums logeqv lognand lognor
        logorc2 logtest logbitp logcount integer length nil""".split()

class koSchemeLanguage(koLispLanguage):
    name = "Scheme"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7463ae07-1bec-4ae2-9c7a-9f5a6877b63b}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".scm" #*.scm;*.smd;*.ss

    _keywords = """+ - * / = < > <= >= =>
abs acos and angle append apply asin assoc assoc assq assv atan
begin boolean?
caar cadr call-with-current-continuation call/cc
call-with-input-file call-with-output-file call-with-values
car cdr
caar cadr cdar cddr
caaar caadr cadar caddr cdaar cdadr cddar cdddr
caaaar caaadr caadar caaddr cadaar cadadr caddar cadddr
cdaaar cdaadr cdadar cdaddr cddaar cddadr cdddar cddddr
case ceiling char->integer
char-alphabetic? char-ci<=? char-ci<? char-ci=? char-ci>=? char-ci>?
char-downcase char-lower-case? char-numeric? char-ready?
char-upcase char-upper-case? char-whitespace?
char<=? char<? char=? char>=? char>? char?
close-input-port close-output-port complex? cond cons cos
current-input-port current-output-port
define define-syntax delay denominator display do dynamic-wind
else eof-object? eq? equal? eqv? eval even? exact->inexact exact?
exp expt
floor for-each force
gcd
if imag-part inexact->exact inexact? input-port? integer->char integer? interaction-environment
lambda lcm length let let* let-syntax letrec letrec-syntax
list list->string list->vector list-ref list-tail list? load log
magnitude make-polar make-rectangular make-string make-vector
map max member memq memv min modulo
negative? newline not null-environment null? number->string number? numerator
odd? open-input-file open-output-file or output-port?
pair? peek-char input-port? output-port? positive? procedure?
quasiquote quote quotient
rational? rationalize read read-char real-part real? remainder reverse round
scheme-report-environment set! set-car! set-cdr! sin sqrt string
string->list string->number string->symbol string-append
string-ci<=? string-ci<? string-ci=? string-ci>=? string-ci>?
string-copy string-fill! string-length string-ref string-set!
string<=? string<? string=? string>=? string>? string?
substring symbol->string symbol? syntax-rules
transcript-off transcript-on truncate
unquote unquote-splicing
values vector vector->list vector-fill! vector-length vector-ref vector-set! vector?
with-input-from-file with-output-to-file write write-char
zero?""".split()