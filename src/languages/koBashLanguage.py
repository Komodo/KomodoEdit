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
    registery.registerLanguage(koBashLanguage())

class koBashLanguage(KoLanguageBase):
    name = "Bash"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{728daa03-1f7a-4eef-bb7b-de7b322825fa}"

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
    
    sample = """# build our tags file

find src \( \( -name '*.h' \) -o \\
           \( -name '*.cpp' \) -o \\
           \( -name '*.c' \) -o \\
           \( -name '*.cxx' \) -o \\
            -exec ls -1 `pwd`/{} \; | 
sed -e 's@/cygdrive/c@c:@' -e 's@/\./@/@' | 
perl -n -e 'chomp; printf(qq(%c%c%s,1%c), 12, 10, $_, 10);' > TAGS
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_BASH)
            self._lexer.setKeywords(0, self.bash_keywords1 + self.bash_keywords2)
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
