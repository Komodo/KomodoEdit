/* parser.c -- HTML Parser

  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.
  
  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/08/23 14:03:38 $ 
    $Revision: 1.148 $ 

*/

#include "tidy-int.h"
#include "lexer.h"
#include "parser.h"
#include "message.h"
#include "clean.h"
#include "tags.h"
#include "tmbstr.h"

#ifdef AUTO_INPUT_ENCODING
#include "charsets.h"
#endif

Bool CheckNodeIntegrity(Node *node)
{
#ifndef NO_NODE_INTEGRITY_CHECK
    if (node->prev)
    {
        if (node->prev->next != node)
            return no;
    }

    if (node->next)
    {
        if (node->next->prev != node)
            return no;
    }

    if (node->parent)
    {
        Node *child = NULL;
        if (node->prev == NULL && node->parent->content != node)
            return no;

        if (node->next == NULL && node->parent->last != node)
            return no;

        for (child = node->parent->content; child; child = child->next)
        {
            if (child == node)
                break;
        }
        if ( node != child )
            return no;
    }

    for (node = node->content; node; node = node->next)
        if ( !CheckNodeIntegrity(node) )
            return no;

#endif
    return yes;
}

/*
 used to determine how attributes
 without values should be printed
 this was introduced to deal with
 user defined tags e.g. Cold Fusion
*/
Bool IsNewNode(Node *node)
{
    if (node && node->tag)
    {
        return (node->tag->model & CM_NEW);
    }
    return yes;
}

void CoerceNode(TidyDocImpl* doc, Node *node, TidyTagId tid, Bool obsolete, Bool unexpected)
{
    const Dict* tag = LookupTagDef(tid);
    Node* tmp = InferredTag(doc, tag->id);

    if (obsolete)
        ReportWarning(doc, node, tmp, OBSOLETE_ELEMENT);
    else if (unexpected)
        ReportError(doc, node, tmp, REPLACING_UNEX_ELEMENT);
    else
        ReportNotice(doc, node, tmp, REPLACING_ELEMENT);

    MemFree(tmp->element);
    MemFree(tmp);

    node->was = node->tag;
    node->tag = tag;
    node->type = StartTag;
    node->implicit = yes;
    MemFree(node->element);
    node->element = tmbstrdup(tag->name);
}

/* extract a node and its children from a markup tree */
Node *RemoveNode(Node *node)
{
    if (node->prev)
        node->prev->next = node->next;

    if (node->next)
        node->next->prev = node->prev;

    if (node->parent)
    {
        if (node->parent->content == node)
            node->parent->content = node->next;

        if (node->parent->last == node)
            node->parent->last = node->prev;
    }

    node->parent = node->prev = node->next = NULL;
    return node;
}

/* remove node from markup tree and discard it */
Node *DiscardElement( TidyDocImpl* doc, Node *element )
{
    Node *next = NULL;

    if (element)
    {
        next = element->next;
        RemoveNode(element);
        FreeNode( doc, element);
    }

    return next;
}

/*
 insert "node" into markup tree as the firt element
 of content of "element"
*/
void InsertNodeAtStart(Node *element, Node *node)
{
    node->parent = element;

    if (element->content == NULL)
        element->last = node;
    else
        element->content->prev = node;

    node->next = element->content;
    node->prev = NULL;
    element->content = node;
}

/*
 insert "node" into markup tree as the last element
 of content of "element"
*/
void InsertNodeAtEnd(Node *element, Node *node)
{
    node->parent = element;
    node->prev = element->last;

    if (element->last != NULL)
        element->last->next = node;
    else
        element->content = node;

    element->last = node;
}

/*
 insert "node" into markup tree in place of "element"
 which is moved to become the child of the node
*/
static void InsertNodeAsParent(Node *element, Node *node)
{
    node->content = element;
    node->last = element;
    node->parent = element->parent;
    element->parent = node;

    if (node->parent->content == element)
        node->parent->content = node;

    if (node->parent->last == element)
        node->parent->last = node;

    node->prev = element->prev;
    element->prev = NULL;

    if (node->prev)
        node->prev->next = node;

    node->next = element->next;
    element->next = NULL;

    if (node->next)
        node->next->prev = node;
}

/* insert "node" into markup tree before "element" */
void InsertNodeBeforeElement(Node *element, Node *node)
{
    Node *parent;

    parent = element->parent;
    node->parent = parent;
    node->next = element;
    node->prev = element->prev;
    element->prev = node;

    if (node->prev)
        node->prev->next = node;

    if (parent->content == element)
        parent->content = node;
}

/* insert "node" into markup tree after "element" */
void InsertNodeAfterElement(Node *element, Node *node)
{
    Node *parent;

    parent = element->parent;
    node->parent = parent;

    /* AQ - 13 Jan 2000 fix for parent == NULL */
    if (parent != NULL && parent->last == element)
        parent->last = node;
    else
    {
        node->next = element->next;
        /* AQ - 13 Jan 2000 fix for node->next == NULL */
        if (node->next != NULL)
            node->next->prev = node;
    }

    element->next = node;
    node->prev = element;
}

static Bool CanPrune( TidyDocImpl* doc, Node *element )
{
    if ( nodeIsText(element) )
        return yes;

    if ( element->content )
        return no;

    if ( element->tag == NULL )
        return no;

    if ( element->tag->model & CM_BLOCK && element->attributes != NULL )
        return no;

    if ( nodeIsA(element) && element->attributes != NULL )
        return no;

    if ( nodeIsP(element) && !cfgBool(doc, TidyDropEmptyParas) )
        return no;

    if ( element->tag->model & CM_ROW )
        return no;

    if ( element->tag->model & CM_EMPTY )
        return no;

    if ( nodeIsAPPLET(element) )
        return no;

    if ( nodeIsOBJECT(element) )
        return no;

    if ( nodeIsSCRIPT(element) && attrGetSRC(element) )
        return no;

    if ( nodeIsTITLE(element) )
        return no;

    /* #433359 - fix by Randy Waki 12 Mar 01 */
    if ( nodeIsIFRAME(element) )
        return no;

    /* fix for bug 770297 */
    if (nodeIsTEXTAREA(element))
        return no;

    if ( attrGetID(element) || attrGetNAME(element) )
        return no;

    /* fix for bug 695408; a better fix would look for unknown and    */
    /* known proprietary attributes that make the element significant */
    if (attrGetDATAFLD(element))
        return no;

    /* fix for bug 723772, don't trim new-...-tags */
    if (element->tag->id == TidyTag_UNKNOWN)
        return no;

    if (nodeIsBODY(element))
        return no;

    if (nodeIsCOLGROUP(element))
        return no;

    return yes;
}

Node *TrimEmptyElement( TidyDocImpl* doc, Node *element )
{
    if ( CanPrune(doc, element) )
    {
       if (element->type != TextNode)
            ReportNotice(doc, element, NULL, TRIM_EMPTY_ELEMENT);

        return DiscardElement(doc, element);
    }
    else if ( nodeIsP(element) && element->content == NULL )
    {
        /* Put a non-breaking space into empty paragraphs.
        ** Contrary to intent, replacing empty paragraphs
        ** with two <br><br> does not preserve formatting.
        */
        const char onesixty[2] = { '\240', '\0' };
        InsertNodeAtStart( element, NewLiteralTextNode(doc->lexer, onesixty) );
    }
    return element;
}

Node* DropEmptyElements(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (node->content)
            DropEmptyElements(doc, node->content);

        if (!nodeIsElement(node) &&
            !(nodeIsText(node) && !(node->start < node->end)))
        {
            node = next;
            continue;
        }

        next = TrimEmptyElement(doc, node);
        node = node == next ? node->next : next;
    }

    return node;
}

/* 
  errors in positioning of form start or end tags
  generally require human intervention to fix
*/
static void BadForm( TidyDocImpl* doc )
{
    doc->badForm = yes;
    /* doc->errors++; */
}

/*
  This maps 
       <em>hello </em><strong>world</strong>
  to
       <em>hello</em> <strong>world</strong>

  If last child of element is a text node
  then trim trailing white space character
  moving it to after element's end tag.
*/
static void TrimTrailingSpace( TidyDocImpl* doc, Node *element, Node *last )
{
    Lexer* lexer = doc->lexer;
    byte c;

    if (nodeIsText(last))
    {
        if (last->end > last->start)
        {
            c = (byte) lexer->lexbuf[ last->end - 1 ];

            if (   c == ' '
#ifdef COMMENT_NBSP_FIX
                || c == 160
#endif
               )
            {
#ifdef COMMENT_NBSP_FIX
                /* take care with <td>&nbsp;</td> */
                if ( c == 160 && 
                     ( element->tag == doc->tags.tag_td || 
                       element->tag == doc->tags.tag_th )
                   )
                {
                    if (last->end > last->start + 1)
                        last->end -= 1;
                }
                else
#endif
                {
                    last->end -= 1;
                    if ( (element->tag->model & CM_INLINE) &&
                         !(element->tag->model & CM_FIELD) )
                        lexer->insertspace = yes;
                }
            }
        }
    }
}

#if 0
static Node *EscapeTag(Lexer *lexer, Node *element)
{
    Node *node = NewNode(lexer);

    node->start = lexer->lexsize;
    AddByte(lexer, '<');

    if (element->type == EndTag)
        AddByte(lexer, '/');

    if (element->element)
    {
        char *p;
        for (p = element->element; *p != '\0'; ++p)
            AddByte(lexer, *p);
    }
    else if (element->type == DocTypeTag)
    {
        uint i;
        AddStringLiteral( lexer, "!DOCTYPE " );
        for (i = element->start; i < element->end; ++i)
            AddByte(lexer, lexer->lexbuf[i]);
    }

    if (element->type == StartEndTag)
        AddByte(lexer, '/');

    AddByte(lexer, '>');
    node->end = lexer->lexsize;

    return node;
}
#endif /* 0 */

/* Only true for text nodes. */
Bool IsBlank(Lexer *lexer, Node *node)
{
    Bool isBlank = nodeIsText(node);
    if ( isBlank )
        isBlank = ( node->end == node->start ||       /* Zero length */
                    ( node->end == node->start+1      /* or one blank. */
                      && lexer->lexbuf[node->start] == ' ' ) );
    return isBlank;
}

/*
  This maps 
       <p>hello<em> world</em>
  to
       <p>hello <em>world</em>

  Trims initial space, by moving it before the
  start tag, or if this element is the first in
  parent's content, then by discarding the space
*/
static void TrimInitialSpace( TidyDocImpl* doc, Node *element, Node *text )
{
    Lexer* lexer = doc->lexer;
    Node *prev, *node;

    if ( nodeIsText(text) && 
         lexer->lexbuf[text->start] == ' ' && 
         text->start < text->end )
    {
        if ( (element->tag->model & CM_INLINE) &&
             !(element->tag->model & CM_FIELD) )
        {
            prev = element->prev;

            if (nodeIsText(prev))
            {
                if (prev->end == 0 || lexer->lexbuf[prev->end - 1] != ' ')
                    lexer->lexbuf[(prev->end)++] = ' ';

                ++(element->start);
            }
            else /* create new node */
            {
                node = NewNode(lexer);
                node->start = (element->start)++;
                node->end = element->start;
                lexer->lexbuf[node->start] = ' ';
                InsertNodeBeforeElement(element ,node);
            }
        }

        /* discard the space in current node */
        ++(text->start);
    }
}

static Bool IsPreDescendant(Node* node)
{
    Node *parent = node->parent;

    while (parent)
    {
        if (parent->tag && parent->tag->parser == ParsePre)
            return yes;

        parent = parent->parent;
    }

    return no;
}

static Bool CleanTrailingWhitespace(TidyDocImpl* doc, Node* node)
{
    Node* next;

    if (!nodeIsText(node))
        return no;

    if (node->parent->type == DocTypeTag)
        return no;

    if (IsPreDescendant(node))
        return no;

    if (node->parent->tag->parser == ParseScript)
        return no;

    next = node->next;

    /* <p>... </p> */
    if (!next && !nodeHasCM(node->parent, CM_INLINE))
        return yes;

    /* <div><small>... </small><h3>...</h3></div> */
    if (!next && node->parent->next && !nodeHasCM(node->parent->next, CM_INLINE))
        return yes;

    if (!next)
        return no;

    if (nodeIsBR(next))
        return yes;

    if (nodeHasCM(next, CM_INLINE))
        return no;

    /* <a href='/'>...</a> <p>...</p> */
    if (next->type == StartTag)
        return yes;

    /* <strong>...</strong> <hr /> */
    if (next->type == StartEndTag)
        return yes;

    /* evil adjacent text nodes, Tidy should not generate these :-( */
    if (nodeIsText(next) && next->start < next->end
        && IsWhite(doc->lexer->lexbuf[next->start]))
        return yes;

    return no;
}

static Bool CleanLeadingWhitespace(TidyDocImpl* ARG_UNUSED(doc), Node* node)
{
    if (!nodeIsText(node))
        return no;

    if (node->parent->type == DocTypeTag)
        return no;

    if (IsPreDescendant(node))
        return no;

    if (node->parent->tag->parser == ParseScript)
        return no;

    /* <p>...<br> <em>...</em>...</p> */
    if (nodeIsBR(node->prev))
        return yes;

    /* <p> ...</p> */
    if (node->prev == NULL && !nodeHasCM(node->parent, CM_INLINE))
        return yes;

    /* <h4>...</h4> <em>...</em> */
    if (node->prev && !nodeHasCM(node->prev, CM_INLINE) &&
        nodeIsElement(node->prev))
        return yes;

    /* <p><span> ...</span></p> */
    if (!node->prev && !node->parent->prev && !nodeHasCM(node->parent->parent, CM_INLINE))
        return yes;

    return no;
}

static void CleanSpaces(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (nodeIsText(node) && CleanLeadingWhitespace(doc, node))
            while (node->start < node->end && IsWhite(doc->lexer->lexbuf[node->start]))
                ++(node->start);

        if (nodeIsText(node) && CleanTrailingWhitespace(doc, node))
            while (node->end > node->start && IsWhite(doc->lexer->lexbuf[node->end - 1]))
                --(node->end);

        if (nodeIsText(node) && !(node->start < node->end))
        {
            RemoveNode(node);
            FreeNode(doc, node);
            node = next;

            continue;
        }

        if (node->content)
            CleanSpaces(doc, node->content);

        node = next;
    }
}

/* 
  Move initial and trailing space out.
  This routine maps:

       hello<em> world</em>
  to
       hello <em>world</em>
  and
       <em>hello </em><strong>world</strong>
  to
       <em>hello</em> <strong>world</strong>
*/
static void TrimSpaces( TidyDocImpl* doc, Node *element)
{
    Node* text = element->content;

    if (nodeIsPRE(element) || IsPreDescendant(element))
        return;

    if (nodeIsText(text))
        TrimInitialSpace(doc, element, text);

    text = element->last;

    if (nodeIsText(text))
        TrimTrailingSpace(doc, element, text);
}

Bool DescendantOf( Node *element, TidyTagId tid )
{
    Node *parent;
    for ( parent = element->parent;
          parent != NULL;
          parent = parent->parent )
    {
        if ( TagIsId(parent, tid) )
            return yes;
    }
    return no;
}

static Bool InsertMisc(Node *element, Node *node)
{
    if (node->type == CommentTag ||
        node->type == ProcInsTag ||
        node->type == CDATATag ||
        node->type == SectionTag ||
        node->type == AspTag ||
        node->type == JsteTag ||
        node->type == PhpTag )
    {
        InsertNodeAtEnd(element, node);
        return yes;
    }

    if ( node->type == XmlDecl )
    {
        Node* root = element;
        while ( root && root->parent )
            root = root->parent;
        if ( root )
        {
          InsertNodeAtStart( root, node );
          return yes;
        }
    }

    /* Declared empty tags seem to be slipping through
    ** the cracks.  This is an experiment to figure out
    ** a decent place to pick them up.
    */
    if ( node->tag &&
         nodeIsElement(node) &&
         nodeCMIsEmpty(node) && TagId(node) == TidyTag_UNKNOWN &&
         (node->tag->versions & VERS_PROPRIETARY) != 0 )
    {
        InsertNodeAtEnd(element, node);
        return yes;
    }

    return no;
}


static void ParseTag( TidyDocImpl* doc, Node *node, uint mode )
{
    Lexer* lexer = doc->lexer;
    /*
       Fix by GLP 2000-12-21.  Need to reset insertspace if this 
       is both a non-inline and empty tag (base, link, meta, isindex, hr, area).
    */
    if (node->tag->model & CM_EMPTY)
    {
        lexer->waswhite = no;
        if (node->tag->parser == NULL)
            return;
    }
    else if (!(node->tag->model & CM_INLINE))
        lexer->insertspace = no;

    if (node->tag->parser == NULL)
        return;

    if (node->type == StartEndTag)
        return;

    (*node->tag->parser)( doc, node, mode );
}

/*
 the doctype has been found after other tags,
 and needs moving to before the html element
*/
static void InsertDocType( TidyDocImpl* doc, Node *element, Node *doctype )
{
    Node* existing = FindDocType( doc );
    if ( existing )
    {
        ReportError(doc, element, doctype, DISCARDING_UNEXPECTED );
        FreeNode( doc, doctype );
    }
    else
    {
        ReportError(doc, element, doctype, DOCTYPE_AFTER_TAGS );
        while ( !nodeIsHTML(element) )
            element = element->parent;
        InsertNodeBeforeElement( element, doctype );
    }
}

/*
 move node to the head, where element is used as starting
 point in hunt for head. normally called during parsing
*/
static void MoveToHead( TidyDocImpl* doc, Node *element, Node *node )
{
    Node *head;

    RemoveNode( node );  /* make sure that node is isolated */

    if ( nodeIsElement(node) )
    {
        ReportError(doc, element, node, TAG_NOT_ALLOWED_IN );

        head = FindHEAD(doc);
        assert(head != NULL);

        InsertNodeAtEnd(head, node);

        if ( node->tag->parser )
            ParseTag( doc, node, IgnoreWhitespace );
    }
    else
    {
        ReportError(doc, element, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node );
    }
}

/* moves given node to end of body element */
static void MoveNodeToBody( TidyDocImpl* doc, Node* node )
{
    Node* body = FindBody( doc );
    if ( body )
    {
        RemoveNode( node );
        InsertNodeAtEnd( body, node );
    }
}

/*
   element is node created by the lexer
   upon seeing the start tag, or by the
   parser when the start tag is inferred
*/
void ParseBlock( TidyDocImpl* doc, Node *element, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node;
    Bool checkstack = yes;
    uint istackbase = 0;

    if ( element->tag->model & CM_EMPTY )
        return;

    if ( nodeIsFORM(element) && 
         DescendantOf(element, TidyTag_FORM) )
        ReportError(doc, element, NULL, ILLEGAL_NESTING );

    /*
     InlineDup() asks the lexer to insert inline emphasis tags
     currently pushed on the istack, but take care to avoid
     propagating inline emphasis inside OBJECT or APPLET.
     For these elements a fresh inline stack context is created
     and disposed of upon reaching the end of the element.
     They thus behave like table cells in this respect.
    */
    if (element->tag->model & CM_OBJECT)
    {
        istackbase = lexer->istackbase;
        lexer->istackbase = lexer->istacksize;
    }

    if (!(element->tag->model & CM_MIXED))
        InlineDup( doc, NULL );

    mode = IgnoreWhitespace;

    while ((node = GetToken(doc, mode /*MixedContent*/)) != NULL)
    {
        /* end tag for this element */
        if (node->type == EndTag && node->tag &&
            (node->tag == element->tag || element->was == node->tag))
        {
            FreeNode( doc, node );

            if (element->tag->model & CM_OBJECT)
            {
                /* pop inline stack */
                while (lexer->istacksize > lexer->istackbase)
                    PopInline( doc, NULL );
                lexer->istackbase = istackbase;
            }

            element->closed = yes;
            TrimSpaces( doc, element );
            return;
        }

        if ( nodeIsBODY( node ) && DescendantOf( element, TidyTag_HEAD ))
        {
            /*  If we're in the HEAD, close it before proceeding.
                This is an extremely rare occurance, but has been observed.
            */
            UngetToken( doc );
            break;
        }

        if ( nodeIsHTML(node) || nodeIsHEAD(node) || nodeIsBODY(node) )
        {
            if ( nodeIsElement(node) )
                ReportError(doc, element, node, DISCARDING_UNEXPECTED );
            FreeNode( doc, node );
            continue;
        }


        if (node->type == EndTag)
        {
            if (node->tag == NULL)
            {
                ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                FreeNode( doc, node );
                continue;
            }
            else if ( nodeIsBR(node) )
                node->type = StartTag;
            else if ( nodeIsP(node) )
            {
                /* Cannot have a block inside a paragraph, so no checking
                   for an ancestor is necessary -- but we _can_ have
                   paragraphs inside a block, so change it to an implicit
                   empty paragraph, to be dealt with according to the user's
                   options
                */
                node->type = StartEndTag;
                node->implicit = yes;
#if OBSOLETE
                CoerceNode(doc, node, TidyTag_BR, no, no);
                FreeAttrs( doc, node ); /* discard align attribute etc. */
                InsertNodeAtEnd( element, node );
                node = InferredTag(doc, TidyTag_BR);
#endif
            }
            else if (DescendantOf( element, node->tag->id ))
            {
                /* 
                  if this is the end tag for an ancestor element
                  then infer end tag for this element
                */
                UngetToken( doc );
                break;
#if OBSOLETE
                Node *parent;
                for ( parent = element->parent;
                      parent != NULL; 
                      parent = parent->parent )
                {
                    if (node->tag == parent->tag)
                    {
                        if (!(element->tag->model & CM_OPT))
                            ReportError(doc, element, node, MISSING_ENDTAG_BEFORE );

                        UngetToken( doc );

                        if (element->tag->model & CM_OBJECT)
                        {
                            /* pop inline stack */
                            while (lexer->istacksize > lexer->istackbase)
                                PopInline( doc, NULL );
                            lexer->istackbase = istackbase;
                        }

                        TrimSpaces( doc, element );
                        return;
                    }
                }
#endif
            }
            else
            {
                /* special case </tr> etc. for stuff moved in front of table */
                if ( lexer->exiled
                     && node->tag->model
                     && (node->tag->model & CM_TABLE) )
                {
                    UngetToken( doc );
                    TrimSpaces( doc, element );
                    return;
                }
            }
        }

        /* mixed content model permits text */
        if (nodeIsText(node))
        {
            if ( checkstack )
            {
                checkstack = no;
                if (!(element->tag->model & CM_MIXED))
                {
                    if ( InlineDup(doc, node) > 0 )
                        continue;
                }
            }

            InsertNodeAtEnd(element, node);
            mode = MixedContent;

            /*
              HTML4 strict doesn't allow mixed content for
              elements with %block; as their content model
            */
            /*
              But only body, map, blockquote, form and
              noscript have content model %block;
            */
            if ( nodeIsBODY(element)       ||
                 nodeIsMAP(element)        ||
                 nodeIsBLOCKQUOTE(element) ||
                 nodeIsFORM(element)       ||
                 nodeIsNOSCRIPT(element) )
                ConstrainVersion( doc, ~VERS_HTML40_STRICT );
            continue;
        }

        if ( InsertMisc(element, node) )
            continue;

        /* allow PARAM elements? */
        if ( nodeIsPARAM(node) )
        {
            if ( nodeHasCM(element, CM_PARAM) && nodeIsElement(node) )
            {
                InsertNodeAtEnd(element, node);
                continue;
            }

            /* otherwise discard it */
            ReportError(doc, element, node, DISCARDING_UNEXPECTED );
            FreeNode( doc, node );
            continue;
        }

        /* allow AREA elements? */
        if ( nodeIsAREA(node) )
        {
            if ( nodeIsMAP(element) && nodeIsElement(node) )
            {
                InsertNodeAtEnd(element, node);
                continue;
            }

            /* otherwise discard it */
            ReportError(doc, element, node, DISCARDING_UNEXPECTED );
            FreeNode( doc, node );
            continue;
        }

        /* ignore unknown start/end tags */
        if ( node->tag == NULL )
        {
            ReportError(doc, element, node, DISCARDING_UNEXPECTED );
            FreeNode( doc, node );
            continue;
        }

        /*
          Allow CM_INLINE elements here.

          Allow CM_BLOCK elements here unless
          lexer->excludeBlocks is yes.

          LI and DD are special cased.

          Otherwise infer end tag for this element.
        */

        if ( !nodeHasCM(node, CM_INLINE) )
        {
            if ( !nodeIsElement(node) )
            {
                if ( nodeIsFORM(node) )
                    BadForm( doc );

                ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                FreeNode( doc, node );
                continue;
            }

            /* #427671 - Fix by Randy Waki - 10 Aug 00 */
            /*
             If an LI contains an illegal FRAME, FRAMESET, OPTGROUP, or OPTION
             start tag, discard the start tag and let the subsequent content get
             parsed as content of the enclosing LI.  This seems to mimic IE and
             Netscape, and avoids an infinite loop: without this check,
             ParseBlock (which is parsing the LI's content) and ParseList (which
             is parsing the LI's parent's content) repeatedly defer to each
             other to parse the illegal start tag, each time inferring a missing
             </li> or <li> respectively.

             NOTE: This check is a bit fragile.  It specifically checks for the
             four tags that happen to weave their way through the current series
             of tests performed by ParseBlock and ParseList to trigger the
             infinite loop.
            */
            if ( nodeIsLI(element) )
            {
                if ( nodeIsFRAME(node)    ||
                     nodeIsFRAMESET(node) ||
                     nodeIsOPTGROUP(node) ||
                     nodeIsOPTION(node) )
                {
                    ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                    FreeNode( doc, node );  /* DSR - 27Apr02 avoid memory leak */
                    continue;
                }
            }

            if ( nodeIsTD(element) || nodeIsTH(element) )
            {
                /* if parent is a table cell, avoid inferring the end of the cell */

                if ( nodeHasCM(node, CM_HEAD) )
                {
                    MoveToHead( doc, element, node );
                    continue;
                }

                if ( nodeHasCM(node, CM_LIST) )
                {
                    UngetToken( doc );
                    node = InferredTag(doc, TidyTag_UL);
                    /* AddClass( doc, node, "noindent" ); */
                    lexer->excludeBlocks = yes;
                }
                else if ( nodeHasCM(node, CM_DEFLIST) )
                {
                    UngetToken( doc );
                    node = InferredTag(doc, TidyTag_DL);
                    lexer->excludeBlocks = yes;
                }

                /* infer end of current table cell */
                if ( !nodeHasCM(node, CM_BLOCK) )
                {
                    UngetToken( doc );
                    TrimSpaces( doc, element );
                    return;
                }
            }
            else if ( nodeHasCM(node, CM_BLOCK) )
            {
                if ( lexer->excludeBlocks )
                {
                    if ( !nodeHasCM(element, CM_OPT) )
                        ReportError(doc, element, node, MISSING_ENDTAG_BEFORE );

                    UngetToken( doc );

                    if ( nodeHasCM(element, CM_OBJECT) )
                        lexer->istackbase = istackbase;

                    TrimSpaces( doc, element );
                    return;
                }
            }
            else /* things like list items */
            {
                if (node->tag->model & CM_HEAD)
                {
                    MoveToHead( doc, element, node );
                    continue;
                }

                /*
                 special case where a form start tag
                 occurs in a tr and is followed by td or th
                */

                if ( nodeIsFORM(element) &&
                     nodeIsTD(element->parent) &&
                     element->parent->implicit )
                {
                    if ( nodeIsTD(node) )
                    {
                        ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                        FreeNode( doc, node );
                        continue;
                    }

                    if ( nodeIsTH(node) )
                    {
                        ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                        FreeNode( doc, node );
                        node = element->parent;
                        MemFree(node->element);
                        node->element = tmbstrdup("th");
                        node->tag = LookupTagDef( TidyTag_TH );
                        continue;
                    }
                }

                if ( !nodeHasCM(element, CM_OPT) && !element->implicit )
                    ReportError(doc, element, node, MISSING_ENDTAG_BEFORE );

                UngetToken( doc );

                if ( nodeHasCM(node, CM_LIST) )
                {
                    if ( element->parent && element->parent->tag &&
                         element->parent->tag->parser == ParseList )
                    {
                        TrimSpaces( doc, element );
                        return;
                    }

                    node = InferredTag(doc, TidyTag_UL);
                    /* AddClass( doc, node, "noindent" ); */
                }
                else if ( nodeHasCM(node, CM_DEFLIST) )
                {
                    if ( nodeIsDL(element->parent) )
                    {
                        TrimSpaces( doc, element );
                        return;
                    }

                    node = InferredTag(doc, TidyTag_DL);
                }
                else if ( nodeHasCM(node, CM_TABLE) || nodeHasCM(node, CM_ROW) )
                {
                    node = InferredTag(doc, TidyTag_TABLE);
                }
                else if ( nodeHasCM(element, CM_OBJECT) )
                {
                    /* pop inline stack */
                    while ( lexer->istacksize > lexer->istackbase )
                        PopInline( doc, NULL );
                    lexer->istackbase = istackbase;
                    TrimSpaces( doc, element );
                    return;

                }
                else
                {
                    TrimSpaces( doc, element );
                    return;
                }
            }
        }

        /* parse known element */
        if (nodeIsElement(node))
        {
            if (node->tag->model & CM_INLINE)
            {
                if (checkstack && !node->implicit)
                {
                    checkstack = no;

                    if (!(element->tag->model & CM_MIXED)) /* #431731 - fix by Randy Waki 25 Dec 00 */
                    {
                        if ( InlineDup(doc, node) > 0 )
                            continue;
                    }
                }

                mode = MixedContent;
            }
            else
            {
                checkstack = yes;
                mode = IgnoreWhitespace;
            }

            /* trim white space before <br> */
            if ( nodeIsBR(node) )
                TrimSpaces( doc, element );

            InsertNodeAtEnd(element, node);
            
            if (node->implicit)
                ReportError(doc, element, node, INSERTING_TAG );

            ParseTag( doc, node, IgnoreWhitespace /*MixedContent*/ );
            continue;
        }

        /* discard unexpected tags */
        if (node->type == EndTag)
            PopInline( doc, node );  /* if inline end tag */

        ReportError(doc, element, node, DISCARDING_UNEXPECTED );
        FreeNode( doc, node );
        continue;
    }

    if (!(element->tag->model & CM_OPT))
        ReportError(doc, element, node, MISSING_ENDTAG_FOR);

    if (element->tag->model & CM_OBJECT)
    {
        /* pop inline stack */
        while ( lexer->istacksize > lexer->istackbase )
            PopInline( doc, NULL );
        lexer->istackbase = istackbase;
    }

    TrimSpaces( doc, element );
}

void ParseInline( TidyDocImpl* doc, Node *element, uint mode )
{
    Lexer* lexer = doc->lexer;
    Node *node, *parent;

    if (element->tag->model & CM_EMPTY)
        return;

    /*
     ParseInline is used for some block level elements like H1 to H6
     For such elements we need to insert inline emphasis tags currently
     on the inline stack. For Inline elements, we normally push them
     onto the inline stack provided they aren't implicit or OBJECT/APPLET.
     This test is carried out in PushInline and PopInline, see istack.c

     InlineDup(...) is not called for elements with a CM_MIXED (inline and
     block) content model, e.g. <del> or <ins>, otherwise constructs like 

       <p>111<a name='foo'>222<del>333</del>444</a>555</p>
       <p>111<span>222<del>333</del>444</span>555</p>
       <p>111<em>222<del>333</del>444</em>555</p>

     will get corrupted.
    */
    if ((nodeHasCM(element, CM_BLOCK) || nodeIsDT(element)) &&
        !nodeHasCM(element, CM_MIXED))
        InlineDup(doc, NULL);
    else if (nodeHasCM(element, CM_INLINE))
        PushInline(doc, element);

    if ( nodeIsNOBR(element) )
        doc->badLayout |= USING_NOBR;
    else if ( nodeIsFONT(element) )
        doc->badLayout |= USING_FONT;

    /* Inline elements may or may not be within a preformatted element */
    if (mode != Preformatted)
        mode = MixedContent;

    while ((node = GetToken(doc, mode)) != NULL)
    {
        /* end tag for current element */
        if (node->tag == element->tag && node->type == EndTag)
        {
            if (element->tag->model & CM_INLINE)
                PopInline( doc, node );

            FreeNode( doc, node );

            if (!(mode & Preformatted))
                TrimSpaces(doc, element);

            /*
             if a font element wraps an anchor and nothing else
             then move the font element inside the anchor since
             otherwise it won't alter the anchor text color
            */
            if ( nodeIsFONT(element) && 
                 element->content && element->content == element->last )
            {
                Node *child = element->content;

                if ( nodeIsA(child) )
                {
                    child->parent = element->parent;
                    child->next = element->next;
                    child->prev = element->prev;

                    element->next = NULL;
                    element->prev = NULL;
                    element->parent = child;

                    element->content = child->content;
                    element->last = child->last;
                    child->content = element;

                    FixNodeLinks(child);
                    FixNodeLinks(element);
                }
            }

            element->closed = yes;
            TrimSpaces( doc, element );
            return;
        }

        /* <u>...<u>  map 2nd <u> to </u> if 1st is explicit */
        /* otherwise emphasis nesting is probably unintentional */
        /* big, small, sub, sup have cumulative effect to leave them alone */
        if ( node->type == StartTag
             && node->tag == element->tag
             && IsPushed( doc, node )
             && !node->implicit
             && !element->implicit
             && node->tag && (node->tag->model & CM_INLINE)
             && !nodeIsA(node)
             && !nodeIsFONT(node)
             && !nodeIsBIG(node)
             && !nodeIsSMALL(node)
             && !nodeIsSUB(node)
             && !nodeIsSUP(node)
             && !nodeIsQ(node)
             && !nodeIsSPAN(node)
           )
        {
            if (element->content != NULL && node->attributes == NULL)
            {
                ReportWarning(doc, element, node, COERCE_TO_ENDTAG_WARN);
                node->type = EndTag;
                UngetToken(doc);
                continue;
            }

            if (node->attributes == NULL || element->attributes == NULL)
                ReportWarning(doc, element, node, NESTED_EMPHASIS);
        }
        else if ( IsPushed(doc, node) && node->type == StartTag && 
                  nodeIsQ(node) )
        {
            ReportWarning(doc, element, node, NESTED_QUOTATION);
        }

        if ( nodeIsText(node) )
        {
            /* only called for 1st child */
            if ( element->content == NULL && !(mode & Preformatted) )
                TrimSpaces( doc, element );

            if ( node->start >= node->end )
            {
                FreeNode( doc, node );
                continue;
            }

            InsertNodeAtEnd(element, node);
            continue;
        }

        /* mixed content model so allow text */
        if (InsertMisc(element, node))
            continue;

        /* deal with HTML tags */
        if ( nodeIsHTML(node) )
        {
            if ( nodeIsElement(node) )
            {
                ReportError(doc, element, node, DISCARDING_UNEXPECTED );
                FreeNode( doc, node );
                continue;
            }

            /* otherwise infer end of inline element */
            UngetToken( doc );

            if (!(mode & Preformatted))
                TrimSpaces(doc, element);

            return;
        }

        /* within <dt> or <pre> map <p> to <br> */
        if ( nodeIsP(node) &&
             node->type == StartTag &&
             ( (mode & Preformatted) ||
               nodeIsDT(element) || 
               DescendantOf(element, TidyTag_DT )
             )
           )
        {
            node->tag = LookupTagDef( TidyTag_BR );
            MemFree(node->element);
            node->element = tmbstrdup("br");
            TrimSpaces(doc, element);
            InsertNodeAtEnd(element, node);
            continue;
        }

        /* <p> allowed within <address> in HTML 4.01 Transitional */
        if ( nodeIsP(node) &&
             node->type == StartTag &&
             nodeIsADDRESS(element) )
        {
            ConstrainVersion( doc, ~VERS_HTML40_STRICT );
            InsertNodeAtEnd(element, node);
            (*node->tag->parser)( doc, node, mode );
            continue;
        }

        /* ignore unknown and PARAM tags */
        if ( node->tag == NULL || nodeIsPARAM(node) )
        {
            ReportError(doc, element, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node );
            continue;
        }

        if ( nodeIsBR(node) && node->type == EndTag )
            node->type = StartTag;

        if ( node->type == EndTag )
        {
           /* coerce </br> to <br> */
           if ( nodeIsBR(node) )
                node->type = StartTag;
           else if ( nodeIsP(node) )
           {
               /* coerce unmatched </p> to <br><br> */
                if ( !DescendantOf(element, TidyTag_P) )
                {
                    CoerceNode(doc, node, TidyTag_BR, no, no);
                    TrimSpaces( doc, element );
                    InsertNodeAtEnd( element, node );
                    node = InferredTag(doc, TidyTag_BR);
                    InsertNodeAtEnd( element, node ); /* todo: check this */
                    continue;
                }
           }
           else if ( nodeHasCM(node, CM_INLINE)
                     && !nodeIsA(node)
                     && !nodeHasCM(node, CM_OBJECT)
                     && nodeHasCM(element, CM_INLINE) )
            {
                /* allow any inline end tag to end current element */
                PopInline( doc, element );

                if ( !nodeIsA(element) )
                {
                    if ( nodeIsA(node) && node->tag != element->tag )
                    {
                       ReportError(doc, element, node, MISSING_ENDTAG_BEFORE );
                       UngetToken( doc );
                    }
                    else
                    {
                        ReportError(doc, element, node, NON_MATCHING_ENDTAG);
                        FreeNode( doc, node);
                    }

                    if (!(mode & Preformatted))
                        TrimSpaces(doc, element);

                    return;
                }

                /* if parent is <a> then discard unexpected inline end tag */
                ReportError(doc, element, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }  /* special case </tr> etc. for stuff moved in front of table */
            else if ( lexer->exiled
                      && node->tag->model
                      && (node->tag->model & CM_TABLE) )
            {
                UngetToken( doc );
                TrimSpaces(doc, element);
                return;
            }
        }

        /* allow any header tag to end current header */
        if ( nodeHasCM(node, CM_HEADING) && nodeHasCM(element, CM_HEADING) )
        {

            if ( node->tag == element->tag )
            {
                ReportError(doc, element, node, NON_MATCHING_ENDTAG );
                FreeNode( doc, node);
            }
            else
            {
                ReportError(doc, element, node, MISSING_ENDTAG_BEFORE );
                UngetToken( doc );
            }

            if (!(mode & Preformatted))
                TrimSpaces(doc, element);

            return;
        }

        /*
           an <A> tag to ends any open <A> element
           but <A href=...> is mapped to </A><A href=...>
        */
        /* #427827 - fix by Randy Waki and Bjoern Hoehrmann 23 Aug 00 */
        /* if (node->tag == doc->tags.tag_a && !node->implicit && IsPushed(doc, node)) */
        if ( nodeIsA(node) && !node->implicit && 
             (nodeIsA(element) || DescendantOf(element, TidyTag_A)) )
        {
            /* coerce <a> to </a> unless it has some attributes */
            /* #427827 - fix by Randy Waki and Bjoern Hoehrmann 23 Aug 00 */
            /* other fixes by Dave Raggett */
            /* if (node->attributes == NULL) */
            if (node->type != EndTag && node->attributes == NULL)
            {
                node->type = EndTag;
                ReportError(doc, element, node, COERCE_TO_ENDTAG);
                /* PopInline( doc, node ); */
                UngetToken( doc );
                continue;
            }

            UngetToken( doc );
            ReportError(doc, element, node, MISSING_ENDTAG_BEFORE);
            /* PopInline( doc, element ); */

            if (!(mode & Preformatted))
                TrimSpaces(doc, element);

            return;
        }

        if (element->tag->model & CM_HEADING)
        {
            if ( nodeIsCENTER(node) || nodeIsDIV(node) )
            {
                if (!nodeIsElement(node))
                {
                    ReportError(doc, element, node, DISCARDING_UNEXPECTED);
                    FreeNode( doc, node);
                    continue;
                }

                ReportError(doc, element, node, TAG_NOT_ALLOWED_IN);

                /* insert center as parent if heading is empty */
                if (element->content == NULL)
                {
                    InsertNodeAsParent(element, node);
                    continue;
                }

                /* split heading and make center parent of 2nd part */
                InsertNodeAfterElement(element, node);

                if (!(mode & Preformatted))
                    TrimSpaces(doc, element);

                element = CloneNode( doc, element );
                InsertNodeAtEnd(node, element);
                continue;
            }

            if ( nodeIsHR(node) )
            {
                if ( !nodeIsElement(node) )
                {
                    ReportError(doc, element, node, DISCARDING_UNEXPECTED);
                    FreeNode( doc, node);
                    continue;
                }

                ReportError(doc, element, node, TAG_NOT_ALLOWED_IN);

                /* insert hr before heading if heading is empty */
                if (element->content == NULL)
                {
                    InsertNodeBeforeElement(element, node);
                    continue;
                }

                /* split heading and insert hr before 2nd part */
                InsertNodeAfterElement(element, node);

                if (!(mode & Preformatted))
                    TrimSpaces(doc, element);

                element = CloneNode( doc, element );
                InsertNodeAfterElement(node, element);
                continue;
            }
        }

        if ( nodeIsDT(element) )
        {
            if ( nodeIsHR(node) )
            {
                Node *dd;
                if ( !nodeIsElement(node) )
                {
                    ReportError(doc, element, node, DISCARDING_UNEXPECTED);
                    FreeNode( doc, node);
                    continue;
                }

                ReportError(doc, element, node, TAG_NOT_ALLOWED_IN);
                dd = InferredTag(doc, TidyTag_DD);

                /* insert hr within dd before dt if dt is empty */
                if (element->content == NULL)
                {
                    InsertNodeBeforeElement(element, dd);
                    InsertNodeAtEnd(dd, node);
                    continue;
                }

                /* split dt and insert hr within dd before 2nd part */
                InsertNodeAfterElement(element, dd);
                InsertNodeAtEnd(dd, node);

                if (!(mode & Preformatted))
                    TrimSpaces(doc, element);

                element = CloneNode( doc, element );
                InsertNodeAfterElement(dd, element);
                continue;
            }
        }


        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            for (parent = element->parent;
                    parent != NULL; parent = parent->parent)
            {
                if (node->tag == parent->tag)
                {
                    if (!(element->tag->model & CM_OPT) && !element->implicit)
                        ReportError(doc, element, node, MISSING_ENDTAG_BEFORE);

                    PopInline( doc, element );
                    UngetToken( doc );

                    if (!(mode & Preformatted))
                        TrimSpaces(doc, element);

                    return;
                }
            }
        }

        /* block level tags end this element */
        if (!(node->tag->model & CM_INLINE) &&
            !(element->tag->model & CM_MIXED))
        {
            if ( !nodeIsElement(node) )
            {
                ReportError(doc, element, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if (!(element->tag->model & CM_OPT))
                ReportError(doc, element, node, MISSING_ENDTAG_BEFORE);

            if (node->tag->model & CM_HEAD && !(node->tag->model & CM_BLOCK))
            {
                MoveToHead(doc, element, node);
                continue;
            }

            /*
               prevent anchors from propagating into block tags
               except for headings h1 to h6
            */
            if ( nodeIsA(element) )
            {
                if (node->tag && !(node->tag->model & CM_HEADING))
                    PopInline( doc, element );
                else if (!(element->content))
                {
                    DiscardElement( doc, element );
                    UngetToken( doc );
                    return;
                }
            }

            UngetToken( doc );

            if (!(mode & Preformatted))
                TrimSpaces(doc, element);

            return;
        }

        /* parse inline element */
        if (nodeIsElement(node))
        {
            if (node->implicit)
                ReportError(doc, element, node, INSERTING_TAG);

            /* trim white space before <br> */
            if ( nodeIsBR(node) )
                TrimSpaces(doc, element);
            
            InsertNodeAtEnd(element, node);
            ParseTag(doc, node, mode);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, element, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node );
        continue;
    }

    if (!(element->tag->model & CM_OPT))
        ReportError(doc, element, node, MISSING_ENDTAG_FOR);

}

void ParseEmpty(TidyDocImpl* doc, Node *element, uint mode)
{
    Lexer* lexer = doc->lexer;
    if ( lexer->isvoyager )
    {
        Node *node = GetToken( doc, mode);
        if ( node )
        {
            if ( !(node->type == EndTag && node->tag == element->tag) )
            {
                ReportError(doc, element, node, ELEMENT_NOT_EMPTY);
                UngetToken( doc );
            }
            else
            {
                FreeNode( doc, node );
            }
        }
    }
}

void ParseDefList(TidyDocImpl* doc, Node *list, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node, *parent;

    if (list->tag->model & CM_EMPTY)
        return;

    lexer->insert = NULL;  /* defer implicit inline start tags */

    while ((node = GetToken( doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == list->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            list->closed = yes;
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(list, node))
            continue;

        if (nodeIsText(node))
        {
            UngetToken( doc );
            node = InferredTag(doc, TidyTag_DT);
            ReportError(doc, list, node, MISSING_STARTTAG);
        }

        if (node->tag == NULL)
        {
            ReportError(doc, list, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            if ( nodeIsFORM(node) )
            {
                BadForm( doc );
                ReportError(doc, list, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node );
                continue;
            }

            for (parent = list->parent;
                    parent != NULL; parent = parent->parent)
            {
               /* Do not match across BODY to avoid infinite loop
                  between ParseBody and this parser,
                  See http://tidy.sf.net/bug/1098012. */
                if (nodeIsBODY(parent))
                    break;
                if (node->tag == parent->tag)
                {
                    ReportError(doc, list, node, MISSING_ENDTAG_BEFORE);

                    UngetToken( doc );
                    return;
                }
            }
        }

        /* center in a dt or a dl breaks the dl list in two */
        if ( nodeIsCENTER(node) )
        {
            if (list->content)
                InsertNodeAfterElement(list, node);
            else /* trim empty dl list */
            {
                InsertNodeBeforeElement(list, node);

/* #540296 tidy dumps with empty definition list */
#if 0
                DiscardElement(list);
#endif
            }

            /* #426885 - fix by Glenn Carroll 19 Apr 00, and
                         Gary Dechaines 11 Aug 00 */
            /* ParseTag can destroy node, if it finds that
             * this <center> is followed immediately by </center>.
             * It's awkward but necessary to determine if this
             * has happened.
             */
            parent = node->parent;

            /* and parse contents of center */
            lexer->excludeBlocks = no;
            ParseTag( doc, node, mode);
            lexer->excludeBlocks = yes;

            /* now create a new dl element,
             * unless node has been blown away because the
             * center was empty, as above.
             */
            if (parent->last == node)
            {
                list = InferredTag(doc, TidyTag_DL);
                InsertNodeAfterElement(node, list);
            }
            continue;
        }

        if ( !(nodeIsDT(node) || nodeIsDD(node)) )
        {
            UngetToken( doc );

            if (!(node->tag->model & (CM_BLOCK | CM_INLINE)))
            {
                ReportError(doc, list, node, TAG_NOT_ALLOWED_IN);
                return;
            }

            /* if DD appeared directly in BODY then exclude blocks */
            if (!(node->tag->model & CM_INLINE) && lexer->excludeBlocks)
                return;

            node = InferredTag(doc, TidyTag_DD);
            ReportError(doc, list, node, MISSING_STARTTAG);
        }

        if (node->type == EndTag)
        {
            ReportError(doc, list, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }
        
        /* node should be <DT> or <DD>*/
        InsertNodeAtEnd(list, node);
        ParseTag( doc, node, IgnoreWhitespace);
    }

    ReportError(doc, list, node, MISSING_ENDTAG_FOR);
}

void ParseList(TidyDocImpl* doc, Node *list, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node, *parent;

    if (list->tag->model & CM_EMPTY)
        return;

    lexer->insert = NULL;  /* defer implicit inline start tags */

    while ((node = GetToken( doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == list->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            list->closed = yes;
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(list, node))
            continue;

        if (node->type != TextNode && node->tag == NULL)
        {
            ReportError(doc, list, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            if ( nodeIsFORM(node) )
            {
                BadForm( doc );
                ReportError(doc, list, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node );
                continue;
            }

            if (node->tag && node->tag->model & CM_INLINE)
            {
                ReportError(doc, list, node, DISCARDING_UNEXPECTED);
                PopInline( doc, node );
                FreeNode( doc, node);
                continue;
            }

            for ( parent = list->parent;
                  parent != NULL; parent = parent->parent )
            {
               /* Do not match across BODY to avoid infinite loop
                  between ParseBody and this parser,
                  See http://tidy.sf.net/bug/1053626. */
                if (nodeIsBODY(parent))
                    break;
                if (node->tag == parent->tag)
                {
                    ReportError(doc, list, node, MISSING_ENDTAG_BEFORE);
                    UngetToken( doc );
                    return;
                }
            }

            ReportError(doc, list, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        if ( !nodeIsLI(node) )
        {
            UngetToken( doc );

            if (node->tag && (node->tag->model & CM_BLOCK) && lexer->excludeBlocks)
            {
                ReportError(doc, list, node, MISSING_ENDTAG_BEFORE);
                return;
            }

            node = InferredTag(doc, TidyTag_LI);
            AddAttribute( doc, node, "style", "list-style: none" );
            ReportError(doc, list, node, MISSING_STARTTAG );
        }

        /* node should be <LI> */
        InsertNodeAtEnd(list,node);
        ParseTag( doc, node, IgnoreWhitespace);
    }

    ReportError(doc, list, node, MISSING_ENDTAG_FOR);
}

/*
 unexpected content in table row is moved to just before
 the table in accordance with Netscape and IE. This code
 assumes that node hasn't been inserted into the row.
*/
static void MoveBeforeTable( TidyDocImpl* ARG_UNUSED(doc), Node *row,
                             Node *node )
{
    Node *table;

    /* first find the table element */
    for (table = row->parent; table; table = table->parent)
    {
        if ( nodeIsTABLE(table) )
        {
            InsertNodeBeforeElement( table, node );
            return;
        }
    }
    /* No table element */
    InsertNodeBeforeElement( row->parent, node );
}

/*
 if a table row is empty then insert an empty cell
 this practice is consistent with browser behavior
 and avoids potential problems with row spanning cells
*/
static void FixEmptyRow(TidyDocImpl* doc, Node *row)
{
    Node *cell;

    if (row->content == NULL)
    {
        cell = InferredTag(doc, TidyTag_TD);
        InsertNodeAtEnd(row, cell);
        ReportError(doc, row, cell, MISSING_STARTTAG);
    }
}

void ParseRow(TidyDocImpl* doc, Node *row, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node;
    Bool exclude_state;

    if (row->tag->model & CM_EMPTY)
        return;

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == row->tag)
        {
            if (node->type == EndTag)
            {
                FreeNode( doc, node);
                row->closed = yes;
                FixEmptyRow( doc, row);
                return;
            }

            /* New row start implies end of current row */
            UngetToken( doc );
            FixEmptyRow( doc, row);
            return;
        }

        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if ( node->type == EndTag )
        {
            if ( DescendantOf(row, TagId(node)) )
            {
                UngetToken( doc );
                return;
            }

            if ( nodeIsFORM(node) || nodeHasCM(node, CM_BLOCK|CM_INLINE) )
            {
                if ( nodeIsFORM(node) )
                    BadForm( doc );

                ReportError(doc, row, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if ( nodeIsTD(node) || nodeIsTH(node) )
            {
                ReportError(doc, row, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }
        }

        /* deal with comments etc. */
        if (InsertMisc(row, node))
            continue;

        /* discard unknown tags */
        if (node->tag == NULL && node->type != TextNode)
        {
            ReportError(doc, row, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* discard unexpected <table> element */
        if ( nodeIsTABLE(node) )
        {
            ReportError(doc, row, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* THEAD, TFOOT or TBODY */
        if ( nodeHasCM(node, CM_ROWGRP) )
        {
            UngetToken( doc );
            return;
        }

        if (node->type == EndTag)
        {
            ReportError(doc, row, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /*
          if text or inline or block move before table
          if head content move to head
        */

        if (node->type != EndTag)
        {
            if ( nodeIsFORM(node) )
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_TD);
                ReportError(doc, row, node, MISSING_STARTTAG);
            }
            else if ( nodeIsText(node)
                      || nodeHasCM(node, CM_BLOCK | CM_INLINE) )
            {
                MoveBeforeTable( doc, row, node );
                ReportError(doc, row, node, TAG_NOT_ALLOWED_IN);
                lexer->exiled = yes;

                if (node->type != TextNode)
                    ParseTag( doc, node, IgnoreWhitespace);

                lexer->exiled = no;
                continue;
            }
            else if (node->tag->model & CM_HEAD)
            {
                ReportError(doc, row, node, TAG_NOT_ALLOWED_IN);
                MoveToHead( doc, row, node);
                continue;
            }
        }

        if ( !(nodeIsTD(node) || nodeIsTH(node)) )
        {
            ReportError(doc, row, node, TAG_NOT_ALLOWED_IN);
            FreeNode( doc, node);
            continue;
        }
        
        /* node should be <TD> or <TH> */
        InsertNodeAtEnd(row, node);
        exclude_state = lexer->excludeBlocks;
        lexer->excludeBlocks = no;
        ParseTag( doc, node, IgnoreWhitespace);
        lexer->excludeBlocks = exclude_state;

        /* pop inline stack */

        while ( lexer->istacksize > lexer->istackbase )
            PopInline( doc, NULL );
    }

}

void ParseRowGroup(TidyDocImpl* doc, Node *rowgroup, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node, *parent;

    if (rowgroup->tag->model & CM_EMPTY)
        return;

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == rowgroup->tag)
        {
            if (node->type == EndTag)
            {
                rowgroup->closed = yes;
                FreeNode( doc, node);
                return;
            }

            UngetToken( doc );
            return;
        }

        /* if </table> infer end tag */
        if ( nodeIsTABLE(node) && node->type == EndTag )
        {
            UngetToken( doc );
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(rowgroup, node))
            continue;

        /* discard unknown tags */
        if (node->tag == NULL && node->type != TextNode)
        {
            ReportError(doc, rowgroup, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /*
          if TD or TH then infer <TR>
          if text or inline or block move before table
          if head content move to head
        */

        if (node->type != EndTag)
        {
            if ( nodeIsTD(node) || nodeIsTH(node) )
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_TR);
                ReportError(doc, rowgroup, node, MISSING_STARTTAG);
            }
            else if ( nodeIsText(node)
                      || nodeHasCM(node, CM_BLOCK|CM_INLINE) )
            {
                MoveBeforeTable( doc, rowgroup, node );
                ReportError(doc, rowgroup, node, TAG_NOT_ALLOWED_IN);
                lexer->exiled = yes;

                if (node->type != TextNode)
                    ParseTag(doc, node, IgnoreWhitespace);

                lexer->exiled = no;
                continue;
            }
            else if (node->tag->model & CM_HEAD)
            {
                ReportError(doc, rowgroup, node, TAG_NOT_ALLOWED_IN);
                MoveToHead(doc, rowgroup, node);
                continue;
            }
        }

        /* 
          if this is the end tag for ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            if ( nodeIsFORM(node) || nodeHasCM(node, CM_BLOCK|CM_INLINE) )
            {
                if ( nodeIsFORM(node) )
                    BadForm( doc );

                ReportError(doc, rowgroup, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if ( nodeIsTR(node) || nodeIsTD(node) || nodeIsTH(node) )
            {
                ReportError(doc, rowgroup, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            for ( parent = rowgroup->parent;
                  parent != NULL;
                  parent = parent->parent )
            {
                if (node->tag == parent->tag)
                {
                    UngetToken( doc );
                    return;
                }
            }
        }

        /*
          if THEAD, TFOOT or TBODY then implied end tag

        */
        if (node->tag->model & CM_ROWGRP)
        {
            if (node->type != EndTag)
            {
                UngetToken( doc );
                return;
            }
        }

        if (node->type == EndTag)
        {
            ReportError(doc, rowgroup, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }
        
        if ( !nodeIsTR(node) )
        {
            node = InferredTag(doc, TidyTag_TR);
            ReportError(doc, rowgroup, node, MISSING_STARTTAG);
            UngetToken( doc );
        }

       /* node should be <TR> */
        InsertNodeAtEnd(rowgroup, node);
        ParseTag(doc, node, IgnoreWhitespace);
    }

}

void ParseColGroup(TidyDocImpl* doc, Node *colgroup, uint ARG_UNUSED(mode))
{
    Node *node, *parent;

    if (colgroup->tag->model & CM_EMPTY)
        return;

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == colgroup->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            colgroup->closed = yes;
            return;
        }

        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            if ( nodeIsFORM(node) )
            {
                BadForm( doc );
                ReportError(doc, colgroup, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            for ( parent = colgroup->parent;
                  parent != NULL;
                  parent = parent->parent )
            {
                if (node->tag == parent->tag)
                {
                    UngetToken( doc );
                    return;
                }
            }
        }

        if (nodeIsText(node))
        {
            UngetToken( doc );
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(colgroup, node))
            continue;

        /* discard unknown tags */
        if (node->tag == NULL)
        {
            ReportError(doc, colgroup, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        if ( !nodeIsCOL(node) )
        {
            UngetToken( doc );
            return;
        }

        if (node->type == EndTag)
        {
            ReportError(doc, colgroup, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }
        
        /* node should be <COL> */
        InsertNodeAtEnd(colgroup, node);
        ParseTag(doc, node, IgnoreWhitespace);
    }
}

void ParseTableTag(TidyDocImpl* doc, Node *table, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node, *parent;
    uint istackbase;

    DeferDup( doc );
    istackbase = lexer->istackbase;
    lexer->istackbase = lexer->istacksize;
    
    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == table->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            lexer->istackbase = istackbase;
            table->closed = yes;
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(table, node))
            continue;

        /* discard unknown tags */
        if (node->tag == NULL && node->type != TextNode)
        {
            ReportError(doc, table, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* if TD or TH or text or inline or block then infer <TR> */

        if (node->type != EndTag)
        {
            if ( nodeIsTD(node) || nodeIsTH(node) || nodeIsTABLE(node) )
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_TR);
                ReportError(doc, table, node, MISSING_STARTTAG);
            }
            else if ( nodeIsText(node) ||nodeHasCM(node,CM_BLOCK|CM_INLINE) )
            {
                InsertNodeBeforeElement(table, node);
                ReportError(doc, table, node, TAG_NOT_ALLOWED_IN);
                lexer->exiled = yes;

                if (node->type != TextNode) 
                    ParseTag(doc, node, IgnoreWhitespace);

                lexer->exiled = no;
                continue;
            }
            else if (node->tag->model & CM_HEAD)
            {
                MoveToHead(doc, table, node);
                continue;
            }
        }

        /* 
          if this is the end tag for an ancestor element
          then infer end tag for this element
        */
        if (node->type == EndTag)
        {
            if ( nodeIsFORM(node) )
            {
                BadForm( doc );
                ReportError(doc, table, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            /* best to discard unexpected block/inline end tags */
            if ( nodeHasCM(node, CM_TABLE|CM_ROW) ||
                 nodeHasCM(node, CM_BLOCK|CM_INLINE) )
            {
                ReportError(doc, table, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            for ( parent = table->parent;
                  parent != NULL;
                  parent = parent->parent )
            {
                if (node->tag == parent->tag)
                {
                    ReportError(doc, table, node, MISSING_ENDTAG_BEFORE );
                    UngetToken( doc );
                    lexer->istackbase = istackbase;
                    return;
                }
            }
        }

        if (!(node->tag->model & CM_TABLE))
        {
            UngetToken( doc );
            ReportError(doc, table, node, TAG_NOT_ALLOWED_IN);
            lexer->istackbase = istackbase;
            return;
        }

        if (nodeIsElement(node))
        {
            InsertNodeAtEnd(table, node);
            ParseTag(doc, node, IgnoreWhitespace);
            continue;
        }

        /* discard unexpected text nodes and end tags */
        ReportError(doc, table, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    ReportError(doc, table, node, MISSING_ENDTAG_FOR);
    lexer->istackbase = istackbase;
}

/* acceptable content for pre elements */
Bool PreContent( TidyDocImpl* ARG_UNUSED(doc), Node* node )
{
    /* p is coerced to br's, Text OK too */
    if ( nodeIsP(node) || nodeIsText(node) )
        return yes;

    if ( node->tag == NULL ||
         nodeIsPARAM(node) ||
         !nodeHasCM(node, CM_INLINE|CM_NEW) )
        return no;

    return yes;
}

void ParsePre( TidyDocImpl* doc, Node *pre, uint ARG_UNUSED(mode) )
{
    Node *node;

    if (pre->tag->model & CM_EMPTY)
        return;

    InlineDup( doc, NULL ); /* tell lexer to insert inlines if needed */

    while ((node = GetToken(doc, Preformatted)) != NULL)
    {
        if ( node->type == EndTag && 
             (node->tag == pre->tag || DescendantOf(pre, TagId(node))) )
        {
            if (nodeIsBODY(node) || nodeIsHTML(node))
            {
                ReportError(doc, pre, node, DISCARDING_UNEXPECTED);
                FreeNode(doc, node);
                continue;
            }
            if (node->tag == pre->tag)
            {
                FreeNode(doc, node);
            }
            else
            {
                ReportError(doc, pre, node, MISSING_ENDTAG_BEFORE );
                UngetToken( doc );
            }
            pre->closed = yes;
            TrimSpaces(doc, pre);
            return;
        }

        if (nodeIsText(node))
        {
            InsertNodeAtEnd(pre, node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(pre, node))
            continue;

        if (node->tag == NULL)
        {
            ReportError(doc, pre, node, DISCARDING_UNEXPECTED);
            FreeNode(doc, node);
            continue;
        }

        /* strip unexpected tags */
        if ( !PreContent(doc, node) )
        {
            Node *newnode;

            /* fix for http://tidy.sf.net/bug/772205 */
            if (node->type == EndTag)
            {
               ReportError(doc, pre, node, DISCARDING_UNEXPECTED);
               FreeNode(doc, node);
               continue;
            }
            /*
              This is basically what Tidy 04 August 2000 did and far more accurate
              with respect to browser behaivour than the code commented out above.
              Tidy could try to propagate the <pre> into each disallowed child where
              <pre> is allowed in order to replicate some browsers behaivour, but
              there are a lot of exceptions, e.g. Internet Explorer does not propagate
              <pre> into table cells while Mozilla does. Opera 6 never propagates
              <pre> into blocklevel elements while Opera 7 behaves much like Mozilla.

              Tidy behaves thus mostly like Opera 6 except for nested <pre> elements
              which are handled like Mozilla takes them (Opera6 closes all <pre> after
              the first </pre>).

              There are similar issues like replacing <p> in <pre> with <br>, for
              example

                <pre>...<p>...</pre>                 (Input)
                <pre>...<br>...</pre>                (Tidy)
                <pre>...<br>...</pre>                (Opera 7 and Internet Explorer)
                <pre>...<br><br>...</pre>            (Opera 6 and Mozilla)

                <pre>...<p>...</p>...</pre>          (Input)
                <pre>...<br>......</pre>             (Tidy, BUG!)
                <pre>...<br>...<br>...</pre>         (Internet Explorer)
                <pre>...<br><br>...<br><br>...</pre> (Mozilla, Opera 6)
                <pre>...<br>...<br><br>...</pre>     (Opera 7)
                
              or something similar, they could also be closing the <pre> and propagate
              the <pre> into the newly opened <p>.

              Todo: IMG, OBJECT, APPLET, BIG, SMALL, SUB, SUP, FONT, and BASEFONT are
              dissallowed in <pre>, Tidy neither detects this nor does it perform any
              cleanup operation. Tidy should at least issue a warning if it encounters
              such constructs.

              Todo: discarding </p> is abviously a bug, it should be replaced by <br>.
            */
            InsertNodeAfterElement(pre, node);
            ReportError(doc, pre, node, MISSING_ENDTAG_BEFORE);
            ParseTag(doc, node, IgnoreWhitespace);

            newnode = InferredTag(doc, TidyTag_PRE);
            ReportError(doc, pre, newnode, INSERTING_TAG);
            pre = newnode;
            InsertNodeAfterElement(node, pre);

            continue;
        }

        if ( nodeIsP(node) )
        {
            if (node->type == StartTag)
            {
                ReportError(doc, pre, node, USING_BR_INPLACE_OF);

                /* trim white space before <p> in <pre>*/
                TrimSpaces(doc, pre);
            
                /* coerce both <p> and </p> to <br> */
                CoerceNode(doc, node, TidyTag_BR, no, no);
                FreeAttrs( doc, node ); /* discard align attribute etc. */
                InsertNodeAtEnd( pre, node );
            }
            else
            {
                ReportError(doc, pre, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
            }
            continue;
        }

        if ( nodeIsElement(node) )
        {
            /* trim white space before <br> */
            if ( nodeIsBR(node) )
                TrimSpaces(doc, pre);
            
            InsertNodeAtEnd(pre, node);
            ParseTag(doc, node, Preformatted);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, pre, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    ReportError(doc, pre, node, MISSING_ENDTAG_FOR);
}

void ParseOptGroup(TidyDocImpl* doc, Node *field, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node;

    lexer->insert = NULL;  /* defer implicit inline start tags */

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == field->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            field->closed = yes;
            TrimSpaces(doc, field);
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(field, node))
            continue;

        if ( node->type == StartTag && 
             (nodeIsOPTION(node) || nodeIsOPTGROUP(node)) )
        {
            if ( nodeIsOPTGROUP(node) )
                ReportError(doc, field, node, CANT_BE_NESTED);

            InsertNodeAtEnd(field, node);
            ParseTag(doc, node, MixedContent);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, field, node, DISCARDING_UNEXPECTED );
        FreeNode( doc, node);
    }
}


void ParseSelect(TidyDocImpl* doc, Node *field, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node;

    lexer->insert = NULL;  /* defer implicit inline start tags */

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == field->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            field->closed = yes;
            TrimSpaces(doc, field);
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(field, node))
            continue;

        if ( node->type == StartTag && 
             ( nodeIsOPTION(node)   ||
               nodeIsOPTGROUP(node) ||
               nodeIsSCRIPT(node)) 
           )
        {
            InsertNodeAtEnd(field, node);
            ParseTag(doc, node, IgnoreWhitespace);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, field, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    ReportError(doc, field, node, MISSING_ENDTAG_FOR);
}

void ParseText(TidyDocImpl* doc, Node *field, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node;

    lexer->insert = NULL;  /* defer implicit inline start tags */

    if ( nodeIsTEXTAREA(field) )
        mode = Preformatted;
    else
        mode = MixedContent;  /* kludge for font tags */

    while ((node = GetToken(doc, mode)) != NULL)
    {
        if (node->tag == field->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            field->closed = yes;
            TrimSpaces(doc, field);
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(field, node))
            continue;

        if (nodeIsText(node))
        {
            /* only called for 1st child */
            if (field->content == NULL && !(mode & Preformatted))
                TrimSpaces(doc, field);

            if (node->start >= node->end)
            {
                FreeNode( doc, node);
                continue;
            }

            InsertNodeAtEnd(field, node);
            continue;
        }

        /* for textarea should all cases of < and & be escaped? */

        /* discard inline tags e.g. font */
        if (   node->tag 
            && node->tag->model & CM_INLINE
            && !(node->tag->model & CM_FIELD)) /* #487283 - fix by Lee Passey 25 Jan 02 */
        {
            ReportError(doc, field, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* terminate element on other tags */
        if (!(field->tag->model & CM_OPT))
            ReportError(doc, field, node, MISSING_ENDTAG_BEFORE);

        UngetToken( doc );
        TrimSpaces(doc, field);
        return;
    }

    if (!(field->tag->model & CM_OPT))
        ReportError(doc, field, node, MISSING_ENDTAG_FOR);
}


void ParseTitle(TidyDocImpl* doc, Node *title, uint ARG_UNUSED(mode))
{
    Node *node;
    while ((node = GetToken(doc, MixedContent)) != NULL)
    {
        if (node->tag == title->tag && node->type == StartTag)
        {
            ReportError(doc, title, node, COERCE_TO_ENDTAG);
            node->type = EndTag;
            UngetToken( doc );
            continue;
        }
        else if (node->tag == title->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            title->closed = yes;
            TrimSpaces(doc, title);
            return;
        }

        if (nodeIsText(node))
        {
            /* only called for 1st child */
            if (title->content == NULL)
                TrimInitialSpace(doc, title, node);

            if (node->start >= node->end)
            {
                FreeNode( doc, node);
                continue;
            }

            InsertNodeAtEnd(title, node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(title, node))
            continue;

        /* discard unknown tags */
        if (node->tag == NULL)
        {
            ReportError(doc, title, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* pushback unexpected tokens */
        ReportError(doc, title, node, MISSING_ENDTAG_BEFORE);
        UngetToken( doc );
        TrimSpaces(doc, title);
        return;
    }

    ReportError(doc, title, node, MISSING_ENDTAG_FOR);
}

/*
  This isn't quite right for CDATA content as it recognises
  tags within the content and parses them accordingly.
  This will unfortunately screw up scripts which include
  < + letter,  < + !, < + ?  or  < + / + letter
*/

void ParseScript(TidyDocImpl* doc, Node *script, uint ARG_UNUSED(mode))
{
    Node *node;
    
    doc->lexer->parent = script;
    node = GetToken(doc, CdataContent);
    doc->lexer->parent = NULL;

    if (node)
    {
        InsertNodeAtEnd(script, node);
    }
    else
    {
        /* handle e.g. a document like "<script>" */
        ReportError(doc, script, NULL, MISSING_ENDTAG_FOR);
        return;
    }

    node = GetToken(doc, IgnoreWhitespace);

    if (!(node && node->type == EndTag && node->tag &&
        node->tag->id == script->tag->id))
    {
        ReportError(doc, script, node, MISSING_ENDTAG_FOR);

        if (node)
            UngetToken(doc);
    }
    else
    {
        FreeNode(doc, node);
    }
}

Bool IsJavaScript(Node *node)
{
    Bool result = no;
    AttVal *attr;

    if (node->attributes == NULL)
        return yes;

    for (attr = node->attributes; attr; attr = attr->next)
    {
        if ( (attrIsLANGUAGE(attr) || attrIsTYPE(attr))
             && AttrContains(attr, "javascript") )
        {
            result = yes;
            break;
        }
    }

    return result;
}

void ParseHead(TidyDocImpl* doc, Node *head, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node;
    int HasTitle = 0;
    int HasBase = 0;

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == head->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            head->closed = yes;
            break;
        }

        /* find and discard multiple <head> elements */
        /* find and discard <html> in <head> elements */
        if ((node->tag == head->tag || nodeIsHTML(node)) && node->type == StartTag)
        {
            ReportError(doc, head, node, DISCARDING_UNEXPECTED);
            FreeNode(doc, node);
            continue;
        }

        if (nodeIsText(node))
        {
            ReportError(doc, head, node, TAG_NOT_ALLOWED_IN);
            UngetToken( doc );
            break;
        }

        if (node->type == ProcInsTag && node->element &&
            tmbstrcmp(node->element, "xml-stylesheet") == 0)
        {
            ReportError(doc, head, node, TAG_NOT_ALLOWED_IN);
            InsertNodeBeforeElement(FindHTML(doc), node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(head, node))
            continue;

        if (node->type == DocTypeTag)
        {
            InsertDocType(doc, head, node);
            continue;
        }

        /* discard unknown tags */
        if (node->tag == NULL)
        {
            ReportError(doc, head, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }
        
        /*
         if it doesn't belong in the head then
         treat as implicit end of head and deal
         with as part of the body
        */
        if (!(node->tag->model & CM_HEAD))
        {
            /* #545067 Implicit closing of head broken - warn only for XHTML input */
            if ( lexer->isvoyager )
                ReportError(doc, head, node, TAG_NOT_ALLOWED_IN );
            UngetToken( doc );
            break;
        }

        if (nodeIsElement(node))
        {
            if ( nodeIsTITLE(node) )
            {
                ++HasTitle;

                if (HasTitle > 1)
                    if (head)
                        ReportError(doc, head, node, TOO_MANY_ELEMENTS_IN);
                    else
                        ReportError(doc, head, node, TOO_MANY_ELEMENTS);
            }
            else if ( nodeIsBASE(node) )
            {
                ++HasBase;

                if (HasBase > 1)
                    if (head)
                        ReportError(doc, head, node, TOO_MANY_ELEMENTS_IN);
                    else
                        ReportError(doc, head, node, TOO_MANY_ELEMENTS);
            }
            else if ( nodeIsNOSCRIPT(node) )
            {
                ReportError(doc, head, node, TAG_NOT_ALLOWED_IN);
            }

#ifdef AUTO_INPUT_ENCODING
            else if (nodeIsMETA(node))
            {
                AttVal * httpEquiv = AttrGetById(node, TidyAttr_HTTP_EQUIV);
                AttVal * content = AttrGetById(node, TidyAttr_CONTENT);
                if (httpEquiv && AttrValueIs(httpEquiv, "Content-Type") && AttrHasValue(content))
                {
                    tmbstr val, charset;
                    uint end = 0;
                    val = charset = tmbstrdup(content->value);
                    val = tmbstrtolower(val);
                    val = strstr(content->value, "charset");
                    
                    if (val)
                        val += 7;

                    while(val && *val && (IsWhite((tchar)*val) ||
                          *val == '=' || *val == '"' || *val == '\''))
                        ++val;

                    while(val && val[end] && !(IsWhite((tchar)val[end]) ||
                          val[end] == '"' || val[end] == '\'' || val[end] == ';'))
                        ++end;

                    if (val && end)
                    {
                        tmbstr encoding = tmbstrndup(val, end);
                        uint id = GetEncodingIdFromName(encoding);

                        /* todo: detect mismatch with BOM/XMLDecl/declared */
                        /* todo: error for unsupported encodings */
                        /* todo: try to re-init transcoder */
                        /* todo: change input/output encoding settings */
                        /* todo: store id in StreamIn */

                        MemFree(encoding);
                    }

                    MemFree(charset);
                }
            }
#endif /* AUTO_INPUT_ENCODING */

            InsertNodeAtEnd(head, node);
            ParseTag(doc, node, IgnoreWhitespace);
            continue;
        }

        /* discard unexpected text nodes and end tags */
        ReportError(doc, head, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }
}

void ParseBody(TidyDocImpl* doc, Node *body, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node;
    Bool checkstack, iswhitenode;

    mode = IgnoreWhitespace;
    checkstack = yes;

    BumpObject( doc, body->parent );

    while ((node = GetToken(doc, mode)) != NULL)
    {
        /* find and discard multiple <body> elements */
        if (node->tag == body->tag && node->type == StartTag)
        {
            ReportError(doc, body, node, DISCARDING_UNEXPECTED);
            FreeNode(doc, node);
            continue;
        }

        /* #538536 Extra endtags not detected */
        if ( nodeIsHTML(node) )
        {
            if (nodeIsElement(node) || lexer->seenEndHtml) 
                ReportError(doc, body, node, DISCARDING_UNEXPECTED);
            else
                lexer->seenEndHtml = 1;

            FreeNode( doc, node);
            continue;
        }

        if ( lexer->seenEndBody && 
             ( node->type == StartTag ||
               node->type == EndTag   ||
               node->type == StartEndTag ) )
        {
            ReportError(doc, body, node, CONTENT_AFTER_BODY );
        }

        if ( node->tag == body->tag && node->type == EndTag )
        {
            body->closed = yes;
            TrimSpaces(doc, body);
            FreeNode( doc, node);
            lexer->seenEndBody = 1;
            mode = IgnoreWhitespace;

            if ( nodeIsNOFRAMES(body->parent) )
                break;

            continue;
        }

        if ( nodeIsNOFRAMES(node) )
        {
            if (node->type == StartTag)
            {
                InsertNodeAtEnd(body, node);
                ParseBlock(doc, node, mode);
                continue;
            }

            if (node->type == EndTag && nodeIsNOFRAMES(body->parent) )
            {
                TrimSpaces(doc, body);
                UngetToken( doc );
                break;
            }
        }

        if ( (nodeIsFRAME(node) || nodeIsFRAMESET(node))
             && nodeIsNOFRAMES(body->parent) )
        {
            TrimSpaces(doc, body);
            UngetToken( doc );
            break;
        }
        
        iswhitenode = no;

        if ( nodeIsText(node) &&
             node->end <= node->start + 1 &&
             lexer->lexbuf[node->start] == ' ' )
            iswhitenode = yes;

        /* deal with comments etc. */
        if (InsertMisc(body, node))
            continue;

        /* #538536 Extra endtags not detected */
#if 0
        if ( lexer->seenEndBody == 1 && !iswhitenode )
        {
            ++lexer->seenEndBody;
            ReportError(doc, body, node, CONTENT_AFTER_BODY);
        }
#endif

        /* mixed content model permits text */
        if (nodeIsText(node))
        {
            if (iswhitenode && mode == IgnoreWhitespace)
            {
                FreeNode( doc, node);
                continue;
            }

            /* HTML 2 and HTML4 strict don't allow text here */
            ConstrainVersion(doc, ~(VERS_HTML40_STRICT | VERS_HTML20));

            if (checkstack)
            {
                checkstack = no;

                if ( InlineDup(doc, node) > 0 )
                    continue;
            }

            InsertNodeAtEnd(body, node);
            mode = MixedContent;
            continue;
        }

        if (node->type == DocTypeTag)
        {
            InsertDocType(doc, body, node);
            continue;
        }
        /* discard unknown  and PARAM tags */
        if ( node->tag == NULL || nodeIsPARAM(node) )
        {
            ReportError(doc, body, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /*
          Netscape allows LI and DD directly in BODY
          We infer UL or DL respectively and use this
          Bool to exclude block-level elements so as
          to match Netscape's observed behaviour.
        */
        lexer->excludeBlocks = no;
        
        if ( nodeIsINPUT(node) ||
             (!nodeHasCM(node, CM_BLOCK) && !nodeHasCM(node, CM_INLINE))
           )
        {
            /* avoid this error message being issued twice */
            if (!(node->tag->model & CM_HEAD))
                ReportError(doc, body, node, TAG_NOT_ALLOWED_IN);

            if (node->tag->model & CM_HTML)
            {
                /* copy body attributes if current body was inferred */
                if ( nodeIsBODY(node) && body->implicit 
                     && body->attributes == NULL )
                {
                    body->attributes = node->attributes;
                    node->attributes = NULL;
                }

                FreeNode( doc, node);
                continue;
            }

            if (node->tag->model & CM_HEAD)
            {
                MoveToHead(doc, body, node);
                continue;
            }

            if (node->tag->model & CM_LIST)
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_UL);
                /* AddClass( doc, node, "noindent" ); */
                lexer->excludeBlocks = yes;
            }
            else if (node->tag->model & CM_DEFLIST)
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_DL);
                lexer->excludeBlocks = yes;
            }
            else if (node->tag->model & (CM_TABLE | CM_ROWGRP | CM_ROW))
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_TABLE);
                lexer->excludeBlocks = yes;
            }
            else if ( nodeIsINPUT(node) )
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_FORM);
                lexer->excludeBlocks = yes;
            }
            else
            {
                if ( !nodeHasCM(node, CM_ROW | CM_FIELD) )
                {
                    UngetToken( doc );
                    return;
                }

                /* ignore </td> </th> <option> etc. */
                FreeNode( doc, node );
                continue;
            }
        }

        if (node->type == EndTag)
        {
            if ( nodeIsBR(node) )
                node->type = StartTag;
            else if ( nodeIsP(node) )
            {
                node->type = StartEndTag;
                node->implicit = yes;
#if OBSOLETE
                CoerceNode(doc, node, TidyTag_BR, no, no);
                FreeAttrs( doc, node ); /* discard align attribute etc. */
                InsertNodeAtEnd(body, node);
                node = InferredTag(doc, TidyTag_BR);
#endif
            }
            else if ( nodeHasCM(node, CM_INLINE) )
                PopInline( doc, node );
        }

        if (nodeIsElement(node))
        {
            if ( nodeHasCM(node, CM_INLINE) && !nodeHasCM(node, CM_MIXED) )
            {
                /* HTML4 strict doesn't allow inline content here */
                /* but HTML2 does allow img elements as children of body */
                if ( nodeIsIMG(node) )
                    ConstrainVersion(doc, ~VERS_HTML40_STRICT);
                else
                    ConstrainVersion(doc, ~(VERS_HTML40_STRICT|VERS_HTML20));

                if (checkstack && !node->implicit)
                {
                    checkstack = no;

                    if ( InlineDup(doc, node) > 0 )
                        continue;
                }

                mode = MixedContent;
            }
            else
            {
                checkstack = yes;
                mode = IgnoreWhitespace;
            }

            if (node->implicit)
                ReportError(doc, body, node, INSERTING_TAG);

            InsertNodeAtEnd(body, node);
            ParseTag(doc, node, mode);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, body, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }
}

void ParseNoFrames(TidyDocImpl* doc, Node *noframes, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node;

    if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
    {
        doc->badAccess |=  USING_NOFRAMES;
    }
    mode = IgnoreWhitespace;

    while ( (node = GetToken(doc, mode)) != NULL )
    {
        if ( node->tag == noframes->tag && node->type == EndTag )
        {
            FreeNode( doc, node);
            noframes->closed = yes;
            TrimSpaces(doc, noframes);
            return;
        }

        if ( nodeIsFRAME(node) || nodeIsFRAMESET(node) )
        {
            TrimSpaces(doc, noframes);
            if (node->type == EndTag)
            {
                ReportError(doc, noframes, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);       /* Throw it away */
            }
            else
            {
                ReportError(doc, noframes, node, MISSING_ENDTAG_BEFORE);
                UngetToken( doc );
            }
            return;
        }

        if ( nodeIsHTML(node) )
        {
            if (nodeIsElement(node))
                ReportError(doc, noframes, node, DISCARDING_UNEXPECTED);

            FreeNode( doc, node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(noframes, node))
            continue;

        if ( nodeIsBODY(node) && node->type == StartTag )
        {
            Bool seen_body = lexer->seenEndBody;
            InsertNodeAtEnd(noframes, node);
            ParseTag(doc, node, IgnoreWhitespace /*MixedContent*/);

            /* fix for bug http://tidy.sf.net/bug/887259 */
            if (seen_body && FindBody(doc) != node)
            {
                CoerceNode(doc, node, TidyTag_DIV, no, no);
                MoveNodeToBody(doc, node);
            }
            continue;
        }

        /* implicit body element inferred */
        if (nodeIsText(node) || (node->tag && node->type != EndTag))
        {
            if ( lexer->seenEndBody )
            {
                Node *body = FindBody( doc );
                if ( body == NULL )
                {
                    ReportError(doc, noframes, node, DISCARDING_UNEXPECTED);
                    FreeNode( doc, node);
                    continue;
                }
                if ( nodeIsText(node) )
                {
                    UngetToken( doc );
                    node = InferredTag(doc, TidyTag_P);
                    ReportError(doc, noframes, node, CONTENT_AFTER_BODY );
                }
                InsertNodeAtEnd( body, node );
            }
            else
            {
                UngetToken( doc );
                node = InferredTag(doc, TidyTag_BODY);
                if ( cfgBool(doc, TidyXmlOut) )
                    ReportError(doc, noframes, node, INSERTING_TAG);
                InsertNodeAtEnd( noframes, node );
            }

            ParseTag( doc, node, IgnoreWhitespace /*MixedContent*/ );
            continue;
        }

        /* discard unexpected end tags */
        ReportError(doc, noframes, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    ReportError(doc, noframes, node, MISSING_ENDTAG_FOR);
}

void ParseFrameSet(TidyDocImpl* doc, Node *frameset, uint ARG_UNUSED(mode))
{
    Lexer* lexer = doc->lexer;
    Node *node;

    if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
    {
        doc->badAccess |=  USING_FRAMES;
    }
    
    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->tag == frameset->tag && node->type == EndTag)
        {
            FreeNode( doc, node);
            frameset->closed = yes;
            TrimSpaces(doc, frameset);
            return;
        }

        /* deal with comments etc. */
        if (InsertMisc(frameset, node))
            continue;

        if (node->tag == NULL)
        {
            ReportError(doc, frameset, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue; 
        }

        if (nodeIsElement(node))
        {
            if (node->tag && node->tag->model & CM_HEAD)
            {
                MoveToHead(doc, frameset, node);
                continue;
            }
        }

        if ( nodeIsBODY(node) )
        {
            UngetToken( doc );
            node = InferredTag(doc, TidyTag_NOFRAMES);
            ReportError(doc, frameset, node, INSERTING_TAG);
        }

        if (node->type == StartTag && (node->tag->model & CM_FRAMES))
        {
            InsertNodeAtEnd(frameset, node);
            lexer->excludeBlocks = no;
            ParseTag(doc, node, MixedContent);
            continue;
        }
        else if (node->type == StartEndTag && (node->tag->model & CM_FRAMES))
        {
            InsertNodeAtEnd(frameset, node);
            continue;
        }

        /* discard unexpected tags */
        ReportError(doc, frameset, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    ReportError(doc, frameset, node, MISSING_ENDTAG_FOR);
}

void ParseHTML(TidyDocImpl* doc, Node *html, uint mode)
{
    Node *node, *head;
    Node *frameset = NULL;
    Node *noframes = NULL;

    SetOptionBool( doc, TidyXmlTags, no );

    for (;;)
    {
        node = GetToken(doc, IgnoreWhitespace);

        if (node == NULL)
        {
            node = InferredTag(doc, TidyTag_HEAD);
            break;
        }

        if ( nodeIsHEAD(node) )
            break;

        if (node->tag == html->tag && node->type == EndTag)
        {
            ReportError(doc, html, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        /* find and discard multiple <html> elements */
        if (node->tag == html->tag && node->type == StartTag)
        {
            ReportError(doc, html, node, DISCARDING_UNEXPECTED);
            FreeNode(doc, node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(html, node))
            continue;

        UngetToken( doc );
        node = InferredTag(doc, TidyTag_HEAD);
        break;
    }

    head = node;
    InsertNodeAtEnd(html, head);
    ParseHead(doc, head, mode);

    for (;;)
    {
        node = GetToken(doc, IgnoreWhitespace);

        if (node == NULL)
        {
            if (frameset == NULL) /* implied body */
            {
                node = InferredTag(doc, TidyTag_BODY);
                InsertNodeAtEnd(html, node);
                ParseBody(doc, node, mode);
            }

            return;
        }

        /* robustly handle html tags */
        if (node->tag == html->tag)
        {
            if (node->type != StartTag && frameset == NULL)
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);

            FreeNode( doc, node);
            continue;
        }

        /* deal with comments etc. */
        if (InsertMisc(html, node))
            continue;

        /* if frameset document coerce <body> to <noframes> */
        if ( nodeIsBODY(node) )
        {
            if (node->type != StartTag)
            {
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if ( cfg(doc, TidyAccessibilityCheckLevel) == 0 )
            {
                if (frameset != NULL)
                {
                    UngetToken( doc );

                    if (noframes == NULL)
                    {
                        noframes = InferredTag(doc, TidyTag_NOFRAMES);
                        InsertNodeAtEnd(frameset, noframes);
                        ReportError(doc, html, noframes, INSERTING_TAG);
                    }

                    ParseTag(doc, noframes, mode);
                    continue;
                }
            }

            ConstrainVersion(doc, ~VERS_FRAMESET);
            break;  /* to parse body */
        }

        /* flag an error if we see more than one frameset */
        if ( nodeIsFRAMESET(node) )
        {
            if (node->type != StartTag)
            {
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if (frameset != NULL)
                ReportFatal(doc, html, node, DUPLICATE_FRAMESET);
            else
                frameset = node;

            InsertNodeAtEnd(html, node);
            ParseTag(doc, node, mode);

            /*
              see if it includes a noframes element so
              that we can merge subsequent noframes elements
            */

            for (node = frameset->content; node; node = node->next)
            {
                if ( nodeIsNOFRAMES(node) )
                    noframes = node;
            }
            continue;
        }

        /* if not a frameset document coerce <noframes> to <body> */
        if ( nodeIsNOFRAMES(node) )
        {
            if (node->type != StartTag)
            {
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                continue;
            }

            if (frameset == NULL)
            {
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
                node = InferredTag(doc, TidyTag_BODY);
                break;
            }

            if (noframes == NULL)
            {
                noframes = node;
                InsertNodeAtEnd(frameset, noframes);
            }
            else
                FreeNode( doc, node);

            ParseTag(doc, noframes, mode);
            continue;
        }

        if (nodeIsElement(node))
        {
            if (node->tag && node->tag->model & CM_HEAD)
            {
                MoveToHead(doc, html, node);
                continue;
            }

            /* discard illegal frame element following a frameset */
            if ( frameset != NULL && nodeIsFRAME(node) )
            {
                ReportError(doc, html, node, DISCARDING_UNEXPECTED);
                FreeNode(doc, node);
                continue;
            }
        }

        UngetToken( doc );

        /* insert other content into noframes element */

        if (frameset)
        {
            if (noframes == NULL)
            {
                noframes = InferredTag(doc, TidyTag_NOFRAMES);
                InsertNodeAtEnd(frameset, noframes);
            }
            else
                ReportError(doc, html, node, NOFRAMES_CONTENT);

            ConstrainVersion(doc, VERS_FRAMESET);
            ParseTag(doc, noframes, mode);
            continue;
        }

        node = InferredTag(doc, TidyTag_BODY);
        ConstrainVersion(doc, ~VERS_FRAMESET);
        break;
    }

    /* node must be body */

    InsertNodeAtEnd(html, node);
    ParseTag(doc, node, mode);
}

static Bool nodeCMIsOnlyInline( Node* node )
{
    return nodeHasCM( node, CM_INLINE ) && !nodeHasCM( node, CM_BLOCK );
}

static void EncloseBodyText(TidyDocImpl* doc)
{
    Node* node;
    Node* body = FindBody(doc);

    if (!body)
        return;

    node = body->content;

    while (node)
    {
        if ((nodeIsText(node) && !IsBlank(doc->lexer, node)) ||
            (nodeIsElement(node) && nodeCMIsOnlyInline(node)))
        {
            Node* p = InferredTag(doc, TidyTag_P);
            InsertNodeBeforeElement(node, p);
            while (node && (!nodeIsElement(node) || nodeCMIsOnlyInline(node)))
            {
                Node* next = node->next;
                RemoveNode(node);
                InsertNodeAtEnd(p, node);
                node = next;
            }
            TrimSpaces(doc, p);
            continue;
        }
        node = node->next;
    }
}

/* <form>, <blockquote> and <noscript> do not allow #PCDATA in
   HTML 4.01 Strict (%block; model instead of %flow;).
  When requested, text nodes in these elements are wrapped in <p>. */
static void EncloseBlockText(TidyDocImpl* doc, Node* node)
{
    Node *next;
    Node *block;

    while (node)
    {
        next = node->next;

        if (node->content)
            EncloseBlockText(doc, node->content);

        if (!(nodeIsFORM(node) || nodeIsNOSCRIPT(node) ||
              nodeIsBLOCKQUOTE(node))
            || !node->content)
        {
            node = next;
            continue;
        }

        block = node->content;

        if ((nodeIsText(block) && !IsBlank(doc->lexer, block)) ||
            (nodeIsElement(block) && nodeCMIsOnlyInline(block)))
        {
            Node* p = InferredTag(doc, TidyTag_P);
            InsertNodeBeforeElement(block, p);
            while (block &&
                   (!nodeIsElement(block) || nodeCMIsOnlyInline(block)))
            {
                Node* tempNext = block->next;
                RemoveNode(block);
                InsertNodeAtEnd(p, block);
                block = tempNext;
            }
            TrimSpaces(doc, p);
            continue;
        }

        node = next;
    }
}

static void ReplaceObsoleteElements(TidyDocImpl* doc, Node* node)
{
    Node *next;

    while (node)
    {
        next = node->next;

        if (nodeIsDIR(node) || nodeIsMENU(node))
            CoerceNode(doc, node, TidyTag_UL, yes, yes);

        if (nodeIsXMP(node) || nodeIsLISTING(node) ||
            (node->tag && node->tag->id == TidyTag_PLAINTEXT))
            CoerceNode(doc, node, TidyTag_PRE, yes, yes);

        if (node->content)
            ReplaceObsoleteElements(doc, node->content);

        node = next;
    }
}

static void AttributeChecks(TidyDocImpl* doc, Node* node)
{
    Node *next;

    while (node)
    {
        next = node->next;

        if (nodeIsElement(node))
        {
            if (node->tag->chkattrs)
                node->tag->chkattrs(doc, node);
            else
                CheckAttributes(doc, node);
        }

        if (node->content)
            AttributeChecks(doc, node->content);

        node = next;
    }
}

/*
  HTML is the top level element
*/
void ParseDocument(TidyDocImpl* doc)
{
    Node *node, *html, *doctype = NULL;

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        if (node->type == XmlDecl)
        {
            if (FindXmlDecl(doc) && doc->root.content)
            {
                ReportError(doc, &doc->root, node, DISCARDING_UNEXPECTED);
                FreeNode(doc, node);
                continue;
            }
            if (node->line != 1 || (node->line == 1 && node->column != 1))
            {
                ReportError(doc, &doc->root, node, SPACE_PRECEDING_XMLDECL);
            }
        }
#ifdef AUTO_INPUT_ENCODING
        if (node->type == XmlDecl)
        {
            AttVal* encoding = GetAttrByName(node, "encoding");
            if (AttrHasValue(encoding))
            {
                uint id = GetEncodingIdFromName(encoding->value);

                /* todo: detect mismatch with BOM/XMLDecl/declared */
                /* todo: error for unsupported encodings */
                /* todo: try to re-init transcoder */
                /* todo: change input/output encoding settings */
                /* todo: store id in StreamIn */
            }
        }
#endif /* AUTO_INPUT_ENCODING */

        /* deal with comments etc. */
        if (InsertMisc( &doc->root, node ))
            continue;

        if (node->type == DocTypeTag)
        {
            if (doctype == NULL)
            {
                InsertNodeAtEnd( &doc->root, node);
                doctype = node;
            }
            else
            {
                ReportError(doc, &doc->root, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
            }
            continue;
        }

        if (node->type == EndTag)
        {
            ReportError(doc, &doc->root, node, DISCARDING_UNEXPECTED);
            FreeNode( doc, node);
            continue;
        }

        if (node->type == StartTag && nodeIsHTML(node))
        {
            AttVal *xmlns;

            xmlns = AttrGetById(node, TidyAttr_XMLNS);

            if (AttrValueIs(xmlns, XHTML_NAMESPACE))
            {
                Bool htmlOut = cfgBool( doc, TidyHtmlOut );
                doc->lexer->isvoyager = yes;                  /* Unless plain HTML */
                SetOptionBool( doc, TidyXhtmlOut, !htmlOut ); /* is specified, output*/
                SetOptionBool( doc, TidyXmlOut, !htmlOut );   /* will be XHTML. */

                /* adjust other config options, just as in config.c */
                if ( !htmlOut )
                {
                    SetOptionBool( doc, TidyUpperCaseTags, no );
                    SetOptionBool( doc, TidyUpperCaseAttrs, no );
                }
            }
        }

        if ( node->type != StartTag || !nodeIsHTML(node) )
        {
            UngetToken( doc );
            html = InferredTag(doc, TidyTag_HTML);
        }
        else
            html = node;

        if (!FindDocType(doc))
            ReportError(doc, NULL, NULL, MISSING_DOCTYPE);

        InsertNodeAtEnd( &doc->root, html);
        ParseHTML( doc, html, IgnoreWhitespace );
        break;
    }

    if (!FindHTML(doc))
    {
        /* a later check should complain if <body> is empty */
        html = InferredTag(doc, TidyTag_HTML);
        InsertNodeAtEnd( &doc->root, html);
        ParseHTML(doc, html, IgnoreWhitespace);
    }

    if (!FindTITLE(doc))
    {
        Node* head = FindHEAD(doc);
        ReportError(doc, head, NULL, MISSING_TITLE_ELEMENT);
        InsertNodeAtEnd(head, InferredTag(doc, TidyTag_TITLE));
    }

    AttributeChecks(doc, &doc->root);
    ReplaceObsoleteElements(doc, &doc->root);
    DropEmptyElements(doc, &doc->root);
    CleanSpaces(doc, &doc->root);

    if (cfgBool(doc, TidyEncloseBodyText))
        EncloseBodyText(doc);
    if (cfgBool(doc, TidyEncloseBlockText))
        EncloseBlockText(doc, &doc->root);
}

Bool XMLPreserveWhiteSpace( TidyDocImpl* doc, Node *element)
{
    AttVal *attribute;

    /* search attributes for xml:space */
    for (attribute = element->attributes; attribute; attribute = attribute->next)
    {
        if (AttrValueIs(attribute, "xml:space"))
        {
            if (AttrValueIs(attribute, "preserve"))
                return yes;

            return no;
        }
    }

    if (element->element == NULL)
        return no;
        
    /* kludge for html docs without explicit xml:space attribute */
    if (nodeIsPRE(element)    ||
        nodeIsSCRIPT(element) ||
        nodeIsSTYLE(element)  ||
        FindParser(doc, element) == ParsePre)
        return yes;

    /* kludge for XSL docs */
    if ( tmbstrcasecmp(element->element, "xsl:text") == 0 )
        return yes;

    return no;
}

/*
  XML documents
*/
static void ParseXMLElement(TidyDocImpl* doc, Node *element, uint mode)
{
    Lexer* lexer = doc->lexer;
    Node *node;

    /* if node is pre or has xml:space="preserve" then do so */

    if ( XMLPreserveWhiteSpace(doc, element) )
        mode = Preformatted;

    while ((node = GetToken(doc, mode)) != NULL)
    {
        if (node->type == EndTag &&
           node->element && element->element &&
           tmbstrcmp(node->element, element->element) == 0)
        {
            FreeNode( doc, node);
            element->closed = yes;
            break;
        }

        /* discard unexpected end tags */
        if (node->type == EndTag)
        {
            if (element)
                ReportFatal(doc, element, node, UNEXPECTED_ENDTAG_IN);
            else
                ReportFatal(doc, element, node, UNEXPECTED_ENDTAG);

            FreeNode( doc, node);
            continue;
        }

        /* parse content on seeing start tag */
        if (node->type == StartTag)
            ParseXMLElement( doc, node, mode );

        InsertNodeAtEnd(element, node);
    }

    /*
     if first child is text then trim initial space and
     delete text node if it is empty.
    */

    node = element->content;

    if (nodeIsText(node) && mode != Preformatted)
    {
        if ( lexer->lexbuf[node->start] == ' ' )
        {
            node->start++;

            if (node->start >= node->end)
                DiscardElement( doc, node );
        }
    }

    /*
     if last child is text then trim final space and
     delete the text node if it is empty
    */

    node = element->last;

    if (nodeIsText(node) && mode != Preformatted)
    {
        if ( lexer->lexbuf[node->end - 1] == ' ' )
        {
            node->end--;

            if (node->start >= node->end)
                DiscardElement( doc, node );
        }
    }
}

void ParseXMLDocument(TidyDocImpl* doc)
{
    Node *node, *doctype = NULL;

    SetOptionBool( doc, TidyXmlTags, yes );

    while ((node = GetToken(doc, IgnoreWhitespace)) != NULL)
    {
        /* discard unexpected end tags */
        if (node->type == EndTag)
        {
            ReportError(doc, NULL, node, UNEXPECTED_ENDTAG);
            FreeNode( doc, node);
            continue;
        }

         /* deal with comments etc. */
        if (InsertMisc( &doc->root, node))
            continue;

        if (node->type == DocTypeTag)
        {
            if (doctype == NULL)
            {
                InsertNodeAtEnd( &doc->root, node);
                doctype = node;
            }
            else
            {
                ReportError(doc, &doc->root, node, DISCARDING_UNEXPECTED);
                FreeNode( doc, node);
            }
            continue;
        }

        if (node->type == StartEndTag)
        {
            InsertNodeAtEnd( &doc->root, node);
            continue;
        }

       /* if start tag then parse element's content */
        if (node->type == StartTag)
        {
            InsertNodeAtEnd( &doc->root, node );
            ParseXMLElement( doc, node, IgnoreWhitespace );
            continue;
        }

        ReportError(doc, &doc->root, node, DISCARDING_UNEXPECTED);
        FreeNode( doc, node);
    }

    /* ensure presence of initial <?xml version="1.0"?> */
    if ( cfgBool(doc, TidyXmlDecl) )
        FixXmlDecl( doc );
}

