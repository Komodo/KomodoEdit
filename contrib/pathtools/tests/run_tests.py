#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys
import nose

def absolute_path(path):
    return os.path.abspath(os.path.normpath(path))

dir_path = absolute_path(os.path.dirname(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path[0:0] = [parent_dir_path]

# Explicitly define which packages/modules to cover.
cover_packages = [
    'pathtools',
]

if __name__ == "__main__":
    config_path = os.path.join(parent_dir_path, 'nose.cfg')

    argv = [__file__]
    argv.append('--detailed-errors')
    argv.append('--with-coverage')
    # Coverage by itself generates more usable reports.
    #argv.append('--cover-erase')
    #argv.append('--cover-html')
    argv.append('--cover-package=%s' % ','.join(cover_packages))
    argv.append('--config=%s' % config_path)
    nose.run(argv=argv)
