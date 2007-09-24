/* Copyright (c) 2000-2006 ActiveState Software Inc.
 * See the file LICENSE.txt for licensing information.
 *
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
    int nFiles;
    char** files;       // generally these are pointers into argv
    char* line;         // --line string argument
    char* selection;    // --selection string argument
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

