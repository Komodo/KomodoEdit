/*
  config.c -- read config file and manage config properties
  
  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/08/16 17:02:18 $ 
    $Revision: 1.92 $ 

*/

/*
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

#include "config.h"
#include "tidy-int.h"
#include "message.h"
#include "tmbstr.h"
#include "tags.h"

#ifdef WINDOWS_OS
#include <io.h>
#else
#ifdef DMALLOC
/*
   macro for valloc() in dmalloc.h may conflict with declaration for valloc() in unistd.h -
   we don't need (debugging for) valloc() here. dmalloc.h should come last but it doesn't.
*/
#ifdef valloc
#undef valloc
#endif
#endif
#include <unistd.h>
#endif

#ifdef TIDY_WIN32_MLANG_SUPPORT
#include "win32tc.h"
#endif

void InitConfig( TidyDocImpl* doc )
{
    ClearMemory( &doc->config, sizeof(TidyConfigImpl) );
    ResetConfigToDefault( doc );
}

void FreeConfig( TidyDocImpl* doc )
{
    ResetConfigToDefault( doc );
    TakeConfigSnapshot( doc );
}


/* Arrange so index can be cast to enum
*/
static const ctmbstr boolPicks[] = 
{
  "no",
  "yes",
  NULL
};

static const ctmbstr autoBoolPicks[] = 
{
  "no",
  "yes",
  "auto",
  NULL
};

static const ctmbstr repeatAttrPicks[] = 
{
  "keep-first",
  "keep-last",
  NULL
};

static const ctmbstr accessPicks[] = 
{
  "0 (Tidy Classic)",
  "1 (Priority 1 Checks)",
  "2 (Priority 2 Checks)",
  "3 (Priority 3 Checks)",
  NULL
};

static const ctmbstr charEncPicks[] = 
{
  "raw",
  "ascii",
  "latin0",
  "latin1",
  "utf8",
#ifndef NO_NATIVE_ISO2022_SUPPORT
  "iso2022",
#endif
  "mac",
  "win1252",
  "ibm858",

#if SUPPORT_UTF16_ENCODINGS
  "utf16le",
  "utf16be",
  "utf16",
#endif

#if SUPPORT_ASIAN_ENCODINGS
  "big5",
  "shiftjis",
#endif

  NULL
};

static const ctmbstr newlinePicks[] = 
{
  "LF",
  "CRLF",
  "CR",
  NULL
};

static const ctmbstr doctypePicks[] = 
{
  "omit",
  "auto",
  "strict",
  "transitional",
  "user",
  NULL 
};

#define MU TidyMarkup
#define DG TidyDiagnostics
#define PP TidyPrettyPrint
#define CE TidyEncoding
#define MS TidyMiscellaneous

#define IN TidyInteger
#define BL TidyBoolean
#define ST TidyString

#define XX (TidyConfigCategory)-1
#define XY (TidyOptionType)-1

#define DLF DEFAULT_NL_CONFIG

/* If Accessibility checks not supported, make config setting read-only */
#if SUPPORT_ACCESSIBILITY_CHECKS
#define ParseAcc ParseInt
#else
#define ParseAcc NULL 
#endif

static const TidyOptionImpl option_defs[] =
{
  { TidyUnknownOption,           MS, "unknown!",                    IN, 0,               NULL,              NULL            },
  { TidyIndentSpaces,            PP, "indent-spaces",               IN, 2,               ParseInt,          NULL            },
  { TidyWrapLen,                 PP, "wrap",                        IN, 68,              ParseInt,          NULL            },
  { TidyTabSize,                 PP, "tab-size",                    IN, 8,               ParseInt,          NULL            },
  { TidyCharEncoding,            CE, "char-encoding",               IN, ASCII,           ParseCharEnc,      charEncPicks    },
  { TidyInCharEncoding,          CE, "input-encoding",              IN, LATIN1,          ParseCharEnc,      charEncPicks    },
  { TidyOutCharEncoding,         CE, "output-encoding",             IN, ASCII,           ParseCharEnc,      charEncPicks    },
  { TidyNewline,                 CE, "newline",                     IN, DLF,             ParseNewline,      newlinePicks    },
  { TidyDoctypeMode,             MU, "doctype-mode",                IN, TidyDoctypeAuto, NULL,              doctypePicks    },
  { TidyDoctype,                 MU, "doctype",                     ST, 0,               ParseDocType,      doctypePicks    },
  { TidyDuplicateAttrs,          MU, "repeated-attributes",         IN, TidyKeepLast,    ParseRepeatAttr,   repeatAttrPicks },
  { TidyAltText,                 MU, "alt-text",                    ST, 0,               ParseString,       NULL            },

  /* obsolete */
  { TidySlideStyle,              MS, "slide-style",                 ST, 0,               ParseName,         NULL            },

  { TidyErrFile,                 MS, "error-file",                  ST, 0,               ParseString,       NULL            },
  { TidyOutFile,                 MS, "output-file",                 ST, 0,               ParseString,       NULL            },
  { TidyWriteBack,               MS, "write-back",                  BL, no,              ParseBool,         boolPicks       },
  { TidyShowMarkup,              PP, "markup",                      BL, yes,             ParseBool,         boolPicks       },
  { TidyShowWarnings,            DG, "show-warnings",               BL, yes,             ParseBool,         boolPicks       },
  { TidyQuiet,                   MS, "quiet",                       BL, no,              ParseBool,         boolPicks       },
  { TidyIndentContent,           PP, "indent",                      IN, TidyNoState,     ParseAutoBool,     autoBoolPicks   },
  { TidyHideEndTags,             MU, "hide-endtags",                BL, no,              ParseBool,         boolPicks       },
  { TidyXmlTags,                 MU, "input-xml",                   BL, no,              ParseBool,         boolPicks       },
  { TidyXmlOut,                  MU, "output-xml",                  BL, no,              ParseBool,         boolPicks       },
  { TidyXhtmlOut,                MU, "output-xhtml",                BL, no,              ParseBool,         boolPicks       },
  { TidyHtmlOut,                 MU, "output-html",                 BL, no,              ParseBool,         boolPicks       },
  { TidyXmlDecl,                 MU, "add-xml-decl",                BL, no,              ParseBool,         boolPicks       },
  { TidyUpperCaseTags,           MU, "uppercase-tags",              BL, no,              ParseBool,         boolPicks       },
  { TidyUpperCaseAttrs,          MU, "uppercase-attributes",        BL, no,              ParseBool,         boolPicks       },
  { TidyMakeBare,                MU, "bare",                        BL, no,              ParseBool,         boolPicks       },
  { TidyMakeClean,               MU, "clean",                       BL, no,              ParseBool,         boolPicks       },
  { TidyLogicalEmphasis,         MU, "logical-emphasis",            BL, no,              ParseBool,         boolPicks       },
  { TidyDropPropAttrs,           MU, "drop-proprietary-attributes", BL, no,              ParseBool,         boolPicks       },
  { TidyDropFontTags,            MU, "drop-font-tags",              BL, no,              ParseBool,         boolPicks       },
  { TidyDropEmptyParas,          MU, "drop-empty-paras",            BL, yes,             ParseBool,         boolPicks       },
  { TidyFixComments,             MU, "fix-bad-comments",            BL, yes,             ParseBool,         boolPicks       },
  { TidyBreakBeforeBR,           PP, "break-before-br",             BL, no,              ParseBool,         boolPicks       },

  /* obsolete */
  { TidyBurstSlides,             PP, "split",                       BL, no,              ParseBool,         boolPicks       },

  { TidyNumEntities,             MU, "numeric-entities",            BL, no,              ParseBool,         boolPicks       },
  { TidyQuoteMarks,              MU, "quote-marks",                 BL, no,              ParseBool,         boolPicks       },
  { TidyQuoteNbsp,               MU, "quote-nbsp",                  BL, yes,             ParseBool,         boolPicks       },
  { TidyQuoteAmpersand,          MU, "quote-ampersand",             BL, yes,             ParseBool,         boolPicks       },
  { TidyWrapAttVals,             PP, "wrap-attributes",             BL, no,              ParseBool,         boolPicks       },
  { TidyWrapScriptlets,          PP, "wrap-script-literals",        BL, no,              ParseBool,         boolPicks       },
  { TidyWrapSection,             PP, "wrap-sections",               BL, yes,             ParseBool,         boolPicks       },
  { TidyWrapAsp,                 PP, "wrap-asp",                    BL, yes,             ParseBool,         boolPicks       },
  { TidyWrapJste,                PP, "wrap-jste",                   BL, yes,             ParseBool,         boolPicks       },
  { TidyWrapPhp,                 PP, "wrap-php",                    BL, yes,             ParseBool,         boolPicks       },
  { TidyFixBackslash,            MU, "fix-backslash",               BL, yes,             ParseBool,         boolPicks       },
  { TidyIndentAttributes,        PP, "indent-attributes",           BL, no,              ParseBool,         boolPicks       },
  { TidyXmlPIs,                  MU, "assume-xml-procins",          BL, no,              ParseBool,         boolPicks       },
  { TidyXmlSpace,                MU, "add-xml-space",               BL, no,              ParseBool,         boolPicks       },
  { TidyEncloseBodyText,         MU, "enclose-text",                BL, no,              ParseBool,         boolPicks       },
  { TidyEncloseBlockText,        MU, "enclose-block-text",          BL, no,              ParseBool,         boolPicks       },
  { TidyKeepFileTimes,           MS, "keep-time",                   BL, no,              ParseBool,         boolPicks       },
  { TidyWord2000,                MU, "word-2000",                   BL, no,              ParseBool,         boolPicks       },
  { TidyMark,                    MS, "tidy-mark",                   BL, yes,             ParseBool,         boolPicks       },
  { TidyEmacs,                   MS, "gnu-emacs",                   BL, no,              ParseBool,         boolPicks       },
  { TidyEmacsFile,               MS, "gnu-emacs-file",              ST, 0,               ParseString,       NULL            },
  { TidyLiteralAttribs,          MU, "literal-attributes",          BL, no,              ParseBool,         boolPicks       },
  { TidyBodyOnly,                MU, "show-body-only",              BL, no,              ParseBool,         boolPicks       },
  { TidyFixUri,                  MU, "fix-uri",                     BL, yes,             ParseBool,         boolPicks       },
  { TidyLowerLiterals,           MU, "lower-literals",              BL, yes,             ParseBool,         boolPicks       },
  { TidyHideComments,            MU, "hide-comments",               BL, no,              ParseBool,         boolPicks       },
  { TidyIndentCdata,             MU, "indent-cdata",                BL, no,              ParseBool,         boolPicks       },
  { TidyForceOutput,             MS, "force-output",                BL, no,              ParseBool,         boolPicks       },
  { TidyShowErrors,              DG, "show-errors",                 IN, 6,               ParseInt,          NULL            },
  { TidyAsciiChars,              CE, "ascii-chars",                 BL, no,              ParseBool,         boolPicks       },
  { TidyJoinClasses,             MU, "join-classes",                BL, no,              ParseBool,         boolPicks       },
  { TidyJoinStyles,              MU, "join-styles",                 BL, yes,             ParseBool,         boolPicks       },
  { TidyEscapeCdata,             MU, "escape-cdata",                BL, no,              ParseBool,         boolPicks       },
#if SUPPORT_ASIAN_ENCODINGS
  { TidyLanguage,                CE, "language",                    ST, 0,               ParseName,         NULL            },
  { TidyNCR,                     MU, "ncr",                         BL, yes,             ParseBool,         boolPicks       },
#endif
#if SUPPORT_UTF16_ENCODINGS
  { TidyOutputBOM,               CE, "output-bom",                  IN, TidyAutoState,   ParseAutoBool,     autoBoolPicks   },
#endif
  { TidyReplaceColor,            MU, "replace-color",               BL, no,              ParseBool,         boolPicks       },
  { TidyCSSPrefix,               MU, "css-prefix",                  ST, 0,               ParseCSS1Selector, NULL            },
  { TidyInlineTags,              MU, "new-inline-tags",             ST, 0,               ParseTagNames,     NULL            },
  { TidyBlockTags,               MU, "new-blocklevel-tags",         ST, 0,               ParseTagNames,     NULL            },
  { TidyEmptyTags,               MU, "new-empty-tags",              ST, 0,               ParseTagNames,     NULL            },
  { TidyPreTags,                 MU, "new-pre-tags",                ST, 0,               ParseTagNames,     NULL            },
  { TidyAccessibilityCheckLevel, DG, "accessibility-check",         IN, 0,               ParseAcc,          accessPicks     },
  { TidyVertSpace,               PP, "vertical-space",              BL, no,              ParseBool,         boolPicks       },
#if SUPPORT_ASIAN_ENCODINGS
  { TidyPunctWrap,               PP, "punctuation-wrap",            BL, no,              ParseBool,         boolPicks       },
#endif
  { TidyMergeDivs,               MU, "merge-divs",                  IN, TidyAutoState,   ParseAutoBool,     autoBoolPicks   },
  { N_TIDY_OPTIONS,              XX, NULL,                          XY, 0,               NULL,              NULL            }
};

/* Should only be called by options set by name
** thus, it is cheaper to do a few scans than set
** up every option in a hash table.
*/
const TidyOptionImpl* lookupOption( ctmbstr s )
{
    const TidyOptionImpl* np = option_defs;
    for ( /**/; np < option_defs + N_TIDY_OPTIONS; ++np )
    {
        if ( tmbstrcasecmp(s, np->name) == 0 )
            return np;
    }
    return NULL;
}

const TidyOptionImpl* getOption( TidyOptionId optId )
{
  if ( optId < N_TIDY_OPTIONS )
      return option_defs + optId;
  return NULL;
}


static void FreeOptionValue( const TidyOptionImpl* option, ulong value )
{
    if ( value && option->type == TidyString && value != option->dflt )
    {
        MemFree( (void*) value );
    }
}

static void CopyOptionValue( const TidyOptionImpl* option,
                             ulong* oldval, ulong newval )
{
    assert( oldval != NULL );
    FreeOptionValue( option, *oldval );

    if ( newval && option->type == TidyString && newval != option->dflt )
        *oldval = (ulong) tmbstrdup( (ctmbstr) newval );
    else
        *oldval = newval;
}


Bool SetOptionValue( TidyDocImpl* doc, TidyOptionId optId, ctmbstr val )
{
   const TidyOptionImpl* option = &option_defs[ optId ];
   Bool status = ( optId < N_TIDY_OPTIONS );
   if ( status )
   {
      assert( option->id == optId && option->type == TidyString );
      FreeOptionValue( option, doc->config.value[ optId ] );
      doc->config.value[ optId ] = (ulong) tmbstrdup( val );
   }
   return status;
}

Bool SetOptionInt( TidyDocImpl* doc, TidyOptionId optId, ulong val )
{
   Bool status = ( optId < N_TIDY_OPTIONS );
   if ( status )
   {
       assert( option_defs[ optId ].type == TidyInteger );
       doc->config.value[ optId ] = val;
   }
   return status;
}

Bool SetOptionBool( TidyDocImpl* doc, TidyOptionId optId, Bool val )
{
   Bool status = ( optId < N_TIDY_OPTIONS );
   if ( status )
   {
       assert( option_defs[ optId ].type == TidyBoolean );
       doc->config.value[ optId ] = val;
   }
   return status;
}

Bool ResetOptionToDefault( TidyDocImpl* doc, TidyOptionId optId )
{
    Bool status = ( optId > 0 && optId < N_TIDY_OPTIONS );
    if ( status )
    {
        const TidyOptionImpl* option = option_defs + optId;
        ulong* value = &doc->config.value[ optId ];
        assert( optId == option->id );
        CopyOptionValue( option, value, option->dflt );
    }
    return status;
}

static void ReparseTagType( TidyDocImpl* doc, TidyOptionId optId )
{
    ctmbstr tagdecl = cfgStr( doc, optId );
    tmbstr dupdecl = tmbstrdup( tagdecl );
    ParseConfigValue( doc, optId, dupdecl );
    MemFree( dupdecl );
}

/* Not efficient, but effective */
static void ReparseTagDecls( TidyDocImpl* doc )
{
    FreeDeclaredTags( doc, tagtype_null );
    if ( cfg(doc, TidyInlineTags) )
        ReparseTagType( doc, TidyInlineTags );
    if ( cfg(doc, TidyBlockTags) )
        ReparseTagType( doc, TidyBlockTags );
    if ( cfg(doc, TidyEmptyTags) )
        ReparseTagType( doc, TidyEmptyTags );
    if ( cfg(doc, TidyPreTags) )
        ReparseTagType( doc, TidyPreTags );
}

void ResetConfigToDefault( TidyDocImpl* doc )
{
    uint ixVal;
    const TidyOptionImpl* option = option_defs;
    ulong* value = &doc->config.value[ 0 ];
    for ( ixVal=0; ixVal < N_TIDY_OPTIONS; ++option, ++ixVal )
    {
        assert( ixVal == (uint) option->id );
        CopyOptionValue( option, &value[ixVal], option->dflt );
    }
    FreeDeclaredTags( doc, tagtype_null );
}

void TakeConfigSnapshot( TidyDocImpl* doc )
{
    uint ixVal;
    const TidyOptionImpl* option = option_defs;
    ulong* value = &doc->config.value[ 0 ];
    ulong* snap  = &doc->config.snapshot[ 0 ];

    AdjustConfig( doc );  /* Make sure it's consistent */
    for ( ixVal=0; ixVal < N_TIDY_OPTIONS; ++option, ++ixVal )
    {
        assert( ixVal == (uint) option->id );
        CopyOptionValue( option, &snap[ixVal], value[ixVal] );
    }
}

void ResetConfigToSnapshot( TidyDocImpl* doc )
{
    uint ixVal;
    const TidyOptionImpl* option = option_defs;
    ulong* value = &doc->config.value[ 0 ];
    ulong* snap  = &doc->config.snapshot[ 0 ];

    for ( ixVal=0; ixVal < N_TIDY_OPTIONS; ++option, ++ixVal )
    {
        assert( ixVal == (uint) option->id );
        CopyOptionValue( option, &value[ixVal], snap[ixVal] );
    }
    FreeDeclaredTags( doc, tagtype_null );
    ReparseTagDecls( doc );
}

void CopyConfig( TidyDocImpl* docTo, TidyDocImpl* docFrom )
{
    if ( docTo != docFrom )
    {
        uint ixVal;
        const TidyOptionImpl* option = option_defs;
        ulong* from = &docFrom->config.value[ 0 ];
        ulong* to   = &docTo->config.value[ 0 ];

        TakeConfigSnapshot( docTo );
        for ( ixVal=0; ixVal < N_TIDY_OPTIONS; ++option, ++ixVal )
        {
            assert( ixVal == (uint) option->id );
            CopyOptionValue( option, &to[ixVal], from[ixVal] );
        }
        ReparseTagDecls( docTo );
        AdjustConfig( docTo );  /* Make sure it's consistent */
    }
}


#ifdef _DEBUG

/* Debug accessor functions will be type-safe and assert option type match */
ulong   _cfgGet( TidyDocImpl* doc, TidyOptionId optId )
{
  assert( optId < N_TIDY_OPTIONS );
  return doc->config.value[ optId ];
}

Bool    _cfgGetBool( TidyDocImpl* doc, TidyOptionId optId )
{
  ulong val = _cfgGet( doc, optId );
  const TidyOptionImpl* opt = &option_defs[ optId ];
  assert( opt && opt->type == TidyBoolean );
  return (Bool) val;
}

TidyTriState    _cfgGetAutoBool( TidyDocImpl* doc, TidyOptionId optId )
{
  ulong val = _cfgGet( doc, optId );
  const TidyOptionImpl* opt = &option_defs[ optId ];
  assert( opt && opt->type == TidyInteger );
  return (TidyTriState) val;
}

ctmbstr _cfgGetString( TidyDocImpl* doc, TidyOptionId optId )
{
  ulong val = _cfgGet( doc, optId );
  const TidyOptionImpl* opt = &option_defs[ optId ];
  assert( opt && opt->type == TidyString );
  return (ctmbstr) val;
}
#endif


/* for use with Gnu Emacs */
void SetEmacsFilename( TidyDocImpl* doc, ctmbstr filename )
{
    SetOptionValue( doc, TidyEmacsFile, filename );
}


static tchar GetC( TidyConfigImpl* config )
{
    if ( config->cfgIn )
        return ReadChar( config->cfgIn );
    return EndOfStream;
}

static tchar FirstChar( TidyConfigImpl* config )
{
    config->c = GetC( config );
    return config->c;
}

static tchar AdvanceChar( TidyConfigImpl* config )
{
    if ( config->c != EndOfStream )
        config->c = GetC( config );
    return config->c;
}

static tchar SkipWhite( TidyConfigImpl* config )
{
    while ( IsWhite(config->c) && !IsNewline(config->c) )
        config->c = GetC( config );
    return config->c;
}

/* skip until end of line
static tchar SkipToEndofLine( TidyConfigImpl* config )
{
    while ( config->c != EndOfStream )
    {
        config->c = GetC( config );
        if ( config->c == '\n' || config->c == '\r' )
            break;
    }
    return config->c;
}
*/

/*
 skip over line continuations
 to start of next property
*/
static uint NextProperty( TidyConfigImpl* config )
{
    do
    {
        /* skip to end of line */
        while ( config->c != '\n' &&  config->c != '\r' &&  config->c != EndOfStream )
             config->c = GetC( config );

        /* treat  \r\n   \r  or  \n as line ends */
        if ( config->c == '\r' )
             config->c = GetC( config );

        if ( config->c == '\n' )
            config->c = GetC( config );
    }
    while ( IsWhite(config->c) );  /* line continuation? */

    return config->c;
}

/*
 Todd Lewis contributed this code for expanding
 ~/foo or ~your/foo according to $HOME and your
 user name. This will work partially on any system 
 which defines $HOME.  Support for ~user/foo will
 work on systems that support getpwnam(userid), 
 namely Unix/Linux.
*/
ctmbstr ExpandTilde( ctmbstr filename )
{
    char *home_dir = NULL;

    if ( !filename )
        return NULL;

    if ( filename[0] != '~' )
        return filename;

    if (filename[1] == '/')
    {
        home_dir = getenv("HOME");
        if ( home_dir )
            ++filename;
    }
#ifdef SUPPORT_GETPWNAM
    else
    {
        struct passwd *passwd = NULL;
        ctmbstr s = filename + 1;
        tmbstr t;

        while ( *s && *s != '/' )
            s++;

        if ( t = MemAlloc(s - filename) )
        {
            memcpy(t, filename+1, s-filename-1);
            t[s-filename-1] = 0;

            passwd = getpwnam(t);

            MemFree(t);
        }

        if ( passwd )
        {
            filename = s;
            home_dir = passwd->pw_dir;
        }
    }
#endif /* SUPPORT_GETPWNAM */

    if ( home_dir )
    {
        uint len = tmbstrlen(filename) + tmbstrlen(home_dir) + 1;
        tmbstr p = (tmbstr)MemAlloc( len );
        tmbstrcpy( p, home_dir );
        tmbstrcat( p, filename );
        return (ctmbstr) p;
    }
    return (ctmbstr) filename;
}

Bool TIDY_CALL tidyFileExists( ctmbstr filename )
{
  ctmbstr fname = (tmbstr) ExpandTilde( filename );
#ifndef NO_ACCESS_SUPPORT
  Bool exists = ( access(fname, 0) == 0 );
#else
  Bool exists;
  /* at present */
  FILE* fin = fopen(fname, "r");
  if (fin != NULL)
      fclose(fin);
  exists = ( fin != NULL );
#endif
  if ( fname != filename )
      MemFree( (tmbstr) fname );
  return exists;
}


#ifndef TIDY_MAX_NAME
#define TIDY_MAX_NAME 64
#endif

int ParseConfigFile( TidyDocImpl* doc, ctmbstr file )
{
    return ParseConfigFileEnc( doc, file, "ascii" );
}

/* open the file and parse its contents
*/
int ParseConfigFileEnc( TidyDocImpl* doc, ctmbstr file, ctmbstr charenc )
{
    uint opterrs = doc->optionErrors;
    tmbstr fname = (tmbstr) ExpandTilde( file );
    TidyConfigImpl* cfg = &doc->config;
    FILE* fin = fopen( fname, "r" );
    int enc = CharEncodingId( charenc );

    if ( fin == NULL || enc < 0 )
    {
        FileError( doc, fname, TidyConfig );
        return -1;
    }
    else
    {
        tchar c;
        cfg->cfgIn = FileInput( doc, fin, enc );
        c = FirstChar( cfg );
       
        for ( c = SkipWhite(cfg); c != EndOfStream; c = NextProperty(cfg) )
        {
            uint ix = 0;
            tmbchar name[ TIDY_MAX_NAME ] = {0};

            /* // or # start a comment */
            if ( c == '/' || c == '#' )
                continue;

            while ( ix < sizeof(name)-1 && c != '\n' && c != EndOfStream && c != ':' )
            {
                name[ ix++ ] = (tmbchar) c;  /* Option names all ASCII */
                c = AdvanceChar( cfg );
            }

            if ( c == ':' )
            {
                const TidyOptionImpl* option = lookupOption( name );
                c = AdvanceChar( cfg );
                if ( option )
                    option->parser( doc, option );
                else
                {
                    if (NULL != doc->pOptCallback)
                    {
                        TidyConfigImpl* cfg = &doc->config;
                        tmbchar buf[8192];
                        uint i = 0;
                        tchar delim = 0;
                        Bool waswhite = yes;

                        tchar c = SkipWhite( cfg );

                        if ( c == '"' || c == '\'' )
                        {
                            delim = c;
                            c = AdvanceChar( cfg );
                        }

                        while ( i < sizeof(buf)-2 && c != EndOfStream && c != '\r' && c != '\n' )
                        {
                            if ( delim && c == delim )
                                break;

                            if ( IsWhite(c) )
                            {
                                if ( waswhite )
                                {
                                    c = AdvanceChar( cfg );
                                    continue;
                                }
                                c = ' ';
                            }
                            else
                                waswhite = no;

                            buf[i++] = (tmbchar) c;
                            c = AdvanceChar( cfg );
                        }
                        buf[i] = '\0';
                        if (no == (*doc->pOptCallback)( name, buf ))
                            ReportUnknownOption( doc, name );
                    }
                    else
                        ReportUnknownOption( doc, name );
                }
            }
        }

        fclose( fin );
        MemFree( (void *)cfg->cfgIn->source.sourceData ); /* fix for bug #810259 */
        freeStreamIn( cfg->cfgIn );
        cfg->cfgIn = NULL;
    }

    if ( fname != (tmbstr) file )
        MemFree( fname );

    AdjustConfig( doc );

    /* any new config errors? If so, return warning status. */
    return (doc->optionErrors > opterrs ? 1 : 0); 
}

/* returns false if unknown option, missing parameter,
** or option doesn't use parameter
*/
Bool ParseConfigOption( TidyDocImpl* doc, ctmbstr optnam, ctmbstr optval )
{
    const TidyOptionImpl* option = lookupOption( optnam );
    Bool status = ( option != NULL );
    if ( !status )
    {
        /* Not a standard tidy option.  Check to see if the user application 
           recognizes it  */
        if (NULL != doc->pOptCallback)
            status = (*doc->pOptCallback)( optnam, optval );
        if (!status)
            ReportUnknownOption( doc, optnam );
    }
    else 
        status = ParseConfigValue( doc, option->id, optval );
    return status;
}

/* returns false if unknown option, missing parameter,
** or option doesn't use parameter
*/
Bool ParseConfigValue( TidyDocImpl* doc, TidyOptionId optId, ctmbstr optval )
{
    const TidyOptionImpl* option = option_defs + optId;
    Bool status = ( optId < N_TIDY_OPTIONS && optval != NULL );

    if ( !status )
        ReportBadArgument( doc, option->name );
    else
    {
        TidyBuffer inbuf = {0};            /* Set up input source */
        tidyBufAttach( &inbuf, (byte*)optval, tmbstrlen(optval)+1 );
        doc->config.cfgIn = BufferInput( doc, &inbuf, ASCII );
        doc->config.c = GetC( &doc->config );

        status = option->parser( doc, option );

        freeStreamIn(doc->config.cfgIn);  /* Release input source */
        doc->config.cfgIn  = NULL;
        tidyBufDetach( &inbuf );
    }
    return status;
}


/* ensure that char encodings are self consistent */
Bool  AdjustCharEncoding( TidyDocImpl* doc, int encoding )
{
    int outenc = -1;
    int inenc = -1;
    
    switch( encoding )
    {
    case MACROMAN:
        inenc = MACROMAN;
        outenc = ASCII;
        break;

    case WIN1252:
        inenc = WIN1252;
        outenc = ASCII;
        break;

    case IBM858:
        inenc = IBM858;
        outenc = ASCII;
        break;

    case ASCII:
        inenc = LATIN1;
        outenc = ASCII;
        break;

    case LATIN0:
        inenc = LATIN0;
        outenc = ASCII;
        break;

    case RAW:
    case LATIN1:
    case UTF8:
#ifndef NO_NATIVE_ISO2022_SUPPORT
    case ISO2022:
#endif

#if SUPPORT_UTF16_ENCODINGS
    case UTF16LE:
    case UTF16BE:
    case UTF16:
#endif
#if SUPPORT_ASIAN_ENCODINGS
    case SHIFTJIS:
    case BIG5:
#endif
        inenc = outenc = encoding;
        break;
    }

    if ( inenc >= 0 )
    {
        SetOptionInt( doc, TidyCharEncoding, encoding );
        SetOptionInt( doc, TidyInCharEncoding, inenc );
        SetOptionInt( doc, TidyOutCharEncoding, outenc );
        return yes;
    }
    return no;
}

/* ensure that config is self consistent */
void AdjustConfig( TidyDocImpl* doc )
{
    if ( cfgBool(doc, TidyEncloseBlockText) )
        SetOptionBool( doc, TidyEncloseBodyText, yes );

    if ( cfgAutoBool(doc, TidyIndentContent) == TidyNoState )
        SetOptionInt( doc, TidyIndentSpaces, 0 );

    /* disable wrapping */
    if ( cfg(doc, TidyWrapLen) == 0 )
        SetOptionInt( doc, TidyWrapLen, 0x7FFFFFFF );

    /* Word 2000 needs o:p to be declared as inline */
    if ( cfgBool(doc, TidyWord2000) )
    {
        doc->config.defined_tags |= tagtype_inline;
        DefineTag( doc, tagtype_inline, "o:p" );
    }

    /* #480701 disable XHTML output flag if both output-xhtml and xml input are set */
    if ( cfgBool(doc, TidyXmlTags) )
        SetOptionBool( doc, TidyXhtmlOut, no );

    /* XHTML is written in lower case */
    if ( cfgBool(doc, TidyXhtmlOut) )
    {
        SetOptionBool( doc, TidyXmlOut, yes );
        SetOptionBool( doc, TidyUpperCaseTags, no );
        SetOptionBool( doc, TidyUpperCaseAttrs, no );
        /* SetOptionBool( doc, TidyXmlPIs, yes ); */
    }

    /* if XML in, then XML out */
    if ( cfgBool(doc, TidyXmlTags) )
    {
        SetOptionBool( doc, TidyXmlOut, yes );
        SetOptionBool( doc, TidyXmlPIs, yes );
    }

    /* #427837 - fix by Dave Raggett 02 Jun 01
    ** generate <?xml version="1.0" encoding="iso-8859-1"?>
    ** if the output character encoding is Latin-1 etc.
    */
    if ( cfg(doc, TidyOutCharEncoding) != ASCII &&
         cfg(doc, TidyOutCharEncoding) != UTF8 &&
#if SUPPORT_UTF16_ENCODINGS
         cfg(doc, TidyOutCharEncoding) != UTF16 &&
         cfg(doc, TidyOutCharEncoding) != UTF16BE &&
         cfg(doc, TidyOutCharEncoding) != UTF16LE &&
#endif
         cfg(doc, TidyOutCharEncoding) != RAW &&
         cfgBool(doc, TidyXmlOut) )
    {
        SetOptionBool( doc, TidyXmlDecl, yes );
    }

    /* XML requires end tags */
    if ( cfgBool(doc, TidyXmlOut) )
    {
#if SUPPORT_UTF16_ENCODINGS
        /* XML requires a BOM on output if using UTF-16 encoding */
        ulong enc = cfg( doc, TidyOutCharEncoding );
        if ( enc == UTF16LE || enc == UTF16BE || enc == UTF16 )
            SetOptionInt( doc, TidyOutputBOM, yes );
#endif
        SetOptionBool( doc, TidyQuoteAmpersand, yes );
        SetOptionBool( doc, TidyHideEndTags, no );
    }
}

/* unsigned integers */
Bool ParseInt( TidyDocImpl* doc, const TidyOptionImpl* entry )
{
    ulong number = 0;
    Bool digits = no;
    TidyConfigImpl* cfg = &doc->config;
    tchar c = SkipWhite( cfg );

    while ( IsDigit(c) )
    {
        number = c - '0' + (10 * number);
        digits = yes;
        c = AdvanceChar( cfg );
    }

    if ( !digits )
        ReportBadArgument( doc, entry->name );
    else
        SetOptionInt( doc, entry->id, number );
    return digits;
}

/* true/false or yes/no or 0/1 or "auto" only looks at 1st char */
static Bool ParseTriState( TidyTriState theState, TidyDocImpl* doc,
                    const TidyOptionImpl* entry, ulong* flag )
{
    TidyConfigImpl* cfg = &doc->config;
    tchar c = SkipWhite( cfg );

    if (c == 't' || c == 'T' || c == 'y' || c == 'Y' || c == '1')
        *flag = yes;
    else if (c == 'f' || c == 'F' || c == 'n' || c == 'N' || c == '0')
        *flag = no;
    else if (theState == TidyAutoState && (c == 'a' || c =='A'))
        *flag = TidyAutoState;
    else
    {
        ReportBadArgument( doc, entry->name );
        return no;
    }

    return yes;
}

/* cr, lf or crlf */
Bool ParseNewline( TidyDocImpl* doc, const TidyOptionImpl* entry )
{
    int nl = -1;
    tmbchar work[ 16 ] = {0};
    tmbstr cp = work, end = work + sizeof(work);
    TidyConfigImpl* cfg = &doc->config;
    tchar c = SkipWhite( cfg );

    while ( c!=EndOfStream && cp < end && !IsWhite(c) && c != '\r' && c != '\n' )
    {
        *cp++ = (tmbchar) c;
        c = AdvanceChar( cfg );
    }
    *cp = 0;

    if ( tmbstrcasecmp(work, "lf") == 0 )
        nl = TidyLF;
    else if ( tmbstrcasecmp(work, "crlf") == 0 )
        nl = TidyCRLF;
    else if ( tmbstrcasecmp(work, "cr") == 0 )
        nl = TidyCR;

    if ( nl < TidyLF || nl > TidyCR )
        ReportBadArgument( doc, entry->name );
    else
        SetOptionInt( doc, entry->id, nl );
    return ( nl >= TidyLF && nl <= TidyCR );
}

Bool ParseBool( TidyDocImpl* doc, const TidyOptionImpl* entry )
{
    ulong flag = 0;
    Bool status = ParseTriState( TidyNoState, doc, entry, &flag );
    if ( status )
        SetOptionBool( doc, entry->id, flag != 0 );
    return status;
}

Bool ParseAutoBool( TidyDocImpl* doc, const TidyOptionImpl* entry )
{
    ulong flag = 0;
    Bool status = ParseTriState( TidyAutoState, doc, entry, &flag );
    if ( status )
        SetOptionInt( doc, entry->id, flag );
    return status;
}

/* a string excluding whitespace */
Bool ParseName( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    tmbchar buf[ 1024 ] = {0};
    uint i = 0;
    uint c = SkipWhite( &doc->config );

    while ( i < sizeof(buf)-2 && c != EndOfStream && !IsWhite(c) )
    {
        buf[i++] = (tmbchar) c;
        c = AdvanceChar( &doc->config );
    }
    buf[i] = 0;

    if ( i == 0 )
        ReportBadArgument( doc, option->name );
    else
        SetOptionValue( doc, option->id, buf );
    return ( i > 0 );
}

/* #508936 - CSS class naming for -clean option */
Bool ParseCSS1Selector( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    char buf[256] = {0};
    uint i = 0;
    uint c = SkipWhite( &doc->config );

    while ( i < sizeof(buf)-2 && c != EndOfStream && !IsWhite(c) )
    {
        buf[i++] = (tmbchar) c;
        c = AdvanceChar( &doc->config );
    }
    buf[i] = '\0';

    if ( i == 0 || !IsCSS1Selector(buf) ) {
        ReportBadArgument( doc, option->name );
        return no;
    }

    buf[i++] = '-';  /* Make sure any escaped Unicode is terminated */
    buf[i] = 0;      /* so valid class names are generated after */
                     /* Tidy appends last digits. */

    SetOptionValue( doc, option->id, buf );
    return yes;
}

/* Coordinates Config update and Tags data */
static void DeclareUserTag( TidyDocImpl* doc, TidyOptionId optId,
                            UserTagType tagType, ctmbstr name )
{
  ctmbstr prvval = cfgStr( doc, optId );
  tmbstr catval = NULL;
  ctmbstr theval = name;
  if ( prvval )
  {
    uint len = tmbstrlen(name) + tmbstrlen(prvval) + 3;
    catval = tmbstrndup( prvval, len );
    tmbstrcat( catval, ", " );
    tmbstrcat( catval, name );
    theval = catval;
  }
  DefineTag( doc, tagType, name );
  SetOptionValue( doc, optId, theval );
  if ( catval )
    MemFree( catval );
}

/* a space or comma separated list of tag names */
Bool ParseTagNames( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    TidyConfigImpl* cfg = &doc->config;
    tmbchar buf[1024];
    uint i = 0, nTags = 0;
    uint c = SkipWhite( cfg );
    UserTagType ttyp = tagtype_null;

    switch ( option->id )
    {
    case TidyInlineTags:  ttyp = tagtype_inline;    break;
    case TidyBlockTags:   ttyp = tagtype_block;     break;
    case TidyEmptyTags:   ttyp = tagtype_empty;     break;
    case TidyPreTags:     ttyp = tagtype_pre;       break;
    default:
       ReportUnknownOption( doc, option->name );
       return no;
    }

    SetOptionValue( doc, option->id, NULL );
    FreeDeclaredTags( doc, ttyp );
    cfg->defined_tags |= ttyp;

    do
    {
        if (c == ' ' || c == '\t' || c == ',')
        {
            c = AdvanceChar( cfg );
            continue;
        }

        if ( c == '\r' || c == '\n' )
        {
            uint c2 = AdvanceChar( cfg );
            if ( c == '\r' && c2 == '\n' )
                c = AdvanceChar( cfg );
            else
                c = c2;

            if ( !IsWhite(c) )
            {
                buf[i] = 0;
                UngetChar( c, cfg->cfgIn );
                UngetChar( '\n', cfg->cfgIn );
                break;
            }
        }

        /*
        if ( c == '\n' )
        {
            c = AdvanceChar( cfg );
            if ( !IsWhite(c) )
            {
                buf[i] = 0;
                UngetChar( c, cfg->cfgIn );
                UngetChar( '\n', cfg->cfgIn );
                break;
            }
        }
        */

        while ( i < sizeof(buf)-2 && c != EndOfStream && !IsWhite(c) && c != ',' )
        {
            buf[i++] = (tmbchar) c;
            c = AdvanceChar( cfg );
        }

        buf[i] = '\0';
        if (i == 0)          /* Skip empty tag definition.  Possible when */
            continue;        /* there is a trailing space on the line. */
            
        /* add tag to dictionary */
        DeclareUserTag( doc, option->id, ttyp, buf );
        i = 0;
        ++nTags;
    }
    while ( c != EndOfStream );

    if ( i > 0 )
      DeclareUserTag( doc, option->id, ttyp, buf );
    return ( nTags > 0 );
}

/* a string including whitespace */
/* munges whitespace sequences */

Bool ParseString( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    TidyConfigImpl* cfg = &doc->config;
    tmbchar buf[8192];
    uint i = 0;
    tchar delim = 0;
    Bool waswhite = yes;

    tchar c = SkipWhite( cfg );

    if ( c == '"' || c == '\'' )
    {
        delim = c;
        c = AdvanceChar( cfg );
    }

    while ( i < sizeof(buf)-2 && c != EndOfStream && c != '\r' && c != '\n' )
    {
        if ( delim && c == delim )
            break;

        if ( IsWhite(c) )
        {
            if ( waswhite )
            {
                c = AdvanceChar( cfg );
                continue;
            }
            c = ' ';
        }
        else
            waswhite = no;

        buf[i++] = (tmbchar) c;
        c = AdvanceChar( cfg );
    }
    buf[i] = '\0';

    SetOptionValue( doc, option->id, buf );
    return yes;
}

Bool ParseCharEnc( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    tmbchar buf[64] = {0};
    uint i = 0;
    int enc = ASCII;
    Bool validEncoding = yes;
    tchar c = SkipWhite( &doc->config );

    while ( i < sizeof(buf)-2 && c != EndOfStream && !IsWhite(c) )
    {
        buf[i++] = (tmbchar) ToLower( c );
        c = AdvanceChar( &doc->config );
    }
    buf[i] = 0;

    enc = CharEncodingId( buf );

#ifdef TIDY_WIN32_MLANG_SUPPORT
    /* limit support to --input-encoding */
    if (option->id != TidyInCharEncoding && enc > WIN32MLANG)
        enc = -1;
#endif

    if ( enc < 0 )
    {
        validEncoding = no;
        ReportBadArgument( doc, option->name );
    }
    else
        SetOptionInt( doc, option->id, enc );

    if ( validEncoding && option->id == TidyCharEncoding )
        AdjustCharEncoding( doc, enc );
    return validEncoding;
}


int CharEncodingId( ctmbstr charenc )
{
    int enc = GetCharEncodingFromOptName( charenc );

#ifdef TIDY_WIN32_MLANG_SUPPORT
    if (enc == -1)
    {
        uint wincp = Win32MLangGetCPFromName(charenc);
        if (wincp)
            enc = wincp;
    }
#endif

    return enc;
}

ctmbstr CharEncodingName( int encoding )
{
    ctmbstr encodingName = GetEncodingNameFromTidyId(encoding);

    if (!encodingName)
        encodingName = "unknown";

    return encodingName;
}

ctmbstr CharEncodingOptName( int encoding )
{
    ctmbstr encodingName = GetEncodingOptNameFromTidyId(encoding);

    if (!encodingName)
        encodingName = "unknown";

    return encodingName;
}

/*
   doctype: omit | auto | strict | loose | <fpi>

   where the fpi is a string similar to

      "-//ACME//DTD HTML 3.14159//EN"
*/
Bool ParseDocType( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    tmbchar buf[ 32 ] = {0};
    uint i = 0;
    Bool status = yes;
    TidyDoctypeModes dtmode = TidyDoctypeAuto;

    TidyConfigImpl* cfg = &doc->config;
    tchar c = SkipWhite( cfg );

    /* "-//ACME//DTD HTML 3.14159//EN" or similar */

    if ( c == '"' || c == '\'' )
    {
        status = ParseString(doc, option);
        if (status)
            SetOptionInt( doc, TidyDoctypeMode, TidyDoctypeUser );

        return status;
    }

    /* read first word */
    while ( i < sizeof(buf)-1 && c != EndOfStream && !IsWhite(c) )
    {
        buf[i++] = (tmbchar) c;
        c = AdvanceChar( cfg );
    }
    buf[i] = '\0';

    if ( tmbstrcasecmp(buf, "auto") == 0 )
        dtmode = TidyDoctypeAuto;
    else if ( tmbstrcasecmp(buf, "omit") == 0 )
        dtmode = TidyDoctypeOmit;
    else if ( tmbstrcasecmp(buf, "strict") == 0 )
        dtmode = TidyDoctypeStrict;
    else if ( tmbstrcasecmp(buf, "loose") == 0 ||
              tmbstrcasecmp(buf, "transitional") == 0 )
        dtmode = TidyDoctypeLoose;
    else
    {
        ReportBadArgument( doc, option->name );
        status = no;
    }
     
    if ( status )
        SetOptionInt( doc, TidyDoctypeMode, dtmode );
    return status;
}

Bool ParseRepeatAttr( TidyDocImpl* doc, const TidyOptionImpl* option )
{
    Bool status = yes;
    tmbchar buf[64] = {0};
    uint i = 0;

    TidyConfigImpl* cfg = &doc->config;
    tchar c = SkipWhite( cfg );

    while (i < sizeof(buf)-1 && c != EndOfStream && !IsWhite(c))
    {
        buf[i++] = (tmbchar) c;
        c = AdvanceChar( cfg );
    }
    buf[i] = '\0';

    if ( tmbstrcasecmp(buf, "keep-first") == 0 )
        cfg->value[ TidyDuplicateAttrs ] = TidyKeepFirst;
    else if ( tmbstrcasecmp(buf, "keep-last") == 0 )
        cfg->value[ TidyDuplicateAttrs ] = TidyKeepLast;
    else
    {
        ReportBadArgument( doc, option->name );
        status = no;
    }
    return status;
}

/* Use TidyOptionId as iterator.
** Send index of 1st option after TidyOptionUnknown as start of list.
*/
TidyIterator getOptionList( TidyDocImpl* ARG_UNUSED(doc) )
{
  return (TidyIterator) 1;
}

/* Check if this item is last valid option.
** If so, zero out iterator.
*/
const TidyOptionImpl*  getNextOption( TidyDocImpl* ARG_UNUSED(doc),
                                      TidyIterator* iter )
{
  const TidyOptionImpl* option = NULL;
  ulong optId;
  assert( iter != NULL );
  optId = (ulong) *iter;
  if ( optId > TidyUnknownOption && optId < N_TIDY_OPTIONS )
  {
    option = &option_defs[ optId ];
    optId++;
  }
  *iter = (TidyIterator) ( optId < N_TIDY_OPTIONS ? optId : 0 );
  return option;
}

/* Use a 1-based array index as iterator: 0 == end-of-list
*/
TidyIterator getOptionPickList( const TidyOptionImpl* option )
{
    ulong ix = 0;
    if ( option && option->pickList )
        ix = 1;
    return (TidyIterator) ix;
}

ctmbstr      getNextOptionPick( const TidyOptionImpl* option,
                                TidyIterator* iter )
{
    ulong ix;
    ctmbstr val = NULL;
    assert( option!=NULL && iter != NULL );

    ix = (ulong) *iter;
    if ( ix > 0 && ix < 16 && option->pickList )
        val = option->pickList[ ix-1 ];
    *iter = (TidyIterator) ( val && option->pickList[ix] ? ix + 1 : 0 );
    return val;
}

static int  WriteOptionString( const TidyOptionImpl* option,
                               ctmbstr sval, StreamOut* out )
{
  ctmbstr cp = option->name;
  while ( *cp )
      WriteChar( *cp++, out );
  WriteChar( ':', out );
  WriteChar( ' ', out );
  cp = sval;
  while ( *cp )
      WriteChar( *cp++, out );
  WriteChar( '\n', out );
  return 0;
}

static int  WriteOptionInt( const TidyOptionImpl* option, uint ival, StreamOut* out )
{
  tmbchar sval[ 32 ] = {0};
  tmbsnprintf(sval, sizeof(sval), "%u", ival );
  return WriteOptionString( option, sval, out );
}

static int  WriteOptionBool( const TidyOptionImpl* option, Bool bval, StreamOut* out )
{
  ctmbstr sval = bval ? "yes" : "no";
  return WriteOptionString( option, sval, out );
}

static int  WriteOptionPick( const TidyOptionImpl* option, uint ival, StreamOut* out )
{
    uint ix;
    const ctmbstr* val = option->pickList;
    for ( ix=0; val[ix] && ix<ival; ++ix )
        /**/;
    if ( ix==ival && val[ix] )
        return WriteOptionString( option, val[ix], out );
    return -1;
}

Bool  ConfigDiffThanSnapshot( TidyDocImpl* doc )
{
  int diff = memcmp( &doc->config.value, &doc->config.snapshot,
                     N_TIDY_OPTIONS * sizeof(uint) );
  return ( diff != 0 );
}

Bool  ConfigDiffThanDefault( TidyDocImpl* doc )
{
  Bool diff = no;
  const TidyOptionImpl* option = option_defs + 1;
  ulong* ival = doc->config.value;
  for ( /**/; !diff && option && option->name; ++option, ++ival )
  {
    diff = ( *ival != option->dflt );
  }
  return diff;
}


static int  SaveConfigToStream( TidyDocImpl* doc, StreamOut* out )
{
    int rc = 0;
    const TidyOptionImpl* option;
    for ( option=option_defs+1; 0==rc && option && option->name; ++option )
    {
        ulong ival = doc->config.value[ option->id ];
        if ( option->parser == NULL )
            continue;
        if ( ival == option->dflt && option->id != TidyDoctype)
            continue;

        if ( option->id == TidyDoctype )  /* Special case */
        {
          ulong dtmode = cfg( doc, TidyDoctypeMode );
          if ( dtmode == TidyDoctypeUser )
          {
            tmbstr t;
            
            /* add 2 double quotes */
            if (( t = (tmbstr)MemAlloc( tmbstrlen( (ctmbstr)ival) + 2 ) ))
            {
              t[0] = '\"'; t[1] = 0;
            
              tmbstrcat( t, (ctmbstr)ival );
              tmbstrcat( t, "\"" );
              rc = WriteOptionString( option, (ctmbstr)t, out );
            
              MemFree( t );
            }
          }
          else if ( dtmode == option_defs[TidyDoctypeMode].dflt )
            continue;
          else
            rc = WriteOptionPick( option, dtmode, out );
        }
        else if ( option->pickList )
          rc = WriteOptionPick( option, ival, out );
        else
        {
          switch ( option->type )
          {
          case TidyString:
            rc = WriteOptionString( option, (ctmbstr) ival, out );
            break;
          case TidyInteger:
            rc = WriteOptionInt( option, ival, out );
            break;
          case TidyBoolean:
            rc = WriteOptionBool( option, ival ? yes : no, out );
            break;
          }
        }
    }
    return rc;
}

int  SaveConfigFile( TidyDocImpl* doc, ctmbstr cfgfil )
{
    int status = -1;
    StreamOut* out = NULL;
    uint outenc = cfg( doc, TidyOutCharEncoding );
    uint nl = cfg( doc, TidyNewline );
    FILE* fout = fopen( cfgfil, "wb" );
    if ( fout )
    {
        out = FileOutput( fout, outenc, nl );
        status = SaveConfigToStream( doc, out );
        fclose( fout );
        MemFree( out );
    }
    return status;
}

int  SaveConfigSink( TidyDocImpl* doc, TidyOutputSink* sink )
{
    uint outenc = cfg( doc, TidyOutCharEncoding );
    uint nl = cfg( doc, TidyNewline );
    StreamOut* out = UserOutput( sink, outenc, nl );
    int status = SaveConfigToStream( doc, out );
    MemFree( out );
    return status;
}
