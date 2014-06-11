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

/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

#include "nsSciMoz.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

HINSTANCE hInstSciLexer = 0;
static ATOM atomParkingLotClass = 0;
const char SciMozDLLName[] = "npscimoz.DLL";
const char ScintillaDLLName[] = "SciLexer.DLL";

void SciMoz::LoadScintillaLibrary() {
    // called in constructor
    if (!hInstSciLexer) {
        HMODULE hmodSciMoz = ::GetModuleHandle(SciMozDLLName);
        if (hmodSciMoz) {
            char fullPathModule[MAX_PATH];
            DWORD res = ::GetModuleFileName(hmodSciMoz, fullPathModule, sizeof(fullPathModule));
            if (res) {
                char *lastSlash = strrchr(fullPathModule, '\\');
                if (lastSlash && ((lastSlash + 1 - fullPathModule + strlen(ScintillaDLLName)) < sizeof(fullPathModule))) {
                    strcpy(lastSlash + 1, ScintillaDLLName);
                    hInstSciLexer = ::LoadLibrary(fullPathModule);
                }
            }
        }
    }

    if (!hInstSciLexer) {
        hInstSciLexer = ::LoadLibrary(ScintillaDLLName);
    }
}

void SciMoz::PlatformCreate(WinID hWnd) {
	RECT rc;
	::GetWindowRect(hWnd, &rc);
	wEditor = ::CreateWindow("Scintilla", "Scintilla", WS_CHILD | WS_CLIPSIBLINGS | WS_CLIPCHILDREN,
	                       0, 0, rc.right-rc.left, rc.bottom-rc.top,
	                       hWnd, (HMENU)1111, 0, NULL);
	NS_ABORT_IF_FALSE(wEditor, "CreateWindow for Scintilla failed\n");

#ifdef USE_SCIN_DIRECT
	fnEditor = reinterpret_cast<SciFnDirect>(::SendMessage(wEditor, SCI_GETDIRECTFUNCTION, 0, 0));
	ptrEditor = ::SendMessage(wEditor, SCI_GETDIRECTPOINTER, 0, 0);
#endif

	// Mozilla's d&d mechanism only works for nsIWindow objects, and we
	// aren't one (*sob* - I wish we were!).  So we report file drops
	// via the notifier service, and text d&d internally.
	DragAcceptFiles(wEditor, TRUE);
	/* Now subclass the child and save the real wndproc away
	 */
	fPlatform.fDefaultChildWindowProc =
	    (WNDPROC)SetWindowLong( wEditor,
	                            GWL_WNDPROC, (LONG)SciMoz::ChildWndProc);
        SetProp(wEditor, gInstanceLookupString, (HANDLE)this);
}

void SciMoz::Resize() {
	RECT rc;
	NS_PRECONDITION(wMain, "Must have a valid wMain to resize");
#ifdef SCIMOZ_DEBUG
	fprintf(stderr, "SciMoz::Resize width: %d height: %d\n", fPlatform.width, fPlatform.height);
#endif
	// Use the stored window size from the last PlatformSetWindow call.
	::SetWindowPos(wEditor, 0, 0, 0, fPlatform.width, fPlatform.height, SWP_NOZORDER | SWP_NOACTIVATE);
}

NS_IMETHODIMP SciMoz::_DoButtonUpDown(bool up, PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt) {
	long lpoint = LONGFROMTWOSHORTS(x,y);
	UINT msg;
	switch (button) {
		case 0:
			msg = up ? WM_LBUTTONUP : WM_LBUTTONDOWN;
			break;
		case 1:
			msg = up ? WM_MBUTTONUP : WM_MBUTTONDOWN;
			break;
		case 2:
			msg = up ? WM_RBUTTONUP : WM_RBUTTONDOWN;
			break;
		default:
			NS_WARNING("Bad mouse button number!\n");
			return NS_ERROR_INVALID_ARG;
	}
	WPARAM keyFlags = 0;
	if (bShift) keyFlags |= MK_SHIFT;
	if (bCtrl) keyFlags |= MK_CONTROL;
	// XXX - Scintilla still looks for ALT itself!
	SendEditor(msg, keyFlags, lpoint);
	return NS_OK;
}


/* void ButtonMove( in long x, in long y); */
NS_IMETHODIMP SciMoz::ButtonMove(PRInt32 x, PRInt32 y) {
	SCIMOZ_CHECK_VALID("ButtonMove");
	long lpoint = LONGFROMTWOSHORTS(x,y);
	SendEditor(WM_MOUSEMOVE, 0, lpoint);
	return NS_OK;
}


/* void AddChar( in PRUint32 ch); */
NS_IMETHODIMP SciMoz::AddChar(PRUint32 ch) {
	SCIMOZ_CHECK_VALID("AddChar");
	// XXX - Scintilla needs an SCI_ADDCHAR API??
	// !!! we received a wide char, send a wide char
	SendEditor(WM_UNICHAR, (WPARAM)ch);
	// Force any pending repaints now, to get around
	// Mozilla favouring keystroke messages in nsAppShell::Run
	UpdateWindow(wEditor);
	return NS_OK;
}

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformNew\n");
#endif
#ifdef SCIMOZ_TIMELINE
    if (gTimelineEnabled)
        NS_TimelineMark("SciMoz: object created at 0x%p", this);
#endif // SCIMOZ_TIMELINE
    fPlatform.fDefaultWindowProc = NULL;
    fPlatform.width = 100;
    fPlatform.height = 50;
    // Create a parent window for our parking lot.
    if (atomParkingLotClass == 0) {
        WNDCLASS wc;
        memset(&wc, 0, sizeof(wc));
        wc.lpfnWndProc = ParkingLotWndProc;
        wc.lpszClassName = "ScintillaParkingList";
        atomParkingLotClass = RegisterClass(&wc);
        NS_ABORT_IF_FALSE(atomParkingLotClass, "RegisterClass failed!");
    }
    wParkingLot = ::CreateWindow((LPCTSTR)atomParkingLotClass,
                                    "ScintillaParkingLot",
                                    0, // style
                                    0, 0, 0, 0, // pos
                                    NULL, NULL, 0, NULL);
    NS_ABORT_IF_FALSE(wParkingLot, "CreateWindow for the parking lot failed!");
    SetProp(wParkingLot, gInstanceLookupString, (HANDLE)this);
    // And create scintilla itself, parked in the lot.
    Create(wParkingLot);
}

nsresult SciMoz::PlatformDestroy(void) {
    PlatformResetWindow();
    // This must have reset out window.
    NS_PRECONDITION(portMain==0, "Should not be possible to destruct with a window!");
    if (wParkingLot) {
            ::DestroyWindow(wParkingLot);
            wParkingLot = NULL;
    }
    wEditor = NULL;
    fWindow = NULL;
    portMain = NULL;
    wMain = NULL;
#ifdef SCIMOZ_TIMELINE
    if (gTimelineEnabled)
        NS_TimelineMark("SciMoz: <%s@0x%p> object dieing", NS_ConvertUTF16toUTF8(name).get());
#endif
    isClosed = 1;
    return NS_OK;
}

void SciMoz::PlatformMarkClosed() {
	// Nothing.
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformResetWindow\n");
#endif
	// If our "parking lot" exists and is not already the parent,
	// then park our editor
	if (wParkingLot
		&& wEditor
		&& ::GetParent(wEditor) != wParkingLot) {
		::SetParent(wEditor, wParkingLot);
		parked = true;
	}
	if ( fWindow != NULL ) { /* If we have a Moz window, clean
	                          * it up. */
		SetWindowLong(wMain, GWL_WNDPROC, (LONG)fPlatform.fDefaultWindowProc);
		fPlatform.fDefaultWindowProc = NULL;
		portMain = NULL;
		wMain = NULL;
	}
	return NS_OK;
}

nsresult SciMoz::PlatformSetWindow(NPWindow* window) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformSetWindow %p\n",window);
#endif
	if ( fWindow != NULL ) /* If we already have a window, clean
	                        * it up before trying to subclass
	                        * the new window. */
	{
		fPlatform.width = window->width;
		fPlatform.height = window->height;
		if ( window && window->window && portMain == window->window ) {
			/* The new window is the same as the old one. Just resize and exit. */
			Resize();
			return NS_OK;
		}
		// Otherwise, just reset the window ready for the new one.
		PlatformResetWindow();
	}
	else if ( (window == NULL) || ( window->window == NULL ) ) {
		/* We can just get out of here if there is no current
		 * window and there is no new window to use. */
		return NS_OK;
	}
	if (window && window->window) {
		fWindow = window;
		portMain = window->window;
		wMain = (HWND) portMain;

		LONG style = GetWindowLong(wMain, GWL_STYLE);
		style |= WS_CLIPCHILDREN;
		SetWindowLong(wMain, GWL_STYLE, style);
		/* At this point, we will subclass
		 * window->window so that we can begin drawing and
		 * receiving window messages. */
		fPlatform.fDefaultWindowProc =
			(WNDPROC)SetWindowLong( wMain,
						GWL_WNDPROC, (LONG)SciMoz::WndProc);

		SetProp(wMain, gInstanceLookupString, (HANDLE)this);

		/* The Scintilla window is already created, and in the
		   parking lot.  Attach to the real window. */
		NS_ABORT_IF_FALSE(wEditor, "Don't have the real child in the parking lot.");
		/* Create the child, Scintilla window */
		::SetParent(wEditor, wMain);
		parked = false;
	}
	return NS_OK;
}

PRInt16 SciMoz::PlatformHandleEvent(void* /*event*/) {
	/* Windows Plugins use the Windows event call-back mechanism
	   for events. (See WndProc) */
	return 0;
}

// This is the WndProc for the "parking lot"
// (ie, the Window created by us as a temporary parent of Scintilla)
LRESULT CALLBACK SciMoz::ParkingLotWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam) {
	SciMoz* inst = (SciMoz*) GetProp(hWnd, gInstanceLookupString);
	switch (Msg) {

	case WM_SIZE: {
		NS_ABORT_IF_FALSE(inst, "Null instance in parking lot WndProc");
		inst->Resize();
		break;
    }

	case WM_NOTIFY: {
		NS_ABORT_IF_FALSE(inst, "Null instance in parking lot WndProc");
		inst->Notify(lParam);
		break;
    }

	default:
		break;
	}
	NS_ABORT_IF_FALSE(::IsWindow(hWnd), "Parking lot parent window is not a window!!");
	LRESULT rc = DefWindowProc(hWnd, Msg, wParam, lParam);
	return rc;
}

// This is the WndProc for plug-in container window
// (ie, the Window created by Mozilla for us, and the parent of Scintilla)
LRESULT CALLBACK SciMoz::WndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam) {
	SciMoz* inst = (SciMoz*) GetProp(hWnd, gInstanceLookupString);
	NS_ABORT_IF_FALSE(inst, "Null instance in plugin WndProc");

	switch (Msg) {

	case WM_DESTROY: {
		// Ensure we are parked and that our framework knows we are dead.
		// However, snaffle our wndProc before we do!
		WNDPROC wndProcSave = inst->fPlatform.fDefaultWindowProc;
		NS_ABORT_IF_FALSE(wndProcSave, "Expecting to have a default window proc!");
		if (wndProcSave==NULL) wndProcSave = DefWindowProc;
		inst->PlatformResetWindow();
		return wndProcSave(hWnd, Msg, wParam, lParam);
		}

	case WM_SIZE:
		inst->Resize();
	case WM_INPUTLANGCHANGE:
	case WM_INPUTLANGCHANGEREQUEST:
	case WM_IME_STARTCOMPOSITION: 	// dbcs
	case WM_IME_ENDCOMPOSITION: 	// dbcs
	case WM_IME_COMPOSITION:
	case WM_IME_CHAR: 
#ifdef SCIMOZ_DEBUG
		fprintf(stderr,"got someting re: i18n in Scimoz::WndProc\n");
#endif
		CallWindowProc(inst->fPlatform.fDefaultWindowProc, hWnd, Msg, wParam, lParam);
		break;

	case WM_NOTIFY:
		inst->Notify(lParam);
		break;

	case WM_CONTEXTMENU:
		// Sending this on seems to upset Mozilla.  It does all its context
		// menu as part the button processing.  Just ignore it.
		break;

	case WM_KILLFOCUS:
	case WM_SETFOCUS:
		// fall through!
	default:
		CallWindowProc(inst->fPlatform.fDefaultWindowProc, hWnd, Msg, wParam, lParam);
	}
	return 0;
}

// This is the WndProc for the sub-classed Scintilla control.
LRESULT CALLBACK SciMoz::ChildWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam) {
	SciMoz* inst = (SciMoz*) GetProp(hWnd, gInstanceLookupString);
	NS_ABORT_IF_FALSE(inst, "Null instance in child WndProc");
	LRESULT rc;
	switch (Msg) {
	// NOTE: We DONT pass on DBLCLK messages, as both Scintilla and
	// Mozilla have their own special logic, and they step on each other.
	// (causing Scintilla to see a double-click as a triple-click)
	case WM_KEYDOWN:
	case WM_SYSKEYDOWN:
	case WM_KEYUP:
	case WM_SYSKEYUP:
	case WM_CHAR:
	case WM_UNICHAR:
	case WM_SYSCHAR:
	case WM_LBUTTONDOWN:
	case WM_LBUTTONUP:
	case WM_MBUTTONDOWN:
	case WM_MBUTTONUP:
	case WM_RBUTTONDOWN:
	case WM_RBUTTONUP:
	case WM_MOUSEMOVE:
		// send the event through the DOM so we can use it.  Moz will
		// prevent bubbling on some events, primarily key and mouse
		CallWindowProc(inst->fPlatform.fDefaultWindowProc, (HWND)inst->portMain, Msg, wParam, lParam);
		// Tell scintilla about the event so it can do it's work
		if (Msg != WM_RBUTTONDOWN) {
			// But don't tell Scintilla about rbutton-down: bug 91616
			inst->fPlatform.fDefaultChildWindowProc(hWnd, Msg, wParam, lParam);
		}
		rc = 0; // allow the event to bubble if moz doesn't block us
		break;
	case WM_KILLFOCUS:
	case WM_SETFOCUS:
	  // fprintf(stderr,"Child Focus message %d\n", Msg);
		// XXX - Windows focus vs Mozilla focus screws us!
		// We ignore all Windows focus messages, and explicitly
		// set focus when Mozilla tells us to.
		rc = 1;
		break;
	case WM_INPUTLANGCHANGE:
	case WM_INPUTLANGCHANGEREQUEST:
	case WM_IME_STARTCOMPOSITION: 	// dbcs
	case WM_IME_ENDCOMPOSITION: 	// dbcs
	case WM_IME_COMPOSITION:
	case WM_IME_CHAR:
#ifdef SCIMOZ_DEBUG
		fprintf(stderr,"got INPUT LANG request in SciMoz::ChildWndProc\n");
#endif
	default:
		// let Scintilla's default handle it.
		rc = inst->fPlatform.fDefaultChildWindowProc(hWnd, Msg, wParam, lParam);
		break;
	}
	return rc;
}


/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	*_ret = wEditor && wMain && !isClosed
			&& ::GetParent(wEditor) == wMain;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetVisible(bool *_ret) {
	SCIMOZ_CHECK_VALID("GetVisible");
	*_ret = wEditor != 0
		&& IsWindowVisible(wEditor);
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::SetVisible(bool vis) {
	SCIMOZ_CHECK_VALID("SetVisible");
	ShowWindow(wEditor, vis ? SW_SHOW : SW_HIDE);
	return NS_OK;
}

/* void endDrop( ); */
NS_IMETHODIMP SciMoz::EndDrop()
{
	SCIMOZ_CHECK_VALID("EndDrop");
	// This will disable drag drop tracking - bug 87342.
	SendEditor(SCI_RELEASEMOUSECAPTURE, 0, 0);
	return NS_OK;
}

/* readonly attribute boolean inDragSession; */
NS_IMETHODIMP SciMoz::GetInDragSession(bool *_ret) {
	SCIMOZ_CHECK_VALID("GetInDragSession");
	*_ret = 0;
	return NS_OK;
}

/* readonly attribute boolean isTracking */
NS_IMETHODIMP SciMoz::GetIsTracking(bool *_ret) {
	SCIMOZ_CHECK_VALID("GetIsTracking");
	*_ret = 0;
	return NS_OK;
}
