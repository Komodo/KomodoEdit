#ifndef __CONFIG_H__
#define __CONFIG_H__

/* config.h -- read config file and manage config properties
  
  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/03/31 13:10:34 $ 
    $Revision: 1.10 $ 

  config files associate a property name with a value.

  // comments can start at the beginning of a line
  # comments can start at the beginning of a line
  name: short values fit onto one line
  name: a really long value that
   continues on the next line

  property names are case insensitive and should be less than
  60 characters in length and must start at the begining of
  the line, as whitespace at the start of a line signifies a
  line continuation.

*/

#include "forward.h"
#include "tidy.h"
#include "streamio.h"

struct _tidy_option;
typedef struct _tidy_option TidyOptionImpl;

typedef Bool (ParseProperty)( TidyDocImpl* doc, const TidyOptionImpl* opt );

struct _tidy_option
{
    TidyOptionId        id;
    TidyConfigCategory  category;   /* put 'em in groups */
    ctmbstr             name;       /* property name */
    TidyOptionType      type;       /* string, int or bool */
    ulong               dflt;       /* factory default */
    ParseProperty*      parser;     /* parsing method, read-only if NULL */
    const ctmbstr*      pickList;   /* pick list */
};


typedef struct _tidy_config
{
    ulong value[ N_TIDY_OPTIONS + 1 ];     /* current config values */
    ulong snapshot[ N_TIDY_OPTIONS + 1 ];  /* Snapshot of values to be restored later */

    /* track what tags user has defined to eliminate unnecessary searches */
    uint  defined_tags;

    uint c;           /* current char in input stream */
    StreamIn* cfgIn;  /* current input source */

} TidyConfigImpl;


typedef struct {
  TidyOptionId opt;          /**< Identifier. */
  ctmbstr doc;               /**< HTML text */
  TidyOptionId const *links; /**< Cross references.
                             Last element must be 'TidyUnknownOption'. */
} TidyOptionDoc;


const TidyOptionImpl* lookupOption( ctmbstr optnam );
const TidyOptionImpl* getOption( TidyOptionId optId );

TidyIterator getOptionList( TidyDocImpl* doc );
const TidyOptionImpl*  getNextOption( TidyDocImpl* doc, TidyIterator* iter );

TidyIterator getOptionPickList( const TidyOptionImpl* option );
ctmbstr getNextOptionPick( const TidyOptionImpl* option, TidyIterator* iter );

const TidyOptionDoc* tidyOptGetDocDesc( TidyOptionId optId );

void InitConfig( TidyDocImpl* doc );
void FreeConfig( TidyDocImpl* doc );

Bool SetOptionValue( TidyDocImpl* doc, TidyOptionId optId, ctmbstr val );
Bool SetOptionInt( TidyDocImpl* doc, TidyOptionId optId, ulong val );
Bool SetOptionBool( TidyDocImpl* doc, TidyOptionId optId, Bool val );

Bool ResetOptionToDefault( TidyDocImpl* doc, TidyOptionId optId );
void ResetConfigToDefault( TidyDocImpl* doc );
void TakeConfigSnapshot( TidyDocImpl* doc );
void ResetConfigToSnapshot( TidyDocImpl* doc );

void CopyConfig( TidyDocImpl* docTo, TidyDocImpl* docFrom );

/*
 Todd Lewis contributed this code for expanding
 ~/foo or ~your/foo according to $HOME and your
 user name. This will only work on Unix systems.
*/
ctmbstr ExpandTilde(ctmbstr filename);

int  ParseConfigFile( TidyDocImpl* doc, ctmbstr cfgfil );
int  ParseConfigFileEnc( TidyDocImpl* doc,
                         ctmbstr cfgfil, ctmbstr charenc );

int  SaveConfigFile( TidyDocImpl* doc, ctmbstr cfgfil );
int  SaveConfigSink( TidyDocImpl* doc, TidyOutputSink* sink );

/* returns false if unknown option, missing parameter, or
   option doesn't use parameter
*/
Bool  ParseConfigOption( TidyDocImpl* doc, ctmbstr optnam, ctmbstr optVal );
Bool  ParseConfigValue( TidyDocImpl* doc, TidyOptionId optId, ctmbstr optVal );

/* ensure that char encodings are self consistent */
Bool  AdjustCharEncoding( TidyDocImpl* doc, int encoding );

/* ensure that config is self consistent */
void AdjustConfig( TidyDocImpl* doc );

Bool  ConfigDiffThanDefault( TidyDocImpl* doc );
Bool  ConfigDiffThanSnapshot( TidyDocImpl* doc );

int CharEncodingId( ctmbstr charenc );
ctmbstr CharEncodingName( int encoding );
ctmbstr CharEncodingOptName( int encoding );

void SetEmacsFilename( TidyDocImpl* doc, ctmbstr filename );


#ifdef _DEBUG

/* Debug lookup functions will be type-safe and assert option type match */
ulong   _cfgGet( TidyDocImpl* doc, TidyOptionId optId );
Bool    _cfgGetBool( TidyDocImpl* doc, TidyOptionId optId );
TidyTriState _cfgGetAutoBool( TidyDocImpl* doc, TidyOptionId optId );
ctmbstr _cfgGetString( TidyDocImpl* doc, TidyOptionId optId );

#define cfg(doc, id)            _cfgGet( (doc), (id) )
#define cfgBool(doc, id)        _cfgGetBool( (doc), (id) )
#define cfgAutoBool(doc, id)    _cfgGetAutoBool( (doc), (id) )
#define cfgStr(doc, id)         _cfgGetString( (doc), (id) )

#else

/* Release build macros for speed */
#define cfg(doc, id)            ((doc)->config.value[ (id) ])
#define cfgBool(doc, id)        ((Bool) cfg(doc, id))
#define cfgAutoBool(doc, id)    ((TidyTriState) cfg(doc, id))
#define cfgStr(doc, id)         ((ctmbstr) cfg(doc, id))

#endif /* _DEBUG */



/* parser for integer values */
ParseProperty ParseInt;

/* parser for 't'/'f', 'true'/'false', 'y'/'n', 'yes'/'no' or '1'/'0' */
ParseProperty ParseBool;

/* parser for 't'/'f', 'true'/'false', 'y'/'n', 'yes'/'no', '1'/'0'
   or 'auto' */
ParseProperty ParseAutoBool;

/* a string excluding whitespace */
ParseProperty ParseName;

/* a CSS1 selector - CSS class naming for -clean option */
ParseProperty ParseCSS1Selector;

/* a string including whitespace */
ParseProperty ParseString;

/* a space or comma separated list of tag names */
ParseProperty ParseTagNames;

/* RAW, ASCII, LATIN0, LATIN1, UTF8, ISO2022, MACROMAN, 
   WIN1252, IBM858, UTF16LE, UTF16BE, UTF16, BIG5, SHIFTJIS
*/
ParseProperty ParseCharEnc;
ParseProperty ParseNewline;

/* omit | auto | strict | loose | <fpi> */
ParseProperty ParseDocType;

/* keep-first or keep-last? */
ParseProperty ParseRepeatAttr;

#endif /* __CONFIG_H__ */
