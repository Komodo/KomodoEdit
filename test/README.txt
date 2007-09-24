README for the Komodo test suite
================================

Note: "bk test" is just a shortcut for (1) running `test.py` in this
directory and (2) doing so with your configured mozilla environment -- i.e.
your `bkconfig.py`.


A "bk test" primer
------------------

	$ bk test

This runs the whole Komodo test suite (such as it is). Note that there are many test-y things spread around Komodo, but the "test suite" that I'm talking about here is stuff under: 

	Komodo-devel/test/suite

As of right now: no PyXPCOM stuff, no running Komodo, no Casper, no GUI.


	$ bk test foo bar baz

Those are *tags* used to (1) filter the set of test files run and (2) are also passed to those tests so they can sub-filter based on the tags. Some examples:

	$ bk test xdebug   # run test/suite/test_xdebug.py

	$ bk test dbgp     # run all the DBGP tests (.../test_dbgp.py)

	$ bk test -- -xdebug  # run everything *except* test_xdebug

(Note that to use the "-foo" trick you need to explicitly stop option processing with the "--".)


Some examples of sub-filtering:

	$ bk test dbgp python   # run just the *Python* DBGP tests
	$ bk test dbgp perl     # guess

        $ bk test dbgp python
	test_dbgp:python2.2:goodbyeworld.test ... ok
	test_dbgp:python2.2:helloworld.test ... ok
	test_dbgp:python2.3:goodbyeworld.test ... ok
	test_dbgp:python2.3:helloworld.test ... ok
	test_dbgp:python2.4:goodbyeworld.test ... ok
	test_dbgp:python2.4:helloworld.test ... ok

	$ bk test dbgp python hello
	test_dbgp:python2.2:helloworld.test ... ok
	test_dbgp:python2.3:helloworld.test ... ok
	test_dbgp:python2.4:helloworld.test ... ok

	$ bk test dbgp python hello 2.3
	test_dbgp:python2.3:helloworld.test ... ok


Full glorious details:

	$ bk test -h



How do I add new tests?
-----------------------

1. Add a test/suite/test_*.py file. Start with 'test_xdebug.py'.
2. Consider extending the README.txt in that directory with things that you found confusing when adding a new test.



How do I add new DBGP tests?
----------------------------

TODO




