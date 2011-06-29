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

/* * *
 * Komodo startup helper routines.
 *
 */

#ifndef __KO_START_H__
#define __KO_START_H__
#ifdef __cplusplus
extern "C" {
#endif

#ifdef WIN32
    #include <windows.h>
#endif

/* Komodo command-line options struct. */
typedef struct {
    int newWindow;
    int nFiles;
    char** files;       // generally these are pointers into argv
    char* line;         // --line string argument
    char* selection;    // --selection string argument
    int usePosition;
} KoStartOptions;


/* KoStart status return codes for KoStart_* functions that return an int. */
#define KS_ERROR 0
#define KS_EXIT 1
#define KS_CONTINUE 2


/* A "handle" typedef for KoStart_* routines. */
#ifdef WIN32
typedef HANDLE KoStartHandle;   // Win32 synchronization handle
#define KS_BAD_HANDLE NULL
#else
typedef int KoStartHandle;      // Posix file descriptor
#define KS_BAD_HANDLE -1
#endif


extern int KoStart_HandleArgV(int argc, char** argv,
                              KoStartOptions* pOptions);

extern KoStartHandle KoStart_AcquireMutex(void);
extern void KoStart_ReleaseMutex(KoStartHandle mutex);

extern KoStartHandle KoStart_WantToBeTheMan(void);
extern void KoStart_ReleaseTheMan(KoStartHandle theMan);

// Initialize the commandments data pipe.
// This should only be called by the Komodo process that is "the man".
extern void KoStart_InitCommandments();

// Issue commandments to the running (or soon to be so) Komodo.
//  "pOptions" is a pointer to startup options as filled out by
//      KoStart_HandleArgv().
//  "isTheMan" is a boolean indicating if this is Komodo instance is
//      "the man", i.e. the one starting the XRE.
extern void KoStart_IssueCommandments(const KoStartOptions* pOptions,
                                      int first);

extern void KoStart_PrepareForXRE(int argc, char** argv,
                                  int* pXreArgc, char*** pXreArgv);


#ifdef __cplusplus
}
#endif
#endif /* !__KO_START_H__ */

