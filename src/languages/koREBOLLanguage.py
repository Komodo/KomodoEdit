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

# see http://www.rebol.com/
class koREBOLLanguage(KoLanguageBase):
    name = "REBOL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7DA39DE8-53ED-11DA-9186-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    commentDelimiterInfo = {
        "line": [ ";", ";;" ]
    }

    defaultExtension = ".r" 

    supportsSmartIndent = "brace"
    # Scintilla bug https://sourceforge.net/tracker/index.php?func=detail&aid=2710475&group_id=2439&atid=102439:
    # Rebol brackets are colored as default
    _lineup_styles = (components.interfaces.ISciMoz.SCE_REBOL_DEFAULT,)
    _lineup_chars = "()[]"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_REBOL

    _stateMap = {
        'default': ('SCE_REBOL_DEFAULT',),
        'keywords': ('SCE_REBOL_WORD', 'SCE_REBOL_WORD2', 'SCE_REBOL_WORD3',
                     'SCE_REBOL_WORD4', 'SCE_REBOL_WORD5', 'SCE_REBOL_WORD6',
                     'SCE_REBOL_WORD7', 'SCE_REBOL_WORD8',),
        'identifiers': ('SCE_REBOL_IDENTIFIER',),
        'comments': ('SCE_REBOL_COMMENTLINE','SCE_REBOL_COMMENTBLOCK',),
        'operators': ('SCE_REBOL_OPERATOR', ),
        'numbers': ('SCE_REBOL_NUMBER', ),
        'strings': ('SCE_REBOL_CHARACTER', 'SCE_REBOL_QUOTEDSTRING',
                    'SCE_REBOL_BRACEDSTRING',),
        'variables': ('SCE_REBOL_PAIR', 'SCE_REBOL_TUPLE', 'SCE_REBOL_BINARY',
                      'SCE_REBOL_MONEY', ),
        'preface': ('SCE_REBOL_PREFACE',),
        'date': ('SCE_REBOL_DATE',),
        'time': ('SCE_REBOL_TIME',),
        'issue': ('SCE_REBOL_ISSUE',),
        'tag': ('SCE_REBOL_TAG',),
        'file': ('SCE_REBOL_FILE',),
        'email': ('SCE_REBOL_EMAIL',),
        'url': ('SCE_REBOL_URL',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer


    #  http://www.rebol.com/docs/dictionary.html
    _keywords = """
        about abs absolute add
        alert alias all alter and
        any any-block? any-function? any-string? any-type?
        any-word? append arccosine arcsine arctangent
        array as-pair ask at attempt
        back binary? bind bitset? block?
        break brightness? browse build-tag caret-to-offset
        catch center-face change change-dir char?
        charset checksum choose clean-path clear
        clear-fields close comment complement component?
        compose compress confirm connected? construct
        context copy cosine datatype? date?
        debase decimal? decode-cgi decompress dehex
        delete detab difference dir? dirize
        disarm dispatch divide do do-events
        does dump-face dump-obj echo either
        else email? empty? enbase entab
        equal? error? even? event? exclude
        exists? exit exp extract fifth
        file? find first flash focus
        for forall foreach forever form
        forskip found? fourth free func
        function function? get get-modes get-word?
        greater-or-equal? greater? halt has hash?
        head head? help hide hide-popup
        if image? import-email in in-window?
        index? info? inform input input?
        insert integer? intersect issue? join
        last launch layout length? lesser-or-equal?
        lesser? library? license link? list-dir
        list? lit-path? lit-word? load load-image
        log-10 log-2 log-e logic? loop
        lowercase make make-dir make-face max
        maximum maximum-of min minimum minimum-of
        modified? mold money? multiply native?
        negate negative? next none? not
        not-equal? now number? object? odd?
        offset-to-caret offset? op? open or
        pair? paren? parse parse-xml path?
        pick poke port? positive? power
        prin print probe protect protect-system
        query quit random read read-io
        recycle reduce refinement? reform rejoin
        remainder remold remove remove-each rename
        repeat repend replace request request-color
        request-date request-download request-file request-list request-pass
        request-text resend return reverse routine?
        same? save script? second secure
        select send series? set set-modes
        set-net set-path? set-word? show show-popup
        sign? sine size-text size? skip
        sort source span? split-path square-root
        strict-equal? strict-not-equal? string? struct? stylize
        subtract suffix? switch tag? tail
        tail? tangent third throw time?
        to to-binary to-bitset to-block to-char
        to-date to-decimal to-email to-file to-get-word
        to-hash to-hex to-idate to-image to-integer
        to-issue to-list to-lit-path to-lit-word to-local-file
        to-logic to-money to-pair to-paren to-path
        to-rebol-file to-refinement to-set-path to-set-word to-string
        to-tag to-time to-tuple to-url to-word
        trace trim try tuple? type?
        unfocus union unique unprotect unset
        unset? until unview update upgrade
        uppercase url? usage use value?
        view viewed? wait what what-dir
        while within? word? write write-io xor zero?

        action? any-block? any-function? any-string?
        any-type? any-word? binary? bitset? block? char? component? connected?
        datatype? date? decimal? dir? email? empty? equal? error? even? event? exists?
        file? found? function? get-word? greater-or-equal greater? hash? head? image?
        index? info? input? integer? issue? length? lesser-or-equal? lesser? library?
        link-app? link? list? lit-path? lit-word? logic? modified? money? native? negative?
        none? not-equal? number? object? odd? offset? op? pair? paren? path? port?
        positive? rebol-command? rebol-encap? rebol-link? rebol-pro? rebol-view?
        refinement? routine? same? script? series? set-path? set-word? sign? size?
        strict-equal? strict-not-equal string? struct? suffix? tag? tail? time? tuple? type?
        unset? url? value? view? word? zero?

        action! any-block! any-function! any-string! any-type!
        any-word! binary! bitset! block! char! datatype! date! decimal! email! error!
        event! file! function! get-word! hash! image! integer! issue! library! list! lit-path!
        lit-word! logic! money! native! none! number! object! op! pair! paren! path!
        port! refinement! routine! series! set-path! set-word! string! struct! symbol! tag!
        time! tuple! unset! url! word!
    """.split()
    
