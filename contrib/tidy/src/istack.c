/* istack.c -- inline stack for compatibility with Mosaic

  (c) 1998-2004 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.
  
  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2004/12/06 12:53:25 $ 
    $Revision: 1.16 $ 

*/

#include "tidy-int.h"
#include "lexer.h"
#include "attrs.h"
#include "streamio.h"
#include "tmbstr.h"

/* duplicate attributes */
AttVal *DupAttrs( TidyDocImpl* doc, AttVal *attrs)
{
    AttVal *newattrs;

    if (attrs == NULL)
        return attrs;

    newattrs = NewAttribute();
    *newattrs = *attrs;
    newattrs->next = DupAttrs( doc, attrs->next );
    newattrs->attribute = tmbstrdup(attrs->attribute);
    newattrs->value = tmbstrdup(attrs->value);
    newattrs->dict = FindAttribute(doc, newattrs);
    newattrs->asp = attrs->asp ? CloneNode(doc, attrs->asp) : NULL;
    newattrs->php = attrs->php ? CloneNode(doc, attrs->php) : NULL;
    return newattrs;
}

/*
  push a copy of an inline node onto stack
  but don't push if implicit or OBJECT or APPLET
  (implicit tags are ones generated from the istack)

  One issue arises with pushing inlines when
  the tag is already pushed. For instance:

      <p><em>text
      <p><em>more text

  Shouldn't be mapped to

      <p><em>text</em></p>
      <p><em><em>more text</em></em>
*/
void PushInline( TidyDocImpl* doc, Node *node)
{
    Lexer* lexer = doc->lexer;
    IStack *istack;

    if (node->implicit)
        return;

    if (node->tag == NULL)
        return;

    if (!(node->tag->model & CM_INLINE))
        return;

    if (node->tag->model & CM_OBJECT)
        return;

    if ( !nodeIsFONT(node) && IsPushed(doc, node) )
        return;

    /* make sure there is enough space for the stack */
    if (lexer->istacksize + 1 > lexer->istacklength)
    {
        if (lexer->istacklength == 0)
            lexer->istacklength = 6;   /* this is perhaps excessive */

        lexer->istacklength = lexer->istacklength * 2;
        lexer->istack = (IStack *)MemRealloc(lexer->istack,
                            sizeof(IStack)*(lexer->istacklength));
    }

    istack = &(lexer->istack[lexer->istacksize]);
    istack->tag = node->tag;

    istack->element = tmbstrdup(node->element);
    istack->attributes = DupAttrs( doc, node->attributes );
    ++(lexer->istacksize);
}

/* pop inline stack */
void PopInline( TidyDocImpl* doc, Node *node )
{
    Lexer* lexer = doc->lexer;
    AttVal *av;
    IStack *istack;

    if (node)
    {
        if (node->tag == NULL)
            return;

        if (!(node->tag->model & CM_INLINE))
            return;

        if (node->tag->model & CM_OBJECT)
            return;

        /* if node is </a> then pop until we find an <a> */
        if ( nodeIsA(node) )
        {
            while (lexer->istacksize > 0)
            {
                --(lexer->istacksize);
                istack = &(lexer->istack[lexer->istacksize]);

                while (istack->attributes)
                {
                    av = istack->attributes;
                    istack->attributes = av->next;
                    FreeAttribute( doc, av );
                }

                if ( istack->tag->id == TidyTag_A )
                {
                    MemFree(istack->element);
                    break;
                }

                MemFree(istack->element);
            }

            return;
        }
    }

    if (lexer->istacksize > 0)
    {
        --(lexer->istacksize);
        istack = &(lexer->istack[lexer->istacksize]);

        while (istack->attributes)
        {
            av = istack->attributes;
            istack->attributes = av->next;
            FreeAttribute( doc, av );
        }

        MemFree(istack->element);

        /* #427822 - fix by Randy Waki 7 Aug 00 */
        if (lexer->insert >= lexer->istack + lexer->istacksize)
            lexer->insert = NULL;
    }
}

Bool IsPushed( TidyDocImpl* doc, Node *node)
{
    Lexer* lexer = doc->lexer;
    int i;

    for (i = lexer->istacksize - 1; i >= 0; --i)
    {
        if (lexer->istack[i].tag == node->tag)
            return yes;
    }

    return no;
}

/*
  This has the effect of inserting "missing" inline
  elements around the contents of blocklevel elements
  such as P, TD, TH, DIV, PRE etc. This procedure is
  called at the start of ParseBlock. when the inline
  stack is not empty, as will be the case in:

    <i><h1>italic heading</h1></i>

  which is then treated as equivalent to

    <h1><i>italic heading</i></h1>

  This is implemented by setting the lexer into a mode
  where it gets tokens from the inline stack rather than
  from the input stream.
*/
int InlineDup( TidyDocImpl* doc, Node* node )
{
    Lexer* lexer = doc->lexer;
    int n;

    if ((n = lexer->istacksize - lexer->istackbase) > 0)
    {
        lexer->insert = &(lexer->istack[lexer->istackbase]);
        lexer->inode = node;
    }

    return n;
}

/*
 defer duplicates when entering a table or other
 element where the inlines shouldn't be duplicated
*/
void DeferDup( TidyDocImpl* doc )
{
    doc->lexer->insert = NULL;
    doc->lexer->inode = NULL;
}

Node *InsertedToken( TidyDocImpl* doc )
{
    Lexer* lexer = doc->lexer;
    Node *node;
    IStack *istack;
    uint n;

    /* this will only be NULL if inode != NULL */
    if (lexer->insert == NULL)
    {
        node = lexer->inode;
        lexer->inode = NULL;
        return node;
    }

    /*
    
      is this is the "latest" node then update
      the position, otherwise use current values
    */

    if (lexer->inode == NULL)
    {
        lexer->lines = doc->docIn->curline;
        lexer->columns = doc->docIn->curcol;
    }

    node = NewNode(lexer);
    node->type = StartTag;
    node->implicit = yes;
    node->start = lexer->txtstart;
    /* #431734 [JTidy bug #226261 (was 126261)] - fix by Gary Peskin 20 Dec 00 */ 
    node->end = lexer->txtend; /* was : lexer->txtstart; */
    istack = lexer->insert;

#if 0 && defined(_DEBUG)
    if ( lexer->istacksize == 0 )
        fprintf( stderr, "0-size istack!\n" );
#endif

    node->element = tmbstrdup(istack->element);
    node->tag = istack->tag;
    node->attributes = DupAttrs( doc, istack->attributes );

    /* advance lexer to next item on the stack */
    n = (uint)(lexer->insert - &(lexer->istack[0]));

    /* and recover state if we have reached the end */
    if (++n < lexer->istacksize)
        lexer->insert = &(lexer->istack[n]);
    else
        lexer->insert = NULL;

    return node;
}




