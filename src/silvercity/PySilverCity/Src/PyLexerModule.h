// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#ifndef PYLEXERMODULE_H_
#define PYLEXERMODULE_H_

#include <Python.h>

#include "ILexer.h"
#include "Scintilla.h"
#include <SciLexer.h>
#include "WordList.h"
#include <LexAccessor.h>
#include <Accessor.h>

#include "StyleContext.h"
#include "CharacterSet.h"
#include "LexerModule.h"

#include <LexState.h> // SilverCity object that wraps a LexerModule
#include <SC_PropSet.h>
#include <WordList.h>

extern PyTypeObject PyLexStateType;

typedef struct {
    PyObject_HEAD
    LexState * lexer;
} PyLexState;

#define PyLexState_Check(op) ((op)->ob_type == &PyLexStateType)

PyObject*
PyLexState_new(LexState * lexerWrapper);

void
initPyLexState(void);

#endif // PYLEXERMODULE_H_
