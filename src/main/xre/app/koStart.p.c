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
 * Startup support for an XRE-based Komodo.
 *
 * In an XRE-based app there is typically an "app" build dir with an
 * "ns<name>App.cpp" file, e.g. "nsKomodoApp.cpp", with a main() that is
 * at minimum this:
 *      int main(int argc, char* argv[])
 *      {
 *          XRE_main(argc, argv, &kAppInfo);
 *      }
 *
 * This module provides facilities to:
 * - ensure there is one Komodo instance per user
 * - pass "commandments" to a running Komodo instance
 * - setup the environment as require for the Komodo runtime
 *
 * Using these facilities not *really* straighforward, but it isn't that
 * bad. The current nsKomodoApp.cpp is the best "documentation" for how
 * to use this module.
 *
 *
 * Notes on Logging:
 *
 * This module logs Komodo startup processing via four _LogXXX methods.
 * *Where* these log message go depends on the platform and (on Windows)
 * whether there is a console to which to write. _LogDebug messages are
 * only written if in verbose mode (via the '-v'/'--verbose' option):
 *
 *      LOG FUNCTION  NON-WINDOWS  WINDOWS (gui)    WINDOWS (console)
 *      ------------  -----------  -------------    -----------------
 *      _LogError     stderr       MessageBox       stderr
 *      _LogWarning   stderr       MessageBox       stderr
 *      _LogInfo      stdout       MessageBox       stdout
 *      _LogDebug     stderr       startup.log (*)  stderr
 *
 * (*) startup.log is in the Komodo host user data dir.
 * 
 *
 * Dev Notes:
 * - XXX Should we use the MsgWaitForMultipleObjects() from the old
 *   _FriendlyWaitForObject() whereever we have WaitForSingleObject()?
 */


/* ---- Configuration defines ---- 
 * Komodo preprocessor modifies this section at build-time.
 */
// #ifndef PP_KO_SHORT_VERSION
// #error "this file cannot be preprocessed by 'bk build quick'"
// #endif
#define KO_SHORT_VERSION "PP_KO_SHORT_VERSION"
#define KO_MARKETING_SHORT_VERSION "PP_KO_MARKETING_SHORT_VERSION"
#define KO_FULL_PRETTY_VERSION "PP_KO_FULL_PRETTY_VERSION"
#define KO_BUILD_PLATFORM "PP_KO_BUILD_PLATFORM"
#define KO_PROD_TYPE "PP_KO_PROD_TYPE"
#define KO_APPDATADIR_NAME "PP_KO_APPDATADIR_NAME"
#define KO_VERSION "PP_KO_VERSION"
#define KO_BUILD_NUMBER "PP_KO_BUILD_NUMBER"
#define PYTHON_MAJOR_MINOR "PP_PYTHON_MAJOR_MINOR"



/* Platform defines
 *    Mac OS X:         MACOSX
 *    Windows:          WIN32
 *    Linux/Solaris:    <nothing defined: use #else>
 */
#if defined(__APPLE__)
#define MACOSX 1
#endif


/* ---- includes ---- */

#ifdef WIN32
    #include <winsock2.h>
    #include <windows.h>
    #include <ShlObj.h> // For CSIDL_LOCAL_APPDATA
    #include <KnownFolders.h> // For FOLDERID_LocalAppData
    #include <process.h>
    #include <direct.h>
    #include <shlwapi.h>
#else /* Unix-y */
    #ifdef MACOSX
        #include <Carbon/Carbon.h>
        #include <sys/acl.h>
    #endif
    #include <pwd.h>
    #include <unistd.h>
    #include <sys/file.h>
    #include <sys/types.h>
    #include <sys/utsname.h>
    #include <fcntl.h>
#endif /* WIN32 */
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include "koStart.h"

/* Benjamin Sittler's getopt() re-implementation */
#include "getopt.h"


/* ---- constants ---- */

#ifndef TRUE
#define TRUE (1)
#endif
#ifndef FALSE
#define FALSE (0)
#endif

#define BUF_LENGTH 4096
#define MAX_XRE_ARGS 20
#define MAXPATHLEN 1024
/* Max commandment length:
 *     overhead(5):          open\t
 *     selection option(25): --selection ...\t
 *     filepath(MAXPATHLEN): <filepath>
 */
#define MAX_COMMANDMENT_LEN  (5+25+MAXPATHLEN)

#ifdef WIN32
    #define SEP '\\'
    #define ALTSEP '/'
    /* path list element separator */
    #define DELIM ';'
#else /* Unix-y */
    #define SEP '/'
    /* path list element separator */
    #define DELIM ':'
#endif

#ifdef WIN32
    #define snprintf _snprintf
    #define vsnprintf _vsnprintf
    /* NOTE: this is for the stat *call* and the stat *struct* */
    #define stat _stat
    #define ssize_t SSIZE_T
#endif



/* ---- globals ---- */

#ifdef WIN32

#if defined(_MSC_VER) || defined(__MINGW32__) || defined(__BORLANDC__)
#    define environ _environ
#endif

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
    buffer = (wchar_t*)malloc(size * sizeof(wchar_t));
    (void)MultiByteToWideChar(CP_UTF8, 0, str, -1, buffer, size);
    return buffer;
}

/**
 * Helper function to convert a UTF-16 string to UTF-8
 * @param str The UTF-16 string
 * @returns The equivalent UTF-8 string; it should be free()ed.
 */
static char* _ToUTF8(const wchar_t* str)
{
    char *buffer;
    int size;
    size = WideCharToMultiByte(CP_UTF8, 0, str, -1, NULL, 0, NULL, NULL);
    buffer = (char*)malloc(size * sizeof(char));
    (void)WideCharToMultiByte(CP_UTF8, 0, str, -1, buffer, size, NULL, NULL);
    return buffer;
}

#else /* !WIN32 */

/* Bug: http://bugs.activestate.com/show_bug.cgi?id=39273 
 * gcc >= 4.0 will hide environ when the default policy is
 * to hide all symbols. It's probably a gcc bug, but this
 * workaround seems to do the trick
 */

#ifdef HAVE_VISIBILITY_HIDDEN_ATTRIBUTE
#   define KO_VISIBLE __attribute__ ((visibility ("default")))
#else
#   define KO_VISIBLE
#endif

     KO_VISIBLE extern char **environ;   /* the user environment */
#endif

static int _KoStart_verbose = 0;
static char* _KoStart_logPrefix = "komodo";



/* ---- logging functions ---- */

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

static void _LogError KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(WIN32) && defined(_WINDOWS)
    char consoleTitle[1000];
    KO_VARARGS_START(const char *, format, ap);
    if (GetConsoleTitle(consoleTitle, 1000) == 0
        && GetLastError() != ERROR_SUCCESS)
    {
        char caption[BUF_LENGTH+1];
        char msg[BUF_LENGTH+1];

        snprintf(caption, BUF_LENGTH, "Error in %s", _KoStart_logPrefix);
        vsnprintf(msg, BUF_LENGTH, format, ap);
        MessageBox(NULL, msg, caption, MB_OK | MB_ICONEXCLAMATION);
    }
    else {
        fprintf(stderr, "%s: error: ", _KoStart_logPrefix);
        vfprintf(stderr, format, ap);
    }
#else
    KO_VARARGS_START(const char *, format, ap);
    fprintf(stderr, "%s: error: ", _KoStart_logPrefix);
    vfprintf(stderr, format, ap);
#endif /* WIN32 && _WINDOWS */
    va_end(ap);
}


static void _LogWarning KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(WIN32) && defined(_WINDOWS)
    char consoleTitle[1000];
    KO_VARARGS_START(const char *, format, ap);
    if (GetConsoleTitle(consoleTitle, 1000) == 0
        && GetLastError() != ERROR_SUCCESS)
    {
        char caption[BUF_LENGTH+1];
        char msg[BUF_LENGTH+1];

        snprintf(caption, BUF_LENGTH, "Warning in %s", _KoStart_logPrefix);
        vsnprintf(msg, BUF_LENGTH, format, ap);
        MessageBox(NULL, msg, caption, MB_OK | MB_ICONWARNING);
    }
    else {
        fprintf(stderr, "%s: warning: ", _KoStart_logPrefix);
        vfprintf(stderr, format, ap);
    }
#else
    KO_VARARGS_START(const char *, format, ap);
    fprintf(stderr, "%s: warning: ", _KoStart_logPrefix);
    vfprintf(stderr, format, ap);
#endif /* WIN32 && _WINDOWS */
    va_end(ap);
}


static void _LogInfo KO_VARARGS_DEF(const char *, format)
{
    va_list ap;
#if defined(WIN32) && defined(_WINDOWS)
    char consoleTitle[1000];
    KO_VARARGS_START(const char *, format, ap);
    if (GetConsoleTitle(consoleTitle, 1000) == 0
        && GetLastError() != ERROR_SUCCESS)
    {
        char caption[BUF_LENGTH+1];
        char msg[BUF_LENGTH+1];

        snprintf(caption, BUF_LENGTH, "%s", _KoStart_logPrefix);
        vsnprintf(msg, BUF_LENGTH, format, ap);
        MessageBox(NULL, msg, caption, MB_OK | MB_ICONINFORMATION);
    }
    else {
        vfprintf(stdout, format, ap);
    }
#else
    KO_VARARGS_START(const char *, format, ap);
    vfprintf(stdout, format, ap);
#endif /* WIN32 && _WINDOWS */
    va_end(ap);
}

static char* _KoStart_GetStartupLogFileName(); // fwd decl
static void _LogDebug KO_VARARGS_DEF(const char *, format)
{
    if (_KoStart_verbose)
    {
        va_list ap;
#if defined(WIN32) && defined(_WINDOWS)
        char consoleTitle[1000];
        wchar_t *startLogFileNameW;
        KO_VARARGS_START(const char *, format, ap);
        if (GetConsoleTitle(consoleTitle, 1000) == 0
            && GetLastError() != ERROR_SUCCESS)
        {
            FILE* startlog;
            static int isFirstTime = 1;
            wchar_t* mode = L"a";
            if (isFirstTime) {
                mode = L"w";
                isFirstTime = 0;
            }
            startLogFileNameW = _ToUTF16(_KoStart_GetStartupLogFileName());
            startlog = _wfopen(startLogFileNameW, mode);
            free(startLogFileNameW);
            fprintf(startlog, "%s: debug: ", _KoStart_logPrefix);
            vfprintf(startlog, format, ap);
            fclose(startlog);
        }
        else {
            fprintf(stderr, "%s: debug: ", _KoStart_logPrefix);
            vfprintf(stderr, format, ap);
        }
#else
        KO_VARARGS_START(const char *, format, ap);
        fprintf(stderr, "%s: debug: ", _KoStart_logPrefix);
        vfprintf(stderr, format, ap);
#endif /* WIN32 && _WINDOWS */
        va_end(ap);
    }
}



/* ---- generic utilities functions ---- */

#ifdef WIN32
static DWORD _FriendlyWaitForObject(HANDLE h)
{
    /* Run a "friendly" wait for the object.
     * Apart from simply waiting, if we have a process handle, also
     * wait on that (returning ERROR_PROCESS_ABORTED in that case)
     * If we need to process a Windows message, then transparently do that.
     */
    HANDLE handles[1] = {h};
    DWORD num_handles = 1;

    while (1) {
        DWORD rv = MsgWaitForMultipleObjects(
            num_handles,    /* number of handles in array */
            handles,        /* object-handle array */
            FALSE,          /* wait all option */
            INFINITE,       /* time-out interval */
            QS_ALLEVENTS);  /* input-event type */
        if (rv==WAIT_OBJECT_0)
            /* Requested object signalled - indicate success */
            return 0;
        if (num_handles==2 && rv==WAIT_OBJECT_0+1)
            /* Process termination */
            return ERROR_PROCESS_ABORTED;
        if (rv==WAIT_OBJECT_0+num_handles) {
            /* Process a Windows message. */
            MSG msg;
            while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
                TranslateMessage(&msg);
                DispatchMessage(&msg);
            }
            /* All messages done - re-enter the wait state. */
            continue;
        }
        /* trouble. */
        return GetLastError();
    }
    _LogError("unreachable code\n");
    return E_UNEXPECTED;
}

#endif


/* _IsDir: Is the given dirname an existing directory */
static int _IsDir(char *dirname)
{
#ifdef WIN32
    DWORD dwAttrib;
    wchar_t *dirnamew = _ToUTF16(dirname);
    dwAttrib = GetFileAttributesW(dirnamew);
    free(dirnamew);

    if (dwAttrib == -1) {
        return 0;
    }
    if (dwAttrib & FILE_ATTRIBUTE_DIRECTORY) {
        return 1;
    }
    return 0;
#else /* i.e. linux */
    struct stat buf;

    if (stat(dirname, &buf) != 0)
        return 0;
    if (!S_ISDIR(buf.st_mode))
        return 0;
    return 1;
#endif
}


/* _IsLink: Is the given filename a symbolic link */
static int _IsLink(char *filename)
{
#ifdef WIN32
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
static int _IsFile(char *filename)
{
#ifdef WIN32
    wchar_t *filenamew = _ToUTF16(filename);
    int result = PathFileExistsW(filenamew);
    free(filenamew);
    return result;
#else /* i.e. linux */
    struct stat buf;

    if (stat(filename, &buf) != 0)
        return 0;
    if (!S_ISREG(buf.st_mode))
        return 0;
    return 1;
#endif /* WIN32 */
}


/* Is executable file
 * On Linux: check 'x' permission. On Windows: just check existence.
 */
static int _IsExecutableFile(char *filename)
{
#ifdef WIN32
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
#endif /* WIN32 */
}



/* Split the given path into a dirname and basename (like Python's
 * os.path.split()).
 * @param path [in] The path to split
 * @param head [optional, out] The dirname
 * @param tail [optional, out] The basename
 */
static void _SplitPath(char *path, char *head, char* tail)
{
    char* sep = strrchr(path, SEP);
    char tmpHead[MAXPATHLEN+1], tmpTail[MAXPATHLEN+1];
    if (sep == NULL) {
        tmpHead[0] = '\0';
        strncpy(tmpTail, path, strlen(path));
        tmpTail[strlen(path)+1] = '\0';
    } else {
        if (sep == path) {
            tmpHead[0] = SEP;
            tmpHead[1] = '\0';
        } else {
            strncpy(tmpHead, path, sep-path);
            tmpHead[sep-path] = '\0';
        }
#ifdef WIN32
        if (strlen(tmpHead) == 2 && tmpHead[1] == ':') {
            /* _SplitPath("C:\\trentm") -> ("C:\\", "trentm") */
            tmpHead[2] = SEP;
            tmpHead[3] = '\0';
        }
#endif
        strcpy(tmpTail, sep+1);
    }
    if (head) {
        strcpy(head, tmpHead);
    }
    if (tail) {
        strcpy(tail, tmpTail);
    }
}

/* Create the given directory (creating each parent dir in turn, as
 * necessary).
 * Returns zero iff not successful.
 */
static int _MakeDirs(char *dirpath)
{
    int retval;
    char head[MAXPATHLEN+1], tail[MAXPATHLEN+1];

    if (strlen(dirpath) > MAXPATHLEN) {
        _LogError("cannot create directory path: path too long (>%d): '%s'",
                  MAXPATHLEN, dirpath);
        return 0;
    }
    /* Copying algorithm from Python's os.makedirs(). */
    _SplitPath(dirpath, head, tail);
    if (!strlen(tail)) {
        _SplitPath(head, head, tail);
    }
    if (strlen(head) && strlen(tail) && !_IsDir(head)) {
        if(! _MakeDirs(head)) {
            return 0;
        }
    }

#ifdef WIN32
    {
        wchar_t *dirpathw = _ToUTF16(dirpath);
        BOOL success = CreateDirectoryW(dirpathw, NULL);
        free(dirpathw);
        retval = success ? 0 : -1;
    }
#else /* i.e. linux */
    retval = mkdir(dirpath, 0777);
#endif /* WIN32 */
    if (retval == -1) {
        _LogError("error creating '%s': %s\n", dirpath, strerror(errno));
        return 0;
    }
    return 1;
}


#ifdef WIN32
/* xpgetenv - mimic getenv(); needed on Windows to return UTF8 strings.
*/
static char *xpgetenv(const char* name)
{
    static char buffer[BUF_LENGTH];
    static wchar_t buffer_w[BUF_LENGTH];
    wchar_t *namew = _ToUTF16(name);
    DWORD result = GetEnvironmentVariableW(namew, buffer_w, BUF_LENGTH);
    free(namew);
    if (!result) {
        return NULL;
    }
    (void)WideCharToMultiByte(CP_UTF8, 0, buffer_w, -1, buffer, BUF_LENGTH,
                              NULL, NULL);
    return buffer;
}
#else
static char *xpgetenv(const char *name)
{
    return getenv(name);
}
#endif

/* xpsetenv - mimic the Linux std call to set an environment variable
 * this is needed since Windows needs to deal with Unicode
 */
static int xpsetenv(const char *name, const char *value, int overwrite)
{
#ifdef WIN32
    int failed;
    wchar_t *namew = _ToUTF16(name), *valuew = NULL;
    if (value) {
        valuew = _ToUTF16(value);
    }
    /* We need to set the environment two ways: SetEnvironmentVariableW modifies
     * the Windows environment block, and is used for spawned sub-processes
     * (which is required to pass things to the real Komodo from the stub);
     * _wputenv_s modifies the current process's CRT environment block, which is
     * reflected in things like what Python sees.  See bug 93912 for details.
     */
    /* SetEnvironmentVariableW returns non-zero on success */
    failed = !SetEnvironmentVariableW(namew, valuew);
    /* _wputenv_s returns zero on success */
    if (!valuew) {
        /* Must use the empty string for _wputenv_s, NULL will cause a crash! */
        failed |= _wputenv_s(namew, L"");
    } else {
        failed |= _wputenv_s(namew, valuew);
    }
    free(namew);
    if (valuew) {
        free(valuew);
    }
    return failed;
#else
    return setenv(name, value, 1);
#endif
}

/* xpunsetenv - mimic the Linux std call to unset an environment variable
 *
 * This is needed since Windows needs to deal with Unicode
 */
static int xpunsetenv(const char *name)
{
#ifdef WIN32
    return xpsetenv(name, NULL, 1);
#else
    return unsetenv(name);
#endif
}

#ifdef WIN32
/* Determine the absolute path to the dir containing this binary.
 *
 *    Takes into account the current working directory, etc.
 */
static char* _GetProgramDir(char* argv0)
{
    /*XXX this is ugly but I didn't want to use malloc, no reason */
    static wchar_t progPathW[MAXPATHLEN+1];
    static char progPath[MAXPATHLEN+1];
    wchar_t *p;

    /* get absolute path to module */
    if (!GetModuleFileNameW(NULL, progPathW, MAXPATHLEN)) {
        _LogError("could not get absolute program name from "\
                  "GetModuleFileName\n");
        exit(1);
    }
    /* just need dirname */
    for (p = progPathW+wcslen(progPathW);
         *p != SEP && *p != ALTSEP;
         --p)
        {
            /* nothing */
        }
    *p = L'\0';  /* remove the trailing SEP and anything after */
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
        char *home = xpgetenv("HOME");
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
_GetProgramDir(char* argv0)
{
    /* XXX this routine does *no* error checking */
    static char progPath[MAXPATHLEN+1];
    char* path = xpgetenv("PATH");
    char* pLetter;

    /* If there is no slash in the argv0 path, then we have to
     * assume the program is on the user's $PATH, since there's no
     * other way to find a directory to start the search from.  If
     * $PATH isn't exported, you lose.
     */
    if (strchr(argv0, SEP)) {
        strncpy(progPath, argv0, MAXPATHLEN);
    }
    else if (path) {
        size_t bufspace = MAXPATHLEN;
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

            _JoinPath(progPath, argv0);
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

    /* Resolve symlinks
     */
    char* pathBuf = realpath(progPath, NULL);
    if (pathBuf) {
        strncpy(progPath, pathBuf, MAXPATHLEN);
        free(pathBuf);
    }

    /* 'progPath' now contains the full path to the program *and* the
     * program name. We only want the dirname. */
    _SplitPath(progPath, progPath, NULL);

    return progPath;
}
#endif  /* WIN32 */


/* _GetOSName
 *   Get the host-specific operating system name.
 *   Return value is a null terminated string.
 *   VC6 limits us to what information we can retrieve, whilst in later versions
 *   if the compiler (vc7, vc8) there is more information about systems available.
 */
#define     MAX_OS_NAME     1024

#ifdef WIN32
#define     WIN_BUFSIZE     80
#define     SM_SERVERR2     89
typedef void (WINAPI *PGNSI) (LPSYSTEM_INFO);
#endif /* WIN32 */

static char* _GetOSName(void)
{
    static int haveOSName = 0;
    static char osName[MAX_OS_NAME+1]; /* static to cheaply avoid malloc/free */

#ifdef WIN32
    /* Windows information, this code comes from MSDN OSVERSIONINFOEX:
     *   http://msdn.microsoft.com/en-us/library/windows/desktop/ms724833.aspx
     *   XXX - If Windows add a new OS type, then this will have to be updated.
     */
    OSVERSIONINFOEX osvi;
    DWORD version;

    /* Return early if already have value from previous runs. */
    if (haveOSName) {
        return osName;
    }
    
    ZeroMemory(&osvi, sizeof(osvi));
    osvi.dwOSVersionInfoSize = sizeof(osvi);

    strncpy(osName, "Unknown windows machine", MAX_OS_NAME);
    osName[MAX_OS_NAME] = '\0'; // Should not be needed, but I err on the side of caution

    if (! GetVersionEx ( (OSVERSIONINFO *) &osvi) ) {
        return osName;
    }

    version = (osvi.dwMajorVersion * 10) + (osvi.dwMinorVersion / 10) + (osvi.dwMinorVersion % 10);
    switch (version) {
        // Test for the Windows NT product family.
        case 62:
            if (osvi.wProductType == VER_NT_WORKSTATION) {
                strncpy (osName, "Windows 8 ", MAX_OS_NAME);
            } else {
                strncpy (osName, "Windows Server 2012 ", MAX_OS_NAME);
            }
            break;
        case 61:
            if (osvi.wProductType == VER_NT_WORKSTATION) {
                strncpy (osName, "Windows 7 ", MAX_OS_NAME);
            } else {
                strncpy (osName, "Windows Server 2008 R2 ", MAX_OS_NAME);
            }
            break;
        case 60:
            if (osvi.wProductType == VER_NT_WORKSTATION) {
                strncpy (osName, "Windows Vista ", MAX_OS_NAME);
            } else {
                strncpy (osName, "Windows Server 2008 ", MAX_OS_NAME);
            }
            break;
        case 52:
            if (GetSystemMetrics(SM_SERVERR2) != 0) {
                strncpy (osName, "Windows Server 2003 R2 ", MAX_OS_NAME);
            } else if (osvi.wSuiteMask & VER_SUITE_WH_SERVER) {
                strncpy (osName, "Windows Home Server ", MAX_OS_NAME);
            } else if (osvi .wProductType == VER_NT_WORKSTATION) {
                /* the only 5.2 workstation was XP64 */
                strncpy (osName, "Windows XP Professional x64 Edition ", MAX_OS_NAME);
            } else {
                strncpy (osName, "Windows Server 2003 ", MAX_OS_NAME);
            }
            break;
        case 51:
            strncpy (osName, "Windows XP ", MAX_OS_NAME);
            break;
        case 50:
            strncpy (osName, "Windows 2000 ", MAX_OS_NAME);
            break;
        default:
            if (osvi.wProductType == VER_NT_WORKSTATION) {
                snprintf (osName, MAX_OS_NAME, "Unknown Windows version %i.%i ",
                          osvi.dwMajorVersion, osvi.dwMinorVersion);
            } else {
                snprintf (osName, MAX_OS_NAME, "Unknown Windows server version %i.%i ",
                          osvi.dwMajorVersion, osvi.dwMinorVersion);
            }
            break;
    }
#else /* !WIN32 */

    struct utsname u;

    /* Return early if already have value from previous runs. */
    if (haveOSName) {
        return osName;
    }
    
    uname (&u);
    snprintf ( osName, MAX_OS_NAME, "%s release %s on %s (%s)",
               u.sysname, u.release, u.machine, u.version);
#endif

    haveOSName = 1;
    osName[MAX_OS_NAME] = '\0'; // Ensure at least NULL terminated
    return osName; 
}

/* _GetVerUserDataDir
 *   Get a (versioned) user-specific Komodo data directory. XXX This
 *   should be kept in sync with koDirs.py. Return value is like the
 *   Win32 API GetTempPath, i.e. length of the path on sucess, 0 on
 *   failure.
 */
static int _GetVerUserDataDir(
    size_t nBufferLength,    /* size of buffer */
    char*  lpBuffer          /* path buffer */
)
{
    char *envPath = xpgetenv("KOMODO_USERDATADIR");
    ssize_t overflow;

    if (envPath && strlen(envPath)) {
        /* Currently don't handle "~" expansion in paths. */
        if (envPath[0] == '~') {
            _LogError("cannot expand '~' in KOMODO_USERDATADIR: '%s'\n",
                      envPath);
            return 0;
        }

        if (nBufferLength < strlen(envPath)+1) {
            _LogError("buffer is too small for KOMODO_USERDATADIR: '%s'\n",
                      envPath);
            return 0;
        }

        /* append "Major.Minor" */
        overflow = snprintf(lpBuffer, nBufferLength,
            "%s%c%s", envPath, SEP, KO_SHORT_VERSION);
        if (overflow > (ssize_t)nBufferLength || overflow < 0) {
            _LogError("buffer overflow while determining "\
                "Komodo user data directory\n");
            return 0;
        }

        /* Create the directory if necessary. */
        if (! _IsDir(lpBuffer)) {
            if (!_MakeDirs(lpBuffer)) {
                _LogError("could not create user data dir: '%s'\n", lpBuffer);
                return 0;
            }
        }
    }
    
    else {
#if defined(WIN32)
        HMODULE hShell32;
        BOOL freeHandle = FALSE;
        hShell32 = GetModuleHandle(TEXT("shell32.dll"));
        if (!hShell32) {
            hShell32 = LoadLibrary(TEXT("shell32.dll"));
            freeHandle = TRUE;
        }
        lpBuffer[0] = 0;
        if (hShell32) {
            // Try the Vista "SHGetKnownFolderPath" first, and then
            // fall back to the Win2K "SHGetFolderPath"
            // Don't bother with GetVersionEx(), because the user
            // might have installed a service pack for the older OS that
            // added "SHGetKnownFolderPath".
            //
            // This falls in the category of "test for the feature, not the OS
            // version".

            // Vista, W7, future versions...
            const char *funcName = "SHGetKnownFolderPath";
            HRESULT hr;
            WCHAR wideCharPath[MAX_PATH+1];
            
            typedef HRESULT (WINAPI * SHGetKnownFolderPathFn)(const GUID *rfid,
                                                              DWORD dwFlags,
                                                              HANDLE hToken,
                                                              PWSTR *ppszPath);
            SHGetKnownFolderPathFn shGetFolderPathFunc;
            shGetFolderPathFunc =
                (SHGetKnownFolderPathFn) GetProcAddress(hShell32, funcName);

            wideCharPath[0] = 0;
            if (shGetFolderPathFunc) {
                // Defined in Microsoft SDKs/Windows/v6.1/Include/KnownFolders.h
                PWSTR path;
                // Copy constant to a var so we can pass it by reference
                GUID guid_LocalAppData = FOLDERID_LocalAppData;
                HMODULE hOLE32;
                hr = shGetFolderPathFunc(&guid_LocalAppData,
                                         0, NULL, &path);
                if (hr == S_OK) {
                    if (wcslen(path) < MAX_PATH) {
                        wcscpy(wideCharPath, path);
                    } else {
                        fprintf(stderr, "Komodo startup: can't copy %d chars from path into %d-sized wideCharPath\n",
                                wcslen(path), MAX_PATH);
                    }
                    // The MSDN docs say to use CoTaskMemFree to free this memory.
                    // We avoid linking OLE32 on XP systems by checking to see
                    // if it's already loaded and making a dynamic call.
                    // If it isn't loaded, leak the few dozen bytes.
                    hOLE32 = GetModuleHandle(TEXT("ole32.dll"));
                    if (hOLE32) {
                        typedef void (WINAPI * CoTaskMemFreeFn)(LPVOID pv);
                        CoTaskMemFreeFn coTaskMemFreeFunc;
                        coTaskMemFreeFunc = (CoTaskMemFreeFn) GetProcAddress(hOLE32, "CoTaskMemFree");
                        if (coTaskMemFreeFunc) {
                            coTaskMemFreeFunc(path);
                        }
                    }
                }
            }
            if (!wideCharPath[0]) {
                typedef HRESULT (WINAPI* SHGetFolderPathFn)(HWND hwndOwner,
                                                           int nFolder,
                                                           HANDLE hToken,
                                                           DWORD dwFlags,
                                                           WCHAR *pszPath);
                SHGetFolderPathFn shGetFolderPathFunc;
                funcName = "SHGetFolderPathW"; // ASCII version
                shGetFolderPathFunc =
                    (SHGetFolderPathFn) GetProcAddress(hShell32, funcName);
                if (shGetFolderPathFunc) {
                    hr = shGetFolderPathFunc(NULL, CSIDL_LOCAL_APPDATA,
                                             NULL, 0, wideCharPath);
                }
            }
            if (wideCharPath[0]) {
                char *utf8Path = _ToUTF8(wideCharPath);
                strncpy(lpBuffer, utf8Path, nBufferLength);
                lpBuffer[nBufferLength - 1] = '\0';
                free(utf8Path);
            }
            if (freeHandle) {
                FreeLibrary(hShell32);
            }
        }

        if (!lpBuffer[0]) {
            /* Fallback looking at this deprecated registry key.
             *    HKEY_CURRENT_USER\Software\Microsoft\Windows\
             *          CurrentVersion\Explorer\Shell Folders\AppData
             * in the registry.
             */
            LONG retval;
            HKEY hKey;
            char* keyName =
                "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders";
            unsigned int i;
            DWORD nValues;

            retval = RegOpenKeyEx(HKEY_CURRENT_USER, keyName, 0,
                                  KEY_QUERY_VALUE, &hKey);
            if (retval != ERROR_SUCCESS) {
                /*XXX could use FormatMessage to kick out a better error message */
                _LogError("failed to open the registry key: '%s'.\n", keyName);
                return 0;
            }
            retval = RegQueryInfoKey(
                                     hKey, NULL, NULL, NULL, NULL, NULL, NULL,
                                     &nValues,  /* number of subkeys */
                                     NULL, NULL, NULL, NULL);
            if (retval != ERROR_SUCCESS) {
                _LogError("failed to get the number of the values "\
                          "of key: '%s'.\n", keyName);
                return 0;
            } else if (nValues == 0) {
                _LogError("there were no values for the key: '%s'.\n", keyName);
                return 0;
            }
            for (i = 0; i < nValues; ++i) {
                wchar_t value[MAXPATHLEN];
                unsigned long lenValue = MAXPATHLEN;
                BYTE data[MAXPATHLEN];
                unsigned long lenData = MAXPATHLEN;

                retval = RegEnumValueW(hKey, i,
                                       value, &lenValue, NULL, NULL, data, &lenData);
                if (retval != ERROR_SUCCESS) {
                    _LogError("enumerating index %d of key: '%s'.\n", i, keyName);
                    return 0;
                }
                if (wcsncmp(value, L"AppData", MAXPATHLEN) == 0) {
                    char* utf8Path = _ToUTF8((wchar_t*)data);
                    strncpy(lpBuffer, utf8Path, nBufferLength);
                    lpBuffer[nBufferLength - 1] = '\0';
                    free(utf8Path);
                    /*XXX should check strncpy retval for error */
                    break;
                }
            } 
            RegCloseKey(hKey);
        }
        /* append "ActiveState\Komodo[IDE|Edit]\[Major].[Minor]" and create it
         * if necessary.
         */
        overflow = snprintf(lpBuffer, nBufferLength,
                            "%s%cActiveState%c%s%c%s", lpBuffer, SEP, SEP,
                            KO_APPDATADIR_NAME, SEP, KO_SHORT_VERSION);
        if (overflow > (ssize_t)nBufferLength || overflow < 0) {
            _LogError("buffer overflow while determining "\
                "Komodo user data directory\n");
            return 0;
        }
        if (! _IsDir(lpBuffer)) {
            if (!_MakeDirs(lpBuffer)) {
                _LogError("error creating '%s': %s\n", lpBuffer, strerror(errno));
                return 0;
            }
        }

#elif defined(MACOSX)
        char tmpBuffer[MAXPATHLEN];
        ssize_t overflow;


// #if MOZILLA_VERSION_MAJOR < 35
        FSRef fsRef;
        OSErr err = FSFindFolder(kUserDomain, kApplicationSupportFolderType,
                                 kCreateFolder, &fsRef);
        if (err) {
          _LogError("Unable to determine the User Data Directory\n");
          return 0;
        }
        err = FSRefMakePath(&fsRef, lpBuffer, nBufferLength);
        if (err) {
          _LogError("Unable to determine the User Data Directory\n");
          return 0;
        }
        /* have "~/Library/Application Support" 
         * append "Komodo[IDE|Edit]/<ver>"
         */

        overflow = snprintf(tmpBuffer, MAXPATHLEN,
            "%s%c%s%c%s", 
            lpBuffer, SEP, KO_APPDATADIR_NAME, SEP, KO_SHORT_VERSION);
// #else
        NSArray *paths = NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory, NSUserDomainMask, YES);
        if ([paths count] == 0) {
          _LogError("Unable to determine the User Data Directory\n");
          return 0;
        }
        NSString *appSupportDir = [paths objectAtIndex:0];
        /* have "~/Library/Application Support" 
         * append "Komodo[IDE|Edit]/<ver>"
         */

        overflow = snprintf(tmpBuffer, MAXPATHLEN,
            "%s%c%s%c%s", 
            [appSupportDir UTF8String], SEP, KO_APPDATADIR_NAME, SEP, KO_SHORT_VERSION);
// #endif


        if (overflow > (ssize_t)nBufferLength || overflow < 0) {
            _LogError("buffer overflow while determining "\
                      "Komodo user data directory\n");
            return 0;
        }
        strncpy(lpBuffer, tmpBuffer, nBufferLength); /*XXX should check retval */
        if (! _IsDir(lpBuffer)) {
            if (!_MakeDirs(lpBuffer)) {
                _LogError("could not create user data dir: '%s'\n", lpBuffer);
                return 0;
            }
        }
        /* Clear ACLs on the user data directory; bug 91899 */
        acl_t acl = acl_init(0);
        if (acl) {
            acl_set_file(lpBuffer, ACL_TYPE_EXTENDED, acl);
            acl_free(acl);
        }

#else /* linux, solaris */
        /* use ~/.komodo[ide|edit] */
        char tmpBuffer[MAXPATHLEN];
        char* home = xpgetenv("HOME");
        size_t overflow;
        if (home) {
            overflow = snprintf(lpBuffer, nBufferLength,
                "%s%c.%s", home, SEP, KO_APPDATADIR_NAME);
            if (overflow > nBufferLength || overflow < 0) {
                _LogError("buffer overflow while determining "\
                    "Komodo user data directory\n");
                return 0;
            }
        } else {
            _LogError("could not determine home directory from HOME "\
                "environment variable\n");
            return 0;
        }
        /* create ~/.komodo if it does not exist */
        if (! _IsDir(lpBuffer)) {
            int retval = mkdir(lpBuffer, 0777);
            if (retval == -1) {
                _LogError("error creating '%s': %s\n", lpBuffer, strerror(errno));
                return 0;
            }
        }
        /* append "Major.Minor" and create it if necessary */
        overflow = snprintf(tmpBuffer, MAXPATHLEN,
            "%s%c%s", lpBuffer, SEP, KO_SHORT_VERSION);
        if (overflow > nBufferLength || overflow < 0) {
            _LogError("buffer overflow while determining "\
                "Komodo user data directory\n");
            return 0;
        }
        strncpy(lpBuffer, tmpBuffer, nBufferLength); /*XXX should check retval */
        if (! _IsDir(lpBuffer)) {
            int retval = mkdir(lpBuffer, 0777);
            if (retval == -1) {
                _LogError("error creating '%s': %s\n", lpBuffer, strerror(errno));
                return 0;
            }
        }
#endif /* linux, solaris */
    }

    /* ensure there is a trailing dir separator (as with GetTempPath) */
    lpBuffer[strlen(lpBuffer)+1] = '\0';
    lpBuffer[strlen(lpBuffer)] = SEP;
    return strlen(lpBuffer);
}


#ifndef WIN32
/* _fullpath - mimic the Win32 API call to convert a path from
 *             relative to absolute
 */
static char *_fullpath( char *absPath, const char *relPath, size_t maxLength )
{
    if (strlen(relPath) + 1 > maxLength) {
        return NULL;
    }
    if (relPath[0] == '/') {
        strcpy(absPath, relPath);
    } else if (relPath[0] == '~') {
        const char *home;
        struct passwd *pPtr;
        if (relPath[1] == '/' || relPath[1] == '\0') {
            pPtr = getpwnam((const char *)getlogin());
            home = relPath + 1;
        } else {
            home = strchr((const char *)relPath, '/');
            if (home) {
                strncpy(absPath, relPath + 1, home - relPath - 1);
                absPath[home-relPath-1] = '\0';
                pPtr = getpwnam((const char *)absPath);
            } else {
                pPtr = getpwnam((const char *)(relPath + 1));
            }
        }
        if ((pPtr == NULL) ||
            (strlen(pPtr->pw_dir) + strlen(relPath) + 1 >
                maxLength)) {
            return NULL;
        }
        strcpy(absPath, pPtr->pw_dir);
        if (home) strcat(absPath, home);
    } else {
        int len;
        if (getcwd(absPath, maxLength) == NULL) {
            return NULL;
        }
        len = strlen(absPath);
        if (len + strlen(relPath) + 1 /* SEP */ +
            1 /* null */ > maxLength) {
            return NULL;
        }
        absPath[len] = '/';
        absPath[len+1] = '\0';
        strncat(absPath, relPath, maxLength-len);
    }
    return absPath;
}
#endif


/* Return true if the given executable name is on the PATH env var */
static int _IsExecutableOnPath(char* exeName) {
    char* path = xpgetenv("PATH");
    char* firstChar = path;   /* first char of one path element */
    char* lastChar;
    char* delim;
    /* skip a possible leading DELIM */
    if (*firstChar == DELIM && strlen(path) > 1) {
        firstChar++;
    }
    while (1) {
        /* find the last char of the next path element */
        delim = strchr(firstChar, DELIM);
        if (delim == NULL) {
            lastChar = path + strlen(path);
        } else {
            lastChar = delim - 1;
        }
        /* process any non-zero path element */
        if (lastChar - firstChar + 1 > 0) {
            /* get the path element */
            char pathDir[MAXPATHLEN];
            strncpy(pathDir, firstChar, lastChar-firstChar+1);
            pathDir[lastChar-firstChar+1] = '\0';
            /* append exeName to path and see if that is an existing exe file */
            if (pathDir[strlen(pathDir)] != SEP) {
                pathDir[strlen(pathDir)+1] = '\0';
                pathDir[strlen(pathDir)] = SEP;
            }
            /*XXX overflow? */
            strncat(pathDir, exeName, MAXPATHLEN-strlen(pathDir));
            if (_IsExecutableFile(pathDir)) {
                return 1;
            }
        }
        /* determine first char of next path element */
        if (lastChar >= path + strlen(path) - 1) {
            break;
        } else {
            firstChar = lastChar + 2;
        }
    }
    return 0;
}


/* ---- Startup synchronization and commandment system routines. ---- */

/* Return the mutex (file)name.
 *  Windows:  komodo-<ver>-mutex
 *  Mac OS X: ~/Library/Application Support/ActiveState/Komodo/<ver>/mutex.lock
 *  Unix:     ~/.komodo/<ver>/mutex.lock
 */
static char* _KoStart_GetMutexName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
#ifdef WIN32
        size_t overflow = snprintf(buffer, MAXPATHLEN, 
                "komodo-%s-mutex", KO_SHORT_VERSION);
        if (overflow > MAXPATHLEN || overflow < 0) {
            _LogError("buffer overflow while determining mutex name\n");
            exit(1);
        }
#else
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
        strncat(buffer, "mutex.lock", MAXPATHLEN-strlen(buffer));
#endif /* !WIN32 */
        _LogDebug("mutex name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}

/* Return the running lock (file)name.
 *  Windows:  %APPDATA%\ActiveState\Komodo[IDE|Edit]\<ver>\running.lock
 *  Mac OS X: ~/Library/Application Support/ActiveState/KomodoIDE/<ver>/running.lock
 *  Unix:     ~/.komodoide/<ver>/running.lock
 */
static char* _KoStart_GetRunningName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
        strncat(buffer, "running.lock", MAXPATHLEN-strlen(buffer));
        _LogDebug("running lock name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}

#ifdef WIN32
static char* _KoStart_GetCommandmentsLockName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        size_t overflow = snprintf(buffer, MAXPATHLEN, 
                "komodo-%s-%s-commandments-lock", KO_PROD_TYPE,
                KO_SHORT_VERSION);
        if (overflow > MAXPATHLEN || overflow < 0) {
            _LogError("buffer overflow while determining commandments lock name\n");
            exit(1);
        }
        _LogDebug("commandments lock name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}
#endif

#ifdef WIN32
static char* _KoStart_GetCommandmentsEventName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        size_t overflow = snprintf(buffer, MAXPATHLEN, 
                "komodo-%s-%s-new-commandments", KO_PROD_TYPE,
                KO_SHORT_VERSION);
        if (overflow > MAXPATHLEN || overflow < 0) {
            _LogError("buffer overflow while determining commandments event name\n");
            exit(1);
        }
        _LogDebug("commandments event name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}
#endif

/* Return the commandments file/pipe name.
 *  Windows:  %APPDATA%\ActiveState\Komodo[IDE|Edit]\<ver>\commandments.txt
 *  Mac OS X: ~/Library/Application Data/Komodo[IDE|Edit]/<ver>/commandments.fifo
 *  Unix:     ~/.komodo[ide|edit]/<ver>/commandments.fifo
 */
static char* _KoStart_GetCommandmentsFileName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
#ifdef WIN32
        strncat(buffer, "commandments.txt", MAXPATHLEN-strlen(buffer));
#else
        strncat(buffer, "commandments.fifo", MAXPATHLEN-strlen(buffer));
#endif
        _LogDebug("commandments file name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}

#ifndef WIN32
static char* _KoStart_GetFirstCommandmentsFileName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
        strncat(buffer, "first-commandments.txt", MAXPATHLEN-strlen(buffer));
        _LogDebug("first commandments file name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}
#endif

static char* _KoStart_GetStartupEnvFileName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
        strncat(buffer, "startup-env.tmp", MAXPATHLEN-strlen(buffer));
        _LogDebug("startup env name: '%s'\n", buffer);
        determined = 1;
    }
    return buffer;
}

static char* _KoStart_GetStartupLogFileName()
{
    static int determined = 0;
    static char buffer[MAXPATHLEN+1];
    if (!determined) {
        if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
            _LogError("could not determine the user data dir\n");
            exit(1);
        }
        strncat(buffer, "startup.log", MAXPATHLEN-strlen(buffer));
        determined = 1;
    }
    return buffer;
}


#ifndef WIN32
void _KoStart_CloseFD(int fd, char* filename)
{
    if (fd > 0) {
        int rv = close(fd);
        if (rv == -1) {
            _LogError("unexpected error closing fd for '%s': %d: %s\n",
                      filename, errno, strerror(errno));
            exit(1);
        }
    }
}
#endif


/* Save the startup environment to a temp file.
 * This is done so that the running Komodo can restore the user's
 * environment before running any processes on behalf of the user (e.g. running
 * or debugging a script).
 */
void _KoStart_SaveStartupEnvironment()
{
    /* create temp file to which environ is written */
    char* envFileName = _KoStart_GetStartupEnvFileName();
    FILE* envFile = NULL;
    char* envVar;
    int i;

#ifdef WIN32
    wchar_t* envFileNameW = _ToUTF16(envFileName);
    envFile = _wfopen(envFileNameW, L"w");
    free(envFileNameW);
#else
    envFile = fopen(envFileName, "w");
#endif
    if (envFile == NULL) {
        _LogError("could not open '%s' for writing\n", envFileName);
        exit(1);
    }

    /* write out the environment */
    _LogDebug("writing out startup environment\n");
    for(i = 0, envVar = environ[i]; envVar != NULL; i++, envVar = environ[i]) {
#ifdef WIN32
        if (envVar[0] == '=' && envVar[1] != '\0'
		&& envVar[2] == ':' && envVar[3] == '=') {
            /* skip the "=X:" environment vars on Windows
             *  (these are the ones list the current dir on each system drive)
             */
	    continue;
        } else if (strncmp("=ExitCode", envVar, 9) == 0) {
            /* skip the "=ExitCode" env var */
	    continue;
        }
#endif /* WIN32 */
	fprintf(envFile, "%s\n", envVar);
    }

    /* close output file */
    if (fclose(envFile)) {
        _LogError("could not close '%s'\n", envFileName);
        exit(1);
    }
}


/* Setup the environment as required for running Komodo */
void _KoStart_SetupEnvironment(const char* programDir)
{
    size_t overflow = 0;
    char *envVar;
    char buffer[MAXPATHLEN+1];
/* #if PP_IS_GTK2_SILOED */
    char buf[BUF_LENGTH+1];
/* #endif */

    /* ---- Setup Mozilla- and XRE-related environment variables ---- */

    /* Set MOZ_NO_REMOTE=1.
     *
     * This is to make sure Komodo does not try to remote to another running
     * Komodo version.
     */
    _LogDebug("setting MOZ_NO_REMOTE=1\n");
    xpsetenv("MOZ_NO_REMOTE", "1", 1);

#ifdef MACOSX
    /* Set PYTHONHOME=$programDir/../Frameworks/Python.framework/Versions/Current
     *
     * Pyxpcom needs to know where it's Python lives.
     */
    overflow = snprintf(buffer, MAXPATHLEN, "%s/../Frameworks/Python.framework/Versions/Current", programDir);
    if (overflow > (ssize_t)MAXPATHLEN || overflow < 0) {
        _LogError("buffer overflow while setting PYTHONHOME\n");
        return;
    }
    _LogDebug("setting PYTHONHOME=%s\n", buffer);
    xpsetenv("PYTHONHOME", buffer, 1);
#else
    /* Set PYTHONHOME=$programDir/../python
     *
     * Pyxpcom needs to know where it's Python lives.
     */
    overflow = snprintf(buffer, MAXPATHLEN, "%s%c..%cpython", programDir, SEP, SEP);
    if (overflow > (ssize_t)MAXPATHLEN || overflow < 0) {
        _LogError("buffer overflow while setting PYTHONHOME\n");
        return;
    }
    _LogDebug("setting PYTHONHOME=%s\n", buffer);
    xpsetenv("PYTHONHOME", buffer, 1);
#endif

    /* Set XRE_PROFILE_PATH and _XRE_USERAPPDATADIR to "XRE"
     * under the Komodo host user data dir. */
    if (!_GetVerUserDataDir(MAXPATHLEN, buffer)) {
        _LogError("could not determine the user data dir\n");
        exit(1);
    }
    _LogDebug("setting %s=%s\n", "_KOMODO_VERUSERDATADIR", buffer);
    xpsetenv("_KOMODO_VERUSERDATADIR", buffer, 1);
    if (_KoStart_verbose) {
        _LogDebug("setting %s=1\n", "KOMODO_VERBOSE", buffer);
        xpsetenv("KOMODO_VERBOSE", "1", 1);
    }
    strncat(buffer, "XRE", MAXPATHLEN - strlen(buffer));
    if (! _IsDir(buffer)) {
        if (!_MakeDirs(buffer)) { /* XRE startup fails if profile dir doesn't exist */
            _LogError("could not create the XRE appdata dir: '%s'\n", buffer);
            exit(1);
        }
    }
    _LogDebug("setting XRE_PROFILE_PATH=%s\n", buffer);
    xpsetenv("XRE_PROFILE_PATH", buffer, 1);
    _LogDebug("setting _XRE_USERAPPDATADIR=%s\n", buffer);
    xpsetenv("_XRE_USERAPPDATADIR", buffer, 1);

#if !defined(WIN32)
    /* Unset MOZILLA_FIVE_HOME if it is set.
     * - Gentoo Linux, for example, liked to do this for the system
     *   Mozilla installation. This screws up Komodo startup. See bug
     *   26376.
     * - I *think* the Komodo startup (in run-mozilla.sh) is immune to
     *   an external MOZILLA_FIVE_HOME setting (run-mozilla.sh sets its
     *   own value).
     *   XXX I'm not sure, then, if we should NOT remove it here. Try
     *       both ways on Linux and Mac OS X.
     */
    envVar = xpgetenv("MOZILLA_FIVE_HOME");
    if (envVar) {
        _LogDebug("unsetting MOZILLA_FIVE_HOME env var\n");
        xpunsetenv("MOZILLA_FIVE_HOME");
    }

    /* Unset MOZ_PLUGIN_PATH if it is set.
     * - Mandrake 10.0 likes to set this env var. See bug 34779.
     * - With the move to XRE I don't believe this effects us anymore.
     *   However there is still one usage of MOZ_PLUGIN_PATH in the
     *   Mozilla 1.8 sources, so keep this in for now.
     */
    envVar = xpgetenv("MOZ_PLUGIN_PATH");
    if (envVar) {
        _LogDebug("unsetting MOZ_PLUGIN_PATH env var\n");
        xpunsetenv("MOZ_PLUGIN_PATH");
    }

#endif /* !WIN32 */

#if defined(WIN32)
    /* Unset PYTHONCASEOK if it is set on Windows platforms.
     *
     * This causes *all* remote file operations to fail, due to not
     * being able to import paramiko, since it in turn cannot import
     * the hash libraries from pyCrypto. See bug:
     *   http://bugs.activestate.com/show_bug.cgi?id=66125
     */
    envVar = xpgetenv("PYTHONCASEOK");
    if (envVar) {
        _LogDebug("unsetting PYTHONCASEOK env var\n");
        xpunsetenv("PYTHONCASEOK");
    }
#endif /* WIN32 */

    /* Warn about the presence of environment variables that may affect
     * Komodo.
     */
    if (_KoStart_verbose) {
#ifdef WIN32
        wchar_t* envVar;
#define CHECK(s) (wcsncmp(L ## s, envVar, sizeof(s) - 1) == 0)
#define GET() envVar = _wenviron[i]
#else
        char* envVar;
#define CHECK(s) (strncmp(s, envVar, sizeof(s) - 1) == 0)
#define GET() envVar = environ[i]
#endif
        int i;
        for (i = 0; ; ++i) {
            GET();
            if (envVar == NULL) break;
            if (CHECK("MOZILLA_FIVE_HOME=")
                || CHECK("MOZ_MAXWINSDK=")
                || CHECK("MOZ_PLUGIN_PATH=")
                || CHECK("XRE_PROFILE_PATH=")
                || CHECK("MOZ_SRC=")
                || CHECK("MOZ_TOOLS=")
                || CHECK("MOZ_NO_REMOTE=")
                || CHECK("MOZ_MSVCVERSION=")
                || CHECK("MOZ_NO_RESET_PATH=")
               ) {
                /* skip these, already nulled out or set these ones */
            } else if (CHECK("MOZ_") || CHECK("MOZILLA_") || CHECK("XRE_")) {
                _LogWarning("environment variable could possibly conflict "
                            "with Komodo operation: '%s'\n", envVar);
            }
        }
#undef CHECK
#undef GET
    }

    /* unset PYTHONPATH:
     * - Always overwrite the user's PYTHONPATH. If it is set to point to
     *   another Python installation this could keep Komodo from starting up.
     *   It is the job of Komodo's invocations to restore the user's
     *   PYTHONPATH for debugging, etc.
     */
    envVar = xpgetenv("PYTHONPATH");
    if (envVar) {
        _LogDebug("unsetting PYTHONPATH env var\n");
        xpunsetenv("PYTHONPATH");
    }

/* #if PP_IS_GTK2_SILOED */
    /* set FONTCONFIG_FILE (GTK2 libs are in mozbin dir):
     *  Windows:        (Never depend on GTK2 on Windows.)
     *  Linux/Solaris:  <programDir>/fonts.conf
     *  Mac OS X:       (Never depend on GTK2 on Mac OS X.)
     */
    overflow = snprintf(buf, BUF_LENGTH, "%s%cfonts.conf", programDir, SEP);
    if (overflow > BUF_LENGTH || overflow < 0) {
        _LogError("buffer overflow while setting FONTCONFIG_FILE\n");
        exit(1);
    }
    _LogDebug("setting %s=%s\n", "FONTCONFIG_FILE", buf);
    xpsetenv("FONTCONFIG_FILE", buf, 1);

    /* set GDK_PIXBUF_MODULE_FILE (GTK2 libs are in mozbin dir):
     *  Windows:        (Never depend on GTK2 on Windows.)
     *  Linux/Solaris:  <programDir>/gdk-pixbuf/gdk-pixbuf.loaders
     *  Mac OS X:       (Never depend on GTK2 on Mac OS X.)
     */
    overflow = snprintf(buf, BUF_LENGTH,
        "%s%cgdk-pixbuf%cgdk-pixbuf.loaders", programDir, SEP, SEP);
    if (overflow > BUF_LENGTH || overflow < 0) {
        _LogError("buffer overflow while setting GDK_PIXBUF_MODULE_FILE\n");
        exit(1);
    }
    _LogDebug("setting %s=%s\n", "GDK_PIXBUF_MODULE_FILE", buf);
    xpsetenv("GDK_PIXBUF_MODULE_FILE", buf, 1);

    /* set PANGO_RC_FILE (GTK2 libs are in mozbin dir):
     *  Windows:        (Never depend on GTK2 on Windows.)
     *  Linux/Solaris:  <programDir>/pango/pangorc
     *  Mac OS X:       (Never depend on GTK2 on Mac OS X.)
     */
    overflow = snprintf(buf, BUF_LENGTH,
        "%s%cpango%cpangorc", programDir, SEP, SEP);
    if (overflow > BUF_LENGTH || overflow < 0) {
        _LogError("buffer overflow while setting PANGO_RC_FILE\n");
        exit(1);
    }
    _LogDebug("setting %s=%s\n", "PANGO_RC_FILE", buf);
    xpsetenv("PANGO_RC_FILE", buf, 1);
/* #endif */
}



static void _KoStart_PrintHelp(void)
{
// #if PP_KO_PROD_TYPE == 'ide'
    _LogInfo("\n\
Komodo IDE %s -- ActiveState's cross-platform multi-language IDE\n\
\n\
Komodo IDE is cross-platform integrated development environment\n\
with a rich feature set for client-side Ajax languages such as\n\
CSS, HTML, JavaScript and XML, coupled with advanced support for\n\
dynamic languages such as Perl, PHP, Python, Ruby and Tcl.\n\
\n", KO_MARKETING_SHORT_VERSION);
// #else
    _LogInfo("\n\
Komodo Edit %s -- ActiveState's free multi-language editor\n\
\n\
Komodo Edit is a free, cross-platform and multi-language editor\n\
supporting many languages including Perl, PHP, Python, Ruby,\n\
JavaScript, Tcl, XML, HTML and XSLT.\n\
\n", KO_MARKETING_SHORT_VERSION);
// #endif

    _LogInfo("Usage:\n\
\n\
    komodo [options] [<files>...]\n\
\n\
Options:\n\
    -h, --help   \tshow this help and exit\n\
    -V, --version\tprint the Komodo version and exit\n\
    -v, --verbose\tshow verbose startup and runtime info\n\
\n\
    -n, --new-window\topen a new Komodo window\n\
    -l <line>, --line=<line>\n\
        Open the given file(s) at a specific line; use\n\
        <line>,<column> to open at a specific line and column.\n\
        Alternatively, a line can be specified with a \n\
        pseudo-HTML-anchor syntax, e.g.: 'komodo myscript.pl#42'\n\
        will open 'myscript.pl' at line 42.\n\
    -s <range>, --selection=<range>\n\
        Select a specific range in the given file(s);\n\
        <range> must be one of the following forms:\n\
            1,5-2,15\tselect from line 1 and column 5\n\
                    \tto line 2 column 15\n\
            15-22   \tselect from character 15 to 22\n\
    -P, --use-position\n\
        Interpret column coordinates in --line and --selection as positions,\n\
        not columns, so tabs are counted as one character.\n\
\n");
}



/* Handle command line arguments
 *
 * Parses the command line arguments into an optional list of files to
 * open (nFiles, files) and line and selection startup arguments.
 * Note: This also reacts to the KOMODO_VERBOSE environment variable.
 *
 * Returns one of the following status codes:
 *  KS_ERROR    Error while parsing command-line arguments. App should
 *              exit. An error will have already been logged.
 *  KS_EXIT     The command-line has been fully handled. App should
 *              exit.
 *  KS_CONTINUE The command-line has been parsed into the given data
 *              fields. The app should continue starting up.
 */
int KoStart_HandleArgV(int argc, char** argv, KoStartOptions* pOptions)
{
    /* Variables for option processing. */
    char *shortopts = "hVvnXPl:s:";
    struct option longopts[] = {
        /* name,        has_arg,           flag, val */ /* longind */
        { "version",    no_argument,       0,    'V' }, /*       0 */
        { "help",       no_argument,       0,    'h' }, /*       1 */
        { "verbose",    no_argument,       0,    'v' }, /*       2 */
        { "line",       required_argument, 0,    'l' }, /*       3 */
        { "selection",  required_argument, 0,    's' }, /*       4 */
        { "xml-version",no_argument,       0,    'X' }, /*       5 */
        { "new-window", no_argument,       0,    'n' }, /*       6 */
        { "use-position", no_argument,       0,    'P' }, /*       7 */
        { 0, 0, 0, 0 } /* sentinel */
    };
    int longind = 0;
    int opt;
    memset(pOptions, 0, sizeof(KoStartOptions));

    if (xpgetenv("KOMODO_VERBOSE") != NULL) {
        _KoStart_verbose = 1;
    }

    /* The first thing the driving main(), in nsKomodoApp.cpp, does is
     * call this function. We want to do our normal Komodo option
     * processing *except* in the following cases:
     * 1. We were launched by Launch Services on Mac OS X. In this case
     *    there is one command line arg (starting with "-psn" for
     *    process serial number) and other possible arguments (files to
     *    open) are sent via "odoc" and "oapp" Apple Events.
     *    XXX Do we still get this? How does Firefox's AE handling pick
     *        up the PSN?
     * 2. The special "--raw" argument was used (first). This argument
     *    is specifically there for this: to be able to specify
     *    arguments for XRE directly.
     * 3. This is a re-start of Komodo that XRE sometimes does.
     *    Typically on a first start when XPCOM components are
     *    registered.
     */
#ifdef MACOSX
    /* 1. */
    if (argc > 1 && strncmp(argv[1], "-psn", 4) == 0) {
        _LogDebug("dropping psn argument from Launch Services: '%s'\n",
                  argv[1]);
        return KS_CONTINUE;
    }
#endif
    /* 2. */
    if (argc > 1 && strcmp(argv[1], "--raw") == 0) {
        _LogDebug("internal '--raw' argument found: skipping argv processing\n");
        return KS_CONTINUE;
    }
    /* 3. This internal env var is set in _KoStart_SetupEnvironment(). */
    if (xpgetenv("_KOMODO_VERUSERDATADIR") != NULL) {
        _LogDebug("internal '_KOMODO_VERUSERDATADIR' envvar set: skipping argv processing\n");
        return KS_CONTINUE;
    }

    /* Process options and parse out arguments. */
    opterr = 0;
    while ((opt = getopt_long(argc, argv, shortopts, longopts, &longind)) != -1)
    {
        switch(opt) {
        case 'V':
            _LogInfo("%s\n", KO_FULL_PRETTY_VERSION);
            return KS_EXIT;
        case 'X':
            _LogInfo("<?xml version=\"1.0\"?>\n\
<komodo-version>\n\
    <product-type>%s</product-type>\n\
    <version>%s</version>\n\
    <build-number>%s</build-number>\n\
</komodo-version>\n", KO_PROD_TYPE, KO_VERSION, KO_BUILD_NUMBER);
            return KS_EXIT;
        case 'h':
            _KoStart_PrintHelp();
            return KS_EXIT;
        case 'v':
            opterr++; /* turn up error reporting in getopt as well */
            _KoStart_verbose = 1;
            break;
        case 'l':
            if (pOptions->selection) {
                _LogError("cannot use both -l|--line and -s|--selection options\n");
                return KS_ERROR;
            }
            pOptions->line = optarg;
            break;
        case 'P':
            pOptions->usePosition = 1;
            break;
        case 's':
            if (pOptions->line) {
                _LogError("cannot use both -l|--line and -s|--selection options\n");
                return KS_ERROR;
            }
            pOptions->selection = optarg;
            break;
        case 'n':
            pOptions->newWindow = 1;
            break;
        default:
            _LogError("unknown option '%c', aborting\n", optopt);
            return KS_ERROR;
        }
    }
    if (pOptions->usePosition
        && !pOptions->line
        && !pOptions->selection) {
       _LogError("used -P|--use-position but not either -l|--line or -s|--selection options\n");
       return KS_ERROR;
    }
    if (optind < argc) {
        pOptions->files = argv + optind;
        pOptions->nFiles = argc - optind;
    }

    if (_KoStart_verbose) {
        int i;
        const char *host_os_type;

        host_os_type = _GetOSName();
        _LogDebug("Komodo information:\n");
        _LogDebug("  Version: %s %s\n", KO_FULL_PRETTY_VERSION, KO_BUILD_PLATFORM);
        _LogDebug("  OS type: %s\n", host_os_type);
        _LogDebug("Komodo startup options:\n");
        _LogDebug("\tnFiles: %d\n", pOptions->nFiles);
        for (i=0; i < pOptions->nFiles; ++i) {
            _LogDebug("\tfile %d: %s\n", i, pOptions->files[i]);
        }
        if (pOptions->line != NULL) {
            _LogDebug("\tline: %s\n", pOptions->line);
        }
        if (pOptions->selection != NULL) {
            _LogDebug("\tselection: %s\n", pOptions->selection);
        }
        if (pOptions->usePosition) {
            _LogDebug("\t--use-position: 1\n");
        }
    }
    return KS_CONTINUE;
}


/* Acquire the Komodo-start mutex: blocks until acquired */
KoStartHandle KoStart_AcquireMutex(void)
{
    /* if sys.platform == "win32":
     *     mutex = win32event.CreateMutex(None, 0, gMutexName)
     *     win32event.WaitForSingleObject(mutex, win32event.INFINITE)
     * else:
     *     mutex = os.open(gMutexName, os.O_RDWR | os.O_CREAT)
     *     fcntl.lockf(handle, fcntl.LOCK_EX) # blocks until free
     * return mutex
     */
    char* mutexName = _KoStart_GetMutexName();

#ifdef WIN32
    HANDLE mutex;
    DWORD rv;

    mutex = CreateMutex(NULL, FALSE, mutexName);
    rv = WaitForSingleObject(mutex, INFINITE);
    if (rv == WAIT_OBJECT_0) {
        _LogDebug("acquired mutex: handle=0x%x\n", mutex);
        return mutex;
    } else {
        _LogError("unexpected error acquiring mutex: %d: %d\n",
                  rv, GetLastError());
        if (! CloseHandle(mutex)) {
            _LogError("error closing mutex handle: %d\n", GetLastError());
        }
        return KS_BAD_HANDLE;
    }
#else
    int rv, fd;

    /* Use 00777 permissions to prevent starting lockfile created with
     * permissions that disallow write if left behind.
     */
    fd = open(mutexName, O_RDWR | O_CREAT, 00777);
    if (fd == -1) {
        _LogError("unexpected error creating '%s': [errno %d] %s\n",
                  mutexName, errno, strerror(errno));
        exit(1);
    }

    struct flock flockInfo;
    flockInfo.l_type   = F_WRLCK; /* lock op type */
    flockInfo.l_whence = 0; /* lock base indicator */
    flockInfo.l_start  = SEEK_SET; /* starting offset from base */
    flockInfo.l_len    = 0; /* lock length; 0 means until end of file */
    rv = fcntl(fd, F_SETLKW /* blocking */, &flockInfo);
    if (rv == -1) {
        _LogError("unexpected error locking '%s': [errno %d] %s\n",
                  mutexName, errno, strerror(errno));
        close(fd);
        exit(1);
    }
    _LogDebug("acquired mutex: fd=%x\n", fd);
    return fd;
#endif /* !WIN32 */
}


void KoStart_ReleaseMutex(KoStartHandle mutex)
{
    /* if sys.platform == "win32":
     *     win32event.ReleaseMutex(mutex)
     *     win32api.CloseHandle(mutex)
     * else:
     *     fcntl.lockf(mutex, fcntl.LOCK_UN)
     */
#ifdef WIN32
    if (! ReleaseMutex(mutex)) {
        _LogError("error releasing mutex: %d\n", GetLastError());
        exit(1);
    }
    if (! CloseHandle(mutex)) {
        _LogError("error closing mutex handle: %d\n", GetLastError());
        exit(1);
    }
#else
    int rv;
    char* mutexName = _KoStart_GetMutexName();

    struct flock flockInfo;
    flockInfo.l_type   = F_UNLCK; /* lock op type */
    flockInfo.l_whence = 0; /* lock base indicator */
    flockInfo.l_start  = SEEK_SET; /* starting offset from base */
    flockInfo.l_len    = 0; /* lock length; 0 means until end of file */
    rv = fcntl(mutex, F_SETLK /* non-blocking */, &flockInfo);
    if (rv == -1) {
        _LogError("error unlocking '%s' (fd=%d): [errno %d] %s\n",
                  mutexName, mutex, errno, strerror(errno));
        close(mutex);
        exit(1);
    }

    _KoStart_CloseFD(mutex, mutexName);
#endif /* WIN32 */
}


/* Try to grab an exclusive "running" lock. If successful, we are
 * "the man". Returns either KS_BAD_HANDLE (not the man) or a handle
 * (the man).
 */
KoStartHandle KoStart_WantToBeTheMan(void)
{
    char* runningName = _KoStart_GetRunningName();

#ifdef WIN32
    /* - Open the running lock for reading
     * - Open the running lock again, for exclusive writing
     * - If open for writing fails, we are *not* the man
     * - Else, write pid into running lock
     */
    HANDLE hRead, hWrite;
    char buffer[MAXPATHLEN];
    DWORD byteCount, pid;
    wchar_t *runningNameW = _ToUTF16(runningName);
    hRead = CreateFileW(runningNameW, GENERIC_READ,
                        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                        NULL, OPEN_ALWAYS,
                       FILE_ATTRIBUTE_TEMPORARY | FILE_ATTRIBUTE_HIDDEN,
                       NULL);
    if (hRead == INVALID_HANDLE_VALUE) {
        _LogError("Failed to create %s: %08x\n", runningName, GetLastError());
        exit(1);
    }
    hWrite = CreateFileW(runningNameW, GENERIC_WRITE,
                         FILE_SHARE_READ, NULL, TRUNCATE_EXISTING,
                        FILE_ATTRIBUTE_TEMPORARY | FILE_FLAG_DELETE_ON_CLOSE,
                        NULL);
    free(runningNameW);
    if (hWrite == INVALID_HANDLE_VALUE) {
        /* we are not the man */
        _LogDebug("Another instance of Komodo is already running.\n");
        if (ReadFile(hRead, buffer, MAXPATHLEN - 1, &byteCount, NULL)) {
            buffer[byteCount] = '\0';
            if (sscanf(buffer, "%u", &pid)) {
                AllowSetForegroundWindow(pid);
            }
        }
        CloseHandle(hRead);
        return KS_BAD_HANDLE;
    }
    /* we are the man */
    _LogDebug("No current running Komodo - Ok: handle=0x%x\n", hWrite);
    CloseHandle(hRead);
    snprintf(buffer, MAXPATHLEN - 1, "%u", GetCurrentProcessId());
    buffer[MAXPATHLEN-1] = '\0';
    WriteFile(hWrite, buffer, strlen(buffer), &byteCount, NULL);
    return hWrite;
#else
    /* fd = os.open(gRunningName, os.O_WRONLY|os.O_CREAT)
     * try:
     *     fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
     * except IOError, ex:
     *     os.close(fd)
     *     # Darwin:
     *     #   IOError: [Errno 35] Resource temporarily unavailable
     *     # Elsewhere:
     *     #   IOError: [Errno 11] Resource temporarily unavailable
     *     errorid = (sys.platform == "darwin" and 35 or 11)
     *     if ex.errno == errorid:
     *         return None # we are *not* the man
     *     else:
     *         raise
     * else:
     *     os.write(fd, str(os.getpid()))
     *     return fd # we *are* the man
     */
    int rv, fd;

    /* Use 00777 permissions to prevent starting lockfile created with
     * permissions that disallow write if left behind.
     */
    fd = open(runningName, O_WRONLY | O_CREAT, 00777);
    if (fd == -1) {
        _LogError("unexpected error creating '%s': [errno %d] %s\n",
                  runningName, errno, strerror(errno));
        exit(1);
    }

    struct flock flockInfo;
    flockInfo.l_type   = F_WRLCK; /* lock op type */
    flockInfo.l_whence = 0; /* lock base indicator */
    flockInfo.l_start  = SEEK_SET; /* starting offset from base */
    flockInfo.l_len    = 0; /* lock length; 0 means until end of file */
    rv = fcntl(fd, F_SETLK /* non-blocking */, &flockInfo);
    if (rv == -1) {
        if (errno == EAGAIN) { /*XXX EAGAIN? ENOLCK? something else? */
            _KoStart_CloseFD(fd, runningName);
            _LogDebug("Another instance of Komodo is already running.\n");
            return KS_BAD_HANDLE; /* We are _not_ the man. */
        } else {
            _LogError("unexpected error locking '%s': [errno %d] %s\n",
                      runningName, errno, strerror(errno));
            _KoStart_CloseFD(fd, runningName);
            exit(1);
        }
    }
    _LogDebug("No current running Komodo - Ok: fd=%d\n", fd);
    return fd;
#endif
}


void KoStart_ReleaseTheMan(KoStartHandle theMan)
{
#ifdef WIN32
    if (! CloseHandle(theMan)) {
        _LogError("error closing theMan handle: %d\n", GetLastError());
        exit(1);
    }
#else
    int rv;
    char* runningName = _KoStart_GetRunningName();

    struct flock flockInfo;
    flockInfo.l_type   = F_UNLCK; /* lock op type */
    flockInfo.l_whence = 0; /* lock base indicator */
    flockInfo.l_start  = SEEK_SET; /* starting offset from base */
    flockInfo.l_len    = 0; /* lock length; 0 means until end of file */
    rv = fcntl(theMan, F_SETLK /* non-blocking */, &flockInfo);
    if (rv == -1) {
        _LogError("unexpected error unlocking '%s': [errno %d] %s\n",
                  runningName, errno, strerror(errno));
        close(theMan);
        exit(1);
    }

    _KoStart_CloseFD(theMan, runningName);
#endif /* WIN32 */

}


/* if sys.platform == "win32":
 *     if os.path.exists(gCommandmentsFileName):
 *         os.unlink(gCommandmentsFileName)
 * else:
 *     if os.path.exists(gCommandmentsFileName):
 *         os.remove(gCommandmentsFileName) # start fresh
 *     os.mkfifo(gCommandmentsFileName)
 */
void KoStart_InitCommandments()
{
    char* commandmentsFileName = _KoStart_GetCommandmentsFileName();

#ifdef WIN32
    wchar_t *commandmentsFileNameW = _ToUTF16(commandmentsFileName);
    BOOL rv = DeleteFileW(commandmentsFileNameW);
    if (!rv) {
        DWORD lasterr = GetLastError();
        if (lasterr == ERROR_INVALID_NAME
            || lasterr == ERROR_FILE_NOT_FOUND) {
            /* that's fine, the file didn't exist */
        } else {
            _LogError("error deleting '%s': rv=%d, lasterr=%d",
                      commandmentsFileName, rv, lasterr);
            exit(1);
        }
    }
    free(commandmentsFileNameW);
#else
    int rv;

    rv = unlink(commandmentsFileName);
    if (rv) {
        if (errno == ENOENT) {
            /* that's fine, the file didn't exist */
        } else {
            _LogError("error deleting '%s': [errno %d]: %s",
                      commandmentsFileName, errno, strerror(errno));
            exit(1);
        }
    }

    char* firstCommandmentsFileName = _KoStart_GetFirstCommandmentsFileName();
    rv = unlink(firstCommandmentsFileName);
    if (rv) {
        if (errno == ENOENT) {
            /* that's fine, the file didn't exist */
        } else {
            _LogError("error deleting '%s': [errno %d]: %s",
                      firstCommandmentsFileName, errno, strerror(errno));
            exit(1);
        }
    }

    rv = mkfifo(commandmentsFileName, 00666);
    if (rv) {
        _LogError("error creating '%s': [errno %d]: %s",
                  commandmentsFileName, errno, strerror(errno));
        exit(1);
    }
#endif /* WIN32 */
}

// Transform coordinates of form <LINE>,<COLUMN> to 
// <LINE>,p<COLUMN> if the --use-position option was specified.
static char *insertUsePosition(char *coordinates, int usePosition) {
   static char buf[40];
   char *p_comma, *p_coordinates = coordinates, *p_buf = buf;
   int numToCopy;
   if (!usePosition || strlen(coordinates) > sizeof(buf)) {
      return coordinates;
   }
   while ((p_comma = strchr(p_coordinates, ',')) != NULL) {
      numToCopy = p_comma - p_coordinates + 1;
      strncpy(p_buf, p_coordinates, numToCopy);
      p_buf += numToCopy;
      *p_buf++ = 'p';
      p_coordinates = p_comma + 1;
   }
   strcpy(p_buf, p_coordinates);
   return buf;
}

/* Issue the appropriate commandments to the running (or soon to be)
 * Komodo.
 */
void KoStart_IssueCommandments(const KoStartOptions* pOptions,
                               int isTheMan)
{
    char * commandmentsFileName;
    FILE* commandmentsFile;
    char commandment[MAX_COMMANDMENT_LEN+1];
    char absFile[MAXPATHLEN+1];
    int i;
    ssize_t overflow;
#ifdef WIN32
    wchar_t * commandmentsFileNameW;
    HANDLE lock;
    DWORD rv;
    HANDLE event;
    char* commandmentsLockName = _KoStart_GetCommandmentsLockName();
    char* commandmentsEventName = _KoStart_GetCommandmentsEventName();
#else
    int rv;
#endif

    if (pOptions->nFiles == 0 && !pOptions->newWindow) return;
    _LogDebug("issuing commandments\n");

#ifdef WIN32
    /* Grab the lock. */
    lock = CreateMutex(NULL, FALSE, commandmentsLockName);
    rv = _FriendlyWaitForObject(lock);
    if (rv != 0) {
        _LogError("unexpected result acquiring commandments lock: %d\n", rv);
        exit(1);
    }
#endif

    /* Open the commandments file/pipe. */
#ifdef WIN32
    commandmentsFileName = _KoStart_GetCommandmentsFileName();
#else
    if (isTheMan) {
        /* Because of the use of a fifo for commandment communication on
         * POSIX systems we cannot write the initial commandments to the
         * pipe until the other end of the pipe is up and running. The
         * "other end" here is Komodo's KoCommandmentService PyXPCOM
         * component. We work around by writing the initial set to a
         * different place.
         */
        commandmentsFileName = _KoStart_GetFirstCommandmentsFileName();
    } else {
        commandmentsFileName = _KoStart_GetCommandmentsFileName();
    }
#endif
#ifdef WIN32
    commandmentsFileNameW = _ToUTF16(commandmentsFileName);
    commandmentsFile = _wfopen(commandmentsFileNameW, L"a");
    free(commandmentsFileNameW);
#else
    commandmentsFile = fopen(commandmentsFileName, "a");
#endif
    if (commandmentsFile == NULL) {
        _LogError("could not open '%s' for writing\n",
                  commandmentsFileName);
        exit(1);
    }

    if (pOptions->newWindow) {
        rv = fprintf(commandmentsFile, "new_window\n");
        if (rv != 11) {
            _LogError("error writing new_window commandment to '%s': [rv %d, errno %d] %s",
                      commandmentsFileName, rv, errno, strerror(errno));
            exit(1);
        }
        _LogDebug("issued commandment: new_window\n");
    }

    /* Append the new commandments. */
    for (i = 0; i < pOptions->nFiles; ++i) {
        /* The filenames must be made absolute (or the cwd *could* be passed
         * it) because the Komodo process that actually opens the files
         * will not necessarily have the same cwd.
         */
        if (strstr(pOptions->files[i], "://") != NULL) {
            /* Looks like a URI - leave it alone. */
            strncpy(absFile, pOptions->files[i], MAXPATHLEN);
            absFile[MAXPATHLEN] = '\0';  /* ensure null termination */
        } else {
            _fullpath(absFile, pOptions->files[i], MAXPATHLEN);
        }
        /* Format of an "open" commandment is one of:
         *    open\t<filename>\n
         *    open\t--selection=<selection>\t<filename>\n
         */
        if (pOptions->line && strchr(pOptions->line, ',') != NULL) {
            overflow = snprintf(commandment, MAX_COMMANDMENT_LEN,
                                "open\t--selection=%s\t%s\n",
                                insertUsePosition(pOptions->line,
                                                  pOptions->usePosition),
                                absFile);
        } else if (pOptions->line) {
            /* Ensure that line,col specification has the ",col" as
             * required by the "open" commandment -- presume the first
             * column (1).
             */
            overflow = snprintf(commandment, MAX_COMMANDMENT_LEN,
                                "open\t--selection=%s,1\t%s\n",
                                pOptions->line, absFile);
        } else if (pOptions->selection) {
            overflow = snprintf(commandment, MAX_COMMANDMENT_LEN,
                                "open\t--selection=%s\t%s\n",
                                insertUsePosition(pOptions->selection,
                                                  pOptions->usePosition),
                                absFile);
        } else {
            overflow = snprintf(commandment, MAX_COMMANDMENT_LEN,
                                "open\t%s\n", absFile);
        }
        if (overflow > MAX_COMMANDMENT_LEN || overflow < 0) {
            _LogError("buffer overflow while create open commandment "\
                      "for '%s'\n", absFile);
            exit(1);
        }
        rv = fprintf(commandmentsFile, "%s", commandment);
        if (rv != (int)strlen(commandment)) {
            _LogError("error writing commandment to '%s': [rv %d, errno %d] %s",
                      commandmentsFileName, rv, errno, strerror(errno));
            exit(1);
        }
        _LogDebug("issued commandment: %s", commandment);
    }

    if (fclose(commandmentsFile)) {
        _LogError("could not close '%s'\n", commandmentsFile);
        exit(1);
    }

#ifdef WIN32
    /* Signal Komodo that there are new commandments. */
    event = CreateEvent(NULL, TRUE, FALSE, commandmentsEventName);
    if (! event) {
        _LogError("could not create new commandments event: %d\n",
                  GetLastError());
        exit(1);
    }
    if (! SetEvent(event)) {
        _LogError("could not set new commandments event: %d\n",
                  GetLastError());
        exit(1);
    }
    if (! CloseHandle(event)) {
        _LogError("could not close new commandments handle: %d\n",
                  GetLastError());
        exit(1);
    }
    
    /* Release the lock. */
    if (! ReleaseMutex(lock)) {
        _LogError("error releasing commandments lock: %d\n", GetLastError());
        exit(1);
    }
    if (! CloseHandle(lock)) {
        _LogError("error closing lock handle: %d\n", GetLastError());
        exit(1);
    }
#endif
}


void KoStart_PrepareForXRE(int argc, char** argv,
                           int* pXreArgc, char*** pXreArgv)
{
    char* programDir = _GetProgramDir(argv[0]);
    /* static to cheaply avoid malloc/free (NOT re-entrant!) */
    static char* tmpArgv[MAX_XRE_ARGS];
    int tmpArgc = 0;
    int i;

    /* If this is re-start of the XRE (typical on first start after
     * XPCOM registration) then we've already prepared (saved startup
     * env, modified the env, and constructed the XRE argv).
     */
    if (xpgetenv("_KOMODO_VERUSERDATADIR") != NULL) {
        while (tmpArgc < argc) {
            tmpArgv[tmpArgc] = argv[tmpArgc];
            ++tmpArgc;
        }
    }

    else {
        _LogDebug("saving startup environment...\n");
        _KoStart_SaveStartupEnvironment();
        _LogDebug("setting up environment for XRE launch...\n");
        _KoStart_SetupEnvironment(programDir);

        /* If first arg is '--raw', then pass the subsequent arguments
         * directly through to the XRE.
         */
        if (argc > 1 && strcmp(argv[1], "--raw") == 0) {
            tmpArgv[tmpArgc++] = argv[0];
            for (i = 2; i < argc; ++i) {
                tmpArgv[tmpArgc++] = argv[i];
            }
        } else {
            tmpArgv[tmpArgc++] = argv[0];
#ifdef WIN32
            if (_KoStart_verbose) {
                /* Use -console XRE option to open a dos shell for
                 * stdout/stderr output.
                 */
                tmpArgv[tmpArgc++] = "-console";
            }
#endif
        }
    }

    _LogDebug("startup argv for XRE:\n");
    for (i = 0; i < tmpArgc; ++i) {
        _LogDebug("\targv[%d] = '%s'\n", i, tmpArgv[i]);
    }
    *pXreArgc = tmpArgc;
    *pXreArgv = tmpArgv;
}


