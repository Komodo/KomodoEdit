#!/usr/bin/env python

import io
import os

from setuptools import setup
import versioneer

commands = versioneer.get_cmdclass().copy()

# Use README.md to set markdown long_description
directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(directory, "README.md")
with io.open(readme_path, encoding="utf-8") as read_file:
    long_description = read_file.read()

setup(
    name="ecdsa",
    version=versioneer.get_version(),
    description="ECDSA cryptographic signature library (pure python)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Brian Warner",
    author_email="warner@lothar.com",
    url="http://github.com/tlsfuzzer/python-ecdsa",
    packages=["ecdsa"],
    package_dir={"": "src"},
    license="MIT",
    cmdclass=commands,
    python_requires=">=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, "
    "!=3.5.*",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    install_requires=["six>=1.9.0"],
    extras_require={"gmpy2": "gmpy2", "gmpy": "gmpy"},
)
