from distutils.core import setup

import six

six_classifiers = [
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

fp = open("README", "r")
try:
    six_long_description = fp.read()
finally:
    fp.close()


setup(name="six",
      version=six.__version__,
      author="Benjamin Peterson",
      author_email="benjamin@python.org",
      url="http://pypi.python.org/pypi/six/",
      py_modules=["six"],
      description="Python 2 and 3 compatibility utilities",
      long_description=six_long_description,
      classifiers=six_classifiers
      )
