/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

#ifndef __nsSciMoz_h__
#define __nsSciMoz_h__

#include <stdio.h> 
#include <string.h> 

//#define SCIMOZ_DEBUG
//#define SCIDEBUG_REFS

#ifdef _WINDOWS
// with optimizations on, we crash "somewhere" in this file in a release build
// when we drag from scintilla into mozilla, over an tree
// komodo bugzilla bug 19186
// #pragma optimize("", off)
#else
#ifndef XP_MACOSX
#include <gdk/gdkx.h>
#include <gdk/gdkprivate.h> 
#include <gtk/gtk.h> 
#include <gdk/gdkkeysyms.h>
#include <gtk/gtksignal.h>

#ifdef GTK2
#include <gtk/gtkplug.h>
#else
#include <gtkmozbox.h>
#endif

/* Xlib/Xt stuff */
#ifdef MOZ_X11
#include <X11/Xlib.h>
#include <X11/Intrinsic.h>
#include <X11/cursorfont.h>
#endif
#endif
#endif 

/**
 * {3849EF46-AE99-45f7-BF8A-CC4B053A946B}
 */
#define SCI_MOZ_CID { 0x3849ef46, 0xae99, 0x45f7, { 0xbf, 0x8a, 0xcc, 0x4b, 0x5, 0x3a, 0x94, 0x6b } }
#define SCI_MOZ_PROGID "@mozilla.org/inline-plugin/application/x-scimoz-plugin"

#include "nscore.h"
#include "nsObserverList.h"
#include "nsObserverService.h"
#include <nsIConsoleService.h>

#include "nsCOMPtr.h"
#include "nsIServiceManager.h"
#include "nsISupports.h"
#include "nsIGenericFactory.h"
#include "nsString.h"
#include "nsIAllocator.h"
#include "nsIDOMWindowInternal.h"
#include "nsWeakReference.h"
#include "nsIObserverService.h"
#include "nsILocalFile.h"
#include "nsIProgrammingLanguage.h"

#include "ISciMoz.h"
#include "ISciMozEvents.h"
#include "nsIClassInfo.h"

#ifdef _WINDOWS
#include <windows.h>
#include <shellapi.h>
#include <richedit.h>
#undef FindText // conflicts with our definition of that name!
#endif

#ifdef XP_MACOSX
#include <Platform.h>
#include <ScintillaMacOSX.h>
#endif
#include <Scintilla.h>
#include "sendscintilla.h"
#include <SciLexer.h>

#define SCIMAX(a, b) (a > b ? a : b)
#define SCIMIN(a, b) (a < b ? a : b)
#define LONGFROMTWOSHORTS(a, b) ((a) | ((b) << 16))

// XXX also defined in ScintillaWin.cxx
#ifndef WM_UNICHAR
#define WM_UNICHAR                      0x0109
#endif


#include "SciMozEvents.h"

class nsPluginInstance;

// We must implement nsIClassInfo because it signals the
// Mozilla Security Manager to allow calls from JavaScript.

class nsClassInfoMixin : public nsIClassInfo
{
  // These flags are used by the DOM and security systems to signal that 
  // JavaScript callers are allowed to call this object's scritable methods.
  NS_IMETHOD GetFlags(PRUint32 *aFlags)
    {*aFlags = nsIClassInfo::PLUGIN_OBJECT | nsIClassInfo::DOM_OBJECT;
     return NS_OK;}
  NS_IMETHOD GetImplementationLanguage(PRUint32 *aImplementationLanguage)
    {*aImplementationLanguage = nsIProgrammingLanguage::CPLUSPLUS;
     return NS_OK;}
  // The rest of the methods can safely return error codes...
  NS_IMETHOD GetInterfaces(PRUint32 * /*count*/, nsIID * ** /*array*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetHelperForLanguage(PRUint32 /*language*/, nsISupports ** /*_retval*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetContractID(char * * /*aContractID*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassDescription(char * * /*aClassDescription*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassID(nsCID * * /*aClassID*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
  NS_IMETHOD GetClassIDNoAlloc(nsCID * /*aClassIDNoAlloc*/)
    {return NS_ERROR_NOT_IMPLEMENTED;}
};

#ifdef XP_PC
static const char* gInstanceLookupString = "instance->pdata";

typedef struct _PlatformInstance {
	WNDPROC	fDefaultWindowProc;
	WNDPROC fDefaultChildWindowProc;
}
PlatformInstance;
#endif 

#if defined(XP_UNIX) && !defined(XP_MACOSX)
typedef struct _PlatformInstance {
	NPSetWindowCallbackStruct *ws_info;
	GtkWidget *moz_box;
}
PlatformInstance;
#define PLAT_GTK 1
#include "ScintillaWidget.h"
#endif 

#if defined(XP_MAC) || defined(XP_MACOSX)
#include <Carbon/Carbon.h>
typedef struct _PlatformInstance {
	WindowPtr	container;
	CGrafPtr    port;
}
PlatformInstance;
#endif

class SciMoz : public ISciMoz,
               public nsClassInfoMixin,
               public nsSupportsWeakReference
               
{
private:
    long _lastCharCodeAdded;
    long _ySlop;
    
    // brace match support
    long bracesStyle;
    long bracesCheck;
    bool bracesSloppy;
    
    bool FindMatchingBracePosition(int &braceAtCaret, int &braceOpposite, bool sloppy);
    void BraceMatch();
    
public:
  SciMoz(nsPluginInstance* plugin);
  ~SciMoz();

#ifdef SCIDEBUG_REFS
public:
  int getRefCount() { return mRefCnt.get(); }
#endif
protected: 
    NPWindow* fWindow;
//    nsPluginMode fMode;
    PlatformInstance fPlatform;

    void *portMain;	// Native window in portable type
    WinID wMain;	// portMain cast into a native type
    WinID wEditor;
    WinID wParkingLot;  // temporary parent window while not visible.

#ifdef USE_SCIN_DIRECT	
    SciFnDirect fnEditor;
    long ptrEditor;
#endif

    bool initialised;
    bool parked;
    int width;
    int height;
    EventListeners listeners;
    nsCOMPtr<nsIDOMWindowInternal> commandUpdateTarget;
    PRBool bCouldUndoLastTime;
    PRBool bCouldRedoLastTime;

    long SendEditor(unsigned int Msg, unsigned long wParam = 0, long lParam = 0);

    void Create(WinID hWnd);
    void PlatformCreate(WinID hWnd);
    void Notify(long lParam);
    void Resize();
    NS_IMETHOD _DoButtonUpDown(PRBool up, PRInt32 x, PRInt32 y, PRUint16 button, PRUint64 timeStamp, PRBool bShift, PRBool bCtrl, PRBool bAlt);

#ifdef XP_MACOSX
	void SetHIViewShowHide(bool disabled);
	static void NotifySignal(sptr_t *ThisPtr, long param);
	Scintilla::ScintillaMacOSX *scintilla;
#endif
#ifdef XP_PC
    void LoadScintillaLibrary();
#endif

    // IME support
    int imeStartPos;
    bool imeComposing;
    bool imeActive;
    nsString mIMEString;
    void StartCompositing();
    void EndCompositing();
public:
  nsString name;
  // native methods callable from JavaScript
  NS_DECL_ISUPPORTS
  NS_DECL_ISCIMOZLITE
  NS_DECL_ISCIMOZ

  void SetInstance(nsPluginInstance* plugin);

    void PlatformNew(void);

    // Destroy is always called as we destruct.
    nsresult PlatformDestroy(void);

    // SetWindow is called as Mozilla gives us a window object.
    // If we are doing "window parking", we can attach
    // our existing Scintilla to the new Moz window.
    nsresult PlatformSetWindow(NPWindow* window);

    // ResetWindow is called as the Mozilla window dies.
    // If we are doing "window parking", this is when we park.
    // Will also be called if Moz ever hands us a new window
    // while we already have one.
    nsresult PlatformResetWindow();

    PRInt16 PlatformHandleEvent(void* event);

//    void SetMode(nsPluginMode mode) { fMode = mode; }

#ifdef XP_PC
    static LRESULT CALLBACK WndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK ParkingLotWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    static LRESULT CALLBACK ChildWndProc(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
#endif 

#if defined(XP_UNIX) && !defined(XP_MACOSX)
    int sInGrab;
    static void NotifySignal(GtkWidget *, gint wParam, gpointer lParam, SciMoz *scimoz);
#endif 

protected:
  nsPluginInstance* mPlugin;
};

// We use our own timeline macros so they can be switch on independently.
#include "nsITimelineService.h"
#if !defined(MOZ_TIMELINE) && defined (SCIMOZ_TIMELINE)
#undef SCIMOZ_TIMELINE
#endif

#if defined (SCIMOZ_TIMELINE)

#define SCIMOZ_TIMELINE_MARK NS_TIMELINE_MARK
// NS_TIMELINE_MARKV is wrong!
#define SCIMOZ_TIMELINE_MARKV NS_TimelineMark
#define SCIMOZ_TIMELINE_INDENT NS_TIMELINE_INDENT
#define SCIMOZ_TIMELINE_OUTDENT NS_TIMELINE_OUTDENT
#define SCIMOZ_TIMELINE_ENTER NS_TIMELINE_ENTER
#define SCIMOZ_TIMELINE_LEAVE NS_TIMELINE_LEAVE
#define SCIMOZ_TIMELINE_START_TIMER NS_TIMELINE_START_TIMER
#define SCIMOZ_TIMELINE_STOP_TIMER NS_TIMELINE_STOP_TIMER
#define SCIMOZ_TIMELINE_MARK_TIMER NS_TIMELINE_MARK_TIMER
#define SCIMOZ_TIMELINE_RESET_TIMER NS_TIMELINE_RESET_TIMER
#define SCIMOZ_TIMELINE_MARK_TIMER1 NS_TIMELINE_MARK_TIMER1

#else
#define SCIMOZ_TIMELINE_MARK(text)
#define SCIMOZ_TIMELINE_MARKV(args)
#define SCIMOZ_TIMELINE_INDENT()
#define SCIMOZ_TIMELINE_OUTDENT()
#define SCIMOZ_TIMELINE_START_TIMER(timerName)
#define SCIMOZ_TIMELINE_STOP_TIMER(timerName)
#define SCIMOZ_TIMELINE_MARK_TIMER(timerName)
#define SCIMOZ_TIMELINE_RESET_TIMER(timerName)
#define SCIMOZ_TIMELINE_MARK_TIMER1(timerName, str)
#define SCIMOZ_TIMELINE_ENTER(text)
#define SCIMOZ_TIMELINE_LEAVE(text)
#define SCIMOZ_TIMELINE_MARK_URI(text, uri)
#define SCIMOZ_TIMELINE_MARK_FUNCTION(timer)
#define SCIMOZ_TIMELINE_TIME_FUNCTION(timer)
#define SCIMOZ_TIMELINE_MARK_CHANNEL(text, channel)
#define SCIMOZ_TIMELINE_MARK_LOADER(text, loader);
#endif // defined (SCIMOZ_TIMELINE)

#endif

