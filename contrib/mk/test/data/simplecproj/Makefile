prog: prog.o
	@echo link it
	@cp prog.o prog

prog.o: prog.c
	@echo compile it
	@cp prog.c prog.o

prog.c: prog.h

clean:
	@rm -f prog prog.o
distclean: clean
	@rm -f prog.h prog.c