// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#ifndef PYLEXERMODULE_H_
#define PYLEXERMODULE_H_

#include <Python.h>

#include <Accessor.h>
#include <SC_PropSet.h>
#include <KeyWords.h>

extern PyTypeObject PyLexerModuleType;

typedef struct {
    PyObject_HEAD
    const LexerModule * lexer;
} PyLexerModule;

#define PyLexerModule_Check(op) ((op)->ob_type == &PyLexerModuleType)

PyObject*
PyLexerModule_new(const LexerModule * lexer);

void
initPyLexerModule(void);

#endif // PYLEXERMODULE_H_
