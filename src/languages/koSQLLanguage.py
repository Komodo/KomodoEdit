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

def registerLanguage(registery):
    registery.registerLanguage(koSQLLanguage())
    registery.registerLanguage(koPLSQLLanguage())
    
class koSQLLanguage(KoLanguageBase):
    name = "SQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{EC1B0777-D982-41af-906F-34923D602B72}"

    _stateMap = {
        'default': ('SCE_SQL_DEFAULT',),
        'identifiers': ('SCE_SQL_IDENTIFIER',),
        'keywords': ('SCE_SQL_WORD',
                     'SCE_SQL_WORD2',
                     ),
        'comments': ('SCE_SQL_COMMENT',
                     'SCE_SQL_COMMENTLINE',
                     'SCE_SQL_COMMENTLINEDOC',
                     'SCE_SQL_COMMENTDOC',
                     'SCE_SQL_COMMENTDOCKEYWORD',
                     'SCE_SQL_COMMENTDOCKEYWORDERROR',
                     'SCE_SQL_SQLPLUS_COMMENT',
                     ),
        'numbers': ('SCE_SQL_NUMBER',),
        'strings': ('SCE_SQL_STRING',
                    'SCE_SQL_CHARACTER',
                    ),
        'operators': ('SCE_SQL_OPERATOR',),
        }
    defaultExtension = ".sql"
    commentDelimiterInfo = {
        "line": [ "--" ],
        "block": [ ("/*", "*/") ],
    }

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_SQL_COMMENT]
            )
        del self.matchingSoftChars['"']
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_SQL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

    # LexSQL seems to ignore keywords completely
    _keywords = """absolute action add admin after aggregate
        alias all allocate alter and any are array as asc
        assertion at authorization
        before begin binary bit blob boolean both breadth by
        call cascade cascaded case cast catalog char character
        check class clob close collate collation column commit
        completion connect connection constraint constraints
        constructor continue corresponding create cross cube current
        current_date current_path current_role current_time current_timestamp
        current_user cursor cycle
        data date day deallocate dec decimal declare default
        deferrable deferred delete depth deref desc describe descriptor
        destroy destructor deterministic dictionary diagnostics disconnect
        distinct domain double drop dynamic
        each else end end-exec equals escape every except
        exception exec execute external
        false fetch first float for foreign found from free full
        function
        general get global go goto grant group grouping
        having host hour
        identity if ignore immediate in indicator initialize initially
        inner inout input insert int integer intersect interval
        into is isolation iterate
        join
        key
        language large last lateral leading left less level like
        limit local localtime localtimestamp locator
        map match minute modifies modify module month
        names national natural nchar nclob new next no none
        not null numeric
        object of off old on only open operation option
        or order ordinality out outer output
        pad parameter parameters partial path postfix precision prefix
        preorder prepare preserve primary
        prior privileges procedure public
        read reads real recursive ref references referencing relative
        restrict result return returns revoke right
        role rollback rollup routine row rows
        savepoint schema scroll scope search second section select
        sequence session session_user set sets size smallint some| space
        specific specifictype sql sqlexception sqlstate sqlwarning start
        state statement static structure system_user
        table temporary terminate than then time timestamp
        timezone_hour timezone_minute to trailing transaction translation
        treat trigger true
        under union unique unknown
        unnest update usage user using
        value values varchar variable varying view
        when whenever where with without work write
        year
        zone""".split()

class koPLSQLLanguage(koSQLLanguage):
    name = "PL-SQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{543492ec-bdb7-4724-b4ea-482b777d07b4}"

    _stateMap = {
        'comments': ('SCE_SQL_COMMENTLINE',
                     'SCE_SQL_COMMENT',
                     ),
    }

    _keywords = """all alter and any array as asc at authid avg begin between
        binary_integer
        body boolean bulk by char char_base check close cluster collect
        comment commit compress connect constant create current currval
        cursor date day declare decimal default delete desc distinct
        do drop else elsif end exception exclusive execute exists exit
        extends false fetch float for forall from function goto group
        having heap hour if immediate in index indicator insert integer
        interface intersect interval into is isolation java level like
        limited lock long loop max min minus minute mlslabel mod mode
        month natural naturaln new nextval nocopy not nowait null number
        number_base ocirowid of on opaque open operator option or order
        organization others out package partition pctfree pls_integer
        positive positiven pragma prior private procedure public raise
        range raw real record ref release return reverse rollback row
        rowid rownum rowtype savepoint second select separate set share
        smallint space sql sqlcode sqlerrm start stddev subtype successful
        sum synonym sysdate table then time timestamp to trigger true
        type uid union unique update use user validate values varchar
        varchar2 variance view when whenever where while with work write
        year zone""".split()

