/*
Ben's notes:

* three files should be #included in posixmodule.c
  - posixmodule_scandir_main.c (this file) after posix_set_blocking
  - posixmodule_scandir_methods.c at end of posix_methods (before Sentinel)
  - posixmodule_scandir_init.c after "PyStructSequence_InitType2(&TerminalSizeType"

* something I noticed while looking at _listdir_windows_no_opendir():
  - "bufptr" is not used
  - initial Py_ARRAY_LENGTH(namebuf)-4 value of "len" is not used
  - "po" is not used

* haypo's feedback:
  - he'd prefer if DirEntry.path was a read-only property (store scandir_path
    and join to name on demand)
  - 
*/

#include "structmember.h"

PyDoc_STRVAR(posix_scandir__doc__,
"scandir(path='.') -> iterator of DirEntry objects for given path");

static char *follow_symlinks_keywords[] = {"follow_symlinks", NULL};

typedef struct {
    PyObject_HEAD
    PyObject *name;
    PyObject *path;
    PyObject *stat;
    PyObject *lstat;
#ifdef MS_WINDOWS
    struct win32_stat win32_lstat;
#else
    unsigned char d_type;
#endif
} DirEntry;

static void
DirEntry_dealloc(DirEntry *entry)
{
    Py_XDECREF(entry->name);
    Py_XDECREF(entry->path);
    Py_XDECREF(entry->stat);
    Py_XDECREF(entry->lstat);
    Py_TYPE(entry)->tp_free((PyObject *)entry);
}

#ifdef MS_WINDOWS

static PyObject *
DirEntry_is_symlink(DirEntry *self)
{
    return PyBool_FromLong((self->win32_lstat.st_mode & S_IFMT) == S_IFLNK);
}

static PyObject *
DirEntry_get_lstat(DirEntry *self)
{
    if (!self->lstat) {
        self->lstat = _pystat_fromstructstat(&self->win32_lstat);
    }
    Py_XINCREF(self->lstat);
    return self->lstat;
}

static PyObject *
DirEntry_get_stat(DirEntry *self, int follow_symlinks)
{
    if (follow_symlinks) {
        if (!self->stat) {
            if ((self->win32_lstat.st_mode & S_IFMT) == S_IFLNK) {
                path_t path = PATH_T_INITIALIZE("DirEntry.stat", NULL, 0, 0);

                if (!path_converter(self->path, &path)) {
                    return NULL;
                }
                self->stat = posix_do_stat("DirEntry.stat", &path, DEFAULT_DIR_FD, 1);
                path_cleanup(&path);
            }
            else {
                self->stat = DirEntry_get_lstat(self);
            }
        }
        Py_XINCREF(self->stat);
        return self->stat;
    }
    else {
        return DirEntry_get_lstat(self);
    }
}

#else  /* POSIX */

/* Forward reference */
static PyObject *
DirEntry_test_mode(DirEntry *self, int follow_symlinks, unsigned short mode_bits);

static PyObject *
DirEntry_is_symlink(DirEntry *self)
{
    if (self->d_type != DT_UNKNOWN) {
        return PyBool_FromLong(self->d_type == DT_LNK);
    }
    else {
        return DirEntry_test_mode(self, 0, S_IFLNK);
    }
}

static PyObject *
DirEntry_fetch_stat(DirEntry *self, int follow_symlinks)
{
    PyObject *result;
    path_t path = PATH_T_INITIALIZE("DirEntry.stat", NULL, 0, 0);

    if (!path_converter(self->path, &path)) {
        return NULL;
    }
    result = posix_do_stat("DirEntry.stat", &path, DEFAULT_DIR_FD, follow_symlinks);
    path_cleanup(&path);
    return result;
}

static PyObject *
DirEntry_get_lstat(DirEntry *self)
{
    if (!self->lstat) {
        self->lstat = DirEntry_fetch_stat(self, 0);
    }
    Py_XINCREF(self->lstat);
    return self->lstat;
}

static PyObject *
DirEntry_get_stat(DirEntry *self, int follow_symlinks)
{
    if (follow_symlinks) {
        if (!self->stat) {
            int is_symlink;
            PyObject *po_is_symlink = DirEntry_is_symlink(self);
            if (!po_is_symlink) {
                return NULL;
            }
            is_symlink = PyObject_IsTrue(po_is_symlink);
            Py_DECREF(po_is_symlink);

            if (is_symlink) {
                self->stat = DirEntry_fetch_stat(self, 1);
            }
            else {
                self->stat = DirEntry_get_lstat(self);
            }
        }
        Py_XINCREF(self->stat);
        return self->stat;
    }
    else {
        return DirEntry_get_lstat(self);
    }
}

#endif

static PyObject *
DirEntry_stat(DirEntry *self, PyObject *args, PyObject *kwargs)
{
    int follow_symlinks = 1;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|$p:DirEntry.stat",
                                     follow_symlinks_keywords,
                                     &follow_symlinks)) {
        return NULL;
    }

    return DirEntry_get_stat(self, follow_symlinks);
}

static PyObject *
DirEntry_test_mode(DirEntry *self, int follow_symlinks, unsigned short mode_bits)
{
    PyObject *stat = NULL;
    PyObject *st_mode = NULL;
    int mode;
    int result = 0;
    int is_symlink;
    int need_stat;
    unsigned long dir_bits;

#ifdef MS_WINDOWS
    is_symlink = (self->win32_lstat.st_mode & S_IFMT) == S_IFLNK;
    need_stat = follow_symlinks && is_symlink;
#else
    is_symlink = self->d_type == DT_LNK;
    need_stat = self->d_type == DT_UNKNOWN || (follow_symlinks && is_symlink);
#endif
    if (need_stat) {
        stat = DirEntry_get_stat(self, follow_symlinks);
        if (!stat) {
            if (PyErr_ExceptionMatches(PyExc_OSError) && errno == ENOENT) {
                /* If file doesn't exist (anymore), then return False
                   (say it's not a directory) */
                PyErr_Clear();
                Py_RETURN_FALSE;
            }
            goto error;
        }
        st_mode = PyObject_GetAttrString(stat, "st_mode");
        if (!st_mode) {
            goto error;
        }

        mode = PyLong_AsLong(st_mode);
        if (mode == -1 && PyErr_Occurred()) {
            goto error;
        }
        Py_DECREF(st_mode);
        Py_DECREF(stat);
        result = (mode & S_IFMT) == mode_bits;
    }
    else if (is_symlink) {
        assert(mode_bits != S_IFLNK);
        result = 0;
    }
    else {
        assert(mode_bits == S_IFDIR || mode_bits == S_IFREG);
#ifdef MS_WINDOWS
        dir_bits = self->win32_lstat.st_file_attributes & FILE_ATTRIBUTE_DIRECTORY;
        if (mode_bits == S_IFDIR) {
            result = dir_bits != 0;
        }
        else {
            result = dir_bits == 0;
        }
#else
        if (mode_bits == S_IFDIR) {
            result = self->d_type == DT_DIR;
        }
        else {
            result = self->d_type == DT_REG;
        }
#endif
    }

    return PyBool_FromLong(result);

error:
    Py_XDECREF(st_mode);
    Py_XDECREF(stat);
    return NULL;
}

static PyObject *
DirEntry_is_dir(DirEntry *self, PyObject *args, PyObject *kwargs)
{
    int follow_symlinks = 1;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|$p:DirEntry.is_dir",
                                     follow_symlinks_keywords,
                                     &follow_symlinks)) {
        return NULL;
    }

    return DirEntry_test_mode(self, follow_symlinks, S_IFDIR);
}

static PyObject *
DirEntry_is_file(DirEntry *self, PyObject *args, PyObject *kwargs)
{
    int follow_symlinks = 1;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|$p:DirEntry.is_file",
                                     follow_symlinks_keywords,
                                     &follow_symlinks)) {
        return NULL;
    }

    return DirEntry_test_mode(self, follow_symlinks, S_IFREG);
}

static PyMemberDef DirEntry_members[] = {
    {"name", T_OBJECT_EX, offsetof(DirEntry, name), READONLY,
     "the entry's base filename, relative to scandir() \"path\" argument"},
    {"path", T_OBJECT_EX, offsetof(DirEntry, path), READONLY,
     "the entry's full path name; equivalent to os.path.join(scandir_path, entry.name)"},
    {NULL}
};

static PyMethodDef DirEntry_methods[] = {
    {"is_dir", (PyCFunction)DirEntry_is_dir, METH_VARARGS | METH_KEYWORDS,
     "return True if the entry is a directory; cached per entry"
    },
    {"is_file", (PyCFunction)DirEntry_is_file, METH_VARARGS | METH_KEYWORDS,
     "return True if the entry is a file; cached per entry"
    },
    {"is_symlink", (PyCFunction)DirEntry_is_symlink, METH_NOARGS,
     "return True if the entry is a symbolic link; cached per entry"
    },
    {"stat", (PyCFunction)DirEntry_stat, METH_VARARGS | METH_KEYWORDS,
     "return stat_result object for the entry; cached per entry"
    },
    {NULL}
};

PyTypeObject DirEntryType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "DirEntry",                             /* tp_name */
    sizeof(DirEntry),                       /* tp_basicsize */
    0,                                      /* tp_itemsize */
    /* methods */
    (destructor)DirEntry_dealloc,           /* tp_dealloc */
    0,                                      /* tp_print */
    0,                                      /* tp_getattr */
    0,                                      /* tp_setattr */
    0,                                      /* tp_compare */
    0,                                      /* tp_repr */
    0,                                      /* tp_as_number */
    0,                                      /* tp_as_sequence */
    0,                                      /* tp_as_mapping */
    0,                                      /* tp_hash */
    0,                                      /* tp_call */
    0,                                      /* tp_str */
    0,                                      /* tp_getattro */
    0,                                      /* tp_setattro */
    0,                                      /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                     /* tp_flags */
    0,                                      /* tp_doc */
    0,                                      /* tp_traverse */
    0,                                      /* tp_clear */
    0,                                      /* tp_richcompare */
    0,                                      /* tp_weaklistoffset */
    0,                                      /* tp_iter */
    0,                                      /* tp_iternext */
    DirEntry_methods,                       /* tp_methods */
    DirEntry_members,                       /* tp_members */
};

static char *
join_path_filenameA(char *path_narrow, char* filename, Py_ssize_t filename_len)
{
    Py_ssize_t path_len;
    char *result;
    char ch;

    if (!path_narrow) { /* Default arg: "." */
        path_narrow = ".";
        path_len = 1;
    }
    else {
        path_len = strlen(path_narrow);
    }

    if (filename_len == -1) {
        filename_len = strlen(filename);
    }

    /* The +1's are for the path separator and the NUL */
    result = PyMem_Malloc(path_len + 1 + filename_len + 1);
    if (!result) {
        PyErr_NoMemory();
        return NULL;
    }
    strcpy(result, path_narrow);
    ch = result[path_len - 1];
#ifdef MS_WINDOWS
    if (ch != '\\' && ch != '/' && ch != ':') {
        result[path_len++] = '\\';
    }
#else
    if (ch != '/') {
        result[path_len++] = '/';
    }
#endif
    strcpy(result + path_len, filename);
    return result;
}

#ifdef MS_WINDOWS

static void
find_data_to_stat(WIN32_FIND_DATAW *data, struct win32_stat *result)
{
    /* Note: data argument can point to a WIN32_FIND_DATAW or a
       WIN32_FIND_DATAA struct, as the first members are in the same
       position, and cFileName is not used here
    */
    memset(result, 0, sizeof(*result));

    result->st_mode = attributes_to_mode(data->dwFileAttributes);
    if ((data->dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) != 0 &&
            (data->dwReserved0 == IO_REPARSE_TAG_SYMLINK)) {
        /* first clear the S_IFMT bits */
        result->st_mode ^= (result->st_mode & S_IFMT);
        /* now set the bits that make this a symlink */
        result->st_mode |= S_IFLNK;
    }

    result->st_size = (((__int64)data->nFileSizeHigh)<<32) + data->nFileSizeLow;

    FILE_TIME_to_time_t_nsec(&data->ftCreationTime, &result->st_ctime, &result->st_ctime_nsec);
    FILE_TIME_to_time_t_nsec(&data->ftLastWriteTime, &result->st_mtime, &result->st_mtime_nsec);
    FILE_TIME_to_time_t_nsec(&data->ftLastAccessTime, &result->st_atime, &result->st_atime_nsec);

    result->st_file_attributes = data->dwFileAttributes;
}

static wchar_t *
join_path_filenameW(wchar_t *path_wide, wchar_t* filename)
{
    Py_ssize_t path_len;
    wchar_t *result;
    wchar_t ch;

    if (!path_wide) { /* Default arg: "." */
        path_wide = L".";
        path_len = 1;
    }
    else {
        path_len = wcslen(path_wide);
    }

    /* The +1's are for the path separator and the NUL */
    result = PyMem_Malloc((path_len + 1 + wcslen(filename) + 1) * sizeof(wchar_t));
    if (!result) {
        PyErr_NoMemory();
        return NULL;
    }
    wcscpy(result, path_wide);
    ch = result[path_len - 1];
    if (ch != SEP && ch != ALTSEP && ch != L':') {
        result[path_len++] = SEP;
    }
    wcscpy(result + path_len, filename);
    return result;
}

static PyObject *
DirEntry_new(path_t *path, void *data)
{
    DirEntry *entry;

    entry = PyObject_New(DirEntry, &DirEntryType);
    if (!entry) {
        return NULL;
    }
    entry->name = NULL;
    entry->path = NULL;
    entry->stat = NULL;
    entry->lstat = NULL;

    if (!path->narrow) {
        WIN32_FIND_DATAW *dataW = (WIN32_FIND_DATAW *)data;
        wchar_t *path_strW;

        entry->name = PyUnicode_FromWideChar(dataW->cFileName, wcslen(dataW->cFileName));
        if (!entry->name) {
            goto error;
        }

        path_strW = join_path_filenameW(path->wide, dataW->cFileName);
        if (!path_strW) {
            goto error;
        }
        entry->path = PyUnicode_FromWideChar(path_strW, wcslen(path_strW));
        PyMem_Free(path_strW);
        if (!entry->path) {
            goto error;
        }
    }
    else {
        WIN32_FIND_DATAA *dataA = (WIN32_FIND_DATAA *)data;
        char *path_strA;

        entry->name = PyBytes_FromString(dataA->cFileName);
        if (!entry->name) {
            goto error;
        }

        path_strA = join_path_filenameA(path->narrow, dataA->cFileName, -1);
        if (!path_strA) {
            goto error;
        }
        entry->path = PyBytes_FromString(path_strA);
        PyMem_Free(path_strA);
        if (!entry->path) {
            goto error;
        }
    }
    find_data_to_stat((WIN32_FIND_DATAW *)data, &entry->win32_lstat);

    return (PyObject *)entry;

error:
    Py_XDECREF(entry);
    return NULL;
}

#else  /* POSIX */

static PyObject *
DirEntry_new(path_t *path, char *name, Py_ssize_t name_len, unsigned char d_type)
{
    DirEntry *entry;
    char *joined_path;

    entry = PyObject_New(DirEntry, &DirEntryType);
    if (!entry) {
        return NULL;
    }
    entry->name = NULL;
    entry->path = NULL;
    entry->stat = NULL;
    entry->lstat = NULL;

    joined_path = join_path_filenameA(path->narrow, name, name_len);
    if (!joined_path) {
        goto error;
    }

    if (!path->narrow || !PyBytes_Check(path->object)) {
        entry->name = PyUnicode_DecodeFSDefaultAndSize(name, name_len);
        entry->path = PyUnicode_DecodeFSDefault(joined_path);
    }
    else {
        entry->name = PyBytes_FromStringAndSize(name, name_len);
        entry->path = PyBytes_FromString(joined_path);
    }
    PyMem_Free(joined_path);
    if (!entry->name || !entry->path) {
        goto error;
    }

    entry->d_type = d_type;

    return (PyObject *)entry;

error:
    Py_XDECREF(entry);
    return NULL;
}
#endif

typedef struct {
    PyObject_HEAD
    path_t path;
    int yield_name;  /* for when listdir() is implemented using scandir() */
#ifdef MS_WINDOWS
    HANDLE handle;
#else
    DIR *dirp;
#endif
} ScandirIterator;

static void
ScandirIterator_dealloc(ScandirIterator *iterator)
{
    Py_XDECREF(iterator->path.object);
    path_cleanup(&iterator->path);
    Py_TYPE(iterator)->tp_free((PyObject *)iterator);
}

#ifdef MS_WINDOWS

static PyObject *
ScandirIterator_iternext(ScandirIterator *iterator)
{
    union {  /* We only use one at a time, so save space */
        WIN32_FIND_DATAW W;
        WIN32_FIND_DATAA A;
    } FileData;

    int is_unicode = !iterator->path.narrow;

    while (1) {
        if (iterator->handle == INVALID_HANDLE_VALUE) {
            /* First time around, prepare path and call FindFirstFile */
            if (is_unicode) {
                wchar_t *path_strW;

                path_strW = join_path_filenameW(iterator->path.wide, L"*.*");
                if (!path_strW) {
                    return NULL;
                }

                Py_BEGIN_ALLOW_THREADS
                iterator->handle = FindFirstFileW(path_strW, &FileData.W);
                Py_END_ALLOW_THREADS

                PyMem_Free(path_strW);  /* We're done with path_strW now */
            }
            else {
                char *path_strA;

                path_strA = join_path_filenameA(iterator->path.narrow, "*.*", -1);
                if (!path_strA) {
                    return NULL;
                }

                Py_BEGIN_ALLOW_THREADS
                iterator->handle = FindFirstFileA(path_strA, &FileData.A);
                Py_END_ALLOW_THREADS

                PyMem_Free(path_strA);  /* We're done with path_strA now */
            }

            if (iterator->handle == INVALID_HANDLE_VALUE) {
                if (GetLastError() != ERROR_FILE_NOT_FOUND) {
                    return path_error(&iterator->path);
                }
                /* No files found, stop iterating */
                PyErr_SetNone(PyExc_StopIteration);
                return NULL;
            }
        }
        else {
            BOOL success;

            Py_BEGIN_ALLOW_THREADS
            success = is_unicode ? FindNextFileW(iterator->handle, &FileData.W) :
                                   FindNextFileA(iterator->handle, &FileData.A);
            Py_END_ALLOW_THREADS

            if (!success) {
                if (GetLastError() != ERROR_NO_MORE_FILES) {
                    return path_error(&iterator->path);
                }
                /* No more files found in directory, stop iterating */
                Py_BEGIN_ALLOW_THREADS
                success = FindClose(iterator->handle);
                Py_END_ALLOW_THREADS
                if (!success) {
                    return path_error(&iterator->path);
                }
                iterator->handle = INVALID_HANDLE_VALUE;

                PyErr_SetNone(PyExc_StopIteration);
                return NULL;
            }
        }

        /* Skip over . and .. */
        if (is_unicode) {
            if (wcscmp(FileData.W.cFileName, L".") != 0 &&
                    wcscmp(FileData.W.cFileName, L"..") != 0) {
                if (iterator->yield_name) {
                    return PyUnicode_FromWideChar(FileData.W.cFileName, wcslen(FileData.W.cFileName));
                }
                else {
                    return DirEntry_new(&iterator->path, &FileData.W);
                }
            }
        }
        else {
            if (strcmp(FileData.A.cFileName, ".") != 0 &&
                    strcmp(FileData.A.cFileName, "..") != 0) {
                if (iterator->yield_name) {
                    return PyBytes_FromString(FileData.A.cFileName);
                }
                else {
                    return DirEntry_new(&iterator->path, &FileData.A);
                }
            }
        }

        /* Loop till we get a non-dot directory or finish iterating */
    }
}

#else  /* POSIX */

static PyObject *
ScandirIterator_iternext(ScandirIterator *iterator)
{
    struct dirent *direntp;
    Py_ssize_t name_len;
    int is_dot;

    if (!iterator->dirp) {
        /* First time iterating, prepare path and call opendir */
        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        iterator->dirp = opendir(iterator->path.narrow ? iterator->path.narrow : ".");
        Py_END_ALLOW_THREADS

        if (!iterator->dirp) {
            return path_error(&iterator->path);
        }
    }

    while (1) {
        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        direntp = readdir(iterator->dirp);
        Py_END_ALLOW_THREADS

        if (!direntp) {
            int result;

            if (errno != 0) {
                return path_error(&iterator->path);
            }

            /* No more files found in directory, stop iterating */
            Py_BEGIN_ALLOW_THREADS
            result = closedir(iterator->dirp);
            Py_END_ALLOW_THREADS
            if (result != 0) {
                return path_error(&iterator->path);
            }
            iterator->dirp = NULL;

            PyErr_SetNone(PyExc_StopIteration);
            return NULL;
        }

        /* Skip over . and .. */
        name_len = NAMLEN(direntp);
        is_dot = direntp->d_name[0] == '.' &&
                 (name_len == 1 || (direntp->d_name[1] == '.' && name_len == 2));
        if (!is_dot) {
            if (!iterator->yield_name) {
                return DirEntry_new(&iterator->path, direntp->d_name, name_len,
                                    direntp->d_type);
            }
            if (!iterator->path.narrow || !PyBytes_Check(iterator->path.object)) {
                return PyUnicode_DecodeFSDefaultAndSize(direntp->d_name, name_len);
            }
            else {
                return PyBytes_FromStringAndSize(direntp->d_name, name_len);
            }
        }

        /* Loop till we get a non-dot directory or finish iterating */
    }
}

#endif

PyTypeObject ScandirIteratorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "ScandirIterator",                      /* tp_name */
    sizeof(ScandirIterator),                /* tp_basicsize */
    0,                                      /* tp_itemsize */
    /* methods */
    (destructor)ScandirIterator_dealloc,    /* tp_dealloc */
    0,                                      /* tp_print */
    0,                                      /* tp_getattr */
    0,                                      /* tp_setattr */
    0,                                      /* tp_compare */
    0,                                      /* tp_repr */
    0,                                      /* tp_as_number */
    0,                                      /* tp_as_sequence */
    0,                                      /* tp_as_mapping */
    0,                                      /* tp_hash */
    0,                                      /* tp_call */
    0,                                      /* tp_str */
    0,                                      /* tp_getattro */
    0,                                      /* tp_setattro */
    0,                                      /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                     /* tp_flags */
    0,                                      /* tp_doc */
    0,                                      /* tp_traverse */
    0,                                      /* tp_clear */
    0,                                      /* tp_richcompare */
    0,                                      /* tp_weaklistoffset */
    PyObject_SelfIter,                      /* tp_iter */
    (iternextfunc)ScandirIterator_iternext, /* tp_iternext */
};

static PyObject *
posix_scandir(PyObject *self, PyObject *args, PyObject *kwargs)
{
    ScandirIterator *iterator;
    static char *keywords[] = {"path", NULL};

    iterator = PyObject_New(ScandirIterator, &ScandirIteratorType);
    if (!iterator) {
        return NULL;
    }
    iterator->yield_name = 0;
    memset(&iterator->path, 0, sizeof(path_t));
    iterator->path.function_name = "scandir";
    iterator->path.nullable = 1;

#ifdef MS_WINDOWS
    iterator->handle = INVALID_HANDLE_VALUE;
#else
    iterator->dirp = NULL;
#endif

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O&:scandir", keywords,
                                     path_converter, &iterator->path)) {
        Py_DECREF(iterator);
        return NULL;
    }

    /* path_converter doesn't keep path.object around, so do it
       manually for the lifetime of the iterator here (the refcount
       is decremented in ScandirIterator_dealloc)
    */
    Py_XINCREF(iterator->path.object);

    return (PyObject *)iterator;
}

/* TODO ben: version of listdir() implemented using ScandirIterator;
   note that this doesn't yet support specifying a file descriptor */
static PyObject *
posix_listdir2(PyObject *self, PyObject *args, PyObject *kwargs)
{
    ScandirIterator *iterator = NULL;
    PyObject *list = NULL;

    iterator = (ScandirIterator *)posix_scandir(self, args, kwargs);
    if (!iterator) {
        goto error;
    }
    iterator->yield_name = 1;

    list = PyList_New(0);
    if (!list) {
        goto error;
    }

    while (1) {
        PyObject *name = ScandirIterator_iternext(iterator);
        if (!name) {
            if (PyErr_ExceptionMatches(PyExc_StopIteration)) {
                PyErr_Clear();
                break;
            }
            else {
                goto error;
            }
        }
        if (PyList_Append(list, name) != 0) {
            goto error;
        }
    }

    Py_DECREF(iterator);
    return list;

error:
    Py_XDECREF(list);
    Py_XDECREF(iterator);
    return NULL;
}
