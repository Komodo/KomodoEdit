/*
  A prepared statment cache for SQLite

  See the accompanying LICENSE file.
*/

/* This is used while executing a statement.  It may either be
   residing in the statement cache (doing the prepare to make a
   sqlite3_stmt is relatively expensive) or standalone if the cache
   was full. A doubly linked list is used to keep track of a
   least/most recent use. */

/* The following keys are considered for a cache entry:

   - The original text passed in (PyString/PyUnicode)
   - The utf8 of the original text (APSWBuffer)
   - The utf8 of the first statement (APSWBuffer)
   
   Currently only the first two are implemented.

 */

/* Some defines */

/* Set to zero to disable statement object recycling.  Even small amount makes a big difference
   with diminishing returns based on how many the user program goes through without freeing and
   the interpretter gc intervals. */
#define SC_NRECYCLE 32

/* The maximum length of something in bytes that we would consider putting in the statement cache */
#define SC_MAXSIZE 16384

/* Define to do statement cache statistics */
/* #define SC_STATS */

typedef struct APSWStatement {
  PyObject_HEAD
  sqlite3_stmt *vdbestatement;      /* the sqlite level vdbe code */
  unsigned inuse;                   /* indicates an element is inuse when in cache preventing simulataneous use */
  unsigned incache;                 /* indicates APSWStatement resides in cache */
  PyObject *utf8;                   /* The text of the statement, also the key in the cache */
  PyObject *next;                   /* If not null, the utf8 text of the remaining statements in multi statement queries. */
  Py_ssize_t querylen;              /* How many bytes of utf8 made up the query (used for exectrace) */
  PyObject *origquery;              /* The original query object, also a key in the cache pointing to this same statement - could be NULL */
  struct APSWStatement *lru_prev;   /* previous item in lru list (ie more recently used than this one) */
  struct APSWStatement *lru_next;   /* next item in lru list (ie less recently used than this one) */
} APSWStatement;

static PyTypeObject APSWStatementType;


typedef struct StatementCache {
  sqlite3 *db;                      /* database connection */
  PyObject *cache;                  /* the actual cache itself */
  unsigned numentries;              /* how many APSWStatement entries
                                       we have in cache */
  unsigned maxentries;              /* maximum number of entries */
  APSWStatement *mru;               /* most recently used entry (head of the list) */
  APSWStatement *lru;               /* least recently used entry (tail of the list) */
#ifdef SC_STATS
  unsigned st_cachemiss;            /* entry was not in cache */
  unsigned st_cachehit;             /* entry was in cache */
  unsigned st_hitinuse;             /* was a hit but was inuse */
#endif
#if SC_NRECYCLE > 0
  APSWStatement* recyclelist[SC_NRECYCLE];   /* recycle these rather than go through repeated malloc/free */
  unsigned nrecycle;                /* index of last entry in recycle list */
#endif
} StatementCache;

#ifndef NDEBUG
static void 
statementcache_sanity_check(StatementCache *sc)
{
  unsigned itemcountfwd, itemcountbackwd, i;
  APSWStatement *last, *item;

#if SC_NRECYCLE > 0
  /* also check the recycle list */
  for(i=0;i<sc->nrecycle;i++)
    assert(Py_REFCNT(sc->recyclelist[i])==1);
  assert(sc->nrecycle<=SC_NRECYCLE);
#endif

  /* make sure everything is fine */
  if(!sc->mru || !sc->lru)
    {
      /* list should be empty */
      assert(!sc->mru);
      assert(!sc->lru);
      return;
    }

  if(sc->mru == sc->lru)
    {
      /* should be exactly one item */
      assert(!sc->mru->lru_prev);
      assert(!sc->mru->lru_next);
      assert(sc->mru->incache);
      assert(sc->mru->vdbestatement);
      assert(!sc->mru->inuse);
      return;
    }

  /* Must be two or more items.  If there are any loops then this function will
     execute forever. */

  /* check items going forward */
  last=NULL;
  itemcountfwd=0;
  item=sc->mru;
  
  while(item)
    {
      /* check item thinks it is in cache */
      assert(item->incache==1);
      /* should not be inuse - inuse items are removed from lru list */
      assert(!item->inuse);
      /* does prev actually go to prev? */
      assert(item->lru_prev==last);
      /* check for loops */
      assert(item->lru_prev!=item);
      assert(item->lru_next!=item);
      assert(item->lru_prev!=item->lru_next);

      itemcountfwd++;
      last=item;
      item=item->lru_next;
    }
  assert(sc->lru==last);

  /* check items going backwards */
  last=NULL;
  itemcountbackwd=0;
  item=sc->lru;

  while(item)
    {
      /* does next actually go to next? */
      assert(item->lru_next==last);
      /* check for loops */
      assert(item->lru_next!=item);
      assert(item->lru_prev!=item);
      assert(item->lru_prev!=item->lru_next);
      /* statement not null */
      assert(item->vdbestatement);

      itemcountbackwd++;
      last=item;
      item=item->lru_prev;
    }

  /* count should be same going forwards as going back */
  assert(itemcountbackwd==itemcountfwd);
}

/* verifies a particular value is not in the dictionary */
static void assert_not_in_dict(PyObject *dict, PyObject *check)
{
  PyObject *key, *value;
  Py_ssize_t pos=0;

  while(PyDict_Next(dict, &pos, &key, &value))
    assert(check!=value);
}
#else
#define statementcache_sanity_check(x)
#define assert_not_in_dict(x,y)
#endif


/* re-prepare for SQLITE_SCHEMA */
static int
statementcache_reprepare(StatementCache *sc, APSWStatement *statement)
{
  int res, res2;
  sqlite3_stmt *newvdbe=0;
  const char *tail;
  const char *buffer;
  Py_ssize_t buflen;
  int usepreparev2;

  usepreparev2=sqlite3_bind_parameter_count(statement->vdbestatement);
  buffer=APSWBuffer_AS_STRING(statement->utf8);
  buflen=APSWBuffer_GET_SIZE(statement->utf8);
  /* see statementcache_prepare */
  assert(buffer[buflen+1-1]==0);
  PYSQLITE_SC_CALL(res=usepreparev2?
		   sqlite3_prepare_v2(sc->db, buffer, buflen+1, &newvdbe, &tail):  /* PYSQLITE_SC_CALL */
		   sqlite3_prepare(sc->db, buffer, buflen+1, &newvdbe, &tail)      /* PYSQLITE_SC_CALL */
		   );
  if(res!=SQLITE_OK)
    goto error;

  /* the query size certainly shouldn't have changed! */
  assert(statement->querylen==tail-buffer);
  APSW_FAULT_INJECT(TransferBindingsFail,
                    PYSQLITE_SC_CALL(res=sqlite3_transfer_bindings(statement->vdbestatement, newvdbe)),
                    res=SQLITE_NOMEM);
  if(res!=SQLITE_OK)
    goto error;

  PYSQLITE_SC_CALL(sqlite3_finalize(statement->vdbestatement));
  statement->vdbestatement=newvdbe;
  return SQLITE_OK;

 error:
  SET_EXC(res, sc->db);
  AddTraceBackHere(__FILE__, __LINE__, "sqlite3_prepare", "{s: N}", "sql", convertutf8stringsize(buffer, buflen));
  /* we don't want to clobber the errmsg so pretend everything is ok */
  res2=res;
  res=SQLITE_OK;
  if(newvdbe)
    PYSQLITE_SC_CALL(sqlite3_finalize(newvdbe));
  
  return res2;
}

/* Internal prepare routine after doing utf8 conversion.  Returns a new reference. Must be reentrant */
static APSWStatement*
statementcache_prepare(StatementCache *sc, PyObject *query, int usepreparev2)
{
  APSWStatement *val=NULL;
  const char *buffer;
  const char *tail;
  Py_ssize_t buflen;
  int res;
  PyObject *utf8=NULL;

  if(!APSWBuffer_Check(query))
    {
      /* Check to see if query is already in cache.  The size checks are to
         avoid calculating hashes on long strings */
      if( sc->cache && sc->numentries && ((PyUnicode_CheckExact(query) && PyUnicode_GET_DATA_SIZE(query) < SC_MAXSIZE)
#if PY_MAJOR_VERSION < 3 
          || (PyString_CheckExact(query) && PyString_GET_SIZE(query) < SC_MAXSIZE)
#endif
                        ))
        {
          val=(APSWStatement*)PyDict_GetItem(sc->cache, query);
          if(val)
            {
              utf8=val->utf8;
              Py_INCREF(utf8);
              goto cachehit;
            }
        }

      utf8=getutf8string(query);
  
      if(!utf8)
        return NULL;
  
      {
        /* Make a buffer of utf8 which then owns underlying bytes */
        PyObject *tmp=APSWBuffer_FromObject(utf8, 0, PyBytes_GET_SIZE(utf8));
        Py_DECREF(utf8);
        if(!tmp) return NULL;
        utf8=tmp;
      }
    }
  else
    {
      utf8=query;
      query=NULL;
      Py_INCREF(utf8);
    }

  assert(APSWBuffer_Check(utf8));

  /* if we have cache and utf8 is reasonable size? */
  if(sc->cache && sc->numentries && APSWBuffer_GET_SIZE(utf8) < SC_MAXSIZE)
    {
      /* then is it in the cache? */
      val=(APSWStatement*)PyDict_GetItem(sc->cache, utf8);
    }

  /* by this point we have created utf8 or added a reference to it */
 cachehit:
  assert(APSWBuffer_Check(utf8));

#ifdef SC_STATS
  if(val) 
    {
      sc->st_cachehit++;
      if(val->inuse)
        sc->st_hitinuse++;
    }
  else
    sc->st_cachemiss++;
#endif


  if(val)
    {
      if(!val->inuse)
        {
          /* yay, one we can use */
          assert(val->incache);
          assert(val->vdbestatement);
          val->inuse=1;

          /* unlink from lru tracking */
          if(sc->mru==val)
            sc->mru=val->lru_next;
          if(sc->lru==val)
            sc->lru=val->lru_prev;
          if(val->lru_prev)
            {
              assert(val->lru_prev->lru_next==val);
              val->lru_prev->lru_next=val->lru_next;
            }
          if(val->lru_next)
            {
              assert(val->lru_next->lru_prev==val);
              val->lru_next->lru_prev=val->lru_prev;
            }
          val->lru_prev=val->lru_next=0;
          statementcache_sanity_check(sc);

          _PYSQLITE_CALL_V(sqlite3_clear_bindings(val->vdbestatement));          
          Py_INCREF( (PyObject*)val);
          assert(PyObject_RichCompareBool(utf8, val->utf8, Py_EQ)==1);
          APSWBuffer_XDECREF_unlikely(utf8);
          return val;
        }
      /* someone else is using it so we can't */
      val=NULL;
    }

#if SC_NRECYCLE > 0
  if(sc->nrecycle)
    {
      val=sc->recyclelist[--sc->nrecycle];
      assert(Py_REFCNT(val)==1);
      assert(!val->incache);
      assert(!val->inuse);
      if(val->vdbestatement)
        _PYSQLITE_CALL_V(sqlite3_finalize(val->vdbestatement));
      APSWBuffer_XDECREF_likely(val->utf8);
      APSWBuffer_XDECREF_unlikely(val->next);
      Py_XDECREF(val->origquery);
      val->lru_prev=val->lru_next=0;
      statementcache_sanity_check(sc);
    }
#else
  assert(!val);
#endif

  if(!val)
    {
      /* have to make one */
      val=PyObject_New(APSWStatement, &APSWStatementType);
      if(!val) goto error;
      /* zero it - other fields are set below */
      val->incache=0;
      val->lru_prev=0;
      val->lru_next=0;
    }

  statementcache_sanity_check(sc);
  
  val->utf8=utf8;
  val->next=NULL;
  val->vdbestatement=NULL;
  val->inuse=1;
  Py_XINCREF(query);
  val->origquery=query;

  buffer=APSWBuffer_AS_STRING(utf8);
  buflen=APSWBuffer_GET_SIZE(utf8);

  /* If buffer[lengthpassedin-1] is not zero then SQLite makes a duplicate copy of the
     entire string passed in.  The buffer we originally got from getutf8string
     will always have had an extra zero on the end.  The assert is just to make
     sure */
  assert(buffer[buflen+1-1]==0);
  PYSQLITE_SC_CALL(res=(usepreparev2)?
		   sqlite3_prepare_v2(sc->db, buffer, buflen+1, &val->vdbestatement, &tail):  /* PYSQLITE_SC_CALL */
		   sqlite3_prepare(sc->db, buffer, buflen+1, &val->vdbestatement, &tail));    /* PYSQLITE_SC_CALL */

  /* Handle error.  We would have a Python error if vtable.FindFunction had an error */
  if(res!=SQLITE_OK || PyErr_Occurred())
    {
      SET_EXC(res, sc->db);
      AddTraceBackHere(__FILE__, __LINE__, "sqlite3_prepare", "{s: N}", "sql", convertutf8stringsize(buffer, buflen));
      goto error;
    }

  val->querylen=tail-buffer;
  /* is there a next statement (ignore semicolons and white space) */
  while( (tail-buffer<buflen) && (*tail==' ' || *tail=='\t' || *tail==';' || *tail=='\r' || *tail=='\n') )
    tail++;
  if(tail-buffer<buflen)
    {
      /* there are more statements */
      val->next=APSWBuffer_FromObject(utf8, tail-buffer, buflen-(tail-buffer));
      if(!val->next) goto error;
    }
  return val;

 error:
  if(val) 
    {
      val->inuse=0;
#if SC_NRECYCLE > 0
      if(sc->nrecycle<SC_NRECYCLE)
        {
          sc->recyclelist[sc->nrecycle++]=val;
        }
      else
#endif
        /* Getting this line to execute is hard as the statement would
           have come from the recyclelist in the first place so there
           will be a spot to return it to.  The only way to do it
           would be some violent threading to refill the recyclelist
           between this statement being taken out and returned */
        Py_DECREF(val);
    }
  return NULL;
}     


/* Consumes reference on stmt.  This routine must be reentrant. 
   If reprepare_on_schema then if SQLITE_SCHEMA is the error, we reprepare
   the statement and don't finalize.
*/
static int
statementcache_finalize(StatementCache *sc, APSWStatement *stmt, int reprepare_on_schema)
{
  int res;

  /* PyDict_Contains will end up whining in comparison function if
     there is an existing exception hanging over our head */
  assert(!PyErr_Occurred());

  statementcache_sanity_check(sc);

  assert(stmt->inuse);

  /* we do not release the lock until the last possible moment,
     otherwise another thread could enter and reuse what we are in the
     middle of disposing of */

  PYSQLITE_SC_CALL(res=sqlite3_reset(stmt->vdbestatement));
  if(res==SQLITE_SCHEMA && reprepare_on_schema)
    {
      res=statementcache_reprepare(sc, stmt);
      if(res==SQLITE_OK)
        return SQLITE_SCHEMA;
    }

  /* is it going to be put in cache? */
  if(stmt->incache || (sc->cache && stmt->vdbestatement && APSWBuffer_GET_SIZE(stmt->utf8) < SC_MAXSIZE && !PyDict_Contains(sc->cache, stmt->utf8)))
    {
      /* add ourselves to cache */
      if(!stmt->incache)
        {
          assert(!PyDict_Contains(sc->cache, stmt->utf8));
          assert_not_in_dict(sc->cache, (PyObject*)stmt);
          PyDict_SetItem(sc->cache, stmt->utf8, (PyObject*)stmt);
          if(stmt->origquery)
            /* something equal to this query may already be in cache
               which would cause an eviction of an unrelated item and
               all sorts of grief */
            if (!PyDict_Contains(sc->cache, stmt->origquery))
                PyDict_SetItem(sc->cache, stmt->origquery, (PyObject*)stmt);
          stmt->incache=1;
          sc->numentries += 1;
        }

      assert(PyDict_Contains(sc->cache, stmt->utf8));

      /* do we need to do an evict? */
      while(sc->numentries > sc->maxentries)
        {
          APSWStatement *evictee=sc->lru;
          statementcache_sanity_check(sc);
          assert(evictee!=stmt);      /* we were inuse and so should not be on evict list */

          /* no possibles to evict? */
          if(!sc->lru)
            break;

          /* only entry? */
          if(!evictee->lru_prev)
            {
              assert(sc->mru==evictee);   /* points to sole entry */
              assert(sc->lru==evictee);   /* points to sole entry */
              assert(!evictee->lru_prev); /* should be anyone before */
              assert(!evictee->lru_next); /* or after */
              sc->mru=NULL;
              sc->lru=NULL;
              goto delevictee;
            }
          /* take out lru member */
          sc->lru=evictee->lru_prev;
          assert(sc->lru->lru_next==evictee);
          sc->lru->lru_next=NULL;
          
        delevictee:
          assert(!evictee->inuse);
          assert(evictee->incache);
          statementcache_sanity_check(sc);

          /* only references should be the dict */
          assert(Py_REFCNT(evictee)==1+!!evictee->origquery);

#if SC_NRECYCLE > 0
          /* we don't gc to run on object */
          Py_INCREF(evictee);
#endif
          if(evictee->origquery)
            {
              assert(evictee==(APSWStatement*)PyDict_GetItem(sc->cache, evictee->origquery));
              PyDict_DelItem(sc->cache, evictee->origquery);
              Py_DECREF(evictee->origquery);
              evictee->origquery=NULL;
            }
          assert(evictee==(APSWStatement*)PyDict_GetItem(sc->cache, evictee->utf8));
          PyDict_DelItem(sc->cache, evictee->utf8);
          assert_not_in_dict(sc->cache, (PyObject*)evictee);
          assert(!PyErr_Occurred());

#if SC_NRECYCLE > 0
          if(sc->nrecycle<SC_NRECYCLE)
            {
              assert(Py_REFCNT(evictee)==1);
              sc->recyclelist[sc->nrecycle++]=evictee;
              evictee->incache=0;
            }
          else
            {
              Py_DECREF(evictee);
            }
#endif
          sc->numentries -= 1;
          statementcache_sanity_check(sc);
        }

      statementcache_sanity_check(sc);

      /* plumb ourselves into head of lru list */
      assert(stmt->inuse);
      stmt->inuse=0;
      stmt->lru_next=sc->mru;
      stmt->lru_prev=NULL;
      if(sc->mru)
        sc->mru->lru_prev=stmt;
      sc->mru=stmt;
      if(!sc->lru)
        sc->lru=stmt;
      statementcache_sanity_check(sc);
    }

  stmt->inuse=0;
#if SC_NRECYCLE > 0
  if(!stmt->incache && sc->nrecycle<SC_NRECYCLE)
    {
      assert(Py_REFCNT(stmt)==1);
      sc->recyclelist[sc->nrecycle++]=stmt;
    }
  else
#endif
    {
      Py_DECREF(stmt);
    }
  return res;
}
    

/* returns SQLITE_OK on success.  ppstmt will be next statement on
   success else null on error.  reference will be consumed on ppstmt
   passed in and new reference on one returned */
static int
statementcache_next(StatementCache *sc, APSWStatement **ppstmt, int usepreparev2)
{
  PyObject *next=(*ppstmt)->next;
  int res;

  assert(next);
  Py_INCREF(next);

  res=statementcache_finalize(sc, *ppstmt, 0); /* INUSE_CALL not needed here */

  /* defensive coding.  res will never be an error as errors would
     have been returned from earlier step call */
     
  assert(res==SQLITE_OK);
    
  if(res!=SQLITE_OK) goto error;

  /* statementcache_prepare already sets exception */
  *ppstmt=statementcache_prepare(sc, next, usepreparev2);  /* INUSE_CALL not needed here */
  res=(*ppstmt)?SQLITE_OK:SQLITE_ERROR;

 error:
  APSWBuffer_XDECREF_unlikely(next);

  return res;
}



static StatementCache*
statementcache_init(sqlite3 *db, unsigned nentries)
{
  StatementCache *sc=(StatementCache*)PyMem_Malloc(sizeof(StatementCache));
  if(!sc) return NULL;

  memset(sc, 0, sizeof(StatementCache));
  sc->db=db;
  /* sc->cache is left as null if we aren't caching */
  if (nentries)
    {
      APSW_FAULT_INJECT(StatementCacheAllocFails,
                        sc->cache=PyDict_New(),
                        sc->cache=PyErr_NoMemory());
      if(!sc->cache)
        {
          PyMem_Free(sc);
          return NULL;
        }
    }
  sc->maxentries=nentries;
  sc->mru=NULL;
  sc->lru=NULL;
#if SC_NRECYCLE > 0
  sc->nrecycle=0;
#endif
  return sc;
}

static void
statementcache_free(StatementCache *sc)
{
#if SC_NRECYCLE>0
  while(sc->nrecycle)
    {
      PyObject *o=(PyObject*)sc->recyclelist[--sc->nrecycle];
      Py_DECREF(o);
    }
#endif
  Py_XDECREF(sc->cache);
  PyMem_Free(sc);

#ifdef SC_STATS
  fprintf(stderr, "SC Miss: %u Hit: %u HitButInuse: %u\n", sc->st_cachemiss, sc->st_cachehit, sc->st_hitinuse);
#endif
}

static void
APSWStatement_dealloc(APSWStatement *stmt)
{
  if(stmt->vdbestatement)
    _PYSQLITE_CALL_V(sqlite3_finalize(stmt->vdbestatement));
  assert(stmt->inuse==0);
  APSWBuffer_XDECREF_likely(stmt->utf8);
  APSWBuffer_XDECREF_likely(stmt->next);
  Py_XDECREF(stmt->origquery);
  Py_TYPE(stmt)->tp_free((PyObject*)stmt);
}

/* Convert a utf8 buffer to PyUnicode */
static PyObject *
convertutf8buffertounicode(PyObject *buffer)
{
  assert(APSWBuffer_Check(buffer));
  return convertutf8stringsize(APSWBuffer_AS_STRING(buffer), APSWBuffer_GET_SIZE(buffer));
}

/* Convert a utf8 buffer and size to PyUnicode */
static PyObject *
convertutf8buffersizetounicode(PyObject *buffer, Py_ssize_t len)
{
  assert(APSWBuffer_Check(buffer));
  assert(len<=APSWBuffer_GET_SIZE(buffer));

  return convertutf8stringsize(APSWBuffer_AS_STRING(buffer), len);
}


static PyTypeObject APSWStatementType =
  {
    APSW_PYTYPE_INIT
    "apsw.APSWStatement",      /*tp_name*/
    sizeof(APSWStatement),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)APSWStatement_dealloc, /*tp_dealloc*/ 
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
    "APSWStatement object",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    0,                         /* tp_methods */
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
