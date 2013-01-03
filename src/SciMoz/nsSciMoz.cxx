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

//#define SCIMOZ_DEBUG

/////////////////////////////////////////////////////
//
// This file implements the SciMoz object
// The native methods of this class are supposed to
// be callable from JavaScript
//

#include "nsSciMoz.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif
#ifdef XP_MACOSX
#ifdef XP_UNIX
#undef XP_UNIX
#endif
#endif

// XXX Mook hack to avoid including the internal string api
#define nsString_h___

// IME support
#include "nsIPrivateTextEvent.h"
#include "nsIPrivateTextRange.h"
#include "nsGUIEvent.h"
#if 0
#include "nsUnitConversion.h"
#include "nsIDeviceContext.h"
#endif
// -- IME support

#ifdef SCIMOZ_DEBUG
	#define SCIMOZ_DEBUG_PRINTF(...) fprintf(stderr, __VA_ARGS__)
#else
	#define SCIMOZ_DEBUG_PRINTF(...) do { } while (0)
#endif

#include "plugin.h"

NS_INTERFACE_MAP_BEGIN(SciMoz)
  NS_INTERFACE_MAP_ENTRY(nsIClassInfo)
  NS_INTERFACE_MAP_ENTRY(nsISupportsWeakReference)
  NS_INTERFACE_MAP_ENTRY_AMBIGUOUS(nsISupports, nsIClassInfo)
NS_INTERFACE_MAP_END



SciMoz::SciMoz(SciMozPluginInstance* aPlugin)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::SciMoz %p\n",aPlugin);
#endif

    SciMozInitNPIdentifiers();

    isClosed = 0;
    mPlugin = aPlugin;

    // XXX what do we need here?
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

#ifdef _WINDOWS
    LoadScintillaLibrary();
#endif
#if defined(XP_UNIX) && !defined(XP_MACOSX)
    sInGrab = 0;
#endif

    bracesStyle = 10;
    bracesCheck = true;
    bracesSloppy = true;

    // There is no cached text to start with.
    _cachedText.SetIsVoid(TRUE);

    PlatformNew();
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

// So we can debug reference issues we will implement our own addref/release
// but we could use the macros if we wanted to:

#ifndef SCIDEBUG_REFS
NS_IMPL_ADDREF(SciMoz)
NS_IMPL_RELEASE(SciMoz)
#else
NS_IMETHODIMP_(nsrefcnt) SciMoz::AddRef()
{
  ++mRefCnt;
  //fprintf(stderr, "SciMoz::AddRef %d %08X\n", mRefCnt.get(), this);
  return mRefCnt;
}

NS_IMETHODIMP_(nsrefcnt) SciMoz::Release()
{
  --mRefCnt;
  if (mPlugin == NULL) {
	fprintf(stderr, "SciMoz::Release %d plugin %p peer %p\n", mRefCnt.get(), mPlugin, this);
  }
  if (mRefCnt == 0) {
	fprintf(stderr, "deleting SciMoz, no refcount %p peer %p\n", mPlugin, this);
    delete this;
    return 0;
  }
  return mRefCnt;
}
#endif

long SciMoz::SendEditor(unsigned int Msg, unsigned long wParam, long lParam) {
    if (isClosed) {
	fprintf(stderr,"SciMoz::SendEditor %x %lx %lx used when closed!\n", Msg, wParam, lParam);
    }
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::SendEditor %x %lx %lx\n", Msg, wParam, lParam);
#endif
#if defined(_WINDOWS)
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
	SendEditor(SCI_SETLEXER, SCLEX_CPP);
	SendEditor(SCI_STYLECLEARALL);	// Copies global style to all others
	SendEditor(SCI_SETMOUSEDOWNCAPTURES, 0);
}

bool SciMoz::Init(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	if (argCount != 1) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (!NPVARIANT_IS_OBJECT(args[0])) {
		SCIMOZ_DEBUG_PRINTF("%s: arg is not an object\n", __FUNCTION__);
		return false;
	}
	if (!NPN_HasMethod(mPlugin->GetNPP(),
			   NPVARIANT_TO_OBJECT(args[0]),
			   NPN_GetStringIdentifier("abortComposing")))
	{
		SCIMOZ_DEBUG_PRINTF("%s: object has no abortComposing method\n",
				    __FUNCTION__);
		return false;
	}

	mIMEHelper = NPVARIANT_TO_OBJECT(args[0]);
	return true;
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

	if ((notification->nmhdr.code == SCN_PAINTED) && commandUpdateTarget) {
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

#ifdef SCIMOZ_DEBUG
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
				eventSink->OnUpdateUI();
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
				_cachedText.SetIsVoid(TRUE);
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
			mask = ISciMozEvents::SME_DWELLSTART;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDwellStart(notification->position, notification->x, notification->y);
			break;
		case SCN_DWELLEND:
			mask = ISciMozEvents::SME_DWELLEND;
			while ( nullptr != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDwellEnd(notification->position, notification->x, notification->y);
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
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::MarkClosed(const NPVariant * /*args*/, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::MarkClosed\n");
	if (argCount != 0) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 0 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (!isClosed) {
		// Disable ondwell handlers.
                SendEditor(SCI_SETMOUSEDWELLTIME, SC_TIME_FOREVER, 0);
		// Turn off all of the scintilla timers.
		SendEditor(SCI_STOPTIMERS, 0, 0);
		PlatformMarkClosed();
		isClosed = true;
	}
	return true;
}

/* void HookEvents (in nsISupports eventListener); */
NS_IMETHODIMP SciMoz::HookEvents(ISciMozEvents *eventListener) {
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::HookEvents(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::HookEvents\n");
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
	return listeners.Add(mPlugin->GetNPP(),
			     NPVARIANT_TO_OBJECT(eventListenerVar),
			     PR_FALSE,
			     ISciMozEvents::SME_ALL /*& ~ISciMozEvents::SME_PAINTED*/);
}

/* void UnhookEvents (in ISciMozEvents eventListener); */
NS_IMETHODIMP SciMoz::UnhookEvents(ISciMozEvents *eventListener) {
	SCIMOZ_CHECK_VALID("UnhookEvents");
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::UnhookEvents(const NPVariant *args, uint32_t argCount, NPVariant * /*result*/) {
	SCIMOZ_DEBUG_PRINTF("SciMoz::HookEvents\n");
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
	return listeners.Remove(mPlugin->GetNPP(),
			        NPVARIANT_TO_OBJECT(eventListenerVar));
}

/* void getStyledText (in long min, in long max, out unsigned long count, [array, size_is (count), retval] out octet str); */
NS_IMETHODIMP SciMoz::GetStyledText(PRInt32 min, PRInt32 max, PRUint32 *count, PRUint8 **str) {
	SCIMOZ_CHECK_VALID("GetStyledText");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetStyledText\n");
#endif
	size_t length = (max - min + 1) * 2;
	char *buffer = new char[length + 1];
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
        buffer[length] = 0;
#ifdef USE_SCIN_DIRECT
	long bytesCopied = GetStyledRange(fnEditor, ptrEditor, min, max, buffer);
#else
	long bytesCopied = GetStyledRange(wEditor, min, max, buffer);
#endif
        NS_ASSERTION(buffer[length] == NULL, "Buffer overflow");
	*str = reinterpret_cast<PRUint8*>(nsAllocator::Clone(buffer, bytesCopied));
	delete []buffer;
	*count = bytesCopied;
	return (*str) ? NS_OK : NS_ERROR_OUT_OF_MEMORY;
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
	NPObject *win = nullptr;
	NPError err = NPN_GetValue(mPlugin->GetNPP(), NPNVWindowNPObject, &win);
	if (err != NPERR_NO_ERROR) {
		SCIMOZ_DEBUG_PRINTF("%s: failed to get window\n",
				    __FUNCTION__);
		NS_Free(buf);
		return false;
	}
	NPString script = { "new Array()" };
	script.UTF8Length = strlen(script.UTF8Characters);
	if (!NPN_Evaluate(mPlugin->GetNPP(),
			  win,
			  &script,
			  result))
	{
		SCIMOZ_DEBUG_PRINTF("%s: failed to create array\n",
				    __FUNCTION__);
		NS_Free(buf);
		return false;
	}
	NPN_RetainObject(NPVARIANT_TO_OBJECT(*result));
	for (PRUint32 i = 0; i < count; ++i) {
		NPVariant v;
		INT32_TO_NPVARIANT(buf[i], v);
		NPN_SetProperty(mPlugin->GetNPP(),
				NPVARIANT_TO_OBJECT(*result),
				NPN_GetIntIdentifier(i),
				&v);
	}
	NS_Free(buf);
	NPN_ReleaseObject(NPVARIANT_TO_OBJECT(*result));
	return true;
}

/* long getCurLine (out string text); */
NS_IMETHODIMP SciMoz::GetCurLine(nsAString & text, PRInt32 *_retval) {
	SCIMOZ_CHECK_VALID("GetCurLine");
#ifdef SCIMOZ_DEBUG
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

	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	if (codePage == 0) {
	    text =  NS_ConvertASCIItoUTF16(buffer, lineLength);
	} else {
	    text =  NS_ConvertUTF8toUTF16(buffer, lineLength);
	}

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
NS_IMETHODIMP SciMoz::GetLine(PRInt32 line, nsAString & text, PRInt32  *_retval) 
{
	SCIMOZ_CHECK_VALID("GetLine");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetLine\n");
#endif
	int lineLength = SendEditor(SCI_LINELENGTH, line, 0);
	char *buffer = new char[lineLength + 1];
	if (!buffer)
		return NS_ERROR_OUT_OF_MEMORY;
        buffer[lineLength]=0;
	*_retval = SendEditor(SCI_GETLINE, line, reinterpret_cast<long>(buffer));
	NS_ASSERTION(buffer[lineLength] == NULL, "Buffer overflow");

	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	if (codePage == 0) {
	    text =  NS_ConvertASCIItoUTF16(buffer, lineLength);
	} else {
	    text =  NS_ConvertUTF8toUTF16(buffer, lineLength);
	}

	delete []buffer;
	return NS_OK;
}

bool SciMoz::GetLine(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_OBJECT(args[1])) return false;
	nsString text;
	PRInt32 retval;
	nsresult rv = GetLine(NPVARIANT_TO_INT32(args[0]),
			      text,
			      &retval);
	if (NS_FAILED(rv)) return false;

	NS_ConvertUTF16toUTF8 textUtf8(text);
	NPUTF8* buf = reinterpret_cast<NPUTF8*>(NPN_MemAlloc(textUtf8.Length()));
	if (!buf) return false;
	memcpy(buf, textUtf8.get(), textUtf8.Length());
	NPVariant textNp;
	STRINGN_TO_NPVARIANT(buf, textUtf8.Length(), textNp);
	bool success = NPN_SetProperty(mPlugin->GetNPP(),
				       NPVARIANT_TO_OBJECT(args[1]),
				       NPN_GetStringIdentifier("value"),
				       &textNp);
	if (!success) {
		NPN_ReleaseVariantValue(&textNp);
		return false;
	}

	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);
	return true;
}

/* void assignCmdKey (in long key, in long modifiers, in long msg); */
NS_IMETHODIMP SciMoz::AssignCmdKey(PRInt32 key, PRInt32 modifiers, PRInt32 msg) {
	SCIMOZ_CHECK_VALID("AssignCmdKey");
#ifdef SCIMOZ_DEBUG
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
#ifdef SCIMOZ_DEBUG
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
	// OBSOLETE; see the NPAPI version (which doesn't require excessively
	// converting the string UTF8->UTF16->UTF8)
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::GetTextRange(const NPVariant *args, uint32_t argCount, NPVariant *result) {
#ifdef SCIMOZ_DEBUG
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
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetName\n");
#endif
	val = name;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetName(const nsAString &val) {
	SCIMOZ_CHECK_VALID("SetName");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::SetName\n");
#endif
	name = val;
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
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetText\n");
#endif
	if (!_cachedText.IsVoid()) {
		text = _cachedText;
		return NS_OK;
	}
	size_t length = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
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

	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	if (codePage == 0) {
	    _cachedText = NS_ConvertASCIItoUTF16(buffer, length);
	} else {
	    _cachedText = NS_ConvertUTF8toUTF16(buffer, length);
	}
	delete []buffer;
	text = _cachedText;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetText(const nsAString &aText)
{
	SCIMOZ_CHECK_VALID("SetText");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::SetText\n");
#endif

	SendEditor(SCI_CLEARALL, 0, 0);
 	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	nsCString convertedText;
 	if (codePage == 0) {
	    convertedText = NS_LossyConvertUTF16toASCII(aText);
 	} else {
	    convertedText = NS_ConvertUTF16toUTF8(aText);
 	}

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
#ifdef SCIMOZ_DEBUG
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
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetSelText\n");
#endif
	int min = SendEditor(SCI_GETSELECTIONSTART, 0, 0);
	int max = SendEditor(SCI_GETSELECTIONEND, 0, 0);
	size_t length = max - min;
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

	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	if (codePage == 0) {
	    aSelText =  NS_ConvertASCIItoUTF16(buffer, length);
	} else {
	    aSelText =  NS_ConvertUTF8toUTF16(buffer, length);
	}

	delete []buffer;
	return NS_OK;
}


/* void ButtonDown( in long x, in long y, in PRUint16 button, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonDown(PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::ButtonDown\n");
#endif
	return _DoButtonUpDown(PR_FALSE, x, y, button, bShift, bCtrl, bAlt);
}

/* void ButtonUp( in long x, in long y, in PRUint16 button, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonUp(PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::ButtonUp\n");
#endif
	return _DoButtonUpDown(PR_TRUE, x, y, button, bShift, bCtrl, bAlt);
}


/* void setCommandUpdateTarget( in nsISupports window); */
NS_IMETHODIMP SciMoz::SetCommandUpdateTarget(nsISupports * /*window*/) {
	return NS_ERROR_NOT_IMPLEMENTED;
}

bool SciMoz::SetCommandUpdateTarget(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 1) {
		SCIMOZ_DEBUG_PRINTF("%s: expected 1 argument, got %i\n",
				    __FUNCTION__,
				    argCount);
		return false;
	}
	if (NPVARIANT_IS_VOID(args[0]) || NPVARIANT_IS_NULL(args[0])) {
		commandUpdateTarget = 0;
		return true;
	}
	if (!NPVARIANT_IS_OBJECT(args[0])) {
		SCIMOZ_DEBUG_PRINTF("%s: arg is not an object\n", __FUNCTION__);
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
	NPString script = { "Components.interfaces.nsIDOMWindow" };
	script.UTF8Length = strlen(script.UTF8Characters);
	NPVariant iid = { NPVariantType_Void };
	if (!NPN_Evaluate(mPlugin->GetNPP(),
			  NPVARIANT_TO_OBJECT(args[0]),
			  &script,
			  &iid))
	{
		SCIMOZ_DEBUG_PRINTF("%s: failed to get nsIDOMWindow\n",
				    __FUNCTION__);
		return false;
	}

	NPVariant domWindowInternal;
	if (!NPN_Invoke(mPlugin->GetNPP(),
			NPVARIANT_TO_OBJECT(args[0]),
			NPN_GetStringIdentifier("QueryInterface"),
			&iid,
			1,
			&domWindowInternal))
	{
		SCIMOZ_DEBUG_PRINTF("%s: QI failed\n", __FUNCTION__);
		return false;
	}

	// sanity check the nsIDOMWindowInternal we got
	if (!NPN_HasMethod(mPlugin->GetNPP(),
			   NPVARIANT_TO_OBJECT(domWindowInternal),
			   NPN_GetStringIdentifier("updateCommands")))
	{
		SCIMOZ_DEBUG_PRINTF("%s: nsIDOMWindowInternal does not have an updateCommands method!\n",
				    __FUNCTION__);
		return false;
	}
	commandUpdateTarget = NPVARIANT_TO_OBJECT(domWindowInternal);

	return true;
}

/* void sendUpdateCommands( in string text); */
NS_IMETHODIMP SciMoz::SendUpdateCommands(const char *text) {
	NS_ABORT_IF_FALSE(commandUpdateTarget != nullptr,
			  "Can't send a command update if you havent set the target!");
	if (commandUpdateTarget==nullptr)
		return NS_ERROR_UNEXPECTED;

	NPVariant result = { NPVariantType_Void };
	NPVariant varText;
	STRINGZ_TO_NPVARIANT(text, varText);
	bool success = NPN_Invoke(mPlugin->GetNPP(),
				  commandUpdateTarget,
				  NPN_GetStringIdentifier("updateCommands"),
				  &varText,
				  1,
				  &result);
	return success ? NS_OK : NS_ERROR_FAILURE;
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

NS_IMETHODIMP SciMoz::HandleTextEvent(nsIDOMEvent* /*aTextEvent*/, nsIBoxObject * /*aBoxObject*/, nsAString & /*text*/)
{
	return NS_ERROR_NOT_IMPLEMENTED;
}

/* wchar getWCharAt(in long pos); */
NS_IMETHODIMP SciMoz::GetWCharAt(PRInt32 pos, PRUnichar *_retval) {
#ifdef SCIMOZ_DEBUG
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

NS_IMETHODIMP SciMoz::ConvertUTF16StringSendMessage(int message, PRInt32 length, const PRUnichar *text, PRInt32  *_retval) {
	nsCAutoString utf8Text;
	if (length == -1) {
		utf8Text = NS_ConvertUTF16toUTF8(text);
	} else {
		utf8Text = NS_ConvertUTF16toUTF8(text, length);
	}
	*_retval = SendEditor(message, utf8Text.Length(), reinterpret_cast<long>(utf8Text.get()));
	return NS_OK;
}

/* long replaceTarget(in long length, in wstring text); */
NS_IMETHODIMP SciMoz::ReplaceTarget(PRInt32 length, const PRUnichar *text, PRInt32  *_retval) {
#ifdef SCIMOZ_DEBUG
	printf("SciMoz::ReplaceTarget\n");
#endif
	return ConvertUTF16StringSendMessage(SCI_REPLACETARGET, length, text, _retval);
}

bool SciMoz::ReplaceTarget(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_STRING(args[1])) return false;

	NS_ConvertUTF8toUTF16 textUtf16(NPVARIANT_TO_STRING(args[1]).UTF8Characters,
					NPVARIANT_TO_STRING(args[1]).UTF8Length);
	PRInt32 retval;
	nsresult rv;
	rv = ReplaceTarget(NPVARIANT_TO_INT32(args[0]), textUtf16.get(), &retval);
	if (NS_FAILED(rv)) return false;
	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);
	return true;
}

/* long replaceTargetRE(in long length, in wstring text); */
NS_IMETHODIMP SciMoz::ReplaceTargetRE(PRInt32 length, const PRUnichar *text, PRInt32  *_retval) {
#ifdef SCIMOZ_DEBUG
	printf("SciMoz::ReplaceTargetRE\n");
#endif
	return ConvertUTF16StringSendMessage(SCI_REPLACETARGETRE, length, text, _retval);
}

bool SciMoz::ReplaceTargetRE(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_STRING(args[1])) return false;

	NS_ConvertUTF8toUTF16 textUtf16(NPVARIANT_TO_STRING(args[1]).UTF8Characters,
					NPVARIANT_TO_STRING(args[1]).UTF8Length);
	PRInt32 retval;
	nsresult rv;
	rv = ReplaceTargetRE(NPVARIANT_TO_INT32(args[0]), textUtf16.get(), &retval);
	if (NS_FAILED(rv)) return false;
	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);
	return true;
}

/* long searchInTarget(in long length, in wstring text); */
NS_IMETHODIMP SciMoz::SearchInTarget(PRInt32 length, const PRUnichar *text, PRInt32  *_retval) {
#ifdef SCIMOZ_DEBUG
	printf("SciMoz::SearchInTarget\n");
#endif
	return ConvertUTF16StringSendMessage(SCI_SEARCHINTARGET, length, text, _retval);
}

bool SciMoz::SearchInTarget(const NPVariant *args, uint32_t argCount, NPVariant *result) {
	if (argCount != 2) return false;
	if (!NPVARIANT_IS_INT32(args[0])) return false;
	if (!NPVARIANT_IS_STRING(args[1])) return false;

	NS_ConvertUTF8toUTF16 textUtf16(NPVARIANT_TO_STRING(args[1]).UTF8Characters,
					NPVARIANT_TO_STRING(args[1]).UTF8Length);
	PRInt32 retval;
	nsresult rv;
	rv = SearchInTarget(NPVARIANT_TO_INT32(args[0]), textUtf16.get(), &retval);
	if (NS_FAILED(rv)) return false;
	NPN_ReleaseVariantValue(result);
	INT32_TO_NPVARIANT(retval, *result);
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

/*****
 * Not used - XPCOM-style stubs for methods implemented at the NPAPI layer
 *****/
NS_IMETHODIMP SciMoz::GetWordChars(nsACString&) {
	return NS_ERROR_NOT_IMPLEMENTED;
}
NS_IMETHODIMP SciMoz::SetWordChars(const nsACString&) {
	return NS_ERROR_NOT_IMPLEMENTED;
}
NS_IMETHODIMP SciMoz::SetWordChars_backCompat(const nsACString &) {
	return NS_ERROR_NOT_IMPLEMENTED;
}

// ***********************************************************************
// *
// * Include interface implementation autogenerated from Scintilla.iface.
// *
// ***********************************************************************
#include "npscimoz_gen.h"

#include "generated_plugin_code.h"
