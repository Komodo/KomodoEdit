/* Copyright (c) 2000-2007 ActiveState Software Inc.
 * See the file LICENSE.txt for licensing information.
 *
 * Recursively remove the given directory... as best as possible. Failure
 * to remove particular files/directories in the tree (possible if those
 * files are open by another process) are skipped.
 *
 * Note: This is Windows-only.
 *
 * TODO: just warn about failure to remove a particular file
 */

#include <stdio.h>
#include <io.h>
#include <sys/stat.h>
#include <errno.h>
#include <windows.h>

#define snprintf _snprintf



/* ---- internal logging stuff ---- */

#if !defined(NO_STDARG)
#   include <stdarg.h>
#   define LOG_VARARGS(type, name) (type name, ...)
#   define LOG_VARARGS_DEF(type, name) (type name, ...)
#   define LOG_VARARGS_START(type, name, list) (va_start(list, name), name)
#else
#   include <varargs.h>
#   define LOG_VARARGS(type, name) ()
#   define LOG_VARARGS_DEF(type, name) (va_alist)
#   define LOG_VARARGS_START(type, name, list) (va_start(list), va_arg(list, type))
#endif

#define LOG_ENABLED 0
#define LOG_NAME "rmtree"
#define LOG_TO_FILE 1
#define LOG_FILE "C:\\the.log"

static void log_error LOG_VARARGS_DEF(const char *, format)
{
#if LOG_ENABLED
    va_list ap;
    FILE* fout;
    LOG_VARARGS_START(const char *, format, ap);
#if LOG_TO_FILE
    fout = fopen(LOG_FILE, "a");
    fprintf(fout, LOG_NAME ": error: ");
    vfprintf(fout, format, ap);
    fprintf(fout, "\n");
    fclose(fout);
#else
    fprintf(stderr, LOG_NAME ": error: ");
    vfprintf(stderr, format, ap);
    fprintf(stderr, "\n");
#endif
    va_end(ap);
#endif
}

static void log_warn LOG_VARARGS_DEF(const char *, format)
{
#if LOG_ENABLED
    va_list ap;
    FILE* fout;
    LOG_VARARGS_START(const char *, format, ap);
#if LOG_TO_FILE
    fout = fopen(LOG_FILE, "a");
    fprintf(fout, LOG_NAME ": warn: ");
    vfprintf(fout, format, ap);
    fprintf(fout, "\n");
    fclose(fout);
#else
    fprintf(stderr, LOG_NAME ": warn: ");
    vfprintf(stderr, format, ap);
    fprintf(stderr, "\n");
#endif
    va_end(ap);
#endif
}

static void log_info LOG_VARARGS_DEF(const char *, format)
{
#if LOG_ENABLED
    va_list ap;
    FILE* fout;
    LOG_VARARGS_START(const char *, format, ap);
#if LOG_TO_FILE
    fout = fopen(LOG_FILE, "a");
    fprintf(fout, LOG_NAME ": ");
    vfprintf(fout, format, ap);
    fprintf(fout, "\n");
    fclose(fout);
#else
    fprintf(stderr, LOG_NAME ": ");
    vfprintf(stderr, format, ap);
    fprintf(stderr, "\n");
#endif
    va_end(ap);
#endif
}



/* Recursively remove all files in the given dir.
 *
 * This continues removing files after an error removing one.
 * Does not support wide characters.
 * Returns 0 if successful, non-zero otherwise. 
 */
static int rmtree(char* dir)
{
    size_t overflow;
    char dir_pat[MAX_PATH+1];
    char file_path[MAX_PATH+1];
    WIN32_FIND_DATA find_file_data;
    HANDLE h_find;
    DWORD error;
    int len, rv, retval = 0;

    //log_info("rmtree '%s'", dir);

    //TODO: Remove this or add it if needed.
    //len = strlen(dir);
    //if (len && dir[len-1] == '\\') {
    //    overflow = snprintf(dir_pat, MAX_PATH, "%s*", dir);
    //} else {
    //    overflow = snprintf(dir_pat, MAX_PATH, "%s\\*", dir);
    //}
    overflow = snprintf(dir_pat, MAX_PATH, "%s\\*", dir);
    if (overflow > MAX_PATH || overflow < 0) {
        log_error("path too long: '%s'", dir);
        return 1;
    }

    h_find = FindFirstFile(dir_pat, &find_file_data);
    if (h_find == INVALID_HANDLE_VALUE) 
    {
        log_error("invalid file handle (%d): '%s'",
                  GetLastError(), dir_pat);
        return 1;
    }

    do {
        // Skip '.' and '..' entries.
        if (strcmp(find_file_data.cFileName, ".") == 0
            || strcmp(find_file_data.cFileName, "..") == 0)
        {
            continue;
        }

        // Get the full path.
        overflow = snprintf(file_path, MAX_PATH, "%s\\%s", dir,
                            find_file_data.cFileName);
        if (overflow > MAX_PATH || overflow < 0) {
            log_error("path too long: '%s\\%s'",
                      dir, find_file_data.cFileName);
            return 1;
        }
    
        if (find_file_data.dwFileAttributes == FILE_ATTRIBUTE_DIRECTORY) {
            if ((rv = rmtree(file_path)) != 0)
                retval = rv;
        } else {
            if ((rv = _remove_file(file_path)) != 0)
                retval = rv;
        }

    } while (FindNextFile(h_find, &find_file_data) != 0);
    error = GetLastError();
    FindClose(h_find);
    if (error != ERROR_NO_MORE_FILES) {
       log_error("FindNextFile returned %u\n", error);
       return 1;
    }

    if (!retval)
        retval = _remove_dir(dir);
    return retval;
}



/* ---- internal support stuff ---- */

static void _ensure_write_perms(char *path)
{
  (void) _chmod(path, _S_IREAD | _S_IWRITE);
}


/* Remove the given file path.
 * Returns 0 on success, non-zero (and logs a warning) otherwise. */
static int _remove_file(char* path)
{
    int rv;
    //log_info("rm %s", path);
    _ensure_write_perms(path);
    rv = remove(path);
    if (rv) {
        log_warn("%s (%d): %s", strerror(errno), errno, path);
    }
    return rv;
}

/* Remove the given dir path.
 * Returns 0 on success, non-zero (and logs a warning) otherwise. */
static int _remove_dir(char* path)
{
    int rv;
    //log_info("rm %s", path);
    rv = _rmdir(path);
    if (rv) {
        log_warn("%s (%d): %s", strerror(errno), errno, path);
    }
    return rv;
}


/* ---- mainline ---- */

int main(int argc, char* argv[])
{
    if (argc != 2) {
        printf("usage: rmtree DIR\n");
        return 1;
    }

    return rmtree(argv[1]);
}


int WINAPI WinMain(
    HINSTANCE hInstance,      /* handle to current instance */
    HINSTANCE hPrevInstance,  /* handle to previous instance */
    LPSTR lpCmdLine,          /* pointer to command line */
    int nCmdShow              /* show state of window */
    )
{
    return main(__argc, __argv);
}


