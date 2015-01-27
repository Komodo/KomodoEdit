// scandir C speedups
//
// There's a fair bit of PY_MAJOR_VERSION boilerplate to support both Python 2
// and Python 3 -- the structure of this is taken from here:
// http://docs.python.org/3.3/howto/cporting.html

#include <Python.h>
#include <structseq.h>

#ifdef MS_WINDOWS
#include <windows.h>
#else
#include <dirent.h>
#endif

#if PY_MAJOR_VERSION >= 3
#define INITERROR return NULL
#define FROM_LONG PyLong_FromLong
#define BYTES_LENGTH PyBytes_GET_SIZE
#define TO_CHAR PyBytes_AS_STRING
#define UNICODE_AND_SIZE(u, w, s) w = PyUnicode_AsUnicodeAndSize(u, &s)
#else
#define INITERROR return
#define FROM_LONG PyInt_FromLong
#define BYTES_LENGTH PyString_GET_SIZE
#define TO_CHAR PyString_AS_STRING
#define UNICODE_AND_SIZE(u, w, s) w = PyUnicode_AsUnicode(u); s = PyUnicode_GetSize(u);
#endif

#ifdef Py_CLEANUP_SUPPORTED
#define PATH_CONVERTER_RESULT (Py_CLEANUP_SUPPORTED)
#else
#define PATH_CONVERTER_RESULT (1)
#endif

typedef struct {
    const char *function_name;
    const char *argument_name;
    int nullable;
    int allow_fd;
    wchar_t *wide;
    char *narrow;
    int arg_is_wide;
    int fd;
    Py_ssize_t length;
    PyObject *object;
    PyObject *cleanup;
} path_t;

static void
path_cleanup(path_t *path) {
    if (path->cleanup) {
        Py_CLEAR(path->cleanup);
    }
    free(path->wide);
    free(path->narrow);
}

#ifdef MS_WINDOWS
static int
win32_warn_bytes_api()
{
    return PyErr_WarnEx(PyExc_DeprecationWarning,
        "The Windows bytes API has been deprecated, "
        "use Unicode filenames instead",
        1);
}
#endif

static int
path_converter(PyObject *o, void *p) {
    path_t *path = (path_t *)p;
    PyObject *unicode, *bytes;
    Py_ssize_t length;
    char *narrow;

#define FORMAT_EXCEPTION(exc, fmt) \
    PyErr_Format(exc, "%s%s" fmt, \
        path->function_name ? path->function_name : "", \
        path->function_name ? ": "                : "", \
        path->argument_name ? path->argument_name : "path")

    /* Py_CLEANUP_SUPPORTED support */
    if (o == NULL) {
        path_cleanup(path);
        return 1;
    }

    /* ensure it's always safe to call path_cleanup() */
    path->cleanup = NULL;

    if (o == Py_None) {
        if (!path->nullable) {
            FORMAT_EXCEPTION(PyExc_TypeError,
                             "can't specify None for %s argument");
            return 0;
        }
        path->wide = NULL;
        path->narrow = NULL;
        path->length = 0;
        path->object = o;
        path->fd = -1;
        return 1;
    }

    unicode = PyUnicode_FromObject(o);
    if (unicode) {
#ifdef MS_WINDOWS
        wchar_t *wide;

        path->arg_is_wide = 1;
        UNICODE_AND_SIZE(unicode, wide, length);
        if (!wide) {
            Py_DECREF(unicode);
            return 0;
        }
        if (length > 32767) {
            FORMAT_EXCEPTION(PyExc_ValueError, "%s too long for Windows");
            Py_DECREF(unicode);
            return 0;
        }

        path->wide = wide;
        path->narrow = NULL;
        path->length = length;
        path->object = o;
        path->fd = -1;
        path->cleanup = unicode;
        return PATH_CONVERTER_RESULT;
#else
        path->arg_is_wide = 1;
#if PY_MAJOR_VERSION >= 3
        if (!PyUnicode_FSConverter(unicode, &bytes))
            bytes = NULL;
#else
        bytes = PyUnicode_AsEncodedString(unicode, Py_FileSystemDefaultEncoding, "strict");
#endif
        Py_DECREF(unicode);
#endif
    }
    else {
        path->arg_is_wide = 0;
        PyErr_Clear();
#if PY_MAJOR_VERSION >= 3
        if (PyObject_CheckBuffer(o)) {
            bytes = PyBytes_FromObject(o);
        }
#else
        if (PyString_Check(o)) {
            bytes = o;
            Py_INCREF(bytes);
        }
#endif
        else
            bytes = NULL;
        if (!bytes) {
            PyErr_Clear();
        }
    }

    if (!bytes) {
        if (!PyErr_Occurred())
            FORMAT_EXCEPTION(PyExc_TypeError, "illegal type for %s parameter");
        return 0;
    }

#ifdef MS_WINDOWS
    if (win32_warn_bytes_api()) {
        Py_DECREF(bytes);
        return 0;
    }
#endif

    length = BYTES_LENGTH(bytes);
#ifdef MS_WINDOWS
    if (length > MAX_PATH-1) {
        FORMAT_EXCEPTION(PyExc_ValueError, "%s too long for Windows");
        Py_DECREF(bytes);
        return 0;
    }
#endif

    narrow = TO_CHAR(bytes);
    if (length != strlen(narrow)) {
        FORMAT_EXCEPTION(PyExc_ValueError, "embedded NUL character in %s");
        Py_DECREF(bytes);
        return 0;
    }

    path->wide = NULL;
    path->narrow = narrow;
    path->length = length;
    path->object = o;
    path->fd = -1;
    path->cleanup = bytes;
    return PATH_CONVERTER_RESULT;
}

typedef struct {
    PyObject_HEAD
    path_t path;
    /* handle will be a HANDLE on Windows, and a DIR type on Posix
    */
    void* handle;
} FileIterator;

static PyObject *_iterfile(path_t);

#ifdef MS_WINDOWS

static PyObject *
win32_error_unicode(char* function, Py_UNICODE* filename)
{
    errno = GetLastError();
    if (filename)
        return PyErr_SetFromWindowsErrWithUnicodeFilename(errno, filename);
    else
        return PyErr_SetFromWindowsErr(errno);
}

/* Below, we *know* that ugo+r is 0444 */
#if _S_IREAD != 0400
#error Unsupported C library
#endif
static int
attributes_to_mode(DWORD attr)
{
    int m = 0;
    if (attr & FILE_ATTRIBUTE_DIRECTORY)
        m |= _S_IFDIR | 0111; /* IFEXEC for user,group,other */
    else
        m |= _S_IFREG;
    if (attr & FILE_ATTRIBUTE_READONLY)
        m |= 0444;
    else
        m |= 0666;
    return m;
}

double
filetime_to_time(FILETIME *filetime)
{
    const double SECONDS_BETWEEN_EPOCHS = 11644473600.0;

    unsigned long long total = (unsigned long long)filetime->dwHighDateTime << 32 |
                               (unsigned long long)filetime->dwLowDateTime;
    return (double)total / 10000000.0 - SECONDS_BETWEEN_EPOCHS;
}

unsigned long long
filetime_to_time_ns(FILETIME *filetime)
{
    const unsigned long long NS100_BETWEEN_EPOCHS = 116444736000000000ULL;

    unsigned long long total = (unsigned long long)filetime->dwHighDateTime << 32 |
                               (unsigned long long)filetime->dwLowDateTime;
    return (total - NS100_BETWEEN_EPOCHS) * 100ULL;
}

static PyTypeObject StatResultType;

static PyObject *
find_data_to_statresult(WIN32_FIND_DATAW *data)
{
    unsigned PY_LONG_LONG size;
    int mode;

    PyObject *v = PyStructSequence_New(&StatResultType);
    if (v == NULL)
        return NULL;

    size = (unsigned PY_LONG_LONG)data->nFileSizeHigh << 32 |
           (unsigned PY_LONG_LONG)data->nFileSizeLow;

    mode = attributes_to_mode(data->dwFileAttributes);
    if ((data->dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0 &&
            (data->dwReserved0 == IO_REPARSE_TAG_SYMLINK)) {
        mode ^= mode & 0170000;  /* S_IFMT */
        mode |= 0120000;         /* S_IFLNK */
    }

    PyStructSequence_SET_ITEM(v, 0, FROM_LONG(mode));
    PyStructSequence_SET_ITEM(v, 1, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 2, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 3, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 4, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 5, FROM_LONG(0));
    PyStructSequence_SET_ITEM(v, 6, PyLong_FromUnsignedLongLong((unsigned PY_LONG_LONG)size));
    PyStructSequence_SET_ITEM(v, 7, PyFloat_FromDouble(filetime_to_time(&data->ftLastAccessTime)));
    PyStructSequence_SET_ITEM(v, 8, PyFloat_FromDouble(filetime_to_time(&data->ftLastWriteTime)));
    PyStructSequence_SET_ITEM(v, 9, PyFloat_FromDouble(filetime_to_time(&data->ftCreationTime)));
    PyStructSequence_SET_ITEM(v, 10, PyLong_FromUnsignedLongLong(filetime_to_time_ns(&data->ftLastAccessTime)));
    PyStructSequence_SET_ITEM(v, 11, PyLong_FromUnsignedLongLong(filetime_to_time_ns(&data->ftLastWriteTime)));
    PyStructSequence_SET_ITEM(v, 12, PyLong_FromUnsignedLongLong(filetime_to_time_ns(&data->ftCreationTime)));
    PyStructSequence_SET_ITEM(v, 13, PyLong_FromUnsignedLong(data->dwFileAttributes));

    if (PyErr_Occurred()) {
        Py_DECREF(v);
        return NULL;
    }

    return v;
}

static PyStructSequence_Field stat_result_fields[] = {
    {"st_mode",    "protection bits"},
    {"st_ino",     "inode"},
    {"st_dev",     "device"},
    {"st_nlink",   "number of hard links"},
    {"st_uid",     "user ID of owner"},
    {"st_gid",     "group ID of owner"},
    {"st_size",    "total size, in bytes"},
    {"st_atime",   "time of last access"},
    {"st_mtime",   "time of last modification"},
    {"st_ctime",   "time of last change"},
    {"st_atime_ns",   "time of last access (integer nanoseconds)"},
    {"st_mtime_ns",   "time of last modification (integer nanoseconds)"},
    {"st_ctime_ns",   "time of last change (integer nanoseconds)"},
    {"st_file_attributes",  "Windows file attributes"},
    {0}
};

static PyStructSequence_Desc stat_result_desc = {
    "stat_result", /* name */
    NULL, /* doc */
    stat_result_fields,
    10
};

/* FileIterator support
*/
static void
_fi_close(FileIterator* fi)
{
HANDLE handle;

    handle = *((HANDLE *)fi->handle);
    if (handle != INVALID_HANDLE_VALUE) {
        Py_BEGIN_ALLOW_THREADS
        FindClose(handle);
        Py_END_ALLOW_THREADS
        free(fi->handle);
    }
}

static PyObject *
_fi_next(FileIterator* fi)
{
PyObject *file_data;
BOOL is_finished;
WIN32_FIND_DATAW data;
HANDLE *p_handle;

    if (!fi->path.wide) {
        return PyErr_Format(PyExc_TypeError,
                    "scandir needs a unicode path on Windows");
    }

    memset(&data, 0, sizeof(data));

    /*
    Put data into the iterator's data buffer, using the state of the
    hFind handle to determine whether this is the first iteration or
    a successive one.

    If the API indicates that there are no (or no more) files, raise
    a StopIteration exception.
    */
    is_finished = 0;
    while (1) {

        if (fi->handle == NULL) {
            p_handle = malloc(sizeof(HANDLE));
            if (p_handle == NULL) {
                return PyErr_NoMemory();
            }
            Py_BEGIN_ALLOW_THREADS
            *p_handle = FindFirstFileW(fi->path.wide, &data);
            Py_END_ALLOW_THREADS

            if (*p_handle == INVALID_HANDLE_VALUE) {
                if (GetLastError() != ERROR_FILE_NOT_FOUND) {
                    return PyErr_SetFromWindowsErr(GetLastError());
                }
                is_finished = 1;
            }
            fi->handle = (void *)p_handle;
        }
        else {
            Py_BEGIN_ALLOW_THREADS
            is_finished = !FindNextFileW(*((HANDLE *)fi->handle), &data);
            Py_END_ALLOW_THREADS

            if (is_finished) {
                if (GetLastError() != ERROR_NO_MORE_FILES) {
                    return PyErr_SetFromWindowsErr(GetLastError());
                }
                break;
            }
        }

        /* Only continue if we have a useful filename or we've run out of files
        A useful filename is one which isn't the "." and ".." pseudo-directories
        */
        if ((wcscmp(data.cFileName, L".") != 0 &&
             wcscmp(data.cFileName, L"..") != 0)) {
            break;
        }

    }

    if (is_finished) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }

    file_data = find_data_to_statresult(&data);
    if (!file_data) {
        return PyErr_SetFromWindowsErr(GetLastError());
    }
    else {
        return Py_BuildValue("u#N",
                            data.cFileName, wcslen(data.cFileName),
                            file_data);
    }
}

#else  // Linux / OS X

static void
_fi_close(FileIterator* fi)
{
    Py_BEGIN_ALLOW_THREADS
    closedir((DIR *)fi->handle);
    Py_END_ALLOW_THREADS
}

static PyObject *
_fi_next(FileIterator *fi)
{
struct dirent *ep;

    /*
    Put data into the iterator's data buffer, using the state of the
    hFind handle to determine whether this is the first iteration or
    a successive one.

    If the API indicates that there are no (or no more) files, raise
    a StopIteration exception.
    */
    while (1) {

        /* If the handle is NULL, this is the first time through the
        iterator: open the directory handle and drop through to the
        iteration logic proper.
        */
        if (fi->handle == NULL) {
            Py_BEGIN_ALLOW_THREADS
            fi->handle = (void *)opendir(fi->path.narrow);
            Py_END_ALLOW_THREADS

            if (fi->handle == NULL) {
                return PyErr_SetFromErrnoWithFilename(PyExc_OSError, fi->path.narrow);
            }
        }

        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        ep = readdir((DIR *)fi->handle);
        Py_END_ALLOW_THREADS

        /* If nothing was returned, it's either an error (errno != 0) or
        the end of the list of entries, in which case flag is_finished.
        */
        if (ep == NULL) {
            if (errno != 0) {
                return PyErr_SetFromErrnoWithFilename(PyExc_OSError, fi->path.narrow);
            }
            break;
        }

        if ((strcmp(ep->d_name, ".") != 0 &&
            strcmp(ep->d_name, "..") != 0)) {
            break;
        }
    }

    if (ep == NULL) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }

#if PY_MAJOR_VERSION >= 3
    return Py_BuildValue("yN", ep->d_name, FROM_LONG(ep->d_type));
#else
    return Py_BuildValue("sN", ep->d_name, FROM_LONG(ep->d_type));
#endif
}

#endif

static void
fi_dealloc(PyObject *iterator)
{
FileIterator *fi;

    fi = (FileIterator *)iterator;
    if (fi != NULL) {
        if (fi->handle != NULL) {
            _fi_close(fi);
        }
        path_cleanup(&(fi->path));
        PyObject_Del(iterator);
    }
}

static PyObject *
fi_iternext(PyObject *iterator)
{
FileIterator *fi;

    /*
    There's scope here for refactoring things like the check
    for dot and double-dot directories and possibly converting
    the stat result. For now those, we'll just leave it simple.
    */
    fi = (FileIterator *)iterator;
    return _fi_next(fi);
}


PyTypeObject FileIterator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "FileIterator",                        /* tp_name */
    sizeof(FileIterator),                /* tp_basicsize */
    0,                                    /* tp_itemsize */
    /* methods */
    (destructor)fi_dealloc,             /* tp_dealloc */
    0,                                    /* tp_print */
    0,                                    /* tp_getattr */
    0,                                    /* tp_setattr */
    0,                                    /* tp_compare */
    0,                                    /* tp_repr */
    0,                                    /* tp_as_number */
    0,                                    /* tp_as_sequence */
    0,                                    /* tp_as_mapping */
    0,                                    /* tp_hash */
    0,                                    /* tp_call */
    0,                                    /* tp_str */
    PyObject_GenericGetAttr,            /* tp_getattro */
    0,                                    /* tp_setattro */
    0,                                    /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                 /* tp_flags */
    0,                                    /* tp_doc */
    0,                                    /* tp_traverse */
    0,                                    /* tp_clear */
    0,                                    /* tp_richcompare */
    0,                                    /* tp_weaklistoffset */
    PyObject_SelfIter,                    /* tp_iter */
    (iternextfunc)fi_iternext,            /* tp_iternext */
    0,                                    /* tp_methods */
    0,                                    /* tp_members */
    0,                                    /* tp_getset */
    0,                                    /* tp_base */
    0,                                    /* tp_dict */
    0,                                    /* tp_descr_get */
    0,                                    /* tp_descr_set */
};

static PyObject*
_iterfile(path_t path)
{
    FileIterator *iterator = PyObject_New(FileIterator, &FileIterator_Type);
    if (iterator == NULL) {
        return NULL;
    }
    iterator->handle = NULL;
    iterator->path = path;
    return (PyObject *)iterator;
}

static PyObject *
scandir_helper(PyObject *self, PyObject *args, PyObject *kwargs)
{
path_t path;
static char *keywords[] = {"path", NULL};
PyObject *iterator;

    memset(&path, 0, sizeof(path));
    path.function_name = "scandir_helper";

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O&:scandir_helper", keywords,
                                     path_converter, &path)) {
        return NULL;
    }

   if (path.wide) {
        wchar_t *filepath;

        /* Reallocate for additional backslash and wildcard */
        filepath = (wchar_t *)malloc(sizeof(wchar_t) * (path.length + 3));
        if (filepath == NULL)
            return PyErr_NoMemory();
        wcscpy(filepath, path.wide);
        if ((path.wide[path.length] != L'\\') && (path.wide[path.length] != L'/')) {
            wcscat(filepath, L"/");
        }
#ifdef MS_WINDOWS
        wcscat(filepath, L"*");
#endif
        path.wide = filepath;
        path.length = wcslen(path.wide);
    }
    if (path.narrow) {
        char *filepath;

        filepath = (char *)malloc(sizeof(char) * (path.length + 2));
        if (filepath == NULL)
            return PyErr_NoMemory();
        strcpy(filepath, path.narrow);
        if ((path.narrow[path.length] != '\\') && (path.narrow[path.length] != '/')) {
            strcat(filepath, "/");
        }
#ifdef MS_WINDOWS
        strcat(filepath, "*");
#endif
        path.narrow = filepath;
        path.length = strlen(path.narrow);
    }

    iterator = _iterfile(path);
    if (iterator == NULL) {
        path_cleanup(&path);
        return NULL;
    }
    return iterator;
}

static PyMethodDef scandir_methods[] = {
    {"scandir_helper", (PyCFunction)scandir_helper, METH_VARARGS | METH_KEYWORDS, NULL},
    {"iterdir", (PyCFunction)scandir_helper, METH_VARARGS | METH_KEYWORDS, NULL},
    {NULL, NULL},
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_scandir",
        NULL,
        0,
        scandir_methods,
        NULL,
        NULL,
        NULL,
        NULL,
};
#endif

#if PY_MAJOR_VERSION >= 3
PyObject *
PyInit__scandir(void)
{
    PyObject *module = PyModule_Create(&moduledef);
#else
void
init_scandir(void)
{
    PyObject *module = Py_InitModule("_scandir", scandir_methods);
#endif
    if (module == NULL) {
        INITERROR;
    }

    if (PyType_Ready(&FileIterator_Type) < 0) {
        INITERROR;
    }

#ifdef MS_WINDOWS
    stat_result_desc.name = "scandir.stat_result";
    PyStructSequence_InitType(&StatResultType, &stat_result_desc);
#endif

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
