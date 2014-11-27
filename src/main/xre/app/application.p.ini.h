#include "nsXREAppData.h"
             static const nsXREAppData sAppData = {
                 sizeof(nsXREAppData),  // size
                 NULL,                  // app directory
                 "ActiveState",         // vendor
                 "PP_KO_PROD_NAME",     // app name
// #if MOZILLA_VERSION_MAJOR > 31
                 NULL,                  // remote app name (NULL means same as app name)
// #endif
                 "PP_KO_VERSION",       // app version
                 "PP_KO_BUILD_NUMBER",  // buildID
                 "{b1042fb5-9e9c-11db-b107-000d935d3368}", // app guid
                 "Copyright (c) 1999 - PP_CURR_YEAR ActiveState", // copyright
                 14,                    // flags (PROFILE_MIGRATOR | EXTENSION_MANAGER | CRASH_REPORTER)
                 NULL,                  // xreDirectory
                 "PP_MOZ_GRE_MILESTONE", // XRE minVersion
                 "PP_MOZ_GRE_MILESTONE", // XRE maxVersion
                 "https://komodo.activestate.com/crash/submit", // crash report
                 NULL                   // profile directory
// #if MOZILLA_VERSION_MAJOR > 31
                 ,
                 NULL                   // user agent string
// #endif
             };
