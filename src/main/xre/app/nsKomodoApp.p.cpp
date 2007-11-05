/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
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

#include "nsXULAppAPI.h"
#ifdef XP_WIN
#include <windows.h>
#include <stdlib.h>
#endif
#ifdef MOZILLA_1_8_BRANCH
#include "nsBuildID.h"
#else
#include "nsCOMPtr.h"
#include "nsILocalFile.h"
#include "nsStringGlue.h"
#endif

#include "koStart.h"

#ifdef MOZILLA_1_8_BRANCH
// NS_XRE_ENABLE_EXTENSION_MANAGER is required for extension install/uninstall
static const nsXREAppData kAppData = {
  sizeof(nsXREAppData),
  nsnull,
  "ActiveState",
  "PP_KO_PROD_NAME",
  NS_STRINGIFY(APP_VERSION),
  NS_STRINGIFY(PP_KO_BUILD_NUMBER),
  "{2cb9d397-8ec9-4211-bd89-7fea34120af6}",
  "Copyright (c) 1998 - 2007 ActiveState Software Inc.",
  NS_XRE_ENABLE_EXTENSION_MANAGER
};
#endif

int main(int argc, char* argv[])
{
    int rv;
    int retval = 0;
    KoStartOptions options;
    KoStartHandle mutex = KS_BAD_HANDLE;
    KoStartHandle theMan = KS_BAD_HANDLE;

#ifndef MOZILLA_1_8_BRANCH
    nsCOMPtr<nsILocalFile> appini;
    nsresult r = XRE_GetBinaryPath(argv[0], getter_AddRefs(appini));
    if (NS_FAILED(r)) {
      fprintf(stderr, "Couldn't calculate the application directory. [%s]\n", argv[0]);
      return 255;
    }
    appini->SetNativeLeafName(NS_LITERAL_CSTRING("application.ini"));
    nsXREAppData *appData;
    r = XRE_CreateAppData(appini, &appData);
    if (NS_FAILED(r)) {
      nsCAutoString pathName;
      appini->GetNativePath(pathName);
      fprintf(stderr, "Couldn't read application.ini [%s]\n", pathName.get());
      return 255;
    }
#else
    const nsXREAppData *appData = &kAppData;
#endif


    // Handle command line arguments.
    rv = KoStart_HandleArgV(argc, argv, &options);
    switch (rv) {
    case KS_ERROR:
        goto main_error;
    case KS_EXIT:
        goto main_exit;
    case KS_CONTINUE:
        break;
    }

    // Grab the mutex.
    mutex = KoStart_AcquireMutex();
    if (mutex == KS_BAD_HANDLE)  {
        goto main_error;
    }

    // Determine if this instance will be the running Komodo instance
    // (i.e. "the man") and handle any commandments appropriately.
    theMan = KoStart_WantToBeTheMan();
    if (theMan != KS_BAD_HANDLE) {
        KoStart_InitCommandments();
    }
    KoStart_IssueCommandments(&options, theMan != KS_BAD_HANDLE);

    // Release mutex and, if we are "the man", start the XRE.
    KoStart_ReleaseMutex(mutex);
    mutex = KS_BAD_HANDLE;
    if (theMan != KS_BAD_HANDLE) {
        int xreArgc;
        char** xreArgv;
        KoStart_PrepareForXRE(argc, argv, &xreArgc, &xreArgv);
        retval = XRE_main(xreArgc, xreArgv, appData);
    }
    goto main_exit;

main_error:
    retval = 1;
main_exit:
    if (mutex != KS_BAD_HANDLE) {
        KoStart_ReleaseMutex(mutex);
    }
    if (theMan != KS_BAD_HANDLE) {
        KoStart_ReleaseTheMan(theMan);
    }
    return retval;
}

#if defined( XP_WIN ) && defined( WIN32 ) && !defined(__GNUC__)
// We need WinMain in order to not be a console app.  This function is
// unused if we are a console application.
int WINAPI WinMain( HINSTANCE, HINSTANCE, LPSTR args, int )
{
    // Do the real work.
    return main( __argc, __argv );
}
#endif
