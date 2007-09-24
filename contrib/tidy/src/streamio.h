#ifndef __STREAMIO_H__
#define __STREAMIO_H__

/* streamio.h -- handles character stream I/O

  (c) 1998-2005 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: arnaud02 $ 
    $Date: 2005/03/03 12:49:24 $ 
    $Revision: 1.14 $ 

  Wrapper around Tidy input source and output sink
  that calls appropriate interfaces, and applies 
  necessary char encoding transformations: to/from
  ISO-10646 and/or UTF-8.

*/

#include "forward.h"
#include "buffio.h"
#include "fileio.h"

#ifdef __cplusplus
extern "C"
{
#endif
typedef enum
{
  FileIO,
  BufferIO,
  UserIO
} IOType;

/* states for ISO 2022

 A document in ISO-2022 based encoding uses some ESC sequences called
 "designator" to switch character sets. The designators defined and
 used in ISO-2022-JP are:

    "ESC" + "(" + ?     for ISO646 variants

    "ESC" + "$" + ?     and
    "ESC" + "$" + "(" + ?   for multibyte character sets
*/
typedef enum
{
  FSM_ASCII,
  FSM_ESC,
  FSM_ESCD,
  FSM_ESCDP,
  FSM_ESCP,
  FSM_NONASCII
} ISO2022State;

/************************
** Source
************************/

#define CHARBUF_SIZE 5

/* non-raw input is cleaned up*/
struct _StreamIn
{
    ISO2022State    state;     /* FSM for ISO2022 */
    Bool   pushed;
    tchar* charbuf;
    uint   bufpos;
    uint   bufsize;
    int    tabs;
    int    lastcol;
    int    curcol;
    int    curline;
    int    encoding;
    IOType iotype;

    TidyInputSource source;

#ifdef TIDY_WIN32_MLANG_SUPPORT
    ulong  mlang;
#endif

#ifdef TIDY_STORE_ORIGINAL_TEXT
    tmbstr otextbuf;
    size_t otextsize;
    uint   otextlen;
#endif

    /* Pointer back to document for error reporting */
    TidyDocImpl* doc;
};

void freeStreamIn(StreamIn* in);

StreamIn* FileInput( TidyDocImpl* doc, FILE* fp, int encoding );
StreamIn* BufferInput( TidyDocImpl* doc, TidyBuffer* content, int encoding );
StreamIn* UserInput( TidyDocImpl* doc, TidyInputSource* source, int encoding );

int       ReadBOMEncoding(StreamIn *in);
uint      ReadChar( StreamIn* in );
void      UngetChar( uint c, StreamIn* in );
uint      PopChar( StreamIn *in );
Bool      IsEOF( StreamIn* in );


/************************
** Sink
************************/

struct _StreamOut
{
    int   encoding;
    ISO2022State   state;     /* for ISO 2022 */
    uint  nl;

#ifdef TIDY_WIN32_MLANG_SUPPORT
    ulong mlang;
#endif

    IOType iotype;
    TidyOutputSink sink;
};

StreamOut* FileOutput( FILE* fp, int encoding, uint newln );
StreamOut* BufferOutput( TidyBuffer* buf, int encoding, uint newln );
StreamOut* UserOutput( TidyOutputSink* sink, int encoding, uint newln );

StreamOut* StdErrOutput(void);
StreamOut* StdOutOutput(void);
void       ReleaseStreamOut( StreamOut* out );

void WriteChar( uint c, StreamOut* out );
void outBOM( StreamOut *out );

ctmbstr GetEncodingNameFromTidyId(uint id);
ctmbstr GetEncodingOptNameFromTidyId(uint id);
int GetCharEncodingFromOptName(ctmbstr charenc);

/************************
** Misc
************************/

/* character encodings
*/
#define RAW         0
#define ASCII       1
#define LATIN0      2
#define LATIN1      3
#define UTF8        4
#define ISO2022     5
#define MACROMAN    6
#define WIN1252     7
#define IBM858      8

#if SUPPORT_UTF16_ENCODINGS
#define UTF16LE     9
#define UTF16BE     10
#define UTF16       11
#endif

/* Note that Big5 and SHIFTJIS are not converted to ISO 10646 codepoints
** (i.e., to Unicode) before being recoded into UTF-8. This may be
** confusing: usually UTF-8 implies ISO10646 codepoints.
*/
#if SUPPORT_ASIAN_ENCODINGS
#if SUPPORT_UTF16_ENCODINGS
#define BIG5        12
#define SHIFTJIS    13
#else
#define BIG5        9
#define SHIFTJIS    10
#endif
#endif

#ifdef TIDY_WIN32_MLANG_SUPPORT
/* hack: windows code page numbers start at 37 */
#define WIN32MLANG  36
#endif


/* char encoding used when replacing illegal SGML chars,
** regardless of specified encoding.  Set at compile time
** to either Windows or Mac.
*/
extern const int ReplacementCharEncoding;

/* Function for conversion from Windows-1252 to Unicode */
uint DecodeWin1252(uint c);

/* Function to convert from MacRoman to Unicode */
uint DecodeMacRoman(uint c);

/* Function for conversion from OS/2-850 to Unicode */
uint DecodeIbm850(uint c);

/* Function for conversion from Latin0 to Unicode */
uint DecodeLatin0(uint c);

/* Function to convert from Symbol Font chars to Unicode */
uint DecodeSymbolFont(uint c);
#ifdef __cplusplus
}
#endif


/* Use numeric constants as opposed to escape chars (\r, \n)
** to avoid conflict Mac compilers that may re-define these.
*/
#define CR    0xD
#define LF    0xA

#if   defined(MAC_OS_CLASSIC)
#define DEFAULT_NL_CONFIG TidyCR
#elif defined(_WIN32) || defined(OS2_OS)
#define DEFAULT_NL_CONFIG TidyCRLF
#else
#define DEFAULT_NL_CONFIG TidyLF
#endif


#endif /* __STREAMIO_H__ */
