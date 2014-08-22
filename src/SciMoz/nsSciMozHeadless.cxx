/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

/**
 ** Implements a headless SciMoz (no UI), that can communicate with a headless
 ** scintilla.
 **
 ** Copyright 2013 by Todd Whiteman <toddw@activestate.com>
 **/

#include "nsSciMoz.h"
#include "ScintillaHeadless.h"
#include <mozilla/ModuleUtils.h>

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

void SciMoz::PlatformNew(void) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformNew\n");
#endif
    wEditor = scintilla_new();
}

nsresult SciMoz::PlatformDestroy(void) {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformDestroy\n");
#endif
	wEditor = 0;
	isClosed = 1;
	return NS_OK;
}

void SciMoz::PlatformMarkClosed() {
	// Nothing.
}

nsresult SciMoz::PlatformSetWindow(NPWindow* npwindow) {
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMoz::PlatformSetWindow:: npwindow %p\n", npwindow);
#endif
    return NS_OK;
}

nsresult SciMoz::PlatformResetWindow() {
#ifdef SCIMOZ_DEBUG
	fprintf(stderr,"SciMoz::PlatformResetWindow\n");
#endif
	return NS_OK;
}

int16 SciMoz::PlatformHandleEvent(void * /*event*/) {
	return 0;
}


/* readonly attribute boolean isOwned; */
NS_IMETHODIMP SciMoz::GetIsOwned(bool *_ret) {
	SCIMOZ_CHECK_THREAD("GetIsOwned", NS_ERROR_FAILURE);
	*_ret = wEditor && !isClosed;
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

SciMoz::SciMoz()
{
    SciMozInit();
}


/**
 * ISciMoz XPCOM bits.
 */


// {1d79ca08-3f1b-4e6c-b00d-39fdf36475b0}
#define SCIMOZHEADLESS_CID \
{ 0x1d79ca08, 0x3f1b, 0x4e6c, { 0xb0, 0x0d, 0x39, 0xfd, 0xf3, 0x64, 0x75, 0xb0 } }
#define SCIMOZHEADLESS_CONTRACTID "@activestate.com/ISciMozHeadless;1"

NS_GENERIC_FACTORY_CONSTRUCTOR(SciMoz)

NS_DEFINE_NAMED_CID(SCIMOZHEADLESS_CID);

static const mozilla::Module::CIDEntry kSciMozHeadlessCIDs[] = {
    { &kSCIMOZHEADLESS_CID, false, nullptr, SciMozConstructor },
    { nullptr }
};

static const mozilla::Module::ContractIDEntry kSciMozHeadlessContracts[] = {
    { SCIMOZHEADLESS_CONTRACTID, &kSCIMOZHEADLESS_CID },
    { nullptr }
};

static const mozilla::Module kScimozModule = {
    mozilla::Module::kVersion,
    kSciMozHeadlessCIDs,
    kSciMozHeadlessContracts,
    nullptr
};

NSMODULE_DEFN(nsSciMozModule) = &kScimozModule;
