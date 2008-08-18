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

// We can enable the timeline for scimoz separately from the rest of Moz
// But for now it is enabled (assuming timeline is!)
// This will get undefined if MOZ_TIMELINE is not defined.
#define SCIMOZ_TIMELINE

/////////////////////////////////////////////////////
//
// This file implements the SciMoz object
// The native methods of this class are supposed to
// be callable from JavaScript
//
#include "plugin.h"
#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif
#ifdef XP_MACOSX
#ifdef XP_UNIX
#undef XP_UNIX
#endif
#endif


/* XXX TODO make thread checks default in dev builds, off in release */
#if 0
#if MOZ_VERSION < 190
/* mozilla 1.8 */
#include "nsIThread.h"
#define IS_MAIN_THREAD() nsIThread::IsMainThread()
#else
/* mozilla 1.9 */
#include "nsThreadUtils.h"
#define IS_MAIN_THREAD() NS_IsMainThread()
#endif
#define SCIMOZ_CHECK_THREAD(a) \
    if (!IS_MAIN_THREAD()) { \
	fprintf(stderr, "SciMoz::" a " was called on a thread\n"); \
	return NS_ERROR_FAILURE; \
    }
#else
#define SCIMOZ_CHECK_THREAD(a)
#endif

// IME support
#include "nsIPrivateTextEvent.h"
#include "nsIPrivateTextRange.h"
#include "nsGUIEvent.h"
#if 0
#include "nsUnitConversion.h"
#include "nsIDeviceContext.h"
#endif
#include "nsGfxCIID.h"
static NS_DEFINE_IID(kDeviceContextIID, NS_DEVICE_CONTEXT_CID);
// -- IME support

static NS_DEFINE_IID(kISciMozIID, ISCIMOZ_IID);
static NS_DEFINE_IID(kISciMozLiteIID, ISCIMOZLITE_IID);
static NS_DEFINE_IID(kIClassInfoIID, NS_ICLASSINFO_IID);
static NS_DEFINE_IID(kISupportsIID, NS_ISUPPORTS_IID);
static NS_DEFINE_IID(kISupportsWeakReferenceIID, NS_ISUPPORTSWEAKREFERENCE_IID);

#ifdef SCIMOZ_TIMELINE
#include "prenv.h" // run time enable of logging.
static int gTimelineEnabled = -1;
#endif


NS_INTERFACE_MAP_BEGIN(SciMoz)
  NS_INTERFACE_MAP_ENTRY(ISciMoz)
  NS_INTERFACE_MAP_ENTRY(ISciMozLite)
  NS_INTERFACE_MAP_ENTRY(nsIClassInfo)
  NS_INTERFACE_MAP_ENTRY(nsISupportsWeakReference)
  NS_INTERFACE_MAP_ENTRY_AMBIGUOUS(nsISupports, ISciMoz)
NS_INTERFACE_MAP_END



SciMoz::SciMoz(nsPluginInstance* aPlugin)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::SciMoz %p\n",aPlugin);
#endif
#ifdef SCIMOZ_TIMELINE
    if (gTimelineEnabled==-1) {
        gTimelineEnabled = PR_GetEnv("KO_TIMELINE_SCIMOZ") != nsnull;
        if (!gTimelineEnabled)
            SCIMOZ_TIMELINE_MARK("SciMoz initializing, but not logging timeline entries (KO_TIMELINE_SCIMOZ not set)");
        NS_ABORT_IF_FALSE(gTimelineEnabled!=-1, "We just set it!");
    }
#endif

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
    _lastCharCodeAdded = 0;

    bracesStyle = 10;
    bracesCheck = true;
    bracesSloppy = true;

    imeStartPos = -1;
    imeComposing = false;
    imeActive = false;
    
    PlatformNew();
}

SciMoz::~SciMoz()
{
#ifdef SCIDEBUG_REFS
    fprintf(stderr,"SciMoz::~SciMoz %p\n", this);
#endif
    PlatformDestroy(); // Perform platform specific cleanup
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

void SciMoz::SetInstance(nsPluginInstance* plugin)
{
  mPlugin = plugin;
  if (plugin == NULL) {
    PlatformResetWindow();
  }
}

long SciMoz::SendEditor(unsigned int Msg, unsigned long wParam, long lParam) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::SendEditor %lx %lx %lx\n", Msg, wParam, lParam);
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
	int bracesStyleCheck = bracesStyle;
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
	SCIMOZ_CHECK_THREAD("DoBraceMatch");
	BraceMatch();
	return NS_OK;
}

#define FAST_CODE
//#define SCIMOZ_DEBUG_NOTIFY
void SciMoz::Notify(long lParam) {
	SCNotification *notification = reinterpret_cast<SCNotification *>(lParam);
#ifdef SCIMOZ_DEBUG
	if (notification->nmhdr.code != SCN_PAINTED)
		fprintf(stderr,"SciMoz::Notify %d\n", notification->nmhdr.code);
#endif
	if (commandUpdateTarget) {
		switch (notification->nmhdr.code) {
		case SCN_PAINTED:
			PRBool bCanUndoNow, bCanRedoNow;
			CanUndo(&bCanUndoNow);
			CanRedo(&bCanRedoNow);
			if (bCouldUndoLastTime != bCanUndoNow ||
			    bCouldRedoLastTime != bCanRedoNow) {
#ifdef SCIMOZ_DEBUG_NOTIFY
				fprintf(stderr,"Scintilla sending 'undo' event\n");
#endif
				commandUpdateTarget->UpdateCommands(
					NS_ConvertASCIItoUTF16("undo"));
				bCouldUndoLastTime = bCanUndoNow;
				bCouldRedoLastTime = bCanRedoNow;
			}
			break;
		default:
			break;
		}
	}
	PRUint32 mask;
	void *handle = nsnull;
	nsCOMPtr<ISciMozEvents> eventSink;
	switch (notification->nmhdr.code) {
		/*
		case SCN_STYLENEEDED:
			mask = ISciMozEvents::SME_STYLENEEDED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnStyleNeeded(notification->position);
			break;
		*/
		case SCN_CHARADDED:
#ifdef FAST_CODE
			_lastCharCodeAdded = notification->ch;
#else
			mask = ISciMozEvents::SME_CHARADDED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnCharAdded(notification->ch);
#endif
			break;
		case SCN_SAVEPOINTREACHED:
			mask = ISciMozEvents::SME_SAVEPOINTREACHED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnSavePointReached();
			break;
		case SCN_SAVEPOINTLEFT:
			mask = ISciMozEvents::SME_SAVEPOINTLEFT;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnSavePointLeft();
			break;
		/*
		case SCN_MODIFYATTEMPTRO:
			mask = ISciMozEvents::SME_MODIFYATTEMPTRO;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnModifyAttemptRO();
			break;
		case SCN_KEY:
			mask = ISciMozEvents::SME_KEY;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnKey(notification->ch, notification->modifiers);
			break;
		*/
		case SCN_DWELLSTART:
			mask = ISciMozEvents::SME_DWELLSTART;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDwellStart(notification->position, notification->x, notification->y);
			break;
		case SCN_DWELLEND:
			mask = ISciMozEvents::SME_DWELLEND;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDwellEnd(notification->position, notification->x, notification->y);
			break;
		case SCN_DOUBLECLICK:
			mask = ISciMozEvents::SME_DOUBLECLICK;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnDoubleClick();
			break;
		case SCN_UPDATEUI:
#if 0
			if (!_lastCharCodeAdded || IsBrace(_lastCharCodeAdded)) {
				BraceMatch();
			} else if (SendEditor(SCI_GETHIGHLIGHTGUIDE, 0) >= 0) {
				SendEditor(SCI_SETHIGHLIGHTGUIDE, 0, 0);
				SendEditor(SCI_BRACEHIGHLIGHT, 0, 0);
			}
#endif
			mask = ISciMozEvents::SME_UPDATEUI;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnUpdateUI();
			break;
		case SCN_MODIFIED: {
			// perf modification, do some early checks to see if
			// we really want to call into js
#ifdef FAST_CODE
			// if we are deleting or inserting on a fold, expand
			// the fold first
			if (notification->modificationType & (SC_MOD_BEFOREDELETE | SC_MOD_BEFOREINSERT))
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
				// dont go on
				break;
			}
			if (!(notification->modificationType & (SC_MOD_INSERTTEXT | SC_MOD_DELETETEXT))) {
				// we currently only want these events, break otherwise
				//fprintf(stderr ,"bail on calling onModified\n");
				break;
			}
#endif
			// Silly js doesnt like NULL strings here :-(
			PRUint32 len = notification->text ? notification->length : 0;
			//XXX Would like to use the commented out code (as was done
			//    in Change 73289), but this causes
			//    <http://bugs.activestate.com/show_bug.cgi?id=26793>
			//    so we will not convert the UTF-8 encoded text to
			//    unicode. Note that this places the burden of
			//    conversion, if necessary, on the listeners of
			//    OnModified() (see views-buffer.xml).
			//const char *pText = len ? notification->text : "";
			//PRUnichar *text =  ToNewUnicode(NS_ConvertUTF8toUTF16(pText));
			const char *text = len ? notification->text : "";
			mask = ISciMozEvents::SME_MODIFIED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnModified(notification->position,
				                      notification->modificationType, text,
				                      len, notification->linesAdded,
				                      notification->line, notification->foldLevelNow,
					                  notification->foldLevelPrev);
			//nsMemory::Free((void*)text);
			}
			break;
		/*
		case SCN_MACRORECORD:
			mask = ISciMozEvents::SME_MACRORECORD;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnMacroRecord(
				    notification->message, notification->wParam, notification->lParam);
			break;
		*/
		case SCN_MARGINCLICK:
			mask = ISciMozEvents::SME_MARGINCLICK;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnMarginClick(
					notification->modifiers, notification->position, notification->margin);
			break;
		/*
		case SCN_NEEDSHOWN:
			mask = ISciMozEvents::SME_NEEDSHOWN;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnNeedShown(notification->position, notification->length);
			break;
		*/
		case SCN_POSCHANGED:
#ifndef FAST_CODE
			mask = ISciMozEvents::SME_POSCHANGED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnPosChanged(notification->position);
#endif
			break;
		/*
		case SCN_PAINTED:
			// No need to waste time with an event for this ATM.
			mask = ISciMozEvents::SME_PAINTED;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnPainted();
			break;
		*/
		case SCN_ZOOM:
			mask = ISciMozEvents::SME_ZOOM;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnZoom();
			break;
		case SCN_HOTSPOTDOUBLECLICK:
			mask = ISciMozEvents::SME_HOTSPOTDOUBLECLICK;
			while ( nsnull != (handle = listeners.GetNext(mask, handle, getter_AddRefs(eventSink))))
				eventSink->OnHotSpotDoubleClick(notification->position, notification->modifiers);
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





/* void HookEvents (in nsISupports eventListener); */
NS_IMETHODIMP SciMoz::HookEvents(ISciMozEvents *eventListener) {
	SCIMOZ_CHECK_THREAD("HookEvents");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::HookEvents\n");
#endif
	if (eventListener==nsnull)
		return NS_ERROR_UNEXPECTED;
	return listeners.Add(eventListener, PR_TRUE, ISciMozEvents::SME_ALL /*& ~ISciMozEvents::SME_PAINTED*/);
}

/* void HookEvents (in nsISupports eventListener); */
NS_IMETHODIMP SciMoz::HookEventsWithStrongReference(ISciMozEvents *eventListener) {
	SCIMOZ_CHECK_THREAD("HookEventsWithStrongReference");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::HookEventsWithStrongReference\n");
#endif
	if (eventListener==nsnull)
		return NS_ERROR_UNEXPECTED;
	return listeners.Add(eventListener, PR_FALSE, ISciMozEvents::SME_ALL /*& ~ISciMozEvents::SME_PAINTED*/);
}

/* void HookSomeEvents (in nsISupports eventListener, in PRUint32 mask); */
NS_IMETHODIMP SciMoz::HookSomeEvents(ISciMozEvents *eventListener, PRUint32 mask) {
	SCIMOZ_CHECK_THREAD("HookSomeEvents");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::HookSomeEvents\n");
#endif
	if (eventListener==nsnull)
		return NS_ERROR_UNEXPECTED;
	return listeners.Add(eventListener, PR_TRUE, mask);
}

/* void HookSomeEventsWithStrongReference (in nsISupports eventListener, in PRUint32 mask); */
NS_IMETHODIMP SciMoz::HookSomeEventsWithStrongReference(ISciMozEvents *eventListener, PRUint32 mask) {
	SCIMOZ_CHECK_THREAD("HookSomeEventsWithStrongReference");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::HookSomeEventsWithStrongReference %08X\n", eventListener);
#endif
	if (eventListener==nsnull)
		return NS_ERROR_UNEXPECTED;
	return listeners.Add(eventListener, PR_FALSE, mask);
}

/* void UnhookEvents (in nsISupports eventListener); */
NS_IMETHODIMP SciMoz::UnhookEvents(ISciMozEvents *eventListener) {
	SCIMOZ_CHECK_THREAD("UnhookEvents");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::UnhookEvents\n");
#endif
	if (eventListener==nsnull)
		return NS_ERROR_UNEXPECTED;
	return listeners.Remove(eventListener);
}

/* void getStyledText (in long min, in long max, out unsigned long count, [array, size_is (count), retval] out octet str); */
NS_IMETHODIMP SciMoz::GetStyledText(PRInt32 min, PRInt32 max, PRUint32 *count, PRUint8 **str) {
	SCIMOZ_CHECK_THREAD("GetStyledText");
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

/* long getCurLine (out string text); */
NS_IMETHODIMP SciMoz::GetCurLine(PRUnichar ** text, PRInt32 *_retval) {
	SCIMOZ_CHECK_THREAD("GetCurLine");
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
	    *text =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
	} else {
	    *text =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
	}

	delete []buffer;
	return NS_OK;
}

/* long getLine(in long line, out AUTF8String text); */
NS_IMETHODIMP SciMoz::GetLine(PRInt32 line, PRUnichar ** text, PRInt32  *_retval) 
{
	SCIMOZ_CHECK_THREAD("GetLine");
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
	    *text =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
	} else {
	    *text =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
	}

	delete []buffer;
	return NS_OK;
}

/* void assignCmdKey (in long key, in long modifiers, in long msg); */
NS_IMETHODIMP SciMoz::AssignCmdKey(PRInt32 key, PRInt32 modifiers, PRInt32 msg) {
	SCIMOZ_CHECK_THREAD("AssignCmdKey");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::AssignCmdKey key=%x modifiers=%x msg=%x\n", key, modifiers, msg);
#endif
	int km = LONGFROMTWOSHORTS(key, modifiers);
	SendEditor(SCI_ASSIGNCMDKEY, km, msg);
	return NS_OK;
}

/* void clearCmdKey (in long key, in long modifiers); */
NS_IMETHODIMP SciMoz::ClearCmdKey(PRInt32 key, PRInt32 modifiers) {
	SCIMOZ_CHECK_THREAD("ClearCmdKey");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::ClearCmdKey key=%x modifiers=%x\n", key, modifiers);
#endif
	int km = LONGFROMTWOSHORTS(key, modifiers);
	SendEditor(SCI_CLEARCMDKEY, km, 0);
	return NS_OK;
}

/* string getTextRange (in long min, in long max); */
NS_IMETHODIMP SciMoz::GetTextRange(PRInt32 min, PRInt32 max, PRUnichar ** _retval) 
{
	SCIMOZ_CHECK_THREAD("GetTextRange");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetTextRange\n");
#endif
	if (max == -1)
		max = SendEditor(SCI_GETTEXTLENGTH, 0, 0);
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
	    *_retval =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
	} else {
	    *_retval =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
	}

	delete []buffer;
	return NS_OK;
}

/* attribute string name; */
NS_IMETHODIMP SciMoz::GetName(nsAString &val) {
	SCIMOZ_CHECK_THREAD("GetName");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetName\n");
#endif
	val = name;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetName(const nsAString &val) {
	SCIMOZ_CHECK_THREAD("SetName");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::SetName\n");
#endif
	name = val;
	return NS_OK;
}

/* attribute string text; */
NS_IMETHODIMP SciMoz::GetText(PRUnichar ** text) 
{
	SCIMOZ_CHECK_THREAD("GetText");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::GetText\n");
#endif
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
	    *text =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
	} else {
	    *text =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
	}

	delete []buffer;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetText(const PRUnichar * aText)
{
	SCIMOZ_CHECK_THREAD("SetText");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::SetText\n");
#endif

	int codePage = SendEditor(SCI_GETCODEPAGE, 0, 0);
	if (codePage == 0) {
	    SendEditor(SCI_SETTEXT, 0, reinterpret_cast<long>(NS_LossyConvertUTF16toASCII(aText).get()));
	} else {
	    SendEditor(SCI_SETTEXT, 0, reinterpret_cast<long>(NS_ConvertUTF16toUTF8(aText).get()));
	}

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

/* attribute long lastCharCodeAdded; */
NS_IMETHODIMP SciMoz::GetLastCharCodeAdded(PRInt32  *_retval)
{
	*_retval = _lastCharCodeAdded;
	return NS_OK;
}

NS_IMETHODIMP SciMoz::SetLastCharCodeAdded(PRInt32  charcode)
{
	_lastCharCodeAdded = charcode;
	return NS_OK;
}

/* long charPosAtPosition(in long); */
NS_IMETHODIMP SciMoz::CharPosAtPosition(PRInt32 pos, PRInt32  *_retval)
{
	SCIMOZ_CHECK_THREAD("CharPosAtPosition");
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

/* readonly attribute wstring selText; */
NS_IMETHODIMP SciMoz::GetSelText(PRUnichar ** aSelText)
{
	SCIMOZ_CHECK_THREAD("GetSelText");
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
	    *aSelText =  ToNewUnicode(NS_ConvertASCIItoUTF16(buffer));
	} else {
	    *aSelText =  ToNewUnicode(NS_ConvertUTF8toUTF16(buffer));
	}

	delete []buffer;
	return NS_OK;
}


/* void ButtonDown( in long x, in long y, in PRUint16 button, in PRUint64 timeStamp, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonDown(PRInt32 x, PRInt32 y, PRUint16 button, PRUint64 timeStamp, PRBool bShift, PRBool bCtrl, PRBool bAlt) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::ButtonDown\n");
#endif
	return _DoButtonUpDown(PR_FALSE, x, y, button, timeStamp, bShift, bCtrl, bAlt);
}

/* void ButtonUp( in long x, in long y, in PRUint16 button, in PRUint64 timeStamp, in boolean bShift, boolean bCtrl, boolean bAlt); */
NS_IMETHODIMP SciMoz::ButtonUp(PRInt32 x, PRInt32 y, PRUint16 button, PRUint64 timeStamp, PRBool bShift, PRBool bCtrl, PRBool bAlt) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::ButtonUp\n");
#endif
	return _DoButtonUpDown(PR_TRUE, x, y, button, timeStamp, bShift, bCtrl, bAlt);
}


/* void setCommandUpdateTarget( in nsISupports window); */
NS_IMETHODIMP SciMoz::SetCommandUpdateTarget(nsISupports *window) {
	if (window==nsnull) {
		commandUpdateTarget = 0; // wipe and release it.
		return NS_OK;
	}
	else
		return window->QueryInterface(NS_GET_IID(nsIDOMWindowInternal),
	                              getter_AddRefs(commandUpdateTarget));
}

/* void sendUpdateCommands( in string text); */
NS_IMETHODIMP SciMoz::SendUpdateCommands(const char *text) {
	NS_ABORT_IF_FALSE(commandUpdateTarget!=nsnull, "Can't send a command update if you havent set the target!");
	if (commandUpdateTarget==nsnull)
		return NS_ERROR_UNEXPECTED;
	return commandUpdateTarget->UpdateCommands(NS_ConvertASCIItoUTF16(text));
}

//#define IME_DEBUG
void SciMoz::StartCompositing()
{
#ifdef IME_DEBUG
	fprintf(stderr, "SciMoz::StartCompositing\n");
#endif
	if (imeStartPos < 0) {
		BeginUndoAction();
		int anchor = SendEditor(SCI_GETANCHOR, 0, 0);
		imeStartPos = SendEditor(SCI_GETCURRENTPOS, 0, 0);
		if (anchor < imeStartPos)
			imeStartPos = anchor;
		imeActive = true;
	}
}

void SciMoz::EndCompositing()
{
#ifdef IME_DEBUG
	fprintf(stderr, "SciMoz::EndCompositing\n");
#endif
	if (imeStartPos >= 0) {
		imeStartPos = -1;
		EndUndoAction();
	}
	if (imeComposing) {
		// blur event, mouse click or other during composition, undo
		// the composition now
		PRBool collectUndo;
		GetUndoCollection(&collectUndo);
		SetUndoCollection(false);
		Undo();
		SetUndoCollection(collectUndo);
		imeComposing = false;
		mIMEString.Truncate();
	}
	imeActive = false;
}

NS_IMETHODIMP SciMoz::HandleTextEvent(nsIDOMEvent* aTextEvent, PRUnichar ** text)
{
	// This is called multiple times in the middle of an 
	// IME composition
	nsCOMPtr<nsIPrivateTextEvent> textEvent(do_QueryInterface(aTextEvent));
	if (!textEvent)
	  return NS_OK;
	
	textEvent->GetText(mIMEString);
	*text =  ToNewUnicode(mIMEString);
	
#if 1
	// this tells mozilla where to place IME input windows
	nsTextEventReply *textEventReply;
	textEvent->GetEventReply(&textEventReply);
	int curPos = SendEditor(SCI_GETCURRENTPOS, 0, 0);
	int curLine = SendEditor(SCI_LINEFROMPOSITION, curPos);
#if 0
	// XXX device dependant!!!!  bug 40959
	// see xpcom/ds/nsUnitConversion.h and gfx/src/mac/nsDeviceContextMac.cpp
	nsCOMPtr<nsIDeviceContext> mDeviceContext = do_CreateInstance(kDeviceContextIID);
	float  p2t;
	p2t = mDeviceContext->DevUnitsToAppUnits();
#else
	int p2t = 15;
#endif

#if MOZ_VERSION < 190
#define PIXELS_TO_APP(x,y) NSIntPixelsToTwips(x,y)
#else
#define PIXELS_TO_APP(x,y) NSIntPixelsToAppUnits(x,y)
#endif
	textEventReply->mCursorPosition.x = PIXELS_TO_APP(SendEditor(SCI_POINTXFROMPOSITION, 0, curPos) + fWindow->x, p2t);
	textEventReply->mCursorPosition.y = PIXELS_TO_APP(SendEditor(SCI_POINTYFROMPOSITION, 0, curPos) + fWindow->y, p2t);
	textEventReply->mCursorPosition.width = fWindow->width;
	textEventReply->mCursorPosition.height = PIXELS_TO_APP(SendEditor(SCI_TEXTHEIGHT, curLine, 0), p2t);
	textEventReply->mCursorIsCollapsed = false;
#ifdef IME_DEBUG
	fprintf(stderr, "text event cursor collapsed %d rect %d %d %d %d\n",
		textEventReply->mCursorIsCollapsed,
		textEventReply->mCursorPosition.x,
		textEventReply->mCursorPosition.y,
		textEventReply->mCursorPosition.width,
		textEventReply->mCursorPosition.height
		);
#endif
#endif
	
	nsIPrivateTextRangeList *textRangeList;
	textEvent->GetInputRange(&textRangeList);

	int caretOffset = 0, selLength = 0;
	imeComposing = false;
	PRUint16 listlen,start,stop,type;
	textRangeList->GetLength(&listlen);
#ifdef IME_DEBUG
	fprintf(stderr, "nsIPrivateTextRangeList[%p] length %d\n",textRangeList, listlen);
#endif
	nsIPrivateTextRange* rangePtr;
	for (int i=0;i<listlen;i++) {
		(void)textRangeList->Item(i,&rangePtr);
		rangePtr->GetRangeStart(&start);
		rangePtr->GetRangeEnd(&stop);
		rangePtr->GetRangeType(&type);
#ifdef IME_DEBUG
		fprintf(stderr, "    range[%d] start=%d end=%d type=",i,start,stop);
		if (type==nsIPrivateTextRange::TEXTRANGE_RAWINPUT) {
		  fprintf(stderr, "TEXTRANGE_RAWINPUT\n");
		} else if (type==nsIPrivateTextRange::TEXTRANGE_SELECTEDRAWTEXT) {
		  fprintf(stderr, "TEXTRANGE_SELECTEDRAWTEXT\n");
		} else if (type==nsIPrivateTextRange::TEXTRANGE_CONVERTEDTEXT) {
		  fprintf(stderr, "TEXTRANGE_CONVERTEDTEXT\n");
		} else if (type==nsIPrivateTextRange::TEXTRANGE_SELECTEDCONVERTEDTEXT) {
		  fprintf(stderr, "TEXTRANGE_SELECTEDCONVERTEDTEXT\n");
		} else if (type==nsIPrivateTextRange::TEXTRANGE_CARETPOSITION) {
		  fprintf(stderr, "TEXTRANGE_CARETPOSITION\n");
		}
#endif
		switch(type) {
		case nsIPrivateTextRange::TEXTRANGE_RAWINPUT:
		case nsIPrivateTextRange::TEXTRANGE_SELECTEDRAWTEXT:
		case nsIPrivateTextRange::TEXTRANGE_CONVERTEDTEXT:
		case nsIPrivateTextRange::TEXTRANGE_SELECTEDCONVERTEDTEXT:
		  imeComposing = true;
		  selLength = stop;
		  break;
		case nsIPrivateTextRange::TEXTRANGE_CARETPOSITION:
		  caretOffset = start;
		}
	}
	if (imeComposing && imeStartPos < 0) {
#ifdef IME_DEBUG
		fprintf(stderr, "ime starting\n");
#endif
		StartCompositing();
	}
	// XXX problem here, we normally only want to insert text if we're
	// in or finishing an ime session.  However, some chinese keyboard
	// events happen a bit differently, so we do a bit of a hack to see
	// if we're receiving something we're interested in.  The real fix
	// is to figure out how to tell mozilla to cancel the IME session
	// in EndCompositing().
	//
	// bug 40960
	if (imeActive || NS_ConvertUTF16toUTF8(mIMEString).Length() > 0)
		ReplaceSel(*text);
	if (imeActive && imeComposing) {
		SetAnchor(imeStartPos);
	} else {
#ifdef IME_DEBUG
		fprintf(stderr, "ime finished\n");
#endif
		EndCompositing();
	}

	return NS_OK;
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


// ***********************************************************************
// *
// * Include interface implementation autogenerated from Scintilla.iface.
// *
// ***********************************************************************
#include "npscimoz_gen.h"


