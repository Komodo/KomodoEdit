/* Augment a traceback with dummy stack frames from C so you can tell
   why the code was called. */

/*
  This code was originally from the Pyrex project:
  Copyright (C) 2004-2006 Greg Ewing <greg.ewing@canterbury.ac.nz>

  It has been lightly modified to be a part of APSW with permission from Greg
  and to be under the same license (and option for any OSI approved license) as
  the rest of APSW.

  See the accompanying LICENSE file.

  */

/* These are python header files */
#include "compile.h"
#include "frameobject.h"
#include "traceback.h"

/* Add a dummy frame to the traceback so the developer has a better idea of what C code was doing 

   @param filename: Use __FILE__ for this - it will be the filename reported in the frame
   @param lineno: Use __LINE__ for this - it will be the line number reported in the frame
   @param functionname: Name of the function reported
   @param localsformat: Format string for Py_BuildValue( that must specify a dictionary or NULL to make
                        an empty dictionary.  An example is "{s:i, s: s}" with the varargs then conforming
			to this format (the corresponding params could be "seven", 7, "foo", "bar"

*/
static void AddTraceBackHere(const char *filename, int lineno, const char *functionname, const char *localsformat, ...)
{
  PyObject *srcfile=0, *funcname=0, *empty_dict=0, *empty_tuple=0, *empty_string=0, *localargs=0, *empty_code=0;
  PyCodeObject *code=0;
  PyFrameObject *frame=0;
  va_list localargsva;

  va_start(localargsva, localsformat);

  assert(PyErr_Occurred());

#if PY_VERSION_HEX<0x03000000
  srcfile=PyString_FromString(filename);
  funcname=PyString_FromString(functionname);
#else
  srcfile=PyUnicode_FromString(filename);
  funcname=PyUnicode_FromString(functionname);
#endif
  empty_dict=PyDict_New();
  empty_tuple=PyTuple_New(0);
#if PY_VERSION_HEX<0x03000000
  empty_string=PyString_FromString("");
  empty_code=PyString_FromString("");
#else
  empty_string=PyUnicode_FromString("");
  empty_code=PyBytes_FromStringAndSize(NULL,0);
#endif

  localargs=localsformat?(Py_VaBuildValue((char *)localsformat, localargsva)):PyDict_New();
  if(localsformat)
    assert(localsformat[0]=='{');
  if(localargs)
    assert(PyDict_Check(localargs));

  /* did any fail? */
  if (!srcfile || !funcname || !empty_dict || !empty_tuple || !empty_string)
    goto end;

  /* make the dummy code object */
  code = PyCode_New(
     0,            /*int argcount,*/
#if PY_VERSION_HEX >= 0x03000000
     0,            /*int kwonlyargcount*/
#endif
     0,            /*int nlocals,*/
     0,            /*int stacksize,*/
     0,            /*int flags,*/
     empty_code,   /*PyObject *code,*/
     empty_tuple,  /*PyObject *consts,*/
     empty_tuple,  /*PyObject *names,*/
     empty_tuple,  /*PyObject *varnames,*/
     empty_tuple,  /*PyObject *freevars,*/
     empty_tuple,  /*PyObject *cellvars,*/
     srcfile,      /*PyObject *filename,*/
     funcname,     /*PyObject *name,*/
     lineno,       /*int firstlineno,*/
     empty_code    /*PyObject *lnotab*/
   );
  if (!code) goto end;

  /* make the dummy frame */
  frame=PyFrame_New(
           PyThreadState_Get(), /*PyThreadState *tstate,*/
	   code,                /*PyCodeObject *code,*/
	   empty_dict,          /*PyObject *globals,*/
	   localargs            /*PyObject *locals*/
	   );
  if(!frame) goto end;

  /* add dummy frame to traceback */
  frame->f_lineno=lineno;
  PyTraceBack_Here(frame);
  
  /* this epilogue deals with success or failure cases */
 end:
  va_end(localargsva);
  Py_XDECREF(localargs);
  Py_XDECREF(srcfile);
  Py_XDECREF(funcname);
  Py_XDECREF(empty_dict); 
  Py_XDECREF(empty_tuple); 
  Py_XDECREF(empty_string); 
  Py_XDECREF(empty_code);
  Py_XDECREF(code); 
  Py_XDECREF(frame); 
}

