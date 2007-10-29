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

/* Black console launch executable.  
 * 
 * This program exists solely to launch "python <installdir>/bk.py <argv>" on
 * Windows. "bk.py" must be in the same directory.
 *
 * Rationale:
 *    - On some Windows flavours .py *can* be put on the PATHEXT to be able
 *      to find "bk.py" if it is on the PATH. This is fine until you need
 *      shell redirection to work. It does NOT for extensions to PATHEXT.
 *      Rediection *does* work for "python <script>.py" so we will try to do
 *      that.
 */

#ifdef WIN32
	#include <windows.h>
	#include <process.h>
	#include <direct.h>
	#include <shlwapi.h>
#else /* linux */
	#include <unistd.h>
#endif /* WIN32 */
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

//---- constants

#define BUF_LENGTH 2048
#define MAX_PYTHON_ARGS 50
#define MAX_FILES 50
#define MAXPATHLEN 1024
#ifdef WIN32
	#define SEP '\\'
	#define ALTSEP '/'
    // path list element separator
    #define DELIM ';'
#else /* linux */
	#define SEP '/'
    // path list element separator
    #define DELIM ':'
#endif

#ifdef WIN32
    #define spawnvp _spawnvp
    #define snprintf _snprintf
    #define vsnprintf _vsnprintf
    //NOTE: this is for the stat *call* and the stat *struct*
    #define stat _stat
#endif


//---- globals

char* programName = NULL;
char* programPath = NULL;
#ifndef WIN32 /* i.e. linux */
    extern char **environ;   // the user environment
#endif /* linux */

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



//---- utilities functions



/* _IsDir: Is the given dirname an existing directory */
static int _IsDir(char *dirname)
{
#ifdef WIN32
    DWORD dwAttrib;
    dwAttrib = GetFileAttributes(dirname);
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


/* Is executable file
 * On Linux: check 'x' permission. On Windows: just check existence.
 */
static int _IsExecutableFile(char *filename)
{
#ifdef WIN32
    return (int)PathFileExists(filename);
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


/* _GetProgramPath: Determine the absolute path to the given program name.
 *
 *	Takes into account the current working directory, etc.
 *	The implementations require the global 'programName' to be set.
 */
#ifdef WIN32
	static char* _GetProgramPath(void)
	{
        //XXX this is ugly but I didn't want to use malloc, no reason
		static char progPath[MAXPATHLEN+1];
		// get absolute path to module
		if (!GetModuleFileName(NULL, progPath, MAXPATHLEN)) {
			_LogError("could not get absolute program name from "\
                "GetModuleFileName\n");
			exit(1);
		}
		// just need dirname
		for (char* p = progPath+strlen(progPath);
			 *p != SEP && *p != ALTSEP;
			 --p)
		{
			*p = '\0';
		}
		*p = '\0';  // remove the trailing SEP as well

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


	static char*
	_GetProgramPath(void)
	{
        /* XXX this routine does *no* error checking */
		char* path = getenv("PATH");
		static char progPath[MAXPATHLEN+1];

		/* If there is no slash in the argv0 path, then we have to
		 * assume the program is on the user's $PATH, since there's no
		 * other way to find a directory to start the search from.  If
		 * $PATH isn't exported, you lose.
		 */
		if (strchr(programName, SEP)) {
			strncpy(progPath, programName, MAXPATHLEN);
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

				_JoinPath(progPath, programName);
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
		char* pLetter = progPath + strlen(progPath);
		for (;pLetter != progPath && *pLetter != SEP; --pLetter) {
			/* do nothing */
		}
		*pLetter = '\0';

		return progPath;
	}
#endif  /* WIN32 */


//---- mainline

int main(int argc, char** argv)
{
    programName = argv[0];
    programPath = _GetProgramPath();
    int i;

    // determine the full path to "bk.py"
    char bkPy[MAXPATHLEN+1];
    snprintf(bkPy, MAXPATHLEN, "%s%cbk.py", programPath, SEP);
    
    // build the argument array for launching bk.py
    char* pythonArgs[MAX_PYTHON_ARGS+1];
    int nPythonArgs = 0;
    pythonArgs[nPythonArgs++] = "python";
    pythonArgs[nPythonArgs++] = bkPy;
    for (i = 1; i < argc; ++i) {
        pythonArgs[nPythonArgs++] = argv[i];
    }
    pythonArgs[nPythonArgs] = NULL;

    // quote each of the arguments, except the app name (to ensure that
    // spaces within arguments do not result is separate arguments)
    for (i = 1; i < nPythonArgs; ++i) {
        char* unquoted = pythonArgs[i];
        pythonArgs[i] = (char *) malloc((strlen(unquoted)+3) * sizeof(char));
        *(pythonArgs[i]) = '\0';
        strcat(pythonArgs[i], "\"");
        strcat(pythonArgs[i], unquoted);
        strcat(pythonArgs[i], "\"");
    }

    // run bk.py
    int retval = _spawnvp(_P_WAIT, pythonArgs[0], pythonArgs);
    
    // free allocated memory
    for (i=1; i < nPythonArgs; ++i) {
        free(pythonArgs[i]);
    }
    
    return retval;
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

