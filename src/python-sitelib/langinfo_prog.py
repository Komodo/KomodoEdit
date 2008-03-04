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

"""LangInfo definitions for some programming languages."""

import re
from langinfo import LangInfo


class PythonLangInfo(LangInfo):
    name = "Python"
    conforms_to_bases = ["Text"]
    exts = ['.py', '.pyw']
    magic_numbers = [
        (0, "regex", re.compile(r'\A#!.*python.*$', re.I | re.M))
    ]
    default_encoding = "ascii"  #TODO: link to ref defining default encoding
    # http://www.python.org/dev/peps/pep-0263/
    encoding_decl_pattern = re.compile(r"coding[:=]\s*(?P<encoding>[-\w.]+)")

class CompiledPythonLangInfo(LangInfo):
    name = "Compiled Python"
    exts = ['.pyc', '.pyo']

class PerlLangInfo(LangInfo):
    name = "Perl"
    conforms_to_bases = ["Text"]
    exts = ['.pl', '.pm', '.t']
    magic_numbers = [
        (0, "regex", re.compile(r'\A#!.*perl.*$', re.I | re.M)),
    ]
    filename_patterns = ["Construct", "Conscript"] # Cons make-replacement tool files

    # http://search.cpan.org/~rgarcia/encoding-source-0.02/lib/encoding/source.pm
    default_encoding = "iso8859-1"
    # Perl >= 5.8.0
    #   http://perldoc.perl.org/encoding.html
    #   use encoding "<encoding-name>";
    #   "Somewhat broken."
    # Perl >= 5.9.5
    #   http://search.cpan.org/~rgarcia/encoding-source-0.02/lib/encoding/source.pm
    #   use encoding::source "<encoding-name>";
    #   "This is like the encoding pragma, but done right."
    encoding_decl_pattern = re.compile(
        r"""use\s+encoding(?:::source)?\s+(['"])(?P<encoding>[\w-]+)\1""")


class PHPLangInfo(LangInfo):
    name = "PHP"
    conforms_to_bases = ["Text"]
    exts = [".php", ".inc"]
    magic_numbers = [
        (0, "string", "<?php"),
        (0, "regex", re.compile(r'\A#!.*php.*$', re.I | re.M)),
    ]
    #TODO: PHP files should inherit the HTML "<meta> charset" check
    #      and the XML prolog encoding check.


class TclLangInfo(LangInfo):
    name = "Tcl"
    conforms_to_bases = ["Text"]
    exts = ['.tcl']
    magic_numbers = [
        (0, "regex", re.compile(r'\A#!.*(tclsh|wish|expect).*$', re.I | re.M)),
        # As suggested here: http://www.tcl.tk/man/tcl8.4/UserCmd/tclsh.htm
        # Make sure we properly catch shebang lines like this:
        #   #!/bin/sh
        #   # the next line restarts using tclsh \
        #   exec tclsh "$0" "$@"
        (0, "regex", re.compile(r'\A#!.*^exec [^\r\n|\n|\r]*?(tclsh|wish|expect)',
                                re.I | re.M | re.S)),
    ]

class RubyLangInfo(LangInfo):
    name = "Ruby"
    conforms_to_bases = ["Text"]
    exts = ['.rb']
    filename_patterns = ["Rakefile"]
    magic_numbers = [
        (0, "regex", re.compile('\A#!.*ruby.*$', re.I | re.M)),
    ]
    #TODO: http://blade.nagaokaut.ac.jp/cgi-bin/scat.rb/ruby/ruby-core/12900
    #      Ruby uses similar (same?) coding decl as Python.

class JavaScriptLangInfo(LangInfo):
    name = "JavaScript"
    conforms_to_bases = ["Text"]
    exts = ['.js']

class CLangInfo(LangInfo):
    #TODO: rationalize with C++ and Komodo's usage
    name = "C"
    conforms_to_bases = ["Text"]
    exts = [
        ".c", 
        ".xs",  # Perl extension modules. *Are* they legal C?
    ]
    #TODO: Note for Jan:
    # .xs files are *NOT* legal C or C++ code.  However, they are
    # similar enough that I find it useful to edit them using c-mode or
    # c++-mode in Emacs.

class CPlusPlusLangInfo(LangInfo):
    #TODO: consider breaking out headers and have separate
    #      scintilla_lexer attr
    name = "C++"
    conforms_to_bases = ["Text"]
    exts = [
              ".c++", ".cpp", ".cxx",
        ".h", ".h++", ".hpp", ".hxx",
        ".xs",  # Perl extension modules. *Are* they legal C++?
    ]

class ADALangInfo(LangInfo):
    name = "Ada"
    conforms_to_bases = ["Text"]
    exts = [".ada"]

class NTBatchLangInfo(LangInfo):
    name = "Batch"
    conforms_to_bases = ["Text"]
    exts = [".bat", ".cmd"]  #TODO ".com"?

class BashLangInfo(LangInfo):
    name = "Bash"
    conforms_to_bases = ["Text"]
    exts = [".sh"]

class CSharpLangInfo(LangInfo):
    name = "C#"
    conforms_to_bases = ["Text"]
    exts = [".cs"]

class ErlangLangInfo(LangInfo):
    name = "Erlang"
    conforms_to_bases = ["Text"]
    exts = [".erl"]

class Fortran77LangInfo(LangInfo):
    name = "Fortran 77"
    conforms_to_bases = ["Text"]
    exts = [".f"]

class Fortran95LangInfo(LangInfo):
    name = "Fortran"
    conforms_to_bases = ["Text"]
    exts = [".f95"]

class JavaLangInfo(LangInfo):
    name = "Java"
    conforms_to_bases = ["Text"]
    exts = [".java", ".jav"]

class LispLangInfo(LangInfo):
    name = "Lisp"
    conforms_to_bases = ["Text"]
    exts = [".lis"]

class LuaLangInfo(LangInfo):
    name = "Lua"
    conforms_to_bases = ["Text"]
    exts = [".lua"]

class PascalLangInfo(LangInfo):
    name = "Pascal"
    conforms_to_bases = ["Text"]
    exts = [".pas"]

class SmalltalkLangInfo(LangInfo):
    name = "Smalltalk"
    conforms_to_bases = ["Text"]
    exts = [".st"]


