/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */

#ifndef KO_NPAPI_UTILS_H
#define KO_NPAPI_UTILS_H

#include <npapi.h>
#include <npruntime.h>

/**
 * RAII for NPObject
 */

class koNPObjectPtr
{
public:
    koNPObjectPtr() : mObj(0) {}
    koNPObjectPtr(const koNPObjectPtr& aOther) {
        Assign(aOther.mObj);
    }
    koNPObjectPtr(NPObject* aObj) {
        Assign(aObj);
    }
    koNPObjectPtr& operator=(const koNPObjectPtr& aOther) {
        Destroy();
        Assign(aOther.mObj);
        return *this;
    }
    ~koNPObjectPtr() {
        Destroy();
    }
    operator NPObject*() { return mObj; }
protected:
    void Destroy() {
        if (mObj) {
            NPN_ReleaseObject(mObj);
            mObj = 0;
        }
    }
    void Assign(NPObject* aObj) {
        mObj = aObj ? NPN_RetainObject(aObj) : aObj;
    }
    NPObject* mObj;
};

#endif /* KO_NPAPI_UTILS_H */
