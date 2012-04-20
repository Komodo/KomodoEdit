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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

/* Komodo console launch executable. 
 *
 * This is small stub executable to spawn the main Komodo binary in its
 * real location. Feature include:
 * 
 * - Handle some of the simple command line options without handing off.
 *   This is done because on Windows the main Komodo binary:
 *      <installdir>\lib\mozilla\komodo.exe
 *   is subsystem:windows but this stub provides both:
 *      komodo.exe  (subsystem:windows)
 *      ko.exe      (subsystem:console, mainly for command-line usage)
 *   and it is often useful to have console output for some command-line
 *   invocations, e.g.: "ko --version", "ko --help".
 *   
 * - Spawn the executable and exit. Without this the *first* start of
 *   Komodo from the terminal would just run in the foreground: not what
 *   is wanted on Windows
 *   
 * - XXX Should do the shell redirection... currently get console output
 *   on Linux. Actually, if we control logging properly then we should
 *   be able to get this to be quiet on stdout/stderr.
 * - XXX Eventually it would be nice to get smarter: (1) to run
 *   synchronously for "komodo -h" and similar; (2) to allow blocking
 *   until editing the file in question is done so that, e.g., Komodo
 *   could be used for P4EDITOR/SVN_EDITOR/EDITOR.
 *   XXX Could fake (1) with a short delay before exit. And could also
 *   do simple checking of argv to see if it is one of these cases, then
 *   actually *do* run synchronously for these: could do this to get the
 *   correct exit value working.
 *
 * Windows:
 *      <installdir>/
 *          komodo.exe      # stub
 *          lib/mozilla/
 *              komodo.exe  # main Komodo binary
 *
 * Linux/Solaris:
 *      <installdir>/
 *          bin/
 *              komodo      # stub
 *          lib/mozilla/
 *              komodo      # main Komodo binary
 *
 * This stub is not used on Mac OS X. (XXX We *should* perhaps have a
 * stub on OS X to put in /usr/local/bin -- or similar -- for launching
 * from the command line. Competitor: BBEdit's "edit" command.)
 */

#if defined(WIN32)
#define PLAT_WIN32 1
#elif defined(__APPLE__)
#define PLAT_MACOSX 1
#endif

#include "koStart.h"

#ifdef PLAT_WIN32
    #include <windows.h>
    #include <process.h>
    #include <direct.h>
    #include <shlwapi.h>
    #include "nsWindowsWMain.cpp"
#else /* unix */
    #include <pwd.h>
    #include <unistd.h>
    #include <sys/file.h>
    #include <sys/types.h>
    #include <fcntl.h>
#endif /* PLAT_WIN32 */
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>


//---- constants

#ifndef TRUE
#define TRUE (1)
#endif
#ifndef FALSE
#define FALSE (0)
#endif

#define BUF_LENGTH 4096
#define MAX_KO_ARGS 50
#define MAX_FILES 50
#define MAXPATHLEN 1024
#ifdef PLAT_WIN32
    #define SEP '\\'
    #define ALTSEP '/'
    // path list element separator
    #define DELIM ';'
    #define EXEEXT ".exe"
    #define KOMODO_BIN "komodo"
#else /* linux */
    #define SEP '/'
    // path list element separator
    #define DELIM ':'
    #define EXEEXT ""
    #ifdef PLAT_MACOSX
        #define KOMODO_BIN "komodo-bin"
    #else
        #define KOMODO_BIN "komodo"
    #endif
#endif

#ifdef PLAT_WIN32
    #define snprintf _snprintf
    #define vsnprintf _vsnprintf
    //NOTE: this is for the stat *call* and the stat *struct*
    #define stat _stat
#endif



//---- globals

#ifndef DEBUG
int DEBUG = 0;
#endif /* DEBUG */

char* _gProgramName = NULL;
char* _gProgramPath = NULL;


//---- logging functions
#if !defined(NO_STDARG)
#   include <stdarg.h>
#   define KO_VARARGS(type, name) (type name, ...)
#   define KO_VARARGS_DEF(type, name) (type name, ...)
#   define KO_VARARGS_START(type, name, list) (va_start(list, name), name)
#else
#   include <varargs.h>
#   define KO_VARARGS(type, name) ()
#   define KO_VARARGS_DEF(type, name) (va_alist)
#   define KO_VARARGS_START(type, name, list) (va_start(list), va_arg(list, type))
#endif

void _LogError KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(PLAT_WIN32) && defined(_WINDOWS)
    // put up a MessageBox
    char caption[BUF_LENGTH+1];
    char msg[BUF_LENGTH+1];

    KO_VARARGS_START(const char *, format, ap);
    snprintf(caption, BUF_LENGTH, "Error in %s", _gProgramName);
    vsnprintf(msg, BUF_LENGTH, format, ap);
    MessageBox(NULL, msg, caption, MB_OK | MB_ICONEXCLAMATION);
#else
    KO_VARARGS_START(const char *, format, ap);
    fprintf(stderr, "%s: error: ", _gProgramName);
    vfprintf(stderr, format, ap);
#endif /* PLAT_WIN32 && _WINDOWS */
    va_end(ap);
}


void _LogWarning KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(PLAT_WIN32) && defined(_WINDOWS)
    // put up a MessageBox
    char caption[BUF_LENGTH+1];
    char msg[BUF_LENGTH+1];

    KO_VARARGS_START(const char *, format, ap);
    snprintf(caption, BUF_LENGTH, "Warning in %s", _gProgramName);
    vsnprintf(msg, BUF_LENGTH, format, ap);
    MessageBox(NULL, msg, caption, MB_OK | MB_ICONWARNING);
#else
    KO_VARARGS_START(const char *, format, ap);
    fprintf(stderr, "%s: warning: ", _gProgramName);
    vfprintf(stderr, format, ap);
#endif /* PLAT_WIN32 && _WINDOWS */
    va_end(ap);
}


void _LogInfo KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(PLAT_WIN32) && defined(_WINDOWS)
    // put up a MessageBox
    char caption[BUF_LENGTH+1];
    char msg[BUF_LENGTH+1];

    KO_VARARGS_START(const char *, format, ap);
    snprintf(caption, BUF_LENGTH, "%s", _gProgramName);
    vsnprintf(msg, BUF_LENGTH, format, ap);
    MessageBox(NULL, msg, caption, MB_OK | MB_ICONWARNING);
#else
    KO_VARARGS_START(const char *, format, ap);
    fprintf(stderr, "%s: ", _gProgramName);
    vfprintf(stderr, format, ap);
#endif /* PLAT_WIN32 && _WINDOWS */
    va_end(ap);
}



//---- utilities functions

#ifdef PLAT_WIN32
/**
 * Helper function to convert a UTF-8 string to UTF-16
 * @param str The UTF-8 string
 * @returns The equivalent UTF-16 string; it should be free()ed.
 */
static wchar_t* _ToUTF16(const char* str)
{
    wchar_t *buffer;
    int size;
    size = MultiByteToWideChar(CP_UTF8, 0, str, -1, NULL, 0);
    buffer = reinterpret_cast<wchar_t*>(malloc(size * sizeof(wchar_t)));
    (void)MultiByteToWideChar(CP_UTF8, 0, str, -1, buffer, size);
    return buffer;
}
#endif /* PLAT_WIN32 */


/* _IsLink: Is the given filename a symbolic link */
static int _IsLink(char *filename)
{
#ifdef PLAT_WIN32
    return 0;
#else /* i.e. linux */
    struct stat buf;

    if (lstat(filename, &buf) != 0)
        return 0;
    if (!S_ISLNK(buf.st_mode))
        return 0;
    return 1;
#endif
}


/* Does the given file exist. */
static int _IsFile(const char *filename)
{
#ifdef PLAT_WIN32
    int result;
    wchar_t *filenamew = _ToUTF16(filename);
    result = PathFileExistsW(filenamew);
    free(filenamew);
    return result;
#else /* i.e. linux */
    struct stat buf;

    if (stat(filename, &buf) != 0)
        return 0;
    if (!S_ISREG(buf.st_mode))
        return 0;
    return 1;
#endif /* PLAT_WIN32 */
}


/* Is executable file
 * On Linux: check 'x' permission. On Windows: just check existence.
 */
static int _IsExecutableFile(const char *filename)
{
#ifdef PLAT_WIN32
    return _IsFile(filename);
#else /* i.e. linux */
    struct stat buf;

    if (stat(filename, &buf) != 0)
        return 0;
    if (!S_ISREG(buf.st_mode))
        return 0;
    if ((buf.st_mode & 0111) == 0)
        return 0;
    return 1;
#endif /* PLAT_WIN32 */
}


/* _GetProgramPath: Determine the absolute path to the currently executing process
 *
 *    Takes into account the current working directory, etc.
 *    The implementations require the global '_gProgramName' to be set.
 */
#ifdef PLAT_WIN32
static char* _GetProgramPath(void)
{
    //XXX this is ugly but I didn't want to use malloc, no reason
    static wchar_t progPathW[MAXPATHLEN+1];
    static char progPath[MAXPATHLEN+1];
    wchar_t *p;

    // get absolute path to module
    if (!GetModuleFileNameW(NULL, progPathW, MAXPATHLEN)) {
        _LogError("could not get absolute program name from "\
                  "GetModuleFileName\n");
        exit(1);
    }
    // just need dirname
    for (p = progPathW+wcslen(progPathW);
         *p != SEP && *p != ALTSEP;
         --p)
        {
            /* nothing */
        }
    *p = L'\0';  // remove the trailing SEP as well
    WideCharToMultiByte(CP_UTF8, 0, progPathW, -1, progPath,
                        sizeof(progPath) / sizeof(progPath[0]), NULL, NULL);

    return progPath;
}
#else


/* _JoinPath requires that any buffer argument passed to it has at
   least MAXPATHLEN + 1 bytes allocated.  If this requirement is met,
   it guarantees that it will never overflow the buffer.  If stuff
   is too long, buffer will contain a truncated copy of stuff.
*/
static void
_JoinPath(char *buffer, char *stuff)
{
    size_t n, k;

    if (stuff[0] == SEP)
        n = 0;
    else {
        n = strlen(buffer);
        if (n > 0 && buffer[n-1] != SEP && n < MAXPATHLEN)
            buffer[n++] = SEP;
    }
    k = strlen(stuff);
    if (n + k > MAXPATHLEN)
        k = MAXPATHLEN - n;
    strncpy(buffer+n, stuff, k);
    buffer[n+k] = '\0';
}


/* _ExpandUser requires that any buffer argument passed to it has at
   least MAXPATHLEN + 1 bytes allocated.  If this requirement is met,
   it guarantees that it will never overflow the buffer.  If stuff
   is too long, buffer will contain a truncated copy of stuff.
*/
static void
_ExpandUser(char *path)
{
    size_t i, n;
    struct passwd *pw;
    char expanded[MAXPATHLEN+1];
    char scratch[MAXPATHLEN+1];

    if (path[0] != '~')
        return;
    for (i = 1, n = strlen(path); i < n && path[i] != SEP; ++i)
        ; /* do nothing */

    if (i == 1) {
        char *home = getenv("HOME");
        if (!home) {
            uid_t uid = getuid();
            pw = getpwuid(uid);
            if (!pw) {
                _LogWarning("could not get home dir for uid %d\n", uid);
                return;
            } else {
                strncpy(expanded, pw->pw_dir, MAXPATHLEN);
            }
        } else {
            strncpy(expanded, home, MAXPATHLEN);
        }
    } else {
        char username[MAXPATHLEN+1];
        strncpy(username, path+1, i-1);
        pw = getpwnam(username);
        if (!pw) {
            _LogWarning("could not get home dir for name '%s'\n", username);
            return;
        } else {
            strncpy(expanded, pw->pw_dir, MAXPATHLEN);
        }
    }

    if (expanded[strlen(expanded)-1] == SEP)
        i++;  /* avoid double SEP in result */
    strncpy(expanded+strlen(expanded), path+i, MAXPATHLEN-strlen(expanded));

    strncpy(path, expanded, MAXPATHLEN);
}


static char*
_GetProgramPath(void)
{
    /* XXX this routine does *no* error checking */
    static char progPath[MAXPATHLEN+1];
    char* path = getenv("PATH");
    char* pLetter;

    /* If there is no slash in the argv0 path, then we have to
     * assume the program is on the user's $PATH, since there's no
     * other way to find a directory to start the search from.  If
     * $PATH isn't exported, you lose.
     */
    if (strchr(_gProgramName, SEP)) {
        strncpy(progPath, _gProgramName, MAXPATHLEN);
    }
    else if (path) {
        int bufspace = MAXPATHLEN;
        while (1) {
            char *delim = strchr(path, DELIM);

            if (delim) {
                size_t len = delim - path;
                if (len > bufspace) {
                    len = bufspace;
                }
                strncpy(progPath, path, len);
                *(progPath + len) = '\0';
                bufspace -= len;
            }
            else {
                strncpy(progPath, path, bufspace);
            }

            _JoinPath(progPath, _gProgramName);
            _ExpandUser(progPath);
            if (_IsExecutableFile(progPath)) {
                break;
            }

            if (!delim) {
                progPath[0] = '\0';
                break;
            }
            path = delim + 1;
        }
    }
    else {
        progPath[0] = '\0';
    }

    // now we have to resolve a string of possible symlinks
    //   - we'll just handle the simple case of a single level of
    //     indirection
    //
    // XXX note this does not handle multiple levels of symlinks
    //     here is pseudo-code for that (please implement it :):
    // while 1:
    //     if islink(progPath):
    //         linkText = readlink(progPath)
    //         if isabsolute(linkText):
    //             progPath = os.path.join(dirname(progPath), linkText)
    //         else:
    //             progPath = linkText
    //     else:
    //         break
    if (_IsLink(progPath)) {
        char newProgPath[MAXPATHLEN+1];
        readlink(progPath, newProgPath, MAXPATHLEN);
        strncpy(progPath, newProgPath, MAXPATHLEN);
    }

    // prefix with the current working directory if the path is
    // relative to conform with the Windows version of this
    if (strlen(progPath) != 0 && progPath[0] != SEP) {
        char cwd[MAXPATHLEN+1];
        char tmp[MAXPATHLEN+1];
        //XXX should check for failure retvals
        getcwd(cwd, MAXPATHLEN);
        snprintf(tmp, MAXPATHLEN, "%s%c%s", cwd, SEP, progPath);
        strncpy(progPath, tmp, MAXPATHLEN);
    }

    // 'progPath' now contains the full path to the program *and* the program
    // name. The latter is not desire.
    pLetter = progPath + strlen(progPath);
    for (;pLetter != progPath && *pLetter != SEP; --pLetter) {
        /* do nothing */
    }
    *pLetter = '\0';

    return progPath;
}
#endif  /* PLAT_WIN32 */


/* _IsDevTree - is this running in a dev-tree layout, as opposed to an
 *              install tree layout?
 *
 * The Python equivalent being used in koDirs.py:
 *
 *  __isDevTreeCache = None
 *  def _isDevTree(self):
 *      """Return true if this Komodo is running in a dev tree layout."""
 *      if self.__isDevTreeCache is None:
 *          landmark = os.path.join(self.get_mozBinDir(), "is_dev_tree.txt")
 *          self.__isDevTreeCache = os.path.isfile(landmark)
 *      return self.__isDevTreeCache
 */
int _IsDevTree(void)
{
    static int isDevTreeCache = -1; // -1: not set, 0: false, 1: true
    if (isDevTreeCache == -1) {
        size_t overflow;
        char landmark[MAXPATHLEN+1];
        // this stub: <mozdist>/komodo-bits/stub/komodo[.exe]
        // landmark:  <mozdist>/bin/is-dev-tree.txt
        overflow = snprintf(landmark, MAXPATHLEN,
                            "%s%c..%c..%cbin%cis_dev_tree.txt",
                            _gProgramPath, SEP, SEP, SEP, SEP);
        if (overflow > MAXPATHLEN || overflow < 0) {
            _LogError("_IsDevTree: buffer overflow calculating landmark path\n");
            exit(1);
        }
        isDevTreeCache = _IsFile(landmark) ? 1 : 0;
    }
    return isDevTreeCache;
}



/* _SetupAndLaunchKomodo - launch komodo chrome in mozilla in a subprocess
 */
int _SetupAndLaunchKomodo(int argc, char** argv)
{
    int i;
    char* koArgs[MAX_KO_ARGS+1];
    int nKoArgs = 0;
    char komodoExe[MAXPATHLEN+1];
#ifdef PLAT_WIN32
    STARTUPINFOW startupInfo;
    PROCESS_INFORMATION processInfo;
    char cmdln[BUF_LENGTH+1];
    wchar_t *cmdlnw;
    char **pArg;
    int pid;
#else
    pid_t pid;
    int rv;
#endif

    // Determine the full path to the main Komodo binary. Cannot just
    // use the basename because it is called "komodo[.exe]" just like
    // this shim.
    if (_IsDevTree()) {
        //  <mozdist>/
        //      bin/
        //          komodo[.exe]        # main Komodo binary
        //      komodo-bits/
        //          stub/
        //              komodo[.exe]    # command-line stub
        snprintf(komodoExe, MAXPATHLEN, "%s%c..%c..%cbin%c%s%s",
                 _gProgramPath, SEP, SEP, SEP, SEP, KOMODO_BIN, EXEEXT);
        //XXX should check for failure
    }
    else {
#if defined(PLAT_WIN32)
        //  <installdir>/
        //      komodo.exe              # command-line stub
        //      lib/
        //          mozilla/
        //              komodo.exe      # main Komodo binary
        snprintf(komodoExe, MAXPATHLEN, "%s%clib%cmozilla%c%s%s",
                 _gProgramPath, SEP, SEP, SEP, KOMODO_BIN, EXEEXT);
#elif defined(PLAT_MACOSX)
#       error "don't know how to get stub-to-main-binary path on Mac OS X"
#else
        //  <installdir>/
        //      bin/
        //          komodo              # command-line stub
        //      lib/
        //          mozilla/
        //              komodo          # main Komodo binary
        snprintf(komodoExe, MAXPATHLEN, "%s%c..%clib%cmozilla%c%s%s",
                 _gProgramPath, SEP, SEP, SEP, SEP, KOMODO_BIN, EXEEXT);
#endif
        //XXX should check for failure
    }

    // XXX Is this correct?
    koArgs[nKoArgs++] = komodoExe;
    for (i = 1; i < argc; ++i) {
        koArgs[nKoArgs++] = argv[i];
    }
    koArgs[nKoArgs++] = NULL;

#ifdef PLAT_WIN32
    memset(&startupInfo, 0, sizeof(startupInfo));
    startupInfo.cb = sizeof(startupInfo);

    //---- determine mozilla command line
    cmdln[0] = '\0';
    for (pArg = koArgs; *pArg; pArg++) {
        if (strchr(*pArg, ' ')) {
            strncat(cmdln, "\"", BUF_LENGTH-strlen(cmdln));
            strncat(cmdln, *pArg, BUF_LENGTH-strlen(cmdln));
            strncat(cmdln, "\"", BUF_LENGTH-strlen(cmdln));
        } else {
            strncat(cmdln, *pArg, BUF_LENGTH-strlen(cmdln));
        }
        strncat(cmdln, " ", BUF_LENGTH-strlen(cmdln));
    }
    if (DEBUG) {
        printf("%s: running '%s'...\n", _gProgramName, cmdln);
    }
    cmdlnw = _ToUTF16(cmdln);

    if (!CreateProcessW(NULL,            /* path name of executable */
                        cmdlnw,          /* executable, and its arguments */
                        NULL,            /* default process attributes */
                        NULL,            /* default thread attributes */
                        TRUE,            /* inherit handles */
                        0,               /* creation flags */
                        (LPVOID)NULL,    /* inherit environment */
                        NULL,            /* inherit cwd */
                        &startupInfo,
                        &processInfo))
    {
        errno = ENOENT;
        return -1;
    } else {
        /* Fix http://bugs.activestate.com/show_bug.cgi?id=53927
         * on some dual-core Windows machines Komodo hangs while or
         * after debugging a Perl program in the IDE, as opposed to
         * running in a console.
         *
         * 0x01 : dwThreadAffinityMask : run the moz process in CPU #1
         */
        SetThreadAffinityMask(processInfo.hThread, 0x01);
    }
    
    free(cmdlnw);
    pid = (int)processInfo.dwProcessId;
    CloseHandle(processInfo.hThread);
    return 0;

#elif defined(PLAT_MACOSX)
#   error "don't know how to start main binary on Mac OS X"

#else  /* linux/solaris */
    pid = fork();
    if (pid == -1) {
        _LogError("error forking for main komodo binary: %s\n",
                  strerror(errno));
        exit(1);
    } else if (pid == 0) { // child
        int rv = execvp(koArgs[0], koArgs);
        // should not get here
        if (rv == -1) {
            _LogError("error execing main komodo binary: %s\n",
                      strerror(errno));
        }
    } else { // parent
        // nothing
    }
    return pid;
#endif /* PLAT_WIN32 */
}


//---- mainline

int main(int argc, char** argv)
{
    int retval = 0;
    int rv;
    KoStartOptions options;
    
    _gProgramName = argv[0];
    _gProgramPath = _GetProgramPath();

    // Handle command line arguments.
    rv = KoStart_HandleArgV(argc, argv, &options);
    switch (rv) {
    case KS_ERROR:
        retval = 1;
        break;
    case KS_EXIT:
        break;
    case KS_CONTINUE:
        _SetupAndLaunchKomodo(argc, argv);

        // HACK: Instead of properly waiting for completion of the main
        // Komodo binary for some conditions (e.g. "komodo -h") we just
        // pause for a sec to let the main Komodo binary do some of the
        // short things -- e.g. print help, print version -- before
        // returning.
#ifdef PLAT_WIN32
        Sleep(300); // in milliseconds
#else
        sleep(1);   // in seconds
#endif
        break;
    }

    return retval;
}


//---- mainline for win32 subsystem:windows app
#ifdef PLAT_WIN32
int WINAPI wWinMain(
    HINSTANCE hInstance,      /* handle to current instance */
    HINSTANCE hPrevInstance,  /* handle to previous instance */
    LPWSTR lpCmdLine,         /* pointer to command line */
    int nCmdShow              /* show state of window */
    )
{
    return wmain(__argc, __wargv);
}
#endif

