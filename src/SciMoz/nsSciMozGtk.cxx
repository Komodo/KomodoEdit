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

//#define SCIMOZ_DEBUG

void SciMoz::PlatformCreate(WinID) {
}

void SciMoz::Resize() {
}

NS_IMETHODIMP SciMoz::_DoButtonUpDown(bool up,
                                      PRInt32 /* x */,
                                      PRInt32 /* y */,
                                      PRUint16 button,
                                      bool /* bShift */,
                                      bool /* bCtrl */,
                                      bool /* bAlt */) {
	if (up and button == 0) {
                SendEditor(SCI_RELEASEMOUSECAPTURE, 0, 0);
        }
        return NS_OK;
}


/* void ButtonMove( in long x, in long y); */
NS_IMETHODIMP SciMoz::ButtonMove(PRInt32 /* x */,
                                 PRInt32 /* y */) {
	SCIMOZ_CHECK_VALID("ButtonMove");
	return NS_OK;
}

/* void AddChar( in PRUint32 ch); */
NS_IMETHODIMP SciMoz::AddChar(PRUint32 ch) {
	SCIMOZ_CHECK_VALID("AddChar");
	SendEditor(WM_UNICHAR, ch);
	return NS_OK;
}

gint ButtonEvents(GtkWidget *widget,
                  GdkEventButton *event,
		  SciMoz *sciThis)
{
    if (event->type != GDK_BUTTON_RELEASE) {
        gtk_grab_add(widget);
        sciThis->sInGrab = 1;
    } else {
        gtk_grab_remove(widget);
        sciThis->sInGrab = 0;
    }
    return FALSE;
}

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformNew\n");
#endif
    fPlatform.moz_box = 0;
    wParkingLot = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    wEditor = scintilla_new();

    // disable scintilla's builtin context menu.
    SendEditor(SCI_USEPOPUP, 0, 0);
    SendEditor(SCI_SETFOCUS, 0, 0);

    gtk_container_add(GTK_CONTAINER(wParkingLot), wEditor);
    gtk_signal_connect(GTK_OBJECT(wEditor), SCINTILLA_NOTIFY,
                        GTK_SIGNAL_FUNC(NotifySignal), this);
    
    // these are necessary for correct focus after a drag/drop session
    gtk_signal_connect_after(GTK_OBJECT(wEditor), "button_press_event",
                             GTK_SIGNAL_FUNC(ButtonEvents), this);
    gtk_signal_connect_after(GTK_OBJECT(wEditor), "button_release_event",
                             GTK_SIGNAL_FUNC(ButtonEvents), this);

    Create(wEditor);
    /* force a size request so that we get the correct scrollbar width/height */
    GtkRequisition child_requisition;
    gtk_widget_size_request(wEditor, &child_requisition);
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformDestroy\n");
#endif
	/*
	  The plugin gtk window has already been destroyed, along with all of
	  the gtk Scintilla sub-windows (due to a gtk_widget_destroy() call
	  on the parenting plugin window), so we just need to reset the
	  variables here and destroy the parking lot.
	*/
	portMain = NULL;
	wMain = NULL;
	parked = true;
	fWindow = NULL;

	fPlatform.moz_box = 0;
	fPlatform.ws_info = NULL;

	wEditor = 0;
	if (wParkingLot) {
		gtk_widget_destroy(wParkingLot);
		wParkingLot = 0;
	}

	isClosed = 1;
	return NS_OK;
}

void SciMoz::PlatformMarkClosed() {
	// Nothing.
}

void SciMoz::NotifySignal(GtkWidget *, gint /*wParam*/, gpointer lParam, SciMoz *scimoz) {
        if (scimoz->isClosed) {
            fprintf(stderr, "SciMoz is getting a GTK signal after being closed.\n");
            return;
        }
        scimoz->Notify(reinterpret_cast<long>(lParam));
}

nsresult SciMoz::PlatformSetWindow(NPWindow* npwindow) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformSetWindow:: npwindow %p\n", npwindow);
#endif
    if (fWindow != NULL) {
	/* If we already have a window, clean
	 * it up before trying to subclass
	 *  the new window. */
	if (npwindow && npwindow->window && portMain == npwindow->window ) {
	    //fprintf(stderr, "Resized to %d,%d\n", npwindow->width, npwindow->height);
	    if (fPlatform.moz_box->window != NULL) {
		    gdk_window_resize(fPlatform.moz_box->window,
				    npwindow->width, npwindow->height);
	    }
	    /* The new window is the same as the old one. Exit now. */
	    return NS_OK;
	}
	// Otherwise, just reset the window ready for the new one.
	if (npwindow) {
	    PlatformResetWindow();
	}
    }
    
    if (npwindow) {
        NPSetWindowCallbackStruct *ws_info = (NPSetWindowCallbackStruct *)npwindow->ws_info;
#ifdef GTK2_XEMBED

// We use both __LP64__ and _LP64 because some platforms define both, others
// only may only define one or the other...
#if defined(__LP64__) || defined(_LP64)
	fPlatform.moz_box = gtk_plug_new((gulong)npwindow->window);
#else
	fPlatform.moz_box = gtk_plug_new((guint)npwindow->window);
#endif

#else /* !GTK2_XEMBED */
	fPlatform.moz_box = gtk_plug_new(0);
#endif
	wMain = fPlatform.moz_box;

	/* only set these if the above logic succeeds, otherwise we crash and burn */
	portMain = npwindow->window;
	fWindow = npwindow;
	fPlatform.ws_info = ws_info;

	if (parked) {
	    // Reparent scintilla onto moz box
	    gtk_widget_ref(wEditor);
	    gtk_container_remove(GTK_CONTAINER(wParkingLot), wEditor);
	    gtk_container_add(GTK_CONTAINER(fPlatform.moz_box), wEditor);
	    gtk_widget_unref(wEditor);
	    parked = false;
	}
	gtk_widget_show_all(fPlatform.moz_box);
#ifndef GTK2_XEMBED
	/* reparent the plug to the mozilla window */
	GdkDrawable* win = GDK_DRAWABLE(fPlatform.moz_box->window);
	XReparentWindow(GDK_DRAWABLE_XDISPLAY(win),
			GDK_DRAWABLE_XID(win),
			(XID)npwindow->window, 0, 0);

	XMapWindow(GDK_DRAWABLE_XDISPLAY(win),
		   GDK_DRAWABLE_XID(win));
#endif
    } else {
	PlatformResetWindow();
    }
    return NS_OK;
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformResetWindow\n");
#endif
	// If our "parking lot" exists and is not already the parent,
	// then park our editor
	if (wParkingLot
		&& wEditor
		&& !parked) {
#ifdef SCIMOZ_DEBUG
		fprintf(stderr, "SciMoz::PlatformResetWindow:: parking the editor.\n");
#endif
		gtk_widget_ref(wEditor);
		gtk_container_remove(GTK_CONTAINER(fPlatform.moz_box), wEditor);
		gtk_container_add(GTK_CONTAINER(wParkingLot), wEditor);
		gtk_widget_unref(wEditor);
		portMain = NULL;
		wMain = NULL;
		parked = true;
		fWindow = NULL;
	}
	if (fPlatform.moz_box) {
	    // XXX bug 33817, when using gtk2 glib generates a warning here
		gtk_widget_destroy(fPlatform.moz_box);
	}
	fPlatform.moz_box = 0;
	fPlatform.ws_info = NULL;
	return NS_OK;
}

int16 SciMoz::PlatformHandleEvent(void * /*event*/) {
	/* UNIX Plugins do not use HandleEvent */
	return 0;
}


/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	*_ret = wEditor && wMain && !isClosed;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetVisible(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	SCIMOZ_CHECK_ALIVE("GetVisible", NS_ERROR_FAILURE);
	*_ret = wEditor != 0;
	return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::SetVisible(bool /* vis */) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	SCIMOZ_CHECK_ALIVE("SetVisible", NS_ERROR_FAILURE);
	return NS_OK;
}

/* void endDrop( ); */
NS_IMETHODIMP SciMoz::EndDrop()
{
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	SCIMOZ_CHECK_ALIVE("EndDrop", NS_ERROR_FAILURE);
	if (sInGrab) {
		gtk_grab_remove(wEditor);
		sInGrab = 0;
	}
	return NS_OK;
}

/* readonly attribute boolean inDragSession; */
NS_IMETHODIMP SciMoz::GetInDragSession(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	SCIMOZ_CHECK_ALIVE("GetInDragSession", NS_ERROR_FAILURE);
	*_ret = 0;
	return NS_OK;
}

/* readonly attribute boolean isTracking */
NS_IMETHODIMP SciMoz::GetIsTracking(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	SCIMOZ_CHECK_ALIVE("GetIsTracking", NS_ERROR_FAILURE);
	*_ret = 0;
	return NS_OK;
}
