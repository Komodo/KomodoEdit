# Make file for Scintilla on Mac OS X
# Copyright 2002 by Evan Jones <ejones@uwaterloo.ca>
# Based on the GTK makefile Copyright 1998-2001 by Neil Hodgson <neilh@scintilla.org>
# The License.txt file describes the conditions under which this software may be distributed.
# This makefile assumes that Apple's version of GCC 3.1 is used and changes will be needed to use other compilers.
# GNU make does not like \r\n line endings so should be saved to CVS in binary form.

.SUFFIXES: .cxx .c .o .h .a .mm
CC = $(CXX)
LIBTOOL = libtool

GCC_MAJOR    := $(shell $(CC) -v 2>&1 | \
                        grep version | cut -d' ' -f3  | cut -d'.' -f1)

# We call it "libscintilla" so when you add it to a Project Builder project,
# Project Builder will link it correctly.
STATICLIB=../bin/libscintilla.a
DYNAMICLIB_BASE=libscintilla.dylib
DYNAMICLIB=../bin/$(DYNAMICLIB_BASE)

vpath %.h ../src ../include ../lexlib
vpath %.cxx ../src ../lexlib ../lexers

INCLUDEDIRS=-I. -I ../include -I ../src -I ../lexlib

ifndef NATIVE
ARCH_BASE_FLAGS=/Developer/SDKs/MacOSX10.5.sdk -arch i386
ARCHFLAGS=-isysroot $(ARCH_BASE_FLAGS)
LINK_FLAGS=-Wl,-syslibroot,$(ARCH_BASE_FLAGS)
DYN_FLAGS=$(LINK_FLAGS) -framework Cocoa -framework QuartzCore -dynamiclib -install_name @executable_path/$(DYNAMICLIB_BASE)
else
DYN_FLAGS=$(LDFLAGS) -framework Cocoa -framework QuartzCore -dynamiclib -install_name @executable_path/$(DYNAMICLIB_BASE) -L. -lpcre
endif

# See http://stackoverflow.com/questions/127426/gnu-compiler-warning-class-has-virtual-functions-but-non-virtual-destructor
OPTIONS=-Wall -Wno-missing-braces -Wno-char-subscripts -Wno-non-virtual-dtor -DSCI_NAMESPACE -DMACOSX -DSCI_LEXER

#DEBUG = 1

ifdef DEBUG
DFLAGS=-DDEBUG -g
else
DFLAGS=-DNDEBUG -Os
endif

ifdef CONTAINER_HANDLES_EVENTS
CONTAINER=-DCONTAINER_HANDLES_EVENTS=1
endif

ifdef EXT_INPUT
EXT_INPUT=-DEXT_INPUT
endif

.cxx.o:
	$(CC) $(CXXFLAGS) $(OPTIONS) $(DFLAGS) $(CONTAINER) $(ARCHFLAGS) $(EXT_INPUT) $(INCLUDEDIRS) -c $<
.mm.o:
	$(CC) $(CXXFLAGS) $(OPTIONS) $(DFLAGS) $(CONTAINER) $(ARCHFLAGS) $(EXT_INPUT) $(INCLUDEDIRS) -c $<
.c.o:
	$(CCOMP) $(CXXFLAGS) $(OPTIONS) $(DFLAGS) $(CONTAINER) $(ARCHFLAGS) $(EXT_INPUT) $(INCLUDEDIRS) -w -c $<

LEXOBJS:=$(addsuffix .o,$(basename $(notdir $(wildcard ../lexers/Lex*.cxx))))

# The LEXOBJS have to be treated specially as the functions in them are not called from external code

all: $(STATICLIB) $(LEXOBJS)

shared: $(DYNAMICLIB) $(LEXOBJS)

clean:
	rm -f *.o $(COMPLIB)

deps:
	$(CC) -MM -DSCI_NAMESPACE -DMACOSX -DSCI_LEXER  $(CXXFLAGS) $(INCLUDEDIRS) -I. *.mm ../src/*.cxx ../lexlib/*.cxx ../src/*.cxx >deps.mak

COMPLIB=Accessor.o CharacterCategory.o CharacterSet.o LexerBase.o LexerModule.o LexerSimple.o StyleContext.o WordList.o \
	CaseConvert.o CaseFolder.o CharClassify.o Decoration.o Document.o PerLine.o Catalogue.o CallTip.o \
	ScintillaBase.o ContractionState.o Editor.o ExternalLexer.o PropSetSimple.o \
	KeyMap.o LineMarker.o PositionCache.o CellBuffer.o ViewStyle.o \
	RESearch.o RunStyles.o Selection.o Style.o Indicator.o AutoComplete.o UniConversion.o XPM.o \
        InfoBar.o PlatCocoa.o ScintillaCocoa.o ScintillaView.o \
	$(LEXOBJS)

$(STATICLIB): $(COMPLIB)
	$(LIBTOOL) -static -o $@ $^

$(DYNAMICLIB): $(COMPLIB)
	$(CC) -dynamic -o $@ $(DYN_FLAGS) $^

# Generate header files from Scintilla.iface
../include/Scintilla_gen.h: ../include/HFacer.py ../include/Face.py ../include/Scintilla.iface
	cd ../include && python HFacer.py
../include/SciLexer_gen.h: ../include/HFacer.py ../include/Face.py ../include/Scintilla.iface
	cd ../include && python HFacer.py
../include/Scintilla.h: ../include/Scintilla_gen.h
../include/SciLexer.h: ../include/SciLexer_gen.h

# Automatically generate header dependencies with "make deps"
include deps.mak
