#!python
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

"""Perl-specific Language Services implementations."""

import os, sys
from xpcom import components, ServerException
from koLanguageServiceBase import *
import logging
import pprint
import re

import sciutils


def registerLanguage(registery):
    registery.registerLanguage(KoPerlLanguage())

    

#---- globals

log = logging.getLogger("koPerlLanguage")
#log.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz



#---- internal support routines

def isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def isdigit(char):
    return "0" <= char <= "9"


#---- Language Service component implementations

class KoPerlLanguage(KoLanguageBase):
    name = "Perl"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{911E8F76-C8F9-46f2-A930-1F1693400FCB}"

    modeNames = ['perl']
    shebangPatterns = [re.compile(ur'\A#!.*perl.*$', re.IGNORECASE | re.MULTILINE)]
    primary = 1
    internal = 0
    accessKey = 'p'

    defaultExtension = ".pl"
    # XXX read url from some config file
    downloadURL = 'http://www.ActiveState.com/Products/ActivePerl'
    commentDelimiterInfo = { "line": [ "#" ]  }
    variableIndicators = '$@%'
    namedBlockRE = "^[ \t]*?(sub\s+\w+|package\s+\w)"
    namedBlockDescription = 'Perl subs and packages'

    styleBits = 6      # Override KoLanguageBase.styleBits setting of 5
    indicatorBits = 2  # Currently (2004-05-25) Same as base class

    
    _lineup_chars = u"{}()[]"
    _lineup_open_chars = "([{" # Perl tells the difference between the indent and lineup {}'s
    _lineup_close_chars = ")]}"

    supportsSmartIndent = "brace"
    sample = r"""#  Fruit salad recipe
my %salad;
while (<DATA>) {
	$salad{$1} = $2 if /^([a-z]+)\s+(\d+)/;
}
my @fruits = keys %salad;
foreach (@fruits) {
	my $fruit = $_;
	$fruit =~ s/s$// if $salad{$_} == 1;
	print "$salad{$_} $fruit\n";
}
print <<_HERE_DOC_
Cut and stir the fruit.
_HERE_DOC_
__DATA__
apples 2
pears 1
oranges 3
"""

    styleStdin = sci_constants.SCE_PL_STDIN
    styleStdout = sci_constants.SCE_PL_STDOUT
    styleStderr = sci_constants.SCE_PL_STDERR

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_PL_OPERATOR],
            _lineup_close_styles = [sci_constants.SCE_PL_OPERATOR,
                                    sci_constants.SCE_PL_VARIABLE_INDEXER,
                                    sci_constants.SCE_PL_REGEX,
                                    sci_constants.SCE_PL_REGSUBST],
            _lineup_styles = [sci_constants.SCE_PL_OPERATOR,
                              sci_constants.SCE_PL_VARIABLE_INDEXER,
                              sci_constants.SCE_PL_REGEX,
                              sci_constants.SCE_PL_REGSUBST],
            _variable_styles = [sci_constants.SCE_PL_SCALAR,
                                sci_constants.SCE_PL_ARRAY,
                                sci_constants.SCE_PL_HASH,
                                sci_constants.SCE_PL_SYMBOLTABLE,
                                sci_constants.SCE_PL_VARIABLE_INDEXER],
            )
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)
        self.matchingSoftChars["/"] = ("/", self.softchar_accept_matching_forward_slash)
        self.matchingSoftChars["("] = (")", self.softchar_check_special_then_return_char)
        self.matchingSoftChars["["] = ("]", self.softchar_check_special_then_return_char)
        
    def getVariableStyles(self):
        return self._style_info._variable_styles

    def getLanguageService(self, iid):
        return KoLanguageBase.getLanguageService(self, iid)

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_PERL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    if 1:
        # The new autocomplete/calltip functionality based on the codeintel
        # system.
        def get_codeintelcompleter(self):
            if self._codeintelcompleter is None:
                self._codeintelcompleter =\
                    components.classes["@activestate.com/koPerlCodeIntelCompletionLanguageService;1"]\
                    .getService(components.interfaces.koICodeIntelCompletionLanguageService)
                self._codeintelcompleter.initialize(self)
                # Ensure the service gets finalized when Komodo shutsdown.
                finalizeSvc = components.classes["@activestate.com/koFinalizeService;1"]\
                    .getService(components.interfaces.koIFinalizeService)
                finalizeSvc.registerFinalizer(self._codeintelcompleter)
            return self._codeintelcompleter
    else:
        def get_completer(self):
            if self._completer is None:
                self._completer = components.classes["@activestate.com/koPerlCompletionLanguageService;1"].getService(components.interfaces.koICompletionLanguageService)
            return self._completer

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter = components.classes["@activestate.com/koAppInfoEx?app=Perl;1"].getService()
        return self._interpreter

    _keywords = [
                 "__DATA__",
                 "__END__",
                 "__FILE__",
                 "__LINE__",
                 "__PACKAGE__",
                 "AUTOLOAD",
                 "BEGIN",
                 "CHECK",
                 "CORE",
                 "DESTROY",
                 "END",
                 "INIT",
                 "UNITCHECK",
                 "abs",
                 "accept",
                 "alarm",
                 "and",
                 "atan2",
                 "bind",
                 "binmode",
                 "bless",
                 "break",
                 "caller",
                 "chdir",
                 "chmod",
                 "chomp",
                 "chop",
                 "chown",
                 "chr",
                 "chroot",
                 "close",
                 "closedir",
                 "cmp",
                 "connect",
                 "continue",
                 "cos",
                 "crypt",
                 "dbmclose",
                 "dbmopen",
                 "default",
                 "defined",
                 "delete",
                 "die",
                 "do",
                 "dump",
                 "each",
                 "else",
                 "elsif",
                 "endgrent",
                 "endhostent",
                 "endnetent",
                 "endprotoent",
                 "endpwent",
                 "endservent",
                 "eof",
                 "eq",
                 "eval",
                 "exec",
                 "exists",
                 "exit",
                 "exp",
                 "fcntl",
                 "fileno",
                 "flock",
                 "for",
                 "foreach",
                 "fork",
                 "format",
                 "formline",
                 "ge",
                 "getc",
                 "getgrent",
                 "getgrgid",
                 "getgrnam",
                 "gethostbyaddr",
                 "gethostbyname",
                 "gethostent",
                 "getlogin",
                 "getnetbyaddr",
                 "getnetbyname",
                 "getnetent",
                 "getpeername",
                 "getpgrp",
                 "getppid",
                 "getpriority",
                 "getprotobyname",
                 "getprotobynumber",
                 "getprotoent",
                 "getpwent",
                 "getpwnam",
                 "getpwuid",
                 "getservbyname",
                 "getservbyport",
                 "getservent",
                 "getsockname",
                 "getsockopt",
                 "given",
                 "glob",
                 "gmtime",
                 "goto",
                 "grep",
                 "gt",
                 "hex",
                 "if",
                 "import",
                 "include",
                 "index",
                 "int",
                 "ioctl",
                 "join",
                 "keys",
                 "kill",
                 "last",
                 "lc",
                 "lcfirst",
                 "le",
                 "length",
                 "link",
                 "listen",
                 "local",
                 "localtime",
                 "lock",
                 "log",
                 "lstat",
                 "lt",
                 "m",
                 "map",
                 "mkdir",
                 "msgctl",
                 "msgget",
                 "msgrcv",
                 "msgsnd",
                 "my",
                 "ne",
                 "new",
                 "next",
                 "no",
                 "not",
                 "oct",
                 "open",
                 "opendir",
                 "or",
                 "ord",
                 "our",
                 "pack",
                 "package",
                 "pipe",
                 "pop",
                 "pos",
                 "print",
                 "printf",
                 "prototype",
                 "push",
                 "q",
                 "qq",
                 "qr",
                 "qx",
                 "qw",
                 "quotemeta",
                 "rand",
                 "read",
                 "readdir",
                 "readline",
                 "readlink",
                 "readpipe",
                 "recv",
                 "redo",
                 "ref",
                 "rename",
                 "require",
                 "reset",
                 "return",
                 "reverse",
                 "rewinddir",
                 "rindex",
                 "rmdir",
                 "s",
                 "say",
                 "scalar",
                 "seek",
                 "seekdir",
                 "select",
                 "semctl",
                 "semget",
                 "semop",
                 "send",
                 "setgrent",
                 "sethostent",
                 "setnetent",
                 "setpgrp",
                 "setpriority",
                 "setprotoent",
                 "setpwent",
                 "setservent",
                 "setsockopt",
                 "shift",
                 "shmctl",
                 "shmget",
                 "shmread",
                 "shmwrite",
                 "shutdown",
                 "sin",
                 "sleep",
                 "socket",
                 "socketpair",
                 "sort",
                 "splice",
                 "split",
                 "sprintf",
                 "sqrt",
                 "srand",
                 "stat",
                 "state",
                 "study",
                 "sub",
                 "substr",
                 "symlink",
                 "syscall",
                 "sysopen",
                 "sysread",
                 "sysseek",
                 "system",
                 "syswrite",
                 "tell"
                 "telldir",
                 "tie",
                 "tied",
                 "time",
                 "times",
                 "tr",
                 "truncate",
                 "uc",
                 "ucfirst",
                 "umask",
                 "undef",
                 "unless",
                 "unlink",
                 "unpack",
                 "unshift",
                 "untie",
                 "until",
                 "use",
                 "utime",
                 "values",
                 "vec",
                 "wait",
                 "waitpid",
                 "wantarray",
                 "warn",
                 "when",
                 "while",
                 "write",
                 "xor",
                 "y"
                 ]
    
    def softchar_accept_matching_forward_slash(self, scimoz, pos, style_info, candidate):
        if pos == 0:
            return candidate
        currStyle = scimoz.getStyleAt(pos)
        if not currStyle in style_info._regex_styles:
            return None
        prevPos = scimoz.positionBefore(pos)
        if scimoz.getStyleAt(prevPos) != currStyle:
            # We're at the start of a regex.
            return candidate
        # Check for m/ or s/
        if pos >= 2:
            prev2Pos = scimoz.positionBefore(prevPos)
            if scimoz.getStyleAt(prev2Pos) == currStyle:
                return None
        leadChar = scimoz.getWCharAt(prevPos)
        if leadChar == 's':
            return "//"
        elif leadChar == 'm':
            return candidate
        return None
    
    def _is_special_variable(self, scimoz, pos, opStyle):
        if pos == 0:
            return False;
        prevPos = scimoz.positionBefore(pos)
        if scimoz.getStyleAt(prevPos) == opStyle and chr(scimoz.getCharAt(prevPos)) == '$':
            # In Perl $( and $[ have particular meanings
            return True
        return False

    def softchar_check_special_then_return_char(self, scimoz, pos, style_info, candidate):
        if self._is_special_variable(scimoz, pos,
                                     self.isUDL() and scimoz.SCE_UDL_SSL_VARIABLE or scimoz.SCE_PL_SCALAR):
            return None
        return candidate

class KoPerlCodeIntelCompletionLanguageService(KoCodeIntelCompletionLanguageService):
    _com_interfaces_ = [components.interfaces.koICodeIntelCompletionLanguageService]
    _reg_desc_ = "Perl CodeIntel Calltip/AutoCompletion Service"
    _reg_clsid_ = "{E08B997A-6638-4574-9FDE-527DE7E09B41}"
    _reg_contractid_ = "@activestate.com/koPerlCodeIntelCompletionLanguageService;1"

    # Characters that should automatically invoke the current completion item
    # - cannot be '-' for "autocomplete-*-subs" because:
    #       attributes::->import(__PACKAGE__, \$x, 'Bent');
    # - cannot be '{' for "autocomplete-object-subs" because:
    #       my $d = $self->{'escape'};
    # - shouldn't be ')' because:
    #       $dumper->dumpValue(\*::);
    completionFillups = "~`!@#$%^&*(=+}[]|\\;:'\",.<>?/ "

    # To regenerate this block:
    # - install the cog Python tool:
    #   http://www.nedbatchelder.com/code/cog/index.html
    # - run "cog -r koPerlLanguage.py"
    #[[[cog
    #import cog
    #import os, sys
    #sys.path.insert(0, os.path.join(os.pardir, "codeintel"))
    #import cidb
    #dbpath = cidb.find_komodo_cidb_path()
    #sql = """SELECT symbol.name FROM file,scan,module,symbol
    #          WHERE file.compare_path LIKE '%perl.cix'
    #            AND scan.file_id=file.id AND module.scan_id=scan.id
    #            AND symbol.module_id=module.id AND symbol.type=0"""
    #cog.outl('allowTriggerOnSpace = {')
    #for line in cidb.query(dbpath, 3, sql, "csv"):
    #    cog.outl('    "%s": 1,' % line.strip())
    #cog.outl('}')
    #]]]
    allowTriggerOnSpace = {
        "-r": 1,
        "-w": 1,
        "-x": 1,
        "-o": 1,
        "-R": 1,
        "-W": 1,
        "-X": 1,
        "-O": 1,
        "-e": 1,
        "-z": 1,
        "-s": 1,
        "-f": 1,
        "-d": 1,
        "-l": 1,
        "-p": 1,
        "-S": 1,
        "-b": 1,
        "-c": 1,
        "-t": 1,
        "-u": 1,
        "-g": 1,
        "-k": 1,
        "-T": 1,
        "-B": 1,
        "-M": 1,
        "-A": 1,
        "-C": 1,
        "abs": 1,
        "accept": 1,
        "alarm": 1,
        "atan2": 1,
        "bind": 1,
        "binmode": 1,
        "bless": 1,
        "caller": 1,
        "chdir": 1,
        "chmod": 1,
        "chomp": 1,
        "chop": 1,
        "chown": 1,
        "chr": 1,
        "chroot": 1,
        "close": 1,
        "closedir": 1,
        "connect": 1,
        "continue": 1,
        "cos": 1,
        "crypt": 1,
        "dbmclose": 1,
        "dbmopen": 1,
        "defined": 1,
        "delete": 1,
        "die": 1,
        "do": 1,
        "dump": 1,
        "each": 1,
        "eof": 1,
        "eval": 1,
        "exec": 1,
        "exists": 1,
        "exit": 1,
        "exp": 1,
        "fcntl": 1,
        "fileno": 1,
        "flock": 1,
        "fork": 1,
        "format": 1,
        "formline": 1,
        "getc": 1,
        "getlogin": 1,
        "getpeername": 1,
        "getpgrp": 1,
        "getppid": 1,
        "getpriority": 1,
        "getpwnam": 1,
        "getgrnam": 1,
        "gethostbyname": 1,
        "getnetbyname": 1,
        "getprotobyname": 1,
        "getpwuid": 1,
        "getgrgid": 1,
        "getservbyname": 1,
        "gethostbyaddr": 1,
        "getnetbyaddr": 1,
        "getprotobynumber": 1,
        "getservbyport": 1,
        "getpwent": 1,
        "getgrent": 1,
        "gethostent": 1,
        "getnetent": 1,
        "getprotoent": 1,
        "getservent": 1,
        "setpwent": 1,
        "setgrent": 1,
        "sethostent": 1,
        "setnetent": 1,
        "setprotoent": 1,
        "setservent": 1,
        "endpwent": 1,
        "endgrent": 1,
        "endhostent": 1,
        "endnetent": 1,
        "endprotoent": 1,
        "endservent": 1,
        "getsockname": 1,
        "getsockopt": 1,
        "glob": 1,
        "gmtime": 1,
        "goto": 1,
        "grep": 1,
        "hex": 1,
        "import": 1,
        "index": 1,
        "int": 1,
        "ioctl": 1,
        "join": 1,
        "keys": 1,
        "kill": 1,
        "last": 1,
        "lc": 1,
        "lcfirst": 1,
        "length": 1,
        "link": 1,
        "listen": 1,
        "local": 1,
        "localtime": 1,
        "lock": 1,
        "log": 1,
        "lstat": 1,
        "m": 1,
        "map": 1,
        "mkdir": 1,
        "msgctl": 1,
        "msgget": 1,
        "msgrcv": 1,
        "msgsnd": 1,
        "my": 1,
        "next": 1,
        "no": 1,
        "oct": 1,
        "open": 1,
        "opendir": 1,
        "ord": 1,
        "our": 1,
        "pack": 1,
        "package": 1,
        "pipe": 1,
        "pop": 1,
        "pos": 1,
        "print": 1,
        "printf": 1,
        "prototype": 1,
        "push": 1,
        "q": 1,
        "qq": 1,
        "qr": 1,
        "qx": 1,
        "qw": 1,
        "quotemeta": 1,
        "rand": 1,
        "read": 1,
        "readdir": 1,
        "readline": 1,
        "readlink": 1,
        "readpipe": 1,
        "recv": 1,
        "redo": 1,
        "ref": 1,
        "rename": 1,
        "reset": 1,
        "return": 1,
        "reverse": 1,
        "rewinddir": 1,
        "rindex": 1,
        "rmdir": 1,
        "s": 1,
        "scalar": 1,
        "seek": 1,
        "seekdir": 1,
        "select": 1,
        "semctl": 1,
        "semget": 1,
        "semop": 1,
        "send": 1,
        "setpgrp": 1,
        "setpriority": 1,
        "setsockopt": 1,
        "shift": 1,
        "shmctl": 1,
        "shmget": 1,
        "shmread": 1,
        "shmwrite": 1,
        "shutdown": 1,
        "sin": 1,
        "sleep": 1,
        "socket": 1,
        "socketpair": 1,
        "sort": 1,
        "splice": 1,
        "split": 1,
        "sprintf": 1,
        "sqrt": 1,
        "srand": 1,
        "stat": 1,
        "study": 1,
        "substr": 1,
        "symlink": 1,
        "syscall": 1,
        "sysopen": 1,
        "sysread": 1,
        "sysseek": 1,
        "system": 1,
        "syswrite": 1,
        "tell": 1,
        "telldir": 1,
        "tie": 1,
        "tied": 1,
        "time": 1,
        "times": 1,
        "tr": 1,
        "truncate": 1,
        "uc": 1,
        "ucfirst": 1,
        "umask": 1,
        "undef": 1,
        "unlink": 1,
        "unpack": 1,
        "untie": 1,
        "unshift": 1,
        "utime": 1,
        "values": 1,
        "vec": 1,
        "wait": 1,
        "waitpid": 1,
        "wantarray": 1,
        "warn": 1,
        "write": 1,
        "y": 1,
    }
    #[[[end]]]

    def __init__(self):
        KoCodeIntelCompletionLanguageService.__init__(self)

    def initialize(self, language):
        KoCodeIntelCompletionLanguageService.initialize(self, language)
        # Some Perl styles in addition to the usual comment and string styles
        # in which implicit completion triggering should no happen.
        self._noImplicitCompletionStyles[sci_constants.SCE_PL_DATASECTION] = True
        self._noCompletionStyles[sci_constants.SCE_PL_REGEX] = True

    # Match a subroutine definition. Used by getTriggerType()
    _subdefPat = re.compile(r"\bsub\s+(\w+(::|'))*\w+$")
    # All Perl trigger points occur at one of these characters:
    #   ' ' (space)         only supported for built-in functions
    #   '(' (open paren)
    #   '>' (greater than)  "->" actually
    #   ':' (colon)         "::" actually
    TRIGGER_CHARS = tuple(' (>:')

    def getTriggerType(self, scimoz, position=None, implicit=1):
        """If the given position is a _likely_ trigger point, return the
        trigger type. Otherwise return None.
        
            "scimoz" is a nsISciMoz component.
            "position" (optional) is the position at which to check for a
                trigger point. If pos is None, then it defaults to the current
                cursor position.
            "implicit" (optional) is a boolean indicating if this trigger
                is being implicitly checked (i.e. as a side-effect of
                typing). Defaults to true.
        
        (See koILanguage.idl::koICodeIntelCompletionLanguageService for
        details.)
        
        Perl-specific return values:
            None (i.e. this is not at a trigger point)
            "calltip-space-call-signature"
            "calltip-call-signature"
            "autocomplete-package-*"
            "autocomplete-*-subs" meaning the actual trigger is one of:
                "autocomplete-package-subs"
                "autocomplete-object-subs"
            "autocomplete-package-packages"

        Not yet implemented:
            "autocomplete-module-exports"
            "autocomplete-available-modules"
        """
        DEBUG = 0  # not using 'logging' system, because want to be fast
        if DEBUG:
            print "\n----- getTriggerType(scimoz, position=%r, implicit=%r) -----"\
                  % (position, implicit)
    
        if position is None:
            position = scimoz.currentPos
        lastPos = position - 1
        lastChar = scimoz.getWCharAt(lastPos)
        if DEBUG:
            print "  lastPos: %s" % lastPos
            print "  lastChar: %r" % lastChar
    
        # All Perl trigger points occur at one of the TRIGGER_CHARS.
        if lastChar not in self.TRIGGER_CHARS:
            if DEBUG:
                print "getTriggerType: no: %r is not in %r"\
                      % (lastChar, self.TRIGGER_CHARS)
            return None
        elif lastChar == ':' \
             and not (lastPos > 0 and scimoz.getWCharAt(lastPos-1) == ':'):
            if DEBUG:
                penultimateChar = lastPos > 0 and scimoz.getWCharAt(lastPos-1) or ''
                print "getTriggerType: no: %r is not '::'"\
                      % (penultimateChar+lastChar)
            return None
        elif lastChar == '>' \
             and not (lastPos > 0 and scimoz.getWCharAt(lastPos-1) == '-'):
            if DEBUG:
                penultimateChar = lastPos > 0 and scimoz.getWCharAt(lastPos-1) or ''
                print "getTriggerType: no: %r is not '->'"\
                      % (penultimateChar+lastChar)
            return None
    
        # We should never trigger in some styles (strings, comments, etc.).
        styleMask = (1 << scimoz.styleBits) - 1
        styleNum = scimoz.getStyleAt(lastPos) & styleMask
        if DEBUG:
            sciUtilsSvc = components.classes["@activestate.com/koSciUtils;1"].\
                          getService(components.interfaces.koISciUtils)
            styleName = sciUtilsSvc.styleNameFromNum("Perl", styleNum)
            print "  style: %s (%s)" % (styleNum, styleName)
        if (implicit and styleNum in self._noImplicitCompletionStyles
            or styleNum in self._noCompletionStyles):
            if DEBUG:
                print "getTriggerType: no: completion is suppressed "\
                      "in style at %s: %s (%s)"\
                      % (lastPos, styleNum, styleName)
            return None
    
        WHITESPACE = tuple(' \t\n\r')
        if lastChar == ' ':
            # This can be either "calltip-space-call-signature" or None (or
            # "autocomplete-module-exports" when that is implemented).
            #
            # calltip-call-signature:
            #   Perl syntax allows a parameter list to be passed to a
            #   function name without enclosing parens. From a quick perusal
            #   of sample Perl code (from a default ActivePerl install)
            #   calling function this way seems to be limited to a number of
            #   core Perl built-ins or some library methods. For efficiency
            #   Komodo will maintain an explicit list of such function names
            #   for which a calltip with trigger without parentheses.
            #   XXX May want to make this a user-configurable list.
            LIMIT = 50
            text = scimoz.getTextRange(max(0,lastPos-LIMIT), lastPos) # working text
            if DEBUG: print "  working text: %r" % text
            i = len(text)-1
            if i >= 0 and not (isident(text[i]) or isdigit(text[i])):
                if DEBUG:
                    print "getTriggerType: no: two before trigger point is not "\
                          "an ident char: '%s'" % text[i]
                return None
            while i >= 0: # parse out the preceding identifier
                if not isident(text[i]):
                    identifier = text[i+1:]
                    # Whitespace is allowed between a Perl variable special
                    # char and the variable name, e.g.: "$ myvar", "@  mylist"
                    j = i
                    while j >= 0 and text[j] in WHITESPACE: # parse off whitespace
                        j -= 1
                    if j >= 0:
                        precedingChar = text[j]
                    else:
                        precedingChar = None
                    break
                i -= 1
            else:
                precedingChar = None
                identifier = text
            if DEBUG: print "  identifier: %r" % identifier
            if not identifier:
                if DEBUG:
                    print "getTriggerType: no: no identifier preceding trigger point"
                return None
            if DEBUG: print "  preceding char: %r" % precedingChar
            if precedingChar and precedingChar in "$@&%\\*": # indicating a Perl variable
                if DEBUG:
                    print "getTriggerType: no: triggering on space after Perl "\
                          "variables not supported"
                return None
            if identifier not in self.allowTriggerOnSpace:
                if DEBUG:
                    print "getTriggerType: no: identifier not in set for which "\
                          "space-triggering is supported (allowTriggerOnSpace)"
                return None
            # Specifically disallow trigger on defining a sub matching one of
            # space-trigger names, i.e.: 'sub split <|>'. Optmization: Assume
            # that there is exacly one space between 'sub' and the subroutine
            # name. Almost all examples in the Perl lib seem to follow this.
            if i >= 3 and text[i-3:i+1] == "sub ":
                if DEBUG:
                    print "getTriggerType: no: do not trigger in sub definition"
                return None
            if DEBUG: print "getTriggerType: calltip-space-call-signature"
            return "calltip-space-call-signature"
    
        elif lastChar == '(':
            # This can be either "calltip-call-signature" or None (or
            # "autocomplete-module-exports" when that is implemented).
            LIMIT = 100
            text = scimoz.getTextRange(max(0,lastPos-LIMIT), lastPos) # working text
            if DEBUG: print "  working text: %r" % text
            i = len(text)-1
            while i >= 0 and text[i] in WHITESPACE: # parse off whitespace
                i -= 1
            if i >= 0 and not (isident(text[i]) or isdigit(text[i])):
                if DEBUG:
                    print "getTriggerType: no: first non-ws char before "\
                          "trigger point is not an ident char: '%s'" % text[i]
                return None
            end = i+1
            while i >= 0: # parse out the preceding identifier
                if not isident(text[i]):
                    identifier = text[i+1:end]
                    # Whitespace is allowed between a Perl variable special
                    # char and the variable name, e.g.: "$ myvar", "@  mylist"
                    j = i
                    while j >= 0 and text[j] in WHITESPACE: # parse off whitespace
                        j -= 1
                    if j >= 0:
                        precedingChar = text[j]
                    else:
                        precedingChar = None
                    break
                i -= 1
            else:
                precedingChar = None
                identifier = text[:end]
            if DEBUG: print "  identifier: %r" % identifier
            if DEBUG:
                assert ' ' not in identifier, "parse error: space in identifier: %r" % identifier
            if not identifier:
                if DEBUG:
                    print "getTriggerType: no: no identifier preceding trigger point"
                return None
            if DEBUG: print "  preceding char: %r" % precedingChar
            if precedingChar and precedingChar in "$@%\\*":
                # '&foo(' *is* a trigger point, but the others -- '$foo(',
                # '&$foo(', etc. -- are not because current CodeIntel wouldn't
                # practically be able to determine the method to which $foo
                # refers.
                if DEBUG:
                    print "getTriggerType: no: calltip trigger on Perl var not supported"
                return None
            if identifier in ("if", "else", "elsif", "while", "for", "sub", "unless"):
                if DEBUG:
                    print "getTriggerType: no: no trigger on anonymous sub or control structure"
                return None
            # Now we want to rule out the subroutine definition lines, e.g.:
            #    sub FOO(<|>
            #    sub FOO::BAR(<|>
            #    sub FOO'BAR(<|>
            #    sub FOO::BAR::BAZ(<|>
            # Note: Frankly 80/20 rules out the last three.
            line = text[:end].splitlines(0)[-1]
            if DEBUG:
                print "  trigger line: %r" % line
            if "sub " in line: # only use regex if "sub " on that line
                if DEBUG:
                    print "  *could* be a subroutine definition"
                if self._subdefPat.search(line):
                    if DEBUG:
                        print "getTriggerType: no: no trigger on Perl sub definition"
                    return None
            if DEBUG: print "getTriggerType: calltip-call-signature"
            return "calltip-call-signature"
    
        elif lastChar == '>':
            # Must be "autocomplete-package-subs", "autocomplete-object-subs"
            # or None. Note that we have already checked (above) that the
            # trigger string is '->'. Basically, as long as the first
            # non-whitespace char preceding the '->' is an identifier char,
            # then this is a trigger point.
            LIMIT = 50
            text = scimoz.getTextRange(max(0,lastPos-1-LIMIT), lastPos-1) # working text
            if DEBUG: print "  working text: %r" % text
            i = len(text)-1
            while i >= 0 and text[i] in WHITESPACE: # parse off whitespace
                i -= 1
            if i < 0:
                if DEBUG:
                    print "getTriggerType: no: no non-whitespace text preceding '->'"
                return None
            elif not isident(text[i]):
                if DEBUG:
                    print "getTriggerType: no: first non-ws char before "\
                          "trigger point is not an ident char: '%s'" % text[i]
                return None
            # At this point we know it is either "autocomplete-package-subs"
            # or "autocomplete-object-subs". We don't really care to take
            # the time to distinguish now -- getTrigger is supposed to be
            # quick -- and we don't have to. 
            if DEBUG: print "getTriggerType: autocomplete-*-subs"
            return "autocomplete-*-subs"
    
        elif lastChar == ':':
            # Must be "autocomplete-package" or None (or
            # "autocomplete-package-packages" when that is implemented). Note
            # that we have already checked (above) that the trigger string is
            # '::'. Basically, as long as the first char preceding the '::'
            # is an identifier char or one of Perl's funny variable
            # identifying characters, then this is a trigger point.
            LIMIT = 50
            text = scimoz.getTextRange(max(0,lastPos-1-LIMIT), lastPos-1) # working text
            if DEBUG: print "  working text: %r" % text
            i = len(text)-1
            if i < 0:
                if DEBUG:
                    print "getTriggerType: no: no text preceding '::'"
                return None
            ch = text[i]
            if not (isident(ch) or isdigit(ch) or ch == '$'):
                # Technically should allow '@', '%' and '&' in there, but there
                # a total of 5 of all of this in the Perl std lib. 80/20 rule.
                if DEBUG:
                    print "getTriggerType: no: first char before trigger "\
                          "point is not an ident char or '$': '%s'" % ch
                return None
            # Check if this is in a 'use' or 'require' statement.
            line = text.splitlines(0)[-1]
            if DEBUG:
                print "  trigger line: %r" % line
            lstripped = line.lstrip()
            if lstripped.startswith("use ") or lstripped.startswith("require "):
                if DEBUG:
                    print "getTriggerType: autocomplete-package-packages"
                return "autocomplete-package-packages"
            if DEBUG: print "getTriggerType: autocomplete-package-*"
            return "autocomplete-package-*"
    
        return None

    def getCallTipHighlightSpan(self, entered, calltip):
        log.debug("getCallTipHighlightSpan(entered=%r, calltip=%r)",
                  entered, calltip)
        index = self._findCallTipEnd(entered)
        if index != -1:
            return (-1, -1) # i.e. close the calltip
        # Determining which of the possibly multiple call signatures to
        # highlight and which argument in that call sig is non-trivial.
        # Punting on this for now.
        return (0, 0)

    def _findCallTipEnd(self, text):
        """Return the index into "text" at which the calltip would be
        closed. I.e. find the end of the call region. Returns -1 if can't
        be found.
        
            "text" is the text *after* the calltip trigger char to the
                current cursor position.

        Algorithm:
        - skip over matching block delimiters
        - terminate at ']', '}', ')', ';', '='
        """
        TERMINATORS = tuple(']});=')
        BLOCKSETS = {
            '(': ')', '{': '}', '[': ']',   # parens
            '"': '"', "'": "'",             # strings
            '/': '/',                       # regexs
        }
        blockstack = []
        length = len(text)
        i = 0
        while i < length:
            ch = text[i]
            if blockstack:
                if ch == blockstack[-1]:
                    blockstack.pop()
            else:
                if ch in BLOCKSETS:
                    blockstack.append(BLOCKSETS[ch])
                elif ch in TERMINATORS:
                    return i
            i += 1
        return -1

    def triggerPrecedingCompletionUI(self, path, scimoz, startPos,
                                     ciCompletionUIHandler):
        DEBUG = 0
        line = scimoz.lineFromPosition(startPos)+1 # want 1-based line
        offset, styledText, styleMask = self._getSciMozContext(scimoz, startPos)
        if DEBUG:
            sciutils._printBanner("triggerPrecedingCompletionUI")
            sciutils._printBufferContext(offset, styledText, startPos)

        # Only look back up to a max of three lines, stopping at a
        # semi-colon statement terminator (unless that semi-colon is one
        # the current line). E.g. Ctrl+J should work for:
        #       foo(bar, baz);<|>
        limitPos = scimoz.positionFromLine(max(line-4, 0))
        if DEBUG:
            print "  limitPos: %r" % limitPos
        currLineStartPos = scimoz.positionFromLine(line-1)
        if DEBUG:
            print "  current line starts at pos: %r" % currLineStartPos
        TRIGGER_CHARS = self.TRIGGER_CHARS
        SCE_PL_OPERATOR = sci_constants.SCE_PL_OPERATOR
        pos = startPos
        while pos > limitPos:
            ch = scimoz.getWCharAt(pos-1)
            if pos < currLineStartPos and ch == ';' \
               and (scimoz.getStyleAt(pos-1) & styleMask) == SCE_PL_OPERATOR:
                if DEBUG:
                    print "  abort at ';' operator: pos=%d" % (pos-1)
                return "no completion trigger point in current statement"
            elif ch in TRIGGER_CHARS:
                if DEBUG:
                    print "  consider trigger char %r at pos %d" % (ch, pos-1)
                triggerType = self.getTriggerType(scimoz, pos, implicit=0)
                if triggerType:
                    if DEBUG:
                        print "  trigger '%s' at pos %d" % (triggerType, pos)
                    try:
                        #XXX If we stop using getAdjustedCurrentScope() and
                        #    instead get the scope from path/line the
                        #    CodeIntelCompletionUIHandler will have to be
                        #    updated to use the proper CI-path so that CIDB
                        #    lookups work.
                        file_id, table, id = self.codeIntelSvc.getAdjustedCurrentScope(scimoz, pos)
                        completions = self._getCompletions(
                            path, line, triggerType, offset, styledText,
                            styleMask, pos, explicit=1, scopeFileId=file_id,
                            scopeTable=table, scopeId=id,
                            content=scimoz.text)
                    except Exception, ex:
                        return "error determining '%s' completions at %d,%d: %s"\
                               % (triggerType, scimoz.lineFromPosition(pos)+1,
                                  scimoz.getColumn(pos)+1, ex)
                    if completions:
                        # May need to move within "range" of the completion
                        # UI. E.g.
                        #       $foo->bar(blam<|>
                        #                `- move back to autocomplete here
                        #       foo(bar, baz);<|>
                        #                   `- move back to calltip here
                        if triggerType.startswith("autocomplete"):
                            curPos = scimoz.currentPos
                            i = pos
                            while i < curPos:
                                ch = scimoz.getWCharAt(i)
                                if not isident(ch) and not isdigit(ch):
                                    scimoz.currentPos = scimoz.anchor = i
                                    break
                                i += 1
                        elif triggerType.startswith("calltip"):
                            index = self._findCallTipEnd(scimoz.getTextRange(pos, scimoz.currentPos))
                            if index != -1 and scimoz.currentPos > pos+index:
                                scimoz.currentPos = scimoz.anchor = pos+index
                        self._dispatchCompletions(triggerType, completions,
                                                  pos, 1, ciCompletionUIHandler)
                        return None
            pos -= 1
        return "no completion trigger point in preceding three lines"


    # Special Perl variables/subs to typically _exclude_ from AutoComplete
    # lists.
    _specialVarsToSkip = {
        "$AUTOLOAD": 1, "DESTROY": 1,
        "@EXPORT": 1, "@EXPORT_FAIL": 1, "@EXPORT_OK": 1, "%EXPORT_TAGS": 1,
        "@ISA": 1, "import": 1,
    }
    _perlVarTokenizer = re.compile(r"([$\\%&@]+)?(\w+)")
    def _massageCompletions(self, types, members, dropSpecials=True,
                            keepOnlySubs=False, filterOnPrefixChar=None):
        """Massage the given list of Perl completions for use in the Scintilla
        completion list. Some transformations are done on the given list:
        - add the appropriate pixmap marker for each completion
        - optionally drop special variables not really appropriate in a
          completion list (e.g. @EXPORTS, $AUTOLOAD, etc.)
        - optionally drop all members except subroutines for '->'-triggered
          autocomplete
        - optionally filter on a leading prefix character
        
            "types" is a list of CodeIntel type names.
            "members" is a list of member names.
            "dropSpecials" (default true) is a boolean indicating if
                special Perl variables (a hardcoded list, e.g. @EXPORT)
                should be dropped from the list.
            "keepOnlySubs" (default false) is a boolean indicating if all
                members except subroutines should be dropped.
            "filterOnPrefixChar" (default None) is a Perl variable prefix
                char (i.e. '$', '@', '%', '&' or '') on which to filter the
                returned list of appropriate completions.
        """
        # Indicate the appropriate pixmap for each entry.
        # c.f. http://scintilla.sf.net/ScintillaDoc.html#SCI_REGISTERIMAGE
        cicui = components.interfaces.koICodeIntelCompletionUIHandler
        typeName2aciid = {
            "class": cicui.ACIID_CLASS,
            "function": cicui.ACIID_FUNCTION,
            "module": cicui.ACIID_MODULE,
            "interface": cicui.ACIID_INTERFACE,
            "namespace": cicui.ACIID_NAMESPACE,
        }
        variablePrefix2aciid = {
            None: cicui.ACIID_VARIABLE,
            "$": cicui.ACIID_VARIABLE_SCALAR,
            "@": cicui.ACIID_VARIABLE_ARRAY,
            "%": cicui.ACIID_VARIABLE_HASH,
        }
        completions = []
        for type, member in zip(types, members):
            if dropSpecials and member in self._specialVarsToSkip:
                continue
            if keepOnlySubs and type != "function":
                continue
            if filterOnPrefixChar is None:
                pass
            elif filterOnPrefixChar in ('', '&') and type == "variable":
                # If the prefix filter char is empty or '&', then filter out
                # variables.
                log.debug("(1) filter out %s member %r based on %r",
                          type, member, filterOnPrefixChar)
                continue
            elif filterOnPrefixChar in ('$', '@', '%') and type == "function":
                # If the prefix filter char is one of the Perl variable
                # prefix chars ($%@), then filter out functions.
                log.debug("(2) filter out %s member %r based on %r",
                          type, member, filterOnPrefixChar)
                continue
            
            try:
                prefix, name = self._perlVarTokenizer.match(member).groups()
            except AttributeError:
                # AttributeError: 'NoneType' object has no attribute 'groups'
                log.error("could not parse Perl var '%s' with '%s' pattern",
                          member, self._perlVarTokenizer.pattern)
                continue
            if type == "variable":
                if prefix:
                    prefix = prefix[-1] # only last char is relevant
                else:
                    log.warn("Perl variable without prefix char: %r" % member)

                if filterOnPrefixChar is None:
                    pass
                elif filterOnPrefixChar == '*':
                    # If the prefix filter char is '*', pass all functions
                    # and variables.
                    pass
                elif filterOnPrefixChar == '$':
                    # If the prefix filter char is '$', then pass all
                    # variables. (Arrays and hashes can pass because a
                    # '$'-prefix is possible for indexing.)
                    pass
                elif prefix and filterOnPrefixChar != prefix:
                    # If the prefix filter char is '%' or '@', then filter
                    # out all variable but the ones of the same
                    # persuasion.
                    log.debug("(3) filter out %s member %r based on %r",
                              type, member, filterOnPrefixChar)
                    continue
                    
                if not prefix:
                    aciid = variablePrefix2aciid[None]
                elif prefix in variablePrefix2aciid:
                    aciid = variablePrefix2aciid[prefix]
                else:
                    aciid = variablePrefix2aciid[None]
            elif type:
                aciid = typeName2aciid[type]
            else: # type may be None to indicate type-not-known
                aciid = cicui.ACIID_VARIABLE
            completions.append(name + "?%d" % aciid)

        return completions

    def _getCompletions(self, path, line, completionType, offset, styledText,
                        styleMask, triggerPos, explicit=0, scopeFileId=0,
                        scopeTable=None, scopeId=0, content=None):
        """Return a list of completions for the given possible trigger point.

            "completionType" is one of the possible retvals from
                getTriggerType()
            "explicit" (optional, default false) is a boolean indicating if
                the completion list was explicitly triggered.
            "scopeFileId", "scopeTable" and "scopeId" (optional) can be
                passed in to express the scope more accurately than "path"
                and "line" -- if, say, the caller is adjusting for recent
                edits not in the database.
            "content" (optional) is the file content. This may be used, if
                passed in, for fallback "dumb" completion handling.

        If this is NOT a valid trigger point (i.e. getTriggerType() was
        mistaken), then return None.
        
        XXX For now, raise an error if there is some error determining the
        completions.
        """
        log.debug("_getCompletions(path=%r, line=%r, %r, offset=%d, "
                  "styledText, styleMask, triggerPos=%d, explicit=%r, "
                  "scopeFileId=%r, scopeTable=%r, scopeId=%r, content)",
                  path, line, completionType, offset, triggerPos, explicit,
                  scopeFileId, scopeTable, scopeId)

        if explicit:
            # Specifically do NOT ignore comment and string styles.
            stylesToIgnore = {}
        else:
            stylesToIgnore = self._noImplicitCompletionStyles

        if completionType in ("calltip-space-call-signature",
                              "calltip-call-signature"):
            lenTrigger = 1  # '(' or ' '
            filter, expr = sciutils.getLeadingPerlCITDLExpr(
                offset, styledText, triggerPos-lenTrigger, stylesToIgnore,
                styleMask)
            log.debug("_getCompletions: CITDL expression: %r", expr)
            if not expr:
                return None
            completions = self.codeIntelSvc.getCallTips("Perl", path, line,
                expr, explicit, scopeFileId, scopeTable, scopeId, content)

        elif completionType == "autocomplete-package-*":
            lenTrigger = 2  # '::'
            filter, expr = sciutils.getLeadingPerlCITDLExpr(
                offset, styledText, triggerPos-lenTrigger, stylesToIgnore,
                styleMask)
            log.debug("_getCompletions: CITDL expression: %r", expr)
            if not expr:
                return None
            types, members = self.codeIntelSvc.getMembers("Perl", path, line,
                expr, explicit, scopeFileId, scopeTable, scopeId, content)
            if filter:
                # Only last char of prefix group is relevant for completion
                # filtering.
                filter = filter[-1]
            completions = self._massageCompletions(types, members,
                filterOnPrefixChar=filter)
            completions.sort(lambda a,b: cmp(a.upper(), b.upper()))

        elif completionType == "autocomplete-*-subs":
            lenTrigger = 2  # '->'
            filter, expr = sciutils.getLeadingPerlCITDLExpr(
                offset, styledText, triggerPos-lenTrigger, stylesToIgnore,
                styleMask)
            log.debug("_getCompletions: CITDL expression: %r", expr)
            if not expr:
                return None
            types, members = self.codeIntelSvc.getMembers("Perl", path, line,
                expr, explicit, scopeFileId, scopeTable, scopeId, content)
            completions = self._massageCompletions(types, members,
                                                   keepOnlySubs=True)
            completions.sort(lambda a,b: cmp(a.upper(), b.upper()))

        elif completionType in ("autocomplete-package-packages",):
            lenTrigger = 2  # '::'
            filter, expr = sciutils.getLeadingPerlCITDLExpr(
                offset, styledText, triggerPos-lenTrigger, stylesToIgnore,
                styleMask)
            log.debug("_getCompletions: CITDL expression: %r", expr)
            if not expr:
                return None
            subimports = self.codeIntelSvc.getSubimports("Perl", expr,
                os.path.dirname(path), explicit)
            completions = self._massageCompletions(
                ["module"]*len(subimports), subimports, dropSpecials=False)
            completions.sort(lambda a,b: cmp(a.upper(), b.upper()))

        else:
            raise ValueError("cannot determine completion: unexpected "
                             "trigger type '%s'" % completionType)

        log.info("completions for '%s' trigger at %s:%s,%s: %r",
                 completionType, os.path.basename(path), line, triggerPos,
                 completions)
        return completions

    def _dispatchCompletions(self, completionType, completions, triggerPos,
                             explicit, ciCompletionUIHandler):
        if completionType.startswith("autocomplete"):
            cstr = self.completionSeparator.join(completions)
            #XXX Might want to include relevant string info leading up to
            #    the trigger char so the Completion Stack can decide
            #    whether the completion info is still relevant.
            ciCompletionUIHandler.setAutoCompleteInfo(cstr, triggerPos)
        elif completionType.startswith("calltip"):
            calltip = completions[0]
            ciCompletionUIHandler.setCallTipInfo(calltip, triggerPos, explicit)
        else:
            raise ValueError("cannot dispatch completions: unexpected "
                             "completion type '%s'" % completionType)

    def _handleRequest(self, request):
        (path, line, completionType, offset, styledText, styleMask,
         triggerPos, scopeFileId, scopeTable, scopeId, content,
         ciCompletionUIHandler) = request
        #log.debug("_handleRequest(path=%r, line=%r, '%s', offset=%d, "
        #          "styledText, styleMask, triggerPos=%d)", path, line,
        #          completionType, offset, triggerPos)
        completions = self._getCompletions(path, line, completionType, offset,
                                           styledText, styleMask, triggerPos,
                                           scopeFileId=scopeFileId,
                                           scopeTable=scopeTable,
                                           scopeId=scopeId,
                                           content=content)
        if completions:
            self._dispatchCompletions(completionType, completions,
                                      triggerPos, 0, ciCompletionUIHandler)

    def test_scimoz(self, scimoz):
        # Make sure we are initialized. We may not be if CodeIntel
        # completion is not enabled.
        if not self._noImplicitCompletionStyles:
            contractID = "@activestate.com/koLanguage?language=Perl;1"
            langSvc = components.classes[contractID].getService()
            self.initialize(langSvc)
        
        # Setup test cases. (unittest.py sucks: this is the only way to get
        # info to the tests)\
        PerlTriggerTestCase.cicSvc = self
        testCases = [PerlTriggerTestCase]
        sciutils.runSciMozTests(testCases, scimoz)



#---- test suites
#
# Run via "Test | SciMoz Tests" in a Komodo dev build.
#

class PerlTriggerTestCase(sciutils.SciMozTestCase):
    """Test suite for KoPerlCodeIntelCompletionLanguageService.
    
    See the following for a description of Perl completion types:
        http://specs.activestate.com/Komodo_3.0/func/code_intelligence.html#perl-completion
    """
    cicSvc = None  # KoPerlCodeIntelCompletionLanguageService instance

    def assertTriggerIs(self, buffer, expectedTriggerInfo):
        self._setupSciMoz(buffer, "Perl")
        actualTriggerInfo = self.cicSvc.getTriggerType(self.scimoz)
        self.assertEqual(actualTriggerInfo, expectedTriggerInfo,
                         "unexpected trigger type for edit case: "
                         "expected %r, got %r, edit case %r"
                         % (expectedTriggerInfo, actualTriggerInfo, buffer))
    def assertTriggerIsNot(self, buffer, notExpectedTriggerInfo):
        self._setupSciMoz(buffer, "Perl")
        actualTriggerInfo = self.cicSvc.getTriggerType(self.scimoz)
        self.assertNotEqual(actualTriggerInfo, notExpectedTriggerInfo,
                            "unexpected trigger type for edit case: "
                            "did not want %r but got it, edit case %r"
                            % (actualTriggerInfo, buffer))

    def test_autocomplete_star_subs(self):
        self.assertTriggerIs("><|>", None)
        self.assertTriggerIs(" ><|>", None)
        self.assertTriggerIs("-><|>", None)
        self.assertTriggerIs(" -><|>", None)
        self.assertTriggerIs("$FOO->{<|>", None)
        self.assertTriggerIs("$FOO->[1]-><|>", None)
        self.assertTriggerIs("$FOO[1]-><|>", None)
        # E.g., from UDDI::Lite
        #   my $auth = get_authToken({userID => 'USERID', cred => 'CRED'})->authInfo;
        self.assertTriggerIs("foo()-><|>", None)

        self.assertTriggerIs("$FOO-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$foo-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$Foo-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$Foo::Bar-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$Foo::Bar::baz-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("Foo::bar $baz-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$ foo-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("$_-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("Foo::Bar-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("Foo::Bar::baz-><|>", "autocomplete-*-subs")
        self.assertTriggerIs("foo\n  \t-><|>", "autocomplete-*-subs")

    def test_autocomplete_package_star(self):
        self.assertTriggerIs(":<|>", None)
        self.assertTriggerIs("::<|>", None)
        self.assertTriggerIs(" :<|>", None)
        self.assertTriggerIs(": :<|>", None)
        self.assertTriggerIs("Foo: :<|>", None)

        self.assertTriggerIs("FOO::<|>", "autocomplete-package-*")
        self.assertTriggerIs("foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("Foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("$FOO::<|>", "autocomplete-package-*")
        self.assertTriggerIs("$foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("$Foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("@foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("\foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("*foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("%foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs("$::<|>", "autocomplete-package-*") # equiv to $main::

        self.assertTriggerIs("@B::<|>SV::ISA = 'B::OBJECT';", "autocomplete-package-*")
        self.assertTriggerIs("@B::SV::<|>ISA = 'B::OBJECT';", "autocomplete-package-*")
        self.assertTriggerIs("@B::SV::ISA = 'B::<|>OBJECT';\n\n", None)

        self.assertTriggerIs("use FOO::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("use foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("use Foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("use Foo::Bar::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("use Foo::<|>Bar::", "autocomplete-package-packages")
        self.assertTriggerIs("$use Foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs(" use Foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("\tuse Foo::<|>", "autocomplete-package-packages")

        self.assertTriggerIs("require FOO::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("require foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("require Foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("require Foo::Bar::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("require Foo::<|>Bar::", "autocomplete-package-packages")
        self.assertTriggerIs("$require Foo::<|>", "autocomplete-package-*")
        self.assertTriggerIs(" require Foo::<|>", "autocomplete-package-packages")
        self.assertTriggerIs("\trequire Foo::<|>", "autocomplete-package-packages")


    def test_calltip_call_signature(self):
        self.assertTriggerIs(" <|>", None)
        self.assertTriggerIs("((<|>", None)
        self.assertTriggerIs("(<|>", None)
        
        self.assertTriggerIs("split <|>", "calltip-space-call-signature")
        self.assertTriggerIs(" split <|>", "calltip-space-call-signature")
        # Keep the scope of space-triggerred calltips low. No absolute
        # need to support more than one space away.
        self.assertTriggerIs("split  <|>", None)
        # Only allowTriggerOnSpace words will trigger space-calltip.
        self.assertTriggerIs("notaperlbuiltin <|>", None)
        self.assertTriggerIs("$split <|>", None)
        self.assertTriggerIs("&split <|>", None)
        self.assertTriggerIs("@split <|>", None)
        self.assertTriggerIs("%split <|>", None)
        self.assertTriggerIs("\\split <|>", None)
        self.assertTriggerIs("*split <|>", None)
        self.assertTriggerIs("$ split <|>", None)
        self.assertTriggerIs("& split <|>", None)
        self.assertTriggerIs("@ split <|>", None)
        self.assertTriggerIs("% split <|>", None)
        self.assertTriggerIs("\\ split <|>", None)
        self.assertTriggerIs("* split <|>", None)
        self.assertTriggerIs("sub split <|>", None) # can overload built-ins

        self.assertTriggerIs(" split(<|>", "calltip-call-signature")
        self.assertTriggerIs(" split (<|>", "calltip-call-signature")
        self.assertTriggerIs("split(<|>", "calltip-call-signature")
        self.assertTriggerIs("split (<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO(<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO (<|>", "calltip-call-signature")
        self.assertTriggerIs("$FOO->BAR(<|>", "calltip-call-signature")
        self.assertTriggerIs("FOO::BAR->BAZ(<|>", "calltip-call-signature")
        # Currently unable to test this because the Perl lexer assigns
        # a number style to the cursor position in the test suite setup.
        # I can't repro that style-assignment in the normal editor and
        # it seems to work fine there, so leaving this for now.
        #self.assertTriggerIs("FOO'BAR->BAZ(<|>", "calltip-call-signature")
        self.assertTriggerIs("&FOO(<|>", "calltip-call-signature")
        if 1:
            self.assertTriggerIs("&$FOO(<|>", None)
            self.assertTriggerIs("&$ FOO(<|>", None)
        else:
            # Really this *is* allowed, but the current Perl completion
            # implementation practically won't be able to identify the
            # sub reference assigned to $FOO.
            self.assertTriggerIs("&$FOO(<|>", "calltip-call-signature")
            self.assertTriggerIs("&$ FOO(<|>", "calltip-call-signature")
        self.assertTriggerIs("$FOO(", None)
        self.assertTriggerIs("$ FOO(", None)
        self.assertTriggerIs("@FOO(", None)
        self.assertTriggerIs("@ FOO(", None)
        # We *could* have the Perl completion trigger handling trigger on
        # the following and let subsequent CITDL evaluation rule them out,
        # but for efficiency we will try to rule them out here.
        self.assertTriggerIs("sub(<|>", None)
        self.assertTriggerIs("sub (<|>", None)
        self.assertTriggerIs("sub FOO(<|>", None)
        self.assertTriggerIs("sub FOO::BAR(<|>", None)
        self.assertTriggerIs("sub FOO'BAR(<|>", None) # see bigrat.pl in Perl lib
        self.assertTriggerIs("sub FOO::BAR::BAZ(<|>", None)
        for keyword in ("if", "else", "elsif", "unless", "while", "for"):
            self.assertTriggerIs("%s (<|>" % keyword, None)
            self.assertTriggerIs("%s(<|>" % keyword, None)
        self.assertTriggerIs("foreach $foo (<|>", None)
        self.assertTriggerIs("foreach my $foo (<|>", None)
