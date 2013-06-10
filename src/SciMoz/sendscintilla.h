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

// sendscintilla.h
// Scintilla plugin for Mozilla
// Communicate with a Scintilla instance
// Separated from npscimoz.cxx to avoid clashes between identifiers such as 
// Font and Window used both by Mozilla and Scintilla.
// Implemented by Neil Hodgson

#if defined(HEADLESS_SCIMOZ)
// Use a fake window handle.
typedef void *WinID;
#elif defined(__APPLE__)
typedef NSObject *WinID;
#else
#if defined(GTK) || !defined(_WIN32)
#include <gtk/gtk.h> 
typedef GtkWidget* WinID;
#else
#include <windows.h>
typedef HWND WinID;
// on windows, we can go direct and get better performance
// we could do the same for GTK, but there is no perf improvement,
// however, we should explore it as it might save us on other problems
//#define USE_SCIN_DIRECT
#endif
#endif

#ifdef USE_SCIN_DIRECT
long SendScintilla(SciFnDirect fnEditor, long ptrEditor, unsigned int iMessage, unsigned long wParam=0, long lParam=0);
long GetTextRange(SciFnDirect fnEditor, long ptrEditor, int min, int max, char *buffer);
long GetStyledRange(SciFnDirect fnEditor, long ptrEditor, int min, int max, char *buffer);
#else
long SendScintilla(WinID w, unsigned int iMessage, unsigned long wParam=0, long lParam=0);
long GetTextRange(WinID w, int min, int max, char *buffer);
long GetStyledRange(WinID w, int min, int max, char *buffer);
#endif
