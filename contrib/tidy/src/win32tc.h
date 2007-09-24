#ifndef __WIN32TC_H__
#define __WIN32TC_H__
#ifdef TIDY_WIN32_MLANG_SUPPORT

/* win32tc.h -- Interface to Win32 transcoding routines

   (c) 1998-2003 (W3C) MIT, ERCIM, Keio University
   See tidy.h for the copyright notice.

   $Id: win32tc.h,v 1.1 2003/04/25 04:26:12 hoehrmann Exp $
*/

uint Win32MLangGetCPFromName(ctmbstr encoding);
Bool Win32MLangInitInputTranscoder(StreamIn * in, uint wincp);
void Win32MLangUninitInputTranscoder(StreamIn * in);
int Win32MLangGetChar(byte firstByte, StreamIn * in, uint * bytesRead);

#endif /* TIDY_WIN32_MLANG_SUPPORT */
#endif /* __WIN32TC_H__ */
