/* Copyright (c) 2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

#define FORCE_PR_LOG

#include "koSciMozIMEHelper.h"

/* XXX Mook: hack to avoid including internal strings */
#define nsString_h___
#include <nsStringGlue.h>

#include <prlog.h>
#include <nsCOMPtr.h>
#include <nsIBoxObject.h>
#include <nsIDOMClientRect.h>
#include <nsIDOMElement.h>
#include <nsIDOMEvent.h>
#include <nsIDOMEventTarget.h>
#include <nsIDOMNSElement.h>
#include <nsRect.h>
#include <nsIPrivateQueryContentEvent.h>
#include <nsIPrivateTextEvent.h>
#include <nsIWeakReference.h>
#include <nsIWeakReferenceUtils.h>
#include <nsGUIEvent.h>
#include "nsSciMoz.h"
#include "Scintilla.h"

/* XXX Mook: debugging */
#ifdef PR_LOGGING
static PRLogModuleInfo *gIMELog = nsnull;
#define LOG(...) \
    PR_LOG(gIMELog, PR_LOG_WARNING, (__VA_ARGS__))
#define TRACE(...) \
    PR_LOG(gIMELog, PR_LOG_ALWAYS, (__VA_ARGS__))
#else
#define LOG(...) PR_BEGIN_MACRO PR_END_MACRO
#define TRACE(...) PR_BEGIN_MACRO PR_END_MACRO
#endif

NS_IMPL_THREADSAFE_ISUPPORTS1(koSciMozIMEHelper, koISciMozIMEHelper)

koSciMozIMEHelper::koSciMozIMEHelper()
    :mIMEComposing(false),
     mIMEActive(false),
     mIMEStartPos(-1)
{
#ifdef PR_LOGGING
    if (!gIMELog) {
        gIMELog = PR_NewLogModule("koSciMozIMEHelper");
    }
    TRACE("%s()", __FUNCTION__);
#endif
}

koSciMozIMEHelper::~koSciMozIMEHelper()
{
    TRACE("%s()", __FUNCTION__);
}

/* void init (in ISciMoz aSciMoz, in nsIDOMEventTarget aEventTarget); */
NS_IMETHODIMP
koSciMozIMEHelper::Init(ISciMoz *aSciMoz, nsIDOMEventTarget *aEventTarget)
{
    TRACE("%s(%p, %p)", __FUNCTION__, aSciMoz, aEventTarget);
#if PR_LOGGING
    nsCOMPtr<nsIDOMElement> elem = do_QueryInterface(aEventTarget);
    if (elem) {
        nsString tagName;
        nsresult rv = elem->GetTagName(tagName);
        if (NS_FAILED(rv)) tagName.AssignLiteral("<error>");
        TRACE("%s: tag name %s", __FUNCTION__, NS_ConvertUTF16toUTF8(tagName).get());
    }
#endif
    NS_ENSURE_FALSE(mSciMoz, NS_ERROR_ALREADY_INITIALIZED);
    NS_ENSURE_ARG_POINTER(aSciMoz);
    NS_ENSURE_ARG_POINTER(aEventTarget);
    mSciMoz = do_GetWeakReference(aSciMoz);
    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NO_INTERFACE);
    
    static const char* kEventNames[] = {
        "querycontentselectedtext", "querycontenttextcontent",
        "querycontentcaretrect", "querycontenttextrect",
        "querycontentcharacteratpoint", "querycontentdomwidgethittest",
        "text",
    };
    for (int i = 0; i < NS_ARRAY_LENGTH(kEventNames); ++i) {
        NS_ConvertASCIItoUTF16 eventName(kEventNames[i]);
        nsresult rv = aEventTarget->AddEventListener(eventName,
                                                     this,
                                                     false);
        NS_ENSURE_SUCCESS(rv, rv);
    }
    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::HandleText(nsIDOMEvent* aEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aEvent);
    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    NS_ENSURE_ARG_POINTER(aEvent);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    // This is called multiple times in the middle of an
    // IME composition
    nsCOMPtr<nsIPrivateTextEvent> textEvent(do_QueryInterface(aEvent));
    if (!textEvent)
        return NS_OK;

    nsresult rv;

    nsString text;
    rv = textEvent->GetText(text);
    NS_ENSURE_SUCCESS(rv, rv);

    TRACE("%s: length: %d, [%s]",
          __FUNCTION__, text.Length(), NS_ConvertUTF16toUTF8(text).get());

    // If there is no textRangeList, then this is the end of the IME session
    // and we need to "harden" any IME input (hardening is done by setting
    // imeComposing to false).
    nsCOMPtr<nsIPrivateTextRangeList> textRangeList;
    textRangeList = textEvent->GetInputRange();
    int textRangeListLength = 0;
    if (textRangeList && (textRangeList->GetLength() > 0)) {
        textRangeListLength = textRangeList->GetLength();
    }
    TRACE("%s: text range length: %d startPos %i active %s composing %s",
          __FUNCTION__,
          textRangeListLength,
          mIMEStartPos,
          mIMEActive ? "yes" : "no",
          mIMEComposing ? "yes" : "no");

    //
    // Notes: mIMEActive is only true from the second IME keypress.
    //
    if (mIMEStartPos < 0) {
        TRACE("%s: IME starting", __FUNCTION__);
        StartComposing(sciMoz);
    }
    if (mIMEActive || text.Length() > 0) {
        rv = sciMoz->ReplaceSel(NS_ConvertUTF16toUTF8(text));
        NS_ENSURE_SUCCESS(rv, rv);
    }
    if (textRangeListLength == 0) {
        TRACE("%s: text range list (%p) is empty",
              __FUNCTION__, textRangeList.get());
        mIMEComposing = false;
    }
    if (mIMEActive && mIMEComposing) {
        rv = sciMoz->SetAnchor(mIMEStartPos);
        NS_ENSURE_SUCCESS(rv, rv);
    #if 0
        /* This lets us abort the entry so that we can restore the old text in
         * the case where
         * 1. the user selects some text
         * 2. starts composing
         * 3. hit escape and cancel compose
         * Unfortunately, if instead of step 3, the user just hits backspace
         * repeatedly and remove all of the candidate text, we also restore the
         * old text - which is definitely not the desired behaviour.
         * Without this chunk of code, we should match text entry in Firefox 4
         * (which doesn't match the OS-native behaviour)
         */
        } else if (text.IsEmpty()) {
            TRACE("%s: finished composition with no text, assuming abort",
                  __FUNCTION__);
            mIMEComposing = true;
            AbortComposing();
    #endif
    } else {
        TRACE("%s: IME finished", __FUNCTION__);
        // mIMEComposing should be set to false due to empty text range list
        NS_ASSERTION(!mIMEComposing, "IME finished while composing!?");
        EndComposing(sciMoz);
    }

    return NS_OK;
}

nsresult
koSciMozIMEHelper::StartComposing(ISciMoz* aSciMoz)
{
    TRACE("%s(): start pos = %d", __FUNCTION__, mIMEStartPos);
    NS_PRECONDITION(aSciMoz, "no ISciMoz given to StartComposing!");

    nsresult rv;
    mIMEComposing = true;
    if (mIMEStartPos < 0) {
        nsresult rv;
        rv = aSciMoz->BeginUndoAction();
        NS_ENSURE_SUCCESS(rv, rv);
        PRInt32 anchor;
        rv = aSciMoz->GetAnchor(&anchor);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = aSciMoz->GetCurrentPos(&mIMEStartPos);
        NS_ENSURE_SUCCESS(rv, rv);
        if (anchor < mIMEStartPos)
            mIMEStartPos = anchor;
        mIMEActive = true;
        TRACE("%s: start pos %d", __FUNCTION__, mIMEStartPos);
    }
    return NS_OK;
}

nsresult
koSciMozIMEHelper::EndComposing(ISciMoz* aSciMoz)
{
    TRACE("%s()", __FUNCTION__);
    NS_PRECONDITION(aSciMoz, "No ISciMoz supplied to EndComposing!");

    nsresult rv;
    if (mIMEStartPos >= 0) {
        mIMEStartPos = -1;
        rv = aSciMoz->EndUndoAction();
        NS_ENSURE_SUCCESS(rv, rv);
    }
    mIMEActive = false;
    return NS_OK;
}

/* void abortComposing(); */
NS_IMETHODIMP
koSciMozIMEHelper::AbortComposing()
{
    TRACE("%s: startPos %d, composing %s",
          __FUNCTION__, mIMEStartPos, mIMEComposing ? "yes" : "no");

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    nsresult rv;
    bool composing = mIMEComposing;
    mIMEComposing = false;
    rv = EndComposing(sciMoz);
    NS_ENSURE_SUCCESS(rv, rv);
    if (composing) {
        // blur event, mouse click or other during composition, undo
        // the composition now
        PRBool collectUndo;
        rv = sciMoz->GetUndoCollection(&collectUndo);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->SetUndoCollection(PR_FALSE);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->Undo();
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->SetUndoCollection(collectUndo);
        NS_ENSURE_SUCCESS(rv, rv);
        mIMEComposing = false;
    }
    return NS_OK;
}

/* void nsIDOMEventListener::handleEvent(in nsIDOMEvent event); */
NS_IMETHODIMP
koSciMozIMEHelper::HandleEvent(nsIDOMEvent* aEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aEvent);
    // we should be getting the separate handlers on nsIDOMQueryContentListener
    nsString eventType;
    nsresult rv = aEvent->GetType(eventType);
    NS_ENSURE_SUCCESS(rv, rv);
    TRACE("%s(%p): event type %s",
          __FUNCTION__, aEvent, NS_ConvertUTF16toUTF8(eventType).get());
    if (eventType.EqualsLiteral("text")) {
        return HandleText(aEvent);
    }
    if (eventType.EqualsLiteral("querycontentselectedtext")) {
        return QuerySelectedText(aEvent);
    }
    if (eventType.EqualsLiteral("querycontenttextcontent")) {
        return QueryTextContent(aEvent);
    }
    if (eventType.EqualsLiteral("querycontentcaretrect")) {
        return QueryCaretRect(aEvent);
    }
    if (eventType.EqualsLiteral("querycontenttextrect")) {
        return QueryTextRect(aEvent);
    }
    if (eventType.EqualsLiteral("querycontentcharacteratpoint")) {
        return QueryCharacterAtPoint(aEvent);
    }
    if (eventType.EqualsLiteral("querycontentdomwidgethittest")) {
        return QueryDOMWidgetHitTest(aEvent);
    }
    TRACE("koSciMozIMEHelper::HandleEvent: unexpected event %s\n",
          NS_ConvertUTF16toUTF8(eventType).get());
    return NS_ERROR_NOT_IMPLEMENTED;
}

NS_IMETHODIMP
koSciMozIMEHelper::QuerySelectedText(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    nsresult rv;
    nsString selText;
    PRInt32 anchor, pos;
    rv = sciMoz->GetSelText(selText);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->GetAnchor(&anchor);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->GetCurrentPos(&pos);
    NS_ENSURE_SUCCESS(rv, rv);

    qcEvent->SetReplyString(selText);
    qcEvent->SetReplyOffset(anchor);
    qcEvent->SetReplyReversed(pos < anchor);
    qcEvent->SetSucceeded(PR_TRUE);
    TRACE("%s(%p): succeeded, text [%s] at offset %i (%s)",
          __FUNCTION__, aQueryContentEvent,
          NS_ConvertUTF16toUTF8(selText).get(),
          anchor, pos < anchor ? "reversed" : "forward");

    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::QueryTextContent(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    PRUint32 offset = qcEvent->GetOffset();
    PRUint32 length = qcEvent->GetLength();

    nsString text;
    nsresult rv;

    // our offsets are in characters. scimoz wants bytes here. :|
    PRInt32 byteOffset, byteEnd;
    rv = sciMoz->PositionAtChar(0, offset, &byteOffset);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->PositionAtChar(byteOffset, length, &byteEnd);
    NS_ENSURE_SUCCESS(rv, rv);
    
    rv = sciMoz->GetTextRange(byteOffset, byteEnd, text);
    NS_ENSURE_SUCCESS(rv, rv);
    qcEvent->SetReplyString(text);
    TRACE("%s: set reply string [%s] (pos %d + %d, bytes %d ~ %d = %d)",
          __FUNCTION__, NS_ConvertUTF16toUTF8(text).get(),
          offset, length, byteOffset, byteEnd, byteEnd - byteOffset);

    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::QueryCaretRect(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    nsIntRect intRect;
    nsRect rect;
    #if PR_LOGGING
        intRect = qcEvent->GetReplyRect();
        TRACE("koSciMozIMEHelper::QueryCaretRect: old rect (%d,%d)-(%d,%d) offset %i",
              intRect.x, intRect.y, intRect.width, intRect.height,
              qcEvent->GetOffset());
    #endif /* PR_LOGGING */

    // get the caret position, in scintilla co-ordinates
    // (device pixels relative to the top-left corner of the plugin)
    nsresult rv;
    rv = sciMoz->PointXFromPosition(qcEvent->GetOffset(), &intRect.x);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->PointYFromPosition(qcEvent->GetOffset(), &intRect.y);
    NS_ENSURE_SUCCESS(rv, rv);
    PRInt32 line;
    rv = sciMoz->LineFromPosition(qcEvent->GetOffset(), &line);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->TextHeight(line, &intRect.height);
    NS_ENSURE_SUCCESS(rv, rv);
    intRect.width = 1; // TODO: actually ask
    TRACE("%s: new rect in scintilla units: (%d,%d)-(%d,%d)",
          __FUNCTION__,
          intRect.x, intRect.y, intRect.width, intRect.height);

    rv = ScintillaPixelsToCSSPixels(intRect, aQueryContentEvent, intRect);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = qcEvent->SetReplyRect(intRect);
    NS_ENSURE_SUCCESS(rv, rv);
    qcEvent->SetSucceeded(PR_TRUE);

    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::QueryTextRect(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    // TODO: this needs refactoring
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    nsIntRect intRect, lineRect;
    nsRect rect;
    nsresult rv;
    #if PR_LOGGING
        intRect = qcEvent->GetReplyRect();
        TRACE("koSciMozIMEHelper::QueryTextRect: old rect %d %d %d %d\n",
              intRect.x, intRect.y, intRect.width, intRect.height);
    #endif /* PR_LOGGING */

    // figure out the start and end line numbers
    PRUint32 start = qcEvent->GetOffset();
    PRUint32 end = qcEvent->GetLength() + start;
    PRInt32 lineStart, lineEnd;
    rv = sciMoz->LineFromPosition(start, &lineStart);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->LineFromPosition(end, &lineEnd);
    NS_ENSURE_SUCCESS(rv, rv);

    if (lineStart == lineEnd) {
        // the selection is within one line; just get its rect
        rv = sciMoz->PointXFromPosition(start, &lineRect.x);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointYFromPosition(start, &lineRect.y);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointXFromPosition(end, &lineRect.width);
        NS_ENSURE_SUCCESS(rv, rv);
        // convert from max pos to width, but make it non-empty
        lineRect.width = PR_MAX(1, lineRect.width - lineRect.x);
        rv = sciMoz->TextHeight(lineStart, &lineRect.height);
        NS_ENSURE_SUCCESS(rv, rv);
        UnionRect(intRect, lineRect);
    } else {
        PRInt32 posStart, posEnd;
        // get the rect for the first line
        rv = sciMoz->GetLineEndPosition(lineStart, &posEnd);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointXFromPosition(start, &lineRect.x);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointYFromPosition(start, &lineRect.y);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointXFromPosition(posEnd, &lineRect.width);
        NS_ENSURE_SUCCESS(rv, rv);
        // convert from max pos to width, but make it non-empty
        lineRect.width = PR_MAX(1, lineRect.width - lineRect.x);
        rv = sciMoz->TextHeight(lineStart, &lineRect.height);
        NS_ENSURE_SUCCESS(rv, rv);
        UnionRect(intRect, lineRect);

        for (PRInt32 line = lineStart + 1; line < lineEnd; ++line) {
            // get the rect for a line in the middle
            rv = sciMoz->PositionFromLine(line, &posStart);
            NS_ENSURE_SUCCESS(rv, rv);
            rv = sciMoz->GetLineEndPosition(line, &posEnd);
            NS_ENSURE_SUCCESS(rv, rv);
            rv = sciMoz->PointXFromPosition(posStart, &lineRect.x);
            NS_ENSURE_SUCCESS(rv, rv);
            rv = sciMoz->PointYFromPosition(posStart, &lineRect.y);
            NS_ENSURE_SUCCESS(rv, rv);
            rv = sciMoz->PointXFromPosition(posEnd, &lineRect.width);
            NS_ENSURE_SUCCESS(rv, rv);
            // convert from max pos to width, but make it non-empty
            lineRect.width = PR_MAX(1, lineRect.width - lineRect.x);
            rv = sciMoz->TextHeight(lineStart, &lineRect.height);
            NS_ENSURE_SUCCESS(rv, rv);
            UnionRect(intRect, lineRect);
        }

        // get the rect for the last line
        rv = sciMoz->PositionFromLine(lineEnd, &posStart);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->GetLineEndPosition(lineEnd, &posEnd);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointXFromPosition(posStart, &lineRect.x);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointYFromPosition(posStart, &lineRect.y);
        NS_ENSURE_SUCCESS(rv, rv);
        rv = sciMoz->PointXFromPosition(posEnd, &lineRect.width);
        NS_ENSURE_SUCCESS(rv, rv);
        // convert from max pos to width, but make it non-empty
        lineRect.width = PR_MAX(1, lineRect.width - lineRect.x);
        rv = sciMoz->TextHeight(lineStart, &lineRect.height);
        NS_ENSURE_SUCCESS(rv, rv);
        UnionRect(intRect, lineRect);
    }

    rv = ScintillaPixelsToCSSPixels(intRect, aQueryContentEvent, intRect);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = qcEvent->SetReplyRect(intRect);
    NS_ENSURE_SUCCESS(rv, rv);
    qcEvent->SetSucceeded(PR_TRUE);

    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::QueryCharacterAtPoint(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    nsresult rv;
    PRInt32 charPos;
    rv = sciMoz->CharPositionFromPointClose(qcEvent->GetRefPointX(),
                                            qcEvent->GetRefPointY(),
                                            &charPos);
    NS_ENSURE_SUCCESS(rv, rv);
    #pragma push_macro("INVALID_POSITION")
    #undef INVALID_POSITION
    if (charPos == ISciMoz::INVALID_POSITION) {
        qcEvent->SetReplyOffset(PR_UINT32_MAX);
        return NS_OK;
    }
    #pragma pop_macro("INVALID_POSITION")

    // get the text rectangle - but check to see if it's a newline, in which
    // case it doesn't really make sense
    PRInt32 nextPos, lineStart, lineEnd;
    nsIntRect rect;
    rv = sciMoz->PositionAfter(charPos, &nextPos);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->LineFromPosition(charPos, &lineStart);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->LineFromPosition(nextPos, &lineEnd);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->PointXFromPosition(charPos, &rect.x);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->PointYFromPosition(charPos, &rect.y);
    NS_ENSURE_SUCCESS(rv, rv);
    rv = sciMoz->TextHeight(lineStart, &rect.height);
    NS_ENSURE_SUCCESS(rv, rv);
    if (lineStart != lineEnd) {
        // the character is a new line...
        rect.width = 1;
    } else {
        rv = sciMoz->PointXFromPosition(nextPos, &rect.width);
        NS_ENSURE_SUCCESS(rv, rv);
        rect.width -= rect.x;
    }

    PRUnichar c;
    rv = sciMoz->GetWCharAt(charPos, &c);
    NS_ENSURE_SUCCESS(rv, rv);
    qcEvent->SetReplyOffset(charPos);
    qcEvent->SetReplyRect(rect);
    qcEvent->SetSucceeded(PR_TRUE);

    return NS_OK;
}

NS_IMETHODIMP
koSciMozIMEHelper::QueryDOMWidgetHitTest(nsIDOMEvent* aQueryContentEvent)
{
    TRACE("%s(%p)", __FUNCTION__, aQueryContentEvent);
    NS_ENSURE_ARG_POINTER(aQueryContentEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> queryContentEvent =
        do_QueryInterface(aQueryContentEvent);
    NS_ENSURE_TRUE(queryContentEvent, NS_ERROR_NO_INTERFACE);

    NS_ENSURE_TRUE(mSciMoz, NS_ERROR_NOT_INITIALIZED);
    nsCOMPtr<ISciMoz> sciMoz = do_QueryReferent(mSciMoz);
    NS_ENSURE_TRUE(sciMoz, NS_ERROR_NOT_AVAILABLE);

    return NS_ERROR_NOT_IMPLEMENTED;
    return NS_OK;
}

/**
 * This is mostly-equivalent to nsIntRect::UnionRect; however, that one lives
 * deep in the bowels of gkgfx, which makes it difficult to link to. This is
 * here for the convenience of the linker only.
 */
/* static */ void
koSciMozIMEHelper::UnionRect(nsIntRect& aRect, const nsIntRect& aOther)
{
    TRACE("%s(%p, %p): (%d,%d)-(%d,%d) + (%d,%d)-(%d,%d)",
          __FUNCTION__, &aRect, &aOther,
          aRect.x, aRect.y, aRect.width, aRect.height,
          aOther.x, aOther.y, aOther.width, aOther.height);
    if (aOther.IsEmpty()) {
        // the second rectangle is empty, it doesn't affect anything
        return;
    }
    if (aRect.IsEmpty()) {
        // the first is empty, the second isn't; use the second
        aRect = aOther;
        return;
    }
    // if we get here, we have two non-empty rectangles
    // store the bottom-right corner (rather than dimensions) in aRect
    aRect.width = PR_MAX(aRect.XMost(), aOther.XMost());
    aRect.height = PR_MAX(aRect.YMost(), aOther.YMost());
    // move the top-left of aRect to the result rectangle
    aRect.x = PR_MIN(aRect.x, aOther.x);
    aRect.y = PR_MIN(aRect.y, aOther.y);
    // convert the bottom-right corner back into dimensions
    aRect.width -= aRect.x;
    aRect.height -= aRect.y;
    TRACE("%s(%p, %p): -> (%d,%d)-(%d,%d)",
          __FUNCTION__, &aRect, &aOther,
          aRect.x, aRect.y, aRect.width, aRect.height);
}

/* static */ nsresult
koSciMozIMEHelper::ScintillaPixelsToCSSPixels(const nsIntRect& aRect,
                                              nsIDOMEvent* aEvent,
                                              nsIntRect& aResult)
{
    TRACE("%s(%p)", __FUNCTION__, aEvent);
    NS_ENSURE_ARG_POINTER(aEvent);
    nsCOMPtr<nsIPrivateQueryContentEvent> qcEvent =
        do_QueryInterface(aEvent);
    NS_ENSURE_TRUE(qcEvent, NS_ERROR_NO_INTERFACE);

    nsRect rect;
    nsresult rv;
    // convert scintilla co-ordinates into css co-ordinates (relative to the
    // top-left corner of the plugin)
    rect = nsRect(qcEvent->DevPixelsToFloatCSSPixels(aRect.x),
                  qcEvent->DevPixelsToFloatCSSPixels(aRect.y),
                  qcEvent->DevPixelsToFloatCSSPixels(aRect.width),
                  qcEvent->DevPixelsToFloatCSSPixels(aRect.height));
    TRACE("%s: in css units: (%d,%d)-(%d,%d)",
          __FUNCTION__,
          rect.x, rect.y, rect.width, rect.height);
    
    // translate the rectangle to be relative to the top-left corner of the
    // (client area of) the window, in app units
    nsCOMPtr<nsIDOMEventTarget> target;
    rv = aEvent->GetCurrentTarget(getter_AddRefs(target));
    NS_ENSURE_SUCCESS(rv, rv);
    nsCOMPtr<nsIDOMNSElement> element = do_QueryInterface(target, &rv);
    NS_ENSURE_SUCCESS(rv, rv);
    nsCOMPtr<nsIDOMClientRect> boundingRect;
    rv = element->GetBoundingClientRect(getter_AddRefs(boundingRect));
    NS_ENSURE_SUCCESS(rv, rv);
    float n;
    rv = boundingRect->GetLeft(&n);
    NS_ENSURE_SUCCESS(rv, rv);
    rect.x += n;
    rv = boundingRect->GetTop(&n);
    NS_ENSURE_SUCCESS(rv, rv);
    rect.y += n;
    aResult = nsIntRect(qcEvent->CSSPixelsToDevPixels(rect.x),
                        qcEvent->CSSPixelsToDevPixels(rect.y),
                        qcEvent->CSSPixelsToDevPixels(rect.width),
                        qcEvent->CSSPixelsToDevPixels(rect.height));

    TRACE("%s: new rect (%d,%d)-(%d,%d)\n",
          __FUNCTION__,
          aResult.x, aResult.y, aResult.width, aResult.height);

    return NS_OK;
}
