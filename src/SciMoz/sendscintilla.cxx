/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

// sendscintilla.cxx
// Scintilla plugin for Mozilla
// Communicate with a Scintilla instance
// Separated from npscimoz.cxx to avoid clashes between identifiers such as 
// Font and Window used both by Mozilla and Scintilla.
// Implemented by Neil Hodgson

#if defined(__APPLE__)
#import <Foundation/Foundation.h>     // Required for NSObject
#endif

#include <Platform.h> 
#include <Scintilla.h> 
#include "sendscintilla.h"

#if defined(_WINDOWS) && defined(HEADLESS_SCIMOZ)
#ifdef __cplusplus
extern "C" {
#endif
extern sptr_t scintilla_send_message(void* sci, unsigned int iMessage, uptr_t wParam, sptr_t lParam);
#ifdef __cplusplus
}
#endif
#endif

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

#ifdef USE_SCIN_DIRECT
long SendScintilla(SciFnDirect fnEditor, long ptrEditor, unsigned int msg, unsigned long wParam, long lParam) {
    return fnEditor(ptrEditor, msg, wParam, lParam);
}

long GetTextRange(SciFnDirect fnEditor, long ptrEditor, int min, int max, char *buffer) {
	TextRange tr = {{0, 0}, 0};
	tr.chrg.cpMin = min;
	tr.chrg.cpMax = max;
	tr.lpstrText = buffer;
	return SendScintilla(fnEditor, ptrEditor, SCI_GETTEXTRANGE, 0, reinterpret_cast<long>(&tr));
}

long GetStyledRange(SciFnDirect fnEditor, long ptrEditor, int min, int max, char *buffer) {
	TextRange tr = {{0, 0}, 0};
	tr.chrg.cpMin = min;
	tr.chrg.cpMax = max;
	tr.lpstrText = buffer;
	return SendScintilla(fnEditor, ptrEditor, SCI_GETSTYLEDTEXT, 0, reinterpret_cast<long>(&tr));
}

#else

long SendScintilla(WinID w, unsigned int msg, unsigned long wParam, long lParam) {
#if defined(GTK) || defined(__APPLE__)
	return Platform::SendScintilla(w, msg, wParam, lParam);
#elif defined(HEADLESS_SCIMOZ)
	//return scintilla_send_message(w, msg, wParam, lParam);
	long result = scintilla_send_message(w, msg, wParam, lParam);
	return result;
#else
	return ::SendMessage(w, msg, wParam, lParam);
#endif
}

long GetTextRange(WinID w, int min, int max, char *buffer) {
#ifdef SCI_NAMESPACE
	Scintilla::TextRange tr = {{0, 0}, 0};
#else
	TextRange tr = {{0, 0}, 0};
#endif
	tr.chrg.cpMin = min;
	tr.chrg.cpMax = max;
	tr.lpstrText = buffer;
	return SendScintilla(w, SCI_GETTEXTRANGE, 0, reinterpret_cast<long>(&tr));
}

long GetStyledRange(WinID w, int min, int max, char *buffer) {
#ifdef SCI_NAMESPACE
	Scintilla::TextRange tr = {{0, 0}, 0};
#else
	TextRange tr = {{0, 0}, 0};
#endif
	tr.chrg.cpMin = min;
	tr.chrg.cpMax = max;
	tr.lpstrText = buffer;
	return SendScintilla(w, SCI_GETSTYLEDTEXT, 0, reinterpret_cast<long>(&tr));
}
#endif
