/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/* ***** BEGIN LICENSE BLOCK *****
 * Version: NPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Netscape Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/NPL/
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
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or 
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the NPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the NPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

#include "plugin.h"
#include "npfunctions.h"

//#define SCIMOZ_DEBUG

#define MIME_TYPES_HANDLED  "application/x-scimoz-plugin"
#define PLUGIN_NAME         "Scintilla"
#define MIME_TYPES_DESCRIPTION  MIME_TYPES_HANDLED"::"PLUGIN_NAME
#define PLUGIN_DESCRIPTION  PLUGIN_NAME " for Mozilla" 

char* NPP_GetMIMEDescription(void)
{
    return(MIME_TYPES_DESCRIPTION);
}

// get values per plugin
NPError NS_PluginGetValue(NPPVariable aVariable, void *aValue)
{
  NPError err = NPERR_NO_ERROR;
  switch (aVariable) {
    case NPPVpluginNameString:
      *((char **)aValue) = PLUGIN_NAME;
      break;
    case NPPVpluginDescriptionString:
      *((char **)aValue) = PLUGIN_DESCRIPTION;
      break;
#ifdef GTK2_XEMBED
    case NPPVpluginNeedsXEmbed:
        *((PRBool *)aValue) = PR_TRUE;
        break;
#endif
    default:
      err = NPERR_INVALID_PARAM;
      break;
  }
  return err;
}

void NPP_Shutdown(void)
{
}

//////////////////////////////////////
//
// general initialization and shutdown
//
NPError NS_PluginInitialize()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"NS_PluginInitialize\n");
#endif
  return NPERR_NO_ERROR;
}

void NS_PluginShutdown()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"NS_PluginShutdown\n");
#endif
}

/////////////////////////////////////////////////////////////
//
// construction and destruction of our plugin instance object
//
nsPluginInstanceBase * NS_NewPluginInstance(nsPluginCreateData * aCreateDataStruct)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"NS_NewPluginInstance %p\n", aCreateDataStruct);
#endif 
  if(!aCreateDataStruct)
    return NULL;
#ifdef USE_LICENSE
    if (!CheckLicense()) {
            return NULL;
    }
#endif /* USE_LICENSE */

#if USE_CARBON
    // Check if the browser supports the CoreGraphics drawing model
    NPBool supportsCoreGraphics = FALSE;
    NPError err = NPN_GetValue(aCreateDataStruct->instance,
                                    NPNVsupportsCoreGraphicsBool,
                                    &supportsCoreGraphics);
    if (err != NPERR_NO_ERROR || !supportsCoreGraphics) 
        return NULL;

    // Set the drawing model
    err = NPN_SetValue(aCreateDataStruct->instance,
                            NPPVpluginDrawingModel,
                            (void*)NPDrawingModelCoreGraphics);
    if (err != NPERR_NO_ERROR) 
        return NULL;
#endif

  nsPluginInstance * plugin = new nsPluginInstance(aCreateDataStruct->instance);
  return plugin;
}

void NS_DestroyPluginInstance(nsPluginInstanceBase * aPlugin)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"NS_DestroyPluginInstance %p\n", aPlugin);
#endif
    if (aPlugin)
        delete (nsPluginInstance *)aPlugin;
}

////////////////////////////////////////
//
// nsPluginInstance class implementation
//
nsPluginInstance::nsPluginInstance(NPP aInstance) : nsPluginInstanceBase(),
  mInstance(aInstance),
  mInitialized(FALSE),
  mScriptableObject(NULL)
{
  mString[0] = '\0';
  mSciMoz = new SciMoz(this);
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance::nsPluginInstance %p inst %p peer %p\n", this, mInstance, mSciMoz);
#endif 
}

nsPluginInstance::~nsPluginInstance()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance::~nsPluginInstance %p inst %p peer %p\n", this, mInstance, mSciMoz);
#endif 
}

NPBool nsPluginInstance::init(NPWindow* aWindow)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p init: window %p\n",this,aWindow);
#endif 
  if(aWindow == NULL)
    return FALSE;

  SetWindow(aWindow);
  mInitialized = TRUE;
  return TRUE;
}

NPError
nsPluginInstance::SetWindow(NPWindow* window)
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p SetWindow: %p\n", this, window);
#endif 
    // nsresult result;

    /*
    * PLUGIN DEVELOPERS:
    *	Before setting window to point to the
    *	new window, you may wish to compare the new window
    *	info to the previous window (if any) to note window
    *	size changes, etc.
    */
    return mSciMoz->PlatformSetWindow(window);
}

uint16 nsPluginInstance::HandleEvent(void* event)
{
    return mSciMoz->PlatformHandleEvent(event);
}

void nsPluginInstance::shut()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p shut\n", this);
#endif 
  mSciMoz = NULL;
  mInitialized = FALSE;
}

NPBool nsPluginInstance::isInitialized()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p isInitialized: %d\n", this, mInitialized);
#endif 
  return mInitialized;
}

void nsPluginInstance::getVersion(char* *aVersion)
{
  const char *ua = NPN_UserAgent(mInstance);
  char*& version = *aVersion;
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p getVersion %s\n", this, ua);
#endif   

  version = (char*)NPN_MemAlloc(strlen(ua) + 1);
  if (version)
    strcpy(version, ua);
}

// ==============================
// ! Scriptability related code !
// ==============================
//
// here the plugin is asked by Mozilla to tell if it is scriptable
// we should return a valid interface id and a pointer to 
// nsScriptablePeer interface which we should have implemented
// and which should be defined in the corressponding *.xpt file
// in the bin/components folder
NPError	nsPluginInstance::GetValue(NPPVariable aVariable, void *aValue)
{
  NPError rv = NPERR_NO_ERROR;
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p GetValue\n", this);
#endif   

  switch (aVariable) {
    case NPPVpluginScriptableNPObject:// Scriptable plugin interface (for accessing from javascript)
      *(NPObject **)aValue = this->getScriptableObject();

    default:
      rv = NS_PluginGetValue(aVariable, aValue);
      break;
  }

  return rv;
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
NPObject* SciMozScriptableNPObject::Allocate(NPP npp, NPClass *aClass) {
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
    #ifdef SCIMOZ_DEBUG
        printf("SciMozScriptableNPObject::HasMethod:: '%s'\n", NPN_UTF8FromIdentifier(name));
    #endif /* SCIMOZ_DEBUG */
    bool result = mSciMoz->HasMethod(name);
    #ifdef SCIMOZ_DEBUG
        printf("%s: %s = %s\n", __FUNCTION__, NPN_UTF8FromIdentifier(name), result ? "yes" : "no");
    #endif /* SCIMOZ_DEBUG */
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
bool SciMozScriptableNPObject::InvokeDefault(const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return false;
}

// static
bool SciMozScriptableNPObject::_HasProperty(NPObject *obj, NPIdentifier name) {
    return ((SciMozScriptableNPObject*)obj)->HasProperty(name);
}
bool SciMozScriptableNPObject::HasProperty(NPIdentifier name) {
    #ifdef SCIMOZ_DEBUG
        printf("SciMozScriptableNPObject::HasProperty:: '%s'\n", NPN_UTF8FromIdentifier(name));
    #endif /* SCIMOZ_DEBUG */
    bool result = mSciMoz->HasProperty(name);
    #ifdef SCIMOZ_DEBUG
        printf("%s: %s = %s\n", __FUNCTION__, NPN_UTF8FromIdentifier(name), result ? "yes" : "no");
    #endif /* SCIMOZ_DEBUG */
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
bool SciMozScriptableNPObject::RemoveProperty(NPIdentifier name) {
    return false;
}

// static
bool SciMozScriptableNPObject::_Enumerate(NPObject *obj, NPIdentifier **identifier, uint32_t *count) {
    return ((SciMozScriptableNPObject*)obj)->Enumerate(identifier, count);
}
bool SciMozScriptableNPObject::Enumerate(NPIdentifier **identifier, uint32_t *count) {
    return false;
}

// static
bool SciMozScriptableNPObject::_Construct(NPObject *obj, const NPVariant *args, uint32_t argCount, NPVariant *result) {
    return ((SciMozScriptableNPObject*)obj)->Construct(args, argCount, result);
}
bool SciMozScriptableNPObject::Construct(const NPVariant *args, uint32_t argCount, NPVariant *result) {
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

NPObject* nsPluginInstance::getScriptableObject()
{
#ifdef SCIMOZ_DEBUG
    fprintf(stderr,"nsPluginInstance:: %p getScriptableObject\n", this);
#endif
  if (!mScriptableObject) {
    mScriptableObject = (NPObject *) SciMozScriptableNPObject::NewScriptableSciMoz(this->mInstance, this->mSciMoz);
    if(!mScriptableObject)
      return NULL;
  }

  NPN_RetainObject(mScriptableObject);

  return mScriptableObject;
}
