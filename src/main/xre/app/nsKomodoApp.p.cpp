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

#include "nsXPCOMGlue.h"
#include "nsXULAppAPI.h"
#if defined(XP_WIN)
#include <windows.h>
#include <stdlib.h>
#elif defined(XP_UNIX)
#include <sys/time.h>
#include <sys/resource.h>
#endif

#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "plstr.h"
#include "prprf.h"
#include "prenv.h"

#include "nsCOMPtr.h"
#include "nsILocalFile.h"
#include "nsStringGlue.h"

#ifdef XP_WIN
// we want a wmain entry point
#include "nsWindowsWMain.cpp"
#define snprintf _snprintf
#define strcasecmp _stricmp
#endif
#include "BinaryPath.h"

#include "nsXPCOMPrivate.h" // for MAXPATHLEN and XPCOM_DLL

#include "mozilla/Telemetry.h"

#include "koStart.h"

static void Output(const char *fmt, ... )
{
  va_list ap;
  va_start(ap, fmt);

#if defined(XP_WIN) && !MOZ_WINCONSOLE
  PRUnichar msg[2048];
  _vsnwprintf(msg, sizeof(msg)/sizeof(msg[0]), NS_ConvertUTF8toUTF16(fmt).get(), ap);
  MessageBoxW(NULL, msg, L"XULRunner", MB_OK | MB_ICONERROR);
#else
  vfprintf(stderr, fmt, ap);
#endif

  va_end(ap);
}

/**
 * A helper class which calls NS_LogInit/NS_LogTerm in its scope.
 */
class ScopedLogging
{
public:
  ScopedLogging() { NS_LogInit(); }
  ~ScopedLogging() { NS_LogTerm(); }
};

XRE_CreateAppDataType XRE_CreateAppData;
XRE_FreeAppDataType XRE_FreeAppData;
#ifdef XRE_HAS_DLL_BLOCKLIST
XRE_SetupDllBlocklistType XRE_SetupDllBlocklist;
#endif
XRE_TelemetryAccumulateType XRE_TelemetryAccumulate;
XRE_mainType XRE_main;

static const nsDynamicFunctionLoad kXULFuncs[] = {
    { "XRE_CreateAppData", (NSFuncPtr*) &XRE_CreateAppData },
    { "XRE_FreeAppData", (NSFuncPtr*) &XRE_FreeAppData },
#ifdef XRE_HAS_DLL_BLOCKLIST
    { "XRE_SetupDllBlocklist", (NSFuncPtr*) &XRE_SetupDllBlocklist },
#endif
    { "XRE_TelemetryAccumulate", (NSFuncPtr*) &XRE_TelemetryAccumulate },
    { "XRE_main", (NSFuncPtr*) &XRE_main },
    { nullptr, nullptr }
};

#if defined( XP_WIN )
/**
 * Set the application user model id; see bug 95183
 * This is used to force the taskbar on Windows Vista/7/etc. to use the same
 * item for various versions of Komodo (as long as the major version matches).
 */
static void SetAppUserModel()
{
  typedef HRESULT (WINAPI * SetCurrentProcessExplicitAppUserModelIDPtr)(PCWSTR AppID);
  SetCurrentProcessExplicitAppUserModelIDPtr funcAppUserModelID = NULL;
  HMODULE hDLL = LoadLibraryW(L"shell32.dll");
  funcAppUserModelID = (SetCurrentProcessExplicitAppUserModelIDPtr)
                       GetProcAddress(hDLL, "SetCurrentProcessExplicitAppUserModelID");
  if (funcAppUserModelID) {
      #if PP_KO_IS_DEV_BUILD
        const wchar_t *appModelId = L"Komodo-PP_KO_PROD_TYPE-PP_KO_SHORT_VERSION";
      #else
        const wchar_t *appModelId = L"Komodo-PP_KO_PROD_TYPE-PP_KO_MAJOR";
      #endif /* PP_KO_IS_DEV_BUILD */
      wchar_t buf[MAXPATHLEN];
      DWORD result = GetEnvironmentVariableW(L"KOMODO_USERDATADIR",
                                             buf, sizeof(buf)/sizeof(buf[0]));
      if (result) {
        // We have a custom user data dir; use that as part of the id.
        // Win32 doesn't have any good APIs to get a case-normalized path (which
        // we need to work across processes); so just open the directory and
        // use its file index (equivalent to an inode number) instead.
        HANDLE hDir = CreateFileW(buf, FILE_READ_ATTRIBUTES,
                                  FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                  NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
        if (hDir != INVALID_HANDLE_VALUE) {
          BY_HANDLE_FILE_INFORMATION info;
          if (GetFileInformationByHandle(hDir, &info)) {
            _snwprintf_s(buf, sizeof(buf)/sizeof(buf[0]), _TRUNCATE,
                         L"%s-%08x.%08x.%08x", appModelId, info.dwVolumeSerialNumber,
                         info.nFileIndexHigh, info.nFileIndexLow);
            appModelId = buf;
          }
          CloseHandle(hDir);
        }
      }
      funcAppUserModelID(appModelId);
  }
  FreeLibrary(hDLL);
}
#endif

static int do_main(const char *exePath, int argc, char* argv[])
{
  nsCOMPtr<nsIFile> appini;
#ifdef XP_WIN
  // exePath comes from mozilla::BinaryPath::Get, which returns a UTF-8
  // encoded path, so it is safe to convert it
  nsresult rv = NS_NewLocalFile(NS_ConvertUTF8toUTF16(exePath), PR_FALSE,
                                getter_AddRefs(appini));
#else
  nsresult rv = NS_NewNativeLocalFile(nsDependentCString(exePath), PR_FALSE,
                                      getter_AddRefs(appini));
#endif
  if (NS_FAILED(rv)) {
    Output("Couldn't get nsILocalFile for '%s'", exePath);
    return 255;
  }

  appini->SetNativeLeafName(NS_LITERAL_CSTRING("application.ini"));
  nsXREAppData *appData;
  rv = XRE_CreateAppData(appini, &appData);
  if (NS_FAILED(rv)) {
    Output("Couldn't read application.ini");
    return 255;
  }

#ifdef KOSTART_PLACEHOLDER
    // The special Komodo startup gymnastics are only done when the
    // properly configured koStart.h|c are built in as part of the
    // *Komodo* build. After the default Mozilla build (in
    // Mozilla-devel/...) we simply start the XRE.
    return XRE_main(argc, argv, appData, 0);
#else
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
        #if defined( XP_WIN )
        SetAppUserModel();
        #endif /* defined( XP_WIN ) */
        retval = XRE_main(xreArgc, xreArgv, appData, 0);
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

int main(int argc, char* argv[])
{
  char exePath[MAXPATHLEN];

  nsresult rv = mozilla::BinaryPath::Get(argv[0], exePath);
  if (NS_FAILED(rv)) {
    Output("Couldn't calculate the application directory.\n");
    return 255;
  }

  char *lastSlash = strrchr(exePath, XPCOM_FILE_PATH_SEPARATOR[0]);
  if (!lastSlash || (lastSlash - exePath > MAXPATHLEN - sizeof(XPCOM_DLL) - 1))
    return 255;

  strcpy(++lastSlash, XPCOM_DLL);

  int gotCounters;
#if defined(XP_UNIX)
  struct rusage initialRUsage;
  gotCounters = !getrusage(RUSAGE_SELF, &initialRUsage);
#elif defined(XP_WIN)
  // GetProcessIoCounters().ReadOperationCount seems to have little to
  // do with actual read operations. It reports 0 or 1 at this stage
  // in the program. Luckily 1 coincides with when prefetch is
  // enabled. If Windows prefetch didn't happen we can do our own
  // faster dll preloading.
  IO_COUNTERS ioCounters;
  gotCounters = GetProcessIoCounters(GetCurrentProcess(), &ioCounters);
  if (gotCounters && !ioCounters.ReadOperationCount)
#endif
  {
      XPCOMGlueEnablePreload();
  }


  rv = XPCOMGlueStartup(exePath);
  if (NS_FAILED(rv)) {
    Output("Couldn't load XPCOM.\n");
    return 255;
  }

  rv = XPCOMGlueLoadXULFunctions(kXULFuncs);
  if (NS_FAILED(rv)) {
    Output("Couldn't load XRE functions.\n");
    return 255;
  }

#ifdef XRE_HAS_DLL_BLOCKLIST
  XRE_SetupDllBlocklist();
#endif

  if (gotCounters) {
#if defined(XP_WIN)
    XRE_TelemetryAccumulate(mozilla::Telemetry::EARLY_GLUESTARTUP_READ_OPS,
                            int(ioCounters.ReadOperationCount));
    XRE_TelemetryAccumulate(mozilla::Telemetry::EARLY_GLUESTARTUP_READ_TRANSFER,
                            int(ioCounters.ReadTransferCount / 1024));
    IO_COUNTERS newIoCounters;
    if (GetProcessIoCounters(GetCurrentProcess(), &newIoCounters)) {
      XRE_TelemetryAccumulate(mozilla::Telemetry::GLUESTARTUP_READ_OPS,
                              int(newIoCounters.ReadOperationCount - ioCounters.ReadOperationCount));
      XRE_TelemetryAccumulate(mozilla::Telemetry::GLUESTARTUP_READ_TRANSFER,
                              int((newIoCounters.ReadTransferCount - ioCounters.ReadTransferCount) / 1024));
    }
#elif defined(XP_UNIX)
    XRE_TelemetryAccumulate(mozilla::Telemetry::EARLY_GLUESTARTUP_HARD_FAULTS,
                            int(initialRUsage.ru_majflt));
    struct rusage newRUsage;
    if (!getrusage(RUSAGE_SELF, &newRUsage)) {
      XRE_TelemetryAccumulate(mozilla::Telemetry::GLUESTARTUP_HARD_FAULTS,
                              int(newRUsage.ru_majflt - initialRUsage.ru_majflt));
    }
#endif
  }

  int result;
  {
    ScopedLogging log;
    result = do_main(exePath, argc, argv);
  }

  XPCOMGlueShutdown();
  return result;
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
