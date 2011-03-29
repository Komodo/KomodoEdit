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

#ifndef __PLUGIN_H__
#define __PLUGIN_H__

#include "npapi.h"
#include <npruntime.h>
#include "pluginbase.h"
#include "nsSciMoz.h"

class nsPluginInstance : public nsPluginInstanceBase
{
public:
  nsPluginInstance(NPP aInstance);
  ~nsPluginInstance();

  NPBool init(NPWindow* aWindow);
  void shut();
  NPBool isInitialized();

  // we need to provide implementation of this method as it will be
  // used by Mozilla to retrive the scriptable peer
  // and couple of other things on Unix
  NPError GetValue(NPPVariable variable, void *value);
  NPError SetWindow(NPWindow* pNPWindow);
  uint16  HandleEvent(void* event);
  // locals
  void getVersion(char* *aVersion);

  /*nsScriptablePeer*/
  SciMoz* getScriptablePeer();
  NPObject* getScriptableObject();
 
  // XXX Mook: this needs to go somewhere better
  NPP GetNPP() { return mInstance; }

private:
  NPP mInstance;
  NPBool mInitialized;
  SciMoz * mSciMoz;
  NPObject * mScriptableObject;

public:
  char mString[128];
};


class SciMozScriptableNPObject : public NPObject
{
protected:
    // Class member functions that do the real work
    void Deallocate();
    void Invalidate();
    bool HasMethod(NPIdentifier name);
    bool Invoke(NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool InvokeDefault(const NPVariant *args, uint32_t argCount, NPVariant *result);
    bool HasProperty(NPIdentifier name);
    bool GetProperty(NPIdentifier name, NPVariant *result);
    bool SetProperty(NPIdentifier name, const NPVariant *value);
    bool RemoveProperty(NPIdentifier name);
    bool Enumerate(NPIdentifier **identifier, uint32_t *count);
    bool Construct(const NPVariant *args, uint32_t argCount, NPVariant *result);
public:
    SciMozScriptableNPObject(NPP npp);
    ~SciMozScriptableNPObject();
    static NPObject* Allocate(NPP npp, NPClass *aClass);
    static SciMozScriptableNPObject* NewScriptableSciMoz(NPP npp, SciMoz * scimoz);

    /////////////////////////////
    // Static NPObject methods //
    /////////////////////////////
    static void _Deallocate(NPObject *npobj);
    static void _Invalidate(NPObject *npobj);
    static bool _HasMethod(NPObject *npobj, NPIdentifier name);
    static bool _Invoke(NPObject *npobj, NPIdentifier name, const NPVariant *args, uint32_t argCount, NPVariant *result);
    static bool _InvokeDefault(NPObject *npobj, const NPVariant *args, uint32_t argCount, NPVariant *result);
    static bool _HasProperty(NPObject * npobj, NPIdentifier name);
    static bool _GetProperty(NPObject *npobj, NPIdentifier name, NPVariant *result);
    static bool _SetProperty(NPObject *npobj, NPIdentifier name, const NPVariant *value);
    static bool _RemoveProperty(NPObject *npobj, NPIdentifier name);
    static bool _Enumerate(NPObject *npobj, NPIdentifier **identifier, uint32_t *count);
    static bool _Construct(NPObject *npobj, const NPVariant *args, uint32_t argCount, NPVariant *result);

    static NPClass _npclass;

protected:
    NPP m_Instance;
    SciMoz * mSciMoz;
};


#endif // __PLUGIN_H__
