// Scintilla source code edit control
// ScintillaHeadless.cxx - Headless subclass of ScintillaBase
// Copyright 1998-2004 by Neil Hodgson <neilh@scintilla.org>
// The License.txt file describes the conditions under which this software may be distributed.
 

#include <new>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <ctype.h>
#include <time.h>

#include <stdexcept>
#include <string>
#include <vector>
#include <map>
#include <algorithm>

#include "Platform.h"
#include "Scintilla.h"

#include "ILexer.h"
#ifdef SCI_LEXER
#include "SciLexer.h"
#endif
#include "SplitVector.h"
#include "Partitioning.h"
#include "RunStyles.h"
#include "ContractionState.h"
#include "CellBuffer.h"
#include "CallTip.h"
#include "KeyMap.h"
#include "Indicator.h"
#include "XPM.h"
#include "LineMarker.h"
#include "Style.h"
#include "AutoComplete.h"
#include "ViewStyle.h"
#include "Decoration.h"
#include "CharClassify.h"
#include "CaseFolder.h"
#include "Document.h"
#include "Selection.h"
#include "PositionCache.h"
#include "EditModel.h"
#include "MarginView.h"
#include "LineMarker.h"
#include "EditView.h"
#include "Editor.h"
#include "UniConversion.h"
#include "CaseConvert.h"
#include "ScintillaBase.h"

#ifdef SCI_LEXER
#include "LexerModule.h"
#include "ExternalLexer.h"
#endif

#include "ScintillaHeadless.h"

#ifdef SCI_NAMESPACE
using namespace Scintilla;
#endif


class ScintillaHeadless : public ScintillaBase {
public:
	ScintillaHeadless();
	virtual ~ScintillaHeadless();
	virtual sptr_t WndProc(unsigned int iMessage, uptr_t wParam, sptr_t lParam);
private:
	Window wText;
	Window scrollbarv;
	Window scrollbarh;
	int scrollBarWidth;
	int scrollBarHeight;

	SelectionText primary;

	bool capturedMouse;
	bool dragWasDropped;
	int lastKey;
	int rectangularSelectionModifier;

	// Private so ScintillaHeadless objects can not be copied
	ScintillaHeadless(const ScintillaHeadless &);
	ScintillaHeadless &operator=(const ScintillaHeadless &);

	virtual void Initialise();
	virtual void Finalise();
	virtual void StartDrag();

	virtual sptr_t DefWndProc(unsigned int iMessage, uptr_t wParam, sptr_t lParam);
	virtual void SetVerticalScrollPos();
	virtual void SetHorizontalScrollPos();
	virtual void NotifyChange();
	virtual void NotifyParent(SCNotification scn);
	virtual bool ModifyScrollBars(int nMax, int nPage);
	virtual void SetTicking(bool on);
	virtual bool SetIdle(bool on);
	virtual void SetMouseCapture(bool on);
	virtual bool HaveMouseCapture();
	virtual void CopyToClipboard(const SelectionText &selectedText);
	virtual void Copy();
	virtual void Paste();
	virtual void CreateCallTipWindow(PRectangle rc);
	virtual void AddToPopUp(const char *label, int cmd = 0, bool enabled = true);
	virtual void ClaimSelection();
	void StoreOnClipboard(SelectionText *clipText);

	static sptr_t DirectFunction(ScintillaHeadless *sciThis,
	                             unsigned int iMessage, uptr_t wParam, sptr_t lParam);
};



ScintillaHeadless::ScintillaHeadless() :
		scrollBarWidth(30), scrollBarHeight(30),
		capturedMouse(false), dragWasDropped(false),
		lastKey(0), rectangularSelectionModifier(SCMOD_CTRL) {
	Initialise();
	// Pretend to have a main window, so that we will end up allocating
	// surfaces (so that we can actually lay things out).  Bug 102147.
	wMain = reinterpret_cast<WindowID>(this);
}

ScintillaHeadless::~ScintillaHeadless() {
}

void ScintillaHeadless::Initialise() {
	SetTicking(true);
}

void ScintillaHeadless::Finalise() {
	SetTicking(false);
	ScintillaBase::Finalise();
}

void ScintillaHeadless::StartDrag() {
	dragWasDropped = false;
}

sptr_t ScintillaHeadless::WndProc(unsigned int iMessage, uptr_t wParam, sptr_t lParam) {
	try {
		switch (iMessage) {

		case SCI_GETDIRECTFUNCTION:
			return reinterpret_cast<sptr_t>(DirectFunction);

		case SCI_GETDIRECTPOINTER:
			return reinterpret_cast<sptr_t>(this);

#ifdef SCI_LEXER
		case SCI_LOADLEXERLIBRARY:
                        LexerManager::GetInstance()->Load(reinterpret_cast<const char*>(lParam));
			break;
#endif
 
		default:
			return ScintillaBase::WndProc(iMessage, wParam, lParam);
		}
	} catch (std::bad_alloc&) {
		errorStatus = SC_STATUS_BADALLOC;
	} catch (...) {
		errorStatus = SC_STATUS_FAILURE;
	}
	return 0l;
}

sptr_t ScintillaHeadless::DefWndProc(unsigned int, uptr_t, sptr_t) {
	return 0;
}

void ScintillaHeadless::SetVerticalScrollPos() {
}

void ScintillaHeadless::SetHorizontalScrollPos() {
}

bool ScintillaHeadless::ModifyScrollBars(int nMax, int nPage) {
	return true;
}

void ScintillaHeadless::NotifyChange() {
}

void ScintillaHeadless::NotifyParent(SCNotification scn) {
}

void ScintillaHeadless::SetTicking(bool on) {
}

bool ScintillaHeadless::SetIdle(bool on) {
	return true;
}

void ScintillaHeadless::SetMouseCapture(bool on) {
}

bool ScintillaHeadless::HaveMouseCapture() {
	return false;
}

void ScintillaHeadless::CopyToClipboard(const SelectionText &selectedText) {
}

void ScintillaHeadless::Copy() {
}

void ScintillaHeadless::Paste() {
}

void ScintillaHeadless::CreateCallTipWindow(PRectangle rc) {
}

void ScintillaHeadless::AddToPopUp(const char *label, int cmd, bool enabled) {
}

void ScintillaHeadless::ClaimSelection() {
}

void ScintillaHeadless::StoreOnClipboard(SelectionText *clipText) {
}

#ifdef _WIN32
sptr_t __stdcall Scintilla_DirectFunction(
    ScintillaHeadless *sci, unsigned int  iMessage, uptr_t wParam, sptr_t lParam) {
	return sci->WndProc(iMessage, wParam, lParam);
}
#endif

sptr_t ScintillaHeadless::DirectFunction(
    ScintillaHeadless *sciThis, unsigned int iMessage, uptr_t wParam, sptr_t lParam) {
	return sciThis->WndProc(iMessage, wParam, lParam);
}

//sptr_t scintilla_send_message(void *sci, unsigned int iMessage, uptr_t wParam, sptr_t lParam) {
//	ScintillaHeadless *psci = reinterpret_cast<ScintillaHeadless *>(sci->pscin);
//	return psci->WndProc(iMessage, wParam, lParam);
//}
//
//static void scintilla_init(ScintillaObject *sci) {
//	try {
//		sci->pscin = new ScintillaHeadless(sci);
//	} catch (...) {
//	}
//}
//
//void scintilla_set_id(ScintillaObject *sci, uptr_t id) {
//	ScintillaHeadless *psci = reinterpret_cast<ScintillaHeadless *>(sci->pscin);
//	psci->ctrlID = id;
//}

void* scintilla_new(void) {
	return new ScintillaHeadless();
}

sptr_t scintilla_send_message(void *sci, unsigned int iMessage, uptr_t wParam, sptr_t lParam) {
	ScintillaHeadless *psci = reinterpret_cast<ScintillaHeadless *>(sci);
	return psci->WndProc(iMessage, wParam, lParam);
}

void scintilla_release_resources(void) {
	try {
		//Platform_Finalise();
	} catch (...) {
	}
}
