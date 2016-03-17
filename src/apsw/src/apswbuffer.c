/*
  A lightweight buffer class that works across Python 2 and 3.

  See the accompanying LICENSE file.
*/

/* Set to zero to disable buffer object recycling.  Even a small amount
   makes a big difference with diminishing returns based on how many
   the user program goes through without freeing and the interpretter
   gc intervals. */
#ifndef AB_NRECYCLE
#define AB_NRECYCLE 256
#endif

typedef struct APSWBuffer {
  PyObject_HEAD
  PyObject *base; /* the pybytes/pystring we are a view of */
  const char *data;
  Py_ssize_t length;
  long hash;
} APSWBuffer;

static PyTypeObject APSWBufferType;

#define APSWBuffer_Check(x) (Py_TYPE(x)==&APSWBufferType)
#define APSWBuffer_AS_STRING(x)  ( ((APSWBuffer*)(x)) -> data )
#define APSWBuffer_GET_SIZE(x)   ( ((APSWBuffer*)(x)) -> length )


#if AB_NRECYCLE > 0
static APSWBuffer* apswbuffer_recyclelist[AB_NRECYCLE];
static unsigned apswbuffer_nrecycle=0;

static void 
_APSWBuffer_DECREF(PyObject *x)
{
  APSWBuffer *y=(APSWBuffer*)x;
  assert(APSWBuffer_Check(x));
  assert(Py_REFCNT(x)==1);

  if(apswbuffer_nrecycle<AB_NRECYCLE)
    {
      apswbuffer_recyclelist[apswbuffer_nrecycle++]=y;
      if(y->base)
        assert(!APSWBuffer_Check(y->base));
      Py_XDECREF(y->base); 
      y->base=NULL;            
    }
  else
    {
      Py_DECREF(y);
    }
}


#define APSWBuffer_XDECREF(x) \
do {                                                              \
  if(x)                                                           \
    {                                                             \
      if(Py_REFCNT(x)==1)                                         \
        { _APSWBuffer_DECREF(x); }                                \
      else                                                        \
        { Py_DECREF(x);                        }                  \
    }                                                             \
 } while(0)                                          

/* Profiling of the test suite and speedtest was used to which locations
   were likely to meet the criteria for recycling the buffer object and
   which wouldn't */
#define APSWBuffer_XDECREF_likely APSWBuffer_XDECREF
#define APSWBuffer_XDECREF_unlikely Py_XDECREF

#ifdef APSW_TESTFIXTURES
static void
APSWBuffer_fini(void)
{
  while(apswbuffer_nrecycle)
    {
      PyObject *p=(PyObject*)apswbuffer_recyclelist[--apswbuffer_nrecycle];
      Py_DECREF(p);
    }
}
#endif

#else
#define APSWBuffer_XDECREF_likely Py_XDECREF
#define APSWBuffer_XDECREF_unlikely Py_XDECREF
#ifdef APSW_TESTFIXTURES
static void
APSWBuffer_fini(void)
{
}
#endif
#endif


static long
APSWBuffer_hash(APSWBuffer *self)
{
  long hash;
  unsigned char *p;
  Py_ssize_t len;

  if(self->hash!=-1)
    return self->hash;

  /* this is the same algorithm as used for Python
     strings/bytes/buffer except we add one so that there is no hash
     collision */
  p=(unsigned char*)self->data;
  len=self->length;

  /* The python implementations all start the hash with the first byte
     even if the length is zero.  This checks there was a zero padding
     byte there as pystring/pyunicode do anyway */
  assert( (len==0)?(*p==0):1 );

  hash=*p << 7;

  while(--len>=0)
    hash=(1000003*hash) ^ *p++;

  hash ^= self->length;

  hash++; /* avoid collision */

  /* I tried to find a string that would have a hash of -2 but failed. */
  if(hash==-1)
    hash= -2;

  self->hash=hash;
  
  return hash;
}


static PyObject *
APSWBuffer_FromObject(PyObject *base, Py_ssize_t offset, Py_ssize_t length)
{
  APSWBuffer *res=NULL;
#if AB_NRECYCLE > 0
  if(apswbuffer_nrecycle)
    {
      res=apswbuffer_recyclelist[--apswbuffer_nrecycle];
    }
  else
#endif
    {
      res=PyObject_New(APSWBuffer, &APSWBufferType);
      if(!res) return NULL;
    }

  assert(length>=0);

  /* the base object can be another apswbuffer */
  if(APSWBuffer_Check(base))
    {
      assert(PyBytes_Check(((APSWBuffer*)base)->base));
      assert(offset <= APSWBuffer_GET_SIZE(base));
      assert(offset+length <= APSWBuffer_GET_SIZE(base));

      res->base=((APSWBuffer*)base)->base;
      Py_INCREF(res->base);
      res->data=APSWBuffer_AS_STRING(base)+offset;
      res->length=length;
      res->hash= -1;
      
      return (PyObject*)res;
    }

  /* or pybytes/pystring */
  assert(PyBytes_Check(base));
  assert(offset<=PyBytes_GET_SIZE(base));
  assert(offset+length<=PyBytes_GET_SIZE(base));
  Py_INCREF(base);
  res->base=base;
  res->data=PyBytes_AS_STRING(base)+offset;
  res->length=length;

  /* Performance hack. If the bytes/string we are copying from has
     already calculated a hash then use that rather than recalculating
     it ourselves. */
  res->hash= -1;
#ifndef PYPY_VERSION
  assert(PyBytes_CheckExact(base));
  if(offset==0 && length==PyBytes_GET_SIZE(base))
    {
      res->hash=((PyBytesObject*)base)->ob_shash;
      if(res->hash<-2 || res->hash>-1)
        res->hash+=1;
    }
#endif

#ifndef NDEBUG
  /* check our conniving performance hack actually worked */
  if(res->hash!=-1)
    {
      long tmp=res->hash;
      res->hash= -1;
      assert(tmp==APSWBuffer_hash(res));
      res->hash=tmp;
    }
#endif

  return (PyObject*)res;
}

static void
APSWBuffer_dealloc(APSWBuffer *self)
{
  if(self->base)
    assert(!APSWBuffer_Check(self->base));
  Py_CLEAR(self->base);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

/* Our instances are not publically exposed and we are only compared
   for dictionary insertion/checking, so take some serious short cuts */
static PyObject *
APSWBuffer_richcompare(APSWBuffer *left, APSWBuffer *right, int op)
{
  assert(op==Py_EQ);
  assert(left->hash!=-1);
  assert(right->hash!=-1);
  
  if(left->hash != right->hash || left->length != right->length)
    goto notequal;

  if(left->data == right->data)
    goto equal;

  if(0==memcmp(left->data, right->data, left->length))
    goto equal;

 notequal:
  Py_RETURN_FALSE;

 equal:
  Py_RETURN_TRUE;
}

static PyTypeObject APSWBufferType =
  {
    APSW_PYTYPE_INIT
    "apsw.APSWBuffer",         /*tp_name*/
    sizeof(APSWBuffer),        /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)APSWBuffer_dealloc, /*tp_dealloc*/ 
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    (hashfunc)APSWBuffer_hash, /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_VERSION_TAG, /*tp_flags*/
    "APSWStatement object",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    (richcmpfunc)APSWBuffer_richcompare,    /* tp_richcompare */
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
