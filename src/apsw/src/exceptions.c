/*
  Exception code, data and macros

  See the accompanying LICENSE file.
*/


/* EXCEPTION TYPES */

static PyObject *APSWException;  /* root exception class */
static PyObject *ExcThreadingViolation; /* thread misuse */
static PyObject *ExcIncomplete;  /* didn't finish previous query */
static PyObject *ExcBindings;  /* wrong number of bindings */
static PyObject *ExcComplete;  /* query is finished */
static PyObject *ExcTraceAbort; /* aborted by exectrace */
static PyObject *ExcExtensionLoading; /* error loading extension */
static PyObject *ExcConnectionNotClosed; /* connection wasn't closed when destructor called */
static PyObject *ExcCursorClosed; /* cursor object was closed when function called */
static PyObject *ExcConnectionClosed; /* connection was closed when function called */
static PyObject *ExcVFSNotImplemented; /* base vfs doesn't implment function */
static PyObject *ExcVFSFileClosed;     /* attempted operation on closed file */
static PyObject *ExcForkingViolation; /* used object across a fork */

static void make_exception(int res, sqlite3 *db);

/* If res indicates an SQLite error then do all the exception creation
 work.  We don't overwrite earlier exceptions hence the PyErr_Occurred
 check */
#define SET_EXC(res,db)  { if(res != SQLITE_OK && !PyErr_Occurred()) make_exception(res,db); }

/* A dictionary we store the last error from each thread in.  Used
   thread local storage previously. The key is a PyLong of the thread
   id and the value is a PyBytes. */
static PyObject *tls_errmsg;

/* This method is called with the database mutex held but the GIL
   released.  Previous code used thread local storage which is a bit
   too OS dependent (eg required a DllMain under Windows) but it
   didn't need any Python code.  It is safe to acquire the GIL since
   the db mutex has been acquired first so we are no different than a
   user defined function. */
static void
apsw_set_errmsg(const char *msg)
{
  PyObject *key=NULL, *value=NULL;
  PyObject *etype, *eval, *etb;

  PyGILState_STATE gilstate=PyGILState_Ensure();
  /* dictionary operations whine if there is an outstanding error */
  PyErr_Fetch(&etype, &eval, &etb);

  if(!tls_errmsg)
    {
      tls_errmsg=PyDict_New();
      if(!tls_errmsg) goto finally;
    }
  key=PyLong_FromLong(PyThread_get_thread_ident());
  if(!key) goto finally;
  value=PyBytes_FromStringAndSize(msg, strlen(msg));
  if(!value) goto finally;

  PyDict_SetItem(tls_errmsg, key, value);

 finally:
  Py_XDECREF(key);
  Py_XDECREF(value);
  PyErr_Restore(etype, eval, etb);
  PyGILState_Release(gilstate);
}

static const char *
apsw_get_errmsg(void)
{
  const char *retval=NULL;
  PyObject *key=NULL, *value;

  /* set should always have been called first */
  assert(tls_errmsg);
  
  key=PyLong_FromLong(PyThread_get_thread_ident());
  if(!key) goto finally;
  value=PyDict_GetItem(tls_errmsg, key);
  if(value)
    retval=PyBytes_AsString(value);

 finally:
  Py_XDECREF(key);
  /* value is borrowed */
  return retval;
}


static struct { int code; const char *name; PyObject *cls;}
exc_descriptors[]=
  {
    /* Generic Errors */
    {SQLITE_ERROR,    "SQL", NULL},    
    {SQLITE_MISMATCH, "Mismatch", NULL},
    {SQLITE_NOTFOUND, "NotFound", NULL},

    /* Internal Errors */
    {SQLITE_INTERNAL, "Internal", NULL},  /* NOT USED */
    {SQLITE_PROTOCOL, "Protocol", NULL},
    {SQLITE_MISUSE,   "Misuse", NULL},
    {SQLITE_RANGE,    "Range", NULL},

    /* permissions etc */
    {SQLITE_PERM,     "Permissions", NULL},
    {SQLITE_READONLY, "ReadOnly", NULL},
    {SQLITE_CANTOPEN, "CantOpen", NULL},
    {SQLITE_AUTH,     "Auth", NULL},

    /* abort/busy/etc */
    {SQLITE_ABORT,    "Abort", NULL},
    {SQLITE_BUSY,     "Busy", NULL},
    {SQLITE_LOCKED,   "Locked", NULL},
    {SQLITE_INTERRUPT,"Interrupt", NULL},
    {SQLITE_SCHEMA,   "SchemaChange", NULL}, 
    {SQLITE_CONSTRAINT, "Constraint", NULL},

    /* memory/disk/corrupt etc */
    {SQLITE_NOMEM,    "NoMem", NULL},
    {SQLITE_IOERR,    "IO", NULL},
    {SQLITE_CORRUPT,  "Corrupt", NULL},
    {SQLITE_FULL,     "Full", NULL},
    {SQLITE_TOOBIG,   "TooBig", NULL},
    {SQLITE_NOLFS,    "NoLFS", NULL},
    {SQLITE_EMPTY,    "Empty", NULL},
    {SQLITE_FORMAT,   "Format", NULL},
    {SQLITE_NOTADB,   "NotADB", NULL},

    {-1, 0, 0}
  };


/* EXCEPTION CODE */

/* MS compiler is stupid and requires this pulled out */

typedef struct {PyObject **var; const char *name; } APSWExceptionMapping;

static int init_exceptions(PyObject *m)
{
  char buffy[100]; /* more than enough for anyone :-) */
  unsigned int i;
  PyObject *obj;

  APSWExceptionMapping apswexceptions[]={
    {&ExcThreadingViolation, "ThreadingViolationError"},
    {&ExcIncomplete, "IncompleteExecutionError"},
    {&ExcBindings, "BindingsError"},
    {&ExcComplete, "ExecutionCompleteError"},
    {&ExcTraceAbort, "ExecTraceAbort"},
    {&ExcExtensionLoading, "ExtensionLoadingError"},
    {&ExcConnectionNotClosed, "ConnectionNotClosedError"},
    {&ExcConnectionClosed, "ConnectionClosedError"},
    {&ExcCursorClosed, "CursorClosedError"},
    {&ExcVFSNotImplemented, "VFSNotImplementedError"},
    {&ExcVFSFileClosed, "VFSFileClosedError"},
    {&ExcForkingViolation, "ForkingViolationError"}
  };


  /* PyModule_AddObject uses borrowed reference so we incref whatever
     we give to it, so we still have a copy to use */

  /* custom ones first */

  APSWException=PyErr_NewException("apsw.Error", NULL, NULL);
  if(!APSWException) return -1;
  Py_INCREF(APSWException);
  if(PyModule_AddObject(m, "Error", (PyObject *)APSWException))
    return -1;

  for(i=0; i<sizeof(apswexceptions)/sizeof(apswexceptions[0]); i++)
    {
      sprintf(buffy, "apsw.%s", apswexceptions[i].name);
      *apswexceptions[i].var=PyErr_NewException(buffy, APSWException, NULL);
      if(!*apswexceptions[i].var) return -1;                                      
      Py_INCREF(*apswexceptions[i].var);                                          
      if(PyModule_AddObject(m, apswexceptions[i].name, *apswexceptions[i].var))         
        return -1;
    }

  /* all the ones corresponding to SQLITE error codes */
  for(i=0;exc_descriptors[i].name;i++)
    {
      sprintf(buffy, "apsw.%sError", exc_descriptors[i].name);
      obj=PyErr_NewException(buffy, APSWException, NULL);
      if(!obj) return -1;
      Py_INCREF(obj);
      exc_descriptors[i].cls=obj;
      sprintf(buffy, "%sError", exc_descriptors[i].name);
      if(PyModule_AddObject(m, buffy, obj))
        return -1;
    }
  
  return 0;
}

static void make_exception(int res, sqlite3 *db)
{
  int i;
  const char *errmsg=NULL;
  
  if(db) errmsg=apsw_get_errmsg();
  if(!errmsg) errmsg="error";

  APSW_FAULT_INJECT(UnknownSQLiteErrorCode,,res=0xfe);
  
  for(i=0;exc_descriptors[i].name;i++)
    if (exc_descriptors[i].code==(res&0xff))
      {
	PyObject *etype, *eval, *etb;
        assert(exc_descriptors[i].cls);
        PyErr_Format(exc_descriptors[i].cls, "%sError: %s", exc_descriptors[i].name, errmsg);
	PyErr_Fetch(&etype, &eval, &etb);
	PyErr_NormalizeException(&etype, &eval, &etb);
	PyObject_SetAttrString(eval, "result", Py_BuildValue("i", res&0xff));
	PyObject_SetAttrString(eval, "extendedresult", Py_BuildValue("i", res));
	PyErr_Restore(etype, eval, etb);
        assert(PyErr_Occurred());
        return;
      }

  /* this line should only be reached if SQLite returns an error code not in the main list */
  PyErr_Format(APSWException, "Error %d: %s", res, errmsg);  
}

/* Turns the current Python exception into an SQLite error code and
   stores the string in the errmsg field (if not NULL).  The errmsg
   field is expected to belong to sqlite and hence uses sqlite
   semantics/ownership - for example see the pzErr parameter to
   xCreate */

static int
MakeSqliteMsgFromPyException(char **errmsg)
{
  int res=SQLITE_ERROR;
  int i;
  PyObject *str=NULL;
  PyObject *etype=NULL, *evalue=NULL, *etraceback=NULL;

  assert(PyErr_Occurred());

  PyErr_Fetch(&etype, &evalue, &etraceback);

  /* find out if the exception corresponds to an apsw exception descriptor */
  for(i=0;exc_descriptors[i].code!=-1;i++)
    if(PyErr_GivenExceptionMatches(etype, exc_descriptors[i].cls))
      {
        res=exc_descriptors[i].code;
        /* do we have extended information available? */
        if(PyObject_HasAttrString(evalue, "extendedresult"))
          {
            /* extract it */
            PyObject *extended=PyObject_GetAttrString(evalue, "extendedresult");
            if(extended && PyIntLong_Check(extended))
              /* Any errors in this will be swallowed */
              res=(PyIntLong_AsLong(extended) & 0xffffff00u)|res;
            Py_XDECREF(extended);
          }
        break;
      }

  if(errmsg)
    {
      /* I just want a string of the error! */      
      if(!str && evalue)
	str=PyObject_Str(evalue);
      if(!str && etype)
	str=PyObject_Str(etype);
      if(!str) str=MAKESTR("python exception with no information");
      if(*errmsg)
	sqlite3_free(*errmsg);
      *errmsg=sqlite3_mprintf("%s",PyBytes_AsString(str));

      Py_XDECREF(str);
    }

  PyErr_Restore(etype, evalue, etraceback);
  assert(PyErr_Occurred());
  return res;
}
