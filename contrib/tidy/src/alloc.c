/* alloc.c -- Default memory allocation routines.

  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/04/08 09:11:13 $ 
    $Revision: 1.5 $ 

*/

#include "tidy.h"

static TidyMalloc  g_malloc  = NULL;
static TidyRealloc g_realloc = NULL;
static TidyFree    g_free    = NULL;
static TidyPanic   g_panic   = NULL;

Bool TIDY_CALL tidySetMallocCall( TidyMalloc fmalloc )
{
  g_malloc  = fmalloc;
  return yes;
}
Bool TIDY_CALL tidySetReallocCall( TidyRealloc frealloc )
{
  g_realloc = frealloc;
  return yes;
}
Bool TIDY_CALL tidySetFreeCall( TidyFree ffree )
{
  g_free    = ffree;
  return yes;
}
Bool TIDY_CALL tidySetPanicCall( TidyPanic fpanic )
{
  g_panic   = fpanic;
  return yes;
}

void FatalError( ctmbstr msg )
{
  if ( g_panic )
    g_panic( msg );
  else
  {
    /* 2 signifies a serious error */
    fprintf( stderr, "Fatal error: %s\n", msg );
    exit(2);
  }
}

void* MemAlloc( size_t size )
{
    void *p = ( g_malloc ? g_malloc(size) : malloc(size) );
    if ( !p )
        FatalError("Out of memory!");
    return p;
}

void* MemRealloc( void* mem, size_t newsize )
{
    void *p;
    if ( mem == NULL )
        return MemAlloc( newsize );

    p = ( g_realloc ? g_realloc(mem, newsize) : realloc(mem, newsize) );
    if (!p)
        FatalError("Out of memory!");
    return p;
}

void MemFree( void* mem )
{
    if ( mem )
    {
        if ( g_free )
            g_free( mem );
        else
            free( mem );
    }
}

void ClearMemory( void *mem, size_t size )
{
    memset(mem, 0, size);
}

