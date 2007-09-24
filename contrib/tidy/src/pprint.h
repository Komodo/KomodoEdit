#ifndef __PPRINT_H__
#define __PPRINT_H__

/* pprint.h -- pretty print parse tree  
  
   (c) 1998-2003 (W3C) MIT, ERCIM, Keio University
   See tidy.h for the copyright notice.
  
   CVS Info:
     $Author: hoehrmann $ 
     $Date: 2003/05/24 15:55:02 $ 
     $Revision: 1.4 $ 

*/

#include "forward.h"

/*
  Block-level and unknown elements are printed on
  new lines and their contents indented 2 spaces

  Inline elements are printed inline.

  Inline content is wrapped on spaces (except in
  attribute values or preformatted text, after
  start tags and before end tags
*/

#define NORMAL        0
#define PREFORMATTED  1
#define COMMENT       2
#define ATTRIBVALUE   4
#define NOWRAP        8
#define CDATA         16


/* The pretty printer keeps at most two lines of text in the
** buffer before flushing output.  We need to capture the
** indent state (indent level) at the _beginning_ of _each_
** line, not the end of just the second line.
**
** We must also keep track "In Attribute" and "In String"
** states at the _end_ of each line, 
*/

typedef struct _TidyIndent
{
    int spaces;
    int attrValStart;
    int attrStringStart;
} TidyIndent;

typedef struct _TidyPrintImpl
{
    uint *linebuf;
    uint lbufsize;
    uint linelen;
    uint wraphere;
    uint linecount;
  
    uint ixInd;
    TidyIndent indent[2];  /* Two lines worth of indent state */

} TidyPrintImpl;

void PPrintDocument( TidyDocImpl* doc );


#if SUPPORT_ASIAN_ENCODINGS
/* #431953 - start RJ Wraplen adjusted for smooth international ride */
uint CWrapLen( TidyDocImpl* doc, uint ind );
#endif

void InitPrintBuf( TidyDocImpl* doc );
void FreePrintBuf( TidyDocImpl* doc );

void PFlushLine( TidyDocImpl* doc, uint indent );
void PCondFlushLine( TidyDocImpl* doc, uint indent );

void PPrintScriptStyle( TidyDocImpl* doc, uint mode, uint indent, Node* node );

/* print just the content of the body element.
** useful when you want to reuse material from
** other documents.
** 
** -- Sebastiano Vigna <vigna@dsi.unimi.it>
*/

void PrintPreamble( TidyDocImpl* doc );   /* Between these 3, */
void PrintBody( TidyDocImpl* doc );       /* you can print an entire document */
void PrintPostamble( TidyDocImpl* doc );  /* or you can substitute another */
                                          /* node as body using PPrintTree() */

void PPrintTree( TidyDocImpl* doc, uint mode, uint indent, Node *node );

void PPrintXMLTree( TidyDocImpl* doc, uint mode, uint indent, Node *node );


#endif /* __PPRINT_H__ */
