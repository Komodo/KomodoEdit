/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is mozilla.org code.
 *
 * The Initial Developer of the Original Code is
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1998
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Josh Aas <josh@mozilla.com>
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

#include "plugin.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stddef.h>

/**
 * For understanding NPAPI plugins, I suggest taking a good read of:
 * http://colonelpanic.net/2009/03/building-a-firefox-plugin-part-one/
 *
 * This gives a good description of the necessary functions and how they
 * differ between platforms.
 */

#define PLUGIN_NAME             "Komodo Editor"
#define PLUGIN_DESCRIPTION      "The ActiveState Komodo Editor - do not disable"
#define PLUGIN_VERSION          "1.0.0.0"
#define MIME_TYPES_DESCRIPTION  "application/x-scimoz-plugin::Scintilla"

#include "nsSciMoz.h"

NPNetscapeFuncs *browserNPNFuncs = NULL;

/**
 * Exported plugin NP_ functions - called by Mozilla when loading plugins.
 */

/**
 * Windows version of NP_Initialize.
 */
#if defined(XP_WIN) || defined(XP_MACOSX)
#define NP_EXPORT(__type) __type
NP_EXPORT(NPError) OSCALL 
NP_Initialize(NPNetscapeFuncs* bFuncs)
{
  browserNPNFuncs = bFuncs;

  return NPERR_NO_ERROR;
}
#endif /* XP_WIN or XP_MACOSX */

/**
 * Linux version of NP_Initialize.
 */
#if defined(XP_UNIX) && !defined(XP_MACOSX)
NP_EXPORT(NPError)
NP_Initialize(NPNetscapeFuncs* bFuncs, NPPluginFuncs* pFuncs)
{
  browserNPNFuncs = bFuncs;

  // Check the size of the provided structure based on the offset of the
  // last member we need.
  if (pFuncs->size < (offsetof(NPPluginFuncs, setvalue) + sizeof(void*)))
    return NPERR_INVALID_FUNCTABLE_ERROR;

  pFuncs->newp = NPP_New;
  pFuncs->destroy = NPP_Destroy;
  pFuncs->setwindow = NPP_SetWindow;
  pFuncs->newstream = NPP_NewStream;
  pFuncs->destroystream = NPP_DestroyStream;
  pFuncs->asfile = NPP_StreamAsFile;
  pFuncs->writeready = NPP_WriteReady;
  pFuncs->write = NPP_Write;
  pFuncs->print = NPP_Print;
  pFuncs->event = NPP_HandleEvent;
  pFuncs->urlnotify = NPP_URLNotify;
  pFuncs->getvalue = NPP_GetValue;
  pFuncs->setvalue = NPP_SetValue;

  return NPERR_NO_ERROR;
}
#endif /* XP_UNIX && !XP_MACOSX*/

// NP_GetEntryPoints is only called by the plugin host on win32 and osx.
#if defined(XP_WIN) || defined(XP_MACOSX)
NPError OSCALL
NP_GetEntryPoints(NPPluginFuncs* pFuncs)
{
  if(pFuncs == NULL)
    return NPERR_INVALID_FUNCTABLE_ERROR;

  if(pFuncs->size < (offsetof(NPPluginFuncs, setvalue) + sizeof(void*)))
    return NPERR_INVALID_FUNCTABLE_ERROR;

  pFuncs->version       = (NP_VERSION_MAJOR << 8) | NP_VERSION_MINOR;
  pFuncs->newp          = NPP_New;
  pFuncs->destroy       = NPP_Destroy;
  pFuncs->setwindow     = NPP_SetWindow;
  pFuncs->newstream     = NULL;
  pFuncs->destroystream = NULL;
  pFuncs->asfile        = NULL;
  pFuncs->writeready    = NULL;
  pFuncs->write         = NULL;
  pFuncs->print         = NULL;
  pFuncs->event         = NPP_HandleEvent;
  pFuncs->urlnotify     = NULL;
  pFuncs->javaClass     = NULL;
  pFuncs->getvalue      = NPP_GetValue;
  pFuncs->setvalue      = NPP_SetValue;
#if 0
  /* not implemented in gecko */
  gotfocus;
  lostfocus;
  /* optional, we don't implement */
  urlredirectnotify;
  clearsitedata;
  getsiteswithdata;
#endif

  return NPERR_NO_ERROR;
}
#endif /* XP_WIN || XP_MACOSX */

NP_EXPORT(char*)
NP_GetPluginVersion()
{
  return PLUGIN_VERSION;
}

NP_EXPORT(const char*)
NP_GetMIMEDescription()
{
  return(MIME_TYPES_DESCRIPTION);
}

NP_EXPORT(NPError)
NP_GetValue(void* instance, NPPVariable aVariable, void* aValue) {
  return NPP_GetValue((NPP)instance, aVariable, aValue);
}

NP_EXPORT(NPError) OSCALL 
NP_Shutdown()
{
  return NPERR_NO_ERROR;
}


/**
 * NPP_ functions that the plugin must implement.
 */

NPError
NPP_New(NPMIMEType /*pluginType*/, NPP instance, uint16_t /*mode*/, int16_t /*argc*/, char** /*argn[]*/, char** /*argv[]*/, NPSavedData* /*saved*/) {

#if defined(USE_COCOA)

#if XP_MACOSX_USE_CORE_ANIMATION
#if XP_MACOSX_USE_INVALIDATING_CORE_ANIMATION
  // Check if the browser supports the CoreAnimation drawing model
  NPBool supportsCoreAnimationInvalidating = FALSE;
  NPError err = NPN_GetValue(instance, NPNVsupportsInvalidatingCoreAnimationBool,
                             &supportsCoreAnimationInvalidating);
  if (err != NPERR_NO_ERROR || !supportsCoreAnimationInvalidating) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
  // Set the drawing model
  err = NPN_SetValue(instance, NPPVpluginDrawingModel,
                     (void*)NPDrawingModelInvalidatingCoreAnimation);
  if (err != NPERR_NO_ERROR) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
#else
  // Check if the browser supports the CoreAnimation drawing model
  NPBool supportsCoreAnimation = FALSE;
  NPError err = NPN_GetValue(instance, NPNVsupportsCoreAnimationBool,
                             &supportsCoreAnimation);
  if (err != NPERR_NO_ERROR || !supportsCoreAnimation) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
  // Set the drawing model
  err = NPN_SetValue(instance, NPPVpluginDrawingModel,
                     (void*)NPDrawingModelCoreAnimation);
  if (err != NPERR_NO_ERROR) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
#endif
#else
  // Check if the browser supports the CoreGraphics drawing model
  NPBool supportsCoreGraphics = FALSE;
  NPError err = NPN_GetValue(instance, NPNVsupportsCoreGraphicsBool,
                             &supportsCoreGraphics);
  if (err != NPERR_NO_ERROR || !supportsCoreGraphics) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
  // Set the drawing model
  err = NPN_SetValue(instance, NPPVpluginDrawingModel,
                     (void*)NPDrawingModelCoreGraphics);
  if (err != NPERR_NO_ERROR) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
#endif /* XP_MACOSX_USE_CORE_ANIMATION */

  NPBool supportsCocoaEvents = FALSE;
  // Verify the host supports the Cocoa event model
  err = NPN_GetValue(instance, NPNVsupportsCocoaBool, &supportsCocoaEvents);
  if (err != NPERR_NO_ERROR || !supportsCocoaEvents) {
    return NPERR_INCOMPATIBLE_VERSION_ERROR;
  }
  NPN_SetValue(instance, NPPVpluginEventModel, (void *) NPEventModelCocoa);
#endif /* USE_COCOA */

  // Create our new SciMoz plugin instance.
  SciMozPluginInstance* scimozPlugin = new SciMozPluginInstance(instance);
  if (!scimozPlugin)
    return NPERR_OUT_OF_MEMORY_ERROR;
  instance->pdata = scimozPlugin;

  return NPERR_NO_ERROR;
}

NPError
NPP_Destroy(NPP instance, NPSavedData** /*save*/) {
  SciMozPluginInstance* scimozPlugin = (SciMozPluginInstance*)(instance->pdata);
  delete scimozPlugin;
  return NPERR_NO_ERROR;
}

NPError
NPP_GetValue(NPP instance, NPPVariable variable, void *value) {
#ifdef SCIMOZ_DEBUG
  fprintf(stderr,"NPP_GetValue:: GetValue\n");
#endif   

  switch (variable) {
    case NPPVpluginNameString:
      *((char**)value) = (char *)PLUGIN_NAME;
      return NPERR_NO_ERROR;
    case NPPVpluginDescriptionString:
      *((char**)value) = (char *)PLUGIN_DESCRIPTION;
      return NPERR_NO_ERROR;
#ifdef GTK2_XEMBED
    case NPPVpluginNeedsXEmbed:
      *((bool *)value) = PR_TRUE;
      return NPERR_NO_ERROR;
#endif
    case NPPVpluginScriptableNPObject:// Scriptable plugin interface (for accessing from javascript)
    {
      SciMozPluginInstance* scimozPlugin = (SciMozPluginInstance*)(instance->pdata);
      *(NPObject **)value = scimozPlugin->getScriptableObject();
      return NPERR_NO_ERROR;
    }
#ifdef XP_MACOSX_USE_CORE_ANIMATION
    case NPPVpluginCoreAnimationLayer:
    {
      SciMozPluginInstance* scimozPlugin = (SciMozPluginInstance*)(instance->pdata);
      *((void **)value) = scimozPlugin->GetCoreAnimationLayer();
      return NPERR_NO_ERROR;
    }
#endif
    default:
      return NPERR_INVALID_PARAM;
  }
}

NPError
NPP_SetWindow(NPP instance, NPWindow* window) {
  SciMozPluginInstance* scimozPlugin = (SciMozPluginInstance*)(instance->pdata);
  scimozPlugin->SetWindow(window);
  return NPERR_NO_ERROR;
}

int16_t
NPP_HandleEvent(NPP instance, void* event) {
  SciMozPluginInstance *scimozPlugin = (SciMozPluginInstance*)(instance->pdata);
  return scimozPlugin->HandleEvent(event);
}


/**
 * The rest are generic stubs - for the plugin functions that we don't use.
 */

NPError
NPP_NewStream(NPP /*instance*/, NPMIMEType /*type*/, NPStream* /*stream*/, NPBool /*seekable*/, uint16_t* /*stype*/) {
  return NPERR_GENERIC_ERROR;
}

NPError
NPP_DestroyStream(NPP /*instance*/, NPStream* /*stream*/, NPReason /*reason*/) {
  return NPERR_GENERIC_ERROR;
}

int32_t
NPP_WriteReady(NPP /*instance*/, NPStream* /*stream*/) {
  return 0;
}

int32_t
NPP_Write(NPP /*instance*/, NPStream* /*stream*/, int32_t /*offset*/, int32_t /*len*/, void* /*buffer*/) {
  return 0;
}

void
NPP_StreamAsFile(NPP /*instance*/, NPStream* /*stream*/, const char* /*fname*/) {

}

void
NPP_Print(NPP /*instance*/, NPPrint* /*platformPrint*/) {

}

void
NPP_URLNotify(NPP /*instance*/, const char* /*URL*/, NPReason /*reason*/, void* /*notifyData*/) {

}

NPError
NPP_SetValue(NPP /*instance*/, NPNVariable /*variable*/, void * /*value*/) {
  return NPERR_GENERIC_ERROR;
}



/**
 * SciMoz plugin instance (really just a handle on the SciMoz instance).
 */

SciMozPluginInstance::SciMozPluginInstance(NPP aInstance) :
    nppInstance(aInstance),
    scimozScriptableObject(NULL)
{
    scimozInstance = new SciMoz(this);
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMozPluginInstance::SciMozPluginInstance %p inst %p peer %p\n", this, nppInstance, scimozInstance);
#endif 
}

SciMozPluginInstance::~SciMozPluginInstance()
{
    delete scimozInstance;
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMozPluginInstance::~SciMozPluginInstance %p inst %p peer %p\n", this, nppInstance, scimozInstance);
#endif
}

NPError
SciMozPluginInstance::SetWindow(NPWindow* window)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMozPluginInstance:: %p SetWindow: %p\n", this, window);
#endif 
    // nsresult result;

    /*
    * PLUGIN DEVELOPERS:
    *	Before setting window to point to the
    *	new window, you may wish to compare the new window
    *	info to the previous window (if any) to note window
    *	size changes, etc.
    */
    if (!NS_SUCCEEDED(scimozInstance->PlatformSetWindow(window))) {
        return NPERR_INVALID_PLUGIN_ERROR;
    }
    return NPERR_NO_ERROR;
}

uint16_t
SciMozPluginInstance::HandleEvent(void* event)
{
    return scimozInstance->PlatformHandleEvent(event);
}

#ifdef XP_MACOSX_USE_CORE_ANIMATION
void *
SciMozPluginInstance::GetCoreAnimationLayer()
{
    return scimozInstance->GetCoreAnimationLayer();
}
#endif

NPObject*
SciMozPluginInstance::getScriptableObject()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"SciMozPluginInstance:: %p getScriptableObject\n", this);
#endif
  if (!scimozScriptableObject) {
    scimozScriptableObject = (NPObject *) SciMozScriptableNPObject::NewScriptableSciMoz(this->nppInstance, this->scimozInstance);
    if(!scimozScriptableObject)
      return NULL;
  }

  NPN_RetainObject(scimozScriptableObject);

  return scimozScriptableObject;
}




// ==============================
// ! Scriptability related code !
// ==============================
//


SciMozScriptableNPObject::SciMozScriptableNPObject(NPP npp) : m_Instance(npp)
{
}

SciMozScriptableNPObject::~SciMozScriptableNPObject()
{
}

// static
NPObject* SciMozScriptableNPObject::Allocate(NPP npp, NPClass * /*aClass*/) {
    return new SciMozScriptableNPObject(npp);
}

// static
void SciMozScriptableNPObject::_Invalidate(NPObject *obj) {
    ((SciMozScriptableNPObject*)obj)->Invalidate();
}
void SciMozScriptableNPObject::Invalidate() {
    // Invalidate the control however you wish
}

// static
void SciMozScriptableNPObject::_Deallocate(NPObject *obj) {
    ((SciMozScriptableNPObject*)obj)->Deallocate();
    delete ((SciMozScriptableNPObject*)obj);
}
void SciMozScriptableNPObject::Deallocate() {
    // Do any cleanup needed
}

// static
bool SciMozScriptableNPObject::_HasMethod(NPObject *obj, NPIdentifier name) {
    return ((SciMozScriptableNPObject*)obj)->HasMethod(name);
}
bool SciMozScriptableNPObject::HasMethod(NPIdentifier name) {
    #ifdef SCIMOZ_DEBUG_VERBOSE_VERBOSE
        printf("SciMozScriptableNPObject::HasMethod:: '%s'\n", NPN_UTF8FromIdentifier(name));
    #endif /* SCIMOZ_DEBUG_VERBOSE_VERBOSE */
    bool result = mSciMoz->HasMethod(name);
    #ifdef SCIMOZ_DEBUG_VERBOSE_VERBOSE
        printf("%s: %s = %s\n", __FUNCTION__, NPN_UTF8FromIdentifier(name), result ? "yes" : "no");
    #endif /* SCIMOZ_DEBUG_VERBOSE_VERBOSE */
    return result;
}

// static
bool SciMozScriptableNPObject::_Invoke(NPObject *obj, NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return ((SciMozScriptableNPObject*)obj)->Invoke(name, args, argCount, result);
}
bool SciMozScriptableNPObject::Invoke(NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return mSciMoz->Invoke(m_Instance, name, args, argCount, result);
}

// static
bool SciMozScriptableNPObject::_InvokeDefault(NPObject *obj, const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return ((SciMozScriptableNPObject*)obj)->InvokeDefault(args, argCount, result);
}
bool SciMozScriptableNPObject::InvokeDefault(const NPVariant * /*args*/, uint32_t /*argCount*/, NPVariant * /*result*/) {
    return false;
}

// static
bool SciMozScriptableNPObject::_HasProperty(NPObject *obj, NPIdentifier name) {
    return ((SciMozScriptableNPObject*)obj)->HasProperty(name);
}
bool SciMozScriptableNPObject::HasProperty(NPIdentifier name) {
    #ifdef SCIMOZ_DEBUG_VERBOSE_VERBOSE
        printf("SciMozScriptableNPObject::HasProperty:: '%s'\n", NPN_UTF8FromIdentifier(name));
    #endif /* SCIMOZ_DEBUG_VERBOSE_VERBOSE */
    bool result = mSciMoz->HasProperty(name);
    #ifdef SCIMOZ_DEBUG_VERBOSE_VERBOSE
        printf("%s: %s = %s\n", __FUNCTION__, NPN_UTF8FromIdentifier(name), result ? "yes" : "no");
    #endif /* SCIMOZ_DEBUG_VERBOSE_VERBOSE */
    return result;
}

// static
bool SciMozScriptableNPObject::_GetProperty(NPObject *obj, NPIdentifier name, NPVariant *result) {
    return ((SciMozScriptableNPObject*)obj)->GetProperty(name, result);
}
bool SciMozScriptableNPObject::GetProperty(NPIdentifier name, NPVariant *result) {
    return mSciMoz->GetProperty(name, result);
}

// static
bool SciMozScriptableNPObject::_SetProperty(NPObject *obj, NPIdentifier name, const NPVariant *value) {
    return ((SciMozScriptableNPObject*)obj)->SetProperty(name, value);
}
bool SciMozScriptableNPObject::SetProperty(NPIdentifier name, const NPVariant *value) {
    return mSciMoz->SetProperty(name, value);
}

// static
bool SciMozScriptableNPObject::_RemoveProperty(NPObject *obj, NPIdentifier name) {
    return ((SciMozScriptableNPObject*)obj)->RemoveProperty(name);
}
bool SciMozScriptableNPObject::RemoveProperty(NPIdentifier /*name*/) {
    return false;
}

// static
bool SciMozScriptableNPObject::_Enumerate(NPObject *obj, NPIdentifier **identifier, uint32_t *count) {
    return ((SciMozScriptableNPObject*)obj)->Enumerate(identifier, count);
}
bool SciMozScriptableNPObject::Enumerate(NPIdentifier ** /*identifier*/, uint32_t * /*count*/) {
    return false;
}

// static
bool SciMozScriptableNPObject::_Construct(NPObject *obj, const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return ((SciMozScriptableNPObject*)obj)->Construct(args, argCount, result);
}
bool SciMozScriptableNPObject::Construct(const NPVariant * /*args*/, uint32_t /*argCount*/, NPVariant * /*result*/) {
    return false;
}


NPClass SciMozScriptableNPObject::_npclass = {
    NP_CLASS_STRUCT_VERSION,
    SciMozScriptableNPObject::Allocate,
    SciMozScriptableNPObject::_Deallocate,
    SciMozScriptableNPObject::_Invalidate,
    SciMozScriptableNPObject::_HasMethod,
    SciMozScriptableNPObject::_Invoke,
    SciMozScriptableNPObject::_InvokeDefault,
    SciMozScriptableNPObject::_HasProperty,
    SciMozScriptableNPObject::_GetProperty,
    SciMozScriptableNPObject::_SetProperty,
    SciMozScriptableNPObject::_RemoveProperty,
    SciMozScriptableNPObject::_Enumerate,
    SciMozScriptableNPObject::_Construct
};


// static
SciMozScriptableNPObject* SciMozScriptableNPObject::NewScriptableSciMoz(NPP npp, SciMoz * scimoz) {
    SciMozScriptableNPObject* newObj = (SciMozScriptableNPObject*)NPN_CreateObject(npp, &SciMozScriptableNPObject::_npclass);
    newObj->mSciMoz = scimoz;
    return newObj;
}
