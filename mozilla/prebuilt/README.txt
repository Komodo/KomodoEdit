README for Mozilla-devel/prebuilt
=================================

This tree holds prebuilt binaries for the following parts of our Mozilla
builds:

- Python 2.5 (python2.5/$build_name/...)

  We silo Python in our Mozilla builds (e.g. those for Komodo).
  Here is how you update these builds (or add a new platform):

    p4 sync Mozilla-devel/...
    p4 sync ActivePython-devel/...
    cd ActivePython-devel
    python configure.py -p embedding25  # use 'embedding25' build profile
    python Makefile.py all image_embedding update_mozilla_prebuilt

  Note: An older (2.4) Python build is under "$plat/release/python/...".

