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

