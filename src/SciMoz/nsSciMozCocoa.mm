/*
  Web pages for cocoa/mozilla info:

  https://wiki.mozilla.org/NPAPI:CocoaEventModel - 2011-01-18, Josh Aas & Anders Carlsson

  https://developer.mozilla.org/en-US/docs/Gecko_Plugin_API_Reference - general

  http://colonelpanic.net/2009/03/building-a-firefox-plugin-part-one/  


 */
#import "plugin.h"
#import "nsSciMoz.h"

#import <Cocoa/Cocoa.h>

#import "ScintillaView.h"

    /*
      typedef struct _NPCocoaEvent {
    NPCocoaEventType type;
    uint32 version;
    union {
        struct {
            uint32 modifierFlags;
            double pluginX;
            double pluginY;            
            int32 buttonNumber;
            int32 clickCount;
            double deltaX;
            double deltaY;
            double deltaZ;
        } mouse;
        struct {
            uint32 modifierFlags;
            NPNSString *characters;
            NPNSString *charactersIgnoringModifiers;
            NPBool isARepeat;
            uint16 keyCode;
        } key;
        struct {
           CGContextRef context;
           double x;
           double y;
           double width;
           double height;
        } draw;
        struct {
            NPBool hasFocus;
        } focus;
        struct {
            NPNSString *text;
        } text;
    } data;
} NPCocoaEvent;

uint32 modifierFlags;

An integer bit field indicating the modifier keys. It uses the same constants as -[NSEvent modifierFlags].

int32 clickCount;

The number of mouse clicks associated with the event.

double deltaX;
double deltaY;
double deltaZ;

The X, Y or Z coordinate change for a scroll wheel, mouse-move, or mouse-drag event. 

See https://wiki.mozilla.org/NPAPI:CocoaEventModel for info on
Popup menus, Text Input & IME handling

    */


#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

void SciMoz::PlatformCreate(WinID) {
}

void SciMoz::Resize() {
    // NSMakeRect(origin.x, origin.y, width, height)
    NSRect boundsRect = NSMakeRect(fWindow->x,
                                   fWindow->y,
                                   fWindow->width,
                                   fWindow->height);
#ifdef DEBUG_PAINT
    fprintf(stderr, "SciMoz::Resize window %d %d %d %d  clip rect %d %d %d %d\n",
            fWindow->x, fWindow->y, fWindow->width + fWindow->x,
            fWindow->height + fWindow->y, 
            fWindow->clipRect.left, fWindow->clipRect.top, 
            fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
    ScintillaView *scView = (ScintillaView *) wEditor;
    [scView setFrame:boundsRect];
    [scView setNeedsDisplay:YES];
}

static NSEvent *SynthesizeEvent(PRBool up, PRInt32 x, PRInt32 y, PRUint16 button, PRBool bShift, PRBool bCtrl, PRBool bAlt, WinID wEditor) {
    NSEventType eventType;
	switch (button) {
    case 0:
        eventType = up ? NSLeftMouseUp : NSLeftMouseDown;
        break;
    case 1:
        eventType = up ? NSOtherMouseUp : NSOtherMouseDown;
        break;
    case 2:
        eventType = up ? NSRightMouseUp : NSRightMouseDown;
        break;
    default:
        NS_WARNING("Bad mouse button number!\n");
        return NULL;
	}
    NSUInteger aModifierFlags = (0
                                 | (bShift ? NSShiftKeyMask : 0)
                                 | (bCtrl ? NSControlKeyMask : 0)
                                 | (bAlt ? NSAlternateKeyMask : 0));
    // This part from nsChildView.mm SynthesizeNativeMouseEvent
    NSPoint screenPoint = NSMakePoint(x, [[NSScreen mainScreen] frame].size.height - y);
    ScintillaView *scView = (ScintillaView *) wEditor;
    NSWindow *scWindow = [scView window];
    NSPoint windowPoint = [scWindow convertScreenToBase:screenPoint];
    NSEvent* event = [NSEvent mouseEventWithType:eventType
                      location:windowPoint
                      modifierFlags:aModifierFlags
                      timestamp:[NSDate timeIntervalSinceReferenceDate]
                      windowNumber:[scWindow windowNumber]
                      context:nil
                      eventNumber:0
                      clickCount:1
                      pressure:0.0];
    return event;
}

NS_IMETHODIMP SciMoz::_DoButtonUpDown(PRBool up, PRInt32 x, PRInt32 y,
                                      PRUint16 button, PRBool bShift,
                                      PRBool bCtrl, PRBool bAlt) {
    NSEvent* event = SynthesizeEvent(up, x, y, button, bShift, bCtrl, bAlt, wEditor);
    if (!event) {
        return NS_ERROR_FAILURE;
    }
    if (up) {
        scintilla->MouseUp(event);
    } else {
        scintilla->MouseDown(event);
    }
    return NS_OK;
}

/* void ButtonMove( in long x, in long y); */
NS_IMETHODIMP SciMoz::ButtonMove(PRInt32 x, PRInt32 y) {
    SCIMOZ_CHECK_VALID("ButtonMove");
    // This part from nsChildView.mm SynthesizeNativeMouseEvent
    NSPoint screenPoint = NSMakePoint(x, [[NSScreen mainScreen] frame].size.height - y);
    ScintillaView *scView = (ScintillaView *) wEditor;
    NSPoint windowPoint = [[scView window] convertScreenToBase:screenPoint];
    NSEvent* event = [NSEvent mouseEventWithType:NSMouseMoved
                      location:windowPoint
                      modifierFlags:0
                      timestamp:[NSDate timeIntervalSinceReferenceDate]
                      windowNumber:[[scView window] windowNumber]
                      context:nil
                      eventNumber:0
                      clickCount:1
                      pressure:0.0];
    if (!event) {
        return NS_ERROR_FAILURE;
    }
    scintilla->MouseMove(event);
    return NS_OK;
}


/* void AddChar( in PRUint32 ch); */
NS_IMETHODIMP SciMoz::AddChar(PRUint32 ch) {
    SCIMOZ_CHECK_VALID("AddChar");
    // XXX - Scintilla needs an SCI_ADDCHAR API??
    SendEditor(WM_UNICHAR, ch);
    return NS_OK;
}

extern "C" {
extern NSObject scintilla_new(void);
}

void SciMoz::NotifySignal(intptr_t windowid, unsigned int iMessage, uintptr_t wParam, uintptr_t lParam) {
    if (iMessage == WM_NOTIFY) {
        SciMoz *s = reinterpret_cast<SciMoz *>(windowid);
        s->Notify(lParam);
    }
}

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,">> SciMoz::PlatformNew\n");
#endif
    fPlatform.container = NULL;
    fPlatform.context = NULL;
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"<< SciMoz::PlatformNew\n");
#endif
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformDestroy wEditor %p scintilla %p\n", wEditor, scintilla);
#endif
    if (scintilla) {
        scintilla->unregisterNotifyCallback();
        delete scintilla;
        scintilla = NULL;
    }
    if (wEditor) {
        PlatformResetWindow();
        // This must have reset out window.
        NS_PRECONDITION(portMain==0, "Should not be possible to destruct with a window!");
        [wEditor release];
        wEditor = NULL;
    }
    fPlatform.container = NULL;
    isClosed = 1;
    return NS_OK;
 }


void SciMoz::PlatformMarkClosed() {
	if (scintilla) {
            scintilla->unregisterNotifyCallback();
	}
}

#if 0
 typedef struct _NPWindow {
   NSWindow *window;
   uint32_t x, y, width, height;
   NPRect clipRect;
   NPWindowType type;
 } NPWindow;
#endif

#define WINDOW_DISABLED(a) (!a || \
				  (a->clipRect.bottom <= a->clipRect.top && \
				   a->clipRect.right  <= a->clipRect.left))
nsresult SciMoz::PlatformSetWindow(NPWindow* npwindow) {
#ifdef SCIMOZ_DEBUG
  fprintf(stderr,"SciMoz::PlatformSetWindow wEditor:%p npwindow:%p, fWindow:%p\n",
	  wEditor, npwindow, fWindow);
#endif
  if (npwindow) {
    fprintf(stderr, "Show npwindow->window:\n");
    fprintf(stderr, "npwindow->window:%p\n", npwindow->window);
  } else {
    fprintf(stderr, "npwindow is null:\n");
  }

    if (!npwindow || !npwindow->window) {
        /* We can just get out of here if there is no current
         * window and there is no new window to use. */
#ifdef DEBUG_PAINT
      if (!npwindow) {
        fprintf(stderr, "!npwindow\n");
      } else {
        fprintf(stderr, "!npwindow->window\n");
      }
      fprintf(stderr, "....switching states, do not draw\n");
#endif
      if (fWindow) {
	SetHIViewShowHide(true);
      }
        return NS_OK;
    }
    if (fWindow) { /* If we already have a window, clean
                     * it up before trying to subclass
                     * the new window. */
        fprintf(stderr, "We already have a window: fWindow != null\n");
	if (portMain == npwindow->window) {
#ifdef DEBUG_PAINT
            fprintf(stderr, "....have fWindow, call show/hide (%d,%d,%d,%d)\n",
                    fWindow->clipRect.left, fWindow->clipRect.top,
                    fWindow->clipRect.right, fWindow->clipRect.bottom);
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
    fWindow = npwindow;
    portMain = wMain = (NSWindow *) npwindow->window;
    fprintf(stderr, "portMain: npwindow->window:%p\n", npwindow->window);
    fPlatform.container = (NSWindow *) portMain;
    fPlatform.context = 0;
    // Things about the NSWindow object:
    fprintf(stderr, "NPWindow info: x:%d y:%d height:%d width:%d, type:%d\n",
	    fWindow->x,
	    fWindow->y,
	    fWindow->height,
	    fWindow->width,
	    fWindow->type);


    NP_CGContext *cgContext = (NP_CGContext *) npwindow->window;
    portMain = wMain = (NSWindow *) cgContext->window;
    fprintf(stderr, "wMain: npwindow->window->window:%p\n", wMain);
    fPlatform.container = (NSWindow *) portMain;
    fPlatform.context = cgContext->context;

#if 0
    fprintf(stderr, "-[fPlatform.container contentView]\n");
    NSView *contentView = [fPlatform.container contentView];
    fprintf(stderr, "contentView: %p\n",
	    contentView);
    if (contentView) {
      NSRect frame = [contentView frame];
      NSRect bounds = [contentView bounds];
      
    fprintf(stderr, "contentView: %p, frame:%f/%f/%f/%f, bounds:%f/%f/%f/%f\n",
	    contentView,
	    frame.origin.x ,frame.origin.y, frame.size.width, frame.size.height,
	    bounds.origin.x ,bounds.origin.y, bounds.size.width, bounds.size.height);
    }
#endif
#if 0
    fprintf(stderr, "-[fPlatform.container contentView]\n");
    NSView *contentView = [fPlatform.context contentView];
    fprintf(stderr, "contentView: %p\n",
	    contentView);
    if (contentView) {
      NSRect frame = [contentView frame];
      NSRect bounds = [contentView bounds];
      
    fprintf(stderr, "contentView: %p, frame:%f/%f/%f/%f, bounds:%f/%f/%f/%f\n",
	    contentView,
	    frame.origin.x ,frame.origin.y, frame.size.width, frame.size.height,
	    bounds.origin.x ,bounds.origin.y, bounds.size.width, bounds.size.height);
    }
#endif

    parked = false;
    if (fPlatform.container) {
      // NSMakeRect(origin.x, origin.y, width, height)
      fprintf(stderr, "clipRect dims: L:%d T:%d R:%d B:%d\n",
	      fWindow->clipRect.left,
	      fWindow->clipRect.top,
	      fWindow->clipRect.right,
	      fWindow->clipRect.bottom);
#ifdef SCIMOZ_DEBUG
      fprintf(stderr," -NSMakeRect, fWindow:%p\n", fWindow);
#endif
      NSRect newRect = NSMakeRect(fWindow->x,
				  fWindow->y,
				  fWindow->width,
				  fWindow->height);
#ifdef SCIMOZ_DEBUG
      fprintf(stderr," -alloc ScintillaView\n");
#endif
      ScintillaView *scView = [[[ScintillaView alloc] initWithFrame: newRect] retain];
      // ScintillaView.initWithFrame sets mBackEnd to new ScintillaCocoa(mContent)
      wEditor = scView;
#ifdef SCIMOZ_DEBUG
      fprintf(stderr,"scView:%p\n", scView);
      fprintf(stderr,"-scintilla = scView.backend;\n");
#endif
      scintilla = scView.backend;
      assert(scintilla != NULL);

      // disable scintilla's builtin context menu.
#ifdef SCIMOZ_DEBUG
      fprintf(stderr," -SendEditor(...)\n");
#endif
      SendEditor(SCI_USEPOPUP, FALSE, 0);
      SendEditor(SCI_SETFOCUS, FALSE, 0);

#ifdef SCIMOZ_DEBUG
      fprintf(stderr," -scintilla->RegisterNotifyCallback(...)\n");
#endif	
      // setup the hooks that are necessary to receive notifications from scintilla
      scintilla->RegisterNotifyCallback((intptr_t)this, (SciNotifyFunc)SciMoz::NotifySignal);

      Create(wEditor);
      // This was HIViewGetRoot
      wMain = [scView superview];
      SetHIViewShowHide(WINDOW_DISABLED(fWindow)); // show scintilla
    } else {
        PlatformResetWindow();
    }
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"<< SciMoz::PlatformSetWindow \n");
#endif
    return NS_OK;
}

void SciMoz::SetHIViewShowHide(bool disable) {
  fprintf(stderr, "SetHIViewShowHide: disable:%d\n", disable);
    ScintillaView *scView = (ScintillaView *) wEditor;
    int isInvisible = [scView isHidden];
    disable = false;
  fprintf(stderr, "SetHIViewShowHide: disable:%d\n", disable);
  fprintf(stderr, "SetHIViewShowHide: isInvisible:%d\n", isInvisible);
    
    if (disable && isInvisible) {
#ifdef DEBUG_PAINT
        fprintf(stderr, "......hiding editor %08X (%d,%d,%d,%d)\n", scView,
                fWindow->clipRect.left, fWindow->clipRect.top, 
                fWindow->width, fWindow->height);
#endif
        scintilla->SetTicking(false);
        scintilla->Resize();
        [scView setNeedsDisplay:YES];
        //gone: HIViewSetDrawingEnabled(scView, false);
        [scView setHidden:YES];
        [scView removeFromSuperview];

    } else if (!disable && !isInvisible) {
#ifdef DEBUG_PAINT
        fprintf(stderr, "......showing editor %08X (%d,%d,%d,%d)\n", scView,
                fWindow->clipRect.left, fWindow->clipRect.top, 
                fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
        [scView setHidden:NO];
        // gone: HIViewSetDrawingEnabled(scView, true);
        [((NSView *) wMain) addSubview:scView];
        Resize();
        scintilla->Resize();
        [scView setNeedsDisplay:YES];
        scintilla->SetTicking(true);
    }
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformResetWindow\n");
#endif

    // If our "parking lot" exists and is not already the parent,
    // then park our editor
    if (wEditor && !parked) {
      ScintillaView *scView = (ScintillaView *) wEditor;
        [scView removeFromSuperview];
        portMain = NULL;
        wMain = NULL;
        parked = true;
        fWindow = NULL;
        fPlatform.container = NULL;
    }
    return NS_OK;
}

void AbortComposing(NPP npp, NPObject* object) {
	NPVariant dummyResult = { NPVariantType_Void };
	NPN_Invoke(npp,
		   object,
		   NPN_GetStringIdentifier("abortComposing"),
		   nsnull,
		   0,
		   &dummyResult);
	NPN_ReleaseVariantValue(&dummyResult);
}


static NSEvent* nsEventFromNPCocoaMouseClickEvent(NPCocoaEvent *ev,
						  ScintillaView *scView) {
    NSEventType eventType;
    bool isUp = ev->type == NPCocoaEventMouseDown;
    switch (ev->data.mouse.buttonNumber) {
    case 0:
        eventType = isUp ? NSLeftMouseUp : NSLeftMouseDown;
        break;
    case 1:
        eventType = isUp ? NSOtherMouseUp : NSOtherMouseDown;
        break;
    case 2:
        eventType = isUp ? NSRightMouseUp : NSRightMouseDown;
        break;
    default:
        NS_WARNING("Bad mouse button number!\n");
        return NULL;
    }
    double x = ev->data.mouse.pluginX;
    double y = ev->data.mouse.pluginY;
    NSPoint screenPoint = NSMakePoint(x,
                                      [[NSScreen mainScreen] frame].size.height - y);
    NSWindow *scWindow = [scView window];
    NSPoint windowPoint = [scWindow convertScreenToBase:screenPoint];
    NSEvent* event = [NSEvent mouseEventWithType:eventType
                              location:windowPoint
                              modifierFlags:ev->data.mouse.modifierFlags
                              timestamp:[NSDate timeIntervalSinceReferenceDate]
                              windowNumber:[scWindow windowNumber]
                              context:nil
                              eventNumber:0
                              clickCount:1
                              pressure:0.0];
    return event;
}

int16 SciMoz::PlatformHandleEvent(void *ev) {
    NPCocoaEvent *event = (NPCocoaEvent *) ev;
    NSEvent *fixedNSEvent;
	
    if (isClosed) {
        fprintf(stderr, "SciMoz is getting an event after being closed.\n");
        return false;
    }

    switch (event->type) {
    case NPCocoaEventDrawRect:
        break;
    case NPCocoaEventMouseDown:
        fixedNSEvent = nsEventFromNPCocoaMouseClickEvent(event,
						 (ScintillaView *) wEditor);
        if (fixedNSEvent) {
            AbortComposing(mPlugin->GetNPP(), mIMEHelper);
            scintilla->MouseDown(fixedNSEvent);
        }
        break;
    case NPCocoaEventMouseUp:
        fixedNSEvent = nsEventFromNPCocoaMouseClickEvent(event,
						 (ScintillaView *) wEditor);
        if (fixedNSEvent) {
            AbortComposing(mPlugin->GetNPP(), mIMEHelper);
            scintilla->MouseUp(fixedNSEvent);
        }
        break;

    case NPCocoaEventFocusChanged:
    case NPCocoaEventWindowFocusChanged:
        {
            bool windowFocusChanged = event->type == NPCocoaEventWindowFocusChanged;
            fprintf(stderr, "SciMozCocoa::PlatformHandleEvent: %s %s\n",
                    (windowFocusChanged
                     ? "NPCocoaEventWindowFocusChanged"
                     : "NPCocoaEventFocusChanged"),
                    (event->data.focus.hasFocus ? "Gained" : "Lost"));
            if (!event->data.focus.hasFocus) {
		AbortComposing(mPlugin->GetNPP(), mIMEHelper);
            }
        }
        break;

    case NPCocoaEventMouseMoved:
        fixedNSEvent = nsEventFromNPCocoaMouseClickEvent(event,
						 (ScintillaView *) wEditor);
        if (fixedNSEvent) {
            scintilla->MouseMove(fixedNSEvent);
        }
        break;

    case NPCocoaEventMouseEntered:
        fixedNSEvent = nsEventFromNPCocoaMouseClickEvent(event,
						 (ScintillaView *) wEditor);
        if (fixedNSEvent) {
            scintilla->MouseEntered(fixedNSEvent);
        }
        break;

    case NPCocoaEventMouseExited:
        fixedNSEvent = nsEventFromNPCocoaMouseClickEvent(event,
						 (ScintillaView *) wEditor);
        if (fixedNSEvent) {
            scintilla->MouseExited(fixedNSEvent);
        }
        break;

    case NPCocoaEventMouseDragged:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventMouseDragged\n");
        break;

    case NPCocoaEventKeyDown:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventKeyDown\n");
        break;

    case NPCocoaEventScrollWheel:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventScrollWheel\n");
        break;

    case NPCocoaEventTextInput:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventTextInput\n");
        break;

    case NPCocoaEventKeyUp:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventKeyUp\n");
        break;

    case NPCocoaEventFlagsChanged:
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventFlagsChanged\n");
        break;
        
    default:
        fprintf(stderr, "SciMoz::PlatformHandleEvent event %d\n", event->type);
        break;
    }
    return false;
}

/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(PRBool *_ret) {
    SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
    *_ret = wEditor && wMain && !isClosed;
    return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetVisible(PRBool *_ret) {
    SCIMOZ_CHECK_VALID("GetVisible");
    *_ret = wEditor != 0;
    return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::SetVisible(PRBool vis) {
    SCIMOZ_CHECK_VALID("SetVisible");
    return NS_OK;
}

/* void endDrop( ); */
NS_IMETHODIMP SciMoz::EndDrop() {
    SCIMOZ_CHECK_VALID("EndDrop");
    return NS_OK;
}

/* readonly attribute boolean inDragSession; */
NS_IMETHODIMP SciMoz::GetInDragSession(PRBool *_ret) {
    SCIMOZ_CHECK_VALID("GetInDragSession");
    *_ret = scintilla->inDragSession();
    return NS_OK;
}

/* readonly attribute boolean GetIsTracking; */
NS_IMETHODIMP SciMoz::GetIsTracking(PRBool *_ret) {
    SCIMOZ_CHECK_VALID("GetIsTracking");
    *_ret = scintilla->isTracking;
    return NS_OK;
}


