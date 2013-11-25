// Copyright 2002 by Brian Quinlan <brian@sweetapp.com>
// The License.txt file describes the conditions under which this 
// software may be distributed.

#include "PyLexerModule.h"

#include <BufferAccessor.h>

#include "AutoReleasePool.h"
#include "PyPropSet.h"
#include "PyWordList.h"

#include "LexState.h"

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

static char **
getWordList(PyObject * pyWordLists, AutoReleasePool & pool);

PyObject*
PyLexState_new(LexState * lexer)
{
    PyLexState*  pyLexState;

    pyLexState = PyObject_New(PyLexState, &PyLexStateType);
    pyLexState->lexer = lexer;

    return (PyObject*) pyLexState;
}

static void
PyLexState_dealloc(PyLexState* self)
{
    PyObject_Del(self);
}

static int
numWordLists(LexState * lexState)
{
	// If your favorite lexer doesn't support
	// GetNumWordLists() then you can add it here
    const LexerModule *lexerModule = lexState->lexCurrent;
    int res = lexerModule->GetNumWordLists();
    if (res > 0)
        return res;

    switch (lexerModule->GetLanguage()) {
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
PyLexState_tokenize_by_style(PyLexState* self, PyObject * args)
{
    PyObject * pyWordLists = NULL;
    char** wordLists = NULL;
    PropSetEx * propset = NULL;
    PropSetSimple *p_PropSetSimple;
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

    //fprintf(stderr, ">> PyLexerModule.cxx:tokenize_by_style (PyLexState_tokenize_by_style)...\n");

    if (!PyArg_ParseTuple(args, "et#OO|O", bufEncoding, &buf, &bufSize, &pyWordLists, &pyPropSet, &pyCallback)) {
        fprintf(stderr, "Can't get args\n");
        return NULL;
    }

    if (!PyPropSet_Check(pyPropSet)) {
        fprintf(stderr, "expected PropertySet, %.200s found",
                pyPropSet->ob_type->tp_name);
        PyErr_Format(PyExc_TypeError, "expected PropertySet, %.200s found",
            pyPropSet->ob_type->tp_name);
        return NULL;
    }

    if ((pyCallback != NULL) && !PyCallable_Check(pyCallback)) {
        fprintf(stderr, "expected callable object, %.200s found",
            pyCallback->ob_type->tp_name);
        PyErr_Format(PyExc_TypeError, "expected callable object, %.200s found",
            pyCallback->ob_type->tp_name);
        return NULL;        
    }

    wordLists = getWordList(pyWordLists, pool);
    if (wordLists == NULL) {
        fprintf(stderr, "Null wordLists\n");
       return NULL;
    }

    style = new char[bufSize + 1];
    // KOMODO - Ensure no style to begin with. This is required because the
    // lexers (at least the python lexer) will perform a lookahead to check for
    // IO Styles, which are needed/used by the interactive shell system.
    // Without the memset, the Lexer randomly finds IO styles and leaves these
    // in the style buffer, even though they may not have been set explicitly.
    // http://bugs.activestate.com/show_bug.cgi?id=48137
    //
    // http://bugs.activestate.com/show_bug.cgi?id=91179 - Some accessor,
    // when told it has n bytes to work with, is overwriting styleBuf[n]
    // So allocate one extra byte for it to work with.
    memset(style, 0, sizeof(char) * (bufSize + 1));

    propset = PyPropSet_GET_PROPSET(pyPropSet);
    p_PropSetSimple = new(PropSetSimple);
    { 
        char *propKey, *propVal;
        bool res = propset->GetFirst(&propKey, &propVal);
        while (res) {
            p_PropSetSimple->Set(propKey, propVal, strlen(propKey), strlen(propVal));
            self->lexer->PropSet(propKey, propVal);
            res = propset->GetNext(&propKey, &propVal);
        }
    }
    
    if (!PyPropSet_Check(pyPropSet)) {
        fprintf(stderr, "expected PropertySet, %.200s found",
                pyPropSet->ob_type->tp_name);
        PyErr_Format(PyExc_TypeError, "expected PropertySet, %.200s found",
            pyPropSet->ob_type->tp_name);
        return NULL;
    }

    //fprintf(stderr, "   *propset: %p\n", *propset);
    //SC_PropSet myPropSet(*propset);
    //fprintf(stderr, "    buf: <<<%s>>>\n", buf);
    BufferAccessor bufAccessor(buf, bufSize, style, *propset);
	Accessor styler(&bufAccessor, p_PropSetSimple);
    // Introduce the document (bufAccessor) and the LexState object to each other
    //buf.pli = self->lexer;
    self->lexer->SetDocument(&bufAccessor);
    {
        int i;
        char *wl;
        for (i = 0; (wl = wordLists[i]); i++) {
            self->lexer->SetWordList(i, wl);
        }
    }

    Py_BEGIN_ALLOW_THREADS
        //fprintf(stderr, "-About to call self->lexer->Lex...\n");
    //fprintf(stderr, " self->lexer: %p\n", self->lexer);
    //fprintf(stderr, " self->lexer->fnLexer: %p\n", &(self->lexer->fnLexer));
        self->lexer->Colourise();
    //self->lexer->Lex(0, bufSize, 0, wordLists, styler);
        //fprintf(stderr, "+About to call self->lexer->Lex...\n");
        // Push styling info from Accessor styler to bufAccessor
        styler.Flush();
    Py_END_ALLOW_THREADS

    if (pyCallback == NULL) {
        //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
        pyTokenList = PyList_New(0);
        //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
        if (pyTokenList == NULL)
            goto onError;
    } else {
        //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
        pyEmptyTuple = PyTuple_New(0);
        //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
        if (pyEmptyTuple == NULL)
            goto onError;
    }
    
    PyObject *text;
                    
    for (i = startIndex = startLine = startCol = 0; i <= bufSize; ++i) {
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
        if ((i > 0)
            && (i == bufSize || style[i] != style[i-1])) {
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
            line = bufAccessor.LineFromPosition(i-1);
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
            col = bufAccessor.GetColumn(i-1);
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);

            // Turn the bytes back into Unicode, it's currently utf-8 encoded.
            text = PyUnicode_DecodeUTF8(&(buf[startIndex]), i - startIndex, NULL);
	    if (text == NULL)
		goto onError;
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
            pyToken = Py_BuildValue("{s:i,s:O,s:i,s:i,s:i,s:i,s:i,s:i}", 
                "style", style[i - 1], 
                "text", text,
                "start_index", startIndex, 
                "end_index", i - 1, 
                "start_line", startLine, 
                "start_column", startCol,
                "end_line", line, 
                "end_column", col);
            //fprintf(stderr, "Creating new token %d: style:%d, text:%c-%c, lines %d-%d\n",
            //        i, style[i-1], buf[startIndex], buf[i - 1], startLine, line);
            Py_DECREF(text);

            if (pyToken == NULL)
                goto onError;

            if (pyCallback == NULL) {
                if (PyList_Append(pyTokenList, pyToken) == -1)
                    goto onError;
            } else {
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
                pyCallbackResult = PyObject_Call(pyCallback, pyEmptyTuple, pyToken);
    //fprintf(stderr, "%s %d\n", __FILE__, __LINE__);
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

    //fprintf(stderr, "<< tokenize_by_style (#1)\n");
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

    //fprintf(stderr, "<< tokenize_by_style (#2)\n");
    return NULL;
}
#if 1

/**
 * Return an array of WordList** items, terminated by a NULL
 */
static char**
getWordList(PyObject * pyWordLists, AutoReleasePool & pool)
{
    char ** wordLists;
    PyObject * pyWordList = NULL;
    PyWordList *actualWordList;
    int size;

    size = PySequence_Size(pyWordLists);
    if (size == -1) {
        return NULL;
    }

    wordLists = new char*[size + 1];

    for (int i = 0; i < size; ++i) {
        pyWordList = PySequence_GetItem(pyWordLists, i);
        if (!PyWordList_Check(pyWordList)) {
            PyErr_Format(PyExc_TypeError, "expected list of \"WordList\", %.200s found",
                pyWordList->ob_type->tp_name);
            
            goto onError;
        }
        actualWordList = (PyWordList *) pyWordList;
        if (actualWordList->wordListAsString) {
            if (!PyString_Check(actualWordList->wordListAsString)) {
                PyErr_Format(PyExc_TypeError, "expected a wrapped String, %.200s found",
                             actualWordList->wordListAsString->ob_type->tp_name);
            
                goto onError;
            }
            wordLists[i] = PyString_AsString(actualWordList->wordListAsString);
        } else {
            wordLists[i] = (char *) "";
        }
        pool.add(pyWordList);
    }
    wordLists[size] = NULL;
    return wordLists;

onError:
    delete[] wordLists;
    Py_XDECREF(pyWordList);
    return NULL;
}

#endif

#if 0
static WordList **
getWordList(PyObject * pyWordLists, LexState * lexState, AutoReleasePool & pool)
{
    WordList ** wordLists = NULL;
    PyObject * pyWordList = NULL;
    int size;
    int nWordLists = numWordLists(lexState);

    if (nWordLists == -1) {
        PyErr_Format(PyExc_ValueError, "cannot determined WordList requirements for lexer");
        return NULL;
    }

    if (PyWordList_Check(pyWordLists)) {
        if (nWordLists != 1) {
            PyErr_Format(PyExc_TypeError,
                "excepted list of %d WordLists (WordList found)", 
                nWordLists);
            return NULL;
        }
        wordLists = new WordList * [1];
        wordLists[0] = PyWordList_GET_WORDLIST(pyWordLists);
        return wordLists;
    }

    if (!PySequence_Check(pyWordLists)) {
        PyErr_Format(PyExc_TypeError, "expected list of %d WordLists, %.200s found",
           nWordLists, pyWordLists->ob_type->tp_name);
        return NULL;
    }

    size = PySequence_Size(pyWordLists);
    if (size == -1) {
        return NULL;
    }

    if (size != nWordLists) {
        PyErr_Format(PyExc_TypeError, "expected sequence of %d WordLists (%d provided)",
           nWordLists, size);
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
#endif

static PyObject *
PyLexState_get_number_of_wordlists(PyLexState* self, PyObject * args)
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
PyLexState_get_wordlist_descriptions(PyLexState* self, PyObject * args)
{
    PyObject * pyDescriptionsTuple;

    int nWordLists = numWordLists(self->lexer);
    if (nWordLists < 0) {
        return PyErr_Format(PyExc_ValueError, "cannot determined WordList requirements for lexer");
    }

    pyDescriptionsTuple = PyTuple_New(nWordLists);
    if (pyDescriptionsTuple == NULL)
        return NULL;

    for (int i = 0; i < nWordLists; ++i) {
        PyObject * description = PyString_FromString(self->lexer->lexCurrent->GetWordListDescription(i));

        if (description == NULL) {
            Py_DECREF(pyDescriptionsTuple);
        }

        PyTuple_SET_ITEM(pyDescriptionsTuple, i, description);
    }

    return pyDescriptionsTuple;
} 

static PyMethodDef PyLexState_methods[] = 
{
    {"tokenize_by_style", (PyCFunction) PyLexState_tokenize_by_style, METH_VARARGS, tokenize_by_style_doc},
    {"get_number_of_wordlists", (PyCFunction) PyLexState_get_number_of_wordlists, METH_VARARGS, get_number_of_wordlists_doc},
    {"get_wordlist_descriptions", (PyCFunction) PyLexState_get_wordlist_descriptions, METH_VARARGS, get_wordlist_descriptions_doc},
    { NULL, NULL }
};


static PyObject *
PyLexState_getattr(PyLexState *self, char *name)
{
    return Py_FindMethod(PyLexState_methods, (PyObject *) self, name);
}

static PyObject * 
PyLexState_repr(PyLexState *self)
{
#if PYTHON_API_VERSION>1011
    // PyString_FromFormat was added in Python 2.2

    const char *languageName = self->lexer->lexCurrent->languageName;
    if (languageName) {
        return PyString_FromFormat("<%s object for \"%s\" at %p>", 
                                    self->ob_type->tp_name, languageName, self);
    } else {
        return PyString_FromFormat("<%s object at %p>",
                                    self->ob_type->tp_name, self);
    }
#else

    char buf[1024];
    if (languageName) {
        sprintf(buf, "<%s object for \"%s\" at %p>", 
                self->ob_type->tp_name, languageName, self);
    } else {
        sprintf(buf, "<%s object at %p>",
                self->ob_type->tp_name, self);
    }

    return PyString_FromString(buf);
#endif
}

PyTypeObject PyLexStateType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "LexerModule",
    sizeof(PyLexState),
    0,
    (destructor) PyLexState_dealloc,     /*tp_dealloc*/
    0,                                      /*tp_print*/
    (getattrfunc) PyLexState_getattr,    /*tp_getattr*/
    0,                                      /*tp_setattr*/
    0,                                      /*tp_compare*/
    (reprfunc) PyLexState_repr,          /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                                      /*tp_hash */
    0,                                      /*tp_call*/
    0,                                      /*tp_str */
};


void
initPyLexState(void)
{
    PyLexStateType.ob_type = &PyType_Type;
}
