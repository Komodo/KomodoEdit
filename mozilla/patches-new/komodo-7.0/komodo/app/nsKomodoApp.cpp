/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

#include "nsXULAppAPI.h"
#ifdef XP_WIN
#include <windows.h>
#include <stdlib.h>
#endif
#include "nsCOMPtr.h"
#include "nsILocalFile.h"
#include "nsStringGlue.h"

#ifdef XP_WIN
#ifdef KOMODO_USE_WMAIN
// we want a wmain entry point
#include "nsWindowsWMain.cpp"
#endif
#endif

#include "koStart.h"

int main(int argc, char* argv[])
{
    nsCOMPtr<nsILocalFile> appini;
    nsresult rv = XRE_GetBinaryPath(argv[0], getter_AddRefs(appini));
    if (NS_FAILED(rv)) {
      fprintf(stderr, "Couldn't calculate the application directory.");
      return 255;
    }
    appini->SetNativeLeafName(NS_LITERAL_CSTRING("application.ini"));
    nsXREAppData *appData;
    rv = XRE_CreateAppData(appini, &appData);
    if (NS_FAILED(rv)) {
      fprintf(stderr, "Couldn't read application.ini");
      return 255;
    }

#ifdef KOSTART_PLACEHOLDER
    // The special Komodo startup gymnastics are only done when the
    // properly configured koStart.h|c are built in as part of the
    // *Komodo* build. After the default Mozilla build (in
    // Mozilla-devel/...) we simply start the XRE.
    return XRE_main(argc, argv, appData);
#else
    int rv;
    int retval = 0;
    KoStartOptions options;
    KoStartHandle mutex = KS_BAD_HANDLE;
    KoStartHandle theMan = KS_BAD_HANDLE;

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
#endif // USE_KOSTART
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
