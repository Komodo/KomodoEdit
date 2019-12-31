# Module doctest version 0.9.6
# Released to the public domain 16-Jan-2001,
# by Tim Peters (tim.one@home.com).

# local modifications:
# 2001-02-13 fl: minor tweaks to make it run under both 1.5.2 and 2.0

# Provided as-is; use at your own risk; no warranty; no promises; enjoy!

"""Module doctest -- a framework for running examples in docstrings.

NORMAL USAGE

In normal use, end each module M with:

def _test():
    import doctest, M           # replace M with your module's name
    return doctest.testmod(M)   # ditto

if __name__ == "__main__":
    _test()

Then running the module as a script will cause the examples in the
docstrings to get executed and verified:

python M.py

This won't display anything unless an example fails, in which case the
failing example(s) and the cause(s) of the failure(s) are printed to stdout
(why not stderr? because stderr is a lame hack <0.2 wink>), and the final
line of output is "Test failed.".

Run it with the -v switch instead:

python M.py -v

and a detailed report of all examples tried is printed to stdout, along
with assorted summaries at the end.

You can force verbose mode by passing "verbose=1" to testmod, or prohibit
it by passing "verbose=0".  In either of those cases, sys.argv is not
examined by testmod.

In any case, testmod returns a 2-tuple of ints (f, t), where f is the
number of docstring examples that failed and t is the total number of
docstring examples attempted.


WHICH DOCSTRINGS ARE EXAMINED?

+ M.__doc__.

+ f.__doc__ for all functions f in M.__dict__.values(), except those
  with private names.

+ C.__doc__ for all classes C in M.__dict__.values(), except those with
  private names.

+ If M.__test__ exists and "is true", it must be a dict, and
  each entry maps a (string) name to a function object, class object, or
  string.  Function and class object docstrings found from M.__test__
  are searched even if the name is private, and strings are searched
  directly as if they were docstrings.  In output, a key K in M.__test__
  appears with name
      <name of M>.__test__.K

Any classes found are recursively searched similarly, to test docstrings in
their contained methods and nested classes.  Private names reached from M's
globals are skipped, but all names reached from M.__test__ are searched.

By default, a name is considered to be private if it begins with an
underscore (like "_my_func") but doesn't both begin and end with (at least)
two underscores (like "__init__").  You can change the default by passing
your own "isprivate" function to testmod.

If you want to test docstrings in objects with private names too, stuff
them into an M.__test__ dict, or see ADVANCED USAGE below (e.g., pass your
own isprivate function to Tester's constructor, or call the rundoc method
of a Tester instance).

Warning:  imports can cause trouble; e.g., if you do

from XYZ import XYZclass

then XYZclass is a name in M.__dict__ too, and doctest has no way to know
that XYZclass wasn't *defined* in M.  So it may try to execute the examples
in XYZclass's docstring, and those in turn may require a different set of
globals to work correctly.  I prefer to do "import *"- friendly imports,
a la

import XYY
_XYZclass = XYZ.XYZclass
del XYZ

or (Python 2.0)

from XYZ import XYZclass as _XYZclass

and then the leading underscore stops testmod from going nuts.  You may
prefer the method in the next section.


WHAT'S THE EXECUTION CONTEXT?

By default, each time testmod finds a docstring to test, it uses a *copy*
of M's globals (so that running tests on a module doesn't change the
module's real globals, and so that one test in M can't leave behind crumbs
that accidentally allow another test to work).  This means examples can
freely use any names defined at top-level in M.  It also means that sloppy
imports (see above) can cause examples in external docstrings to use
globals inappropriate for them.

You can force use of your own dict as the execution context by passing
"globs=your_dict" to testmod instead.  Presumably this would be a copy of
M.__dict__ merged with the globals from other imported modules.


WHAT IF I WANT TO TEST A WHOLE PACKAGE?

Piece o' cake, provided the modules do their testing from docstrings.
Here's the test.py I use for the world's most elaborate Rational/
floating-base-conversion pkg (which I'll distribute some day):

from Rational import Cvt
from Rational import Format
from Rational import machprec
from Rational import Rat
from Rational import Round
from Rational import utils

modules = (Cvt,
           Format,
           machprec,
           Rat,
           Round,
           utils)

def _test():
    import doctest
    import sys
    verbose = "-v" in sys.argv
    for mod in modules:
        doctest.testmod(mod, verbose=verbose, report=0)
    doctest.master.summarize()

if __name__ == "__main__":
    _test()

IOW, it just runs testmod on all the pkg modules.  testmod remembers the
names and outcomes (# of failures, # of tries) for each item it's seen, and
passing "report=0" prevents it from printing a summary in verbose mode.
Instead, the summary is delayed until all modules have been tested, and
then "doctest.master.summarize()" forces the summary at the end.

So this is very nice in practice:  each module can be tested individually
with almost no work beyond writing up docstring examples, and collections
of modules can be tested too as a unit with no more work than the above.


WHAT ABOUT EXCEPTIONS?

No problem, as long as the only output generated by the example is the
traceback itself.  For example:

    >>> a = [None]
    >>> a[1]
    Traceback (innermost last):
      File "<stdin>", line 1, in ?
    IndexError: list index out of range
    >>>

Note that only the exception type and value are compared (specifically,
only the last line in the traceback).


ADVANCED USAGE

doctest.testmod() captures the testing policy I find most useful most
often.  You may want other policies.

testmod() actually creates a local instance of class doctest.Tester, runs
appropriate methods of that class, and merges the results into global
Tester instance doctest.master.

You can create your own instances of doctest.Tester, and so build your own
policies, or even run methods of doctest.master directly.  See
doctest.Tester.__doc__ for details.


SO WHAT DOES A DOCSTRING EXAMPLE LOOK LIKE ALREADY!?

Oh ya.  It's easy!  In most cases a copy-and-paste of an interactive
console session works fine -- just make sure the leading whitespace is
rigidly consistent (you can mix tabs and spaces if you're too lazy to do it
right, but doctest is not in the business of guessing what you think a tab
means).

    >>> # comments are ignored
    >>> x = 12
    >>> x
    12
    >>> if x == 13:
    ...     print "yes"
    ... else:
    ...     print "no"
    ...     print "NO"
    ...     print "NO!!!"
    ...
    no
    NO
    NO!!!
    >>>

Any expected output must immediately follow the final ">>>" or "..." line
containing the code, and the expected output (if any) extends to the next
">>>" or all-whitespace line.  That's it.

Bummers:

+ Expected output cannot contain an all-whitespace line, since such a line
  is taken to signal the end of expected output.

+ Output to stdout is captured, but not output to stderr (exception
  tracebacks are captured via a different means).

+ If you continue a line via backslashing in an interactive session, or for
  any other reason use a backslash, you need to double the backslash in the
  docstring version.  This is simply because you're in a string, and so the
  backslash must be escaped for it to survive intact.  Like:

>>> if "yes" == \\
...     "y" +   \\
...     "es":   # in the source code you'll see the doubled backslashes
...     print 'yes'
yes

The starting column doesn't matter:

>>> assert "Easy!"
     >>> import math
            >>> math.floor(1.9)
            1.0

and as many leading whitespace characters are stripped from the expected
output as appeared in the initial ">>>" line that triggered it.

If you execute this very file, the examples above will be found and
executed, leading to this output in verbose mode:

Running doctest.__doc__
Trying: a = [None]
Expecting: nothing
ok
Trying: a[1]
Expecting:
Traceback (innermost last):
  File "<stdin>", line 1, in ?
IndexError: list index out of range
ok
Trying: x = 12
Expecting: nothing
ok
Trying: x
Expecting: 12
ok
Trying:
if x == 13:
    print "yes"
else:
    print "no"
    print "NO"
    print "NO!!!"
Expecting:
no
NO
NO!!!
ok
... and a bunch more like that, with this summary at the end:

5 items had no tests:
    doctest.Tester.__init__
    doctest.Tester.run__test__
    doctest.Tester.summarize
    doctest.run_docstring_examples
    doctest.testmod
12 items passed all tests:
   9 tests in doctest
   6 tests in doctest.Tester
  10 tests in doctest.Tester.merge
   7 tests in doctest.Tester.rundict
   3 tests in doctest.Tester.rundoc
   3 tests in doctest.Tester.runstring
   2 tests in doctest.__test__._TestClass
   2 tests in doctest.__test__._TestClass.__init__
   2 tests in doctest.__test__._TestClass.get
   1 tests in doctest.__test__._TestClass.square
   2 tests in doctest.__test__.string
   7 tests in doctest.is_private
54 tests in 17 items.
54 passed and 0 failed.
Test passed.
"""
from __future__ import print_function

# 0,0,1    06-Mar-1999
#    initial version posted
# 0,0,2    06-Mar-1999
#    loosened parsing:
#        cater to stinkin' tabs
#        don't insist on a blank after PS2 prefix
#            so trailing "... " line from a compound stmt no longer
#            breaks if the file gets whitespace-trimmed
#    better error msgs for inconsistent leading whitespace
# 0,9,1    08-Mar-1999
#    exposed the Tester class and added client methods
#        plus docstring examples of their use (eww - head-twisting!)
#    fixed logic error in reporting total # of tests & failures
#    added __test__ support to testmod (a pale reflection of Christian
#        Tismer's vision ...)
#    removed the "deep" argument; fiddle __test__ instead
#    simplified endcase logic for extracting tests, and running them.
#        before, if no output was expected but some was produced
#        anyway via an eval'ed result, the discrepancy wasn't caught
#    made TestClass private and used __test__ to get at it
#    many doc updates
#    speed _SpoofOut for long expected outputs
# 0,9,2    09-Mar-1999
#    throw out comments from examples, enabling use of the much simpler
#        exec compile(... "single") ...
#        for simulating the runtime; that barfs on comment-only lines
#    used the traceback module to do a much better job of reporting
#        exceptions
#    run __doc__ values thru str(), "just in case"
#    privateness of names now determined by an overridable "isprivate"
#        function
#    by default a name now considered to be private iff it begins with
#        an underscore but doesn't both begin & end with two of 'em; so
#        e.g. Class.__init__ etc are searched now -- as they always
#        should have been
# 0,9,3    18-Mar-1999
#    added .flush stub to _SpoofOut (JPython buglet diagnosed by
#        Hugh Emberson)
#    repaired ridiculous docs about backslashes in examples
#    minor internal changes
#    changed source to Unix line-end conventions
#    moved __test__ logic into new Tester.run__test__ method
# 0,9,4    27-Mar-1999
#    report item name and line # in failing examples
# 0,9,5    29-Jun-1999
#    allow straightforward exceptions in examples - thanks to Mark Hammond!
# 0,9,6    16-Jan-2001
#    fiddling for changes in Python 2.0:  some of the embedded docstring
#        examples no longer worked *exactly* as advertised, due to minor
#        language changes, and running doctest on itself pointed that out.
#        Hard to think of a better example of why this is useful <wink>.

__version__ = 0, 9, 6

import types
_FunctionType = types.FunctionType
_ClassType    = type
_ModuleType   = types.ModuleType
_StringType   = bytes
del types

import string
_string_find = string.find
_string_join = string.join
_string_split = string.split
_string_rindex = string.rindex
del string

import re
PS1 = ">>>"
PS2 = "..."
_isPS1 = re.compile(r"(\s*)" + re.escape(PS1)).match
_isPS2 = re.compile(r"(\s*)" + re.escape(PS2)).match
_isEmpty = re.compile(r"\s*$").match
_isComment = re.compile(r"\s*#").match
del re

__all__ = []

# Extract interactive examples from a string.  Return a list of triples,
# (source, outcome, lineno).  "source" is the source code, and ends
# with a newline iff the source spans more than one line.  "outcome" is
# the expected output if any, else an empty string.  When not empty,
# outcome always ends with a newline.  "lineno" is the line number,
# 0-based wrt the start of the string, of the first source line.

def _extract_examples(s):
    isPS1, isPS2 = _isPS1, _isPS2
    isEmpty, isComment = _isEmpty, _isComment
    examples = []
    lines = _string_split(s, "\n")
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        i = i + 1
        m = isPS1(line)
        if m is None:
            continue
        j = m.end(0)  # beyond the prompt
        if isEmpty(line, j) or isComment(line, j):
            # a bare prompt or comment -- not interesting
            continue
        lineno = i - 1
        if line[j] != " ":
            raise ValueError("line " + repr(lineno) + " of docstring lacks "
                "blank after " + PS1 + ": " + line)
        j = j + 1
        blanks = m.group(1)
        nblanks = len(blanks)
        # suck up this and following PS2 lines
        source = []
        while 1:
            source.append(line[j:])
            line = lines[i]
            m = isPS2(line)
            if m:
                if m.group(1) != blanks:
                    raise ValueError("inconsistent leading whitespace "
                        "in line " + repr(i) + " of docstring: " + line)
                i = i + 1
            else:
                break
        if len(source) == 1:
            source = source[0]
        else:
            # get rid of useless null line from trailing empty "..."
            if source[-1] == "":
                del source[-1]
            source = _string_join(source, "\n") + "\n"
        # suck up response
        if isPS1(line) or isEmpty(line):
            expect = ""
        else:
            expect = []
            while 1:
                if line[:nblanks] != blanks:
                    raise ValueError("inconsistent leading whitespace "
                        "in line " + repr(i) + " of docstring: " + line)
                expect.append(line[nblanks:])
                i = i + 1
                line = lines[i]
                if isPS1(line) or isEmpty(line):
                    break
            expect = _string_join(expect, "\n") + "\n"
        examples.append( (source, expect, lineno) )
    return examples

# Capture stdout when running examples.

class _SpoofOut:
    def __init__(self):
        self.clear()
    def write(self, s):
        self.buf.append(s)
    def get(self):
        return _string_join(self.buf, "")
    def clear(self):
        self.buf = []
    def flush(self):
        # JPython calls flush
        pass

# Display some tag-and-msg pairs nicely, keeping the tag and its msg
# on the same line when that makes sense.

def _tag_out(printer, *tag_msg_pairs):
    for tag, msg in tag_msg_pairs:
        printer(tag + ":")
        msg_has_nl = msg[-1:] == "\n"
        msg_has_two_nl = msg_has_nl and \
                        _string_find(msg, "\n") < len(msg) - 1
        if len(tag) + len(msg) < 76 and not msg_has_two_nl:
            printer(" ")
        else:
            printer("\n")
        printer(msg)
        if not msg_has_nl:
            printer("\n")

# Run list of examples, in context globs.  "out" can be used to display
# stuff to "the real" stdout, and fakeout is an instance of _SpoofOut
# that captures the examples' std output.  Return (#failures, #tries).

def _run_examples_inner(out, fakeout, examples, globs, verbose, name):
    import sys, traceback
    OK, BOOM, FAIL = range(3)
    NADA = "nothing"
    stderr = _SpoofOut()
    failures = 0
    for source, want, lineno in examples:
        if verbose:
            _tag_out(out, ("Trying", source),
                          ("Expecting", want or NADA))
        fakeout.clear()
        try:
            exec(compile(source, "<string>", "single"), globs)
            got = fakeout.get()
            state = OK
        except:
            # See whether the exception was expected.
            if _string_find(want, "Traceback (innermost last):\n") == 0 or\
               _string_find(want, "Traceback (most recent call last):\n") == 0:
                # Only compare exception type and value - the rest of
                # the traceback isn't necessary.
                want = _string_split(want, '\n')[-2] + '\n'
                exc_type, exc_val, exc_tb = sys.exc_info()
                got = traceback.format_exception_only(exc_type, exc_val)[0]
                state = OK
            else:
                # unexpected exception
                stderr.clear()
                traceback.print_exc(file=stderr)
                state = BOOM

        if state == OK:
            if got == want:
                if verbose:
                    out("ok\n")
                continue
            state = FAIL

        assert state in (FAIL, BOOM)
        failures = failures + 1
        out("*" * 65 + "\n")
        _tag_out(out, ("Failure in example", source))
        out("from line #" + repr(lineno) + " of " + name + "\n")
        if state == FAIL:
            _tag_out(out, ("Expected", want or NADA), ("Got", got))
        else:
            assert state == BOOM
            _tag_out(out, ("Exception raised", stderr.get()))

    return failures, len(examples)

# Run list of examples, in context globs.  Return (#failures, #tries).

def _run_examples(examples, globs, verbose, name):
    import sys
    saveout = sys.stdout
    try:
        sys.stdout = fakeout = _SpoofOut()
        x = _run_examples_inner(saveout.write, fakeout, examples,
                                globs, verbose, name)
    finally:
        sys.stdout = saveout
    return x

def run_docstring_examples(f, globs, verbose=0, name="NoName"):
    """f, globs, verbose=0, name="NoName" -> run examples from f.__doc__.

    Use dict globs as the globals for execution.
    Return (#failures, #tries).

    If optional arg verbose is true, print stuff even if there are no
    failures.
    Use string name in failure msgs.
    """

    try:
        doc = f.__doc__
        if not doc:
            # docstring empty or None
            return 0, 0
        # just in case CT invents a doc object that has to be forced
        # to look like a string <0.9 wink>
        doc = str(doc)
    except:
        return 0, 0

    e = _extract_examples(doc)
    if not e:
        return 0, 0
    return _run_examples(e, globs, verbose, name)

def is_private(prefix, base):
    """prefix, base -> true iff name prefix + "." + base is "private".

    Prefix may be an empty string, and base does not contain a period.
    Prefix is ignored (although functions you write conforming to this
    protocol may make use of it).
    Return true iff base begins with an (at least one) underscore, but
    does not both begin and end with (at least) two underscores.

    >>> is_private("a.b", "my_func")
    0
    >>> is_private("____", "_my_func")
    1
    >>> is_private("someclass", "__init__")
    0
    >>> is_private("sometypo", "__init_")
    1
    >>> is_private("x.y.z", "_")
    1
    >>> is_private("_x.y.z", "__")
    0
    >>> is_private("", "")  # senseless but consistent
    0
    """

    return base[:1] == "_" and not base[:2] == "__" == base[-2:]

class Tester:
    """Class Tester -- runs docstring examples and accumulates stats.

In normal use, function doctest.testmod() hides all this from you,
so use that if you can.  Create your own instances of Tester to do
fancier things.

Methods:
    runstring(s, name)
        Search string s for examples to run; use name for logging.
        Return (#failures, #tries).

    rundoc(object, name=None)
        Search object.__doc__ for examples to run; use name (or
        object.__name__) for logging.  Return (#failures, #tries).

    rundict(d, name)
        Search for examples in docstrings in all of d.values(); use name
        for logging.  Return (#failures, #tries).

    run__test__(d, name)
        Treat dict d like module.__test__.  Return (#failures, #tries).

    summarize(verbose=None)
        Display summary of testing results, to stdout.  Return
        (#failures, #tries).

    merge(other)
        Merge in the test results from Tester instance "other".

>>> from doctest import Tester
>>> t = Tester(globs={'x': 42}, verbose=0)
>>> t.runstring(r'''
...      >>> x = x * 2
...      >>> print x
...      42
... ''', 'XYZ')
*****************************************************************
Failure in example: print x
from line #2 of XYZ
Expected: 42
Got: 84
(1, 2)
>>> t.runstring(">>> x = x * 2\\n>>> print x\\n84\\n", 'example2')
(0, 2)
>>> t.summarize()
1 items had failures:
   1 of   2 in XYZ
***Test Failed*** 1 failures.
(1, 4)
>>> t.summarize(verbose=1)
1 items passed all tests:
   2 tests in example2
1 items had failures:
   1 of   2 in XYZ
4 tests in 2 items.
3 passed and 1 failed.
***Test Failed*** 1 failures.
(1, 4)
>>>
"""

    def __init__(self, mod=None, globs=None, verbose=None,
                 isprivate=None):
        """mod=None, globs=None, verbose=None, isprivate=None

See doctest.__doc__ for an overview.

Optional keyword arg "mod" is a module, whose globals are used for
executing examples.  If not specified, globs must be specified.

Optional keyword arg "globs" gives a dict to be used as the globals
when executing examples; if not specified, use the globals from
module mod.

In either case, a copy of the dict is used for each docstring
examined.

Optional keyword arg "verbose" prints lots of stuff if true, only
failures if false; by default, it's true iff "-v" is in sys.argv.

Optional keyword arg "isprivate" specifies a function used to determine
whether a name is private.  The default function is doctest.is_private;
see its docs for details.
"""

        if mod is None and globs is None:
            raise TypeError("Tester.__init__: must specify mod or globs")
        if mod is not None and type(mod) is not _ModuleType:
            raise TypeError("Tester.__init__: mod must be a module; " +
                            repr(mod))
        if globs is None:
            globs = mod.__dict__
        self.globs = globs

        if verbose is None:
            import sys
            verbose = "-v" in sys.argv
        self.verbose = verbose

        if isprivate is None:
            isprivate = is_private
        self.isprivate = isprivate

        self.name2ft = {}   # map name to (#failures, #trials) pair

    def runstring(self, s, name):
        """
        s, name -> search string s for examples to run, logging as name.

        Use string name as the key for logging the outcome.
        Return (#failures, #examples).

        >>> t = Tester(globs={}, verbose=1)
        >>> test = r'''
        ...    # just an example
        ...    >>> x = 1 + 2
        ...    >>> x
        ...    3
        ... '''
        >>> t.runstring(test, "Example")
        Running string Example
        Trying: x = 1 + 2
        Expecting: nothing
        ok
        Trying: x
        Expecting: 3
        ok
        0 of 2 examples failed in string Example
        (0, 2)
        """

        if self.verbose:
            print("Running string", name)
        f = t = 0
        e = _extract_examples(s)
        if e:
            f, t = _run_examples(e, self.globs.copy(), self.verbose, name)
        if self.verbose:
            print(f, "of", t, "examples failed in string", name)
        self.__record_outcome(name, f, t)
        return f, t

    def rundoc(self, object, name=None):
        """
        object, name=None -> search object.__doc__ for examples to run.

        Use optional string name as the key for logging the outcome;
        by default use object.__name__.
        Return (#failures, #examples).
        If object is a class object, search recursively for method
        docstrings too.
        object.__doc__ is examined regardless of name, but if object is
        a class, whether private names reached from object are searched
        depends on the constructor's "isprivate" argument.

        >>> t = Tester(globs={}, verbose=0)
        >>> def _f():
        ...     '''Trivial docstring example.
        ...     >>> assert 2 == 2
        ...     '''
        ...     return 32
        ...
        >>> t.rundoc(_f)  # expect 0 failures in 1 example
        (0, 1)
        """

        if name is None:
            try:
                name = object.__name__
            except AttributeError:
                raise ValueError("Tester.rundoc: name must be given "
                    "when object.__name__ doesn't exist; " + repr(object))
        if self.verbose:
            print("Running", name + ".__doc__")
        f, t = run_docstring_examples(object, self.globs.copy(),
                                      self.verbose, name)
        if self.verbose:
            print(f, "of", t, "examples failed in", name + ".__doc__")
        self.__record_outcome(name, f, t)
        if type(object) is _ClassType:
            f2, t2 = self.rundict(object.__dict__, name)
            f = f + f2
            t = t + t2
        return f, t

    def rundict(self, d, name):
        """
        d. name -> search for docstring examples in all of d.values().

        For k, v in d.items() such that v is a function or class,
        do self.rundoc(v, name + "." + k).  Whether this includes
        objects with private names depends on the constructor's
        "isprivate" argument.
        Return aggregate (#failures, #examples).

        >>> def _f():
        ...    '''>>> assert 1 == 1
        ...    '''
        >>> def g():
        ...    '''>>> assert 2 != 1
        ...    '''
        >>> d = {"_f": _f, "g": g}
        >>> t = Tester(globs={}, verbose=0)
        >>> t.rundict(d, "rundict_test")  # _f is skipped
        (0, 1)
        >>> t = Tester(globs={}, verbose=0, isprivate=lambda x,y: 0)
        >>> t.rundict(d, "rundict_test_pvt")  # both are searched
        (0, 2)
        """

        if not hasattr(d, "items"):
            raise TypeError("Tester.rundict: d must support .items(); " +
                            repr(d))
        f = t = 0
        for thisname, value in d.items():
            if type(value) in (_FunctionType, _ClassType):
                f2, t2 = self.__runone(value, name + "." + thisname)
                f = f + f2
                t = t + t2
        return f, t

    def run__test__(self, d, name):
        """d, name -> Treat dict d like module.__test__.

        Return (#failures, #tries).
        See testmod.__doc__ for details.
        """

        failures = tries = 0
        prefix = name + "."
        savepvt = self.isprivate
        try:
            self.isprivate = lambda *args: 0
            for k, v in d.items():
                thisname = prefix + k
                if type(v) is _StringType:
                    f, t = self.runstring(v, thisname)
                elif type(v) in (_FunctionType, _ClassType):
                    f, t = self.rundoc(v, thisname)
                else:
                    raise TypeError("Tester.run__test__: values in "
                            "dict must be strings, functions "
                            "or classes; " + repr(v))
                failures = failures + f
                tries = tries + t
        finally:
            self.isprivate = savepvt
        return failures, tries

    def summarize(self, verbose=None):
        """
        verbose=None -> summarize results, return (#failures, #tests).

        Print summary of test results to stdout.
        Optional arg 'verbose' controls how wordy this is.  By
        default, use the verbose setting established by the
        constructor.
        """

        if verbose is None:
            verbose = self.verbose
        notests = []
        passed = []
        failed = []
        totalt = totalf = 0
        for x in self.name2ft.items():
            name, (f, t) = x
            assert f <= t
            totalt = totalt + t
            totalf = totalf + f
            if t == 0:
                notests.append(name)
            elif f == 0:
                passed.append( (name, t) )
            else:
                failed.append(x)
        if verbose:
            if notests:
                print(len(notests), "items had no tests:")
                notests.sort()
                for thing in notests:
                    print("   ", thing)
            if passed:
                print(len(passed), "items passed all tests:")
                passed.sort()
                for thing, count in passed:
                    print(" %3d tests in %s" % (count, thing))
        if failed:
            print(len(failed), "items had failures:")
            failed.sort()
            for thing, (f, t) in failed:
                print(" %3d of %3d in %s" % (f, t, thing))
        if verbose:
            print(totalt, "tests in", len(self.name2ft), "items.")
            print(totalt - totalf, "passed and", totalf, "failed.")
        if totalf:
            print("***Test Failed***", totalf, "failures.")
        elif verbose:
            print("Test passed.")
        return totalf, totalt

    def merge(self, other):
        """
        other -> merge in test results from the other Tester instance.

        If self and other both have a test result for something
        with the same name, the (#failures, #tests) results are
        summed, and a warning is printed to stdout.

        >>> from doctest import Tester
        >>> t1 = Tester(globs={}, verbose=0)
        >>> t1.runstring('''
        ... >>> x = 12
        ... >>> print x
        ... 12
        ... ''', "t1example")
        (0, 2)
        >>>
        >>> t2 = Tester(globs={}, verbose=0)
        >>> t2.runstring('''
        ... >>> x = 13
        ... >>> print x
        ... 13
        ... ''', "t2example")
        (0, 2)
        >>> common = ">>> assert 1 + 2 == 3\\n"
        >>> t1.runstring(common, "common")
        (0, 1)
        >>> t2.runstring(common, "common")
        (0, 1)
        >>> t1.merge(t2)
        *** Tester.merge: 'common' in both testers; summing outcomes.
        >>> t1.summarize(1)
        3 items passed all tests:
           2 tests in common
           2 tests in t1example
           2 tests in t2example
        6 tests in 3 items.
        6 passed and 0 failed.
        Test passed.
        (0, 6)
        >>>
        """

        d = self.name2ft
        for name, (f, t) in other.name2ft.items():
            if name in d:
                print("*** Tester.merge: '" + name + "' in both" \
                    " testers; summing outcomes.")
                f2, t2 = d[name]
                f = f + f2
                t = t + t2
            d[name] = f, t

    def __record_outcome(self, name, f, t):
        if name in self.name2ft:
            print("*** Warning: '" + name + "' was tested before;", \
                "summing outcomes.")
            f2, t2 = self.name2ft[name]
            f = f + f2
            t = t + t2
        self.name2ft[name] = f, t

    def __runone(self, target, name):
        if "." in name:
            i = _string_rindex(name, ".")
            prefix, base = name[:i], name[i+1:]
        else:
            prefix, base = "", base
        if self.isprivate(prefix, base):
            return 0, 0
        return self.rundoc(target, name)

master = None

def testmod(m, name=None, globs=None, verbose=None, isprivate=None,
               report=1):
    """m, name=None, globs=None, verbose=None, isprivate=None, report=1

    Test examples in docstrings in functions and classes reachable from
    module m, starting with m.__doc__.  Private names are skipped.

    Also test examples reachable from dict m.__test__ if it exists and is
    not None.  m.__dict__ maps names to functions, classes and strings;
    function and class docstrings are tested even if the name is private;
    strings are tested directly, as if they were docstrings.

    Return (#failures, #tests).

    See doctest.__doc__ for an overview.

    Optional keyword arg "name" gives the name of the module; by default
    use m.__name__.

    Optional keyword arg "globs" gives a dict to be used as the globals
    when executing examples; by default, use m.__dict__.  A copy of this
    dict is actually used for each docstring, so that each docstring's
    examples start with a clean slate.

    Optional keyword arg "verbose" prints lots of stuff if true, prints
    only failures if false; by default, it's true iff "-v" is in sys.argv.

    Optional keyword arg "isprivate" specifies a function used to
    determine whether a name is private.  The default function is
    doctest.is_private; see its docs for details.

    Optional keyword arg "report" prints a summary at the end when true,
    else prints nothing at the end.  In verbose mode, the summary is
    detailed, else very brief (in fact, empty if all tests passed).

    Advanced tomfoolery:  testmod runs methods of a local instance of
    class doctest.Tester, then merges the results into (or creates)
    global Tester instance doctest.master.  Methods of doctest.master
    can be called directly too, if you want to do something unusual.
    Passing report=0 to testmod is especially useful then, to delay
    displaying a summary.  Invoke doctest.master.summarize(verbose)
    when you're done fiddling.
    """

    global master

    if type(m) is not _ModuleType:
        raise TypeError("testmod: module required; " + repr(m))
    if name is None:
        name = m.__name__
    tester = Tester(m, globs=globs, verbose=verbose, isprivate=isprivate)
    failures, tries = tester.rundoc(m, name)
    f, t = tester.rundict(m.__dict__, name)
    failures = failures + f
    tries = tries + t
    if hasattr(m, "__test__"):
        testdict = m.__test__
        if testdict:
            if not hasattr(testdict, "items"):
                raise TypeError("testmod: module.__test__ must support "
                                ".items(); " + repr(testdict))
            f, t = tester.run__test__(testdict, name + ".__test__")
            failures = failures + f
            tries = tries + t
    if report:
        tester.summarize()
    if master is None:
        master = tester
    else:
        master.merge(tester)
    return failures, tries

class _TestClass:
    """
    A pointless class, for sanity-checking of docstring testing.

    Methods:
        square()
        get()

    >>> _TestClass(13).get() + _TestClass(-12).get()
    1
    >>> hex(_TestClass(13).square().get())
    '0xa9'
    """

    def __init__(self, val):
        """val -> _TestClass object with associated value val.

        >>> t = _TestClass(123)
        >>> print t.get()
        123
        """

        self.val = val

    def square(self):
        """square() -> square TestClass's associated value

        >>> _TestClass(13).square().get()
        169
        """

        self.val = self.val ** 2
        return self

    def get(self):
        """get() -> return TestClass's associated value.

        >>> x = _TestClass(-42)
        >>> print x.get()
        -42
        """

        return self.val

__test__ = {"_TestClass": _TestClass,
            "string": r"""
                      Example of a string object, searched as-is.
                      >>> x = 1; y = 2
                      >>> x + y, x * y
                      (3, 2)
                      """
           }

def _test():
    import doctest
    return doctest.testmod(doctest)

if __name__ == "__main__":
    _test()
