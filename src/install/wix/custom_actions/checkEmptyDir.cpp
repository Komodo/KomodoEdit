#define UNICODE
#define _UNICODE

#include <windows.h>
#include <shlwapi.h>
#include <msi.h>
#include <msiquery.h>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "msi.lib")

void DisplayError(MSIHANDLE hInstall, LPCWSTR aMessage) {
    /* TODO */
    OutputDebugStringW(L"CheckEmptyDir: Error: ");
    OutputDebugStringW(aMessage);
    OutputDebugStringW(L"\n");

    UINT result;
    PMSIHANDLE record = MsiCreateRecord(1);
    if (!record) {
        return;
    }
    result = MsiRecordSetStringW(record, 0, L"[1]");
    if (result != ERROR_SUCCESS) {
        return;
    }
    result = MsiRecordSetStringW(record, 1, aMessage);
    if (result != ERROR_SUCCESS) {
        return;
    }
    MsiProcessMessage(hInstall, INSTALLMESSAGE_INFO, record);
};

// __cdecl removes name mangling and makes it easier to use from MSI
extern "C"
__declspec(dllexport)
UINT __cdecl CheckEmptyDir(MSIHANDLE hInstall);

UINT CheckEmptyDir(MSIHANDLE hInstall) {
    UINT result;
    DWORD length = 0;
    LPWSTR installDir = NULL;

    MsiSetPropertyW(hInstall, L"IsDirectoryEmpty", L"");
    
    result = MsiGetPropertyW(hInstall, L"INSTALLDIR", L"", &length);
    if (result != ERROR_MORE_DATA) {
        DisplayError(hInstall, L"Failed to get INSTALLDIR length");
        return ERROR_SUCCESS;
    }
    // Increment length for the terminating null; MSI actually gives back the
    // length without it, but expects the buffer length input to include it...
    ++length;
    installDir = (LPWSTR)malloc(sizeof(WCHAR) * length);
    if (!installDir) {
        DisplayError(hInstall, L"Cannot allocate installDir for INSTALLDIR");
        return ERROR_FUNCTION_NOT_CALLED;
    }
    result = MsiGetPropertyW(hInstall, L"INSTALLDIR", installDir, &length);
    if (result != ERROR_SUCCESS) {
        DisplayError(hInstall, L"Failed to get INSTALLDIR");
        return ERROR_SUCCESS;
    }
    OutputDebugStringW(L"Checking directory");
    OutputDebugStringW(installDir);

    if (!PathFileExistsW(installDir)) {
        OutputDebugStringW(L"... does not exist\n");
        // Allow installing into a non-existent path
        return MsiSetPropertyW(hInstall, L"IsDirectoryEmpty", L"1");
    }
    if (!PathIsDirectoryW(installDir)) {
        OutputDebugStringW(L"... is not a directory\n");
        // No good; we can't install into a file.
        return ERROR_SUCCESS;
    }
    if (!PathIsDirectoryEmptyW(installDir)) {
        OutputDebugStringW(L"... is not an empty directory\n");
        return ERROR_SUCCESS;
    }
    OutputDebugStringW(L"... is an empty directory");
    // We allow installing into an empty directory
    return MsiSetPropertyW(hInstall, L"IsDirectoryEmpty", L"1");
}
