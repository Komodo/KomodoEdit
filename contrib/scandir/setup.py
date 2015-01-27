"""Run "python setup.py install" to install scandir."""

from distutils.core import setup, Extension
import os
import re

# Get version without importing scandir because that will lock the
# .pyd file (if scandir is already installed) so it can't be
# overwritten during the install process
with open(os.path.join(os.path.dirname(__file__), 'scandir.py')) as f:
    for line in f:
        match = re.match(r"__version__.*'([0-9.]+)'", line)
        if match:
            version = match.group(1)
            break
    else:
        raise Exception("Couldn't find version in setup.py")

setup(
    name='scandir',
    version=version,
    author='Ben Hoyt',
    author_email='benhoyt@gmail.com',
    url='https://github.com/benhoyt/scandir',
    license='New BSD License',
    description='scandir, a better directory iterator that returns all file info the OS provides',
    long_description="scandir is a generator version of os.listdir() that returns an iterator over "
                     "files in a directory, and also exposes the extra information most OSes provide "
                     "while iterating files in a directory. Read more at the GitHub project page.",
    py_modules=['scandir'],
    ext_modules=[Extension('_scandir', ['_scandir.c'])],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: System :: Filesystems',
        'Topic :: System :: Operating System',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
    ]
)
