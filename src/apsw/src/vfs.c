/*
  VFS code

  See the accompanying LICENSE file.
*/

/**

.. _vfs:

Virtual File System (VFS)
*************************

SQLite 3.6 has new `VFS functionality
<https://sqlite.org/c3ref/vfs.html>`_ which defines the interface
between the SQLite core and the underlying operating system. The
majority of the functionality deals with files. APSW exposes this
functionality letting you provide your own routines. You can also
*inherit* from an existing vfs making it easy to augment or override
specific routines. For example you could obfuscate your database by
XORing the data implemented by augmenting the read and write
methods. The method names are exactly the same as SQLite uses making
it easier to read the SQLite documentation, trouble tickets, web
searches or mailing lists. The SQLite convention results in names like
xAccess, xCurrentTime and xWrite.

You specify which VFS to use as a parameter to the :class:`Connection`
constructor.

.. code-block:: python

  db=apsw.Connection("file", vfs="myvfs")

The easiest way to get started is to make a :class:`VFS` derived class
that inherits from the default vfs.  Then override methods you want to
change behaviour of.  If you want to just change how file operations
are done then you have to override :meth:`VFS.xOpen` to return a file
instance that has your overridden :class:`VFSFile` methods.  The
:ref:`example <example-vfs>` demonstrates obfuscating the database
file contents.

.. note::

  All strings supplied and returned to :class:`VFS`/:class:`VFSFile`
  routines are treated as Unicode.

Exceptions and errors
=====================

To return an error from any routine you should raise an exception. The
exception will be translated into the appropriate SQLite error code
for SQLite. To return a specific SQLite error code use
:meth:`exceptionfor`.  If the exception does not map to any specific
error code then :const:`SQLITE_ERROR` which corresponds to
:exc:`SQLError` is returned to SQLite.

The SQLite code that deals with VFS errors behaves in varying
ways. Some routines have no way to return an error (eg `xDlOpen
<https://sqlite.org/c3ref/vfs.html>`_ just returns zero/NULL on
being unable to load a library, `xSleep
<https://sqlite.org/c3ref/vfs.html>`_ has no error return
parameter), others are unified (eg almost any
error in xWrite will be returned to the user as disk full
error). Sometimes errors are ignored as they are harmless such as when
a journal can't be deleted after a commit (the journal is marked as
obsolete before being deleted).  Simple operations such as opening a
database can result in many different VFS function calls such as hot
journals being detected, locking, and read/writes for
playback/rollback.

To avoid confusion with exceptions being raised in the VFS and
exceptions from normal code to open Connections or execute SQL
queries, VFS exceptions are not raised in the normal way. (If they
were, only one could be raised and it would obscure whatever
exceptions the :class:`Connection` open or SQL query execute wanted to
raise.)  Instead the :meth:`VFS.excepthook` or
:meth:`VFSFile.excepthook` method is called with a tuple of exception
type, exception value and exception traceback. The default
implementation of ``excepthook`` calls ``sys.excepthook()`` which
under Python 2 shows the stack trace and under Python 3 merely prints
the exception value. (If ``sys.excepthook`` fails then
``PyErr_Display()`` is called.)

In normal VFS usage there will be no exceptions raised, or specific
expected ones which APSW clears after noting them and returning the
appropriate value back to SQLite. The exception hooking behaviour
helps you find issues in your code or unexpected behaviour of the
external environment. Remember that :ref:`augmented stack traces
<augmentedstacktraces>` are available which significantly increase
detail about the exceptions.

As an example, lets say you have a divide by zero error in your xWrite
routine. The table below shows what happens with time going down and
across.

+----------------------------------------------+--------------------------------+---------------------------------------------+
| Python Query Code                            | SQLite and APSW C code         | Python VFS code                             |
+==============================================+================================+=============================================+
| ``cursor.execute("update table set foo=3")`` |                                |                                             |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              | SQLite starts executing query  |                                             |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              |                                | Your VFS routines are called                |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              |                                | Your xWrite divides by zero                 |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              |                                | :meth:`VFSFile.excepthook` is called with   |
|                                              |                                | ZeroDivision exception                      |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              | :const:`SQLITE_ERROR` (closest |                                             |
|                                              | matching SQLite error code) is |                                             |
|                                              | returned to SQLite by APSW     |                                             |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              | SQLite error handling and      | More VFS routines are called.  Any          |
|                                              | recovery operates which calls  | exceptions in these routines will result in |
|                                              | more VFS routines.             | :meth:`VFSFile.excepthook` being called with|
|                                              |                                | them.                                       |
+----------------------------------------------+--------------------------------+---------------------------------------------+
|                                              | SQLite returns                 |                                             |
|                                              | :const:`SQLITE_FULL` to APSW   |                                             |
+----------------------------------------------+--------------------------------+---------------------------------------------+
| APSW returns :class:`apsw.FullError`         |                                |                                             |
+----------------------------------------------+--------------------------------+---------------------------------------------+

*/


/* Naming convention prefixes.  Since sqlite3.c is #included alongside
   this file we have to ensure there is no clash with its names.
   There are two objects - the VFS itself and a VFSFile as returned
   from xOpen.  For each there are both C and Python methods.  The C
   methods are what SQLite calls and effectively turns a C call into a
   Python call.  The Python methods turn a Python call into the C call
   of the (SQLite C) object we are inheriting from and wouldn't be
   necessary if we didn't implement the inheritance feature.

   Methods:

   apswvfs_         sqlite3_vfs* functions https://sqlite.org/c3ref/vfs.html
   apswvfspy_       Python implementations of those same functions
   apswvfsfile_     io methods https://sqlite.org/c3ref/io_methods.html
   apswvfsfilepy_   Python implementations of those same functions

   Structures:

   APSWVFS          Python object for vfs (sqlite3_vfs * is used for sqlite object)
   APSWVFSType      Type object for above
   APSWVFSFile      Python object for vfs file
   APSWVFSFileType  Type object for above
   APSWSQLite3File  sqlite object for vfs file ("subclass" of sqlite3_file)
*/

/* what error code do we do for not implemented? */
#define VFSNOTIMPLEMENTED(x, v)		  \
  if(!self->basevfs || self->basevfs->iVersion<v || !self->basevfs->x) \
  { return PyErr_Format(ExcVFSNotImplemented, "VFSNotImplementedError: Method " #x " is not implemented"); }

#define VFSFILENOTIMPLEMENTED(x,v)	      \
  if(!self->base || self->base->pMethods->iVersion<v ||!self->base->pMethods->x) \
  { return PyErr_Format(ExcVFSNotImplemented, "VFSNotImplementedError: File method " #x " is not implemented"); }

/* various checks */
#define CHECKVFS \
   assert(vfs->pAppData);

#define CHECKVFSPY   \
   assert(self->containingvfs->pAppData==self)

#define CHECKVFSFILE \
   assert(apswfile->file);

#define CHECKVFSFILEPY \
  if(!self->base) { return PyErr_Format(ExcVFSFileClosed, "VFSFileClosed: Attempting operation on closed file"); }

#define VFSPREAMBLE                         \
  PyObject *etype, *eval, *etb;             \
  PyGILState_STATE gilstate;                \
  gilstate=PyGILState_Ensure();             \
  PyErr_Fetch(&etype, &eval, &etb);         \
  CHECKVFS;

#define VFSPOSTAMBLE                        \
  if(PyErr_Occurred())                      \
    apsw_write_unraiseable((PyObject*)(vfs->pAppData)); \
  PyErr_Restore(etype, eval, etb);          \
  PyGILState_Release(gilstate);

#define FILEPREAMBLE                        \
  APSWSQLite3File *apswfile=(APSWSQLite3File*)(void*)file; \
  PyObject *etype, *eval, *etb;             \
  PyGILState_STATE gilstate;                \
  gilstate=PyGILState_Ensure();             \
  PyErr_Fetch(&etype, &eval, &etb);         \
  CHECKVFSFILE;

#define FILEPOSTAMBLE                       \
  if(PyErr_Occurred())                      \
    apsw_write_unraiseable(apswfile->file); \
  PyErr_Restore(etype, eval, etb);          \
  PyGILState_Release(gilstate);

typedef struct
{
  PyObject_HEAD
  sqlite3_vfs *basevfs;         /* who we inherit from (might be null) */
  sqlite3_vfs *containingvfs;   /* pointer given to sqlite for this instance */
  int registered;               /* are we currently registered? */
} APSWVFS;

static PyTypeObject APSWVFSType;

typedef struct /* inherits */
{
  const struct sqlite3_io_methods *pMethods;  /* structure sqlite needs */
  PyObject *file;
} APSWSQLite3File;

/* this is only used if there is inheritance */
typedef struct
{
  PyObject_HEAD
  struct sqlite3_file *base;
  char *filename;  /* obtained from fullpathname - has to be around for lifetime of base */
  int filenamefree;  /* filename should be freed on close */
  /* If you add any new members then also initialize them in
     apswvfspy_xOpen() as that function does not call init because it
     has values already */
} APSWVFSFile;

static PyTypeObject APSWVFSFileType;
static PyTypeObject APSWURIFilenameType;

static const struct sqlite3_io_methods apsw_io_methods_v1;
static const struct sqlite3_io_methods apsw_io_methods_v2;

typedef struct
{
  PyObject_HEAD
  char *filename;
} APSWURIFilename;


/** .. class:: VFS

    Provides operating system access.  You can get an overview in the
    `SQLite documentation <https://sqlite.org/c3ref/vfs.html>`_.  To
    create a VFS your Python class must inherit from :class:`VFS`.

*/


/** .. method:: excepthook(etype, evalue, etraceback)

    Called when there has been an exception in a :class:`VFS` routine.
    The default implementation calls ``sys.excepthook`` and if that
    fails then ``PyErr_Display``.  The three arguments correspond to
    what ``sys.exc_info()`` would return.

    :param etype: The exception type
    :param evalue: The exception  value
    :param etraceback: The exception traceback.  Note this
      includes all frames all the way up to the thread being started.
*/

/* This function only needs to call sys.excepthook.  If things mess up
   then whoever called us will fallback on PyErr_Display etc */
static PyObject*
apswvfs_excepthook(APSW_ARGUNUSED PyObject *donotuseself, PyObject *args)
{
  /* NOTE: do not use the self argument as this function is used for
     both apswvfs and apswvfsfile.  If you need to use self then make
     two versions of the function. */
  PyObject *excepthook;

  excepthook=PySys_GetObject("excepthook"); /* NB borrowed reference */
  if(!excepthook) return NULL;

  return PyEval_CallObject(excepthook, args);
}

static int
apswvfs_xDelete(sqlite3_vfs *vfs, const char *zName, int syncDir)
{
  PyObject *pyresult=NULL;
  int result=SQLITE_OK;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xDelete", 1, "(Ni)", convertutf8string(zName), syncDir);
  if(!pyresult)
    {
      result=MakeSqliteMsgFromPyException(NULL);
      if(result==SQLITE_IOERR_DELETE_NOENT)
        PyErr_Clear();
      else
        AddTraceBackHere(__FILE__, __LINE__, "vfs.xDelete", "{s: s, s: i}", "zName", zName, "syncDir", syncDir);
    }

  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xDelete(filename, syncdir)

    Delete the named file.

    .. note::

       SQLite has 3 different behaviours depending on version for how to handle missing files.


       +----------------------------------------+-------------------------------------------------+
       | SQLite < 3.7.8                         |Raise an :exc:`IOError` if the file does not     |
       |                                        |exist.                                           |
       +----------------------------------------+-------------------------------------------------+
       | SQLite >= 3.7.8 and SQLite < 3.7.15    |Do not raise an exception                        |
       +----------------------------------------+-------------------------------------------------+
       | SQLite >= 3.7.15                       |Raise an :exc:`IOError` exception with           |
       |                                        |extendedresult :const:`SQLITE_IOERR_DELETE_NOENT`|
       +----------------------------------------+-------------------------------------------------+

    :param filename: File to delete

    :param syncdir: If True then the directory should be synced
      ensuring that the file deletion has been recorded on the disk
      platters.  ie if there was an immediate power failure after this
      call returns, on a reboot the file would still be deleted.
*/
static PyObject *
apswvfspy_xDelete(APSWVFS *self, PyObject *args)
{
  char *zName=NULL;
  int syncDir, res;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xDelete, 1);

  if(!PyArg_ParseTuple(args, "esi", STRENCODING, &zName, &syncDir))
    return NULL;

  res=self->basevfs->xDelete(self->basevfs, zName, syncDir);
  PyMem_Free(zName);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfs_xAccess(sqlite3_vfs *vfs, const char *zName, int flags, int *pResOut)
{
  PyObject *pyresult=NULL;
  int result=SQLITE_OK;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xAccess", 1, "(Ni)", convertutf8string(zName), flags);
  if(!pyresult)
    goto finally;

  if(PyIntLong_Check(pyresult))
    *pResOut=!!PyIntLong_AsLong(pyresult);
  else
    PyErr_Format(PyExc_TypeError, "xAccess should return a number");

 finally:
  if(PyErr_Occurred())
    {
      *pResOut=0;
      result=MakeSqliteMsgFromPyException(NULL);
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xAccess", "{s: s, s: i}", "zName", zName, "flags", flags);
    }

  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xAccess(pathname, flags) -> bool

    SQLite wants to check access permissions.  Return True or False
    accordingly.

    :param pathname: File or directory to check
    :param flags: One of the `access flags <https://sqlite.org/c3ref/c_access_exists.html>`_
*/
static PyObject *
apswvfspy_xAccess(APSWVFS *self, PyObject *args)
{
  char *zName=NULL;
  int res, flags, resout=0;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xAccess, 1);

  if(!PyArg_ParseTuple(args, "esi", STRENCODING, &zName, &flags))
    return NULL;

  res=self->basevfs->xAccess(self->basevfs, zName, flags, &resout);
  PyMem_Free(zName);

  if(res==SQLITE_OK)
    {
      if(resout)
        Py_RETURN_TRUE;
      Py_RETURN_FALSE;
    }

  SET_EXC(res, NULL);
  return NULL;
}


static int
apswvfs_xFullPathname(sqlite3_vfs *vfs, const char *zName, int nOut, char *zOut)
{
  PyObject *pyresult=NULL, *utf8=NULL;
  int result=SQLITE_OK;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xFullPathname", 1, "(N)", convertutf8string(zName));
  if(!pyresult)
    {
      result=MakeSqliteMsgFromPyException(NULL);
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xFullPathname", "{s: s, s: i}", "zName", zName, "nOut", nOut);
    }
  else
    {
      utf8=getutf8string(pyresult);
      if(!utf8)
        {
          result=SQLITE_ERROR;
          AddTraceBackHere(__FILE__, __LINE__, "vfs.xFullPathname", "{s: s, s: O}", "zName", zName, "result_from_python", pyresult);
          goto finally;
        }
      /* nOut includes null terminator space (ie is mxPathname+1) */
      if(PyBytes_GET_SIZE(utf8)+1>nOut)
        {
          result=SQLITE_TOOBIG;
          SET_EXC(result, NULL);
          AddTraceBackHere(__FILE__, __LINE__, "vfs.xFullPathname", "{s: s, s: O, s: i}", "zName", zName, "result_from_python", utf8, "nOut", nOut);
          goto finally;
        }
      memcpy(zOut, PyBytes_AS_STRING(utf8), PyBytes_GET_SIZE(utf8)+1); /* Python always null terminates hence +1 */
    }

 finally:
  Py_XDECREF(utf8);
  Py_XDECREF(pyresult);

  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xFullPathname(name) -> string

  Return the absolute pathname for name.  You can use ``os.path.abspath`` to do this.
*/
static PyObject *
apswvfspy_xFullPathname(APSWVFS *self, PyObject *name)
{
  char *resbuf=NULL;
  PyObject *result=NULL, *utf8=NULL;
  int res=SQLITE_NOMEM;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xFullPathname, 1);

  utf8=getutf8string(name);
  if(!utf8)
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xFullPathname", "{s: O}", "name", name);
      goto finally;
    }

  resbuf=PyMem_Malloc(self->basevfs->mxPathname+1);
  memset(resbuf, 0, self->basevfs->mxPathname+1); /* make sure it is null terminated */
  if(resbuf)
    res=self->basevfs->xFullPathname(self->basevfs, PyBytes_AsString(utf8), self->basevfs->mxPathname+1, resbuf);

  if(res==SQLITE_OK)
    APSW_FAULT_INJECT(xFullPathnameConversion,result=convertutf8string(resbuf),result=PyErr_NoMemory());

  if(!result)
    res=SQLITE_CANTOPEN;

  if(res!=SQLITE_OK)
    {
      SET_EXC(res, NULL);
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xFullPathname", "{s: O, s: i, s: O}", "name", name, "res", res, "result", result?result:Py_None);
    }

 finally:
  Py_XDECREF(utf8);
  if(resbuf) PyMem_Free(resbuf);

  return result;
}

static int
apswvfs_xOpen(sqlite3_vfs *vfs, const char *zName, sqlite3_file *file, int inflags, int *pOutFlags)
{
  int result=SQLITE_CANTOPEN;
  PyObject *flags=NULL;
  PyObject *pyresult=NULL;
  APSWSQLite3File *apswfile=(APSWSQLite3File*)(void*)file;
  /* how we pass the name */
  PyObject *nameobject;

  VFSPREAMBLE;

  flags=PyList_New(2);
  if(!flags) goto finally;

  PyList_SET_ITEM(flags, 0, PyInt_FromLong(inflags));
  PyList_SET_ITEM(flags, 1, PyInt_FromLong(pOutFlags?*pOutFlags:0));
  if(PyErr_Occurred()) goto finally;

  if(inflags & (SQLITE_OPEN_URI|SQLITE_OPEN_MAIN_DB))
    {
      nameobject=PyObject_New(PyObject, &APSWURIFilenameType);
      if(nameobject)
	((APSWURIFilename*)nameobject)->filename=(char*)zName;
    }
  else
    nameobject=convertutf8string(zName);

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xOpen", 1, "(NO)", nameobject, flags);
  if(!pyresult)
    {
      result=MakeSqliteMsgFromPyException(NULL);
      goto finally;
    }

  if(!PyList_Check(flags) || PyList_GET_SIZE(flags)!=2 || !PyIntLong_Check(PyList_GET_ITEM(flags, 1)))
    {
      PyErr_Format(PyExc_TypeError, "Flags should be two item list with item zero being integer input and item one being integer output");
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xOpen", "{s: s, s: i, s: i}", "zName", zName, "inflags", inflags, "flags", flags);
      goto finally;
    }

  if(pOutFlags)
    *pOutFlags=(int)PyIntLong_AsLong(PyList_GET_ITEM(flags, 1));
  if(PyErr_Occurred()) goto finally;

  /* If we are inheriting from another file object, and that file
     object supports version 2 io_methods (Shm* family of functions)
     then we need to allocate an io_methods dupe of our own and fill
     in their shm methods. */
  if(Py_TYPE(pyresult)==&APSWVFSFileType)
    {
      APSWVFSFile *f=(APSWVFSFile*)pyresult;
      if(!f->base || !f->base->pMethods  || !f->base->pMethods==1 || !f->base->pMethods->xShmMap)
	goto version1;
      apswfile->pMethods=&apsw_io_methods_v2;
    }
  else
    {
    version1:
      apswfile->pMethods=&apsw_io_methods_v1;
    }

  apswfile->file=pyresult;
  pyresult=NULL;
  result=SQLITE_OK;

 finally:
  assert(PyErr_Occurred()?result!=SQLITE_OK:1);
  Py_XDECREF(pyresult);
  Py_XDECREF(flags);

  VFSPOSTAMBLE;

  return result;
}

/** .. method:: xOpen(name, flags) -> VFSFile or similar object

    This method should return a new file object based on name.  You
    can return a :class:`VFSFile` from a completely different VFS.

    :param name: File to open.  Note that *name* may be :const:`None` in which
        case you should open a temporary file with a name of your
        choosing.  May be an instance of :class:`URIFilename`.

    :param flags: A list of two integers ``[inputflags,
      outputflags]``.  Each integer is one or more of the `open flags
      <https://sqlite.org/c3ref/c_open_autoproxy.html>`_ binary orred
      together.  The ``inputflags`` tells you what SQLite wants.  For
      example :const:`SQLITE_OPEN_DELETEONCLOSE` means the file should
      be automatically deleted when closed.  The ``outputflags``
      describes how you actually did open the file.  For example if you
      opened it read only then :const:`SQLITE_OPEN_READONLY` should be
      set.


*/
static PyObject *
apswvfspy_xOpen(APSWVFS *self, PyObject *args)
{
  sqlite3_file *file=NULL;
  int flagsout=0;
  int flagsin=0;
  int res;
  PyObject *result=NULL, *flags;
  PyObject *pyname=NULL, *utf8name=NULL;
  APSWVFSFile *apswfile=NULL;
  char *filename=NULL;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xOpen, 1);

  if(!PyArg_ParseTuple(args, "OO", &pyname, &flags))
    return NULL;

  if(pyname==Py_None)
    {
      filename=NULL;
    }
  else if(pyname->ob_type==&APSWURIFilenameType)
    {
      filename=((APSWURIFilename*)pyname)->filename;
    }
  else
    {
      size_t len;
      utf8name=getutf8string(pyname);
      if(!utf8name)
	goto finally;
      len=strlen(PyBytes_AS_STRING(utf8name));
      APSW_FAULT_INJECT(vfspyopen_fullpathnamemallocfailed,
			filename=PyMem_Malloc(len+3),
			filename=(char*)PyErr_NoMemory());
      if(!filename)
	goto finally;
      strcpy(filename, PyBytes_AS_STRING(utf8name));
      /* ensure extra null padding for URI params */
      filename[len]=filename[len+1]=filename[len+2]=0;
    }


  if(!PyList_Check(flags) || PyList_GET_SIZE(flags)!=2 || !PyIntLong_Check(PyList_GET_ITEM(flags, 0)) || !PyIntLong_Check(PyList_GET_ITEM(flags, 1)))
    {
      PyErr_Format(PyExc_TypeError, "Flags argument needs to be a list of two integers");
      goto finally;
    }

  flagsout=PyIntLong_AsLong(PyList_GET_ITEM(flags, 1));
  flagsin=PyIntLong_AsLong(PyList_GET_ITEM(flags, 0));
  /* check for overflow */
  if(flagsout!=PyIntLong_AsLong(PyList_GET_ITEM(flags, 1)) || flagsin!=PyIntLong_AsLong(PyList_GET_ITEM(flags, 0)))
    PyErr_Format(PyExc_OverflowError, "Flags arguments need to fit in 32 bits");
  if(PyErr_Occurred()) goto finally;

  file=PyMem_Malloc(self->basevfs->szOsFile);
  if(!file) goto finally;

  res=self->basevfs->xOpen(self->basevfs, filename, file, flagsin, &flagsout);
  if(PyErr_Occurred()) goto finally;
  if(res!=SQLITE_OK)
    {
      SET_EXC(res, NULL);
      goto finally;
    }

  PyList_SetItem(flags, 1, PyInt_FromLong(flagsout));
  if(PyErr_Occurred()) goto finally;

  apswfile=PyObject_New(APSWVFSFile, &APSWVFSFileType);
  if(!apswfile) goto finally;
  apswfile->base=file;
  apswfile->filename=filename;
  apswfile->filenamefree=!!utf8name;
  filename=NULL;
  file=NULL;
  result=(PyObject*)(void*)apswfile;

 finally:
  if(file) PyMem_Free(file);
  if(utf8name && filename) PyMem_Free(filename);
  Py_XDECREF(utf8name);
  return result;
}

static void*
apswvfs_xDlOpen(sqlite3_vfs *vfs, const char *zName)
{
  PyObject *pyresult=NULL;
  void *result=NULL;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xDlOpen", 1, "(N)", convertutf8string(zName));
  if(pyresult)
    {
      if(PyIntLong_Check(pyresult))
        result=PyLong_AsVoidPtr(pyresult);
      else
        PyErr_Format(PyExc_TypeError, "Pointer returned must be int/long");
    }
  if(PyErr_Occurred())
    {
      result=NULL;
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xDlOpen", "{s: s, s: O}", "zName", zName, "result", pyresult?pyresult:Py_None);
    }

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xDlOpen(filename) -> number

   Load the shared library. You should return a number which will be
   treated as a void pointer at the C level. On error you should
   return 0 (NULL). The number is passed as is to
   :meth:`~VFS.xDlSym`/:meth:`~VFS.xDlClose` so it can represent
   anything that is convenient for you (eg an index into an
   array). You can use ctypes to load a library::

     def xDlOpen(name):
        return ctypes.cdll.LoadLibrary(name)._handle

*/
static PyObject *
apswvfspy_xDlOpen(APSWVFS *self, PyObject *args)
{
  char *zName=NULL;
  void *res;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xDlOpen, 1);

  if(!PyArg_ParseTuple(args, "es", STRENCODING, &zName))
    return NULL;

  res=self->basevfs->xDlOpen(self->basevfs, zName);
  PyMem_Free(zName);

  return PyLong_FromVoidPtr(res);
}

static void
(*apswvfs_xDlSym(sqlite3_vfs *vfs, void *handle, const char *zName))(void)
{
  PyObject *pyresult=NULL;
  void *result=NULL;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xDlSym", 1, "(NN)", PyLong_FromVoidPtr(handle), convertutf8string(zName));
  if(pyresult)
    {
      if(PyIntLong_Check(pyresult))
        result=PyLong_AsVoidPtr(pyresult);
      else
        PyErr_Format(PyExc_TypeError, "Pointer returned must be int/long");
    }
  if(PyErr_Occurred())
    {
      result=NULL;
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xDlSym", "{s: s, s: O}", "zName", zName, "result", pyresult?pyresult:Py_None);
    }

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xDlSym(handle, symbol) -> address

    Returns the address of the named symbol which will be called by
    SQLite. On error you should return 0 (NULL). You can use ctypes::

      def xDlSym(ptr, name):
         return _ctypes.dlsym (ptr, name)  # Linux/Unix/Mac etc (note leading underscore)
         return ctypes.win32.kernel32.GetProcAddress (ptr, name)  # Windows

    :param handle: The value returned from an earlier :meth:`~VFS.xDlOpen` call
    :param symbol: A string
    :rtype: An int/long with the symbol address
*/
static PyObject *
apswvfspy_xDlSym(APSWVFS *self, PyObject *args)
{
  char *zName=NULL;
  void *res=NULL;
  PyObject *pyptr;
  void *ptr=NULL;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xDlSym, 1);

  if(!PyArg_ParseTuple(args, "Oes", &pyptr, STRENCODING, &zName))
    return NULL;

  if(PyIntLong_Check(pyptr))
    ptr=PyLong_AsVoidPtr(pyptr);
  else
    PyErr_Format(PyExc_TypeError, "Pointer must be int/long");

  if(PyErr_Occurred())
    goto finally;

  res=self->basevfs->xDlSym(self->basevfs, ptr, zName);

 finally:
  PyMem_Free(zName);

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xDlSym", "{s: O}", "args", args);
      return NULL;
    }

  return PyLong_FromVoidPtr(res);
}

static void
apswvfs_xDlClose(sqlite3_vfs *vfs, void *handle)
{
  PyObject *pyresult=NULL;
  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xDlClose", 1, "(N)", PyLong_FromVoidPtr(handle));

  if(PyErr_Occurred())
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xDlClose", "{s: N}", "ptr", PyLong_FromVoidPtr(handle));

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
}

/** .. method:: xDlClose(handle)

    Close and unload the library corresponding to the handle you
    returned from :meth:`~VFS.xDlOpen`.  You can use ctypes to do
    this::

      def xDlClose(handle):
         # Note leading underscore in _ctypes
         _ctypes.dlclose(handle)       # Linux/Mac/Unix
         _ctypes.FreeLibrary(handle)   # Windows
*/
static PyObject *
apswvfspy_xDlClose(APSWVFS *self, PyObject *pyptr)
{
  void *ptr=NULL;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xDlClose, 1);

  if(PyIntLong_Check(pyptr))
    ptr=PyLong_AsVoidPtr(pyptr);
  else
    PyErr_Format(PyExc_TypeError, "Argument is not number (pointer)");

  if(PyErr_Occurred())
    goto finally;

  self->basevfs->xDlClose(self->basevfs, ptr);

 finally:

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xDlClose", "{s: O}", "ptr", pyptr);
      return NULL;
    }

  Py_RETURN_NONE;
}

static void
apswvfs_xDlError(sqlite3_vfs *vfs, int nByte, char *zErrMsg)
{
  PyObject *pyresult=NULL, *utf8=NULL;
  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xDlError", 0, "()");

  if(pyresult && pyresult!=Py_None)
    {
      utf8=getutf8string(pyresult);
      if(utf8)
        {
          /* Get size includes trailing null */
          size_t len=PyBytes_GET_SIZE(utf8);
          if(len>(size_t)nByte) len=(size_t)nByte;
          memcpy(zErrMsg, PyBytes_AS_STRING(utf8), len);
        }

    }

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfs.xDlError", NULL);

  Py_XDECREF(pyresult);
  Py_XDECREF(utf8);
  VFSPOSTAMBLE;
}

/** .. method:: xDlError() -> string

    Return an error string describing the last error of
    :meth:`~VFS.xDlOpen` or :meth:`~VFS.xDlSym` (ie they returned
    zero/NULL). If you do not supply this routine then SQLite provides
    a generic message. To implement this method, catch exceptions in
    :meth:`~VFS.xDlOpen` or :meth:`~VFS.xDlSym`, turn them into
    strings, save them, and return them in this routine.  If you have
    an error in this routine or return None then SQLite's generic
    message will be used.
*/
static PyObject *
apswvfspy_xDlError(APSWVFS *self)
{
  PyObject *res=NULL;
  PyObject *unicode=NULL;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xDlError, 1);

  APSW_FAULT_INJECT(xDlErrorAllocFail,
                    res=PyBytes_FromStringAndSize(NULL, 512+self->basevfs->mxPathname),
                    res=PyErr_NoMemory());
  if(res)
    {
      memset(PyBytes_AS_STRING(res), 0, PyBytes_GET_SIZE(res));
      self->basevfs->xDlError(self->basevfs, PyBytes_GET_SIZE(res), PyBytes_AS_STRING(res));
    }

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xDlError", NULL);
      Py_XDECREF(res);
      return NULL;
    }

  /* did they make a message? */
  if(strlen(PyBytes_AS_STRING(res))==0)
    {
      Py_DECREF(res);
      Py_RETURN_NONE;
    }

  /* turn into unicode */
  APSW_FAULT_INJECT(xDlErrorUnicodeFail,
                    unicode=convertutf8string(PyBytes_AS_STRING(res)),
                    unicode=PyErr_NoMemory());
  if(unicode)
    {
      Py_DECREF(res);
      return unicode;
    }

  AddTraceBackHere(__FILE__, __LINE__, "vfspy.xDlError", "{s: O, s: N}", "self", self, "res", PyBytes_FromStringAndSize(PyBytes_AS_STRING(res), strlen(PyBytes_AS_STRING(res))));
  Py_DECREF(res);
  return NULL;
}

static int
apswvfs_xRandomness(sqlite3_vfs *vfs, int nByte, char *zOut)
{
  PyObject *pyresult=NULL;
  int result=0;
  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xRandomness", 1, "(i)", nByte);

  if(pyresult && PyUnicode_Check(pyresult))
    PyErr_Format(PyExc_TypeError, "Randomness object must be data/bytes not unicode");
  else if(pyresult && pyresult!=Py_None)
    {
      const void *buffer;
      Py_ssize_t buflen;
      int asrb=PyObject_AsReadBuffer(pyresult, &buffer, &buflen);
      if(asrb==0)
        {
          if(buflen>nByte)
            buflen=nByte;
          memcpy(zOut, buffer, buflen);
          result=buflen;
        }
      else
        assert(PyErr_Occurred());
    }

  if(PyErr_Occurred())
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xRandomness", "{s: i, s: O}", "nByte", nByte, "result", pyresult?pyresult:Py_None);

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xRandomness(numbytes) -> bytes

  This method is called once when SQLite needs to seed the random
  number generator. It is called on the default VFS only. It is not
  called again, even across :meth:`apsw.shutdown` calls.  You can
  return less than the number of bytes requested including None. If
  you return more then the surplus is ignored.

  :rtype: (Python 2) string, buffer (Python 3) bytes, buffer
*/
static PyObject *
apswvfspy_xRandomness(APSWVFS *self, PyObject *args)
{
  PyObject *res=NULL;
  int nbyte=0;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xRandomness, 1);

  if(!PyArg_ParseTuple(args, "i", &nbyte))
    return NULL;

  if(nbyte<0)
    return PyErr_Format(PyExc_ValueError, "You can't have negative amounts of randomness!");

  APSW_FAULT_INJECT(xRandomnessAllocFail,
                    res=PyBytes_FromStringAndSize(NULL, nbyte),
                    res=PyErr_NoMemory());
  if(res)
    {
      int amt=self->basevfs->xRandomness(self->basevfs, PyBytes_GET_SIZE(res), PyBytes_AS_STRING(res));
      if(amt<nbyte)
        _PyBytes_Resize(&res, amt);
    }

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xRandomness", "{s: i}", "nbyte", nbyte);
      Py_XDECREF(res);
      return NULL;
    }

  return res;
}

/* return the number of microseconds that the underlying OS was requested to sleep for. */
static int
apswvfs_xSleep(sqlite3_vfs *vfs, int microseconds)
{
  PyObject *pyresult=NULL;
  int result=0;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xSleep", 1, "(i)", microseconds);

  if(pyresult)
    {
      if(PyIntLong_Check(pyresult))
        {
          long actual=PyIntLong_AsLong(pyresult);
          if(actual!=(int)actual)
            PyErr_Format(PyExc_OverflowError, "Result is too big for integer");
          result=actual;
        }
      else
        PyErr_Format(PyExc_TypeError, "You should return a number from sleep");
    }

  if(PyErr_Occurred())
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xSleep", "{s: i, s: O}", "microseconds", microseconds, "result", pyresult?pyresult:Py_None);

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xSleep(microseconds) -> integer

    Pause exection of the thread for at least the specified number of
    microseconds (millionths of a second).  This routine is typically called from the busy handler.

    :returns: How many microseconds you actually requested the
      operating system to sleep for. For example if your operating
      system sleep call only takes seconds then you would have to have
      rounded the microseconds number up to the nearest second and
      should return that rounded up value.
*/
static PyObject *
apswvfspy_xSleep(APSWVFS *self, PyObject *args)
{
  int microseconds=0;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xSleep, 1);

  if(!PyArg_ParseTuple(args, "i", &microseconds))
    return NULL;

  return PyLong_FromLong(self->basevfs->xSleep(self->basevfs, microseconds));
}

static int
apswvfs_xCurrentTime(sqlite3_vfs *vfs, double *julian)
{
  PyObject *pyresult=NULL;
  int result=0;
  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xCurrentTime", 1, "()");

  if(pyresult)
    *julian=PyFloat_AsDouble(pyresult);

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfs.xCurrentTime", "{s: O}", "result", pyresult?pyresult:Py_None);
      result=1;
    }

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return result;
}

/** .. method:: xCurrentTime()  -> float

  Return the `Julian Day Number
  <http://en.wikipedia.org/wiki/Julian_day>`_ as a floating point
  number where the integer portion is the day and the fractional part
  is the time. Do not adjust for timezone (ie use `UTC
  <http://en.wikipedia.org/wiki/Universal_Time>`_).
*/
static PyObject *
apswvfspy_xCurrentTime(APSWVFS *self)
{
  int res;
  double julian=0;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xCurrentTime, 1);

  res=self->basevfs->xCurrentTime(self->basevfs, &julian);

  APSW_FAULT_INJECT(xCurrentTimeFail, ,res=1);

  if(res!=0)
    {
      SET_EXC(SQLITE_ERROR, NULL);   /* general sqlite error code */
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xCurrentTime", NULL);
      return NULL;
    }

  return PyFloat_FromDouble(julian);
}

static int
apswvfs_xGetLastError(sqlite3_vfs *vfs, int nByte, char *zErrMsg)
{
  PyObject *pyresult=NULL, *utf8=NULL;
  int buffertoosmall=0;

  VFSPREAMBLE;

  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xGetLastError", 0, "()");

  if(pyresult && pyresult!=Py_None)
    {
      utf8=getutf8string(pyresult);
      if(utf8)
        {
          /* Get size includes trailing null */
          size_t len=PyBytes_GET_SIZE(utf8);
          if(len>(size_t)nByte)
            {
              len=(size_t)nByte;
              buffertoosmall=1;
            }
          memcpy(zErrMsg, PyBytes_AS_STRING(utf8), len);
        }

    }

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfs.xGetLastError", NULL);

  Py_XDECREF(pyresult);
  Py_XDECREF(utf8);
  VFSPOSTAMBLE;
  return buffertoosmall;
}

/** .. method:: xGetLastError() -> string

   This method is to return text describing the last error that
   happened in this thread. If not implemented SQLite's more generic
   message is used. However the method is :cvstrac:`never called
   <3337>` by SQLite.
*/
static PyObject *
apswvfspy_xGetLastError(APSWVFS *self)
{
  PyObject *res=NULL;
  int toobig=1;
  Py_ssize_t size=256; /* start small */

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xGetLastError, 1);

  res=PyBytes_FromStringAndSize(NULL, size);
  if(!res) goto error;
  while(toobig)
    {
      int resizeresult;

      memset(PyBytes_AS_STRING(res), 0, PyBytes_GET_SIZE(res));
      toobig=self->basevfs->xGetLastError(self->basevfs, PyBytes_GET_SIZE(res), PyBytes_AS_STRING(res));
      if(!toobig)
        break;
      size*=2; /* double size and try again */
      APSW_FAULT_INJECT(xGetLastErrorAllocFail,
                        resizeresult=_PyBytes_Resize(&res, size),
                        resizeresult=(PyErr_NoMemory(), -1));
      if(resizeresult!=0)
        goto error;
    }

  /* did they make a message? */
  if(strlen(PyBytes_AS_STRING(res))==0)
    {
      Py_XDECREF(res);
      Py_RETURN_NONE;
    }

  _PyBytes_Resize(&res, strlen(PyBytes_AS_STRING(res)));
  return res;

 error:
  assert(PyErr_Occurred());
  AddTraceBackHere(__FILE__, __LINE__, "vfspy.xGetLastError", "{s: O, s: i}", "self", self, "size", (int)size);
  Py_XDECREF(res);
  return NULL;
}

static int
apswvfs_xSetSystemCall(sqlite3_vfs *vfs, const char *zName, sqlite3_syscall_ptr call)
{
  int res=SQLITE_OK;
  PyObject *pyresult=NULL;

  VFSPREAMBLE;
  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xSetSystemCall", 1, "(NN)",
			      convertutf8string(zName),
			      PyLong_FromVoidPtr(call));
  if(!pyresult)
    res=MakeSqliteMsgFromPyException(NULL);

  if(res==SQLITE_NOTFOUND)
    PyErr_Clear();

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfs.xSetSystemCall", "{s: O}", "pyresult", pyresult);

  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return res;
}

/** .. method:: xSetSystemCall(name, pointer) -> bool

    Change a system call used by the VFS.  This is useful for testing
    and some other scenarios such as sandboxing.

    :param name: The string name of the system call

    :param pointer: A pointer provided as an int/long.  There is no
      reference counting or other memory tracking of the pointer.  If
      you provide one you need to ensure it is around for the lifetime
      of this and any other related VFS.

    Raise an exception to return an error.  If the system call does
    not exist then raise :exc:`NotFoundError`.

    :returns: True if the system call was set.  False if the system
      call is not known.
*/
static PyObject *
apswvfspy_xSetSystemCall(APSWVFS *self, PyObject *args)
{
  const char *name=0;
  PyObject *pyptr;
  void *ptr=NULL;
  int res=-7; /* initialization to stop compiler whining */

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xSetSystemCall, 3);

  if(!PyArg_ParseTuple(args, "zO", &name, &pyptr))
    return NULL;

  if(PyIntLong_Check(pyptr))
    ptr=PyLong_AsVoidPtr(pyptr);
  else
    PyErr_Format(PyExc_TypeError, "Pointer must be int/long");

  if(PyErr_Occurred())
    goto finally;

  res=self->basevfs->xSetSystemCall(self->basevfs, name, ptr);
  if(res!=SQLITE_OK && res!=SQLITE_NOTFOUND)
    SET_EXC(res, NULL);

 finally:
  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "vfspy.xSetSystemCall", "{s: O, s: i}", "args", args, "res", res);
      return NULL;
    }

  assert(res==SQLITE_OK || res==SQLITE_NOTFOUND);

  if(res==SQLITE_OK)
    Py_RETURN_TRUE;
  Py_RETURN_FALSE;
}

static sqlite3_syscall_ptr
apswvfs_xGetSystemCall(sqlite3_vfs *vfs, const char *zName)
{
  sqlite3_syscall_ptr ptr=NULL;
  PyObject *pyresult=NULL;

  VFSPREAMBLE;
  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xGetSystemCall", 1, "(N)",
			     convertutf8string(zName));
  if(!pyresult)
    goto finally;

  if(PyIntLong_Check(pyresult))
    ptr=PyLong_AsVoidPtr(pyresult);
  else
    PyErr_Format(PyExc_TypeError, "Pointer must be int/long");

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfs.xGetSystemCall", "{s:O}", "pyresult", pyresult);

 finally:
  Py_XDECREF(pyresult);
  VFSPOSTAMBLE;
  return ptr;
}

/** .. method:: xGetSystemCall(name) -> int

    Returns a pointer for the current method implementing the named
    system call.  Return None if the call does not exist.

*/
static PyObject*
apswvfspy_xGetSystemCall(APSWVFS *self, PyObject *args)
{
  const char *name;
  sqlite3_syscall_ptr ptr;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xGetSystemCall, 3);
  if(!PyArg_ParseTuple(args, "es", STRENCODING, &name))
    return NULL;

  ptr=self->basevfs->xGetSystemCall(self->basevfs, name);

  PyMem_Free((void*)name);
  if (ptr)
    return PyLong_FromVoidPtr(ptr);
  Py_RETURN_NONE;
}

static const char*
apswvfs_xNextSystemCall(sqlite3_vfs *vfs, const char *zName)
{
  PyObject *pyresult=NULL;
  PyObject *utf8=NULL;
  const char *res=NULL;

  VFSPREAMBLE;
  pyresult=Call_PythonMethodV((PyObject*)(vfs->pAppData), "xNextSystemCall", 1, "(N)",
			      zName?convertutf8string(zName):(Py_INCREF(Py_None),Py_None));

  if(pyresult && pyresult!=Py_None)
    {
      if(PyUnicode_CheckExact(pyresult)
#if PY_MAJOR_VERSION<3
	 || PyString_CheckExact(pyresult)
#endif
	 )
	{
	  utf8=getutf8string(pyresult);
	  if(utf8)
	    /* note this deliberately leaks memory due to SQLite semantics */
	    res=sqlite3_mprintf("%s", PyBytes_AsString(utf8));
	  else
	    { assert (PyErr_Occurred()) ; }
	}
      else
	PyErr_Format(PyExc_TypeError, "You must return a string or None");
    }

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfs.xNextSystemCall", "{s:O}", "pyresult", pyresult);

  Py_XDECREF(pyresult);
  Py_XDECREF(utf8);
  VFSPOSTAMBLE;
  return res;
}

/** .. method:: xNextSystemCall(name) -> String or None

    This method is repeatedly called to iterate over all of the system
    calls in the vfs.  When called with None you should return the
    name of the first system call.  In subsequent calls return the
    name after the one passed in.  If name is the last system call
    then return None.

    .. note::

      Because of internal SQLite implementation semantics memory will
      be leaked on each call to this function.  Consequently you
      should build up the list of call names once rather than
      repeatedly doing it.

*/
static PyObject *
apswvfspy_xNextSystemCall(APSWVFS *self, PyObject *name)
{
  const char *zName=NULL;
  PyObject *res=NULL;
  PyObject *utf8=NULL;

  CHECKVFSPY;
  VFSNOTIMPLEMENTED(xNextSystemCall, 3);

  if(name!=Py_None)
    {
      if(PyUnicode_CheckExact(name)
#if PY_MAJOR_VERSION<3
	 || PyString_CheckExact(name)
#endif
	 )
	{
	  utf8=getutf8string(name);
	}
      else
	PyErr_Format(PyExc_TypeError, "You must provide a string or None");
    }

  if(PyErr_Occurred())
    goto finally;

  zName=self->basevfs->xNextSystemCall(self->basevfs, utf8?PyBytes_AsString(utf8):NULL);
  if(zName)
    res=convertutf8string(zName);
  else
    {
      Py_INCREF(Py_None);
      res=Py_None;
    }

 finally:
  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfspy.xNextSystemCall", "{s:O}", "name", name);

  Py_XDECREF(utf8);
  return res;
}


/** .. method:: unregister()

   Unregisters the VFS making it unavailable to future database
   opens. You do not need to call this as the VFS is automatically
   unregistered by when the VFS has no more references or open
   datatabases using it. It is however useful to call if you have made
   your VFS be the default and wish to immediately make it be
   unavailable. It is safe to call this routine multiple times.

   -* sqlite3_vfs_unregister
*/
static PyObject *
apswvfspy_unregister(APSWVFS *self)
{
  int res;

  CHECKVFSPY;

  if(self->registered)
    {
      /* although it is undocumented by sqlite, we assume that an
         unregister failure always results in an unregister and so
         continue freeing the data structures.  we memset everything
         to zero so there will be a coredump should this behaviour
         change.  as of 3.6.3 the sqlite code doesn't return
         anything except ok anyway. */
      res=sqlite3_vfs_unregister(self->containingvfs);
      self->registered=0;
      APSW_FAULT_INJECT(APSWVFSDeallocFail, ,res=SQLITE_IOERR);

      SET_EXC(res, NULL);
      if(res!=SQLITE_OK)
        return NULL;
    }
  Py_RETURN_NONE;
}


static void
APSWVFS_dealloc(APSWVFS *self)
{
  if(self->basevfs && self->basevfs->xAccess==apswvfs_xAccess)
    {
      Py_DECREF((PyObject*)self->basevfs->pAppData);
    }

  if(self->containingvfs)
    {
      PyObject *xx;

      /* not allowed to clobber existing exception */
      PyObject *etype=NULL, *evalue=NULL, *etraceback=NULL;
      PyErr_Fetch(&etype, &evalue, &etraceback);

      xx=apswvfspy_unregister(self);
      Py_XDECREF(xx);

      if(PyErr_Occurred())
        apsw_write_unraiseable(NULL);
      PyErr_Restore(etype, evalue, etraceback);

      /* some cleanups */
      self->containingvfs->pAppData=NULL;
      PyMem_Free((void*)(self->containingvfs->zName));
      /* zero it out so any attempt to use results in core dump */
      memset(self->containingvfs, 0, sizeof(sqlite3_vfs));
      PyMem_Free(self->containingvfs);
      self->containingvfs=NULL;

    }

  self->basevfs=self->containingvfs=NULL;

  Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *
APSWVFS_new(PyTypeObject *type, APSW_ARGUNUSED PyObject *args, APSW_ARGUNUSED PyObject *kwds)
{
  APSWVFS *self;
  self= (APSWVFS*)type->tp_alloc(type, 0);
  if(self)
    {
      self->basevfs=NULL;
      self->containingvfs=NULL;
      self->registered=0;
    }
  return (PyObject*)self;
}

/** .. method:: __init__(name[, base=None, makedefault=False, maxpathname=1024])

    :param name: The name to register this vfs under.  If the name
        already exists then this vfs will replace the prior one of the
        same name.  Use :meth:`apsw.vfsnames` to get a list of
        registered vfs names.  :param base: If you would like to
        inherit behaviour from an already registered vfs then give
        their name.  To inherit from the default vfs, use a zero
        length string ``""`` as the name.  :param makedefault: If true
        then this vfs will be registered as the default, and will be
        used by any opens that don't specify a vfs.  :param
        maxpathname: The maximum length of database name in bytes when
        represented in UTF-8.  If a pathname is passed in longer than
        this value then SQLite will not `be able to open it
        <https://sqlite.org/src/tktview/c060923a5422590b3734eb92eae0c94934895b68>`__.

    :raises ValueError: If *base* is not :const:`None` and the named vfs is not
      currently registered.

    -* sqlite3_vfs_register sqlite3_vfs_find
*/
static int
APSWVFS_init(APSWVFS *self, PyObject *args, PyObject *kwds)
{
  static char *kwlist[]={"name", "base", "makedefault", "maxpathname", NULL};
  char *base=NULL, *name=NULL;
  int makedefault=0, maxpathname=0, res;

  if(!PyArg_ParseTupleAndKeywords(args, kwds, "es|esii:init(name, base=None, makedefault=False, maxpathname=1024)", kwlist,
                                  STRENCODING, &name, STRENCODING, &base, &makedefault, &maxpathname))
    return -1;

  if(base)
    {
      int baseversion;
      if(!strlen(base))
        {
          PyMem_Free(base);
          base=NULL;
        }
      self->basevfs=sqlite3_vfs_find(base);
      if(!self->basevfs)
        {
          PyErr_Format(PyExc_ValueError, "Base vfs named \"%s\" not found", base?base:"<default>");
          goto error;
        }
      baseversion=self->basevfs->iVersion;
      APSW_FAULT_INJECT(APSWVFSBadVersion, , baseversion=-789426);
      if(baseversion<1 || baseversion>3)
        {
          PyErr_Format(PyExc_ValueError, "Base vfs implements version %d of vfs spec, but apsw only supports versions 1, 2 and 3", baseversion);
          goto error;
        }
      if(base) PyMem_Free(base);
    }

  self->containingvfs=(sqlite3_vfs *)PyMem_Malloc(sizeof(sqlite3_vfs));
  if(!self->containingvfs) return -1;
  memset(self->containingvfs, 0, sizeof(sqlite3_vfs));
  self->containingvfs->iVersion=3;
  self->containingvfs->szOsFile=sizeof(APSWSQLite3File);
  if(self->basevfs && !maxpathname)
    self->containingvfs->mxPathname=self->basevfs->mxPathname;
  else
    self->containingvfs->mxPathname=maxpathname?maxpathname:1024;
  self->containingvfs->zName=name;
  name=NULL;
  self->containingvfs->pAppData=self;
#define METHOD(meth) \
  self->containingvfs->x##meth=apswvfs_x##meth;

  METHOD(Delete);
  METHOD(FullPathname);
  METHOD(Open);
  METHOD(Access);
  METHOD(DlOpen);
  METHOD(DlSym);
  METHOD(DlClose);
  METHOD(DlError);
  METHOD(Randomness);
  METHOD(Sleep);
  METHOD(CurrentTime);
  METHOD(GetLastError);
  /* The VFS2 method is not particularly useful */
  METHOD(SetSystemCall);
  METHOD(GetSystemCall);
  METHOD(NextSystemCall);
#undef METHOD


  APSW_FAULT_INJECT(APSWVFSRegistrationFails,
                    res=sqlite3_vfs_register(self->containingvfs, makedefault),
                    res=SQLITE_NOMEM);

  if(res==SQLITE_OK)
    {
      self->registered=1;
      if(self->basevfs && self->basevfs->xAccess==apswvfs_xAccess)
        {
          Py_INCREF((PyObject*)self->basevfs->pAppData);
        }
      return 0;
    }

  SET_EXC(res, NULL);

 error:
  if(name) PyMem_Free(name);
  if(base) PyMem_Free(base);
  if(self->containingvfs && self->containingvfs->zName) PyMem_Free((void*)(self->containingvfs->zName));
  if(self->containingvfs) PyMem_Free(self->containingvfs);
  self->containingvfs=NULL;
  return -1;
}

static PyMethodDef APSWVFS_methods[]={
  {"xDelete", (PyCFunction)apswvfspy_xDelete, METH_VARARGS, "xDelete"},
  {"xFullPathname", (PyCFunction)apswvfspy_xFullPathname, METH_O, "xFullPathname"},
  {"xOpen", (PyCFunction)apswvfspy_xOpen, METH_VARARGS, "xOpen"},
  {"xAccess", (PyCFunction)apswvfspy_xAccess, METH_VARARGS, "xAccess"},
  {"xDlOpen", (PyCFunction)apswvfspy_xDlOpen, METH_VARARGS, "xDlOpen"},
  {"xDlSym", (PyCFunction)apswvfspy_xDlSym, METH_VARARGS, "xDlSym"},
  {"xDlClose", (PyCFunction)apswvfspy_xDlClose, METH_O, "xDlClose"},
  {"xDlError", (PyCFunction)apswvfspy_xDlError, METH_NOARGS, "xDlError"},
  {"xRandomness", (PyCFunction)apswvfspy_xRandomness, METH_VARARGS, "xRandomness"},
  {"xSleep", (PyCFunction)apswvfspy_xSleep, METH_VARARGS, "xSleep"},
  {"xCurrentTime", (PyCFunction)apswvfspy_xCurrentTime, METH_NOARGS, "xCurrentTime"},
  {"xGetLastError", (PyCFunction)apswvfspy_xGetLastError, METH_NOARGS, "xGetLastError"},
  {"xSetSystemCall", (PyCFunction)apswvfspy_xSetSystemCall, METH_VARARGS, "xSetSystemCall"},
  {"xGetSystemCall", (PyCFunction)apswvfspy_xGetSystemCall, METH_VARARGS, "xGetSystemCall"},
  {"xNextSystemCall", (PyCFunction)apswvfspy_xNextSystemCall, METH_O, "xNextSystemCall"},
  {"unregister", (PyCFunction)apswvfspy_unregister, METH_NOARGS, "Unregisters the vfs"},
  {"excepthook", (PyCFunction)apswvfs_excepthook, METH_VARARGS, "Exception hook"},
  /* Sentinel */
  {0, 0, 0, 0}
  };

static PyTypeObject APSWVFSType =
  {
    APSW_PYTYPE_INIT
    "apsw.VFS",                /*tp_name*/
    sizeof(APSWVFS),           /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)APSWVFS_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_VERSION_TAG, /*tp_flags*/
    "VFS object",              /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    APSWVFS_methods,           /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)APSWVFS_init,    /* tp_init */
    0,                         /* tp_alloc */
    APSWVFS_new,               /* tp_new */
    0,                         /* tp_free */
    0,                         /* tp_is_gc */
    0,                         /* tp_bases */
    0,                         /* tp_mro */
    0,                         /* tp_cache */
    0,                         /* tp_subclasses */
    0,                         /* tp_weaklist */
    0                          /* tp_del */
    APSW_PYTYPE_VERSION
  };


/** .. class:: VFSFile

    Wraps access to a file.  You only need to derive from this class
    if you want the file object returned from :meth:`VFS.xOpen` to
    inherit from an existing VFS implementation.

    .. note::

       All file sizes and offsets are 64 bit quantities even on 32 bit
       operating systems.
*/

/** .. method:: excepthook(etype, evalue, etraceback)

    Called when there has been an exception in a :class:`VFSFile`
    routine.  The default implementation calls ``sys.excepthook`` and
    if that fails then ``PyErr_Display``.  The three arguments
    correspond to what ``sys.exc_info()`` would return.

    :param etype: The exception type
    :param evalue: The exception  value
    :param etraceback: The exception traceback.  Note this
      includes all frames all the way up to the thread being started.
*/


static PyObject *apswvfsfilepy_xClose(APSWVFSFile *self);

static void
APSWVFSFile_dealloc(APSWVFSFile *self)
{
  PyObject *a,*b,*c;

  PyErr_Fetch(&a, &b, &c);

  if(self->base)
    {
      /* close it */
      PyObject *x=apswvfsfilepy_xClose(self);
      Py_XDECREF(x);
    }
  if(self->filenamefree)
    PyMem_Free(self->filename);

  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "APSWVFS File destructor", NULL);
      apsw_write_unraiseable(NULL);
    }
  Py_TYPE(self)->tp_free((PyObject*)self);

  PyErr_Restore(a,b,c);
}

/*ARGSUSED*/
static PyObject *
APSWVFSFile_new(PyTypeObject *type, APSW_ARGUNUSED PyObject *args, APSW_ARGUNUSED PyObject *kwds)
{
  APSWVFSFile *self;
  self= (APSWVFSFile*)type->tp_alloc(type, 0);
  if(self)
    {
      self->base=NULL;
      self->filename=NULL;
    }

  return (PyObject*)self;
}

/** .. method:: __init__(vfs, name, flags)

    :param vfs: The vfs you want to inherit behaviour from.  You can
       use an empty string ``""`` to inherit from the default vfs.
    :param name: The name of the file being opened.  May be an instance of :class:`URIFilename`.
    :param flags: A two list ``[inflags, outflags]`` as detailed in :meth:`VFS.xOpen`.

    :raises ValueError: If the named VFS is not registered.

    .. note::

      If the VFS that you inherit from supports :ref:`write ahead
      logging <wal>` then your :class:`VFSFile` will also support the
      xShm methods necessary to implement wal.

    .. seealso::

      :meth:`VFS.xOpen`
*/
static int
APSWVFSFile_init(APSWVFSFile *self, PyObject *args, PyObject *kwds)
{
  static char *kwlist[]={"vfs", "name", "flags", NULL};
  char *vfs=NULL;
  PyObject *flags=NULL, *pyname=NULL, *utf8name=NULL;
  int xopenresult;
  int flagsout=0;
  long flagsin;
  int res=-1; /* error */

  PyObject *itemzero=NULL, *itemone=NULL, *zero=NULL, *pyflagsout=NULL;
  sqlite3_vfs *vfstouse=NULL;
  sqlite3_file *file=NULL;

  if(!PyArg_ParseTupleAndKeywords(args, kwds, "esOO:init(vfs, name, flags)", kwlist, STRENCODING, &vfs, &pyname, &flags))
    return -1;

  self->filenamefree=0;
  if(pyname==Py_None)
    {
      self->filename=NULL;
    }
  else if(pyname->ob_type==&APSWURIFilenameType)
    {
      self->filename=((APSWURIFilename*)pyname)->filename;
    }
  else
    {
      size_t len;
      utf8name=getutf8string(pyname);
      if(!utf8name)
	goto finally;
      len=strlen(PyBytes_AS_STRING(utf8name));
      APSW_FAULT_INJECT(vfspyopen_fullpathnamemallocfailed,
			self->filename=PyMem_Malloc(len+3),
			self->filename=(char*)PyErr_NoMemory());
      if(!self->filename)
	goto finally;
      strcpy(self->filename, PyBytes_AS_STRING(utf8name));
      /* ensure extra null padding for URI params */
      self->filename[len]=self->filename[len+1]=self->filename[len+2]=0;
      self->filenamefree=1;
    }

  /* type checking */
  if(strlen(vfs)==0)
    {
      /* sqlite uses null for default vfs - we use empty string */
      PyMem_Free(vfs);
      vfs=NULL;
    }
  /* flags need to be a list of two integers */
  if(!PySequence_Check(flags) || PySequence_Size(flags)!=2)
    {
      PyErr_Format(PyExc_TypeError, "Flags should be a sequence of two integers");
      goto finally;
    }
  itemzero=PySequence_GetItem(flags, 0);
  itemone=PySequence_GetItem(flags, 1);
  if(!itemzero || !itemone || !PyIntLong_Check(itemzero) || !PyIntLong_Check(itemone))
    {
      PyErr_Format(PyExc_TypeError, "Flags should contain two integers");
      goto finally;
    }
  /* check we can change item 1 */
  zero=PyInt_FromLong(0);
  if(!zero) goto finally;
  if(-1==PySequence_SetItem(flags, 1, zero))
    goto finally;

  flagsin=PyIntLong_AsLong(itemzero);
  if(flagsin!=(int)flagsin)
    {
      PyErr_Format(PyExc_OverflowError, "flags[0] is too big!");
      AddTraceBackHere(__FILE__, __LINE__, "VFSFile.__init__", "{s: O}", "flags", flags);
    }
  if(PyErr_Occurred())
    goto finally;

  vfstouse=sqlite3_vfs_find(vfs);
  if(!vfstouse)
    {
      PyErr_Format(PyExc_ValueError, "Unknown vfs \"%s\"", vfs);
      goto finally;
    }
  file=PyMem_Malloc(vfstouse->szOsFile);
  if(!file) goto finally;

  xopenresult=vfstouse->xOpen(vfstouse, self->filename,  file, (int)flagsin, &flagsout);
  SET_EXC(xopenresult, NULL);
  if(PyErr_Occurred())
    {
      /* just in case the result was ok, but there was a python level exception ... */
      if(xopenresult==SQLITE_OK) file->pMethods->xClose(file);
      goto finally;
    }

  pyflagsout=PyInt_FromLong(flagsout);

  if(-1==PySequence_SetItem(flags, 1, pyflagsout))
    {
      file->pMethods->xClose(file);
      goto finally;
    }

  if(PyErr_Occurred()) goto finally;

  self->base=(sqlite3_file*)(void*)file;
  res=0;

 finally:
  assert(res==0 || PyErr_Occurred());
  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "vfsfile.init", "{s: O, s: O}", "args", args, "kwargs", kwds);

  Py_XDECREF(pyflagsout);
  Py_XDECREF(itemzero);
  Py_XDECREF(itemone);
  Py_XDECREF(zero);
  Py_XDECREF(utf8name);
  if(res!=0 && file)
    PyMem_Free(file);
  if(vfs) PyMem_Free(vfs);
  return res;
}

static int
apswvfsfile_xRead(sqlite3_file *file, void *bufout, int amount, sqlite3_int64 offset)
{
  int result=SQLITE_ERROR;
  PyObject *pybuf=NULL;
  int asrb;
  Py_ssize_t size;
  const void *buffer;

  FILEPREAMBLE;

  pybuf=Call_PythonMethodV(apswfile->file, "xRead", 1, "(iL)", amount, offset);
  if(!pybuf)
    {
      assert(PyErr_Occurred());
      result=MakeSqliteMsgFromPyException(NULL);
      goto finally;
    }
  if(PyUnicode_Check(pybuf) || !PyObject_CheckReadBuffer(pybuf))
    {
      PyErr_Format(PyExc_TypeError, "Object returned from xRead should be bytes/buffer/string");
      goto finally;
    }
  asrb=PyObject_AsReadBuffer(pybuf, &buffer, &size);

  APSW_FAULT_INJECT(xReadReadBufferFail,,(PyErr_NoMemory(),asrb=-1));

  if(asrb!=0)
    {
      PyErr_Format(PyExc_TypeError, "Object returned from xRead doesn't do read buffer");
      goto finally;
    }

  if(size<amount)
    {
      result=SQLITE_IOERR_SHORT_READ;
      memset(bufout, 0, amount); /* see https://sqlite.org/cvstrac/chngview?cn=5867 */
      memcpy(bufout, buffer, size);
    }
  else
    {
      memcpy(bufout, buffer, amount);
      result=SQLITE_OK;
    }

 finally:
  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xRead", "{s: i, s: L, s: O}", "amount", amount, "offset", offset, "result", pybuf?pybuf:Py_None);

  Py_XDECREF(pybuf);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xRead(amount, offset) -> bytes

    Read the specified *amount* of data starting at *offset*. You
    should make every effort to read all the data requested, or return
    an error. If you have the file open for non-blocking I/O or if
    signals happen then it is possible for the underlying operating
    system to do a partial read. You will need to request the
    remaining data. Except for empty files SQLite considers short
    reads to be a fatal error.

    :param amount: Number of bytes to read
    :param offset: Where to start reading. This number may be 64 bit once the database is larger than 2GB.

    :rtype: (Python 2) string, buffer.  (Python 3) bytes, buffer
*/
static PyObject *
apswvfsfilepy_xRead(APSWVFSFile *self, PyObject *args)
{
  int amount;
  sqlite3_int64 offset;
  int res;
  PyObject *buffy=NULL;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xRead, 1);

  if(!PyArg_ParseTuple(args, "iL", &amount, &offset))
    {
      assert(PyErr_Occurred());
      return NULL;
    }

  buffy=PyBytes_FromStringAndSize(NULL, amount);
  if(!buffy) return NULL;

  res=self->base->pMethods->xRead(self->base, PyBytes_AS_STRING(buffy), amount, offset);

  if(res==SQLITE_OK)
    return buffy;

  if(res==SQLITE_IOERR_SHORT_READ)
    {
      /* We don't know how short the read was, so look for first
         non-trailing null byte.  See
         https://sqlite.org/cvstrac/chngview?cn=5867 */
      while(amount && PyBytes_AS_STRING(buffy)[amount-1]==0)
        amount--;
      _PyBytes_Resize(&buffy, amount);
      return buffy;
    }

  Py_DECREF(buffy);


  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xWrite(sqlite3_file *file, const void *buffer, int amount, sqlite3_int64 offset)
{
  PyObject *pyresult=NULL, *pybuf=NULL;
  int result=SQLITE_OK;
  FILEPREAMBLE;

  /* I could instead use PyBuffer_New here which avoids duplicating
     the memory.  But if the developer keeps a reference on it then
     the underlying memory goes away on return of this function and
     all hell would break lose on next access.  It is very unlikely
     someone would hang on to them but I'd rather there not be any
     possibility of problems.  In any event the data sizes are usually
     very small - typically the SQLite default page size of 1kb */
  pybuf=PyBytes_FromStringAndSize(buffer, amount);
  if(!pybuf) goto finally;

  pyresult=Call_PythonMethodV(apswfile->file, "xWrite", 1, "(OL)", pybuf, offset);

 finally:
  if(PyErr_Occurred())
    {
      result=MakeSqliteMsgFromPyException(NULL);
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xWrite", "{s: i, s: L, s: O}", "amount", amount, "offset", offset, "data", pybuf?pybuf:Py_None);
    }
  Py_XDECREF(pybuf);
  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xWrite(data, offset)

  Write the *data* starting at absolute *offset*. You must write all the data
  requested, or return an error. If you have the file open for
  non-blocking I/O or if signals happen then it is possible for the
  underlying operating system to do a partial write. You will need to
  write the remaining data.

  :param offset: Where to start writing. This number may be 64 bit once the database is larger than 2GB.
  :param data: (Python 2) string, (Python 3) bytes
*/

static PyObject *
apswvfsfilepy_xWrite(APSWVFSFile *self, PyObject *args)
{
  sqlite3_int64 offset;
  int res;
  PyObject *buffy=NULL;
  const void *buffer;
  Py_ssize_t size;
  int asrb;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xWrite, 1);

  if(!PyArg_ParseTuple(args, "OL", &buffy, &offset))
    {
      assert(PyErr_Occurred());
      return NULL;
    }

  asrb=PyObject_AsReadBuffer(buffy, &buffer, &size);
  if(asrb!=0 || PyUnicode_Check(buffy))
    {
      PyErr_Format(PyExc_TypeError, "Object passed to xWrite doesn't do read buffer");
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xWrite", "{s: L, s: O}", "offset", offset, "buffer", buffy);
      return NULL;
    }

  res=self->base->pMethods->xWrite(self->base, buffer, size, offset);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xUnlock(sqlite3_file *file, int flag)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xUnlock", 1, "(i)", flag);
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else
    result=SQLITE_OK;

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile.xUnlock", "{s: i}", "flag", flag);
  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xUnlock(level)

    Decrease the lock to the level specified which is one of the
    `SQLITE_LOCK <https://sqlite.org/c3ref/c_lock_exclusive.html>`_
    family of constants.
*/
static PyObject *
apswvfsfilepy_xUnlock(APSWVFSFile *self, PyObject *args)
{
  int flag, res;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xUnlock, 1);

  if(!PyArg_ParseTuple(args, "i", &flag))
    return NULL;

  res=self->base->pMethods->xUnlock(self->base, flag);

  APSW_FAULT_INJECT(xUnlockFails,,res=SQLITE_IOERR);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xLock(sqlite3_file *file, int flag)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xLock", 1, "(i)", flag);
  if(!pyresult)
    {
      result=MakeSqliteMsgFromPyException(NULL);
      /* a busy exception is normal so we clear it */
      if(SQLITE_BUSY==(result&0xff))
        PyErr_Clear();
    }
  else
    result=SQLITE_OK;

  Py_XDECREF(pyresult);
  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile.xLock", "{s: i}", "level", flag);

  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xLock(level)

  Increase the lock to the level specified which is one of the
  `SQLITE_LOCK <https://sqlite.org/c3ref/c_lock_exclusive.html>`_
  family of constants. If you can't increase the lock level because
  someone else has locked it, then raise :exc:`BusyError`.
*/
static PyObject *
apswvfsfilepy_xLock(APSWVFSFile *self, PyObject *args)
{
  int flag, res;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xLock, 1);

  if(!PyArg_ParseTuple(args, "i", &flag))
    return NULL;

  res=self->base->pMethods->xLock(self->base, flag);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xTruncate(sqlite3_file *file, sqlite3_int64 size)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xTruncate", 1, "(L)", size);
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else
    result=SQLITE_OK;

  Py_XDECREF(pyresult);
  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile.xTruncate", "{s: L}", "size", size);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xTruncate(newsize)

  Set the file length to *newsize* (which may be more or less than the
  current length).
*/
static PyObject *
apswvfsfilepy_xTruncate(APSWVFSFile *self, PyObject *args)
{
  int res;
  sqlite3_int64 size;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xTruncate, 1);

  if(!PyArg_ParseTuple(args, "L", &size))
    return NULL;

  res=self->base->pMethods->xTruncate(self->base, size);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xSync(sqlite3_file *file, int flags)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xSync", 1, "(i)", flags);
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else
    result=SQLITE_OK;

  Py_XDECREF(pyresult);
  if (PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile.xSync", "{s: i}", "flags", flags);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xSync(flags)

  Ensure data is on the disk platters (ie could survive a power
  failure immediately after the call returns) with the `sync flags
  <https://sqlite.org/c3ref/c_sync_dataonly.html>`_ detailing what
  needs to be synced.  You can sync more than what is requested.
*/
static PyObject *
apswvfsfilepy_xSync(APSWVFSFile *self, PyObject *args)
{
  int flags, res;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xSync, 1);

  if(!PyArg_ParseTuple(args, "i", &flags))
    return NULL;

  res=self->base->pMethods->xSync(self->base, flags);

  APSW_FAULT_INJECT(xSyncFails, ,res=SQLITE_IOERR);

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}


static int
apswvfsfile_xSectorSize(sqlite3_file *file)
{
  int result=4096;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xSectorSize", 0, "()");
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else if(pyresult!=Py_None)
    {
      if(PyIntLong_Check(pyresult))
        result=PyIntLong_AsLong(pyresult); /* returns -1 on error/overflow */
      else
        PyErr_Format(PyExc_TypeError, "xSectorSize should return a number");
    }

  /* We can't return errors so use unraiseable */
  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xSectorSize", NULL);
      result=4096; /* could be -1 as stated above */
    }

  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xSectorSize() -> int

    Return the native underlying sector size. SQLite uses the value
    returned in determining the default database page size. If you do
    not implement the function or have an error then 4096 (the SQLite
    default) is returned.
*/
static PyObject *
apswvfsfilepy_xSectorSize(APSWVFSFile *self)
{
  int res=4096;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xSectorSize, 1);

  res=self->base->pMethods->xSectorSize(self->base);

  return PyInt_FromLong(res);
}

static int
apswvfsfile_xDeviceCharacteristics(sqlite3_file *file)
{
  int result=0;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xDeviceCharacteristics", 0, "()");
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else if(pyresult!=Py_None)
    {
      if(PyIntLong_Check(pyresult))
        result=PyIntLong_AsLong(pyresult); /* sets to -1 on error */
      else
        PyErr_Format(PyExc_TypeError, "xDeviceCharacteristics should return a number");
    }

  /* We can't return errors so use unraiseable */
  if(PyErr_Occurred())
    {
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xDeviceCharacteristics", "{s: O}", "result", pyresult?pyresult:Py_None);
      result=0; /* harmless value for error cases */
    }

  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xDeviceCharacteristics() -> int

  Return `I/O capabilities
  <https://sqlite.org/c3ref/c_iocap_atomic.html>`_ (bitwise or of
  appropriate values). If you do not implement the function or have an
  error then 0 (the SQLite default) is returned.
*/
static PyObject *
apswvfsfilepy_xDeviceCharacteristics(APSWVFSFile *self)
{
  int res=0;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xDeviceCharacteristics, 1);

  res=self->base->pMethods->xDeviceCharacteristics(self->base);

  return PyInt_FromLong(res);
}


static int
apswvfsfile_xFileSize(sqlite3_file *file, sqlite3_int64 *pSize)
{
  int result=SQLITE_OK;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xFileSize", 1, "()");
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else if(PyLong_Check(pyresult))
    *pSize=PyLong_AsLongLong(pyresult);
  else if(PyIntLong_Check(pyresult))
    *pSize=PyIntLong_AsLong(pyresult);
  else
    PyErr_Format(PyExc_TypeError, "xFileSize should return a number");

  if(PyErr_Occurred())
    {
      result=MakeSqliteMsgFromPyException(NULL);
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xFileSize", "{s: O}", "result", pyresult?pyresult:Py_None);
    }

  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xFileSize() -> int

  Return the size of the file in bytes.  Remember that file sizes are
  64 bit quantities even on 32 bit operating systems.
*/
static PyObject *
apswvfsfilepy_xFileSize(APSWVFSFile *self)
{
  sqlite3_int64 size;
  int res;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xFileSize, 1);
  res=self->base->pMethods->xFileSize(self->base, &size);

  APSW_FAULT_INJECT(xFileSizeFails, ,res=SQLITE_IOERR);

  if(res!=SQLITE_OK)
    {
      SET_EXC(res, NULL);
      return NULL;
    }
  return PyLong_FromLongLong(size);
}

static int
apswvfsfile_xCheckReservedLock(sqlite3_file *file, int *pResOut)
{
  int result=SQLITE_OK;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xCheckReservedLock", 1, "()");
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else if(PyIntLong_Check(pyresult))
    *pResOut=!!PyIntLong_AsLong(pyresult);
  else
    PyErr_Format(PyExc_TypeError, "xCheckReservedLock should return a boolean/number");

  if(PyErr_Occurred())
    {
      result=MakeSqliteMsgFromPyException(NULL);
      AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile_xCheckReservedLock", "{s: O}", "result", pyresult?pyresult:Py_None);
    }

  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xCheckReservedLock()

  Returns True if any database connection (in this or another process)
  has a lock other than `SQLITE_LOCK_NONE or SQLITE_LOCK_SHARED
  <https://sqlite.org/c3ref/c_lock_exclusive.html>`_.
*/
static PyObject *
apswvfsfilepy_xCheckReservedLock(APSWVFSFile *self)
{
  int islocked;
  int res;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xCheckReservedLock, 1);

  res=self->base->pMethods->xCheckReservedLock(self->base, &islocked);

  APSW_FAULT_INJECT(xCheckReservedLockFails,, res=SQLITE_IOERR);

  if(res!=SQLITE_OK)
    {
      SET_EXC(res, NULL);
      return NULL;
    }

  APSW_FAULT_INJECT(xCheckReservedLockIsTrue,,islocked=1);

  if(islocked)
    Py_RETURN_TRUE;
  Py_RETURN_FALSE;
}

static int
apswvfsfile_xFileControl(sqlite3_file *file, int op, void *pArg)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xFileControl", 1, "(iN)", op, PyLong_FromVoidPtr(pArg));
  if(!pyresult)
      result=MakeSqliteMsgFromPyException(NULL);
  else
    {
      if(pyresult!=Py_True && pyresult!=Py_False)
	{
	  PyErr_Format(PyExc_TypeError, "xFileControl must return True or False");
	  result=SQLITE_ERROR;
	}
      else
	result=(pyresult==Py_True)?SQLITE_OK:SQLITE_NOTFOUND;
    }

  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xFileControl(op, ptr) -> bool

   Receives `file control
   <https://sqlite.org/c3ref/file_control.html>`_ request typically
   issued by :meth:`Connection.filecontrol`.  See
   :meth:`Connection.filecontrol` for an example of how to pass a
   Python object to this routine.

   :param op: A numeric code.  Codes below 100 are reserved for SQLite
     internal use.
   :param ptr: An integer corresponding to a pointer at the C level.

   :returns: A boolean indicating if the op was understood

   As of SQLite 3.6.10, this method is called by SQLite if you have
   inherited from an underlying VFSFile.  Consequently ensure you pass
   any unrecognised codes through to your super class.  For example::

            def xFileControl(self, op, ptr):
                if op==1027:
                    process_quick(ptr)
                elif op==1028:
                    obj=ctypes.py_object.from_address(ptr).value
                else:
                    # this ensures superclass implementation is called
                    return super(MyFile, self).xFileControl(op, ptr)
		# we understood the op
	        return True
*/
static PyObject *
apswvfsfilepy_xFileControl(APSWVFSFile *self, PyObject *args)
{
  int op, res=SQLITE_ERROR;
  PyObject *pyptr;
  void *ptr=NULL;

  CHECKVFSFILEPY;
  VFSFILENOTIMPLEMENTED(xFileControl, 1);

  if(!PyArg_ParseTuple(args, "iO", &op, &pyptr))
    return NULL;

  if(PyIntLong_Check(pyptr))
    ptr=PyLong_AsVoidPtr(pyptr);
  else
    PyErr_Format(PyExc_TypeError, "Argument is not number (pointer)");

  if(PyErr_Occurred())
    goto finally;

  res=self->base->pMethods->xFileControl(self->base, op, ptr);

  if(res==SQLITE_OK)
    Py_RETURN_TRUE;
  if(res==SQLITE_NOTFOUND)
    Py_RETURN_FALSE;
 finally:
  SET_EXC(res, NULL);
  return NULL;
}

static int
apswvfsfile_xClose(sqlite3_file *file)
{
  int result=SQLITE_ERROR;
  PyObject *pyresult=NULL;
  FILEPREAMBLE;

  pyresult=Call_PythonMethodV(apswfile->file, "xClose", 1, "()");
  if(!pyresult)
    result=MakeSqliteMsgFromPyException(NULL);
  else
    result=SQLITE_OK;

  if(PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "apswvfsfile.xClose", NULL);

  Py_XDECREF(apswfile->file);
  apswfile->file=NULL;
  Py_XDECREF(pyresult);
  FILEPOSTAMBLE;
  return result;
}

/** .. method:: xClose()

  Close the database. Note that even if you return an error you should
  still close the file.  It is safe to call this method mutliple
  times.
*/
static PyObject *
apswvfsfilepy_xClose(APSWVFSFile *self)
{
  int res;

  if(!self->base) /* already closed */
    Py_RETURN_NONE;

  res=self->base->pMethods->xClose(self->base);

  APSW_FAULT_INJECT(xCloseFails,, res=SQLITE_IOERR);

  /* we set pMethods to NULL after xClose callback so xClose can call other operations
     such as read or write during close */
  self->base->pMethods=NULL;

  PyMem_Free(self->base);
  self->base=NULL;

  if(res==SQLITE_OK)
    Py_RETURN_NONE;

  SET_EXC(res, NULL);
  return NULL;
}

#define APSWPROXYBASE						\
  APSWSQLite3File *apswfile=(APSWSQLite3File*)(void*)file;	\
  APSWVFSFile *f=(APSWVFSFile*) (apswfile->file);               \
  assert(Py_TYPE(f)==&APSWVFSFileType)

static int
apswproxyxShmLock(sqlite3_file *file, int offset, int n, int flags)
{
  APSWPROXYBASE;
  return f->base->pMethods->xShmLock(f->base, offset, n, flags);
}

static int
apswproxyxShmMap(sqlite3_file *file, int iPage, int pgsz, int isWrite, void volatile **pp)
{
  APSWPROXYBASE;
  return f->base->pMethods->xShmMap(f->base, iPage, pgsz, isWrite, pp);
}

static void
apswproxyxShmBarrier(sqlite3_file *file)
{
  APSWPROXYBASE;
  f->base->pMethods->xShmBarrier(f->base);
}

static int
apswproxyxShmUnmap(sqlite3_file *file, int deleteFlag)
{
  APSWPROXYBASE;
  return f->base->pMethods->xShmUnmap(f->base, deleteFlag);
}

static const struct sqlite3_io_methods apsw_io_methods_v1=
  {
    1,                                 /* version */
    apswvfsfile_xClose,                /* close */
    apswvfsfile_xRead,                 /* read */
    apswvfsfile_xWrite,                /* write */
    apswvfsfile_xTruncate,             /* truncate */
    apswvfsfile_xSync,                 /* sync */
    apswvfsfile_xFileSize,             /* filesize */
    apswvfsfile_xLock,                 /* lock */
    apswvfsfile_xUnlock,               /* unlock */
    apswvfsfile_xCheckReservedLock,    /* checkreservedlock */
    apswvfsfile_xFileControl,          /* filecontrol */
    apswvfsfile_xSectorSize,           /* sectorsize */
    apswvfsfile_xDeviceCharacteristics,/* device characteristics */
    0,                                 /* shmmap */
    0,                                 /* shmlock */
    0,                                 /* shmbarrier */
    0                                  /* shmunmap */
  };

static const struct sqlite3_io_methods apsw_io_methods_v2=
  {
    2,                                 /* version */
    apswvfsfile_xClose,                /* close */
    apswvfsfile_xRead,                 /* read */
    apswvfsfile_xWrite,                /* write */
    apswvfsfile_xTruncate,             /* truncate */
    apswvfsfile_xSync,                 /* sync */
    apswvfsfile_xFileSize,             /* filesize */
    apswvfsfile_xLock,                 /* lock */
    apswvfsfile_xUnlock,               /* unlock */
    apswvfsfile_xCheckReservedLock,    /* checkreservedlock */
    apswvfsfile_xFileControl,          /* filecontrol */
    apswvfsfile_xSectorSize,           /* sectorsize */
    apswvfsfile_xDeviceCharacteristics,/* device characteristics */
    apswproxyxShmMap,                  /* shmmap */
    apswproxyxShmLock,                 /* shmlock */
    apswproxyxShmBarrier,              /* shmbarrier */
    apswproxyxShmUnmap                 /* shmunmap */
  };




static PyMethodDef APSWVFSFile_methods[]={
  {"xRead", (PyCFunction)apswvfsfilepy_xRead, METH_VARARGS, "xRead"},
  {"xUnlock", (PyCFunction)apswvfsfilepy_xUnlock, METH_VARARGS, "xUnlock"},
  {"xLock", (PyCFunction)apswvfsfilepy_xLock, METH_VARARGS, "xLock"},
  {"xClose", (PyCFunction)apswvfsfilepy_xClose, METH_NOARGS, "xClose"},
  {"xSectorSize", (PyCFunction)apswvfsfilepy_xSectorSize, METH_NOARGS, "xSectorSize"},
  {"xFileSize", (PyCFunction)apswvfsfilepy_xFileSize, METH_NOARGS, "xFileSize"},
  {"xDeviceCharacteristics", (PyCFunction)apswvfsfilepy_xDeviceCharacteristics, METH_NOARGS, "xDeviceCharacteristics"},
  {"xCheckReservedLock", (PyCFunction)apswvfsfilepy_xCheckReservedLock, METH_NOARGS, "xCheckReservedLock"},
  {"xWrite", (PyCFunction)apswvfsfilepy_xWrite, METH_VARARGS, "xWrite"},
  {"xSync", (PyCFunction)apswvfsfilepy_xSync, METH_VARARGS, "xSync"},
  {"xTruncate", (PyCFunction)apswvfsfilepy_xTruncate, METH_VARARGS, "xTruncate"},
  {"xFileControl", (PyCFunction)apswvfsfilepy_xFileControl, METH_VARARGS, "xFileControl"},
  {"excepthook", (PyCFunction)apswvfs_excepthook, METH_VARARGS, "Exception hook"},
  /* Sentinel */
  {0, 0, 0, 0}
  };

static PyTypeObject APSWVFSFileType =
  {
    APSW_PYTYPE_INIT
    "apsw.VFSFile",            /*tp_name*/
    sizeof(APSWVFSFile),       /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)APSWVFSFile_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_VERSION_TAG, /*tp_flags*/
    "VFSFile object",          /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    APSWVFSFile_methods,       /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)APSWVFSFile_init, /* tp_init */
    0,                         /* tp_alloc */
    APSWVFSFile_new,           /* tp_new */
    0,                         /* tp_free */
    0,                         /* tp_is_gc */
    0,                         /* tp_bases */
    0,                         /* tp_mro */
    0,                         /* tp_cache */
    0,                         /* tp_subclasses */
    0,                         /* tp_weaklist */
    0                          /* tp_del */
    APSW_PYTYPE_VERSION
  };

/** .. class:: URIFilename

    SQLite uses a convoluted method of storing `uri parameters
    <https://sqlite.org/uri.html>`__ after the filename binding the
    C filename representation and parameters together.  This class
    encapsulates that binding.  The :ref:`example <example-vfs>` shows
    usage of this class.

    Your :meth:`VFS.xOpen` method will generally be passed one of
    these instead of a string as the filename if the URI flag was used
    or the main database flag is set.

    You can safely pass it on to the :class:`VFSFile` constructor
    which knows how to get the name back out.
*/


/** .. method:: filename() -> str

    Returns the filename.
*/
static PyObject*
apswurifilename_filename(APSWURIFilename *self)
{
  return convertutf8string(self->filename);
}

/** .. method:: uri_parameter(name) -> str

    Returns the value of parameter `name` or None.

    -* sqlite3_uri_parameter
*/
static PyObject*
apswurifilename_uri_parameter(APSWURIFilename *self, PyObject *param)
{
  const char *res;
  PyObject *asutf8=getutf8string(param);
  if(!asutf8)
    return NULL;
  res=sqlite3_uri_parameter(self->filename, PyBytes_AS_STRING(asutf8));
  Py_DECREF(asutf8);
  return convertutf8string(res);
}

/** .. method:: uri_int(name, default) -> int

    Returns the integer value for parameter `name` or `default` if not
    present.

    -* sqlite3_uri_int64
*/
static PyObject*
apswurifilename_uri_int(APSWURIFilename *self, PyObject *args)
{
  char *param=NULL;
  long long res=0;

  if(!PyArg_ParseTuple(args, "esL", STRENCODING, &param, &res))
    return NULL;

  res=sqlite3_uri_int64(self->filename, param, res);
  PyMem_Free(param);

  return PyLong_FromLongLong(res);
}

/** .. method:: uri_boolean(name, default) -> bool

    Returns the boolean value for parameter `name` or `default` if not
    present.

    -* sqlite3_uri_boolean
 */
static PyObject*
apswurifilename_uri_boolean(APSWURIFilename *self, PyObject *args)
{
  char *param=NULL;
  int res=0;

  if(!PyArg_ParseTuple(args, "esi", STRENCODING, &param, &res))
    return NULL;

  res=sqlite3_uri_boolean(self->filename, param, res);
  PyMem_Free(param);

  if(res)
    Py_RETURN_TRUE;
  Py_RETURN_FALSE;
}


static PyMethodDef APSWURIFilenameMethods[]={
  {"filename", (PyCFunction) apswurifilename_filename, METH_NOARGS, "Get filename"},
  {"uri_parameter", (PyCFunction) apswurifilename_uri_parameter, METH_O, "Get URI value"},
  {"uri_int", (PyCFunction) apswurifilename_uri_int, METH_VARARGS, "Get URI integer value"},
  {"uri_boolean", (PyCFunction) apswurifilename_uri_boolean, METH_VARARGS, "Get URI boolean value"},
  /* Sentinel */
  {0, 0, 0, 0}
};

static PyTypeObject APSWURIFilenameType=
  {
    APSW_PYTYPE_INIT
    "apsw.URIFilename",        /*tp_name*/
    sizeof(APSWURIFilename),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    0,                         /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_VERSION_TAG, /*tp_flags*/
    "Filename and URI",        /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    APSWURIFilenameMethods,    /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
    0,                         /* tp_new */
    0,                         /* tp_free */
    0,                         /* tp_is_gc */
    0,                         /* tp_bases */
    0,                         /* tp_mro */
    0,                         /* tp_cache */
    0,                         /* tp_subclasses */
    0,                         /* tp_weaklist */
    0                          /* tp_del */
    APSW_PYTYPE_VERSION
  };
