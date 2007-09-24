#!python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


#TODO: docstring

import sys
import os
from os.path import (join, dirname, exists, expanduser, splitext, basename,
                     split, abspath, isabs, isdir, isfile)
import cPickle as pickle
import threading
import time
import md5
import bisect
import fnmatch
from glob import glob
from pprint import pprint, pformat
import logging
from cStringIO import StringIO
import codecs
import copy
import weakref
import Queue

import ciElementTree as ET
from codeintel2.common import *
from codeintel2.buffer import Buffer
from codeintel2.util import dedent, safe_lang_from_lang, banner
from codeintel2.tree import tree_from_cix_path



#---- globals

log = logging.getLogger("codeintel.db")
#log.setLevel(logging.DEBUG)


#---- Resource classes
# For abstraction and canonicalization of paths.

class Resource(object):
    """A reference to a resource for the database.

    Typically this is just a path to a file on the local disk. However
    the intention is to also support remote file urls (TODO) and unsaved
    files (TODO).

    This class also provides canonicalization on comparison of resource
    paths.
    """
    
    def __init__(self, path):
        self.path = path

    @property
    def canon_path(self):
        # normalize os.altsep to os.sep? or even consider normalizing to
        # all '/'. This gets more complicated if have URL resources for
        # remote files: subclassing.
        XXX


class AreaResource(Resource):
    """A resource that is at a relative path under some area.

    For example, at 'template/Perl.pl' under 'the Komodo user data
    dir' or at 'catalog/baz.cix' under 'the codeintel2 package dir'.

    TODO: change ctor sig to AreaResource([area, ] path). More logical
    to have input be in same order as .area_path.
    """
    # The known path areas. We only have use for the one right now.
    _path_areas = {
        "ci-pkg-dir": dirname(dirname(abspath(__file__))),
    }
    _ordered_area_items = [(d,a) for a,d in _path_areas.items()]
    _ordered_area_items.sort(key=lambda i: len(i[0]), reverse=True)

    @classmethod
    def area_and_subpath_from_path(cls, path):
        #XXX Need to worry about canonicalization!
        for area_dir, area in cls._ordered_area_items:
            if (path.startswith(area_dir)
                # Ensure we are matching at a dir boundary. This implies
                # a limitation that there *is* a subpath. I'm fine with
                # that.
                and path[len(area_dir)] in (os.sep, os.altsep)):
                return area, path[len(area_dir)+1:]
        return None, path

    def __init__(self, path, area=None):
        """Create an area-relative resource.

            "path" is either the full path to the resource, or a
                relative path under the given area name. "area" must be
                specified for the latter.
            "area" (optional) can be given to specify under which area
                this resource resides. If not given, the best-fit of the
                known path areas will be used.
        """
        if area is not None:
            if area not in self._path_areas:
                raise ValueError("unknown path area: `%s'" % area)
            self.area = area
            if isabs(path):
                area_base = self._path_areas[area]
                if not path.startswith(area_base):
                    raise ValueError("cannot create AreaResource: `%s' is "
                                     "not under `%s' area (%s)" 
                                     % (path, area, area_base))
                self.subpath = path[len(area_base)+1:]
            else:
                self.subpath = path
        elif isinstance(path, tuple): # as per AreaResource.area_path
            self.area, self.subpath = path 
        else:
            self.area, self.subpath = self.area_and_subpath_from_path(path)

    def __str__(self):
        if self.area:
            return "[%s]%s%s" % (self.area, os.sep, self.subpath)
        else:
            return self.subpath

    def __repr__(self):
        return "AreaResource(%r, %r)" % (self.path, self.area)

    @property
    def area_path(self):
        return (self.area, self.subpath)

    @property
    def path(self):
        if self.area is None:
            return self.subpath
        else:
            return join(self._path_areas[self.area], self.subpath)


