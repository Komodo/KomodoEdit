# Make file for Scintilla on Linux or compatible OS
# Copyright 1998-2010 by Neil Hodgson <neilh@scintilla.org>
# The License.txt file describes the conditions under which this software may be distributed.
# This makefile assumes GCC 4.3 is used and changes will be needed to use other compilers.
# GNU make does not like \r\n line endings so should be saved to CVS in binary form.

.SUFFIXES: .cxx .c .o .h .a
AR = ar
RANLIB = touch

# Environment variable windir always defined on Win32

ifndef windir
ifeq ($(shell uname),Darwin)
RANLIB = ranlib
endif
endif

ifdef windir
DEL = del /q
COMPLIB=..\bin\headlessscintilla.a
else
DEL = rm -f
COMPLIB=../bin/headlessscintilla.a
endif

vpath %.h ../src ../include ../lexlib
vpath %.cxx ../src ../lexlib ../lexers

INCLUDEDIRS=-I ../include -I ../src -I ../lexlib
CXXBASEFLAGS=-Wall -Wno-missing-braces -Wno-char-subscripts -Wno-long-long -pedantic -DSCI_LEXER $(INCLUDEDIRS)

ifeq ($(shell uname),Linux)
CXXBASEFLAGS += -DHEADLESS_GTK
ifdef GTK3
GTKVERSION=gtk+-3.0
else
GTKVERSION=gtk+-2.0
endif
CXXBASEFLAGS += $(shell pkg-config --cflags $(GTKVERSION))
endif

ifdef DEBUG
CXXTFLAGS +=-DDEBUG -g $(CXXFLAGS) $(CXXBASEFLAGS)
CFLAGS += -DDEBUG -g
else
CXXTFLAGS +=-DNDEBUG -Os $(CXXFLAGS) $(CXXBASEFLAGS)
CFLAGS += -DNDEBUG
endif

.cxx.o:
	$(CXX) $(CXXTFLAGS) -c $<
.c.o:
	$(CC) $(CFLAGS) -w -c $<

LEXOBJS:=$(addsuffix .o,$(basename $(notdir $(wildcard ../lexers/Lex*.cxx))))

all: $(COMPLIB)

clean:
	$(DEL) *.o $(COMPLIB)

deps:
	$(CC) -MM $(CXXTFLAGS) *.cxx ../src/*.cxx | sed -e 's/\/usr.* //' | grep [a-zA-Z] >deps.mak

$(COMPLIB): Accessor.o CharacterSet.o LexerBase.o LexerModule.o LexerSimple.o StyleContext.o WordList.o \
	CharClassify.o Decoration.o Document.o PerLine.o Catalogue.o CallTip.o CaseConvert.o CaseFolder.o \
	ScintillaBase.o ContractionState.o Editor.o ExternalLexer.o PropSetSimple.o PlatHeadless.o \
	KeyMap.o LineMarker.o PositionCache.o ScintillaHeadless.o CellBuffer.o CharacterCategory.o ViewStyle.o \
	RESearch.o RunStyles.o Selection.o Style.o Indicator.o AutoComplete.o UniConversion.o XPM.o \
	$(LEXOBJS)
	$(AR) rc $@ $^
	$(RANLIB) $@

# Automatically generate header dependencies with "make deps"
#include deps.mak
