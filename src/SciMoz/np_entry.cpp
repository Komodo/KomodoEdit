/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
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

//////////////////////////////////////////////////////////////
//
// Main plugin entry point implementation
//
#include "npapi.h"
#include "npfunctions.h"
#include <stddef.h>

#ifndef HIBYTE
#define HIBYTE(x) ((((uint32_t)(x)) & 0xff00) >> 8)
#endif

NPNetscapeFuncs NPNFuncs;

// NP_GetEntryPoints is only called by the plugin host on win32 and osx, but
// it's also useful on other unix.
NPError OSCALL NP_GetEntryPoints(NPPluginFuncs* pFuncs)
{
  if(pFuncs == NULL)
    return NPERR_INVALID_FUNCTABLE_ERROR;

  if(pFuncs->size < (offsetof(NPPluginFuncs, setvalue) + sizeof(void*)))
    return NPERR_INVALID_FUNCTABLE_ERROR;

  pFuncs->version       = (NP_VERSION_MAJOR << 8) | NP_VERSION_MINOR;
  pFuncs->newp          = NPP_New;
  pFuncs->destroy       = NPP_Destroy;
  pFuncs->setwindow     = NPP_SetWindow;
  pFuncs->newstream     = NPP_NewStream;
  pFuncs->destroystream = NPP_DestroyStream;
  pFuncs->asfile        = NPP_StreamAsFile;
  pFuncs->writeready    = NPP_WriteReady;
  pFuncs->write         = NPP_Write;
  pFuncs->print         = NPP_Print;
  pFuncs->event         = NPP_HandleEvent;
  pFuncs->urlnotify     = NPP_URLNotify;
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

char *NPP_GetMIMEDescription();

char *
NP_GetMIMEDescription()
{
  return NPP_GetMIMEDescription();
}

NPError
NP_GetValue(void* future, NPPVariable variable, void *value)
{
  return NPP_GetValue((NPP_t *)future, variable, value);
}

NPError OSCALL
NP_Initialize(NPNetscapeFuncs* pFuncs
#if defined(XP_UNIX) && !defined(XP_MACOSX)
              , NPPluginFuncs* pluginFuncs
#endif
              )
{
  if(pFuncs == NULL)
    return NPERR_INVALID_FUNCTABLE_ERROR;

  if(HIBYTE(pFuncs->version) > NP_VERSION_MAJOR)
    return NPERR_INCOMPATIBLE_VERSION_ERROR;

  if(pFuncs->size < sizeof(NPNetscapeFuncs))
    return NPERR_INVALID_FUNCTABLE_ERROR;

  NPNFuncs.size                    = pFuncs->size;
  NPNFuncs.version                 = pFuncs->version;
  NPNFuncs.geturlnotify            = pFuncs->geturlnotify;
  NPNFuncs.geturl                  = pFuncs->geturl;
  NPNFuncs.posturlnotify           = pFuncs->posturlnotify;
  NPNFuncs.posturl                 = pFuncs->posturl;
  NPNFuncs.requestread             = pFuncs->requestread;
  NPNFuncs.newstream               = pFuncs->newstream;
  NPNFuncs.write                   = pFuncs->write;
  NPNFuncs.destroystream           = pFuncs->destroystream;
  NPNFuncs.status                  = pFuncs->status;
  NPNFuncs.uagent                  = pFuncs->uagent;
  NPNFuncs.memalloc                = pFuncs->memalloc;
  NPNFuncs.memfree                 = pFuncs->memfree;
  NPNFuncs.memflush                = pFuncs->memflush;
  NPNFuncs.reloadplugins           = pFuncs->reloadplugins;
  NPNFuncs.getJavaEnv              = NULL;
  NPNFuncs.getJavaPeer             = NULL;
  NPNFuncs.getvalue                = pFuncs->getvalue;
  NPNFuncs.setvalue                = pFuncs->setvalue;
  NPNFuncs.invalidaterect          = pFuncs->invalidaterect;
  NPNFuncs.invalidateregion        = pFuncs->invalidateregion;
  NPNFuncs.forceredraw             = pFuncs->forceredraw;
  NPNFuncs.getstringidentifier     = pFuncs->getstringidentifier;
  NPNFuncs.getstringidentifiers    = pFuncs->getstringidentifiers;
  NPNFuncs.getintidentifier        = pFuncs->getintidentifier;
  NPNFuncs.identifierisstring      = pFuncs->identifierisstring;
  NPNFuncs.utf8fromidentifier      = pFuncs->utf8fromidentifier;
  NPNFuncs.intfromidentifier       = pFuncs->intfromidentifier;
  NPNFuncs.createobject            = pFuncs->createobject;
  NPNFuncs.retainobject            = pFuncs->retainobject;
  NPNFuncs.releaseobject           = pFuncs->releaseobject;
  NPNFuncs.invoke                  = pFuncs->invoke;
  NPNFuncs.invokeDefault           = pFuncs->invokeDefault;
  NPNFuncs.evaluate                = pFuncs->evaluate;
  NPNFuncs.getproperty             = pFuncs->getproperty;
  NPNFuncs.setproperty             = pFuncs->setproperty;
  NPNFuncs.removeproperty          = pFuncs->removeproperty;
  NPNFuncs.hasproperty             = pFuncs->hasproperty;
  NPNFuncs.hasmethod               = pFuncs->hasmethod;
  NPNFuncs.releasevariantvalue     = pFuncs->releasevariantvalue;
  NPNFuncs.setexception            = pFuncs->setexception;

#if defined(XP_UNIX) && !defined(XP_MACOSX)
  /*
   * Set up the plugin function table that Netscape will use to
   * call us.  Netscape needs to know about our version and size
   * and have a UniversalProcPointer for every function we
   * implement.
   */
  pFuncs->size = sizeof(NPPluginFuncs);
  return NP_GetEntryPoints(pluginFuncs);
#endif

  return NPERR_NO_ERROR;
}

NPError OSCALL NP_Shutdown()
{
  return NPERR_NO_ERROR;
}
