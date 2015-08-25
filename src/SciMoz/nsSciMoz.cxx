/*  -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
 *  ***** BEGIN LICENSE BLOCK *****
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

//#define SCIMOZ_DEBUG_VERBOSE

/////////////////////////////////////////////////////
//
// This file implements the SciMoz object
// The native methods of this class are supposed to
// be callable from JavaScript
//

#include "nsSciMoz.h"
#include "nsIClassInfoImpl.h"
#include "nsIVariant.h" /* for generated code */

// Define the snprintf function.
#if defined(_WINDOWS) && !defined(snprintf)
#define snprintf _snprintf
#endif

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif
#ifdef XP_MACOSX
#ifdef XP_UNIX
#undef XP_UNIX
#endif
#endif

#ifdef SCIMOZ_DEBUG_VERBOSE
	#define SCIMOZ_DEBUG_PRINTF(...) fprintf(stderr, __VA_ARGS__)
#else
	#define SCIMOZ_DEBUG_PRINTF(...) do { } while (0)
#endif

#include "plugin.h"


NS_IMPL_CLASSINFO(SciMoz, nullptr, 0, {0})

// Mozilla 31 code base changed - dropping NS_IMPL_ISUPPORTSN, so we support
// both till everyone updates their mozilla builds.
#ifdef NS_IMPL_ISUPPORTS7_CI
NS_IMPL_ISUPPORTS7_CI(SciMoz,
                      ISciMoz,
                      ISciMoz_Part0,
                      ISciMoz_Part1,
                      ISciMoz_Part2,
                      ISciMoz_Part3,
                      ISciMoz_Part4,
                      nsISupportsWeakReference)
#else
NS_IMPL_ISUPPORTS_CI(SciMoz,
                     ISciMoz,
                     ISciMoz_Part0,
                     ISciMoz_Part1,
                     ISciMoz_Part2,
                     ISciMoz_Part3,
                     ISciMoz_Part4,
                     nsISupportsWeakReference)
#endif

int16_t GenerateScimozId() {
    static int16_t s_pluginId = 0;
    return s_pluginId++;
}

SciMoz::SciMoz(SciMozPluginInstance* aPlugin)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::SciMoz %p\n",aPlugin);
#endif

    SciMozInitNPIdentifiers();
    mPlugin = aPlugin;

    SciMozInit();
}

SciMoz::~SciMoz()
{
    if (!isClosed) {
	fprintf(stderr, "SciMoz was not closed correctly before destructor called.\n");
    }
#ifdef SCIDEBUG_REFS
    fprintf(stderr,"SciMoz::~SciMoz %p\n", this);
#endif
    PlatformDestroy();

    isClosed = 1;
}

void SciMoz::SciMozInit() {
    isClosed = 0;
    wMain = 0;
    wEditor = 0;

#ifdef USE_SCIN_DIRECT
    fnEditor = 0;
    ptrEditor = 0;
#endif

    wParkingLot = 0;
    parked = true;
    initialised = true;
    width = 100;
    height = 100;
    bCouldUndoLastTime = PR_FALSE;
    fWindow = 0;

#if defined(_WINDOWS) && !defined(HEADLESS_SCIMOZ)
    LoadScintillaLibrary();
#endif
#if defined(XP_UNIX) && !defined(XP_MACOSX)
    sInGrab = 0;
#endif

    bracesStyle = 10;
    bracesCheck = true;
    bracesSloppy = true;

    // There is no cached text to start with.
    _scimozId = GenerateScimozId();
    _textId = 0;
    mLastLineCount = 1;
	mPluginVisibilityHack = false;

    PlatformNew();
}

// Default settings for Komodo scintilla widgets.
void SciMoz::DefaultSettings() {
    SendEditor(SCI_SETLEXER, SCLEX_CPP);
    SendEditor(SCI_STYLECLEARALL);    // Copies global style to all others

    // UTF-8 always.
    SendEditor(SCI_SETCODEPAGE, SC_CP_UTF8);

    // We set mouseDownCaptures to true, otherwise, when selecting text with the
    // mouse, if you go outside the scimoz plugin and release the mouse button,
    // scintilla will not know and continue to track the mouse position as if
    // you had not released the mouse button.
#if defined(XP_MACOSX) || defined(_WINDOWS)
    SendEditor(SCI_SETMOUSEDOWNCAPTURES, 1);
#else
    SendEditor(SCI_SETMOUSEDOWNCAPTURES, 0);
#endif
    SendEditor(SCI_SETMOUSEDWELLTIME, 500);

    // Indentation.
    SendEditor(SCI_SETINDENT, 4);
    SendEditor(SCI_SETTABWIDTH, 4);
    // Enable multiple caret editing.
    SendEditor(SCI_SETMULTIPLESELECTION, 1);
    SendEditor(SCI_SETADDITIONALSELECTIONTYPING, 1);
    SendEditor(SCI_SETMULTIPASTE, SC_MULTIPASTE_EACH);
#if !(defined(XP_MACOSX) || defined(_WINDOWS))
    // On Windows and Mac OSX, Alt+Mouse creates rectangular
    // selections. On Linux, Alt+Mouse is usually handled by the
    // window manager and moves windows. Thus Scintilla uses
    // Ctrl+Mouse for creating rectangular selections on Linux.
    // However, this prevents creating multiple selections with
    // Ctrl+Click (which is used on Windows and Mac OSX). We want
    // Ctrl+Click to create multiple selections on all platforms, so
    // redefine the modifier for rectangular selection creation.
    SendEditor(SCI_SETRECTANGULARSELECTIONMODIFIER, SCMOD_SUPER);
#endif
    // This allows a rectangular selection to extend past the
    // end of the line when there is a longer selected line.
    SendEditor(SCI_SETVIRTUALSPACEOPTIONS, SCVS_RECTANGULARSELECTION);
    // This allows Scintilla to perform indenting/dedenting when
    // there is a rectangular selection.
    SendEditor(SCI_SETTABINDENTS, 1);

#if defined(_WINDOWS)
    SendEditor(SCI_SETEOLMODE, SC_EOL_CRLF);
#else
    SendEditor(SCI_SETEOLMODE, SC_EOL_LF);
#endif

    // Annotation style, primarly for displaying inline lint results.
    SendEditor(SCI_ANNOTATIONSETVISIBLE, ANNOTATION_INDENTED);

    // Caret slop controls.
    SendEditor(SCI_SETXCARETPOLICY, CARET_SLOP, 75);

    SendEditor(SCI_SETPROPERTY, (unsigned long) "smartCloseTags", (long) "1");

    //SendEditor(SCI_SETMULTIPLESELECTION, 0);
    //SendEditor(SCI_SETMULTIPLESELECTION, 0);
    //SendEditor(SCI_SETMULTIPLESELECTION, 0);
    //SendEditor(SCI_SETMULTIPLESELECTION, 0);
    //SendEditor(SCI_SETMULTIPLESELECTION, 0);
}

long SciMoz::SendEditor(unsigned int Msg, unsigned long wParam, long lParam) {
    if (isClosed) {
        fprintf(stderr,"SciMoz::SendEditor %x (%d) %lx %lx used when closed!\n", Msg, Msg, wParam, lParam);
    }
#ifdef SCIMOZ_DEBUG_VERBOSE_VERBOSE
    fprintf(stderr,"SciMoz::SendEditor %x (%d) %lx %lx\n", Msg, Msg, wParam, lParam);
#endif
#if defined(_WINDOWS) && !defined(HEADLESS_SCIMOZ)
    // The "real" WndProc passes certain messages to Mozilla, so
    // we _must_ sneak in the back-door for those messages.
    // All other uses of SendEditor are also destined for Scintilla,
    // so this shortcut doesnt hurt their, either!
    return fPlatform.fDefaultChildWindowProc(wEditor, Msg, wParam, lParam);
#elif defined(USE_SCIN_DIRECT)
    // going direct we skip all the overhead of window messaging
    return fnEditor(ptrEditor, Msg, wParam, lParam);
#else // linux, etc.
    return ::SendScintilla(wEditor, Msg, wParam, lParam);
#endif
}

void SciMoz::Create(WinID hWnd) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::Create %lx\n", hWnd);
#endif
	PlatformCreate(hWnd);
	DefaultSettings();
}

static bool IsBrace(char ch) {
	return ch == '[' || ch == ']' || ch == '(' || ch == ')' || ch == '{' || ch == '}';
}

/**
 * Find if there is a brace next to the caret, checking before caret first, then
 * after caret. If brace found also find its matching brace.
 * @return @c true if inside a bracket pair.
 */
bool SciMoz::FindMatchingBracePosition(int &braceAtCaret, int &braceOpposite, bool sloppy) {
	// XXX bug 41930 for style matching in here.  there are a couple places
	// below where the style check is commented out.  this is due to
	// bug 41908.
	bool isInside = false;
	int mask = (1 << SendEditor(SCI_GETSTYLEBITS, 0, 0)) - 1;
	// XXX bracesStyle needs to come from language services
	// int bracesStyleCheck = bracesStyle;
	int caretPos = SendEditor(SCI_GETCURRENTPOS, 0, 0);
	braceAtCaret = -1;
	braceOpposite = -1;
	char charBefore = '\0';
	char styleBefore = '\0';
	int lengthDoc = SendEditor(SCI_GETLENGTH, 0, 0);
	if ((lengthDoc > 0) && (caretPos > 0)) {
		// Check to ensure not matching brace that is part of a multibyte character
		int posBefore = SendEditor(SCI_POSITIONBEFORE, caretPos);
		if (posBefore == (caretPos - 1)) {
			charBefore = static_cast<char>(SendEditor(SCI_GETCHARAT, posBefore, 0));
			styleBefore = static_cast<char>(SendEditor(SCI_GETSTYLEAT, posBefore, 0)) & mask;
		}
	}
	// Priority goes to character before caret
	if (charBefore && IsBrace(charBefore) /*&&
	        ((styleBefore == bracesStyleCheck) || (!bracesStyle))*/) {
		braceAtCaret = caretPos - 1;
	}
	bool colonMode = false;
	long lexLanguage = SendEditor(SCI_GETLEXER, 0);
	if ((lexLanguage == SCLEX_PYTHON) &&
	        (':' == charBefore) && (SCE_P_OPERATOR == styleBefore)) {
		braceAtCaret = caretPos - 1;
		colonMode = true;
	}
	bool isAfter = true;
	if (lengthDoc > 0 && sloppy && (braceAtCaret < 0) && (caretPos < lengthDoc)) {
		// No brace found so check other side
		// Check to ensure not matching brace that is part of a multibyte character
		char charAfter = static_cast<char>(SendEditor(SCI_GETCHARAT, caretPos, 0));
		char styleAfter = static_cast<char>(SendEditor(SCI_GETSTYLEAT, caretPos, 0)) & mask;
		if (charAfter && IsBrace(charAfter)/* && (styleAfter == bracesStyleCheck)*/) {
			braceAtCaret = caretPos;
			isAfter = false;
		} else
		if ((lexLanguage == SCLEX_PYTHON) &&
			(':' == charAfter) && (SCE_P_OPERATOR == styleAfter)) {
			braceAtCaret = caretPos;
			colonMode = true;
		}
	}
	if (braceAtCaret >= 0) {
		if (colonMode) {
			int lineStart = SendEditor(SCI_LINEFROMPOSITION, braceAtCaret);
			int lineMaxSubord = SendEditor(SCI_GETLASTCHILD, lineStart, -1);
			braceOpposite = SendEditor(SCI_GETLINEENDPOSITION, lineMaxSubord);
		} else {
			braceOpposite = SendEditor(SCI_BRACEMATCH, braceAtCaret, 0);
		}
		if (braceOpposite > braceAtCaret) {
			isInside = isAfter;
		} else {
			isInside = !isAfter;
		}
	}
	return isInside;
}

void SciMoz::BraceMatch() {
	if (!bracesCheck)
		return;
	int braceAtCaret = -1;
	int braceOpposite = -1;
	FindMatchingBracePosition(braceAtCaret, braceOpposite, bracesSloppy);
	if (braceAtCaret != -1 && braceOpposite == -1) {
		SendEditor(SCI_BRACEBADLIGHT, braceAtCaret, 0);
		SendEditor(SCI_SETHIGHLIGHTGUIDE, 0);
	} else {
		char chBrace = static_cast<char>(SendEditor(SCI_GETCHARAT, braceAtCaret, 0));
		SendEditor(SCI_BRACEHIGHLIGHT, braceAtCaret, braceOpposite);
		int columnAtCaret = SendEditor(SCI_GETCOLUMN, braceAtCaret, 0);
		int columnOpposite = SendEditor(SCI_GETCOLUMN, braceOpposite, 0);
		if (chBrace == ':') {
			int lineStart = SendEditor(SCI_LINEFROMPOSITION, braceAtCaret);
			int indentPos = SendEditor(SCI_GETLINEINDENTPOSITION, lineStart, 0);
			int indentPosNext = SendEditor(SCI_GETLINEINDENTPOSITION, lineStart + 1, 0);
			columnAtCaret = SendEditor(SCI_GETCOLUMN, indentPos, 0);
			int columnAtCaretNext = SendEditor(SCI_GETCOLUMN, indentPosNext, 0);
			int indentSize = SendEditor(SCI_GETINDENT);
			if (columnAtCaretNext - indentSize > 1)
				columnAtCaret = columnAtCaretNext - indentSize;
			//Platform::DebugPrintf(": %d %d %d\n", lineStart, indentPos, columnAtCaret);
			if (columnOpposite == 0)	// If the final line of the structure is empty
				columnOpposite = columnAtCaret;
		}
		SendEditor(SCI_SETHIGHLIGHTGUIDE, SCIMIN(columnAtCaret, columnOpposite), 0);
	}
}

NS_IMETHODIMP SciMoz::DoBraceMatch()
{
	SCIMOZ_CHECK_VALID("DoBraceMatch");
	BraceMatch();
	return NS_OK;
}
bool SciMoz::DoBraceMatch(const NPVariant * /*args*/, uint32_t argCount, NPVariant * /*result*/) {
        SCIMOZ_CHECK_THREAD("DoBraceMatch", false)
        SCIMOZ_CHECK_ALIVE("DoBraceMatch", false)
	if (argCount != 0) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 0 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	BraceMatch();
	return true;
}

NS_IMETHODIMP SciMoz::EnablePluginVisibilityHack()
{
	SCIMOZ_CHECK_VALID("EnablePluginVisibilityHack");
	mPluginVisibilityHack = true;
	return NS_OK;
}
bool SciMoz::EnablePluginVisibilityHack(const NPVariant * /*args*/, uint32_t argCount, NPVariant * /*result*/) {
        SCIMOZ_CHECK_THREAD("EnablePluginVisibilityHack", false)
        SCIMOZ_CHECK_ALIVE("EnablePluginVisibilityHack", false)
	if (argCount != 0) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 0 arguments, got %i\n", __FUNCTION__, argCount);
		return false;
	}
	EnablePluginVisibilityHack();
	return true;
}

NS_IMETHODIMP SciMoz::UpdateMarginWidths() {
	// Only update when the line-number margin is visible.
	long oldMarginWidth = SendEditor(SCI_GETMARGINWIDTHN, MARGIN_LINENUMBERS, 0);
	if (oldMarginWidth > 0) {
		static char buf[32];
		// We are lazy and use mLastLineCount - which gets updated
		// whenever the text is modified - so it should be accurate
		// enough.
		if (mLastLineCount < 100) {
			// Minimum width is two digits.
			snprintf(buf, 32, "00");
		} else {
			// Set the width based on the line number count.
			snprintf(buf, 32, "%ld", mLastLineCount);
			buf[31] = '\0'; // ensure null terminated
		}
		long newMarginWidth = SendEditor(SCI_TEXTWIDTH, STYLE_LINENUMBER, reinterpret_cast<long>(buf));
		newMarginWidth += 4; // 4px padding, otherwise it overlaps the left symbol margin
		if (oldMarginWidth != newMarginWidth) {
			// Set the margin width if it hasn't changed size.
			//printf("\nUpdating margin width from %ld to %ld\n", oldMarginWidth, newMarginWidth);
			SendEditor(SCI_SETMARGINWIDTHN, MARGIN_LINENUMBERS, newMarginWidth);
		}
	}
	return NS_OK;
}
bool SciMoz::UpdateMarginWidths(const NPVariant * /*args*/, uint32_t argCount, NPVariant *result) {
        if (argCount != 0) return false;
        /* return value of type void - needed? */
        NPN_ReleaseVariantValue(result);
	return NS_SUCCEEDED(UpdateMarginWidths());
}

//#define SCIMOZ_DEBUG_NOTIFY
void SciMoz::Notify(long lParam) {
	SCNotification *notification = reinterpret_cast<SCNotification *>(lParam);
	if (isClosed) {
		if (notification->nmhdr.code != SCN_PAINTED) {
			fprintf(stderr,"SciMoz::Notify %d used when closed!\n",
				notification->nmhdr.code);
		}
		return;
	}

	if (notification->nmhdr.code == SCN_PAINTED) {
		bool bCanUndoNow = SendEditor(SCI_CANUNDO, 0, 0);
		bool bCanRedoNow = SendEditor(SCI_CANREDO, 0, 0);
		if (bCouldUndoLastTime != bCanUndoNow || bCouldRedoLastTime != bCanRedoNow) {
#ifdef SCIMOZ_DEBUG_NOTIFY
			fprintf(stderr,"Scintilla sending 'undo' event\n");
#endif
			SendUpdateCommands("undo");
			bCouldUndoLastTime = bCanUndoNow;
			bCouldRedoLastTime = bCanRedoNow;
		}
		return;
	}

#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr, "SciMoz::Notify %d\n", notification->nmhdr.code);
#endif

	PRUint32 mask;
	void *handle = nullptr;
	nsCOMPtr<ISciMozEvents> eventSink;
	switch (notification->nmhdr.code) {
		/*
		case SCN_STYLENEEDED:
			mask = ISciMozEvents::SME_STYLENEEDED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnStyleNeeded(notification->position);
			break;
		*/
		case SCN_CHARADDED:
			mask = ISciMozEvents::SME_CHARADDED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnCharAdded(notification->ch);
			break;
		case SCN_SAVEPOINTREACHED:
			mask = ISciMozEvents::SME_SAVEPOINTREACHED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnSavePointReached();
			break;
		case SCN_SAVEPOINTLEFT:
			mask = ISciMozEvents::SME_SAVEPOINTLEFT;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnSavePointLeft();
			break;
		/*
		case SCN_MODIFYATTEMPTRO:
			mask = ISciMozEvents::SME_MODIFYATTEMPTRO;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnModifyAttemptRO();
			break;
		case SCN_KEY:
			mask = ISciMozEvents::SME_KEY;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnKey(notification->ch, notification->modifiers);
			break;
		*/
		case SCN_DOUBLECLICK:
			mask = ISciMozEvents::SME_DOUBLECLICK;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDoubleClick();
			break;
		case SCN_UPDATEUI:
			mask = ISciMozEvents::SME_UPDATEUI;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnUpdateUI(notification->updated,
						      notification->length);
			break;
		case SCN_MODIFIED: {
			// if we are deleting or inserting on a fold, expand
			// the fold first
			if ((notification->modificationType & (SC_MOD_BEFOREDELETE | SC_MOD_BEFOREINSERT)) &&
			    // Quick check to see if there are any folded lines.
			    !SendEditor(SCI_GETALLLINESVISIBLE, 0, 0))
			{
				// If there's a selection, test both ends of it
				int positions[2];
				int lineAnchors[2];
				int foldLevel;
				int numLineAnchors = 1;
				positions[0] = SendEditor(SCI_GETSELECTIONSTART, 0, 0);
				lineAnchors[0] = SendEditor(SCI_LINEFROMPOSITION, positions[0], 0);
				positions[1] = SendEditor(SCI_GETSELECTIONEND, 0, 0);
				if (positions[1] > positions[0]) {
					lineAnchors[1] = SendEditor(SCI_LINEFROMPOSITION, positions[1], 0);
					if (lineAnchors[1] > lineAnchors[0]) {
						numLineAnchors = 2;
					}
				}
				
				for (int i = 0; i < numLineAnchors; i++) {
					foldLevel = SendEditor(SCI_GETFOLDLEVEL, lineAnchors[i], 0);
					if ((foldLevel & SC_FOLDLEVELHEADERFLAG)
					    && !SendEditor(SCI_GETFOLDEXPANDED, lineAnchors[i], 0)) {
						SendEditor(SCI_TOGGLEFOLD, lineAnchors[i], 0);
					}
				}
			}

			if (!(notification->modificationType & (SC_MOD_INSERTTEXT | SC_MOD_DELETETEXT | SC_MOD_BEFOREDELETE))) {
				// we currently only want these events, break otherwise
				//fprintf(stderr ,"bail on calling onModified\n");
				break;
			}

			bool isInsertOrDeleteText = notification->modificationType & (SC_MOD_INSERTTEXT | SC_MOD_DELETETEXT);
			if (isInsertOrDeleteText) {
				// Buffer has changed, reset the text cache.
				if (_textId >= 0x7FFF)
                    _textId = 0; // Wrap around to start.
                _textId += 1;
			}

			// Check if the line count has changed - if so, we'll
			// need to check if the line number margin width needs
			// updating.
			long lineCount = SendEditor(SCI_GETLINECOUNT, 0, 0);
			if (lineCount != mLastLineCount) {
				mLastLineCount = lineCount;
				UpdateMarginWidths();
			}

			nsAutoString uString;
			if (isInsertOrDeleteText && notification->text && (notification->length > 0)) {
				uString = NS_ConvertUTF8toUTF16(notification->text, notification->length);
			} else {
				uString.Truncate();
			}
			mask = ISciMozEvents::SME_MODIFIED;
			// Note: We are passing unicode text, but length is
			//       given using bytes, so uString.Length() could be
			//       different to notification->length.
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink)))) {
				eventSink->OnModified(notification->position,
						      notification->modificationType,
						      uString,
						      notification->length,
						      notification->linesAdded,
						      notification->line,
						      notification->foldLevelNow,
						      notification->foldLevelPrev);
			}
			}
			break;
		/*
		case SCN_MACRORECORD:
			mask = ISciMozEvents::SME_MACRORECORD;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnMacroRecord(
				    notification->message, notification->wParam, notification->lParam);
			break;
		*/
		case SCN_MARGINCLICK:
			mask = ISciMozEvents::SME_MARGINCLICK;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnMarginClick(
					notification->modifiers, notification->position, notification->margin);
			break;
		case SCN_NEEDSHOWN:
			mask = ISciMozEvents::SME_NEEDSHOWN;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		/*
		case SCN_PAINTED:
			// No need to waste time with an event for this ATM.
			mask = ISciMozEvents::SME_PAINTED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnPainted();
			break;
		*/
		case SCN_USERLISTSELECTION:
			{
				nsAutoString uText;
				if (notification->text) {
					uText = NS_ConvertUTF8toUTF16(notification->text);
				} else {
					uText.Truncate();
				}
				mask = ISciMozEvents::SME_USERLISTSELECTION;
				while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
					eventSink->OnOtherNotification(mask, notification->position, uText, notification->listType);
			}
			break;
		case SCN_DWELLSTART:
		case SCN_DWELLEND:
			{
				// Convert into Mozilla pixel co-ordinates - bug 100492.
#ifdef XP_MACOSX
				const int kDefaultDPI = 72;
#else
				const int kDefaultDPI = 96;
#endif
				int logPixelsX = SendEditor(SCI_GETLOGPIXELSX, 0, 0);
				int logPixelsY = SendEditor(SCI_GETLOGPIXELSY, 0, 0);
				int dwell_x = (notification->x * kDefaultDPI) / logPixelsX;
				int dwell_y = (notification->y * kDefaultDPI) / logPixelsY;
				if (notification->nmhdr.code == SCN_DWELLSTART) {
					mask = ISciMozEvents::SME_DWELLSTART;
					while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
						eventSink->OnDwellStart(notification->position, dwell_x, dwell_y);
				} else {
					mask = ISciMozEvents::SME_DWELLEND;
					while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
						eventSink->OnDwellEnd(notification->position, dwell_x, dwell_y);
				}
			}
			break;
		case SCN_ZOOM:
			mask = ISciMozEvents::SME_ZOOM;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnZoom();
			break;
		case SCN_HOTSPOTDOUBLECLICK:
			mask = ISciMozEvents::SME_HOTSPOTDOUBLECLICK;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnHotSpotDoubleClick(notification->position, notification->modifiers);
			break;
		case SCN_CALLTIPCLICK:
			mask = ISciMozEvents::SME_CALLTIPCLICK;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		case SCN_AUTOCSELECTION:
			{
				nsAutoString uText;
				if (notification->text) {
					uText = NS_ConvertUTF8toUTF16(notification->text);
				} else {
					uText.Truncate();
				}
				mask = ISciMozEvents::SME_AUTOCSELECTION;
				while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
					eventSink->OnOtherNotification(mask, notification->position, uText, notification->modifiers);
			}
			break;
		case SCN_INDICATORCLICK:
			mask = ISciMozEvents::SME_INDICATORCLICK;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		case SCN_INDICATORRELEASE:
			mask = ISciMozEvents::SME_INDICATORRELEASE;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		case SCN_AUTOCCANCELLED:
			mask = ISciMozEvents::SME_AUTOCCANCELLED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		case SCN_AUTOCCHARDELETED:
			mask = ISciMozEvents::SME_AUTOCCHARDELETED;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnOtherNotification(mask, notification->position, NS_LITERAL_STRING(""), notification->modifiers);
			break;
		case SCN_URIDROPPED:
			if (notification->text) {
				NS_ConvertUTF8toUTF16 uText(notification->text);
				mask = ISciMozEvents::SME_URIDROPPED;
				while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
					eventSink->OnOtherNotification(mask, 0, uText, 0);
			}
			break;

		default: {
                    /*  XXX
                        We don't handle all the scimoz notifications any longer,
                        so dont bother with logging it.
                        
			nsCOMPtr<nsIConsoleService> consoleService = do_GetService(NS_CONSOLESERVICE_CONTRACTID);
			NS_ABORT_IF_FALSE(consoleService, "Where is the console service?");
			if (consoleService)
				consoleService->LogStringMessage(NS_LITERAL_STRING("New Scintilla notification we don't respond to!").get());
                    */
			break;
          }
	}
}


/* attribute boolean isFocused; */
NS_IMETHODIMP SciMoz::SetIsFocused(bool /*focus*/) {
	return NS_ERROR_NOT_IMPLEMENTED; /* in XPFacer.p.py as manual setter */
}

/* attribute boolean isFocused; */
NS_IMETHODIMP SciMoz::GetIsFocused(bool  * /*_retval*/) {
	return NS_ERROR_NOT_IMPLEMENTED; /* in XPFacer.p.py as manual getter */
}


/* void markClosed(); */

NS_IMETHODIMP SciMoz::MarkClosed() 
{
	if (!isClosed) {
		SCIMOZ_DEBUG_PRINTF("SciMoz::MarkClosed\n");
		// Disable ondwell handlers.
		SendEditor(SCI_SETMOUSEDWELLTIME, SC_TIME_FOREVER, 0);
		// Turn off all of the scintilla timers.
		SendEditor(SCI_STOPTIMERS, 0, 0);
		PlatformMarkClosed();
		isClosed = true;
	}
	return NS_OK;
}

bool SciMoz::MarkClosed(const NPVariant * /*args*/, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 0) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 0 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	MarkClosed();
	return true;
}

/* void HookEvents (in nsISupports eventListener, [optional] in PRInt32 mask); */
NS_IMETHODIMP SciMoz::HookEvents(ISciMozEvents *eventListener, PRInt32 mask) {
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::HookEvents(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::HookEvents (%u args)\n", argCount);
	if (argCount != 1 && argCount != 2) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 or 2 arguments, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (!NPVARIANT_IS_OBJECT(args[0])) {
		SCIMOZ_DEBUG_PRINTF("%s: parameter is not an object\n",
				    __FUNCTION__);
		return false;
	}
	if (!NPN_HasMethod(mPlugin->GetNPP(),
			   NPVARIANT_TO_OBJECT(args[0]),
			   NPN_GetStringIdentifier("QueryInterface")))
	{
		SCIMOZ_DEBUG_PRINTF("%s: object has no QueryInterface method\n",
				    __FUNCTION__);
		return false;
	}

	// Default to all events
	int mask = ISciMozEvents::SME_ALL; /*& ~ISciMozEvents::SME_PAINTED*/
	if (argCount > 1) {
		if (!NPVARIANT_IS_INT32(args[1])) {
			SCIMOZ_DEBUG_PRINTF("%s: second parameter is not an integer\n",
					    __FUNCTION__, argCount);
			return false;
		}
		// Don't touch the mask if the user gave 0 (assume that means
		// they want everything).
		PRUint32 given_mask = NPVARIANT_TO_INT32(args[1]);
		if (given_mask) {
			mask = mask & given_mask;
		}
	}

	// we need to get a ISciMozEvents IID, wrapped in JS and then
	// wrapped in NPAPI.  The easiest way is to ask JS to do it for us.
	NPString script = { "Components.interfaces.ISciMozEvents" };
	script.UTF8Length = strlen(script.UTF8Characters);
	NPVariant iid = { NPVariantType_Void };
	if (!NPN_Evaluate(mPlugin->GetNPP(),
			  NPVARIANT_TO_OBJECT(args[0]),
			  &script,
			  &iid))
	{
		SCIMOZ_DEBUG_PRINTF("%s: failed to get ISciMozEvents\n",
				    __FUNCTION__);
		return false;
	}

	NPVariant eventListenerVar;
	if (!NPN_Invoke(mPlugin->GetNPP(),
			NPVARIANT_TO_OBJECT(args[0]),
			NPN_GetStringIdentifier("QueryInterface"),
			&iid,
			1,
			&eventListenerVar))
	{
		SCIMOZ_DEBUG_PRINTF("%s: QI failed\n", __FUNCTION__);
		return false;
	}
	if (!NPVARIANT_IS_OBJECT(eventListenerVar)) {
		SCIMOZ_DEBUG_PRINTF("%s: QI result is not an object", __FUNCTION__);
		return false;
	}
	SCIMOZ_DEBUG_PRINTF("%s: Hooking with mask %08X\n", __FUNCTION__, mask);
	return listeners.Add(mPlugin->GetNPP(),
			     NPVARIANT_TO_OBJECT(eventListenerVar),
			     PR_FALSE,
			     mask);
}

/* void UnhookEvents (in ISciMozEvents eventListener); */
NS_IMETHODIMP SciMoz::UnhookEvents(ISciMozEvents *eventListener) {
	SCIMOZ_CHECK_VALID("UnhookEvents");
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::UnhookEvents(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::UnhookEvents\n");
	if (argCount != 1) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (!NPVARIANT_IS_OBJECT(args[0])) {
		SCIMOZ_DEBUG_PRINTF("%s: parameter is not an object\n",
				    __FUNCTION__);
		return false;
	}
	if (!NPN_HasMethod(mPlugin->GetNPP(),
			   NPVARIANT_TO_OBJECT(args[0]),
			   NPN_GetStringIdentifier("QueryInterface")))
	{
		SCIMOZ_DEBUG_PRINTF("%s: object has no QueryInterface method\n",
				    __FUNCTION__);
		return false;
	}
	// we need to get a nsIDOMWindowInternal IID, wrapped in JS and then
	// wrapped in NPAPI.  The easiest way is to ask JS to do it for us.
	NPString script = { "Components.interfaces.ISciMozEvents" };
	script.UTF8Length = strlen(script.UTF8Characters);
	NPVariant iid = { NPVariantType_Void };
	if (!NPN_Evaluate(mPlugin->GetNPP(),
			  NPVARIANT_TO_OBJECT(args[0]),
			  &script,
			  &iid))
	{
		SCIMOZ_DEBUG_PRINTF("%s: failed to get ISciMozEvents\n",
				    __FUNCTION__);
		return false;
	}

	NPVariant eventListenerVar;
	if (!NPN_Invoke(mPlugin->GetNPP(),
			NPVARIANT_TO_OBJECT(args[0]),
			NPN_GetStringIdentifier("QueryInterface"),
			&iid,
			1,
			&eventListenerVar))
	{
		SCIMOZ_DEBUG_PRINTF("%s: QI failed\n", __FUNCTION__);
		return false;
	}
	if (!NPVARIANT_IS_OBJECT(eventListenerVar)) {
		SCIMOZ_DEBUG_PRINTF("%s: QI result is not an object", __FUNCTION__);
		return false;
	}
	listeners.Remove(mPlugin->GetNPP(),
			 NPVARIANT_TO_OBJECT(eventListenerVar));
	return true;
}

/* void getStyledText (in long min, in long max, out unsigned long count, [array, size_is (count), retval] out octet str); */
NS_IMETHODIMP SciMoz::GetStyledText(PRInt32 min, PRInt32 max, PRUint32 *count, PRUint8 **str) {
	SCIMOZ_CHECK_VALID("GetStyledText");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetStyledText\n");
#endif
	size_t length = (max - min + 1) * 2;
	char *buffer = static_cast<char*>(NS_Alloc(length + 1));
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
        buffer[length] = 0;
#ifdef USE_SCIN_DIRECT
	long bytesCopied = GetStyledRange(fnEditor, ptrEditor, min, max, buffer);
#else
	long bytesCopied = GetStyledRange(wEditor, min, max, buffer);
#endif
        NS_ASSERTION(buffer[length] == NULL, "Buffer overflow");
	*str = reinterpret_cast<PRUint8*>(buffer);
	*count = bytesCopied;
	return (*str) ? NS_OK : NS_ERROR_OUT_OF_MEMORY;
}

/**
 * Convert each `buf` array element into a JS array element (of integer type).
 *
 * `element_size` is the C array element size, e.g. (1 for char, 2 for short, 4 for int, ...).
 */
bool _NPN_ConvertCArrayToJSNumberArray(NPP instance, PRUint32 count, PRUint8 element_size, void *array_ptr, NPVariant *result)
{
	NPObject *win = nullptr;
	NPError err = NPN_GetValue(instance, NPNVWindowNPObject, &win);
	if (err != NPERR_NO_ERROR) {
		SCIMOZ_DEBUG_PRINTF("%s: failed to get window\n",
				    __FUNCTION__);
		return false;
	}
	NPString script = { "new Array()" };
	script.UTF8Length = strlen(script.UTF8Characters);
	if (!NPN_Evaluate(instance,
			  win,
			  &script,
			  result))
	{
		SCIMOZ_DEBUG_PRINTF("%s: failed to create array\n",
				    __FUNCTION__);
		return false;
	}
	NPN_RetainObject(NPVARIANT_TO_OBJECT(*result));

	/* The accessor/copier is different depending on the element size. */
	if (element_size == sizeof(PRUint8)) {
		PRUint8 *pthis = (PRUint8 *)array_ptr;
		PRUint8 mask = 0xFF;
		for (PRUint32 i = 0; i < count; ++i, pthis++) {
			NPVariant v;
			INT32_TO_NPVARIANT((*pthis) & mask, v);
			NPN_SetProperty(instance,
					NPVARIANT_TO_OBJECT(*result),
					NPN_GetIntIdentifier(i),
					&v);
		}
	} else if (element_size == sizeof(PRUint16)) {
		PRUint16 *pthis = (PRUint16 *)array_ptr;
		PRUint16 mask = 0xFFFF;
		for (PRUint32 i = 0; i < count; ++i, pthis++) {
			NPVariant v;
			INT32_TO_NPVARIANT((*pthis) & mask, v);
			NPN_SetProperty(instance,
					NPVARIANT_TO_OBJECT(*result),
					NPN_GetIntIdentifier(i),
					&v);
		}
	} else if (element_size == sizeof(PRUint32)) {
		PRUint32 *pthis = (PRUint32 *)array_ptr;
		PRUint32 mask = 0xFFFFFFFF;
		for (PRUint32 i = 0; i < count; ++i, pthis++) {
			NPVariant v;
			INT32_TO_NPVARIANT((*pthis) & mask, v);
			NPN_SetProperty(instance,
					NPVARIANT_TO_OBJECT(*result),
					NPN_GetIntIdentifier(i),
					&v);
		}
	}

	return true;
}

bool SciMoz::GetStyledText(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 3) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_INT32(args[1])) return false;
	if (!NPVARIANT_IS_OBJECT(args[2])) return false;
	PRUint32 count;
	PRUint8* buf = nullptr;
	nsresult rv = GetStyledText(NPVARIANT_TO_INT32(args[0]),
				    NPVARIANT_TO_INT32(args[1]),
						       &count,
						       &buf);
	if (NS_FAILED(rv)) return false;

	NPVariant npCount;
	INT32_TO_NPVARIANT(count, npCount);
	bool success = NPN_SetProperty(mPlugin->GetNPP(),
				       NPVARIANT_TO_OBJECT(args[2]),
				       NPN_GetStringIdentifier("value"),
				       &npCount);
	if (!success) {
		NS_Free(buf);
		return false;
	}

	NPN_ReleaseVariantValue(result);

	// gah, this is an [array] octet, not a string. allocate a JS array :|
	if (!_NPN_ConvertCArrayToJSNumberArray(mPlugin->GetNPP(), count, sizeof(PRUint8), buf, result)) {
		NS_Free(buf);
		return false;
	}

	NS_Free(buf);
	NPN_ReleaseObject(NPVARIANT_TO_OBJECT(*result));
	return true;
}

nsresult SciMoz::_GetStyleBuffer(PRInt32 min, PRInt32 max, PRUint16 *buffer)
{
	PRInt32 length = max - min;
	size_t dlength = length * 2;
	char *dbuffer = new char[dlength+2]; // +2 as getstyledtext adds two \0 bytes at the end
	if (!dbuffer)
		return NS_ERROR_OUT_OF_MEMORY;
	dbuffer[dlength]=0;
#ifdef USE_SCIN_DIRECT
	GetStyledRange(fnEditor, ptrEditor, min, max, dbuffer);
#else
	GetStyledRange(wEditor, min, max, dbuffer);
#endif
        NS_ASSERTION(dbuffer[dlength] == NULL, "Buffer overflow");

	size_t pos;
	size_t i;
	for (pos=0, i=1; i < dlength; ++pos, i+=2) {
		buffer[pos] = dbuffer[i];
	}

	delete []dbuffer;
	buffer[length] = 0;
	return NS_OK;
}

/* void getStyleRange (in long min, in long max, out unsigned long count, [array, size_is (count), retval] out octet styles); */
NS_IMETHODIMP SciMoz::GetStyleRange(PRInt32 min, PRInt32 max, PRUint32 *count, PRUint16 **str)
{
	SCIMOZ_CHECK_VALID("GetStyleRange");
	// converting the string UTF8->UTF16->UTF8)
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetStyleRange\n");
#endif
	PRInt32 textlength = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
	if (max == -1)
		max = textlength;
	PRInt32 length = (max - min);
	if (length < 0 || min < 0 || max < 0 || max > textlength) {
		return NS_ERROR_INVALID_ARG;
	}

	PRUint16 *buffer = static_cast<PRUint16*>(NS_Alloc(sizeof(PRUint16) * (length + 1)));
	if (!buffer) {
		return NS_ERROR_OUT_OF_MEMORY;
	}

	nsresult rv = _GetStyleBuffer(min, max, buffer);
	if (NS_FAILED(rv)) {
		NS_Free(buffer);
		return rv;
	}

	*str = buffer;
	*count = length;
	return NS_OK;
}

bool SciMoz::GetStyleRange(const NPVariant *args, uint32_t argCount, NPVariant *result) {
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetStyleRange\n");
#endif
	if (argCount != 3) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_INT32(args[1])) return false;
	if (!NPVARIANT_IS_OBJECT(args[2])) return false;

	int min = NPVARIANT_TO_INT32(args[0]);
	int max = NPVARIANT_TO_INT32(args[1]);
	int textlength = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
	if (max == -1)
		max = textlength;
	int length = max - min;
	if (length < 0 || min < 0 || max < 0 || max > textlength) {
		return false;
	}
	uint16_t *buf = static_cast<uint16_t*>(NPN_MemAlloc(sizeof(uint16_t) * (length + 1)));
	if (!buf)
		return false;

	nsresult rv = _GetStyleBuffer(min, max, buf);
	if (NS_FAILED(rv)) {
		NPN_MemFree(buf);
		return false;
	}

	NPVariant npCount;
	INT32_TO_NPVARIANT(length, npCount);
	bool success = NPN_SetProperty(mPlugin->GetNPP(),
				       NPVARIANT_TO_OBJECT(args[2]),
				       NPN_GetStringIdentifier("value"),
				       &npCount);
	if (!success) {
		NPN_MemFree(buf);
		return false;
	}

	NPN_ReleaseVariantValue(result);

	// gah, this is an [array] octet, not a string. allocate a JS array :|
	if (!_NPN_ConvertCArrayToJSNumberArray(mPlugin->GetNPP(), length, sizeof(uint16_t), buf, result)) {
		NPN_MemFree(buf);
		return false;
	}

	NPN_MemFree(buf);
	NPN_ReleaseObject(NPVARIANT_TO_OBJECT(*result));
	return true;
}

/* long getCurLine (out string text); */
NS_IMETHODIMP SciMoz::GetCurLine(nsAString & text, PRInt32 *_retval) {
	SCIMOZ_CHECK_VALID("GetCurLine");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetCurLine\n");
#endif
	int currentPos = SendEditor(SCI_GETCURRENTPOS, 0, 0);
    	int lineCurrent = SendEditor(SCI_LINEFROMPOSITION, currentPos, 0);
	int lineLength = SendEditor(SCI_LINELENGTH, lineCurrent, 0);
	char *buffer = new char[lineLength + 1];
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
	buffer[lineLength]=0;
	*_retval = SendEditor(SCI_GETCURLINE, lineLength, reinterpret_cast<long>(buffer));
	NS_ASSERTION(buffer[lineLength] == NULL, "Buffer overflow");

	text =  NS_ConvertUTF8toUTF16(buffer, lineLength);

	delete []buffer;
	return NS_OK;
}

bool SciMoz::GetCurLine(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 1) return false;
	if (!NPVARIANT_IS_OBJECT(args[0])) return false;
	nsString text;
	PRInt32 retval;
	nsresult rv = GetCurLine(text, &retval);
	if (NS_FAILED(rv)) return false;

	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);

	NS_ConvertUTF16toUTF8 textUtf8(text);
	NPUTF8* buf = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(textUtf8.Length()));
	if (!buf) return false;
	memcpy(buf, textUtf8.get(), textUtf8.Length());
	NPVariant textNp;
	STRINGN_TO_NPVARIANT(buf, textUtf8.Length(), textNp);
	bool success = NPN_SetProperty(mPlugin->GetNPP(),
				       NPVARIANT_TO_OBJECT(args[0]),
				       NPN_GetStringIdentifier("value"),
				       &textNp);
	if (!success) {
		NPN_MemFree(buf);
		return false;
	}
	return true;
}

/* long getLine(in long line, out AUTF8String text); */
NS_IMETHODIMP SciMoz::GetLine(PRInt32 line, nsACString & text, PRInt32  *_retval)
{
	SCIMOZ_CHECK_VALID("GetLine");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetLine\n");
#endif
	int lineLength = SendEditor(SCI_LINELENGTH, line, 0);
	char *buffer;
	if (!text.BeginWriting(&buffer, NULL, lineLength + 1))
		return NS_ERROR_OUT_OF_MEMORY;
	buffer[lineLength]=0;
	*_retval = SendEditor(SCI_GETLINE, line, reinterpret_cast<long>(buffer));
	NS_ASSERTION(buffer[lineLength] == NULL, "Buffer overflow");

	text.SetLength(*_retval);
	return NS_OK;
}

bool SciMoz::GetLine(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_OBJECT(args[1])) return false;

	int line = NPVARIANT_TO_INT32(args[0]);
	int lineLength = SendEditor(SCI_LINELENGTH, line, 0);
	char *buffer = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(lineLength + 1));
	if (!buffer) return false;
        buffer[lineLength] = 0;
	long actualLength = SendEditor(SCI_GETLINE, line,
				       reinterpret_cast<sptr_t>(buffer));
	NS_ASSERTION(buffer[lineLength] == NULL, "Buffer overflow");

	NPVariant textNp;
	STRINGN_TO_NPVARIANT(buffer, actualLength, textNp);
	bool success = NPN_SetProperty(mPlugin->GetNPP(),
				       NPVARIANT_TO_OBJECT(args[1]),
				       NPN_GetStringIdentifier("value"),
				       &textNp);
	if (!success) {
		NPN_ReleaseVariantValue(&textNp);
		return false;
	}

	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(actualLength, *result);
	return true;
}

/* void assignCmdKey (in long key, in long modifiers, in long msg); */
NS_IMETHODIMP SciMoz::AssignCmdKey(PRInt32 key, PRInt32 modifiers, PRInt32 msg) {
	SCIMOZ_CHECK_VALID("AssignCmdKey");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::AssignCmdKey key=%x modifiers=%x msg=%x\n", key, modifiers, msg);
#endif
	int km = LONGFROMTWOSHORTS(key, modifiers);
	SendEditor(SCI_ASSIGNCMDKEY, km, msg);
	return NS_OK;
}

bool SciMoz::AssignCmdKey(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 3) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_INT32(args[1])) return false;
	if (!NPVARIANT_IS_INT32(args[2])) return false;
	nsresult rv = AssignCmdKey(NPVARIANT_TO_INT32(args[0]),
				   NPVARIANT_TO_INT32(args[1]),
				   NPVARIANT_TO_INT32(args[2]));
	if (NS_FAILED(rv)) return false;
	return true;
}

/* void clearCmdKey (in long key, in long modifiers); */
NS_IMETHODIMP SciMoz::ClearCmdKey(PRInt32 key, PRInt32 modifiers) {
	SCIMOZ_CHECK_VALID("ClearCmdKey");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::ClearCmdKey key=%x modifiers=%x\n", key, modifiers);
#endif
	int km = LONGFROMTWOSHORTS(key, modifiers);
	SendEditor(SCI_CLEARCMDKEY, km, 0);
	return NS_OK;
}

bool SciMoz::ClearCmdKey(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_INT32(args[1])) return false;
	nsresult rv = ClearCmdKey(NPVARIANT_TO_INT32(args[0]),
				  NPVARIANT_TO_INT32(args[1]));
	if (NS_FAILED(rv)) return false;
	return true;
}

/* string getTextRange (in long min, in long max); */
NS_IMETHODIMP SciMoz::GetTextRange(PRInt32 min, PRInt32 max, nsAString & _retval) 
{
	SCIMOZ_CHECK_VALID("GetTextRange");
	// converting the string UTF8->UTF16->UTF8)
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetTextRange\n");
#endif
	if (max == -1)
		max = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
	PRInt32 length = max - min;
	if (length < 0 || min < 0 || max < 0) {
		return NS_ERROR_INVALID_ARG;
	}
	char *buffer = new char[length + 1];
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
	buffer[length]=0;
#ifdef USE_SCIN_DIRECT
	::GetTextRange(fnEditor, ptrEditor, min, max, buffer);
#else
	::GetTextRange(wEditor, min, max, buffer);
#endif
        NS_ASSERTION(buffer[length] == NULL, "Buffer overflow");

	_retval =  NS_ConvertUTF8toUTF16(buffer, length);

	delete []buffer;
	return NS_OK;
}

bool SciMoz::GetTextRange(const NPVariant *args, uint32_t argCount, NPVariant *result) {
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetTextRange\n");
#endif
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_INT32(args[1])) return false;
	int min = NPVARIANT_TO_INT32(args[0]);
	int max = NPVARIANT_TO_INT32(args[1]);
	if (max == -1)
		max = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
	int length = max - min;
	if (length < 0 || min < 0 || max < 0) {
		return false;
	}
	NPUTF8* buf = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(length + 1));
	if (!buf)
		return false;
	buf[length] = 0;
#ifdef USE_SCIN_DIRECT
	::GetTextRange(fnEditor, ptrEditor, min, max, buf);
#else
	::GetTextRange(wEditor, min, max, buf);
#endif
        NS_ASSERTION(buf[length] == 0, "Buffer overflow");

	NPN_ReleaseVariantValue(result);
	STRINGN_TO_NPVARIANT(buf, length, *result);
	return true;
}


/* attribute string name; */
NS_IMETHODIMP SciMoz::GetName(nsAString &val) {
	SCIMOZ_CHECK_VALID("GetName");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetName\n");
#endif
	val = name;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetName(const nsAString &val) {
	SCIMOZ_CHECK_VALID("SetName");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::SetName\n");
#endif
	name = val;
	return NS_OK;
}

/**
 * We override the modEventMask handling in order to workaround a
 * "scimoz.text" problem, where the scimoz text attribute does not
 * return the correct contents. The terminal-view's turn off the
 * modEventMask, which results in SciMoz not voiding the cached text it
 * holds - resulting in stale text. To work around this SciMoz overrides
 * this method and manually nulls the text when the eventmask is
 * changed. Bug 85194.
 */
NS_IMETHODIMP SciMoz::SetModEventMask(PRInt32 mask)
{
	SCIMOZ_CHECK_VALID("SetModEventMask");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::SetModEventMask\n");
#endif
	SendEditor(SCI_SETMODEVENTMASK, mask, 0);

	// Void the cached text - see bug 85194 for why.
    if (_textId >= 0x7FFF)
        _textId = 0; // Wrap around to start.
    _textId += 1;
	return NS_OK;
}

/* readonly attribute long textId; */
NS_IMETHODIMP SciMoz::GetTextId(int32_t *textId)
{
	SCIMOZ_CHECK_VALID("GetTextId");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetTextId\n");
#endif
    /**
     * Return a combination of a unique SciMoz id and a rolling text id.
     * This should give a unique text id (or close enough) for the life of
     * Komodo.
     * 
     * Caveats:
     *   1) if > 0x7FFF scintilla text changes, the _textId wraps around to 0.
     *   2) if > 0x7FFF plugins are created - then what the hell are you doing?
     */
	*textId = (_scimozId << 16) | _textId;
	return NS_OK;
}

/* attribute string text; */
/**
 * The text value is cached in this routine in order to avoid having to
 * regenerate the "text" property when the Scintilla buffer has not changed.
 * See bug 83216 for further details.
 */ 
NS_IMETHODIMP SciMoz::GetText(nsAString &text) 
{
	SCIMOZ_CHECK_VALID("GetText");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetText\n");
#endif
	GetTextRange(0, -1, text);
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetText(const nsAString &aText)
{
	SCIMOZ_CHECK_VALID("SetText");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::SetText\n");
#endif

	SendEditor(SCI_CLEARALL, 0, 0);
	nsCString convertedText = NS_ConvertUTF16toUTF8(aText);

	// To support null bytes, Komodo needs to use SCI_ADDTEXT instead of
	// the traditional SCI_SETTEXT call, as the add text method supports
	// the passing of a buffer length, whereas the set text call will
	// determine the buffer length using a "strlen" call, which does not
	// include any data after an embedded null.
	//SendEditor(SCI_SETTEXT, 0, reinterpret_cast<long>(convertedText.get()));
	// Bug 84654: SCI_ADDTEXT pushes currentPos and anchor to the end of
	// the text (withouth scrolling), so we need to correct their values.
	SendEditor(SCI_ADDTEXT, convertedText.Length(), reinterpret_cast<long>(convertedText.get()));
	SendEditor(SCI_SETCURRENTPOS, 0, 0);
	SendEditor(SCI_SETANCHOR, 0, 0);

	return NS_OK;
}

/* XXX copied from UniConversion.cxx in Scintilla */
unsigned int SciMozUCS2Length(const char *s, unsigned int len) {
	unsigned int ulen = 0;
	for (unsigned int i=0;i<len;i++) {
		unsigned char ch = static_cast<unsigned char>(s[i]);
		if ((ch < 0x80) || (ch > (0x80 + 0x40)))
			ulen++;
	}
	return ulen;
}

/* long charPosAtPosition(in long); */
NS_IMETHODIMP SciMoz::CharPosAtPosition(PRInt32 pos, PRInt32  *_retval)
{
	SCIMOZ_CHECK_VALID("CharPosAtPosition");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::CharPosAtPosition\n");
#endif
	if (pos < 0)
            pos = SendEditor(SCI_GETCURRENTPOS, 0, 0);
	long max = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
	size_t length = pos < max ? pos : max;
	char *buffer = new char[length + 1];
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
        buffer[length]=0;
#ifdef USE_SCIN_DIRECT
	::GetTextRange(fnEditor, ptrEditor, 0, length, buffer);
#else
	::GetTextRange(wEditor, 0, length, buffer);
#endif
        NS_ASSERTION(buffer[length] == NULL, "Buffer overflow");
        *_retval = SciMozUCS2Length(buffer, length);
	delete []buffer;
	return NS_OK;
}

bool SciMoz::CharPosAtPosition(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 1) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;

	PRInt32 retval;
	nsresult rv;
	rv = CharPosAtPosition(NPVARIANT_TO_INT32(args[0]), &retval);
	if (NS_FAILED(rv)) return false;

	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);

	return true;
}

/* readonly attribute wstring selText; */
NS_IMETHODIMP SciMoz::GetSelText(nsAString & aSelText)
{
	SCIMOZ_CHECK_VALID("GetSelText");
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::GetSelText\n");
#endif
	int min = SendEditor(SCI_GETSELECTIONSTART, 0, 0);
	int max = SendEditor(SCI_GETSELECTIONEND, 0, 0);
	return GetTextRange(min, max, aSelText);
}


/* void ButtonDown( in long x, in long y, in PRUint16 button, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonDown(PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt) {
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::ButtonDown\n");
#endif
	return _DoButtonUpDown(PR_FALSE, x, y, button, bShift, bCtrl, bAlt);
}

/* void ButtonUp( in long x, in long y, in PRUint16 button, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonUp(PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt) {
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr,"SciMoz::ButtonUp\n");
#endif
	return _DoButtonUpDown(PR_TRUE, x, y, button, bShift, bCtrl, bAlt);
}

/* void sendUpdateCommands( in AString commandset); */
NS_IMETHODIMP SciMoz::SendUpdateCommands(const char *commandset) {
    if (isClosed) {
        fprintf(stderr,"SciMoz::SendUpdateCommands '%s' used when closed!\n", commandset);
	return NS_ERROR_FAILURE;
    }
#ifdef SCIMOZ_DEBUG_VERBOSE
	fprintf(stderr, "SciMoz::SendUpdateCommands '%s'\n", commandset);
#endif
	void *handle = nullptr;
	nsCOMPtr<ISciMozEvents> eventSink;
	int mask = ISciMozEvents::SME_COMMANDUPDATE;
	while (nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
		eventSink->OnCommandUpdate(commandset);
	return NS_OK;
}

bool SciMoz::SendUpdateCommands(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 1) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	nsresult rv = SendUpdateCommands(NPVARIANT_TO_STRING(args[0]).UTF8Characters);
	return NS_SUCCEEDED(rv);
}

/* wchar getWCharAt(in long pos); */
NS_IMETHODIMP SciMoz::GetWCharAt(PRInt32 pos, PRUnichar *_retval) {
#ifdef SCIMOZ_DEBUG_VERBOSE
    fprintf(stderr,"SciMoz::GetWCharAt\n");
#endif
    /*
     * This assumes that Scintilla is using an utf-8 byte-addressed buffer.
     *
     * Return the character that is represented by the utf-8 sequence at
     * the requested position (we could be in the middle of the sequence).
     */
    int byte, byte2, byte3;

    /*
     * Unroll 1 to 3 byte UTF-8 sequences.  See reference data at:
     * http://www.cl.cam.ac.uk/~mgk25/unicode.html
     * http://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
     *
     * SendEditor must always be cast to return an unsigned char.
     */

    byte = (unsigned char) SendEditor(SCI_GETCHARAT, pos, 0);
    if (byte < 0x80) {
	/*
	 * Characters in the ASCII charset.
	 * Also treats \0 as a valid characters representing itself.
	 */

	*_retval = (PRUnichar) byte;
	return NS_OK;
    }

    while ((byte < 0xC0) && (byte >= 0x80) && (pos > 0)) {
	/*
	 * Naked trail byte.  We asked for an index in the middle of
	 * a UTF-8 char sequence.  Back up to the beginning.  We should
	 * end up with a start byte >= 0xC0 and <= 0xFD, but check against
	 * 0x80 still in case we have a screwy buffer.
	 *
	 * We could store bytes as we walk backwards, but this shouldn't
	 * be the common case.
	 */

	byte = (unsigned char) SendEditor(SCI_GETCHARAT, --pos, 0);
    }

    if (byte < 0xC0) {
	/*
	 * Handles properly formed UTF-8 characters between 0x01 and 0x7F.
	 * Also treats \0 and naked trail bytes 0x80 to 0xBF as valid
	 * characters representing themselves.
	 */
    } else if (byte < 0xE0) {
	byte2 = (unsigned char) SendEditor(SCI_GETCHARAT, pos+1, 0);
	if ((byte2 & 0xC0) == 0x80) {
	    /*
	     * Two-byte-character lead-byte followed by a trail-byte.
	     */

	    byte = (((byte & 0x1F) << 6) | (byte2 & 0x3F));
	}
	/*
	 * A two-byte-character lead-byte not followed by trail-byte
	 * represents itself.
	 */
    } else if (byte < 0xF0) {
	byte2 = (unsigned char) SendEditor(SCI_GETCHARAT, pos+1, 0);
	byte3 = (unsigned char) SendEditor(SCI_GETCHARAT, pos+2, 0);
	if (((byte2 & 0xC0) == 0x80) && ((byte3 & 0xC0) == 0x80)) {
	    /*
	     * Three-byte-character lead byte followed by two trail bytes.
	     */

	    byte = (((byte & 0x0F) << 12)
		    | ((byte2 & 0x3F) << 6) | (byte3 & 0x3F));
	}
	/*
	 * A three-byte-character lead-byte not followed by two trail-bytes
	 * represents itself.
	 */
    }
#if 0
    /*
     * Byte represents a 4-6 byte sequence.  The rest of Komodo currently
     * won't support this, which makes this code very hard to test.
     * Leave it commented out until we have better 4-6 byte UTF-8 support.
     */
    else {
	/*
	 * This is the general loop construct for building up Unicode
	 * from UTF-8, and could be used for 1-6 byte len sequences.
	 *
	 * The following structure is used for mapping current UTF-8 byte
	 * to number of bytes trail bytes.  It doesn't backtrack from
	 * the middle of a UTF-8 sequence.
	 */
	static const unsigned char totalBytes[256] = {
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
	    2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,
	    3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,6,6,6,6
	};
	int ch, trail;

	trail = totalBytes[byte] - 1; // expected number of trail bytes
	if (trail > 0) {
	    ch = byte & (0x3F >> trail);
	    do {
		byte2 = (unsigned char) SendEditor(SCI_GETCHARAT, ++pos, 0);
		if ((byte2 & 0xC0) != 0x80) {
		    *_retval = (PRUnichar) byte;
		    return NS_OK;
		}
		ch <<= 6;
		ch |= (byte2 & 0x3F);
		trail--;
	    } while (trail > 0);
	    *_retval = (PRUnichar) ch;
	    return NS_OK;
	}
    }
#endif

    *_retval = (PRUnichar) byte;
    return NS_OK;
}

bool SciMoz::GetWCharAt(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 1) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	PRUnichar retval[2];
	nsresult rv = GetWCharAt(NPVARIANT_TO_INT32(args[0]), retval);
	retval[1] = PRUnichar(0);
	if (NS_FAILED(rv)) return false;
	NS_ConvertUTF16toUTF8 retvalUtf8(retval);
	NPUTF8* buf = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(retvalUtf8.Length()));
	memcpy(buf, retvalUtf8.BeginReading(), retvalUtf8.Length());
	STRINGN_TO_NPVARIANT(buf, retvalUtf8.Length(), *result);
	return true;
}

/* void addChar(in PRUint32 ch); */
bool SciMoz::AddChar(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::AddChar\n");
	if (argCount != 1) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (!NPVARIANT_IS_INT32(args[0])) {
		SCIMOZ_DEBUG_PRINTF("%s: parameter is not int\n",
				    __FUNCTION__);
		return false;
	}
	nsresult rv = AddChar(NPVARIANT_TO_INT32(args[0]));
	return NS_SUCCEEDED(rv);
}

bool SciMoz::ButtonDown(const NPVariant *args, uint32_t argCount, NPVariant *result) {
        if (argCount != 6) return false;
        /* arg 0 of type long */
        if (!NPVARIANT_IS_INT32(args[0])) return false;
        /* arg 1 of type long */
        if (!NPVARIANT_IS_INT32(args[1])) return false;
        /* arg 2 of type PRUint16 */
        if (!NPVARIANT_IS_INT32(args[2])) return false;
        /* arg 3 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[3])) return false;
        /* arg 4 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[4])) return false;
        /* arg 5 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[5])) return false;
	nsresult rv = _DoButtonUpDown(PR_FALSE,
				      NPVARIANT_TO_INT32(args[0]),
				      NPVARIANT_TO_INT32(args[1]),
				      NPVARIANT_TO_INT32(args[2]),
				      !!NPVARIANT_TO_BOOLEAN(args[3]),
				      !!NPVARIANT_TO_BOOLEAN(args[4]),
				      !!NPVARIANT_TO_BOOLEAN(args[5]));
        /* return value of type void */
        NPN_ReleaseVariantValue(result);
	return NS_SUCCEEDED(rv);
}
bool SciMoz::ButtonUp(const NPVariant *args, uint32_t argCount, NPVariant *result) {
        if (argCount != 6) return false;
        /* arg 0 of type long */
        if (!NPVARIANT_IS_INT32(args[0])) return false;
        /* arg 1 of type long */
        if (!NPVARIANT_IS_INT32(args[1])) return false;
        /* arg 2 of type PRUint16 */
        if (!NPVARIANT_IS_INT32(args[2])) return false;
        /* arg 3 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[3])) return false;
        /* arg 4 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[4])) return false;
        /* arg 5 of type boolean */
        if (!NPVARIANT_IS_BOOLEAN(args[5])) return false;
	nsresult rv = _DoButtonUpDown(PR_TRUE,
				      NPVARIANT_TO_INT32(args[0]),
				      NPVARIANT_TO_INT32(args[1]),
				      NPVARIANT_TO_INT32(args[2]),
				      !!NPVARIANT_TO_BOOLEAN(args[3]),
				      !!NPVARIANT_TO_BOOLEAN(args[4]),
				      !!NPVARIANT_TO_BOOLEAN(args[5]));
        /* return value of type void */
        NPN_ReleaseVariantValue(result);
	return NS_SUCCEEDED(rv);
}
bool SciMoz::ButtonMove(const NPVariant *args, uint32_t argCount, NPVariant *result) {
        if (argCount != 2) return false;
        /* arg 0 of type long */
        if (!NPVARIANT_IS_INT32(args[0])) return false;
        /* arg 1 of type long */
        if (!NPVARIANT_IS_INT32(args[1])) return false;
	nsresult rv = ButtonMove(NPVARIANT_TO_INT32(args[0]),
				 NPVARIANT_TO_INT32(args[1]));
        /* return value of type void */
        NPN_ReleaseVariantValue(result);
	return NS_SUCCEEDED(rv);
}
bool SciMoz::EndDrop(const NPVariant * /*args*/, uint32_t argCount, NPVariant *result) {
        if (argCount != 0) return false;
	nsresult rv = EndDrop();
        /* return value of type void */
        NPN_ReleaseVariantValue(result);
	return NS_SUCCEEDED(rv);
}

bool SciMoz::AnnotationRemoveAtLine(const NPVariant * args, uint32_t argCount, NPVariant *result) {
	if (argCount != 1) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	AnnotationRemoveAtLine(NPVARIANT_TO_INT32(args[0]));
	return true;
}

NS_IMETHODIMP SciMoz::AnnotationRemoveAtLine(const int32_t lineNo) {
	SendEditor(SCI_ANNOTATIONSETTEXT, lineNo, NULL);
	return NS_OK;
}

NS_IMETHODIMP SciMoz::GetWordChars(nsACString& _retval) {
	size_t length = SendEditor(SCI_GETWORDCHARS, 0, 0);
	char *buf = _retval.BeginWriting(length);
	if (!buf) {
		return NS_ERROR_OUT_OF_MEMORY;
	}
	SendEditor(SCI_GETWORDCHARS, 0, reinterpret_cast<long>(buf));
	return NS_OK;
}
NS_IMETHODIMP SciMoz::SetWordChars(const nsACString& wordChars) {
	SendEditor(SCI_SETWORDCHARS,
	           0,
	           reinterpret_cast<long>(wordChars.BeginReading()));
	return NS_OK;
}
NS_IMETHODIMP SciMoz::SetWordChars_backCompat(const nsACString &wordChars) {
	return SetWordChars(wordChars);
}

/* void markerDefineRGBAImage(in long markerNumber, in AString pixels); */
NS_IMETHODIMP SciMoz::MarkerDefineRGBAImage(PRInt32 markerNumber, const nsAString & pixels) {
	SCIMOZ_CHECK_VALID("MarkerDefineRGBAImage");
        // Convert UTF-16 into 8-bit binary data.
	NS_LossyConvertUTF16toASCII pixels_8bit(pixels);
        SendEditor(SCI_MARKERDEFINERGBAIMAGE, markerNumber, (long)(pixels_8bit.get()));
	return NS_OK;
}
bool SciMoz::MarkerDefineRGBAImage(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_STRING(args[1])) return false;

        // Convert UTF-8 into UTF-16.
        NS_ConvertUTF8toUTF16 pixels_utf16(NPVARIANT_TO_STRING(args[1]).UTF8Characters,
					   NPVARIANT_TO_STRING(args[1]).UTF8Length);
	return NS_SUCCEEDED(MarkerDefineRGBAImage(NPVARIANT_TO_INT32(args[0]), pixels_utf16));
}

// ***********************************************************************
// *
// * Include interface implementation autogenerated from Scintilla.iface.
// *
// ***********************************************************************
#include "npscimoz_gen.h"

#include "generated_plugin_code.h"
