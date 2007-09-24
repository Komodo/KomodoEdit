This is the test suite for process.py. To run the test suite:

1. Build the support executables that the test suite needs:
   On Windows:

        nmake

   On Un*x:

        make -f Makefile.unix

2. Run the test suite:

        python test.py


TODO:
- add tests for process.Process(), currently only test
  process.ProcessProxy(). (XXX Not sure this is true anymore.)

