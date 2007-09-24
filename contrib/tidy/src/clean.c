/*
  clean.c -- clean up misuse of presentation markup

  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/08/03 18:06:59 $ 
    $Revision: 1.98 $ 

  Filters from other formats such as Microsoft Word
  often make excessive use of presentation markup such
  as font tags, B, I, and the align attribute. By applying
  a set of production rules, it is straight forward to
  transform this to use CSS.

  Some rules replace some of the children of an element by
  style properties on the element, e.g.

  <p><b>...</b></p> -> <p style="font-weight: bold">...</p>

  Such rules are applied to the element's content and then
  to the element itself until none of the rules more apply.
  Having applied all the rules to an element, it will have
  a style attribute with one or more properties. 

  Other rules strip the element they apply to, replacing
  it by style properties on the contents, e.g.
  
  <dir><li><p>...</li></dir> -> <p style="margin-left 1em">...
      
  These rules are applied to an element before processing
  its content and replace the current element by the first
  element in the exposed content.

  After applying both sets of rules, you can replace the
  style attribute by a class value and style rule in the
  document head. To support this, an association of styles
  and class names is built.

  A naive approach is to rely on string matching to test
  when two property lists are the same. A better approach
  would be to first sort the properties before matching.

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tidy-int.h"
#include "clean.h"
#include "lexer.h"
#include "parser.h"
#include "attrs.h"
#include "message.h"
#include "tmbstr.h"
#include "utf8.h"

void RenameElem( Node* node, TidyTagId tid )
{
    const Dict* dict = LookupTagDef( tid );
    MemFree( node->element );
    node->element = tmbstrdup( dict->name );
    node->tag = dict;
}

static void FreeStyleProps(StyleProp *props)
{
    StyleProp *next;

    while (props)
    {
        next = props->next;
        MemFree(props->name);
        MemFree(props->value);
        MemFree(props);
        props = next;
    }
}

static StyleProp *InsertProperty( StyleProp* props, ctmbstr name, ctmbstr value )
{
    StyleProp *first, *prev, *prop;
    int cmp;

    prev = NULL;
    first = props;

    while (props)
    {
        cmp = tmbstrcmp(props->name, name);

        if (cmp == 0)
        {
            /* this property is already defined, ignore new value */
            return first;
        }

        if (cmp > 0)
        {
            /* insert before this */

            prop = (StyleProp *)MemAlloc(sizeof(StyleProp));
            prop->name = tmbstrdup(name);
            prop->value = tmbstrdup(value);
            prop->next = props;

            if (prev)
                prev->next = prop;
            else
                first = prop;

            return first;
        }

        prev = props;
        props = props->next;
    }

    prop = (StyleProp *)MemAlloc(sizeof(StyleProp));
    prop->name = tmbstrdup(name);
    prop->value = tmbstrdup(value);
    prop->next = NULL;

    if (prev)
        prev->next = prop;
    else
        first = prop;

    return first;
}

/*
 Create sorted linked list of properties from style string
 It temporarily places nulls in place of ':' and ';' to
 delimit the strings for the property name and value.
 Some systems don't allow you to NULL literal strings,
 so to avoid this, a copy is made first.
*/
static StyleProp* CreateProps( StyleProp* prop, ctmbstr style )
{
    tmbstr name, value = NULL, name_end, value_end, line;
    Bool more;

    line = tmbstrdup(style);
    name = line;

    while (*name)
    {
        while (*name == ' ')
            ++name;

        name_end = name;

        while (*name_end)
        {
            if (*name_end == ':')
            {
                value = name_end + 1;
                break;
            }

            ++name_end;
        }

        if (*name_end != ':')
            break;

        while ( value && *value == ' ')
            ++value;

        value_end = value;
        more = no;

        while (*value_end)
        {
            if (*value_end == ';')
            {
                more = yes;
                break;
            }

            ++value_end;
        }

        *name_end = '\0';
        *value_end = '\0';

        prop = InsertProperty(prop, name, value);
        *name_end = ':';

        if (more)
        {
            *value_end = ';';
            name = value_end + 1;
            continue;
        }

        break;
    }

    MemFree(line);  /* free temporary copy */
    return prop;
}

static tmbstr CreatePropString(StyleProp *props)
{
    tmbstr style, p, s;
    uint len;
    StyleProp *prop;

    /* compute length */

    for (len = 0, prop = props; prop; prop = prop->next)
    {
        len += tmbstrlen(prop->name) + 2;
        if (prop->value)
            len += tmbstrlen(prop->value) + 2;
    }

    style = (tmbstr) MemAlloc(len+1);
    style[0] = '\0';

    for (p = style, prop = props; prop; prop = prop->next)
    {
        s = prop->name;

        while((*p++ = *s++))
            continue;

        if (prop->value)
        {
            *--p = ':';
            *++p = ' ';
            ++p;

            s = prop->value;
            while((*p++ = *s++))
                continue;
        }
        if (prop->next == NULL)
            break;

        *--p = ';';
        *++p = ' ';
        ++p;
    }

    return style;
}

/*
  create string with merged properties
static tmbstr AddProperty( ctmbstr style, ctmbstr property )
{
    tmbstr line;
    StyleProp *prop;

    prop = CreateProps(NULL, style);
    prop = CreateProps(prop, property);
    line = CreatePropString(prop);
    FreeStyleProps(prop);
    return line;
}
*/

void FreeStyles( TidyDocImpl* doc )
{
    Lexer* lexer = doc->lexer;
    if ( lexer )
    {
        TagStyle *style, *next;
        for ( style = lexer->styles; style; style = next )
        {
            next = style->next;
            MemFree( style->tag );
            MemFree( style->tag_class );
            MemFree( style->properties );
            MemFree( style );
        }
    }
}

static tmbstr GensymClass( TidyDocImpl* doc )
{
    tmbchar buf[512];  /* CSSPrefix is limited to 256 characters */
    ctmbstr pfx = cfgStr(doc, TidyCSSPrefix);
    if ( pfx == NULL || *pfx == 0 )
      pfx = "c";

    tmbsnprintf(buf, sizeof(buf), "%s%u", pfx, ++doc->nClassId );
    return tmbstrdup(buf);
}

static ctmbstr FindStyle( TidyDocImpl* doc, ctmbstr tag, ctmbstr properties )
{
    Lexer* lexer = doc->lexer;
    TagStyle* style;

    for (style = lexer->styles; style; style=style->next)
    {
        if (tmbstrcmp(style->tag, tag) == 0 &&
            tmbstrcmp(style->properties, properties) == 0)
            return style->tag_class;
    }

    style = (TagStyle *)MemAlloc( sizeof(TagStyle) );
    style->tag = tmbstrdup(tag);
    style->tag_class = GensymClass( doc );
    style->properties = tmbstrdup( properties );
    style->next = lexer->styles;
    lexer->styles = style;
    return style->tag_class;
}

/*
 Add class="foo" to node
*/
void AddClass( TidyDocImpl* doc, Node* node, ctmbstr classname )
{
    AttVal *classattr = AttrGetById(node, TidyAttr_CLASS);;

    /*
     if there already is a class attribute
     then append class name after a space.
    */
    if (classattr)
    {
        uint len = tmbstrlen(classattr->value) +
                  tmbstrlen(classname) + 2;
        tmbstr s = (tmbstr) MemAlloc( len );
        tmbstrcpy( s, classattr->value );
        tmbstrcat( s, " " );
        tmbstrcat( s, classname );
        MemFree( classattr->value );
        classattr->value = s;
    }
    else /* create new class attribute */
        AddAttribute( doc, node, "class", classname );
}


/*
 Find style attribute in node, and replace it
 by corresponding class attribute. Search for
 class in style dictionary otherwise gensym
 new class and add to dictionary.

 Assumes that node doesn't have a class attribute
*/
static void Style2Rule( TidyDocImpl* doc, Node *node)
{
    AttVal *styleattr, *classattr;
    ctmbstr classname;

    styleattr = AttrGetById(node, TidyAttr_STYLE);

    if (styleattr)
    {
        /* fix for http://tidy.sf.net/bug/850215 */
        if (!styleattr->value)
        {
            RemoveAttribute(doc, node, styleattr);
            return;
        }

        classname = FindStyle( doc, node->element, styleattr->value );
        classattr = AttrGetById(node, TidyAttr_CLASS);

        /*
         if there already is a class attribute
         then append class name after an underscore
        */
        if (classattr)
        {
            uint len = tmbstrlen(classattr->value) +
                      tmbstrlen(classname) + 2;
            tmbstr s = (tmbstr) MemAlloc( len );
            s[0] = '\0';
            if (classattr->value)
            {
                tmbstrcpy(s, classattr->value);
                tmbstrcat(s, " ");
            }
            tmbstrcat(s, classname);
            if (classattr->value)
                MemFree(classattr->value);
            classattr->value = s;
            RemoveAttribute( doc, node, styleattr );
        }
        else /* reuse style attribute for class attribute */
        {
            MemFree(styleattr->attribute);
            MemFree(styleattr->value);
            styleattr->attribute = tmbstrdup("class");
            styleattr->value = tmbstrdup(classname);
        }
    }
}

static void AddColorRule( Lexer* lexer, ctmbstr selector, ctmbstr color )
{
    if ( selector && color )
    {
        AddStringLiteral(lexer, selector);
        AddStringLiteral(lexer, " { color: ");
        AddStringLiteral(lexer, color);
        AddStringLiteral(lexer, " }\n");
    }
}

/*
 move presentation attribs from body to style element

 background="foo" ->  body { background-image: url(foo) }
 bgcolor="foo"    ->  body { background-color: foo }
 text="foo"       ->  body { color: foo }
 link="foo"       ->  :link { color: foo }
 vlink="foo"      ->  :visited { color: foo }
 alink="foo"      ->  :active { color: foo }
*/
static void CleanBodyAttrs( TidyDocImpl* doc, Node* body )
{
    Lexer* lexer  = doc->lexer;
    tmbstr bgurl   = NULL;
    tmbstr bgcolor = NULL;
    tmbstr color   = NULL;
    AttVal* attr;
    
    if (NULL != (attr = AttrGetById(body, TidyAttr_BACKGROUND)))
    {
        bgurl = attr->value;
        attr->value = NULL;
        RemoveAttribute( doc, body, attr );
    }

    if (NULL != (attr = AttrGetById(body, TidyAttr_BGCOLOR)))
    {
        bgcolor = attr->value;
        attr->value = NULL;
        RemoveAttribute( doc, body, attr );
    }

    if (NULL != (attr = AttrGetById(body, TidyAttr_TEXT)))
    {
        color = attr->value;
        attr->value = NULL;
        RemoveAttribute( doc, body, attr );
    }

    if ( bgurl || bgcolor || color )
    {
        AddStringLiteral(lexer, " body {\n");
        if (bgurl)
        {
            AddStringLiteral(lexer, "  background-image: url(");
            AddStringLiteral(lexer, bgurl);
            AddStringLiteral(lexer, ");\n");
            MemFree(bgurl);
        }
        if (bgcolor)
        {
            AddStringLiteral(lexer, "  background-color: ");
            AddStringLiteral(lexer, bgcolor);
            AddStringLiteral(lexer, ";\n");
            MemFree(bgcolor);
        }
        if (color)
        {
            AddStringLiteral(lexer, "  color: ");
            AddStringLiteral(lexer, color);
            AddStringLiteral(lexer, ";\n");
            MemFree(color);
        }

        AddStringLiteral(lexer, " }\n");
    }

    if (NULL != (attr = AttrGetById(body, TidyAttr_LINK)))
    {
        AddColorRule(lexer, " :link", attr->value);
        RemoveAttribute( doc, body, attr );
    }

    if (NULL != (attr = AttrGetById(body, TidyAttr_VLINK)))
    {
        AddColorRule(lexer, " :visited", attr->value);
        RemoveAttribute( doc, body, attr );
    }

    if (NULL != (attr = AttrGetById(body, TidyAttr_ALINK)))
    {
        AddColorRule(lexer, " :active", attr->value);
        RemoveAttribute( doc, body, attr );
    }
}

static Bool NiceBody( TidyDocImpl* doc )
{
    Node* node = FindBody(doc);
    if (node)
    {
        if (AttrGetById(node, TidyAttr_BACKGROUND) ||
            AttrGetById(node, TidyAttr_BGCOLOR)    ||
            AttrGetById(node, TidyAttr_TEXT)       ||
            AttrGetById(node, TidyAttr_LINK)       ||
            AttrGetById(node, TidyAttr_VLINK)      ||
            AttrGetById(node, TidyAttr_ALINK))
        {
            doc->badLayout |= USING_BODY;
            return no;
        }
    }

    return yes;
}

/* create style element using rules from dictionary */
static void CreateStyleElement( TidyDocImpl* doc )
{
    Lexer* lexer = doc->lexer;
    Node *node, *head, *body;
    TagStyle *style;
    AttVal *av;

    if ( lexer->styles == NULL && NiceBody(doc) )
        return;

    node = NewNode( lexer );
    node->type = StartTag;
    node->implicit = yes;
    node->element = tmbstrdup("style");
    FindTag( doc, node );

    /* insert type attribute */
    av = NewAttributeEx( doc, "type", "text/css", '"' );
    InsertAttributeAtStart( node, av );

    body = FindBody( doc );
    lexer->txtstart = lexer->lexsize;
    if ( body )
        CleanBodyAttrs( doc, body );

    for (style = lexer->styles; style; style = style->next)
    {
        AddCharToLexer(lexer, ' ');
        AddStringLiteral(lexer, style->tag);
        AddCharToLexer(lexer, '.');
        AddStringLiteral(lexer, style->tag_class);
        AddCharToLexer(lexer, ' ');
        AddCharToLexer(lexer, '{');
        AddStringLiteral(lexer, style->properties);
        AddCharToLexer(lexer, '}');
        AddCharToLexer(lexer, '\n');
    }

    lexer->txtend = lexer->lexsize;

    InsertNodeAtEnd( node, TextToken(lexer) );

    /*
     now insert style element into document head

     doc is root node. search its children for html node
     the head node should be first child of html node
    */
    if ( NULL != (head = FindHEAD( doc )) )
        InsertNodeAtEnd( head, node );
}


/* ensure bidirectional links are consistent */
void FixNodeLinks(Node *node)
{
    Node *child;

    if (node->prev)
        node->prev->next = node;
    else
        node->parent->content = node;

    if (node->next)
        node->next->prev = node;
    else
        node->parent->last = node;

    for (child = node->content; child; child = child->next)
        child->parent = node;
}

/*
 used to strip child of node when
 the node has one and only one child
*/
static void StripOnlyChild(TidyDocImpl* doc, Node *node)
{
    Node *child;

    child = node->content;
    node->content = child->content;
    node->last = child->last;
    child->content = NULL;
    FreeNode(doc, child);

    for (child = node->content; child; child = child->next)
        child->parent = node;
}

/*
  used to strip font start and end tags.
  Extricate "element", replace it by its content and delete it.
*/
static void DiscardContainer( TidyDocImpl* doc, Node *element, Node **pnode)
{
    if (element->content)
    {
        Node *node, *parent = element->parent;

        element->last->next = element->next;

        if (element->next)
        {
            element->next->prev = element->last;
        }
        else
            parent->last = element->last;

        if (element->prev)
        {
            element->content->prev = element->prev;
            element->prev->next = element->content;
        }
        else
            parent->content = element->content;

        for (node = element->content; node; node = node->next)
            node->parent = parent;

        *pnode = element->content;

        element->next = element->content = NULL;
        FreeNode(doc, element);
    }
    else
    {
        *pnode = DiscardElement(doc, element);
    }
}

/*
  Create new string that consists of the
  combined style properties in s1 and s2

  To merge property lists, we build a linked
  list of property/values and insert properties
  into the list in order, merging values for
  the same property name.
*/
static tmbstr MergeProperties( ctmbstr s1, ctmbstr s2 )
{
    tmbstr s;
    StyleProp *prop;

    prop = CreateProps(NULL, s1);
    prop = CreateProps(prop, s2);
    s = CreatePropString(prop);
    FreeStyleProps(prop);
    return s;
}

/*
 Add style property to element, creating style
 attribute as needed and adding ; delimiter
*/
static void AddStyleProperty(TidyDocImpl* doc, Node *node, ctmbstr property )
{
    AttVal *av = AttrGetById(node, TidyAttr_STYLE);

    /* if style attribute already exists then insert property */

    if ( av )
    {
        if (av->value != NULL)
        {
            tmbstr s = MergeProperties( av->value, property );
            MemFree( av->value );
            av->value = s;
        }
        else
        {
            av->value = tmbstrdup( property );
        }
    }
    else /* else create new style attribute */
    {
        av = NewAttributeEx( doc, "style", property, '"' );
        InsertAttributeAtStart( node, av );
    }
}

static void MergeClasses(TidyDocImpl* doc, Node *node, Node *child)
{
    AttVal *av;
    tmbstr s1, s2, names;

    for (s2 = NULL, av = child->attributes; av; av = av->next)
    {
        if (attrIsCLASS(av))
        {
            s2 = av->value;
            break;
        }
    }

    for (s1 = NULL, av = node->attributes; av; av = av->next)
    {
        if (attrIsCLASS(av))
        {
            s1 = av->value;
            break;
        }
    }

    if (s1)
    {
        if (s2)  /* merge class names from both */
        {
            uint l1, l2;
            l1 = tmbstrlen(s1);
            l2 = tmbstrlen(s2);
            names = (tmbstr) MemAlloc(l1 + l2 + 2);
            tmbstrcpy(names, s1);
            names[l1] = ' ';
            tmbstrcpy(names+l1+1, s2);
            MemFree(av->value);
            av->value = names;
        }
    }
    else if (s2)  /* copy class names from child */
    {
        av = NewAttributeEx( doc, "class", s2, '"' );
        InsertAttributeAtStart( node, av );
    }
}

static void MergeStyles(TidyDocImpl* doc, Node *node, Node *child)
{
    AttVal *av;
    tmbstr s1, s2, style;

    /*
       the child may have a class attribute used
       for attaching styles, if so the class name
       needs to be copied to node's class
    */
    MergeClasses(doc, node, child);

    for (s2 = NULL, av = child->attributes; av; av = av->next)
    {
        if (attrIsSTYLE(av))
        {
            s2 = av->value;
            break;
        }
    }

    for (s1 = NULL, av = node->attributes; av; av = av->next)
    {
        if (attrIsSTYLE(av))
        {
            s1 = av->value;
            break;
        }
    }

    if (s1)
    {
        if (s2)  /* merge styles from both */
        {
            style = MergeProperties(s1, s2);
            MemFree(av->value);
            av->value = style;
        }
    }
    else if (s2)  /* copy style of child */
    {
        av = NewAttributeEx( doc, "style", s2, '"' );
        InsertAttributeAtStart( node, av );
    }
}

static ctmbstr FontSize2Name(ctmbstr size)
{
    static const ctmbstr sizes[7] =
    {
        "60%", "70%", "80%", NULL,
        "120%", "150%", "200%"
    };

    /* increment of 0.8 */
    static const ctmbstr minussizes[] =
    {
        "100%", "80%", "64%", "51%",
        "40%", "32%", "26%"
    };

    /* increment of 1.2 */
    static const ctmbstr plussizes[] =
    {
        "100%", "120%", "144%", "172%",
        "207%", "248%", "298%"
    };

    if (size[0] == '\0')
        return NULL;

    if ('0' <= size[0] && size[0] <= '6')
    {
        int n = size[0] - '0';
        return sizes[n];
    }

    if (size[0] == '-')
    {
        if ('0' <= size[1] && size[1] <= '6')
        {
            int n = size[1] - '0';
            return minussizes[n];
        }
        return "smaller"; /*"70%"; */
    }

    if ('0' <= size[1] && size[1] <= '6')
    {
        int n = size[1] - '0';
        return plussizes[n];
    }

    return "larger"; /* "140%" */
}

static void AddFontFace( TidyDocImpl* doc, Node *node, ctmbstr face )
{
    tmbchar buf[256];
    tmbsnprintf(buf, sizeof(buf), "font-family: %s", face );
    AddStyleProperty( doc, node, buf );
}

static void AddFontSize( TidyDocImpl* doc, Node* node, ctmbstr size )
{
    ctmbstr value = NULL;

    if (nodeIsP(node))
    {
        if (tmbstrcmp(size, "6") == 0)
            value = "h1";
        else if (tmbstrcmp(size, "5") == 0)
            value = "h2";
        else if (tmbstrcmp(size, "4") == 0)
            value = "h3";

        if (value)
        {
            MemFree(node->element);
            node->element = tmbstrdup(value);
            FindTag(doc, node);
            return;
        }
    }

    value = FontSize2Name(size);

    if (value)
    {
        tmbchar buf[64];
        tmbsnprintf(buf, sizeof(buf), "font-size: %s", value);
        AddStyleProperty( doc, node, buf );
    }
}

static void AddFontColor( TidyDocImpl* doc, Node *node, ctmbstr color)
{
    tmbchar buf[128];
    tmbsnprintf(buf, sizeof(buf), "color: %s", color);
    AddStyleProperty( doc, node, buf );
}

/* force alignment value to lower case */
static void AddAlign( TidyDocImpl* doc, Node *node, ctmbstr align )
{
    uint i;
    tmbchar buf[128];

    tmbstrcpy( buf, "text-align: " );
    for ( i = 12; i < sizeof(buf)/sizeof(buf[0])-1; ++i )
    {
        if ( (buf[i] = (tmbchar)ToLower(*align++)) == '\0' )
            break;
    }
    buf[i] = '\0';
    AddStyleProperty( doc, node, buf );
}

/*
 add style properties to node corresponding to
 the font face, size and color attributes
*/
static void AddFontStyles( TidyDocImpl* doc, Node *node, AttVal *av)
{
    while (av)
    {
        if (AttrHasValue(av))
        {
            if (attrIsFACE(av))
                AddFontFace( doc, node, av->value );
            else if (attrIsSIZE(av))
                AddFontSize( doc, node, av->value );
            else if (attrIsCOLOR(av))
                AddFontColor( doc, node, av->value );
        }
        av = av->next;
    }
}

/*
    Symptom: <p align=center>
    Action: <p style="text-align: center">
*/
static void TextAlign( TidyDocImpl* doc, Node* node )
{
    AttVal *av, *prev;

    prev = NULL;

    for (av = node->attributes; av; av = av->next)
    {
        if (attrIsALIGN(av))
        {
            if (prev)
                prev->next = av->next;
            else
                node->attributes = av->next;

            if (av->value)
                AddAlign( doc, node, av->value );

            FreeAttribute(doc, av);
            break;
        }

        prev = av;
    }
}

/*
   The clean up rules use the pnode argument to return the
   next node when the original node has been deleted
*/

/*
    Symptom: <dir> <li> where <li> is only child
    Action: coerce <dir> <li> to <div> with indent.
*/

static Bool Dir2Div( TidyDocImpl* doc, Node *node, Node **ARG_UNUSED(pnode))
{
    Node *child;

    if ( nodeIsDIR(node) || nodeIsUL(node) || nodeIsOL(node) )
    {
        child = node->content;

        if (child == NULL)
            return no;

        /* check child has no peers */

        if (child->next)
            return no;

        if ( !nodeIsLI(child) )
            return no;

        if ( !child->implicit )
            return no;

        /* coerce dir to div */
        node->tag = LookupTagDef( TidyTag_DIV );
        MemFree( node->element );
        node->element = tmbstrdup("div");
        AddStyleProperty( doc, node, "margin-left: 2em" );
        StripOnlyChild( doc, node );
        return yes;
    }

    return no;
}

/*
    Symptom: <center>
    Action: replace <center> by <div style="text-align: center">
*/

static Bool Center2Div( TidyDocImpl* doc, Node *node, Node **pnode)
{
    if ( nodeIsCENTER(node) )
    {
        if ( cfgBool(doc, TidyDropFontTags) )
        {
            if (node->content)
            {
                Node *last = node->last;
                DiscardContainer( doc, node, pnode );

                node = InferredTag(doc, TidyTag_BR);
                InsertNodeAfterElement(last, node);
            }
            else
            {
                Node *prev = node->prev, *next = node->next,
                     *parent = node->parent;
                DiscardContainer( doc, node, pnode );

                node = InferredTag(doc, TidyTag_BR);
                if (next)
                    InsertNodeBeforeElement(next, node);
                else if (prev)
                    InsertNodeAfterElement(prev, node);
                else
                    InsertNodeAtStart(parent, node);
            }

            return yes;
        }

        RenameElem( node, TidyTag_DIV );
        AddStyleProperty( doc, node, "text-align: center" );
        return yes;
    }

    return no;
}

/* Copy child attributes to node. Duplicate attributes are overwritten.
   Unique attributes (such as ID) disable the action.
   Attributes style and class are not dealt with. A call to MergeStyles
   will do that.
*/
static Bool CopyAttrs( TidyDocImpl* doc, Node *node, Node *child)
{
    AttVal *av1, *av2;
    TidyAttrId id;

    /* Detect attributes that cannot be merged or overwritten. */
    if (AttrGetById(child, TidyAttr_ID) != NULL
        && AttrGetById(node, TidyAttr_ID) != NULL)
        return no;

    /* Move child attributes to node. Attributes in node
     can be overwritten or merged. */
    for (av2 = child->attributes; av2; )
    {
        /* Dealt by MergeStyles. */
        if (attrIsSTYLE(av2) || attrIsCLASS(av2))
        {
            av2 = av2->next;
            continue;
        }
        /* Avoid duplicates in node */
        if ((id=AttrId(av2)) != TidyAttr_UNKNOWN
            && (av1=AttrGetById(node, id))!= NULL)
            RemoveAttribute( doc, node, av1 );

        /* Move attribute from child to node */
        DetachAttribute( child, av2 );
        av1 = av2;
        av2 = av2->next;
        av1->next = NULL;
        InsertAttributeAtEnd( node, av1 );
    }

    return yes;
}

/*
    Symptom <XX><XX>...</XX></XX>
    Action: merge the two XXs

  For instance, this is useful after nested <dir>s used by Word
  for indenting have been converted to <div>s

  If state is "no", no merging.
  If state is "yes", inner element is discarded. Only Style and Class
  attributes are merged using MergeStyles().
  If state is "auto", atttibutes are merged as described in CopyAttrs().
  Style and Class attributes are merged using MergeStyles().
*/
static Bool MergeNestedElements( TidyDocImpl* doc,
                                 TidyTagId Id, TidyTriState state, Node *node,
                                 Node **ARG_UNUSED(pnode))
{
    Node *child;

    if ( state == TidyNoState
         || !TagIsId(node, Id) )
        return no;

    child = node->content;

    if ( child == NULL
         || child->next != NULL
         || !TagIsId(child, Id) )
        return no;

    if ( state == TidyAutoState
         && CopyAttrs(doc, node, child) == no )
        return no;

    MergeStyles( doc, node, child );
    StripOnlyChild( doc, node );
    return yes;
}

/*
    Symptom: <ul><li><ul>...</ul></li></ul>
    Action: discard outer list
*/

static Bool NestedList( TidyDocImpl* doc, Node *node, Node **pnode )
{
    Node *child, *list;

    if ( nodeIsUL(node) || nodeIsOL(node) )
    {
        child = node->content;

        if (child == NULL)
            return no;

        /* check child has no peers */

        if (child->next)
            return no;

        list = child->content;

        if (!list)
            return no;

        if (list->tag != node->tag)
            return no;

        /* check list has no peers */
        if (list->next)
            return no;

        *pnode = list;  /* Set node to resume iteration */

        /* move inner list node into position of outer node */
        list->prev = node->prev;
        list->next = node->next;
        list->parent = node->parent;
        FixNodeLinks(list);

        /* get rid of outer ul and its li */
        child->content = NULL;
        FreeNode( doc, child ); /* See test #427841. */
        child = NULL;
        node->content = NULL;
        node->next = NULL;
        FreeNode( doc, node );
        node = NULL;

        /*
          If prev node was a list the chances are this node
          should be appended to that list. Word has no way of
          recognizing nested lists and just uses indents
        */

        if (list->prev)
        {
            if ( (nodeIsUL(list->prev) || nodeIsOL(list->prev))
                 && list->prev->last )
            {
                node = list;
                list = node->prev;

                child = list->last;  /* <li> */

                list->next = node->next;
                FixNodeLinks(list);

                node->parent = child;
                node->next = NULL;
                node->prev = child->last;
                FixNodeLinks(node);
                CleanNode( doc, node );
            }
        }

        return yes;
    }

    return no;
}

/*
  Some necessary conditions to apply BlockStyle().
 */

static Bool CanApplyBlockStyle( Node *node )
{
    if (node->tag->model & (CM_BLOCK | CM_LIST | CM_DEFLIST | CM_TABLE)
        && !nodeIsTABLE(node) && !nodeIsTR(node) && !nodeIsLI(node) )
    {
        return yes;
    }
    return no;
}

/*
  Symptom: the only child of a block-level element is a
  presentation element such as B, I or FONT

  Action: add style "font-weight: bold" to the block and
  strip the <b> element, leaving its children.

  example:

    <p>
      <b><font face="Arial" size="6">Draft Recommended Practice</font></b>
    </p>

  becomes:

      <p style="font-weight: bold; font-family: Arial; font-size: 6">
        Draft Recommended Practice
      </p>

  This code also replaces the align attribute by a style attribute.
  However, to avoid CSS problems with Navigator 4, this isn't done
  for the elements: caption, tr and table
*/
static Bool BlockStyle( TidyDocImpl* doc, Node *node, Node **ARG_UNUSED(pnode) )
{
    Node *child;

    if (CanApplyBlockStyle(node))
    {
        /* check for align attribute */
        if ( !nodeIsCAPTION(node) )
            TextAlign( doc, node );

        child = node->content;
        if (child == NULL)
            return no;

        /* check child has no peers */
        if (child->next)
            return no;

        if ( nodeIsB(child) )
        {
            MergeStyles( doc, node, child );
            AddStyleProperty( doc, node, "font-weight: bold" );
            StripOnlyChild( doc, node );
            return yes;
        }

        if ( nodeIsI(child) )
        {
            MergeStyles( doc, node, child );
            AddStyleProperty( doc, node, "font-style: italic" );
            StripOnlyChild( doc, node );
            return yes;
        }

        if ( nodeIsFONT(child) )
        {
            MergeStyles( doc, node, child );
            AddFontStyles( doc, node, child->attributes );
            StripOnlyChild( doc, node );
            return yes;
        }
    }

    return no;
}

/* the only child of table cell or an inline element such as em */
static Bool InlineStyle( TidyDocImpl* doc, Node *node, Node **ARG_UNUSED(pnode) )
{
    Node *child;

    if ( !nodeIsFONT(node) && nodeHasCM(node, CM_INLINE|CM_ROW) )
    {
        child = node->content;

        if (child == NULL)
            return no;

        /* check child has no peers */

        if (child->next)
            return no;

        if ( nodeIsB(child) && cfgBool(doc, TidyLogicalEmphasis) )
        {
            MergeStyles( doc, node, child );
            AddStyleProperty( doc, node, "font-weight: bold" );
            StripOnlyChild( doc, node );
            return yes;
        }

        if ( nodeIsI(child) && cfgBool(doc, TidyLogicalEmphasis) )
        {
            MergeStyles( doc, node, child );
            AddStyleProperty( doc, node, "font-style: italic" );
            StripOnlyChild( doc, node );
            return yes;
        }

        if ( nodeIsFONT(child) )
        {
            MergeStyles( doc, node, child );
            AddFontStyles( doc, node, child->attributes );
            StripOnlyChild( doc, node );
            return yes;
        }
    }

    return no;
}

/*
  Replace font elements by span elements, deleting
  the font element's attributes and replacing them
  by a single style attribute.
*/
static Bool Font2Span( TidyDocImpl* doc, Node *node, Node **pnode )
{
    AttVal *av, *style, *next;

    if ( nodeIsFONT(node) )
    {
        if ( cfgBool(doc, TidyDropFontTags) )
        {
            DiscardContainer( doc, node, pnode );
            return yes;
        }

        /* if FONT is only child of parent element then leave alone
          Do so only if BlockStyle may be succesful. */
        if ( node->parent->content == node && node->next == NULL &&
             CanApplyBlockStyle(node->parent) )
            return no;

        AddFontStyles( doc, node, node->attributes );

        /* extract style attribute and free the rest */
        av = node->attributes;
        style = NULL;

        while (av)
        {
            next = av->next;

            if (attrIsSTYLE(av))
            {
                av->next = NULL;
                style = av;
            }
            else
            {
                FreeAttribute( doc, av );
            }
            av = next;
        }

        node->attributes = style;
        RenameElem( node, TidyTag_SPAN );
        return yes;
    }

    return no;
}

/*
  Applies all matching rules to a node.
*/
Node* CleanNode( TidyDocImpl* doc, Node *node )
{
    Node *next = NULL;
    TidyTriState mergeDivs = cfgAutoBool(doc, TidyMergeDivs);

    for (next = node; nodeIsElement(node); node = next)
    {
        if ( Dir2Div(doc, node, &next) )
            continue;

        /* Special case: true result means
        ** that arg node and its parent no longer exist.
        ** So we must jump back up the CreateStyleProperties()
        ** call stack until we have a valid node reference.
        */
        if ( NestedList(doc, node, &next) )
            return next;

        if ( Center2Div(doc, node, &next) )
            continue;

        if ( MergeNestedElements(doc, TidyTag_DIV, mergeDivs, node, &next) )
            continue;

        if ( BlockStyle(doc, node, &next) )
            continue;

        if ( InlineStyle(doc, node, &next) )
            continue;

        if ( Font2Span(doc, node, &next) )
            continue;

        break;
    }

    return next;
}

/* Special case: if the current node is destroyed by
** CleanNode() lower in the tree, this node and its parent
** no longer exist.  So we must jump back up the CleanTree()
** call stack until we have a valid node reference.
*/

static Node* CleanTree( TidyDocImpl* doc, Node *node )
{
    if (node->content)
    {
        Node *child;
        for (child = node->content; child != NULL; child = child->next)
        {
            child = CleanTree( doc, child );
            if ( !child )
                break;
        }
    }

    return CleanNode( doc, node );
}

static void DefineStyleRules( TidyDocImpl* doc, Node *node )
{
    Node *child;

    if (node->content)
    {
        for (child = node->content;
                child != NULL; child = child->next)
        {
            DefineStyleRules( doc, child );
        }
    }

    Style2Rule( doc, node );
}

void CleanDocument( TidyDocImpl* doc )
{
    /* placeholder.  CleanTree()/CleanNode() will not
    ** zap root element 
    */
    CleanTree( doc, &doc->root );

    if ( cfgBool(doc, TidyMakeClean) )
    {
        DefineStyleRules( doc, &doc->root );
        CreateStyleElement( doc );
    }
}

/* simplifies <b><b> ... </b> ...</b> etc. */
void NestedEmphasis( TidyDocImpl* doc, Node* node )
{
    Node *next;

    while (node)
    {
        next = node->next;

        if ( (nodeIsB(node) || nodeIsI(node))
             && node->parent && node->parent->tag == node->tag)
        {
            /* strip redundant inner element */
            DiscardContainer( doc, node, &next );
            node = next;
            continue;
        }

        if ( node->content )
            NestedEmphasis( doc, node->content );

        node = next;
    }
}



/* replace i by em and b by strong */
void EmFromI( TidyDocImpl* doc, Node* node )
{
    while (node)
    {
        if ( nodeIsI(node) )
            RenameElem( node, TidyTag_EM );
        else if ( nodeIsB(node) )
            RenameElem( node, TidyTag_STRONG );

        if ( node->content )
            EmFromI( doc, node->content );

        node = node->next;
    }
}

static Bool HasOneChild(Node *node)
{
    return (node->content && node->content->next == NULL);
}

/*
 Some people use dir or ul without an li
 to indent the content. The pattern to
 look for is a list with a single implicit
 li. This is recursively replaced by an
 implicit blockquote.
*/
void List2BQ( TidyDocImpl* doc, Node* node )
{
    while (node)
    {
        if (node->content)
            List2BQ( doc, node->content );

        if ( node->tag && node->tag->parser == ParseList &&
             HasOneChild(node) && node->content->implicit )
        {
            StripOnlyChild( doc, node );
            RenameElem( node, TidyTag_BLOCKQUOTE );
            node->implicit = yes;
        }

        node = node->next;
    }
}


/*
 Replace implicit blockquote by div with an indent
 taking care to reduce nested blockquotes to a single
 div with the indent set to match the nesting depth
*/
void BQ2Div( TidyDocImpl* doc, Node *node )
{
    tmbchar indent_buf[ 32 ];
    uint indent;

    while (node)
    {
        if ( nodeIsBLOCKQUOTE(node) && node->implicit )
        {
            indent = 1;

            while( HasOneChild(node) &&
                   nodeIsBLOCKQUOTE(node->content) &&
                   node->implicit)
            {
                ++indent;
                StripOnlyChild( doc, node );
            }

            if (node->content)
                BQ2Div( doc, node->content );

            tmbsnprintf(indent_buf, sizeof(indent_buf), "margin-left: %dem",
                        2*indent);

            RenameElem( node, TidyTag_DIV );
            AddStyleProperty(doc, node, indent_buf );
        }
        else if (node->content)
            BQ2Div( doc, node->content );

        node = node->next;
    }
}


Node* FindEnclosingCell( TidyDocImpl* ARG_UNUSED(doc), Node *node)
{
    Node *check;

    for ( check=node; check; check = check->parent )
    {
      if ( nodeIsTD(check) )
        return check;
    }
    return NULL;
}

/* node is <![if ...]> prune up to <![endif]> */
static Node* PruneSection( TidyDocImpl* doc, Node *node )
{
    Lexer* lexer = doc->lexer;

    for (;;)
    {
        ctmbstr lexbuf = lexer->lexbuf + node->start;
        if ( tmbstrncmp(lexbuf, "if !supportEmptyParas", 21) == 0 )
        {
          Node* cell = FindEnclosingCell( doc, node );
          if ( cell )
          {
            /* Need to put &nbsp; into cell so it doesn't look weird
            */
            Node* nbsp = NewLiteralTextNode( lexer, "\240" );
            assert( (byte)'\240' == (byte)160 );
            InsertNodeBeforeElement( node, nbsp );
          }
        }

        /* discard node and returns next */
        node = DiscardElement( doc, node );

        if (node == NULL)
            return NULL;
        
        if (node->type == SectionTag)
        {
            if (tmbstrncmp(lexer->lexbuf + node->start, "if", 2) == 0)
            {
                node = PruneSection( doc, node );
                continue;
            }

            if (tmbstrncmp(lexer->lexbuf + node->start, "endif", 5) == 0)
            {
                node = DiscardElement( doc, node );
                break;
            }
        }
    }

    return node;
}

void DropSections( TidyDocImpl* doc, Node* node )
{
    Lexer* lexer = doc->lexer;
    while (node)
    {
        if (node->type == SectionTag)
        {
            /* prune up to matching endif */
            if ((tmbstrncmp(lexer->lexbuf + node->start, "if", 2) == 0) &&
                (tmbstrncmp(lexer->lexbuf + node->start, "if !vml", 7) != 0)) /* #444394 - fix 13 Sep 01 */
            {
                node = PruneSection( doc, node );
                continue;
            }

            /* discard others as well */
            node = DiscardElement( doc, node );
            continue;
        }

        if (node->content)
            DropSections( doc, node->content );

        node = node->next;
    }
}

static void PurgeWord2000Attributes( TidyDocImpl* ARG_UNUSED(doc), Node* node )
{
    AttVal *attr, *next, *prev = NULL;

    for ( attr = node->attributes; attr; attr = next )
    {
        next = attr->next;

        /* special check for class="Code" denoting pre text */
        /* Pass thru user defined styles as HTML class names */
        if (attrIsCLASS(attr))
        {
            if (AttrValueIs(attr, "Code") ||
                 tmbstrncmp(attr->value, "Mso", 3) != 0 )
            {
                prev = attr;
                continue;
            }
        }

        if (attrIsCLASS(attr) ||
            attrIsSTYLE(attr) ||
            attrIsLANG(attr)  ||
             ( (attrIsHEIGHT(attr) || attrIsWIDTH(attr)) &&
               (nodeIsTD(node) || nodeIsTR(node) || nodeIsTH(node)) ) ||
             (attr->attribute && tmbstrncmp(attr->attribute, "x:", 2) == 0) )
        {
            if (prev)
                prev->next = next;
            else
                node->attributes = next;

            FreeAttribute( doc, attr );
        }
        else
            prev = attr;
    }
}

/* Word2000 uses span excessively, so we strip span out */
static Node* StripSpan( TidyDocImpl* doc, Node* span )
{
    Node *node, *prev = NULL, *content;

    /*
     deal with span elements that have content
     by splicing the content in place of the span
     after having processed it
    */

    CleanWord2000( doc, span->content );
    content = span->content;

    if (span->prev)
        prev = span->prev;
    else if (content)
    {
        node = content;
        content = content->next;
        RemoveNode(node);
        InsertNodeBeforeElement(span, node);
        prev = node;
    }

    while (content)
    {
        node = content;
        content = content->next;
        RemoveNode(node);
        InsertNodeAfterElement(prev, node);
        prev = node;
    }

    if (span->next == NULL)
        span->parent->last = prev;

    node = span->next;
    span->content = NULL;
    DiscardElement( doc, span );
    return node;
}

/* map non-breaking spaces to regular spaces */
void NormalizeSpaces(Lexer *lexer, Node *node)
{
    while ( node )
    {
        if ( node->content )
            NormalizeSpaces( lexer, node->content );

        if (nodeIsText(node))
        {
            uint i, c;
            tmbstr p = lexer->lexbuf + node->start;

            for (i = node->start; i < node->end; ++i)
            {
                c = (byte) lexer->lexbuf[i];

                /* look for UTF-8 multibyte character */
                if ( c > 0x7F )
                    i += GetUTF8( lexer->lexbuf + i, &c );

                if ( c == 160 )
                    c = ' ';

                p = PutUTF8(p, c);
            }
            node->end = p - lexer->lexbuf;
        }

        node = node->next;
    }
}

/* used to hunt for hidden preformatted sections */
Bool NoMargins(Node *node)
{
    AttVal *attval = AttrGetById(node, TidyAttr_STYLE);

    if ( !AttrHasValue(attval) )
        return no;

    /* search for substring "margin-top: 0" */
    if (!tmbsubstr(attval->value, "margin-top: 0"))
        return no;

    /* search for substring "margin-bottom: 0" */
    if (!tmbsubstr(attval->value, "margin-bottom: 0"))
        return no;

    return yes;
}

/* does element have a single space as its content? */
static Bool SingleSpace( Lexer* lexer, Node* node )
{
    if ( node->content )
    {
        node = node->content;

        if ( node->next != NULL )
            return no;

        if ( node->type != TextNode )
            return no;

        if ( (node->end - node->start) == 1 &&
             lexer->lexbuf[node->start] == ' ' )
            return yes;

        if ( (node->end - node->start) == 2 )
        {
            uint c = 0;
            GetUTF8( lexer->lexbuf + node->start, &c );
            if ( c == 160 )
                return yes;
        }
    }

    return no;
}

/*
 This is a major clean up to strip out all the extra stuff you get
 when you save as web page from Word 2000. It doesn't yet know what
 to do with VML tags, but these will appear as errors unless you
 declare them as new tags, such as o:p which needs to be declared
 as inline.
*/
void CleanWord2000( TidyDocImpl* doc, Node *node)
{
    /* used to a list from a sequence of bulletted p's */
    Lexer* lexer = doc->lexer;
    Node* list = NULL;

    while ( node )
    {
        /* get rid of Word's xmlns attributes */
        if ( nodeIsHTML(node) )
        {
            /* check that it's a Word 2000 document */
            if ( !GetAttrByName(node, "xmlns:o") &&
                 !cfgBool(doc, TidyMakeBare) )
                return;

            FreeAttrs( doc, node );
        }

        /* fix up preformatted sections by looking for a
        ** sequence of paragraphs with zero top/bottom margin
        */
        if ( nodeIsP(node) )
        {
            if (NoMargins(node))
            {
                Node *pre, *next;
                CoerceNode(doc, node, TidyTag_PRE, no, yes);

                PurgeWord2000Attributes( doc, node );

                if (node->content)
                    CleanWord2000( doc, node->content );

                pre = node;
                node = node->next;

                /* continue to strip p's */

                while ( nodeIsP(node) && NoMargins(node) )
                {
                    next = node->next;
                    RemoveNode(node);
                    InsertNodeAtEnd(pre, NewLineNode(lexer));
                    InsertNodeAtEnd(pre, node);
                    StripSpan( doc, node );
                    node = next;
                }

                if (node == NULL)
                    break;
            }
        }

        if (node->tag && (node->tag->model & CM_BLOCK)
            && SingleSpace(lexer, node))
        {
            node = StripSpan( doc, node );
            continue;
        }
        /* discard Word's style verbiage */
        if ( nodeIsSTYLE(node) || nodeIsMETA(node) ||
             node->type == CommentTag )
        {
            node = DiscardElement( doc, node );
            continue;
        }

        /* strip out all span and font tags Word scatters so liberally! */
        if ( nodeIsSPAN(node) || nodeIsFONT(node) )
        {
            node = StripSpan( doc, node );
            continue;
        }

        if ( nodeIsLINK(node) )
        {
            AttVal *attr = AttrGetById(node, TidyAttr_REL);

            if (AttrValueIs(attr, "File-List"))
            {
                node = DiscardElement( doc, node );
                continue;
            }
        }

        /* discards <o:p> which encodes the paragraph mark */
        if ( node->tag && tmbstrcmp(node->tag->name,"o:p")==0)
        {
            Node* next;
            DiscardContainer( doc, node, &next );
            node = next;
            continue;
        }

        /* discard empty paragraphs */

        if ( node->content == NULL && nodeIsP(node) )
        {
            /*  Use the existing function to ensure consistency */
            node = TrimEmptyElement( doc, node );
            continue;
        }

        if ( nodeIsP(node) )
        {
            AttVal *attr, *atrStyle;
            
            attr = AttrGetById(node, TidyAttr_CLASS);
            atrStyle = AttrGetById(node, TidyAttr_STYLE);
            /*
               (JES) Sometimes Word marks a list item with the following hokie syntax
               <p class="MsoNormal" style="...;mso-list:l1 level1 lfo1;
                translate these into <li>
            */
            /* map sequence of <p class="MsoListBullet"> to <ul>...</ul> */
            /* map <p class="MsoListNumber"> to <ol>...</ol> */
            if ( AttrValueIs(attr, "MsoListBullet") ||
                 AttrValueIs(attr, "MsoListNumber") ||
                 AttrContains(atrStyle, "mso-list:") )
            {
                TidyTagId listType = TidyTag_UL;
                if (AttrValueIs(attr, "MsoListNumber"))
                    listType = TidyTag_OL;

                CoerceNode(doc, node, TidyTag_LI, no, yes);

                if ( !list || TagId(list) != listType )
                {
                    const Dict* tag = LookupTagDef( listType );
                    list = InferredTag(doc, tag->id);
                    InsertNodeBeforeElement(node, list);
                }

                PurgeWord2000Attributes( doc, node );

                if ( node->content )
                    CleanWord2000( doc, node->content );

                /* remove node and append to contents of list */
                RemoveNode(node);
                InsertNodeAtEnd(list, node);
                node = list;
            }
            /* map sequence of <p class="Code"> to <pre>...</pre> */
            else if (AttrValueIs(attr, "Code"))
            {
                Node *br = NewLineNode(lexer);
                NormalizeSpaces(lexer, node->content);

                if ( !list || TagId(list) != TidyTag_PRE )
                {
                    list = InferredTag(doc, TidyTag_PRE);
                    InsertNodeBeforeElement(node, list);
                }

                /* remove node and append to contents of list */
                RemoveNode(node);
                InsertNodeAtEnd(list, node);
                StripSpan( doc, node );
                InsertNodeAtEnd(list, br);
                node = list->next;
            }
            else
                list = NULL;
        }
        else
            list = NULL;

        if (!node)
            return;

        /* strip out style and class attributes */
        if (nodeIsElement(node))
            PurgeWord2000Attributes( doc, node );

        if (node->content)
            CleanWord2000( doc, node->content );

        node = node->next;
    }
}

Bool IsWord2000( TidyDocImpl* doc )
{
    AttVal *attval;
    Node *node, *head;
    Node *html = FindHTML( doc );

    if (html && GetAttrByName(html, "xmlns:o"))
        return yes;
    
    /* search for <meta name="GENERATOR" content="Microsoft ..."> */
    head = FindHEAD( doc );

    if (head)
    {
        for (node = head->content; node; node = node->next)
        {
            if ( !nodeIsMETA(node) )
                continue;

            attval = AttrGetById( node, TidyAttr_NAME );

            if ( !AttrValueIs(attval, "generator") )
                continue;

            attval =  AttrGetById( node, TidyAttr_CONTENT );

            if ( AttrContains(attval, "Microsoft") )
                return yes;
        }
    }

    return no;
}

/* where appropriate move object elements from head to body */
void BumpObject( TidyDocImpl* doc, Node *html )
{
    Node *node, *next, *head = NULL, *body = NULL;

    if (!html)
        return;

    for ( node = html->content; node != NULL; node = node->next )
    {
        if ( nodeIsHEAD(node) )
            head = node;

        if ( nodeIsBODY(node) )
            body = node;
    }

    if ( head != NULL && body != NULL )
    {
        for (node = head->content; node != NULL; node = next)
        {
            next = node->next;

            if ( nodeIsOBJECT(node) )
            {
                Node *child;
                Bool bump = no;

                for (child = node->content; child != NULL; child = child->next)
                {
                    /* bump to body unless content is param */
                    if ( (nodeIsText(child) && !IsBlank(doc->lexer, node))
                         || !nodeIsPARAM(child) )
                    {
                            bump = yes;
                            break;
                    }
                }

                if ( bump )
                {
                    RemoveNode( node );
                    InsertNodeAtStart( body, node );
                }
            }
        }
    }
}

/* This is disabled due to http://tidy.sf.net/bug/681116 */
#if 0
void FixBrakes( TidyDocImpl* pDoc, Node *pParent )
{
    Node *pNode;
    Bool bBRDeleted = no;

    if (NULL == pParent)
        return;

    /*  First, check the status of All My Children  */
    pNode = pParent->content;
    while (NULL != pNode )
    {
        /* The node may get trimmed, so save the next pointer, if any */
        Node *pNext = pNode->next;
        FixBrakes( pDoc, pNode );
        pNode = pNext;
    }


    /*  As long as my last child is a <br />, move it to my last peer  */
    if ( nodeCMIsBlock( pParent ))
    { 
        for ( pNode = pParent->last; 
              NULL != pNode && nodeIsBR( pNode ); 
              pNode = pParent->last ) 
        {
            if ( NULL == pNode->attributes && no == bBRDeleted )
            {
                DiscardElement( pDoc, pNode );
                bBRDeleted = yes;
            }
            else
            {
                RemoveNode( pNode );
                InsertNodeAfterElement( pParent, pNode );
            }
        }
        TrimEmptyElement( pDoc, pParent );
    }
}
#endif

void VerifyHTTPEquiv(TidyDocImpl* pDoc, Node *head)
{
    Node *pNode;
    StyleProp *pFirstProp = NULL, *pLastProp = NULL, *prop = NULL;
    tmbstr s, pszBegin, pszEnd;
    ctmbstr enc = GetEncodingNameFromTidyId(cfg(pDoc, TidyOutCharEncoding));

    if (!enc)
        return;

    if (!nodeIsHEAD(head))
        head = FindHEAD(pDoc);

    if (!head)
        return;

    /* Find any <meta http-equiv='Content-Type' content='...' /> */
    for (pNode = head->content; NULL != pNode; pNode = pNode->next)
    {
        AttVal* httpEquiv = AttrGetById(pNode, TidyAttr_HTTP_EQUIV);
        AttVal* metaContent = AttrGetById(pNode, TidyAttr_CONTENT);

        if ( !nodeIsMETA(pNode) || !metaContent ||
             !AttrValueIs(httpEquiv, "Content-Type") )
            continue;

        pszBegin = s = tmbstrdup( metaContent->value );
        while (pszBegin && *pszBegin)
        {
            while (isspace( *pszBegin ))
                pszBegin++;
            pszEnd = pszBegin;
            while ('\0' != *pszEnd && ';' != *pszEnd)
                pszEnd++;
            if (';' == *pszEnd )
                *(pszEnd++) = '\0';
            if (pszEnd > pszBegin)
            {
                prop = (StyleProp *)MemAlloc(sizeof(StyleProp));
                prop->name = tmbstrdup( pszBegin );
                prop->value = NULL;
                prop->next = NULL;

                if (NULL != pLastProp)
                    pLastProp->next = prop;
                else
                    pFirstProp = prop;

                pLastProp = prop;
                pszBegin = pszEnd;
            }
        }
        MemFree( s );

        /*  find the charset property */
        for (prop = pFirstProp; NULL != prop; prop = prop->next)
        {
            if (0 != tmbstrncasecmp( prop->name, "charset", 7 ))
                continue;

            MemFree( prop->name );
            prop->name = (tmbstr)MemAlloc( 8 + tmbstrlen(enc) + 1 );
            tmbstrcpy(prop->name, "charset=");
            tmbstrcpy(prop->name+8, enc);
            s = CreatePropString( pFirstProp );
            MemFree( metaContent->value );
            metaContent->value = s;
            break;
        }
        /* #718127, prevent memory leakage */
        FreeStyleProps(pFirstProp);
        pFirstProp = NULL;
        pLastProp = NULL;
    }
}

void DropComments(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (node->type == CommentTag)
        {
            RemoveNode(node);
            FreeNode(doc, node);
            node = next;
            continue;
        }

        if (node->content)
            DropComments(doc, node->content);

        node = next;
    }
}

void DropFontElements(TidyDocImpl* doc, Node* node, Node **ARG_UNUSED(pnode))
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (nodeIsFONT(node))
        {
            DiscardContainer(doc, node, &next);
            node = next;
            continue;
        }

        if (node->content)
            DropFontElements(doc, node->content, &next);

        node = next;
    }
}

void WbrToSpace(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (nodeIsWBR(node))
        {
            Node* text;
            text = NewLiteralTextNode(doc->lexer, " ");
            InsertNodeAfterElement(node, text);
            RemoveNode(node);
            FreeNode(doc, node);
            node = next;
            continue;
        }

        if (node->content)
            WbrToSpace(doc, node->content);

        node = next;
   }
}

/*
  Filters from Word and PowerPoint often use smart
  quotes resulting in character codes between 128
  and 159. Unfortunately, the corresponding HTML 4.0
  entities for these are not widely supported. The
  following converts dashes and quotation marks to
  the nearest ASCII equivalent. My thanks to
  Andrzej Novosiolov for his help with this code.

  Note: The old code in the pretty printer applied
  this to all node types and attribute values while
  this routine applies it only to text nodes. First,
  Microsoft Office products rarely put the relevant
  characters into these tokens, second support for
  them is much better now and last but not least, it
  can be harmful to replace these characters since
  US-ASCII quote marks are often used as syntax
  characters, a simple

    <a onmouseover="alert('&#x2018;')">...</a>

  would be broken if the U+2018 is replaced by "'".
  The old code would neither take care whether the
  quote mark is already used as delimiter,

    <p title='&#x2018;'>...</p>

  got
  
    <p title='''>...</p>

  Since browser support is much better nowadays and
  high-quality typography is better than ASCII it'd
  be probably a good idea to drop the feature...
*/
void DowngradeTypography(TidyDocImpl* doc, Node* node)
{
    Node* next;
    Lexer* lexer = doc->lexer;

    while (node)
    {
        next = node->next;

        if (nodeIsText(node))
        {
            uint i, c;
            tmbstr p = lexer->lexbuf + node->start;

            for (i = node->start; i < node->end; ++i)
            {
                c = (unsigned char) lexer->lexbuf[i];

                if (c > 0x7F)
                    i += GetUTF8(lexer->lexbuf + i, &c);

                if (c >= 0x2013 && c <= 0x201E)
                {
                    switch (c)
                    {
                    case 0x2013: /* en dash */
                    case 0x2014: /* em dash */
                        c = '-';
                        break;
                    case 0x2018: /* left single  quotation mark */
                    case 0x2019: /* right single quotation mark */
                    case 0x201A: /* single low-9 quotation mark */
                        c = '\'';
                        break;
                    case 0x201C: /* left double  quotation mark */
                    case 0x201D: /* right double quotation mark */
                    case 0x201E: /* double low-9 quotation mark */
                        c = '"';
                        break;
                    }
                }

                p = PutUTF8(p, c);
            }

            node->end = p - lexer->lexbuf;
        }

        if (node->content)
            DowngradeTypography(doc, node->content);

        node = next;
    }
}

void ReplacePreformattedSpaces(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (node->tag && node->tag->parser == ParsePre)
        {
            NormalizeSpaces(doc->lexer, node->content);
            node = next;
            continue;
        }

        if (node->content)
            ReplacePreformattedSpaces(doc, node->content);

        node = next;
    }
}

void ConvertCDATANodes(TidyDocImpl* doc, Node* node)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (node->type == CDATATag)
            node->type = TextNode;

        if (node->content)
            ConvertCDATANodes(doc, node->content);

        node = next;
    }
}

/*
  FixLanguageInformation ensures that the document contains (only)
  the attributes for language information desired by the output
  document type. For example, for XHTML 1.0 documents both
  'xml:lang' and 'lang' are desired, for XHTML 1.1 only 'xml:lang'
  is desired and for HTML 4.01 only 'lang' is desired.
*/
void FixLanguageInformation(TidyDocImpl* doc, Node* node, Bool wantXmlLang, Bool wantLang)
{
    Node* next;

    while (node)
    {
        next = node->next;

        /* todo: report modifications made here to the report system */

        if (nodeIsElement(node))
        {
            AttVal* lang = AttrGetById(node, TidyAttr_LANG);
            AttVal* xmlLang = AttrGetById(node, TidyAttr_XML_LANG);

            if (lang && xmlLang)
            {
                /*
                  todo: check whether both attributes are in sync,
                  here or elsewhere, where elsewhere is probably
                  preferable.
                  AD - March 2005: not mandatory according the standards.
                */
            }
            else if (lang && wantXmlLang)
            {
                if (NodeAttributeVersions( node, TidyAttr_XML_LANG )
                    & doc->lexer->versionEmitted)
                    RepairAttrValue(doc, node, "xml:lang", lang->value);
            }
            else if (xmlLang && wantLang)
            {
                if (NodeAttributeVersions( node, TidyAttr_LANG )
                    & doc->lexer->versionEmitted)
                    RepairAttrValue(doc, node, "lang", xmlLang->value);
            }

            if (lang && !wantLang)
                RemoveAttribute(doc, node, lang);
            
            if (xmlLang && !wantXmlLang)
                RemoveAttribute(doc, node, xmlLang);
        }

        if (node->content)
            FixLanguageInformation(doc, node->content, wantXmlLang, wantLang);

        node = next;
    }
}

/*
  Set/fix/remove <html xmlns='...'>
*/
void FixXhtmlNamespace(TidyDocImpl* doc, Bool wantXmlns)
{
    Node* html = FindHTML(doc);
    AttVal* xmlns;

    if (!html)
        return;

    xmlns = AttrGetById(html, TidyAttr_XMLNS);

    if (wantXmlns)
    {
        if (!AttrValueIs(xmlns, XHTML_NAMESPACE))
            RepairAttrValue(doc, html, "xmlns", XHTML_NAMESPACE);
    }
    else if (xmlns)
    {
        RemoveAttribute(doc, html, xmlns);
    }
}

/*
  ...
*/
void FixAnchors(TidyDocImpl* doc, Node *node, Bool wantName, Bool wantId)
{
    Node* next;

    while (node)
    {
        next = node->next;

        if (IsAnchorElement(doc, node))
        {
            AttVal *name = AttrGetById(node, TidyAttr_NAME);
            AttVal *id = AttrGetById(node, TidyAttr_ID);

            /* todo: how are empty name/id attributes handled? */

            if (name && id)
            {
                Bool NameHasValue = AttrHasValue(name);
                Bool IdHasValue = AttrHasValue(id);
                if ( (NameHasValue != IdHasValue) ||
                     (NameHasValue && IdHasValue &&
                     tmbstrcmp(name->value, id->value) != 0 ) )
                    ReportAttrError( doc, node, name, ID_NAME_MISMATCH);
            }
            else if (name && wantId)
            {
                if (NodeAttributeVersions( node, TidyAttr_ID )
                    & doc->lexer->versionEmitted)
                {
                    if (IsValidHTMLID(name->value))
                    {
                        RepairAttrValue(doc, node, "id", name->value);
                    }
                    else
                    {
                        ReportAttrError(doc, node, name, INVALID_XML_ID);
                    }
                 }
            }
            else if (id && wantName)
            {
                if (NodeAttributeVersions( node, TidyAttr_NAME )
                    & doc->lexer->versionEmitted)
                    /* todo: do not assume id is valid */
                    RepairAttrValue(doc, node, "name", id->value);
            }

            if (id && !wantId)
                RemoveAttribute(doc, node, id);
            
            if (name && !wantName)
                RemoveAttribute(doc, node, name);

            if (AttrGetById(node, TidyAttr_NAME) == NULL &&
                AttrGetById(node, TidyAttr_ID) == NULL)
                RemoveAnchorByNode(doc, node);
        }

        if (node->content)
            FixAnchors(doc, node->content, wantName, wantId);

        node = next;
    }
}
