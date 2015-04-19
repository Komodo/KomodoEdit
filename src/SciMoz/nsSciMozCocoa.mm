/*
  Web pages for cocoa/mozilla info:

  https://wiki.mozilla.org/NPAPI:CocoaEventModel - 2011-01-18, Josh Aas & Anders Carlsson

  https://developer.mozilla.org/en-US/docs/Gecko_Plugin_API_Reference - general

  http://colonelpanic.net/2009/03/building-a-firefox-plugin-part-one/

  Don't bother with the FireBreath project -- offscreen NSViews
  require massive proxying of events, and I'm not seeing the events.

 */
#import "ScintillaView.h"

#import "plugin.h"
#import "nsSciMoz.h"

#import <Cocoa/Cocoa.h>

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif

#ifdef SCIMOZ_COCOA_DEBUG
static char *getClipStr(NPWindow *win, char *buf) {
  sprintf(buf, "x:%3d, y:%3d, w:%3d, h:%3d",
	  win->clipRect.left,
	  win->clipRect.top,
	  win->clipRect.right - win->clipRect.left,
	  win->clipRect.bottom - win->clipRect.top);
  return buf;
}

static bool differentClipRect(NPWindow *old, NPWindow *now) {
  return (old->clipRect.left != now->clipRect.left ||
          old->clipRect.right != now->clipRect.right ||
          old->clipRect.top != now->clipRect.top ||
          old->clipRect.bottom != now->clipRect.bottom);
}

static char *getRectStr(NPWindow *win, char *buf) {
  sprintf(buf, "x:%3d, y:%3d, w:%3d, h:%3d",
	  win->x,
	  win->y,
	  win->width,
	  win->height);
  return buf;
}

static bool differentWindowRect(NPWindow *old, NPWindow *now) {
  return (old->x != now->x ||
          old->y != now->y ||
          old->width != now->width ||
          old->height != now->height);
}

static char *getNSRectStr(NSRect rect, char *buf) {
  sprintf(buf, "x:%g, y:%g w:%g, h:%g",
	  rect.origin.x,
	  rect.origin.y,
	  rect.size.width,
	  rect.size.height);
  return buf;
}
#endif

// When we get a cliprect positioned at (0,0) and it has a width & height of 0,
// then it means we are hiding the plugin from view, otherwise we are either
// re-showing the plugin or re-sizing the plugin - bug 97395.
#define NPWINDOW_CLIP_HIDDEN(npwin) ((npwin->clipRect.bottom <= npwin->clipRect.top) || \
				                     (npwin->clipRect.right  <= npwin->clipRect.left))


/*-----------------------------------------------------------------------------
 * Timer helper class used to work around the disappering plugin issue.
 *---------------------------------------------------------------------------*/

@implementation SciMozVisibilityTimer

- (id) init: (void*) target
{
  self = [super init];
  if (self != nil)
  {
    mTarget = target;
  }
  mTimer = nil;
  return self;
}

/**
 * Start the timer - will call the timerFired method every n seconds. This two
 * step approach is needed because a native Obj-C class is required as target
 * for the timer.
 */
- (void) startTimer
{
  if (mTimer != nil) {
	[self stopTimer];
  }

  mTimer = [NSTimer scheduledTimerWithTimeInterval:0.5
	                target:self
	                selector:@selector(timerFired:)
	                userInfo:nil
	                repeats:YES];
}

/**
 * Stop the timer.
 */
- (void) stopTimer
{
  if (mTimer != nil) {
	[mTimer invalidate];
	mTimer = nil;
  }
}

/**
 * Timer callback - notify SciMoz that the timer has fired.
 */
- (void) timerFired: (NSTimer*) timer
{
  reinterpret_cast<SciMoz*>(mTarget)->VisibilityTimerCallback(timer);
}

@end

//--------------------------------------------------------------------------------------------------


void SciMoz::PlatformCreate(WinID) {
  SendEditor(SCI_USEPOPUP, FALSE, 0);
  SendEditor(SCI_SETFOCUS, FALSE, 0);
  // Note: The Scintilla RegisterNotifyCallback method is deprecated.
  scintilla->RegisterNotifyCallback((intptr_t)this, (SciNotifyFunc)SciMoz::NotifySignal);
}

void SciMoz::Resize() {
#ifdef SCIMOZ_COCOA_DEBUG
  char buf[80];
  fprintf(stderr, ">> SciMoz::Resize, wEditor:%p, wMain:%p\n", wEditor, wMain);
#endif

  // Get the bounds for plugin view.
  NSView *parentView = (NSView*)wMain;
  ScintillaView *scView = (ScintillaView *) wEditor;
#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "parent bounds: %s, child frame: %s\n",
	  getNSRectStr([parentView bounds], buf),
	  getNSRectStr([scView frame], &buf[40]));
#endif
  [scView setFrame:[parentView bounds]];
  scintilla->Resize();
#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "<< SciMoz::Resize, manually set scView frame to parent's bounds\n");
#endif
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
    PRUnichar ustr[2] = { static_cast <char16_t>(ch), '\0'};
    NS_ConvertUTF16toUTF8 utf8_str(ustr);
    scintilla->AddCharUTF(utf8_str.get(), utf8_str.Length(), false);
    return NS_OK;
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
    memset(&fPlatform.lastWindow, 0, sizeof(NPWindow));
#endif
    fPlatform.firstVisibilityRequest = true;
    portMain = NULL;
    fWindow = NULL;
    wEditor = NULL;
    wMain = NULL;

#if !defined(HEADLESS_SCIMOZ)
    visibilityTimer = [[SciMozVisibilityTimer alloc] init: this];
#endif

#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr,"<< SciMoz::PlatformNew\n");
#endif
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr,"SciMoz::PlatformDestroy wEditor %p scintilla %p\n", wEditor, scintilla);
#endif
    if (scintilla) {
        scintilla->SetIdle(false);
        scintilla->RegisterNotifyCallback(NULL, NULL);
        scintilla = NULL;
    }
    if (wEditor) {
        ScintillaView *scView = (ScintillaView *) wEditor;
        [scView setHidden:YES];
        [scView removeFromSuperview];
        // This must have reset out window.
        NS_PRECONDITION(portMain==NULL, "Should not be possible to destruct with a window!");
        [scView release];
        wEditor = NULL;
    }
    isClosed = 1;
    portMain = NULL;
    wMain = NULL;
    fWindow = NULL;
    [visibilityTimer stopTimer];
    [visibilityTimer release];
    return NS_OK;
 }


void SciMoz::PlatformMarkClosed() {
    scintilla->SetIdle(false);
    scintilla->RegisterNotifyCallback(NULL, NULL);
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
  char buf[400];
  fprintf(stderr,"SciMoz::PlatformSetWindow wEditor:%p npwindow:%p, fWindow:%p\n",
	  wEditor, npwindow, fWindow);
#endif
  if (!npwindow || !npwindow->window) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "  %s\n", npwindow ? "No npwindow->window" : "No npwindow???");
#endif
    if (!wEditor) {
      // Initialization of the plugin - no npwindow->window available yet.
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "    creating new scintilla view\n");
#endif
      NSRect winRect = NSMakeRect(0, 0, 200, 200); /* temporary size */
      ScintillaView *scView = [[[ScintillaView alloc] initWithFrame:winRect] autorelease];
      wEditor = [scView retain];
      scintilla = [scView backend];
#ifdef XP_MACOSX_USE_CORE_ANIMATION
      // Get Scintilla to use layer backed views (for core animation).
      [scView setWantsLayer: YES];
#endif
      Create(wEditor);
    }
    return NS_OK;
  }

  //NSView *currView = (NSView *) npwindow->window;
  // portMain points to npwindow->window
  // wMain points to the parent NSView
  // wEditor points to the current NSView
  if (fWindow) {
    // fWindow is set to npWindow from an earlier call.
    // What is the plugin trying to tell us this time?
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "\nSciMoz::PlatformSetWindow: %p fWindow already set\n", wEditor);
    fprintf(stderr, "  last clip: %s\n  curr clip: %s (changed: %d)\n  last rect: %s\n  curr rect: %s (changed %d)\n",
	    getClipStr(&fPlatform.lastWindow, buf),
	    getClipStr(npwindow, &buf[100]),
            differentClipRect(&fPlatform.lastWindow, npwindow),
	    getRectStr(&fPlatform.lastWindow, &buf[200]),
	    getRectStr(npwindow, &buf[300]),
            differentWindowRect(&fPlatform.lastWindow, npwindow));
    fprintf(stderr, "fWindow == npwindow: %d\n",
	    fWindow == npwindow);
#endif
    HideScintillaView(NPWINDOW_CLIP_HIDDEN(npwindow));

#ifdef SCIMOZ_COCOA_DEBUG
    // Remember the window information.
    fPlatform.lastWindow = *fWindow;
#endif

    return NS_OK;
  }

#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "Show npwindow->window:\n");
  fprintf(stderr, "  npwindow->window:%p\n", npwindow->window);
  fprintf(stderr, "  clipRect: %s, window:%s\n",
	  getClipStr(npwindow, &buf[0]),
	  getRectStr(npwindow, &buf[80]));
  wMain = (NSView *) npwindow->window;
  NSView *mainView = (NSView *) wMain;
  [(NSView *)mainView setAutoresizesSubviews: YES];
  [(NSView *)mainView setAutoresizingMask: NSViewWidthSizable | NSViewHeightSizable];
  fprintf(stderr, ("  notes on (NSView *) npwindow->window:\n"
		   "    flipped: %d, bounds:%s, frame:%s\n"),
	  [mainView isFlipped],
	  getNSRectStr([mainView bounds], &buf[0]),
	  getNSRectStr([mainView frame],  &buf[80]));
#endif

  // Tie the plugin to the given window and make it visible.
  assert(fWindow == NULL);
  assert(npwindow->window);
  assert(scintilla != NULL);
  // Position scView at its parent's origin.
  ScintillaView *scView = wEditor;
  if (!scView) {
#ifdef SCIMOZ_COCOA_DEBUG
    fprintf(stderr, "No memory for a ScintillaView\n");
#endif
    return NS_ERROR_FAILURE;
  }
  fWindow = npwindow;
  portMain = npwindow->window;
  wMain = (NSView *)npwindow->window;
  [(NSView *)wMain addSubview:scView];

  [scView setAutoresizesSubviews: YES];
  [scView setAutoresizingMask: NSViewWidthSizable | NSViewHeightSizable];

  Resize();

  //fprintf(stderr, "<< SciMoz::PlatformSetWindow\n");
  return NS_OK;
}

void SciMoz::VisibilityTimerCallback(NSTimer *timer) {
  //
  ScintillaView *scView = (ScintillaView *) wEditor;

  if ([scView isHidden]) {
	[visibilityTimer stopTimer];
#ifdef SCIMOZ_COCOA_DEBUG
	fprintf(stderr, "VisibilityTimerCallback:: hidden view, stopping timer %p\n", this);
#endif

  } else {
	[scView setHidden:YES];
	[scView setHidden:NO];
#ifdef SCIMOZ_COCOA_DEBUG
	fprintf(stderr, "VisibilityTimerCallback:: toggled visibility %p\n", this);
#endif
  }
}

void SciMoz::HideScintillaView(bool hide) {
  ScintillaView *scView = (ScintillaView *) wEditor;
#ifdef SCIMOZ_COCOA_DEBUG
  fprintf(stderr, "HideScintillaView: hide:%d, isHidden:%d, firstVisibilityRequest:%d\n",
	  hide, [scView isHidden], fPlatform.firstVisibilityRequest);
#endif
    
  if (hide) {
	[visibilityTimer stopTimer];
    scintilla->SetIdle(false);
    if (![scView isHidden]) {
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "    hiding scView\n");
#endif
      [scView setHidden:YES];
    }
  } else {
    scintilla->SetIdle(true);
    if ([scView isHidden]) {
	  if (mPluginVisibilityHack) {
		[visibilityTimer startTimer];
	  }
      // Make Scintilla visible.
      [scView setHidden:NO];
#ifdef SCIMOZ_COCOA_DEBUG
      fprintf(stderr, "    unhiding scView\n");
#endif
    } else if (fPlatform.firstVisibilityRequest) {
      // Necessary hack to ensure the view will become visible - bug 97801.
      [scView setHidden:YES];
      [scView setHidden:NO];
      fPlatform.firstVisibilityRequest = false;
    }
  }
}

nsresult SciMoz::PlatformResetWindow() {
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


static bool hasEmptyRect(NPCocoaEvent *event) {
  return !event->data.draw.width && !event->data.draw.height;
}

int16 SciMoz::PlatformHandleEvent(void *ev) {
    if (isClosed) {
#ifdef SCIMOZ_COCOA_DEBUG
        fprintf(stderr, "SciMoz is getting an event after being closed.\n");
#endif
        return kNPEventNotHandled;
    }
#ifdef SCIMOZ_COCOA_DEBUG
    NPCocoaEvent *event = (NPCocoaEvent *) ev;
    if (event->type != NPCocoaEventMouseMoved)
        fprintf(stderr, "PlatformHandleEvent: event #%d\n", event->type);
#endif

    return kNPEventNotHandled;
}

#ifdef XP_MACOSX_USE_CORE_ANIMATION
void * SciMoz::GetCoreAnimationLayer() {
  if (wEditor) {
    ScintillaView *scView = (ScintillaView *) wEditor;
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


