// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include <stdio.h>  // For NULL, for KeyWords.h
#include <ctype.h> // For ctypes..., for KeyWords.h

#include <Accessor.h>
#include <KeyWords.h>

#include "PyWordList.h"

PyObject*
PyWordList_new(PyObject *, PyObject* args)
{
    PyWordList*     pyWordList;
    char*           wordStr = NULL;

    if (!PyArg_ParseTuple(args, "|s", &wordStr))
        return NULL;

    pyWordList = PyObject_New(PyWordList, &PyWordListType);
    pyWordList->wordList = new WordList();

    if (wordStr != NULL) {
        // XXX Validate that the string is reasonable?
        pyWordList->wordList->Set(wordStr);
    }

    return (PyObject*) pyWordList;
}

static PyObject*
PyWordList_words(PyWordList *self)
{
    PyObject * wordList = PyList_New(self->wordList->len);

    if (wordList == NULL)
    return NULL;

    for (int i = 0; i < self->wordList->len; ++i)
    {
        PyObject * word = PyString_FromString(self->wordList->words[i]);

        if (word == NULL)
        {
            Py_DECREF(wordList);
            return NULL;
        }

        PyList_SET_ITEM(wordList, i, word);
        }

    return wordList;
}

static PyMethodDef PyWordList_methods[] = 
{
    { NULL, NULL }
};


static PyObject *
PyWordList_getattr(PyWordList *self, char *name)
{
    if (strcmp(name, "words") == 0)
        return PyWordList_words(self);

    return Py_FindMethod(PyWordList_methods, (PyObject *) self, name);
}

static void
PyWordList_dealloc(PyWordList* self)
{
    delete self->wordList;
    PyObject_Del(self);
}


PyTypeObject PyWordListType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "WordList",
    sizeof(PyWordList),
    0,
    (destructor) PyWordList_dealloc,        /*tp_dealloc*/
    0,                                      /*tp_print*/
    (getattrfunc) PyWordList_getattr,       /*tp_getattr*/
    0,                                      /*tp_setattr*/
    0,                                      /*tp_compare*/
    0,                                      /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                                      /*tp_hash */
    0,                                      /*tp_call*/
    0,                                      /*tp_str */
};


void
initPyWordList(void)
{
    PyWordListType.ob_type = &PyType_Type;
}
