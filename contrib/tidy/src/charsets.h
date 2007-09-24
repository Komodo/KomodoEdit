/* charsets.h -- character set information and mappings

  (c) 1998-2003 (W3C) MIT, ERCIM, Keio University
  See tidy.h for the copyright notice.

  $Id: charsets.h,v 1.1 2003/04/28 04:45:02 hoehrmann Exp $
*/

uint GetEncodingIdFromName(ctmbstr name);
uint GetEncodingIdFromCodePage(uint cp);
uint GetEncodingCodePageFromName(ctmbstr name);
uint GetEncodingCodePageFromId(uint id);
ctmbstr GetEncodingNameFromId(uint id);
ctmbstr GetEncodingNameFromCodePage(uint cp);
