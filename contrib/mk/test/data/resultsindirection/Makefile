
finishup: build/done.txt

build:
	mkdir build
build/foo.txt: build src/foo.txt
	cp src/foo.txt build/foo.txt
build/bar.txt: build src/bar.txt
	cp src/bar.txt build/bar.txt

sources: build/foo.txt build/bar.txt
build/done.txt: sources
	touch build/done.txt

clean:
	rm -rf build

