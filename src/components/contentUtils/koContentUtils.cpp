/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */
#include "nsXPCOM.h"
#include "nsCOMPtr.h"

#include "jsapi.h"
#include "nsIScriptContext.h"
#include "nsIScriptGlobalObject.h"
#include "nsDOMJSUtils.h"

#include "nsIServiceManager.h"
#include "nsIXPConnect.h"
#include "nsIDOMWindow.h"

#include "mozilla/ModuleUtils.h"

#include "koIContentUtils.h"

// {631e72c5-3779-5a43-870b-9b5d58e1ca91}
#define KO_CONTENT_UTILS_CID \
{ 0x631e72c5, 0x3779, 0x5a43, { 0x87, 0x0b, 0x9b, 0x5d, 0x58, 0xe1, 0xca, 0x91 } }
#define KO_CONTENT_UTILS_CONTRACTID "@activestate.com/koContentUtils;1"

static NS_DEFINE_CID(kContentUtilsCID, KO_CONTENT_UTILS_CID);


class koContentUtils : public koIContentUtils
{
public:
  NS_DECL_ISUPPORTS
  NS_DECL_KOICONTENTUTILS

  koContentUtils();
  virtual ~koContentUtils();
  
private:
  nsCOMPtr<nsIXPConnect> mXPConnect;
  nsIScriptGlobalObject *GetDynamicScriptGlobal(JSContext* aContext);
  already_AddRefed<nsIDOMWindow> GetWindowFromCaller();
};

NS_IMPL_ISUPPORTS1(koContentUtils, koIContentUtils)

koContentUtils::koContentUtils()
{
  mXPConnect = do_GetService("@mozilla.org/js/xpc/XPConnect;1");
}

koContentUtils::~koContentUtils()
{
}

nsIScriptGlobalObject *
koContentUtils::GetDynamicScriptGlobal(JSContext* aContext)
{
  nsIScriptContext *scriptCX = GetScriptContextFromJSContext(aContext);
  if (!scriptCX)
    return nullptr;
  return scriptCX->GetGlobalObject();
}

already_AddRefed<nsIDOMWindow>
koContentUtils::GetWindowFromCaller()
{
  JSContext *cx = nullptr;
  cx = mXPConnect->GetCurrentJSContext();

  if (cx) {
    nsIScriptGlobalObject *sgo = GetDynamicScriptGlobal(cx);
    nsCOMPtr<nsIDOMWindow> win(do_QueryInterface(sgo));

    if (win) {
      return win.forget();
    }
  }

  return nullptr;
}

NS_IMETHODIMP koContentUtils::GetWindowFromCaller(nsIDOMWindow **callingDoc)
{
    NS_ENSURE_ARG_POINTER(callingDoc);
  
    *callingDoc = GetWindowFromCaller().get();
    return NS_OK;
}


NS_GENERIC_FACTORY_CONSTRUCTOR(koContentUtils)

NS_DEFINE_NAMED_CID(KO_CONTENT_UTILS_CID);

static const mozilla::Module::CIDEntry kModuleCIDs[] = {
    { &kKO_CONTENT_UTILS_CID, true, NULL, koContentUtilsConstructor },
    { NULL }
};

static const mozilla::Module::ContractIDEntry kModuleContracts[] = {
    { KO_CONTENT_UTILS_CONTRACTID, &kKO_CONTENT_UTILS_CID },
    { NULL }
};

static const mozilla::Module::CategoryEntry kModuleCategories[] = {
    { NULL }
};

static const mozilla::Module kModule = {
    mozilla::Module::kVersion,
    kModuleCIDs,
    kModuleContracts,
    kModuleCategories
};

// The following line implements the one-and-only "NSModule" symbol exported from this
// shared library.
NSMODULE_DEFN(koContentUtilsModule) = &kModule;
