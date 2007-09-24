// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include <Python.h>

#include <Scintilla.h>

#include "PyLexerModule.h"
#include "PyPropSet.h"
#include "PyWordList.h"

#define MODULE_NAME "_SilverCity"

static char module_doc[] = 
MODULE_NAME" low level interface to Scintilla lexers.";

static char WordList_doc[] = 
"WordList('and assert break class ...') => <WordList object>\n"
"\n"
"Creates a new WordList object given an optional string containing\n"
"words separated by spaces. This object is used to store keywords";

static char PropertySet_doc[] =
"PropertySet({'styling.within.preprocessor':1}) => <PropertySet object>\n"
"\n"
"Creates a new PropertySet object given an optional dictionary of\n"
"lexing options. PropertySet object behave as dictionaries and can\n"
"be used to control the behavior of the lexing process.";

static char find_lexer_module_by_name_doc[] =
"find_lexer_module_by_name('python') => <Python LexerModule object>\n"
"\n"
"Returns a LexerModule object based on the name provided.\n";

static char find_lexer_module_by_id_doc[] =
"find_lexer_module_by_id(SCLEX_PYTHON) => <Python LexerModule object>\n"
"\n"
"Returns a LexerModule object based on an integer constant. These\n"
"constants can be found in ScintillaConstants.py";

static PyObject*
FindLexerModuleByName(PyObject *, PyObject* args)
{
    char* lexerName;
    const LexerModule * lexerModule;

    if (!PyArg_ParseTuple(args, "s", &lexerName))
        return NULL;

    lexerModule = LexerModule::Find(lexerName);
    if (lexerModule == NULL) {
        PyErr_Format(PyExc_ValueError, "could not find lexer %.200s",
            lexerName);
        return NULL;
    }

    return PyLexerModule_new(lexerModule);
}

static PyObject*
FindLexerModuleByID(PyObject *, PyObject* args)
{
    int             lexerID;
    const LexerModule *   lexerModule;

    if (!PyArg_ParseTuple(args, "i", &lexerID))
        return NULL;

    lexerModule = LexerModule::Find(lexerID);
    if (lexerModule == NULL) {
        PyErr_Format(PyExc_ValueError, "could not find lexer %d",
            lexerID);
        return NULL;
    }

    return PyLexerModule_new(lexerModule);
}

static PyMethodDef moduleMethods[] = 
{
    {"WordList", (PyCFunction)PyWordList_new, METH_VARARGS, WordList_doc },
    {"PropertySet", (PyCFunction)PyPropSet_new, METH_VARARGS, PropertySet_doc },
    {"find_lexer_module_by_name", (PyCFunction)FindLexerModuleByName, METH_VARARGS, 
        find_lexer_module_by_name_doc },
    {"find_lexer_module_by_id", (PyCFunction)FindLexerModuleByID, METH_VARARGS, 
        find_lexer_module_by_id_doc },
    {NULL, NULL}
};

// Module init functions.

extern "C"
{

#ifdef WIN32
_declspec(dllexport) 
#endif
void
init_SilverCity(void)
{ 
    PyObject * m;
    PyObject * moduleDict;

    m = Py_InitModule3(MODULE_NAME, moduleMethods, module_doc);
    moduleDict = PyModule_GetDict(m);

    initPyLexerModule();
    initPyPropSet();
    initPyWordList();
}
}
