README for Mozilla-devel/prebuilt
=================================

This tree holds prebuilt binaries for the following parts of our Mozilla
builds:

- Python 2.5 (python2.5/$build_name.zip)

  We silo Python in our Mozilla builds (e.g. those for Komodo).
  Here is how you update these builds (or add a new platform):

    p4 sync ActivePython-devel/...
    cd ActivePython-devel
    python configure.py -p komodosilo  # use 'komodosilo' build profile
    python Makefile.py distclean all image_embedding update_mozilla_prebuilt

  Trent uses the 'bin/rrun.py mozpy' task to do this.

