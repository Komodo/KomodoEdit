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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2012
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

import re, os, sys
from xpcom import components, ServerException
import logging
from koLintResult import runGenericLinter
import process

from koLanguageKeywordBase import KoLanguageKeywordBase
from koLanguageServiceBase import KoLexerLanguageService

log = logging.getLogger("koBashLanguage")
#log.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz

class koBashLanguage(KoLanguageKeywordBase):
    name = "Bash"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{728daa03-1f7a-4eef-bb7b-de7b322825fa}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'operators': ('SCE_SH_OPERATOR',
                      'SCE_SH_BACKTICKS',),
        'parameters': ('SCE_SH_PARAM',),
        'errors': ('SCE_SH_ERROR',),
        'variables': ('SCE_SH_SCALAR',),
        'default': ('SCE_SH_DEFAULT',),
        'numbers': ('SCE_SH_NUMBER',),
        'identifiers': ('SCE_SH_IDENTIFIER',),
        'strings': ('SCE_SH_CHARACTER',
                    'SCE_SH_STRING',),
        'here documents': ('SCE_SH_HERE_DELIM',
                           'SCE_SH_HERE_Q',),
        'comments': ('SCE_SH_COMMENTLINE',),
        'keywords': ('SCE_SH_WORD',),
        }
    defaultExtension = '.sh'
    commentDelimiterInfo = {"line": [ "#" ],}
    shebangPatterns = [
        re.compile(ur'\A#!.*/(ba)?sh.*$', re.IGNORECASE | re.MULTILINE),
    ]
    
    # Ignore parens due to case statements.
    _lineup_chars = u"{}"
    _lineup_open_chars = "{"
    _lineup_close_chars = "}"

    supportsSmartIndent = "keyword"
    # 'then' is kind of weird, but can be treated just like 'else'
    _indenting_statements = ['if', 'for', 'until', 'while', 'else', 'then', 'do']
    _dedenting_statements = ['break', 'continue', 'return']
    # These trigger a dedent when entered, but then count +1
    # This might be better than putting 'else' in both
    # _indenting_statements and _keyword_dedenting_keywords
    
    # Don't count 'esac' as a dedenter because case stmts need to get
    # indented with ")" and ";;"
    _keyword_dedenting_keywords = ['done', 'fi', 'else', 'then', 'do']
    searchURL = "http://www.gnu.org/software/bash/manual/html_node"
    
    sample = """# build our tags file

find src \( \( -name '*.h' \) -o \\
           \( -name '*.cpp' \) -o \\
           \( -name '*.c' \) -o \\
           \( -name '*.cxx' \) -o \\
            -exec ls -1 `pwd`/{} \; | 
sed -e 's@/cygdrive/c@c:@' -e 's@/\./@/@' | 
perl -n -e 'chomp; printf(qq(%c%c%s,1%c), 12, 10, $_, 10);' > TAGS
"""

    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_SH_OPERATOR],
            _variable_styles = [sci_constants.SCE_SH_IDENTIFIER,
                                sci_constants.SCE_SH_SCALAR],
            _lineup_close_styles = [sci_constants.SCE_SH_OPERATOR],
            _lineup_styles = [sci_constants.SCE_SH_OPERATOR],
            _multiline_styles = [sci_constants.SCE_SH_STRING,
                                 sci_constants.SCE_SH_CHARACTER],
            _keyword_styles = [sci_constants.SCE_SH_WORD],
            _default_styles = [sci_constants.SCE_SH_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_SH_ERROR,
                                 sci_constants.SCE_SH_COMMENTLINE,
                                 sci_constants.SCE_SH_NUMBER],
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_BASH)
            self._lexer.setKeywords(0, self.bash_keywords1 + self.bash_keywords2)
            self._lexer.supportsFolding = 1
        return self._lexer

    bash_keywords1="""alias
        ar asa awk banner basename bash bc bdiff break
        bunzip2 bzip2 cal calendar case cat cc cd chmod cksum
        clear cmp col comm compress continue cp cpio crypt
        csplit ctags cut date dc dd declare deroff dev df diff diff3
        dircmp dirname do done du echo ed egrep elif else env
        esac eval ex exec exit expand export expr false fc
        fgrep fi file find fmt fold for function functions
        getconf getopt getopts grep gres hash head help
        history iconv id if in integer jobs join kill local lc
        let line ln logname look ls m4 mail mailx make
        man mkdir more mt mv newgrp nl nm nohup ntps od
        pack paste patch pathchk pax pcat perl pg pr print
        printf ps pwd read readonly red return rev rm rmdir
        sed select set sh shift size sleep sort spell
        split start stop strings strip stty sum suspend
        sync tail tar tee test then time times touch tr
        trap true tsort tty type typeset ulimit umask unalias
        uname uncompress unexpand uniq unpack unset until
        uudecode uuencode vi vim vpax wait wc whence which
        while who wpaste wstart xargs zcat""".split()
    
    bash_keywords2="""chgrp chown chroot dir dircolors
        factor groups hostid install link md5sum mkfifo
        mknod nice pinky printenv ptx readlink seq
        sha1sum shred stat su tac unlink users vdir whoami yes""".split()

class KoBashLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_clsid_ = "{6da201cd-5507-4cdd-a180-746c011d16d5}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Bash;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Bash'),
         ]
    
    def __init__(self):
        if sys.platform.startswith("win"):
            self._bash = None
        elif os.path.exists("/bin/bash"):
            self._bash = "/bin/bash"
        elif os.path.exists("/bin/sh"):
            self._bash = "/bin/sh"
        else:
            self._bash = None
        if self._bash:
            self._cmd_start = [self._bash, "-n"]
    
    def lint(self, request):
        if self._bash is None:
            return
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text_aux(request, text)
        
    def lint_with_text(self, request, text):
        """This routine exists only if someone uses bash in a multi-lang document
        """
        if self._bash is None:
            return
        return self.lint_with_text_aux(request, text)
    
    _ptn_err = re.compile(r'.*?:\s+line\s+(\d+):\s+(syntax\s+error\b.*)')
    def lint_with_text_aux(self, request, text):
        cwd = request.cwd or None
        extension = ".sh"
        return runGenericLinter(text, extension, self._cmd_start,
                                [self._ptn_err], [],
                                cwd=cwd, useStderr=True)
