Patches for Komodo contrib (i.e. 3rd-party) code.

Two sets of patches here:
1. Those that are *already applied* to the sources in
   "contrib/<project>/...". This is most of them.
2. Those that are applied *as part of the build*. This
   includes:
   - contrib/patches/scintilla/...
     Handled by "bk build" (see GetScintillaSource() in Blackfile.py).

Currently the *building* of any of these source tree is handled by
"contrib/Conscript" -- with the exception of "contrib/scintilla".

