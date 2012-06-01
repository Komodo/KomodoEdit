DEST=../../../lib/codeintel2/stdlibs
RUBY=/home/ericp/opt/ruby-1.9.2-p136/bin/ruby
RSRC2=/home/ericp/lab/ruby/ruby-1.9.2-p136
RSRC3=/home/ericp/lab/ruby/ruby-1.9.3-p125

all : build

install: install-1.9.2 install-1.9.3

build: build2 build3

build2: r-1.9.2.cix 

build3: r-1.9.3.cix

check: check2 check3

install-1.9.2: $(DEST)/ruby-1.9.2.cix

install-1.9.3: $(DEST)/ruby-1.9.3.cix

$(DEST)/ruby-1.9.2.cix: r-1.9.2.cix
	cp $< $@

$(DEST)/ruby-1.9.3.cix: r-1.9.3.cix
	cp $< $@

r-1.9.2.cix : gen-from-ri-dir.rb
	$(RUBY) gen-from-ri-dir.rb --ri-dir $(RSRC2)/.ext/rdoc --lib-dir=$(RSRC3)/lib > $@

r-1.9.3.cix : gen-from-ri-dir.rb
	$(RUBY) gen-from-ri-dir.rb --ri-dir $(RSRC3)/.ext/rdoc --lib-dir=$(RSRC3)/lib > $@

check2 : r-1.9.2.cix
	perl xcheck.pl r-1.9.2.cix

check3 : r-1.9.2.cix
	perl xcheck.pl r-1.9.3.cix

args2 : 
	@echo --ri-dir $(RSRC2)/.ext/rdoc --lib-dir=$(RSRC2)/lib

args3 : 
	@echo --ri-dir $(RSRC3)/.ext/rdoc --lib-dir=$(RSRC3)/lib

size:
	wc r-1.9.[23].cix
