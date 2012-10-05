/*
  Web pages for cocoa/mozilla info:

  https://wiki.mozilla.org/NPAPI:CocoaEventModel - 2011-01-18, Josh Aas & Anders Carlsson

  https://developer.mozilla.org/en-US/docs/Gecko_Plugin_API_Reference - general

  http://colonelpanic.net/2009/03/building-a-firefox-plugin-part-one/

  Don't bother with the FireBreath project -- offscreen NSViews
  require massive proxying of events, and I'm not seeing the events.

 */
#import "plugin.h"
#import "nsSciMoz.h"

#import <Cocoa/Cocoa.h>

#import "ScintillaView.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

#ifdef SCIMOZ_COCOA_DEBUG
static char *getClipStr(NPWindow *win, char *buf) {
  sprintf(buf, "l:%d, t:%d, r:%d, b:%d",
	  win->clipRect.left,
	  win->clipRect.top,
	  win->clipRect.right,
	  win->clipRect.bottom);
  return buf;
}
#endif

#ifdef SCIMOZ_COCOA_DEBUG
static char *getRectStr(NPWindow *win, char *buf) {
  sprintf(buf, "x:%d, y:%d w:%d, h:%d",
	  win->x,
	  win->y,
	  win->width,
	  win->height);
  return buf;
}
#endif

#ifdef SCIMOZ_COCOA_DEBUG
static char *getNSRectStr(NSRect rect, char *buf) {
  sprintf(buf, "x:%g, y:%g w:%g, h:%g",
	  rect.origin.x,
	  rect.origin.y,
	  rect.size.width,
	  rect.size.height);
  return buf;
}
#endif

#define WINDOW_DISABLED(a) (!a || \
				  (a->clipRect.bottom <= a->clipRect.top && \
				   a->clipRect.right  <= a->clipRect.left))

void SciMoz::PlatformCreate(WinID) {
}

void SciMoz::Resize() {
  // NSMakeRect(origin.x, origin.y, width, height)
#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, ">> SciMoz::Resize, fWindow:%p\n", fPlatform.container);
  fprintf(stderr, "<< SciMoz::Resize, do nothing\n");
  //  ScintillaView *scView = (ScintillaView *) wEditor;
  //scintilla->Resize();
  return;
#endif
  // Get the bounds for fPlatform.container
  NSView *parentView = (NSView*)(fWindow->window);
  // NSView *parentView = [(NSWindow*)(fPlatform.container)];
  NSRect parentRect = [parentView bounds];
#ifdef SCIMOZ_COCOA_DEBUG
  char buf[30];
  fprintf(stderr, "SciMoz::Resize fWindow.clipRect: %s\n",
	  getClipStr(fWindow, buf));
  fprintf(stderr, "parent bounds: %s\n",
	  getNSRectStr(parentRect, buf));
  fprintf(stderr, "parent frame: %s\n",
	  getNSRectStr([parentView frame], buf));
#endif
  NSRect boundsRect = NSMakeRect(fWindow->clipRect.left,
				 parentRect.size.height - fWindow->clipRect.bottom,
				 fWindow->clipRect.right - fWindow->clipRect.left,
				 fWindow->clipRect.bottom - fWindow->clipRect.top);
  ScintillaView *scView = (ScintillaView *) wEditor;
  [scView setFrame:boundsRect];
  SetHIViewShowHide(WINDOW_DISABLED(fWindow));
}

static NSEvent *SynthesizeEvent(bool up, PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt, WinID wEditor) {
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

NS_IMETHODIMP SciMoz::_DoButtonUpDown(bool up, PRInt32 x, PRInt32 y,
                                      PRUint16 button, bool bShift,
                                      bool bCtrl, bool bAlt) {
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
extern NSObject* scintilla_new(void);
}

void SciMoz::NotifySignal(intptr_t windowid, unsigned int iMessage, uintptr_t wParam, uintptr_t lParam) {
    if (iMessage == WM_NOTIFY) {
        SciMoz *s = reinterpret_cast<SciMoz *>(windowid);
        s->Notify(lParam);
    }
}

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr,">> SciMoz::PlatformNew\n");
#endif
    fPlatform.container = NULL;
    portMain = NULL;
    fWindow = NULL;
    wEditor = NULL;
    wMain = NULL;
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr,"<< SciMoz::PlatformNew\n");
#endif
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr,"SciMoz::PlatformDestroy wEditor %p scintilla %p\n", wEditor, scintilla);
#endif
    if (scintilla) {
        scintilla->unregisterNotifyCallback();
    }
    if (wEditor) {
        PlatformResetWindow();
        // This must have reset out window.
        NS_PRECONDITION(portMain==0, "Should not be possible to destruct with a window!");
        [(ScintillaView *) wEditor release];
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

nsresult SciMoz::PlatformSetWindow(NPWindow* npwindow) {
#ifdef SCIMOZ_COCOA_DEBUG
  char buf[160];
  fprintf(stderr,"SciMoz::PlatformSetWindow wEditor:%p npwindow:%p, fWindow:%p\n",
	  wEditor, npwindow, fWindow);
#endif
  if (!npwindow || !npwindow->window) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "SciMoz::PlatformSetWindow, called with %s, do nothing\n",
	    npwindow ? "No npwindow->window" : "No npwindow???");
#endif
    SetHIViewShowHide(true);
    return NS_OK;
  }

  //NSView *currView = (NSView *) npwindow->window;
  // portMain and fPlatform.container both point to the NSWindow
  // wMain points to the parent NSView
  // wEditor points to the current NSView
  if (fWindow) {
    // fWindow is set to npWindow from an earlier call.
    // What is the plugin trying to tell us this time?
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "SciMoz::PlatformSetWindow: fWindow already set\n");
    fprintf(stderr, "portMain  == npwindow->window, \n    fWindow clip: %s, current: %s, fWindow rect:%s, current:%s\n",
	    getClipStr(fWindow, buf),
	    getClipStr(npwindow, &buf[40]),
	    getRectStr(fWindow, &buf[80]),
	    getRectStr(npwindow, &buf[120]));
    fprintf(stderr, "portMain == npwindow->window: %d\n",
	    portMain == npwindow->window);
#endif
    if (portMain == npwindow->window) {
      // Has the clipRect changed so we should display the window?
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "....have fWindow, call show/hide (%d,%d,%d,%d)\n", 
	      fWindow->clipRect.left, fWindow->clipRect.top, 
	      fWindow->clipRect.right, fWindow->clipRect.bottom);
#endif
      SetHIViewShowHide(WINDOW_DISABLED(fWindow));
      return NS_OK;
    }
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "**************** calling reset window\n");
#endif
    SetHIViewShowHide(true);
    PlatformResetWindow();
  }

#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "Show npwindow->window:\n");
  fprintf(stderr, "  npwindow->window:%p\n", npwindow->window);
  fprintf(stderr, "  clipRect: %s, window:%s\n",
	  getClipStr(npwindow, &buf[0]),
	  getRectStr(npwindow, &buf[80]));
  wMain = (NSView *) npwindow->window;
  NSView *mainView = (NSView *) wMain;
  fprintf(stderr, ("  notes on (NSView *) npwindow->window:\n"
		   "    flipped: %d, bounds:%s, frame:%s\n"),
	  [mainView isFlipped],
	  getNSRectStr([mainView bounds], &buf[0]),
	  getNSRectStr([mainView frame],  &buf[80]));
#endif
  if (npwindow->width && npwindow->height) {
    NSRect winRect = NSMakeRect(npwindow->x, npwindow->y, // temp 0
			  npwindow->width, npwindow->height);
    // No, position scView at its parent's origin.
    winRect = NSMakeRect(0, 0,
			 npwindow->width, npwindow->height);
    ScintillaView *scView = [[[ScintillaView alloc]initWithFrame: winRect] autorelease];
    if (!scView) {
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "No memory for a ScintillaView\n");
#endif
      return NS_OK;
    }

    [scView setHidden: YES];
    scintilla = [scView backend];
    assert(scintilla != NULL);
    if (wEditor) {
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "OK, we have an unhooked scintillaView object\n");
#endif
    }
    fWindow = npwindow;
    fPlatform.container = (NSView *) npwindow->window;
    portMain = npwindow->window;
    wEditor = scView;
    wMain = (NSView *) npwindow->window;
    Create(wEditor);
    SetHIViewShowHide(WINDOW_DISABLED(fWindow));
    SendEditor(SCI_USEPOPUP, FALSE, 0);
    SendEditor(SCI_SETFOCUS, FALSE, 0);
    scintilla->RegisterNotifyCallback((intptr_t)this, (SciNotifyFunc)SciMoz::NotifySignal);
  }
  return NS_OK;
}

void SciMoz::SetHIViewShowHide(bool disable) {
  fprintf(stderr, ">>SciMoz::SetHIViewShowHide(disable:%d)\n", disable);
  ScintillaView *scView = (ScintillaView *) wEditor;
    bool isVisible = ![scView isHidden];
#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "SetHIViewShowHide: disabled:%d\n", disable);
  fprintf(stderr, "SetHIViewShowHide: isVisible:%d\n", isVisible);
#endif
    
  if (disable) {
    if (isVisible) {
      scintilla->SetTicking(false);
      [scView setNeedsDisplay:YES];
      //gone: HIViewSetDrawingEnabled(scView, false);
      [scView setHidden:YES];
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "Remove scView from superview\n");
#endif
      [scView removeFromSuperview];
      scintilla->Resize();
    }
  } else {
    if (!isVisible) {
      [scView setHidden:NO];
#ifdef SCIMOZ_COCOA_DEBUG
      //fprintf(stderr, "-[((NSView *) wMain) addSubview:scView]\n");
#endif
      //[((NSView *) wMain) addSubview:scView];
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "-[scView setNeedsDisplay:YES]\n");
#endif
      [scView setNeedsDisplay:YES];
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "-scintilla->SetTicking(true)\n");
#endif
      scintilla->SetTicking(true);
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "-wMain = fPlatform.container;\n");
#endif
      wMain = fPlatform.container;
      if (wMain) {
#ifdef SCIMOZ_COCOA_DEBUG
	fprintf(stderr, "-[(NSView *)wMain:%p addSubview:scView];\n", wMain);
#endif
	[(NSView *)wMain addSubview:scView];
	[(NSView *)wMain setAutoresizesSubviews: YES];
	[(NSView *)wMain setAutoresizingMask: NSViewWidthSizable | NSViewHeightSizable];
	[scView setAutoresizesSubviews: YES];
	[scView setAutoresizingMask: NSViewWidthSizable | NSViewHeightSizable];
#ifdef SCIMOZ_COCOA_DEBUG
	//fprintf(stderr, "-Resize()\n");
#endif
	Resize();
#ifdef SCIMOZ_COCOA_DEBUG
	//fprintf(stderr, "-scintilla->Resize()\n");
#endif
	scintilla->Resize();
      } else {
#ifdef SCIMOZ_COCOA_DEBUG
	fprintf(stderr, "fPlatform.container is null\n");
#endif
      }
    }
  }
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_COCOA_DEBUG
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
		   nullptr,
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


//#if 0
static bool hasEmptyRect(NPCocoaEvent *event) {
  return !event->data.draw.width && !event->data.draw.height;
}
//#endif

int16 SciMoz::PlatformHandleEvent(void *ev) {
    NPCocoaEvent *event = (NPCocoaEvent *) ev;
    NSEvent *fixedNSEvent;
    char buf[320];
	
    if (isClosed) {
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz is getting an event after being closed.\n");
#endif
        return kNPEventNotHandled;
    }
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "PlatformHandleEvent: event #%d\n", event->type);
#endif
    switch (event->type) {
    case NPCocoaEventDrawRect:
      fprintf(stderr, "NPCocoaEventDrawRect: draw-region: x:%g, y:%g, w:%g, h:%g\n",
	      event->data.draw.x,
	      event->data.draw.y,
	      event->data.draw.width,
	      event->data.draw.height);
      return kNPEventNotHandled;
      if (hasEmptyRect(event)) {
	fprintf(stderr, "Don't draw: empty rect\n");
	return kNPEventNotHandled;
      } else {
	ScintillaView *scView = (ScintillaView *) wEditor;
	if ([scView isHidden]) {
	  fprintf(stderr, "scView is still hidden\n");
	  SetHIViewShowHide(false);
	}
	NSView *parentView = (NSView*)wEditor;
#ifdef SCIMOZ_COCOA_DEBUG
	fprintf(stderr, "   But not going to handle the draw event here!\n");
	fprintf(stderr, ("  notes on (NSView *) npwindow->window:\n"
			 "    bounds:%s, frame:%s\n"),
	  getNSRectStr([parentView bounds], &buf[0]),
	  getNSRectStr([parentView frame],  &buf[80]));
#endif
	// Is fWindow->window == wEditor ?
	// NSView *parentView = [(NSWindow*)(fWindow->window) contentView];
	NSRect parentRect = [parentView bounds];
	fprintf(stderr, "  fWindow clip region: x:%d, y:%d (adj:%g), w:%d, h:%d\n",
			 fWindow->clipRect.left,
			 fWindow->clipRect.top,
			 parentRect.size.height - fWindow->clipRect.bottom,
			 fWindow->clipRect.right - fWindow->clipRect.left,
			 fWindow->clipRect.bottom - fWindow->clipRect.top);
	NSRect boundsRect = NSMakeRect(fWindow->clipRect.left,
				       parentRect.size.height - fWindow->clipRect.bottom,
				       fWindow->clipRect.right - fWindow->clipRect.left,
				       fWindow->clipRect.bottom - fWindow->clipRect.top);
	boundsRect = NSMakeRect(event->data.draw.x,
				event->data.draw.y,
				event->data.draw.width,
				event->data.draw.height);
	[scView drawRect:boundsRect];
	//[scView drawRect:[parentView bounds]];
      }
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
#ifdef SCIMOZ_COCOA_DEBUG
            bool windowFocusChanged = event->type == NPCocoaEventWindowFocusChanged;
            fprintf(stderr, "SciMozCocoa::PlatformHandleEvent: %s %s\n",
                    (windowFocusChanged
                     ? "NPCocoaEventWindowFocusChanged"
                     : "NPCocoaEventFocusChanged"),
                    (event->data.focus.hasFocus ? "Gained" : "Lost"));
#endif
            if (!event->data.focus.hasFocus) {
		AbortComposing(mPlugin->GetNPP(), mIMEHelper);
            } else {
	      // Make the parent the first responder.
	      [[(NSView *)fPlatform.container window] makeFirstResponder:(ScintillaView *) wMain];
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
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventMouseDragged\n");
#endif
        break;

    case NPCocoaEventKeyDown:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventKeyDown\n");
#endif
        break;

    case NPCocoaEventScrollWheel:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventScrollWheel\n");
#endif
        break;

    case NPCocoaEventTextInput:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventTextInput\n");
#endif
        break;

    case NPCocoaEventKeyUp:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventKeyUp\n");
#endif
        break;

    case NPCocoaEventFlagsChanged:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent NPCocoaEventFlagsChanged\n");
#endif
        break;
        
    default:
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz::PlatformHandleEvent event %d\n", event->type);
#endif
	return kNPEventNotHandled;
    }
    return kNPEventNotHandled;
    return kNPEventHandled;
}

#ifdef XP_MACOSX_USE_CORE_ANIMATION
void * SciMoz::GetCoreAnimationLayer() {
  if (wEditor) {
    ScintillaView *scView = (ScintillaView *) wEditor;
    [scView setWantsLayer: YES];
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, " GetCoreAnimationLayer:: layer: %p\n", [scView layer]);
#endif
    return [[scView layer] retain];
  }
  return nullptr;
}
#endif

/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(bool *_ret) {
    SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
    *_ret = wEditor && !isClosed;
    return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::GetVisible(bool *_ret) {
    SCIMOZ_CHECK_VALID("GetVisible");
    *_ret = wEditor != 0;
    return NS_OK;
}

/* attribute boolean visible */
NS_IMETHODIMP SciMoz::SetVisible(bool vis) {
    SCIMOZ_CHECK_VALID("SetVisible");
    return NS_OK;
}

/* void endDrop( ); */
NS_IMETHODIMP SciMoz::EndDrop() {
    SCIMOZ_CHECK_VALID("EndDrop");
    return NS_OK;
}

/* readonly attribute boolean inDragSession; */
NS_IMETHODIMP SciMoz::GetInDragSession(bool *_ret) {
    SCIMOZ_CHECK_VALID("GetInDragSession");
    *_ret = scintilla->inDragSession();
    return NS_OK;
}

/* readonly attribute boolean GetIsTracking; */
NS_IMETHODIMP SciMoz::GetIsTracking(bool *_ret) {
    SCIMOZ_CHECK_VALID("GetIsTracking");
    *_ret = scintilla->isTracking;
    return NS_OK;
}


