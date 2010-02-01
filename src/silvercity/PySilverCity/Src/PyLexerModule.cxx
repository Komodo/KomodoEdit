// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include "PyLexerModule.h"

#include <BufferAccessor.h>
#include <SciLexer.h>

#include "AutoReleasePool.h"
#include "PyPropSet.h"
#include "PyWordList.h"

static char tokenize_by_style_doc[] = 
"tokenize_by_style('import string', WordList('import...'), PropertSet())\n"
"     => list of tokens\n"
"\n"
"Tokenizes the given string using the provided WordList (or list of WordLists)\n" 
"and the PropertySet. The return value is a list of dictionaries containing\n"
"information about the token. Each dictionary contains the following\n"
"information:\n"
"  style: The lexical style of the token e.g. 11\n"
"  text: The text of the token e.g. 'import'\n"
"  start_index: The index in the buffer where the token begins e.g. 0\n"
"  end_index: The index in the buffer where the token ends e.g. 5\n"
"  start_column: The column position (0-based) where the token begins e.g. 0\n"
"  end_column: The column position (0-based) where the token ends e.g. 5\n"
"  start_line: The line position (0-based) where the token begins e.g. 0\n"
"  end_line: The line position (0-based) where the token ends e.g. 0\n"
"\n"
"Optionally, you may also pass a callback function as the last argument.\n"
"The callback function will receive the token information by keyword\n"
"arguments e.g.:\n"
"def my_callback(style, text, start_index, ..., **other_args):\n"
"    pass\n";

static char get_number_of_wordlists_doc[] = 
"get_number_of_wordlists() => 2\n"
"\n"
"Returns the number of WordLists that the lexer requires i.e. for\n"
"for tokenize_by_style.\n"
"\n"
"Raises a ValueError if no WordList information is available.";
    
static char get_wordlist_descriptions_doc[] = 
"get_wordlist_descriptions() => (\"Python keywords\")\n"
"\n"
"Returns a sequence containing a description for each WordList that the\n"
"lexer requires i.e for tokenize_by_style.\n"
"\n"
"Raises a ValueError if no WordList information is available.";

static WordList **
getWordList(PyObject * pyWordLists, const LexerModule * lexer, AutoReleasePool & pool);

PyObject*
PyLexerModule_new(const LexerModule * lexer)
{
    PyLexerModule*  pyLexerModule;

    pyLexerModule = PyObject_New(PyLexerModule, &PyLexerModuleType);
    pyLexerModule->lexer = lexer;

    return (PyObject*) pyLexerModule;
}

static void
PyLexerModule_dealloc(PyLexerModule* self)
{
    PyObject_Del(self);
}

static int
numWordLists(const LexerModule * lexer)
{
	// If your favorite lexer doesn't support
	// GetNumWordLists() then you can add it here
    if (lexer->GetNumWordLists() > 0)
        return lexer->GetNumWordLists();

    switch (lexer->GetLanguage()) {
        case SCLEX_NULL: return 0;
    }
    return -1;
}

#if PYTHON_API_VERSION<1011
// This function was added in Python 2.2

#define PyObject_Call(func,arg, kw) \
        PyEval_CallObjectWithKeywords(func, arg, kw)
#endif

static PyObject *
PyLexerModule_tokenize_by_style(PyLexerModule* self, PyObject * args)
{
    PyObject * pyWordLists = NULL;
    WordList ** wordLists = NULL;
    SC_PropSet * propset = NULL;
    PyObject * pyPropSet = NULL;
    PyObject * pyTokenList = NULL;
    PyObject * pyToken = NULL;
    PyObject * pyCallback = NULL;
    PyObject * pyEmptyTuple = NULL;
    PyObject * pyCallbackResult = NULL;
    const char * bufEncoding = "utf-8";
    char * style = NULL;
    char * buf = NULL;
    AutoReleasePool pool;
    int bufSize;
    int i;
    int startIndex;
    int startLine;
    int line;
    int startCol;
    int col;

    if (!PyArg_ParseTuple(args, "es#OO|O", bufEncoding, &buf, &bufSize, &pyWordLists, &pyPropSet, &pyCallback))
        return NULL;

    if (!PyPropSet_Check(pyPropSet)) {
        PyErr_Format(PyExc_TypeError, "expected PropertySet, %.200s found",
            pyPropSet->ob_type->tp_name);
        return NULL;
    }

    if ((pyCallback != NULL) && !PyCallable_Check(pyCallback)) {
        PyErr_Format(PyExc_TypeError, "expected callable object, %.200s found",
            pyCallback->ob_type->tp_name);
        return NULL;        
    }

    wordLists = getWordList(pyWordLists, self->lexer, pool);
    if (wordLists == NULL)
       return NULL;

    style = new char[bufSize];
    // KOMODO - Ensure no style to begin with. This is required because the
    // lexers (at least the python lexer) will perform a lookahead to check for
    // IO Styles, which are needed/used by the interactive shell system.
    // Without the memset, the Lexer randomly finds IO styles and leaves these
    // in the style buffer, even though they may not have been set explicitly.
    // http://bugs.activestate.com/show_bug.cgi?id=48137
    memset(style, 0, sizeof(char) * bufSize);

    propset = PyPropSet_GET_PROPSET(pyPropSet);
    BufferAccessor bufAccessor(buf, bufSize, style, *propset);

    Py_BEGIN_ALLOW_THREADS
        self->lexer->Lex(0, bufSize, 0, wordLists, bufAccessor);
    Py_END_ALLOW_THREADS

    if (pyCallback == NULL) {
        pyTokenList = PyList_New(0);
        if (pyTokenList == NULL)
            goto onError;
    } else {
        pyEmptyTuple = PyTuple_New(0);
        if (pyEmptyTuple == NULL)
            goto onError;
    }
    
    PyObject *text;
    for (i = startIndex = startLine = startCol = 0; i <= bufSize; ++i) {
        if ((i == bufSize) || ((i != 0) && (style[i] != style[i-1]))) {
            line = bufAccessor.GetLine(i-1);
            col = bufAccessor.GetColumn(i-1);

            // Turn the bytes back into Unicode, it's currently utf-8 encoded.
            text = PyUnicode_DecodeUTF8(&(buf[startIndex]), i - startIndex, NULL);
            pyToken = Py_BuildValue("{s:i,s:O,s:i,s:i,s:i,s:i,s:i,s:i}", 
                "style", style[i - 1], 
                "text", text,
                "start_index", startIndex, 
                "end_index", i - 1, 
                "start_line", startLine, 
                "start_column", startCol,
                "end_line", line, 
                "end_column", col);
            Py_DECREF(text);

            if (pyToken == NULL)
                goto onError;

            if (pyCallback == NULL) {
                if (PyList_Append(pyTokenList, pyToken) == -1)
                    goto onError;
            } else {
                pyCallbackResult = PyObject_Call(pyCallback, pyEmptyTuple, pyToken);
                if (pyCallbackResult == NULL)
                    goto onError;
                Py_DECREF(pyCallbackResult);
            }


            Py_DECREF(pyToken);

            if (i != bufSize) {
                startIndex = i;
                startLine = bufAccessor.GetLine(i);
                startCol = bufAccessor.GetColumn(i);
            }
        }
    }

    Py_XDECREF(pyEmptyTuple);

    delete[] wordLists;
    delete [] style;

    if (pyCallback == NULL)
        return pyTokenList;
    else
        return Py_BuildValue("");

onError:
    Py_XDECREF(pyTokenList);
    Py_XDECREF(pyToken);
    Py_XDECREF(pyEmptyTuple);
    delete[] wordLists;
    delete [] style;

    return NULL;
}

static WordList **
getWordList(PyObject * pyWordLists, const LexerModule * lexer, AutoReleasePool & pool)
{
    WordList ** wordLists = NULL;
    PyObject * pyWordList = NULL;
    int size;

    if (numWordLists(lexer) == -1) {
        PyErr_Format(PyExc_ValueError, "cannot determined WordList requirements for lexer");
        return NULL;
    }

    if (PyWordList_Check(pyWordLists)) {
        if (numWordLists(lexer) != 1) {
            PyErr_Format(PyExc_TypeError,
                "excepted list of %d WordLists (WordList found)", 
                numWordLists(lexer));
            return NULL;
        }
        wordLists = new WordList * [1];
        wordLists[0] = PyWordList_GET_WORDLIST(pyWordLists);
        return wordLists;
    }

    if (!PySequence_Check(pyWordLists)) {
        PyErr_Format(PyExc_TypeError, "expected list of %d WordLists, %.200s found",
           numWordLists(lexer), pyWordLists->ob_type->tp_name);
        return NULL;
    }

    size = PySequence_Size(pyWordLists);
    if (size == -1) {
        return NULL;
    }

    if (size != numWordLists(lexer)) {
        PyErr_Format(PyExc_TypeError, "expected sequence of %d WordLists (%d provided)",
           numWordLists(lexer), size);
        return NULL;
    }

    wordLists = new WordList * [size];

    for (int i = 0; i < size; ++i) {
        pyWordList = PySequence_GetItem(pyWordLists, i);
        if (!PyWordList_Check(pyWordList)) {
            PyErr_Format(PyExc_TypeError, "expected list of WordLists, %.200s found",
                pyWordList->ob_type->tp_name);
            
            goto onError;
        }

        wordLists[i] = PyWordList_GET_WORDLIST(pyWordList);

        pool.add(pyWordList);
    }

    return wordLists;

onError:
    delete[] wordLists;
    Py_XDECREF(pyWordList);
    return NULL;
}

static PyObject *
PyLexerModule_get_number_of_wordlists(PyLexerModule* self, PyObject * args)
{
    int nWordLists;

    if (!PyArg_ParseTuple(args, ""))
        return NULL;


    nWordLists = numWordLists(self->lexer);
    if (nWordLists < 0) {
        return PyErr_Format(PyExc_ValueError, "cannot determined WordList requirements for lexer");
    } else {
        return Py_BuildValue("i", nWordLists);
    }
}

static PyObject *
PyLexerModule_get_wordlist_descriptions(PyLexerModule* self, PyObject * args)
{
    PyObject * pyDescriptionsTuple;

    int numWordLists = self->lexer->GetNumWordLists();
    if (numWordLists < 0) {
        return PyErr_Format(PyExc_ValueError, "cannot determined WordList requirements for lexer");
    }

    pyDescriptionsTuple = PyTuple_New(numWordLists);
    if (pyDescriptionsTuple == NULL)
        return NULL;

    for (int i = 0; i < numWordLists; ++i) {
        PyObject * description = PyString_FromString(self->lexer->GetWordListDescription(i));

        if (description == NULL) {
            Py_DECREF(pyDescriptionsTuple);
        }

        PyTuple_SET_ITEM(pyDescriptionsTuple, i, description);
    }

    return pyDescriptionsTuple;
} 

static PyMethodDef PyLexerModule_methods[] = 
{
    {"tokenize_by_style", (PyCFunction) PyLexerModule_tokenize_by_style, METH_VARARGS, tokenize_by_style_doc},
    {"get_number_of_wordlists", (PyCFunction) PyLexerModule_get_number_of_wordlists, METH_VARARGS, get_number_of_wordlists_doc},
    {"get_wordlist_descriptions", (PyCFunction) PyLexerModule_get_wordlist_descriptions, METH_VARARGS, get_wordlist_descriptions_doc},
    { NULL, NULL }
};


static PyObject *
PyLexerModule_getattr(PyLexerModule *self, char *name)
{
    return Py_FindMethod(PyLexerModule_methods, (PyObject *) self, name);
}

static PyObject * 
PyLexerModule_repr(PyLexerModule *self)
{
#if PYTHON_API_VERSION>1011
    // PyString_FromFormat was added in Python 2.2

    if (self->lexer->languageName) {
        return PyString_FromFormat("<%s object for \"%s\" at %p>", 
                                    self->ob_type->tp_name, self->lexer->languageName, self);
    } else {
        return PyString_FromFormat("<%s object at %p>",
                                    self->ob_type->tp_name, self);
    }
#else

    char buf[1024];
    if (self->lexer->languageName) {
        sprintf(buf, "<%s object for \"%s\" at %p>", 
                self->ob_type->tp_name, self->lexer->languageName, self);
    } else {
        sprintf(buf, "<%s object at %p>",
                self->ob_type->tp_name, self);
    }

    return PyString_FromString(buf);
#endif
}

PyTypeObject PyLexerModuleType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "LexerModule",
    sizeof(PyLexerModule),
    0,
    (destructor) PyLexerModule_dealloc,     /*tp_dealloc*/
    0,                                      /*tp_print*/
    (getattrfunc) PyLexerModule_getattr,    /*tp_getattr*/
    0,                                      /*tp_setattr*/
    0,                                      /*tp_compare*/
    (reprfunc) PyLexerModule_repr,          /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                                      /*tp_hash */
    0,                                      /*tp_call*/
    0,                                      /*tp_str */
};


void
initPyLexerModule(void)
{
    PyLexerModuleType.ob_type = &PyType_Type;
}
