#ifndef __UTF8_H__
#define __UTF8_H__

/* utf8.h -- convert characters to/from UTF-8

  (c) 1998-2004 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  CVS Info :

    $Author: terry_teague $ 
    $Date: 2004/08/02 02:32:47 $ 
    $Revision: 1.4 $ 

*/

#include "platform.h"
#include "buffio.h"

/* UTF-8 encoding/decoding support
** Does not convert character "codepoints", i.e. to/from 10646.
*/

int DecodeUTF8BytesToChar( uint* c, uint firstByte, ctmbstr successorBytes,
                           TidyInputSource* inp, int* count );

int EncodeCharToUTF8Bytes( uint c, tmbstr encodebuf,
                           TidyOutputSink* outp, int* count );


uint  GetUTF8( ctmbstr str, uint *ch );
tmbstr PutUTF8( tmbstr buf, uint c );

#define UNICODE_BOM_BE   0xFEFF   /* big-endian (default) UNICODE BOM */
#define UNICODE_BOM      UNICODE_BOM_BE
#define UNICODE_BOM_LE   0xFFFE   /* little-endian UNICODE BOM */
#define UNICODE_BOM_UTF8 0xEFBBBF /* UTF-8 UNICODE BOM */


Bool    IsValidUTF16FromUCS4( tchar ucs4 );
Bool    IsHighSurrogate( tchar ch );
Bool    IsLowSurrogate( tchar ch );

Bool    IsCombinedChar( tchar ch );
Bool    IsValidCombinedChar( tchar ch );

tchar   CombineSurrogatePair( tchar high, tchar low );
Bool    SplitSurrogatePair( tchar utf16, tchar* high, tchar* low );



#endif /* __UTF8_H__ */
