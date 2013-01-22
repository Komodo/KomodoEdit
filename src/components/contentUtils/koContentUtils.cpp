/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */
#include "nsXPCOM.h"
#include "nsCOMPtr.h"

#include "jsapi.h"
#include "jsdbgapi.h"
#include "prprf.h"
#include "nsIScriptContext.h"
#include "nsIScriptGlobalObject.h"
#include "nsIServiceManager.h"
#include "nsIXPConnect.h"
#include "nsPIDOMWindow.h"

#include "mozilla/ModuleUtils.h"
#include "nsIDocShell.h"
#include "nsIDOMWindow.h"

#include "nsIScriptGlobalObjectOwner.h"
#include "nsIJSContextStack.h"

#include "nsContentCID.h"
#include "koIContentUtils.h"

#include "nsIServiceManager.h"

#include "nsDOMJSUtils.h"

// {631e72c5-3779-5a43-870b-9b5d58e1ca91}
#define KO_CONTENT_UTILS_CID \
{ 0x631e72c5, 0x3779, 0x5a43, { 0x87, 0x0b, 0x9b, 0x5d, 0x58, 0xe1, 0xca, 0x91 } }
#define KO_CONTENT_UTILS_CONTRACTID "@activestate.com/koContentUtils;1"

static NS_DEFINE_CID(kContentUtilsCID, KO_CONTENT_UTILS_CID);

static const char kJSStackContractID[] = "@mozilla.org/js/xpc/ContextStack;1";


class koContentUtils : public koIContentUtils
{
public:
  NS_DECL_ISUPPORTS
  NS_DECL_KOICONTENTUTILS

  koContentUtils();
  virtual ~koContentUtils();
  
private:
  nsIDOMDocument *GetDocumentFromCaller();
  nsIDocShell *GetDocShellFromCaller();
  nsIScriptGlobalObject *GetStaticScriptGlobal(JSContext* aContext, JSObject* aObj);
  nsIThreadJSContextStack *sThreadJSContextStack;
  nsIScriptGlobalObject *GetDynamicScriptGlobal(JSContext* aContext);
  nsIScriptContext *GetDynamicScriptContext(JSContext *aContext);
  nsIDOMWindow *GetWindowFromCaller();
};

NS_IMPL_THREADSAFE_ISUPPORTS1(koContentUtils, koIContentUtils)

koContentUtils::koContentUtils()
{
  NS_INIT_ISUPPORTS();

  CallGetService(kJSStackContractID, &sThreadJSContextStack);
}

koContentUtils::~koContentUtils()
{
}

nsIScriptGlobalObject *
koContentUtils::GetStaticScriptGlobal(JSContext* aContext, JSObject* aObj)
{
  JSClass* clazz;
  JSObject* glob = aObj; // starting point for search

  if (!glob)
    return nullptr;

  glob = JS_GetGlobalForObject(aContext, glob);
  NS_ABORT_IF_FALSE(glob, "Infallible returns null");

  clazz = JS_GetClass(glob);

  // Whenever we end up with globals that are JSCLASS_IS_DOMJSCLASS
  // and have an nsISupports DOM object, we will need to modify this
  // check here.
  MOZ_ASSERT(!(clazz->flags & JSCLASS_IS_DOMJSCLASS));
  nsISupports* supports;
  if (!(clazz->flags & JSCLASS_HAS_PRIVATE) ||
      !(clazz->flags & JSCLASS_PRIVATE_IS_NSISUPPORTS) ||
      !(supports = (nsISupports*)::JS_GetPrivate(glob))) {
    return nullptr;
  }

  // We might either have a window directly (e.g. if the global is a
  // sandbox whose script object principal pointer is a window), or an
  // XPCWrappedNative for a window.  We could also have other
  // sandbox-related script object principals, but we can't do much
  // about those short of trying to walk the proto chain of |glob|
  // looking for a window or something.
  nsCOMPtr<nsIScriptGlobalObject> sgo(do_QueryInterface(supports));
  if (!sgo) {
    nsCOMPtr<nsIXPConnectWrappedNative> wrapper(do_QueryInterface(supports));
    NS_ENSURE_TRUE(wrapper, nullptr);
    sgo = do_QueryWrappedNative(wrapper);
  }

  // We're returning a pointer to something that's about to be
  // released, but that's ok here.
  return sgo;
}

nsIScriptGlobalObject *
koContentUtils::GetDynamicScriptGlobal(JSContext* aContext)
{
  nsIScriptContext *scriptCX = GetDynamicScriptContext(aContext);
  if (!scriptCX)
    return nullptr;
  return scriptCX->GetGlobalObject();
}

nsIScriptContext *
koContentUtils::GetDynamicScriptContext(JSContext *aContext)
{
  return GetScriptContextFromJSContext(aContext);
}

nsIDocShell *
koContentUtils::GetDocShellFromCaller()
{
  JSContext *cx = nullptr;
  sThreadJSContextStack->Peek(&cx);

  if (cx) {
    nsIScriptGlobalObject *sgo = GetDynamicScriptGlobal(cx);
    nsCOMPtr<nsPIDOMWindow> win(do_QueryInterface(sgo));

    if (win) {
      return win->GetDocShell();
    }
  }

  return nullptr;
}

nsIDOMWindow *
koContentUtils::GetWindowFromCaller()
{
  JSContext *cx = nullptr;
  sThreadJSContextStack->Peek(&cx);

  if (cx) {
    nsIScriptGlobalObject *sgo = GetDynamicScriptGlobal(cx);
    nsCOMPtr<nsIDOMWindow> win(do_QueryInterface(sgo));

    if (win) {
      return win;
    }
  }

  return nullptr;
}

NS_IMETHODIMP koContentUtils::GetDocShellFromCaller(nsIDocShell **callingDoc)
{
    NS_ENSURE_ARG_POINTER(callingDoc);
  
    *callingDoc = GetDocShellFromCaller();
    NS_IF_ADDREF(*callingDoc);
    return NS_OK;
}

NS_IMETHODIMP koContentUtils::GetWindowFromCaller(nsIDOMWindow **callingDoc)
{
    NS_ENSURE_ARG_POINTER(callingDoc);
  
    *callingDoc = GetWindowFromCaller();
    NS_IF_ADDREF(*callingDoc);
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
