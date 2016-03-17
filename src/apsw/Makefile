
SQLITEVERSION=3.8.11.1
APSWSUFFIX=-r1

RELEASEDATE="20 August 2015"

VERSION=$(SQLITEVERSION)$(APSWSUFFIX)
VERDIR=apsw-$(VERSION)

PYTHON=python

# Some useful info
#
# To use a different SQLite version: make SQLITEVERSION=1.2.3 blah blah
#
# build_ext      - builds extension in current directory fetching sqlite
# test           - builds extension in place then runs test suite
# doc            - makes the doc
# source         - makes a source zip in dist directory after running code through test suite

GENDOCS = \
	doc/blob.rst \
	doc/vfs.rst \
	doc/vtable.rst \
	doc/connection.rst \
	doc/cursor.rst \
	doc/apsw.rst \
	doc/backup.rst

.PHONY : all docs doc header linkcheck publish showsymbols compile-win source source_nocheck release tags clean ppa dpkg dpkg-bin coverage valgrind valgrind1 tagpush

all: header docs

tagpush:
	git tag -af $(SQLITEVERSION)$(APSWSUFFIX)
	git push --tags

clean:
	make PYTHONPATH="`pwd`" VERSION=$(VERSION) -C doc clean
	rm -rf dist build work/* megatestresults
	mkdir dist
	for i in '*.pyc' '*.pyo' '*~' '*.o' '*.so' '*.dll' '*.pyd' '*.gcov' '*.gcda' '*.gcno' '*.orig' '*.tmp' 'testdb*' 'testextension.sqlext' ; do \
		find . -type f -name "$$i" -print0 | xargs -0t --no-run-if-empty rm -f ; done

doc: docs

docs: build_ext $(GENDOCS) doc/example.rst doc/.static
	env PYTHONPATH=. http_proxy= $(PYTHON) tools/docmissing.py
	env PYTHONPATH=. http_proxy= $(PYTHON) tools/docupdate.py $(VERSION)
	make PYTHONPATH="`pwd`" VERSION=$(VERSION) RELEASEDATE=$(RELEASEDATE) -C doc clean html

doc/example.rst: example-code.py tools/example2rst.py src/apswversion.h
	rm -f dbfile
	env PYTHONPATH=. $(PYTHON) tools/example2rst.py

doc/.static:
	mkdir -p doc/.static

# This is probably gnu make specific but only developers use this makefile
$(GENDOCS): doc/%.rst: src/%.c tools/code2rst.py
	env PYTHONPATH=. http_proxy= $(PYTHON) tools/code2rst.py $(SQLITEVERSION) $< $@

build_ext:
	$(PYTHON) setup.py fetch --version=$(SQLITEVERSION) --all build_ext --inplace --force --enable-all-extensions

coverage:
	$(PYTHON) setup.py fetch --version=$(SQLITEVERSION) --all && env APSW_PY_COVERAGE=t tools/coverage.sh

test: build_ext
	$(PYTHON) tests.py

debugtest:
	gcc -pthread -fno-strict-aliasing -g -fPIC -Wall -DAPSW_USE_SQLITE_CONFIG=\"sqlite3/sqlite3config.h\" -DEXPERIMENTAL -DSQLITE_DEBUG -DAPSW_USE_SQLITE_AMALGAMATION=\"sqlite3.c\" -DAPSW_NO_NDEBUG -DAPSW_TESTFIXTURES -I`$(PYTHON) -c "import distutils.sysconfig,sys; sys.stdout.write(distutils.sysconfig.get_python_inc())"` -I. -Isqlite3 -Isrc -c src/apsw.c
	gcc -pthread -g -shared apsw.o -o apsw.so
	$(PYTHON) tests.py $(APSWTESTS)

# Needs a debug python.  Look at the final numbers at the bottom of
# l6, l7 and l8 and see if any are growing
valgrind: /space/pydebug/bin/python
	$(PYTHON) setup.py fetch --version=$(SQLITEVERSION) --all && \
	  env APSWTESTPREFIX=/tmp/ PATH=/space/pydebug/bin:$$PATH SHOWINUSE=t APSW_TEST_ITERATIONS=6 tools/valgrind.sh 2>&1 | tee l6 && \
	  env APSWTESTPREFIX=/tmp/ PATH=/space/pydebug/bin:$$PATH SHOWINUSE=t APSW_TEST_ITERATIONS=7 tools/valgrind.sh 2>&1 | tee l7 && \
	  env APSWTESTPREFIX=/tmp/ PATH=/space/pydebug/bin:$$PATH SHOWINUSE=t APSW_TEST_ITERATIONS=8 tools/valgrind.sh 2>&1 | tee l8

# Same as above but does just one run
valgrind1: /space/pydebug/bin/python
	$(PYTHON) setup.py fetch --version=$(SQLITEVERSION) --all && \
	  env APSWTESTPREFIX=/tmp/ PATH=/space/pydebug/bin:$$PATH SHOWINUSE=t APSW_TEST_ITERATIONS=1 tools/valgrind.sh


linkcheck:
	make RELEASEDATE=$(RELEASEDATE) VERSION=$(VERSION) -C doc linkcheck

publish: docs
	if [ -d ../apsw-publish ] ; then rm -f ../apsw-publish/* ../apsw-publish/_static/* ../apsw-publish/_sources/* ; \
	rsync -a doc/build/html/ ../apsw-publish/ ;  cd ../apsw-publish ; git status ; \
	fi

header:
	echo "#define APSW_VERSION \"$(VERSION)\"" > src/apswversion.h


# the funky test stuff is to exit successfully when grep has rc==1 since that means no lines found.
showsymbols:
	rm -f apsw.so
	$(PYTHON) setup.py fetch --all --version=$(SQLITEVERSION) build_ext --inplace --force --enable-all-extensions
	test -f apsw.so
	set +e; nm --extern-only --defined-only apsw.so | egrep -v ' (__bss_start|_edata|_end|_fini|_init|initapsw)$$' ; test $$? -eq 1 || false

# Getting Visual Studio 2008 Express to work for 64 compilations is a
# pain, so use this builtin hidden command
WIN64HACK=win64hackvars
WINBPREFIX=fetch --version=$(SQLITEVERSION) --all build --enable-all-extensions
WINBSUFFIX=install build_test_extension test
WINBINST=bdist_wininst
WINBMSI=bdist_msi

# You need to use the MinGW version of make.  See
# http://bugs.python.org/issue3308 if 2.6+ or 3.0+ fail to run with
# missing symbols/dll issues.  For Python 3.1 they went out of their
# way to prevent mingw from working.  You have to install msvc.
# Google for "visual c++ express edition 2008" and hope the right version
# is still available.

compile-win:
	-del /q apsw.pyd
	cmd /c del /s /q dist
	cmd /c del /s /q build
	-cmd /c md dist
	c:/python23/python setup.py $(WINBPREFIX) --compile=mingw32 $(WINBSUFFIX) $(WINBINST)
	c:/python24/python setup.py $(WINBPREFIX) --compile=mingw32 $(WINBSUFFIX) $(WINBINST)
	c:/python25/python setup.py $(WINBPREFIX) --compile=mingw32 $(WINBSUFFIX) $(WINBINST)
	c:/python26/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python26-64/python setup.py $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python27/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python27-64/python setup.py  $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python31/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python31-64/python setup.py  $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python32/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python32-64/python setup.py  $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python33/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python33-64/python setup.py $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python34/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python34-64/python setup.py $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python35/python setup.py $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)
	c:/python35-64/python setup.py $(WIN64HACK) $(WINBPREFIX) $(WINBSUFFIX) $(WINBINST)

source_nocheck: docs
	$(PYTHON) setup.py sdist --formats zip --add-doc

# Make the source and then check it builds and tests correctly.  This will catch missing files etc
source: source_nocheck
	mkdir -p work
	rm -rf work/$(VERDIR)
	cd work ; unzip -q ../dist/$(VERDIR).zip
# Make certain various files do/do not exist
	for f in doc/vfs.html doc/_sources/pysqlite.txt tools/apswtrace.py ; do test -f work/$(VERDIR)/$$f ; done
	for f in sqlite3.c sqlite3/sqlite3.c debian/control ; do test ! -f work/$(VERDIR)/$$f ; done
# Test code works
	cd work/$(VERDIR) ; $(PYTHON) setup.py fetch --version=$(SQLITEVERSION) --all build_ext --inplace --enable-all-extensions build_test_extension test

release:
	test -f dist/$(VERDIR).zip
	test -f dist/$(VERDIR).win32-py2.3.exe
	test -f dist/$(VERDIR).win32-py2.4.exe
	test -f dist/$(VERDIR).win32-py2.5.exe
	test -f dist/$(VERDIR).win32-py2.6.exe
	test -f dist/$(VERDIR).win-amd64-py2.6.exe
	test -f dist/$(VERDIR).win32-py2.7.exe
	test -f dist/$(VERDIR).win-amd64-py2.7.exe
	test -f dist/$(VERDIR).win32-py3.1.exe
	test -f dist/$(VERDIR).win-amd64-py3.1.exe
	test -f dist/$(VERDIR).win32-py3.2.exe
	test -f dist/$(VERDIR).win-amd64-py3.2.exe
	test -f dist/$(VERDIR).win32-py3.3.exe
	test -f dist/$(VERDIR).win-amd64-py3.3.exe
	test -f dist/$(VERDIR).win32-py3.4.exe
	test -f dist/$(VERDIR).win-amd64-py3.4.exe
	-rm -f dist/$(VERDIR)-sigs.zip dist/*.asc
	for f in dist/* ; do gpg --use-agent --armor --detach-sig "$$f" ; done
	cd dist ; zip -m $(VERDIR)-sigs.zip *.asc

tags:
	rm -f TAGS
	ctags-exuberant -e --recurse --exclude=build --exclude=work .
