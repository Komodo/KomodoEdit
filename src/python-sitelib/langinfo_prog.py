# Copyright (c) 2007 ActiveState Software Inc.

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
    exts = [".bat"]  #TODO ".com"?

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


