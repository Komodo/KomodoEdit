/*
  Another Python Sqlite Wrapper

  Wrap SQLite hot backup functionality

  See the accompanying LICENSE file.
*/

#ifdef EXPERIMENTAL

/**

.. _backup:

Backup
******

A backup object encapsulates copying one database to another.  You
call :meth:`Connection.backup` on the destination database to get the
backup object.  Call :meth:`~backup.step` to copy some pages
repeatedly dealing with errors as appropriate.  Finally
:meth:`~backup.finish` cleans up committing or rolling back and
releasing locks.

Here is an example usage using the **with** statement to ensure
:meth:`~backup.finish` is called::

  # copies source.main into db
  with db.backup("main", source, "main") as b:
      while not b.done:
          b.step(100)
          print b.remaining, b.pagecount, "\r",

If you are not using **with** then you'll need to ensure
:meth:`~backup.finish` is called::

  # copies source.main into db
  b=db.backup("main", source, "main")
  try:
      while not b.done:
          b.step(100)
          print b.remaining, b.pagecount, "\r",
  finally:
      b.finish()

Important details
=================

The database is copied page by page.  This means that there is not a
round trip via SQL.  All pages are copied including free ones.

The destination database is locked during the copy.  You will get a
:exc:`ThreadingViolationError` if you attempt to use it.
*/

/* we love us some macros */
#define CHECK_BACKUP_CLOSED(e)                                          \
do                                                                      \
  {                                                                     \
    if(!self->backup || (self->dest && !self->dest->db) || (self->source && !self->source->db) ) \
      {                                                                 \
        PyErr_Format(ExcConnectionClosed, "The backup is finished or the source or destination databases have been closed"); \
        return e;                                                       \
      }                                                                 \
  } while(0)

/** .. class:: backup

  You create a backup instance by calling :meth:`Connection.backup`.
*/

struct APSWBackup
{
  PyObject_HEAD
  Connection *dest;
  Connection *source;
  sqlite3_backup *backup;
  PyObject *done;
  int inuse;
  PyObject *weakreflist;
};

typedef struct APSWBackup APSWBackup;

static void
APSWBackup_init(APSWBackup *self, Connection *dest, Connection *source, sqlite3_backup *backup)
{
  assert(dest->inuse==0);
  dest->inuse=1;
  assert(source->inuse==1);  /* set by caller */

  self->dest=dest;
  self->source=source;
  self->backup=backup;
  self->done=Py_False;
  Py_INCREF(self->done);
  self->inuse=0;
  self->weakreflist=NULL;
}

/* returns non-zero if it set an exception */
static int
APSWBackup_close_internal(APSWBackup *self, int force)
{
  int res, setexc=0;

  assert(!self->inuse);

  if(!self->backup)
    return 0;

  PYSQLITE_BACKUP_CALL(res=sqlite3_backup_finish(self->backup));
  if(res)
    {
      switch(force)
        {
        case 0:
          SET_EXC(res, self->dest->db);
          setexc=1;
          break;
        case 1:
          break;
        case 2:
          {
            PyObject *etype, *eval, *etb;
            PyErr_Fetch(&etype, &eval, &etb);

            SET_EXC(res, self->dest->db);
            apsw_write_unraiseable(NULL);

            PyErr_Restore(etype, eval, etb);
            break;
          }
        }
    }

  self->backup=0;

  assert(self->dest->inuse);
  self->dest->inuse=0;

  Connection_remove_dependent(self->dest, (PyObject*)self);
  Connection_remove_dependent(self->source, (PyObject*)self);

  Py_CLEAR(self->dest);
  Py_CLEAR(self->source);

  return setexc;
}

static void
APSWBackup_dealloc(APSWBackup *self)
{
  APSW_CLEAR_WEAKREFS;

  APSWBackup_close_internal(self, 2);

  Py_CLEAR(self->done);

  Py_TYPE(self)->tp_free((PyObject*)self);
}

/** .. method:: step([npages=All]) -> bool

  Copies *npages* pages from the source to destination database.  The source database is locked during the copy so
  using smaller values allows other access to the source database.  The destination database is always locked until the
  backup object is :meth:`finished <backup.finish>`.

  :param npages: How many pages to copy. If the parameter is omitted
     or negative then all remaining pages are copied. The default page
     size is 1024 bytes (1kb) which can be changed before database
     creation using a `pragma
     <https://sqlite.org/pragma.html#modify>`_.

  This method may throw a :exc:`BusyError` or :exc:`LockedError` if
  unable to lock the source database.  You can catch those and try
  again.

  :returns: True if this copied the last remaining outstanding pages, else false.  This is the same value as :attr:`~backup.done`

  -* sqlite3_backup_step
*/
static PyObject *
APSWBackup_step(APSWBackup *self, PyObject *args)
{
  int pages=-1, res;

  CHECK_USE(NULL);
  CHECK_BACKUP_CLOSED(NULL);

  if(args && !PyArg_ParseTuple(args, "|i:step(pages=All)", &pages))
    return NULL;

  PYSQLITE_BACKUP_CALL(res=sqlite3_backup_step(self->backup, pages));
  if(PyErr_Occurred())
    return NULL;

  if(res==SQLITE_DONE)
    {
      if(self->done!=Py_True)
        {
          Py_CLEAR(self->done);
          self->done=Py_True;
          Py_INCREF(self->done);
        }
      res=SQLITE_OK;
    }

  if(res)
    {
      SET_EXC(res, NULL); /* ::TODO:: will likely have message on dest->db */
      return NULL;
    }

  Py_INCREF(self->done);
  return self->done;
}

/** .. method:: finish()

  Completes the copy process.  If all pages have been copied then the
  transaction is committed on the destination database, otherwise it
  is rolled back.  This method must be called for your backup to take
  effect.  The backup object will always be finished even if there is
  an exception.  It is safe to call this method multiple times.

  -* sqlite3_backup_finish
*/
static PyObject *
APSWBackup_finish(APSWBackup *self)
{
  int setexc;
  CHECK_USE(NULL);

  /* We handle CHECK_BACKUP_CLOSED internally */
  if(!self->backup)
    Py_RETURN_NONE;

  setexc=APSWBackup_close_internal(self, 0);
  if(setexc)
    return NULL;

  Py_RETURN_NONE;
}

/** .. method:: close([force=False])

  Does the same thing as :meth:`~backup.finish`.  This extra api is
  provided to give the same api as other APSW objects such as
  :meth:`Connection.close`, :meth:`blob.close` and
  :meth:`Cursor.close`.  It is safe to call this method multiple
  times.

  :param force: If true then any exceptions are ignored.
*/
static PyObject *
APSWBackup_close(APSWBackup *self, PyObject *args)
{
  int force=0, setexc;

  CHECK_USE(NULL);

  /* We handle CHECK_BACKUP_CLOSED internally */
  if(!self->backup)
    Py_RETURN_NONE; /* already closed */

  if(args && !PyArg_ParseTuple(args, "|i:close(force=False)", &force))
    return NULL;

  setexc=APSWBackup_close_internal(self, force);
  if(setexc)
    return NULL;
  Py_RETURN_NONE;
}

/** .. attribute:: remaining

  Read only. How many pages were remaining to be copied after the last
  step.  If you haven't called :meth:`~backup.step` or the backup
  object has been :meth:`finished <backup.finish>` then zero is
  returned.

  -* sqlite3_backup_remaining
*/
static PyObject *
APSWBackup_get_remaining(APSWBackup *self, APSW_ARGUNUSED void *ignored)
{
  CHECK_USE(NULL);
  return PyInt_FromLong(self->backup?sqlite3_backup_remaining(self->backup):0);
}

/** .. attribute:: pagecount

  Read only. How many pages were in the source database after the last
  step.  If you haven't called :meth:`~backup.step` or the backup
  object has been :meth:`finished <backup.finish>` then zero is
  returned.

  -* sqlite3_backup_pagecount
*/
static PyObject *
APSWBackup_get_pagecount(APSWBackup *self, APSW_ARGUNUSED void *ignored)
{
  CHECK_USE(NULL);
  return PyInt_FromLong(self->backup?sqlite3_backup_pagecount(self->backup):0);
}

/** .. method:: __enter__() -> self

  You can use the backup object as a `context manager
  <http://docs.python.org/reference/datamodel.html#with-statement-context-managers>`_
  as defined in :pep:`0343`.  The :meth:`~backup.__exit__` method ensures that backup
  is :meth:`finished <backup.finish>`.
*/
static PyObject *
APSWBackup_enter(APSWBackup *self)
{
  CHECK_USE(NULL);
  CHECK_BACKUP_CLOSED(NULL);

  Py_INCREF(self);
  return (PyObject*)self;
}

/** .. method:: __exit__() -> False

  Implements context manager in conjunction with :meth:`~backup.__enter__` ensuring
  that the copy is :meth:`finished <backup.finish>`.
*/
static PyObject *
APSWBackup_exit(APSWBackup *self, PyObject *args)
{
  PyObject *etype, *evalue, *etb;
  int setexc;

  CHECK_USE(NULL);

  if(!PyArg_ParseTuple(args, "OOO", &etype, &evalue, &etb))
    return NULL;

  /* If already closed then we are fine - CHECK_BACKUP_CLOSED not needed*/
  if(!self->backup)
    Py_RETURN_FALSE;

  /* we don't want to override any existing exception with the
     corresponding close exception, although there is a chance the
     close exception has more detail.  At the time of writing this
     code the step method only set an error code but not an error
     message */
  setexc=APSWBackup_close_internal(self, etype!=Py_None||evalue!=Py_None||etb!=Py_None);

  if(setexc)
    {
      assert(PyErr_Occurred());
      return NULL;
    }

  Py_RETURN_FALSE;
}


/** .. attribute:: done

  A boolean that is True if the copy completed in the last call to :meth:`~backup.step`.
*/
static PyMemberDef backup_members[] = {
  /* name type offset flags doc */
  {"done", T_OBJECT, offsetof(APSWBackup, done), READONLY, "True if all pages copied"},
  {0,0,0,0,0}
};

static PyGetSetDef backup_getset[] = {
  /* name getter setter doc closure */
  {"remaining", (getter)APSWBackup_get_remaining, NULL, "Pages still to be copied", NULL},
  {"pagecount", (getter)APSWBackup_get_pagecount, NULL, "Total pages in source database", NULL},
  {0,0,0,0,0}
};

static PyMethodDef backup_methods[] = {
  {"__enter__", (PyCFunction)APSWBackup_enter, METH_NOARGS,
   "Context manager entry"},
  {"__exit__", (PyCFunction)APSWBackup_exit, METH_VARARGS,
   "Context manager exit"},
  {"step", (PyCFunction)APSWBackup_step, METH_VARARGS,
   "Copies some pages"},
  {"finish", (PyCFunction)APSWBackup_finish, METH_NOARGS,
   "Commits or rollsback backup"},
  {"close", (PyCFunction)APSWBackup_close, METH_VARARGS,
   "Alternate way to finish"},
  {0,0,0,0}
};

static PyTypeObject APSWBackupType =
  {
    APSW_PYTYPE_INIT
    "apsw.backup",             /*tp_name*/
    sizeof(APSWBackup),        /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)APSWBackup_dealloc, /*tp_dealloc*/
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
    "backup object",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    offsetof(APSWBackup,weakreflist), /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    backup_methods,            /* tp_methods */
    backup_members,            /* tp_members */
    backup_getset,             /* tp_getset */
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



#endif /* EXPERIMENTAL */
