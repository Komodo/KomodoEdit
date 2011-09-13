// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#ifndef PYWORDLIST_H_
#define PYWORDLIST_H_

#include <Python.h>

#include <SC_PropSet.h>

extern PyTypeObject PyWordListType;

typedef struct {
    PyObject_HEAD
    PyObject *wordListAsString;
} PyWordList;

#define PyWordList_Check(op) ((op)->ob_type == &PyWordListType)

PyObject*
PyWordList_new(PyObject *, PyObject* args);

void
initPyWordList(void);

#endif // PYWORDLIST_H_
