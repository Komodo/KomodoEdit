/* Windows-subsystem simple version of start.
 * 
 * This program allows a file to be started (1) using the local system's
 * file associations and (2) without popping up a console (as the
 * standard "start" would do).
 *
 * Algorithm:
 * - run ShellExecuteEx on argv[1:]
 *
 * Limitations:
 * - The current directory is always used.
 */

#include <stdio.h>
#include <windows.h>

#ifdef WIN32
    #define snprintf _snprintf
    #define vsnprintf _vsnprintf
#endif


//---- constants

#define BUF_LENGTH 2048



//---- globals

char* programName = NULL;



//---- error logging functions

void _LogError(const char* format ...)
{
    va_list ap;
    va_start(ap, format);
#if defined(WIN32) && defined(_WINDOWS)
    // put up a MessageBox
    char caption[BUF_LENGTH+1];
    snprintf(caption, BUF_LENGTH, "Error in %s", programName);
    char msg[BUF_LENGTH+1];
    vsnprintf(msg, BUF_LENGTH, format, ap);
    va_end(ap);
    MessageBox(NULL, msg, caption, MB_OK | MB_ICONEXCLAMATION);
#else
    fprintf(stderr, "%s: error: ", programName);
    vfprintf(stderr, format, ap);
    va_end(ap);
#endif /* WIN32 && _WINDOWS */
}


void _LogWarning(const char* format ...)
{
    va_list ap;
    va_start(ap, format);
#if defined(WIN32) && defined(_WINDOWS)
    // put up a MessageBox
    char caption[BUF_LENGTH+1];
    snprintf(caption, BUF_LENGTH, "Warning in %s", programName);
    char msg[BUF_LENGTH+1];
    vsnprintf(msg, BUF_LENGTH, format, ap);
    va_end(ap);
    MessageBox(NULL, msg, caption, MB_OK | MB_ICONWARNING);
#else
    fprintf(stderr, "%s: warning: ", programName);
    vfprintf(stderr, format, ap);
    va_end(ap);
#endif /* WIN32 && _WINDOWS */
}



//---- mainline

int main(int argc, char** argv)
{
    // Setup globals.
    programName = argv[0];

    if (argc < 2) {
        _LogError("You must pass an argument to startw.exe telling it what file to start.\nUsage: startw <filename> [<args>...]");
        return 1;
    }

    // Parse argv.
    char* file = argv[1];
    char params[BUF_LENGTH];
    params[0] = '\0';
    for (int i = 2; i < argc; ++i) {
        strncat(params, argv[i], BUF_LENGTH-strlen(params));
        strncat(params, " ", BUF_LENGTH-strlen(params));
    }

    // Call ShellExecuteEx with the given arguments.
    SHELLEXECUTEINFO execInfo;
    memset(&execInfo, 0, sizeof(execInfo));
    execInfo.cbSize = sizeof(execInfo);
    execInfo.fMask = NULL;
    execInfo.lpVerb = NULL;
    execInfo.lpFile = file;
    execInfo.lpParameters = params;
    //execInfo.lpDirectory = XXX necessary for what I want?
    execInfo.nShow = SW_SHOW;
    int success = ShellExecuteEx(&execInfo);

    if (!success) {
        _LogError("ShellExecuteEx failed: %d, %d",
                  (int)execInfo.hInstApp, GetLastError());
        return 1;
    }
    return 0;
}


//---- mainline for win32 subsystem:windows app
#ifdef WIN32
    int WINAPI WinMain(
        HINSTANCE hInstance,      /* handle to current instance */
        HINSTANCE hPrevInstance,  /* handle to previous instance */
        LPSTR lpCmdLine,          /* pointer to command line */
        int nCmdShow              /* show state of window */
    )
    {
        return main(__argc, __argv);
    }
#endif

