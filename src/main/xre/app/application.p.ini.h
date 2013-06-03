#include "nsXREAppData.h"
             static const nsXREAppData sAppData = {
                 sizeof(nsXREAppData),  // size
                 NULL,                  // app directory
                 "ActiveState",         // vendor
                 "PP_KO_PROD_NAME",     // app name
                 "PP_KO_VERSION",       // app version
                 "PP_KO_BUILD_NUMBER",  // buildID
                 "{b1042fb5-9e9c-11db-b107-000d935d3368}", // app guid
                 "Copyright (c) 1999 - PP_CURR_YEAR ActiveState", // copyright
                 0,                     // flags
                 NULL,                  // xreDirectory
                 "24.0a1",              // XRE minVersion
                 "24.0a1",              // XRE maxVersion
                 "https://komodo.activestate.com/crash/submit", // crash report
                 NULL                   // profile directory
             };
