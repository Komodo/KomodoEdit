README for the Komodo test suite
================================

Note: "bk test" is just a shortcut for (1) running `test.py` in this
directory and (2) doing so with your configured mozilla environment -- i.e.
your `bkconfig.py`.


A "bk test" primer
------------------

	$ bk test

This runs the whole Komodo test suite (such as it is). Note that there are
many test-y things spread around Komodo, but the "test suite" that I'm
talking about here is stuff under the "test" directory.

As of right now: no running Komodo, no Casper, no GUI. However, PyXPCOM tests
run outside of Komodo *are* supported.


	$ bk test foo bar baz

Those are *tags* used to (1) filter the set of test files run and (2) are
also passed to those tests so they can sub-filter based on the tags. Some
examples:

	$ bk test ci            # run all CodeIntel tests
	$ bk test runcommand    # run all run-command system tests
	$ bk test -- -ci        # run everything *except* CodeIntel tests

(Note that to use the "-foo" trick you need to explicitly stop option
processing with the "--".)

You can use multiple tags:

	$ bk test ci python     # run just the Python-related CodeIntel tests

Full glorious details:

	$ bk test -h



How do I add new tests?
-----------------------

To add a new test you generally need to add or extend a "test_*.py" module in
the appropriate place. The test suite is based upon Python's unittest.py
module. Some knowledge of unittest is useful
(http://docs.python.org/lib/module-unittest.html).

If your test cases use PyXPCOM modules, then add a module under
"test/pyxpcom/...". If your tests cases just test a pure-Python system in
Komodo, add a module in the "test" dir.  To add tests to the CodeIntel
system, see the "src/codeintel/test2/..." directory.

If you have difficulties adding a new test, please ask on the OpenKomodo
development list:

    http://lists.openkomodo.com/mailman/listinfo/openkomodo-dev


