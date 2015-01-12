/** Scintilla source code edit control
 ** @file ScintillaFake.h
 ** Definition of headless Scintilla widget - i.e. no UI.
 **
 ** Copyright 2013 by Todd Whiteman <toddw@activestate.com>
 ** The License.txt file describes the conditions under which this software may be distributed.
 **/

#ifndef SCINTILLAFAKE_H
#define SCINTILLAFAKE_H

#ifdef __cplusplus
extern "C" {
#endif

void		*scintilla_new		(void);
sptr_t		scintilla_send_message	(void *sci, unsigned int iMessage, uptr_t wParam, sptr_t lParam);

void		scintilla_release_resources(void);

#ifdef __cplusplus
}
#endif

#endif
