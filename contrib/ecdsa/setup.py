#!/usr/bin/env python
import os, subprocess, re
from distutils.core import setup, Command
from distutils.command.sdist import sdist as _sdist
from ecdsa.six import print_

class Test(Command):
    description = "run unit tests"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        from ecdsa import numbertheory
        numbertheory.__main__()
        from ecdsa import ellipticcurve
        ellipticcurve.__main__()
        from ecdsa import ecdsa
        ecdsa.__main__()
        from ecdsa import test_pyecdsa
        test_pyecdsa.unittest.main(module=test_pyecdsa, argv=["dummy"])
        # all tests os.exit(1) upon failure

VERSION_PY = """
# This file is originally generated from Git information by running 'setup.py
# version'. Distribution tarballs contain a pre-generated copy of this file.

__version__ = '%s'
"""

def update_version_py():
    if not os.path.isdir(".git"):
        print_("This does not appear to be a Git repository.")
        return
    try:
        p = subprocess.Popen(["git", "describe",
                              "--tags", "--dirty", "--always"],
                             stdout=subprocess.PIPE)
    except EnvironmentError:
        print_("unable to run git, leaving ecdsa/_version.py alone")
        return
    stdout = p.communicate()[0]
    if p.returncode != 0:
        print_("unable to run git, leaving ecdsa/_version.py alone")
        return
    # we use tags like "python-ecdsa-0.5", so strip the prefix
    assert stdout.startswith("python-ecdsa-")
    ver = stdout[len("python-ecdsa-"):].strip()
    f = open("ecdsa/_version.py", "w")
    f.write(VERSION_PY % ver)
    f.close()
    print_("set ecdsa/_version.py to '%s'" % ver)

def get_version():
    try:
        f = open("ecdsa/_version.py")
    except EnvironmentError:
        return None
    for line in f.readlines():
        mo = re.match("__version__ = '([^']+)'", line)
        if mo:
            ver = mo.group(1)
            return ver
    return None

class Version(Command):
    description = "update _version.py from Git repo"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        update_version_py()
        print_("Version is now", get_version())

class sdist(_sdist):
    def run(self):
        update_version_py()
        # unless we update this, the sdist command will keep using the old
        # version
        self.distribution.metadata.version = get_version()
        return _sdist.run(self)

setup(name="ecdsa",
      version=get_version(),
      description="ECDSA cryptographic signature library (pure python)",
      author="Brian Warner",
      author_email="warner-pyecdsa@lothar.com",
      url="http://github.com/warner/python-ecdsa",
      packages=["ecdsa"],
      license="MIT",
      cmdclass={ "test": Test, "version": Version, "sdist": sdist },
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
      ],
)
