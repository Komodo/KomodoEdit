/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// sendscintilla.cxx
// Scintilla plugin for Mozilla
// Communicate with a Scintilla instance
// Separated from npscimoz.cxx to avoid clashes between identifiers such as 
// Font and Window used both by Mozilla and Scintilla.
// Implemented by Neil Hodgson
#include "sendscintilla.h"
#include <Platform.h> 
#include <Scintilla.h> 

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
