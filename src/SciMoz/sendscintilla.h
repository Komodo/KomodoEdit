/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// sendscintilla.h
// Scintilla plugin for Mozilla
// Communicate with a Scintilla instance
// Separated from npscimoz.cxx to avoid clashes between identifiers such as 
// Font and Window used both by Mozilla and Scintilla.
// Implemented by Neil Hodgson

#if defined(__APPLE__)
typedef HIViewRef WinID;
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
