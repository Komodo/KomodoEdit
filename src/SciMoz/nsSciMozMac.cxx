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

#include "plugin.h"
#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif
#ifdef XP_MACOSX
#ifdef XP_UNIX
#undef XP_UNIX
#endif
#endif

void SciMoz::PlatformCreate(WinID) {
}

void SciMoz::Resize() {
	// we have to get the titlebar height, and add it to the y origin
	Rect winRect;
	GetWindowBounds(fPlatform.container, kWindowTitleBarRgn, &winRect);
	int tbHeight = winRect.bottom - winRect.top;

	HIRect boundsRect;
	boundsRect.origin.x = fWindow->x; // left
	boundsRect.origin.y = fWindow->y +  tbHeight; // top
	boundsRect.size.width = fWindow->width;
	boundsRect.size.height = fWindow->height;
#ifdef DEBUG_PAINT
	fprintf(stderr, "SciMoz::Resize window %d %d %d %d  clip rect %d %d %d %d\n",
		fWindow->x, fWindow->y, fWindow->width + fWindow->x, fWindow->height + fWindow->y, 
		fWindow->clipRect.left, fWindow->clipRect.top, 
		fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
	HIViewSetFrame(wEditor, &boundsRect);
}

NS_IMETHODIMP SciMoz::_DoButtonUpDown(PRBool up, PRInt32 x, PRInt32 y, PRUint16 button, PRUint64 timeStamp, PRBool bShift, PRBool bCtrl, PRBool bAlt) {
	HIViewRef view;
	HIPoint location;
	UInt32 keyFlags = 0;
	EventMouseButton mb;
	
	location.x = x;
	location.y = y;
	
	// ignore scrollbar hits
	HIViewGetSubviewHit(wEditor, &location, true, &view);
	if (view) return NS_OK;
	
	switch (button) {
		case 0:
			mb = kEventMouseButtonPrimary;
			break;
		case 1:
			mb = kEventMouseButtonTertiary;
			break;
		case 2:
			mb = kEventMouseButtonSecondary;
			break;
		default:
			NS_WARNING("Bad mouse button number!\n");
			return NS_ERROR_INVALID_ARG;
	}
	if (bShift) keyFlags |= shiftKey;
	if (bCtrl) keyFlags |= controlKey;
	if (bAlt) keyFlags |= cmdKey;
	
	if (up) {
		scintilla->MouseUp(location, keyFlags, mb, 1);
	} else {
		scintilla->MouseDown(location, keyFlags, mb, 1);
	}
	return NS_OK;
}


/* void ButtonMove( in long x, in long y); */
NS_IMETHODIMP SciMoz::ButtonMove(PRInt32 x, PRInt32 y) {
	HIPoint location;
	location.x = x;
	location.y = y;
	scintilla->MouseDragged(location, 0, 0, 0);
	return NS_OK;
}


/* void AddChar( in PRUint32 ch); */
NS_IMETHODIMP SciMoz::AddChar(PRUint32 ch) {
	// XXX - Scintilla needs an SCI_ADDCHAR API??
	SendEditor(WM_UNICHAR, ch);
	return NS_OK;
}

extern "C" {
extern HIViewRef scintilla_new(void);
}

typedef void (*SciNotifyFunc)(sptr_t *, long);
void SciMoz::NotifySignal(sptr_t *ptr, long param) {
	SciMoz *s = reinterpret_cast<SciMoz *>(ptr);
	s->Notify(param);
}

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformNew\n");
#endif
	OSStatus err;
	fPlatform.port = NULL;
	fPlatform.container = NULL;
	wEditor = scintilla_new();
	err = GetControlProperty( wEditor, scintillaMacOSType, 0, sizeof( scintilla ), NULL, &scintilla );
	assert( err == noErr && scintilla != NULL );

	// disable scintilla's builtin context menu.
	SendEditor(SCI_USEPOPUP, FALSE, 0);
	SendEditor(SCI_SETFOCUS, FALSE, 0);
	
	// setup the hooks that are necessary to receive notifications from scintilla
	SciMoz* objectPtr = this;
	SciNotifyFunc fn = SciMoz::NotifySignal;
	
	err = SetControlProperty( wEditor, scintillaNotifyObject, 0, sizeof( this ), &objectPtr );
	assert( err == noErr );
	err = SetControlProperty( wEditor, scintillaNotifyFN, 0, sizeof( void * ), &fn );
	assert( err == noErr );

	Create(wEditor);
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformDestroy\n");
#endif
	PlatformResetWindow();
	// This must have reset out window.
	NS_PRECONDITION(portMain==0, "Should not be possible to destruct with a window!");
	
	OSStatus err;
	err = HIViewRemoveFromSuperview(wEditor);
	delete scintilla;
	scintilla = NULL;
	delete wEditor;
	wEditor = NULL;
	fPlatform.port = NULL;
	fPlatform.container = NULL;
	return NS_OK;
}

#define WINDOW_DISABLED(a) (!a || \
				  (a->clipRect.bottom <= a->clipRect.top && \
				   a->clipRect.right  <= a->clipRect.left))
nsresult SciMoz::PlatformSetWindow(NPWindow* npwindow) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformSetWindow e:%08X w:%08X\n", wEditor, npwindow);
#endif
	if ( (npwindow == NULL) || ( npwindow->window == NULL ) ) {
		/* We can just get out of here if there is no current
		 * window and there is no new window to use. */
#ifdef DEBUG_PAINT
		fprintf(stderr, "....switching states, do not draw\n");
#endif
		SetHIViewShowHide(true);
		return NS_OK;
	}
	if ( fWindow != NULL ) /* If we already have a window, clean
				* it up before trying to subclass
				* the new window. */
	{
		if ( npwindow && npwindow->window && portMain == npwindow->window ) {
#ifdef DEBUG_PAINT
			fprintf(stderr, "....have fWindow, call show/hide\n");
#endif
			SetHIViewShowHide(WINDOW_DISABLED(fWindow));
			return NS_OK;
		}
		// Otherwise, just reset the window ready for the new one.
#ifdef DEBUG_PAINT
		fprintf(stderr, "....calling reset window\n");
#endif
		PlatformResetWindow();
	}
	if (npwindow && npwindow->window) {
		fWindow = npwindow;
		portMain = npwindow->window;
		NP_Port* npport = (NP_Port*) portMain;
		fPlatform.port = npport->port;
		fPlatform.container = GetWindowFromPort(fPlatform.port);
		wMain = HIViewGetRoot(fPlatform.container);

		// show scintilla
		SetHIViewShowHide(WINDOW_DISABLED(fWindow));
		parked = false;
	}
	return NS_OK;
}

void SciMoz::SetHIViewShowHide(bool disable) {
	int visible = HIViewGetSuperview(wEditor) != NULL;
	if (disable && visible) {
#ifdef DEBUG_PAINT
		fprintf(stderr, "......hiding editor %08X (%d,%d,%d,%d)\n", wEditor,
											fWindow->clipRect.left, fWindow->clipRect.top, 
											fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
		scintilla->SetTicking(false);
		scintilla->Resize(0,0);
		Draw1Control(wEditor);
		HIViewSetDrawingEnabled(wEditor, false);
		HIViewSetVisible(wEditor, false);
		HIViewRemoveFromSuperview(wEditor);

	} else
	if (!disable && !visible) {
#ifdef DEBUG_PAINT
		fprintf(stderr, "......showing editor %08X (%d,%d,%d,%d)\n", wEditor,
											fWindow->clipRect.left, fWindow->clipRect.top, 
											fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
		HIViewSetVisible(wEditor, true);
		HIViewSetDrawingEnabled(wEditor, true);
		HIViewAddSubview(wMain, wEditor);
		Resize();
		scintilla->Resize(fWindow->width,fWindow->height);
		Draw1Control(wEditor);
		scintilla->SetTicking(true);
	}
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformResetWindow\n");
#endif
	OSStatus err;

	// If our "parking lot" exists and is not already the parent,
	// then park our editor
	if (wEditor
		&& !parked) {
		err = HIViewRemoveFromSuperview(wEditor);
		portMain = NULL;
		wMain = NULL;
		parked = true;
		fWindow = NULL;
		fPlatform.port = NULL;
		fPlatform.container = NULL;
	}
	return NS_OK;
}

int16 SciMoz::PlatformHandleEvent(void *ev) {
	/* UNIX Plugins do not use HandleEvent */
	
	//fprintf(stderr,"SciMoz::PlatformHandleEvent\n");
	EventRecord *event = (EventRecord *)ev;
	switch (event->what)
	{
	case nullEvent:
		break;
	case mouseDown:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent mouseDown h %d v %d\n",event->where.h, event->where.v);
		EndCompositing();
		if (scintilla->MouseDown(event) == noErr) return true;
		break;
	case mouseUp:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent mouseUp h %d v %d\n",event->where.h, event->where.v);
		if (scintilla->MouseUp(event) == noErr) return true;
		break;
	case NPEventType_AdjustCursorEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent AdjustCursorEvent: mouseMove or mouseEnter\n");
		if (scintilla->MouseDragged(event) == noErr) return true;
		break;
	case NPEventType_LoseFocusEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent LoseFocusEvent\n");
		EndCompositing();
		break;
	case NPEventType_GetFocusEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent GetFocusEvent\n");
		break;
	case NPEventType_MenuCommandEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent MenuCommandEvent\n");
		break;
	case NPEventType_ClippingChangedEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent ClippingChangedEvent\n");
		break;
	case NPEventType_ScrollingBeginsEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent ScrollingBeginsEvent\n");
		break;
	case NPEventType_ScrollingEndsEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent ScrollingEndsEvent\n");
		break;
	case keyDown:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent keyDown\n");
		break;
	case keyUp:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent keyUp\n");
		break;
	case autoKey:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent autoKey\n");
		break;
	case updateEvt:
		// SetWindow is *always* called prior to updateEvt, see Paint() in 
		// mozilla/layout/html/base/src/nsObjectFrame.cpp
#ifdef DEBUG_PAINT
		fprintf(stderr, "SciMoz::PlatformHandleEvent updateEvt %08X\n", wEditor);
#endif
		Draw1Control(wEditor);
		return true;
		break;
	case diskEvt:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent diskEvt\n");
		break;
	case activateEvt:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent activateEvt\n");
		break;
	case osEvt:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent osEvt\n");
	// moz is giving us mouse enter/leave events here
		break;
	case kHighLevelEvent:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent kHighLevelEvent\n");
		break;
	default:
		//fprintf(stderr, "SciMoz::PlatformHandleEvent event %d\n", event->what);
		break;
	}
	
	return false;
}


/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(PRBool *_ret) {
	*_ret = wEditor && wMain;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetVisible(PRBool *_ret) {
	*_ret = wEditor != 0;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::SetVisible(PRBool vis) {
	return NS_OK;
}

/* void endDrop( ); */
NS_IMETHODIMP SciMoz::EndDrop()
{
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetInDragSession(PRBool *_ret) {
	*_ret = scintilla->inDragSession;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetIsTracking(PRBool *_ret) {
	*_ret = scintilla->isTracking;
	return NS_OK;
}
