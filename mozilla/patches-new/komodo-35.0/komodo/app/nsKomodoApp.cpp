/* -*- Mode: C++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

/* This is a placeholder for the real nsKomodoApp.cpp code (dropped in as part
 * of the *Komodo* build).
 */

#include <stdio.h>

#ifdef XP_WIN
#include <windows.h>
#include <stdlib.h>
// we want a wmain entry point
#include "nsWindowsWMain.cpp"
#endif

int main(int argc, char* argv[])
{
  fprintf(stderr, "This is just a place holder - go finish building Komodo\n");
  return 255;
}

#if defined( XP_WIN ) && defined( WIN32 ) && !defined(__GNUC__)
// We need WinMain in order to not be a console app.  This function is
// unused if we are a console application.
int WINAPI WinMain( HINSTANCE, HINSTANCE, LPSTR args, int )
{
    // Do the real work.
    return main( __argc, __argv );
}
#endif
