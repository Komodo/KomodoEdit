/*
  Cross Python version compatibility code

  See the accompanying LICENSE file.
*/

/* Python 2.5 compatibility when size_t types become 64 bit.
   SQLite3 is limited to 32 bit sizes even on a 64 bit machine. */
#if PY_VERSION_HEX < 0x02050000
typedef int Py_ssize_t;
#endif

/* Python 2.3 doesn't have these */
#ifndef Py_RETURN_NONE
#define Py_RETURN_NONE return Py_INCREF(Py_None), Py_None
#endif
#ifndef Py_RETURN_TRUE
#define Py_RETURN_TRUE return Py_INCREF(Py_True), Py_True
#define Py_RETURN_FALSE return Py_INCREF(Py_False), Py_False
#endif

/* fun with objects - this is defined in Python 3 */
#ifndef Py_TYPE
#define Py_TYPE(x) ((x)->ob_type)
#endif

#ifndef Py_REFCNT
#define Py_REFCNT(x) (((PyObject*)x)->ob_refcnt)
#endif

#ifndef Py_CLEAR
#define Py_CLEAR(exp)                                   \
         do                                             \
           {                                            \
             if(exp)                                    \
               {                                        \
                 PyObject *_tmpclear=(PyObject*)(exp);  \
                 exp=0;                                 \
                 Py_DECREF(_tmpclear);                  \
               }                                        \
           } while(0)
#endif

/* define as zero if not present - introduced in Python 2.6 */
#ifndef Py_TPFLAGS_HAVE_VERSION_TAG
#define Py_TPFLAGS_HAVE_VERSION_TAG 0
#endif

/* How to make a string from a utf8 constant */
#if PY_MAJOR_VERSION < 3
#define MAKESTR  PyString_FromString
#else
#define MAKESTR  PyUnicode_FromString
#endif

/* Py 2 vs 3 can't decide how to start type initialization */
#if PY_MAJOR_VERSION < 3
/* The zero is ob_size */
#define APSW_PYTYPE_INIT \
  PyObject_HEAD_INIT(NULL)   0,
#else
#define APSW_PYTYPE_INIT PyVarObject_HEAD_INIT(NULL,0)
#endif

/* version tag? */
#if PY_VERSION_HEX >= 0x02060000
#define APSW_PYTYPE_VERSION ,0
#else
#define APSW_PYTYPE_VERSION
#endif

/* PyUnicode_READY needs to be called - Python 3.3 regression bug -
   http://bugs.python.org/issue16145  - gave up because other things
   crashed */

#define APSW_UNICODE_READY(x,y) do {} while(0)



#if PY_MAJOR_VERSION < 3
#define PyBytes_Check             PyString_Check
#define PyBytes_FromStringAndSize PyString_FromStringAndSize
#define PyBytes_AsString          PyString_AsString
#define PyBytes_AS_STRING         PyString_AS_STRING
#define PyBytes_GET_SIZE          PyString_GET_SIZE
#define _PyBytes_Resize           _PyString_Resize
#define PyBytes_CheckExact        PyString_CheckExact
#define PyBytesObject             PyStringObject
#define PyIntLong_Check(x)        (PyInt_Check((x)) || PyLong_Check((x)))
#define PyIntLong_AsLong(x)       ( (PyInt_Check((x))) ? ( PyInt_AsLong((x)) ) : ( (PyLong_AsLong((x)))))
#define PyBytes_FromFormat        PyString_FromFormat
#else
#define PyIntLong_Check           PyLong_Check
#define PyIntLong_AsLong          PyLong_AsLong
#define PyInt_FromLong            PyLong_FromLong
#define PyObject_Unicode          PyObject_Str
#endif

/* we clear weakref lists when close is called on a blob/cursor as
   well as when it is deallocated */
#define APSW_CLEAR_WEAKREFS                             \
  do {                                                  \
    if(self->weakreflist)                               \
      {                                                 \
        PyObject_ClearWeakRefs((PyObject*)self);        \
        self->weakreflist=0;                            \
      }                                                 \
  } while(0)


#if PY_VERSION_HEX<0x02040000
/* Introduced in Python 2.4 */
static int PyDict_Contains(PyObject *dict, PyObject *key)
{
  return !!PyDict_GetItem(dict, key);
}
#endif

/* Calls the named method of object with the provided args */
static PyObject*
Call_PythonMethod(PyObject *obj, const char *methodname, int mandatory, PyObject *args)
{
  PyObject *method=NULL;
  PyObject *res=NULL;

  /* we may be called when there is already an error.  eg if you return an error in
     a cursor method, then SQLite calls vtabClose which calls us.  We don't want to
     clear pre-existing errors, but we do want to clear ones when the function doesn't
     exist but is optional */
  PyObject *etype=NULL, *evalue=NULL, *etraceback=NULL;
  void *pyerralreadyoccurred=PyErr_Occurred();
  if(pyerralreadyoccurred)
    PyErr_Fetch(&etype, &evalue, &etraceback);


  /* we should only be called with ascii methodnames so no need to do
     character set conversions etc */
#if PY_VERSION_HEX < 0x02050000
  method=PyObject_GetAttrString(obj, (char*)methodname);
#else
  method=PyObject_GetAttrString(obj, methodname);
#endif
  assert(method!=obj);
  if (!method)
    {
      if(!mandatory)
	{
	  /* pretend method existed and returned None */
	  PyErr_Clear();
	  res=Py_None;
	  Py_INCREF(res);
	}
      goto finally;
    }

  res=PyEval_CallObject(method, args);
  if(!pyerralreadyoccurred && PyErr_Occurred())
    AddTraceBackHere(__FILE__, __LINE__, "Call_PythonMethod", "{s: s, s: i, s: O, s: O}",
                     "methodname", methodname,
                     "mandatory", mandatory,
                     "args", args,
                     "method", method);

 finally:
  if(pyerralreadyoccurred)
    PyErr_Restore(etype, evalue, etraceback);
  Py_XDECREF(method);
  return res;
}

static PyObject *
Call_PythonMethodV(PyObject *obj, const char *methodname, int mandatory, const char *format, ...)
{
  PyObject *args=NULL, *result=NULL;
  va_list list;
  va_start (list, format);
  args=Py_VaBuildValue(format, list);
  va_end(list);

  if (args)
    result=Call_PythonMethod(obj, methodname, mandatory, args);

  Py_XDECREF(args);
  return result;
}

/* CONVENIENCE FUNCTIONS */

/* Return a PyBuffer (py2) or PyBytes (py3) */
#if PY_MAJOR_VERSION < 3
static PyObject *
converttobytes(const void *ptr, Py_ssize_t size)
{

  PyObject *item;
  item=PyBuffer_New(size);
  if(item)
    {
      void *buffy=0;
      Py_ssize_t size2=size;
      int aswb=PyObject_AsWriteBuffer(item, &buffy, &size2);

      APSW_FAULT_INJECT(AsWriteBufferFails,,(PyErr_NoMemory(),aswb=-1));

      if(aswb==0)
        memcpy(buffy, ptr, size);
      else
        {
          Py_DECREF(item);
          item=NULL;
        }
    }
  return item;
}
#else
#define converttobytes PyBytes_FromStringAndSize
#endif

/* Convert a pointer and size UTF-8 string into a Python object.
   Pointer must be non-NULL.  New behaviour in 3.3.8 - always return
   Unicode strings
*/
static PyObject *
convertutf8stringsize(const char *str, Py_ssize_t size)
{
  assert(str);
  assert(size>=0);

  /* Performance optimization:  If str is all ascii then we
     can just make a unicode object and fill in the chars. PyUnicode_DecodeUTF8 is rather long
  */
  if(size<16384)
    {
      int isallascii=1;
      int i=size;
      const char *p=str;
      while(isallascii && i)
        {
          isallascii=! (*p & 0x80);
          i--;
          p++;
        }
      if(i==0 && isallascii)
        {
          Py_UNICODE *out;
          PyObject *res=PyUnicode_FromUnicode(NULL, size);
          if(!res) return res;
          APSW_UNICODE_READY(res, return NULL);
          out=PyUnicode_AS_UNICODE(res);

          i=size;
          while(i)
            {
              i--;
              *out=*str;
              out++;
              str++;
            }
          return res;
        }
    }

  return PyUnicode_DecodeUTF8(str, size, NULL);
}

/* Convert a NULL terminated UTF-8 string into a Python object.  None
   is returned if NULL is passed in. */
static PyObject *
convertutf8string(const char *str)
{
  if(!str)
    Py_RETURN_NONE;

  return convertutf8stringsize(str, strlen(str));
}

/* Returns a PyBytes/String encoded in UTF8 - new reference.
   Use PyBytes/String_AsString on the return value to get a
   const char * to utf8 bytes */
static PyObject *
getutf8string(PyObject *string)
{
  PyObject *inunicode=NULL;
  PyObject *utf8string=NULL;

  if(PyUnicode_CheckExact(string))
    {
      inunicode=string;
      Py_INCREF(string);
    }
#if PY_MAJOR_VERSION < 3
  else if(PyString_CheckExact(string))
    {
      /* A python 2 performance optimisation.  If the string consists
         only of ascii characters then it is already valid utf8.  And
         in py2 pybytes and pystring are the same thing.  This avoids
         doing a conversion to unicode and then a conversion to utf8.

         We only do this optimisation for strings that aren't
         ridiculously long.
      */
      if(PyString_GET_SIZE(string)<16384)
        {
          int isallascii=1;
          int i=PyString_GET_SIZE(string);
          const char *p=PyString_AS_STRING(string);
          while(isallascii && i)
            {
              isallascii=! (*p & 0x80);
              i--;
              p++;
            }
          if(i==0 && isallascii)
            {
              Py_INCREF(string);
              return string;
            }
        }
    }
#endif

  if(!inunicode)
      inunicode=PyUnicode_FromObject(string);

  if(!inunicode)
    return NULL;

  assert(!PyErr_Occurred());

  utf8string=PyUnicode_AsUTF8String(inunicode);
  Py_DECREF(inunicode);
  return utf8string;
}

