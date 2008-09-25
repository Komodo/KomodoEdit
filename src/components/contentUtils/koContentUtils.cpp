/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */
#include "nsXPCOM.h"
#include "nsCOMPtr.h"

#include "nsIPref.h"

#include "jsapi.h"
#include "jsdbgapi.h"
#include "prprf.h"
#include "nsIScriptContext.h"
#include "nsIScriptObjectOwner.h"
#include "nsIScriptGlobalObject.h"
#include "nsIServiceManager.h"
#include "nsIXPConnect.h"
#include "nsPIDOMWindow.h"

#include "nsIGenericFactory.h"
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

NS_IMPL_ISUPPORTS1(koContentUtils, koIContentUtils)

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
  nsISupports* supports;
  JSClass* clazz;
  JSObject* parent;
  JSObject* glob = aObj; // starting point for search

  if (!glob)
    return nsnull;

  while ((parent = ::JS_GetParent(aContext, glob)))
    glob = parent;

  clazz = JS_GET_CLASS(aContext, glob);

  if (!clazz ||
      !(clazz->flags & JSCLASS_HAS_PRIVATE) ||
      !(clazz->flags & JSCLASS_PRIVATE_IS_NSISUPPORTS) ||
      !(supports = (nsISupports*)::JS_GetPrivate(aContext, glob))) {
    return nsnull;
  }

  nsCOMPtr<nsIXPConnectWrappedNative> wrapper(do_QueryInterface(supports));
  NS_ENSURE_TRUE(wrapper, nsnull);

  nsCOMPtr<nsIScriptGlobalObject> sgo(do_QueryWrappedNative(wrapper));

  // We're returning a pointer to something that's about to be
  // released, but that's ok here.
  return sgo;
}

nsIDOMDocument *
koContentUtils::GetDocumentFromCaller()
{
  JSContext *cx = nsnull;
  sThreadJSContextStack->Peek(&cx);

  nsIDOMDocument *doc = nsnull;

  if (cx) {
    JSObject *callee = nsnull;
    JSStackFrame *fp = nsnull;
    while (!callee && (fp = ::JS_FrameIterator(cx, &fp))) {
      callee = ::JS_GetFrameCalleeObject(cx, fp);
    }

    nsCOMPtr<nsPIDOMWindow> win =
      do_QueryInterface(GetStaticScriptGlobal(cx, callee));
    if (win) {
      doc = win->GetExtantDocument();
    }
  }

  return doc;
}

NS_IMETHODIMP koContentUtils::GetDocumentFromCaller(nsIDOMDocument **callingDoc)
{
    NS_ENSURE_ARG_POINTER(callingDoc);
  
    *callingDoc = GetDocumentFromCaller();
    NS_IF_ADDREF(*callingDoc);
    return NS_OK;
}

nsIScriptGlobalObject *
koContentUtils::GetDynamicScriptGlobal(JSContext* aContext)
{
  nsIScriptContext *scriptCX = GetDynamicScriptContext(aContext);
  if (!scriptCX)
    return nsnull;
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
  JSContext *cx = nsnull;
  sThreadJSContextStack->Peek(&cx);

  if (cx) {
    nsIScriptGlobalObject *sgo = GetDynamicScriptGlobal(cx);
    nsCOMPtr<nsPIDOMWindow> win(do_QueryInterface(sgo));

    if (win) {
      return win->GetDocShell();
    }
  }

  return nsnull;
}

nsIDOMWindow *
koContentUtils::GetWindowFromCaller()
{
  JSContext *cx = nsnull;
  sThreadJSContextStack->Peek(&cx);

  if (cx) {
    nsIScriptGlobalObject *sgo = GetDynamicScriptGlobal(cx);
    nsCOMPtr<nsIDOMWindow> win(do_QueryInterface(sgo));

    if (win) {
      return win;
    }
  }

  return nsnull;
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

static nsModuleComponentInfo components[] =
{
  { 
    "Komodo ContentUtils Wrapper",
    KO_CONTENT_UTILS_CID,
    KO_CONTENT_UTILS_CONTRACTID,
    koContentUtilsConstructor,
    NULL, // RegistrationProc /* NULL if you dont need one */,
    NULL // UnregistrationProc /* NULL if you dont need one */
  }
};

NS_IMPL_NSGETMODULE("koContentUtilsModule", components)
