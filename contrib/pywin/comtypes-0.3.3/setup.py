r"""comtypes - pure Python COM package, based on the ctypes FFI library.

comtypes allows to define, call, and implement custom COM interfaces
in pure Python.

http://svn.python.org/projects/ctypes/trunk/comtypes/#egg=comtypes-dev

----------------------------------------------------------------"""
import comtypes

import sys, os
from distutils.core import setup, Command, DistutilsOptionError

class test(Command):
    # Original version of this class posted
    # by Berthold Hoellmann to distutils-sig@python.org
    description = "run tests"

    user_options = [
        ('tests=', 't',
         "comma-separated list of packages that contain test modules"),
        ('use-resources=', 'u',
         "resources to use - resource names are defined by tests"),
        ('refcounts', 'r',
         "repeat tests to search for refcount leaks (requires 'sys.gettotalrefcount')"),
        ]

    boolean_options = ["refcounts"]

    def initialize_options(self):
        self.build_base = 'build'
        self.use_resources = ""
        self.refcounts = False
        self.tests = "comtypes.test"

    # initialize_options()

    def finalize_options(self):
        if self.refcounts and not hasattr(sys, "gettotalrefcount"):
            raise DistutilsOptionError("refcount option requires Python debug build")
        self.tests = self.tests.split(",")
        self.use_resources = self.use_resources.split(",")

    # finalize_options()

    def run(self):
        self.run_command('build')

        import comtypes.test
        comtypes.test.use_resources.extend(self.use_resources)

        for name in self.tests:
            package = __import__(name, globals(), locals(), ['*'])
            print "Testing package", name, (sys.version, sys.platform, os.name)
            comtypes.test.run_tests(package,
                                    "test_*.py",
                                    self.verbose,
                                    self.refcounts)

    # run()

# class test

classifiers = [
##    'Development Status :: 3 - Alpha',
    'Development Status :: 4 - Beta',
##    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: Microsoft :: Windows CE',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    ]

setup(name="comtypes",
      description="Pure Python COM package, based on the ctypes package",
      long_description = __doc__,
      author="Thomas Heller",
      author_email="theller@python.net",
      url="http://starship.python.net/crew/wiki/the_comtypes_package",
      download_url = "http://sourceforge.net/project/showfiles.php?group_id=115265",

      license="MIT License",
      package_data = {"comtypes.test": ["TestComServer.idl",
                                        "TestComServer.tlb"]},

      classifiers=classifiers,

      cmdclass = {'test': test},
      
      version=comtypes.__version__,
      packages=["comtypes",
                "comtypes.client",
                "comtypes.server",
                "comtypes.tools",
                "comtypes.test"])
