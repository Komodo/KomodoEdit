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

#ifndef __nsSciMoz_h__
#define __nsSciMoz_h__

#include <stdio.h> 
#include <string.h> 

//#define SCIMOZ_DEBUG
//#define SCIMOZ_DEBUG_VERBOSE
//#define SCIMOZ_DEBUG_VERBOSE_VERBOSE
//#define SCIMOZ_COCOA_DEBUG
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

#include <gtk/gtkplug.h>

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
#include "nsStringGlue.h"
#include "nsMemory.h"
#include "nsIDOMWindow.h"
#include "nsWeakReference.h"
#include "nsIObserverService.h"
#include "nsILocalFile.h"
#include "nsIProgrammingLanguage.h"

#include "ISciMoz.h"
#include "ISciMozEvents.h"
#include "nsIClassInfo.h"

#include "npapi_utils.h"

#ifdef _WINDOWS
#include <windows.h>
#include <shellapi.h>
#include <richedit.h>
#undef FindText // conflicts with our definition of that name!
#endif

#ifdef XP_MACOSX
#ifndef HEADLESS_SCIMOZ
#import <Cocoa/Cocoa.h>
#endif
#endif

#include <Scintilla.h>
#include "sendscintilla.h"
#include <SciLexer.h>

#ifdef XP_MACOSX
#ifndef HEADLESS_SCIMOZ
#include <Platform.h>
#include <ScintillaView.h>
#include <ScintillaCocoa.h>
#endif
#endif

#define SCIMAX(a, b) (a > b ? a : b)
#define SCIMIN(a, b) (a < b ? a : b)
#define LONGFROMTWOSHORTS(a, b) ((a) | ((b) << 16))

// XXX also defined in ScintillaWin.cxx
#ifndef WM_UNICHAR
#define WM_UNICHAR                      0x0109
#endif

// Mozilla 31 uses C++11 character types.
#if MOZ_VERSION > 2499
#define PRUnichar char16_t
#endif

/* Thread checks are default in dev builds, off in release */

#if BUILD_FLAVOUR == dev

#include "nsThreadUtils.h"
#define IS_MAIN_THREAD() NS_IsMainThread()

#define SCIMOZ_CHECK_THREAD(method, result) \
    if (!IS_MAIN_THREAD()) { \
	fprintf(stderr, "SciMoz::" method " was called on a thread\n"); \
	return result; \
    }

#else
#define SCIMOZ_CHECK_THREAD(method, result)
#endif // # if BUILD_FLAVOUR

// Ensure that SciMoz has not been closed. Bug 82032.
#define SCIMOZ_CHECK_ALIVE(method, result) \
    if (isClosed) { \
	fprintf(stderr, "SciMoz::" method " used when closed!\n"); \
	return result; \
    }

#define SCIMOZ_CHECK_VALID(method) \
    SCIMOZ_CHECK_THREAD(method, NS_ERROR_FAILURE) \
    SCIMOZ_CHECK_ALIVE(method, NS_ERROR_FAILURE)


#include "SciMozEvents.h"

class SciMozPluginInstance;

#if defined(HEADLESS_SCIMOZ)
// Dummy platform holder.
typedef struct _PlatformInstance {
	void *foo;
}
PlatformInstance;

#else

#ifdef XP_PC
static const char* gInstanceLookupString = "instance->pdata";

typedef struct _PlatformInstance {
	WNDPROC	fDefaultWindowProc;
	WNDPROC fDefaultChildWindowProc;
	int width;
	int height;
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

#if defined(XP_MACOSX)
#include <Cocoa/Cocoa.h>
typedef struct _PlatformInstance {
    bool       firstVisibilityRequest;
#ifdef SCIMOZ_COCOA_DEBUG
    NPWindow   lastWindow;
#endif
}
PlatformInstance;

/**
 * Helper class to be used as timer target (NSTimer).
 */
@interface SciMozVisibilityTimer: NSObject
{
  void* mTimer;
  void* mTarget;
}
- (id) init: (void*) target;
- (void) startTimer;
- (void) stopTimer;
- (void) timerFired: (NSTimer*) timer;
@end

#endif

#endif  // else not HEADLESS_SCIMOZ

class SciMoz : public ISciMoz,
               public ISciMoz_Part0,
               public ISciMoz_Part1,
               public ISciMoz_Part2,
               public ISciMoz_Part3,
               public ISciMoz_Part4,
               public nsSupportsWeakReference
               
{
private:
    // Used to cache the "text" property - increments when the buffer changes.
    int16_t _scimozId;
    int16_t _textId;
    // Last line count gets updated whenever the text is changed.
    long mLastLineCount;
    // Setting for plugin visibility on Cocoa platform.
    bool mPluginVisibilityHack;

    void DefaultSettings();

    // brace match support
    long bracesStyle;
    long bracesCheck;
    bool bracesSloppy;
    
    bool FindMatchingBracePosition(int &braceAtCaret, int &braceOpposite, bool sloppy);
    void BraceMatch();
    
public:
#if defined(HEADLESS_SCIMOZ)
  SciMoz();
#endif
  SciMoz(SciMozPluginInstance* plugin);

protected: 
    virtual ~SciMoz();
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
    bool isClosed;      // If the plugin was removed... Scintilla was destroyed.
    bool parked;
    int width;
    int height;
    EventListeners listeners;
    bool bCouldUndoLastTime;
    bool bCouldRedoLastTime;

    long SendEditor(unsigned int Msg, unsigned long wParam = 0, long lParam = 0);
    NS_IMETHODIMP ConvertUTF16StringSendMessage(int message, PRInt32 length, const PRUnichar *text, PRInt32  *_retval);

    void SciMozInit();  // Shared initialization code.
    void Create(WinID hWnd);
    void PlatformCreate(WinID hWnd);
    void Notify(long lParam);
    void Resize();
    NS_IMETHOD _DoButtonUpDown(bool up, PRInt32 x, PRInt32 y, PRUint16 button, bool bShift, bool bCtrl, bool bAlt);

#ifdef XP_MACOSX
#ifndef HEADLESS_SCIMOZ
	void HideScintillaView(bool disabled);
	static void NotifySignal(intptr_t windowid, unsigned int iMessage, uintptr_t wParam, uintptr_t lParam);
	Scintilla::ScintillaCocoa *scintilla;
#endif
#endif
#if defined(_WINDOWS) && !defined(HEADLESS_SCIMOZ)
    void LoadScintillaLibrary();
#endif

public:
  nsString name;
  // native methods callable from JavaScript
  NS_DECL_ISUPPORTS
  NS_DECL_ISCIMOZLITE
  NS_DECL_ISCIMOZ
  NS_DECL_ISCIMOZ_PART0
  NS_DECL_ISCIMOZ_PART1
  NS_DECL_ISCIMOZ_PART2
  NS_DECL_ISCIMOZ_PART3
  NS_DECL_ISCIMOZ_PART4

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

    // Notify that scimoz was closed.
    void PlatformMarkClosed(void);

#ifdef XP_MACOSX
#ifndef HEADLESS_SCIMOZ
    SciMozVisibilityTimer *visibilityTimer;
    void VisibilityTimerCallback(NSTimer *timer);
#endif
#endif

#ifdef XP_MACOSX_USE_CORE_ANIMATION
    void *GetCoreAnimationLayer();
#endif

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

    // Shared XPCOM/NPRuntime methods.
    nsresult _GetStyleBuffer(PRInt32 min, PRInt32 max, PRUint16 *buffer);

    // NPRuntime support
    static void SciMozInitNPIdentifiers();
    bool HasProperty(NPIdentifier name);
    bool GetProperty(NPIdentifier name, NPVariant *result);
    bool SetProperty(NPIdentifier name, const NPVariant *value);
    bool HasMethod(NPIdentifier name);
    bool Invoke(NPP instance, NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result);

    // NPRuntime custom methods
    #define NPRUNTIME_CUSTOM_METHOD(x) \
	bool x(const NPVariant *args, uint32_t argCount, NPVariant *result)

    NPRUNTIME_CUSTOM_METHOD(UpdateMarginWidths);
    NPRUNTIME_CUSTOM_METHOD(DoBraceMatch);
    NPRUNTIME_CUSTOM_METHOD(EnablePluginVisibilityHack);
    NPRUNTIME_CUSTOM_METHOD(MarkClosed);
    NPRUNTIME_CUSTOM_METHOD(HookEvents);
    NPRUNTIME_CUSTOM_METHOD(UnhookEvents);
    NPRUNTIME_CUSTOM_METHOD(GetStyledText);
    NPRUNTIME_CUSTOM_METHOD(GetStyleRange);
    NPRUNTIME_CUSTOM_METHOD(GetCurLine);
    NPRUNTIME_CUSTOM_METHOD(GetLine);
    NPRUNTIME_CUSTOM_METHOD(AssignCmdKey);
    NPRUNTIME_CUSTOM_METHOD(ClearCmdKey);
    NPRUNTIME_CUSTOM_METHOD(GetTextRange);
    NPRUNTIME_CUSTOM_METHOD(CharPosAtPosition);
    NPRUNTIME_CUSTOM_METHOD(SendUpdateCommands);
    NPRUNTIME_CUSTOM_METHOD(GetWCharAt);

    NPRUNTIME_CUSTOM_METHOD(AddChar);
    NPRUNTIME_CUSTOM_METHOD(ButtonDown);
    NPRUNTIME_CUSTOM_METHOD(ButtonUp);
    NPRUNTIME_CUSTOM_METHOD(ButtonMove);
    NPRUNTIME_CUSTOM_METHOD(EndDrop);
    NPRUNTIME_CUSTOM_METHOD(AnnotationRemoveAtLine);
    NPRUNTIME_CUSTOM_METHOD(MarkerDefineRGBAImage);

    #undef NPRUNTIME_CUSTOM_METHOD
protected:
  SciMozPluginInstance* mPlugin;
  friend class SciMozPluginInstance;
};

#endif

