/* Copyright (c) 2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

#ifndef __koISciMozIMEHelper_h__
#define __koISciMozIMEHelper_h__

#include "koISciMozIMEHelper.h"
#include <nsIDOMQueryContentListener.h>

#include <nsCOMPtr.h>

#include <nsRect.h>

class nsIWeakReference;

class koSciMozIMEHelper : public koISciMozIMEHelper,
                          public nsIDOMQueryContentListener
{
    NS_DECL_ISUPPORTS
    NS_DECL_KOISCIMOZIMEHELPER
    NS_DECL_NSIDOMEVENTLISTENER
public: /* nsIDOMQueryContentListener */
    NS_IMETHOD HandleText           (nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QuerySelectedText    (nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QueryTextContent     (nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QueryCaretRect       (nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QueryTextRect        (nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QueryCharacterAtPoint(nsIDOMEvent* aQueryContentEvent);
    NS_IMETHOD QueryDOMWidgetHitTest(nsIDOMEvent* aQueryContentEvent);
public:
    koSciMozIMEHelper();
    ~koSciMozIMEHelper();
protected:
    /**
     * Reference to the ISciMoz we are helping
     * (weak to avoid a reference cycle)
     */
    nsCOMPtr<nsIWeakReference> mSciMoz;
    /**
     * The start byte position of the composition; -1 if not currently composing
     */
    int mIMEStartPos;
    bool mIMEComposing;
    bool mIMEActive;
protected:
    // helper methods
    /**
     * Finds the smallest rectangle which contains both aDestRect and
     * aOtherRect, and stores the result in aDestRect.  Completely empty
     * rectangles are ignored; if both are empty, aDestRect is unchanged.
     */
    static void UnionRect(nsIntRect& aDestRect, const nsIntRect& aOtherRect);
    /**
     * Given a rectangle in scintilla pixel co-ordinates, convert it to CSS
     * pixels relative to the top left corner of the window.
     */
    static nsresult ScintillaPixelsToCSSPixels(const nsIntRect& aRect,
                                               nsIDOMEvent* aEvent,
                                               nsIntRect& aResult);
    /**
     * Mark the state as we're starting to compose some text
     */
    nsresult StartComposing(ISciMoz* aSciMoz);
    /**
     * Finish composing text (and commit).
     */
    nsresult EndComposing(ISciMoz* aSciMoz);

};

#define KOSCIMOZIMEHELPER_CID \
    /* {DB7DCA40-FA10-411b-B723-3213398D31C3} */ \
    { 0xdb7dca40, 0xfa10, 0x411b, \
        { 0xb7, 0x23, 0x32, 0x13, 0x39, 0x8d, 0x31, 0xc3 } \
    }

#define KOSCIMOZIMEHELPER_CONTRACTID \
    "@activestate.com/koSciMozIMEHelper;1"

#endif /* __koISciMozHelper_h__ */
