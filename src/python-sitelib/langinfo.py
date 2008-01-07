#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.

r"""Database of static info for (text) languages (e.g. Python, Perl, ...).

Basic usage:

    >>> import langinfo
    >>> py = langinfo.langinfo_from_lang("Python")
    >>> py.name
    'Python'
    >>> py.exts
    ['.py', '.pyw']
    >>> py.is_text
    True
    
Advanced usage:

    >>> lidb = langinfo.Database()
    >>> py = lidb.langinfo_from_lang("Python")
    >>> py.name
    'Python'

The advanced usage allows one to customize how the langinfo database is
built. For example, specified 'dirs' will be searched for
'langinfo_*.py' files that can add to the database. (This can be used to
allow Komodo extensions to add/override language info.)
"""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, dirname, abspath, basename, exists
import sys
import re
from pprint import pprint
from glob import glob
import traceback
import logging
import optparse
import types
import struct
import warnings



#---- exceptions and warnings

class LangInfoError(Exception):
    pass

class InvalidLangInfoWarning(Warning):
    pass
warnings.simplefilter("once", InvalidLangInfoWarning)


#---- globals

log = logging.getLogger("langinfo")



#---- module API

def langinfo_from_lang(lang):
    return _get_default_database().langinfo_from_lang(lang)



#---- base LangInfo definition

class LangInfo(object):
    """Base language info class. A subclass of LangInfo defines static
    information about a particular text language (e.g. Python, Perl,
    CSS, ...).

    The following are the "core" attributes for a LangInfo. Subclasses
    can feel free to define others, as makes sense for that language.
    """
    name = None     # a display name (i.e. appropriate for prose, display)
    #TODO: add a 'desc' field

    # Used for identifying files of this language.
    exts = None
    filename_patterns = None
    magic_numbers = None

    # Some languages mandate a default encoding, e.g. for Python it is
    # ASCII, for XML UTF-8.
    default_encoding = None
    encoding_decl_pattern = None  # Regex matching an encoding declaration.

    # A set of lang names to which this language conforms. For example,
    # RDF conforms to XML. See `conforms_to()` below.
    #
    # This is based on the UTI (Uniform Type Identifier) conforms-to
    # idea from Mac OS X:
    #   http://arstechnica.com/reviews/os/macosx-10-4.ars/11
    #   http://developer.apple.com/macosx/uniformtypeidentifiers.html
    #   http://developer.apple.com/documentation/Carbon/Conceptual/understanding_utis/understand_utis_intro/chapter_1_section_1.html
    conforms_to_bases = None

    def __init__(self, db):
        self._db = db

    def __repr__(self):
        return "<%s LangInfo>" % self.name

    @property
    def is_text(self):
        """Convenience property to check if this lang is plain text."""
        return self.conforms_to("Text")

    def conforms_to(self, lang):
        """Returns True iff this language conforms to the given `lang`."""
        if lang == self.name:
            return True
        if self.conforms_to_bases:
            if lang in self.conforms_to_bases:
                return True
            for base in self.conforms_to_bases:
                try:
                    base_li = self._db.langinfo_from_lang(base)
                except LangInfoError:
                    pass
                else:
                    if base_li.conforms_to(lang):
                        return True
        return False

    def conformant_attr(self, attr):
        """Returns the value of the given attr, inheriting from the
        `conforms_to_bases` languages if not directly defined for this
        language.
        """
        if hasattr(self, attr):
            val = getattr(self, attr)
            if val is not None:
                return val
        for base in self.conforms_to_bases or []:
            try:
                base_li = self._db.langinfo_from_lang(base)
            except LangInfoError:
                pass
            else:
                val = base_li.conformant_attr(attr)
                if val is not None:
                    return val
        return None
        


#---- LangInfo classes (most are defined in separate langinfo_*.py files)

class TextLangInfo(LangInfo):
    name = "Text"
    exts = ['.txt', '.text']
    filename_patterns = ["README", "COPYING", "LICENSE", "MANIFEST"]



#---- the Database

class Database(object):
    def __init__(self, dirs=None):
        self._langinfo_from_norm_lang = {}
        self._langinfo_from_ext = None
        self._langinfo_from_filename = None
        self._langinfo_from_filename_re = None
        self._magic_table = None

        self._load()
        if dirs is None:
            dirs = []
        dirs.insert(0, dirname(__file__) or os.curdir)
        for dir in dirs:
            self._load_dir(dir)

    def langinfos(self):
        for li in self._langinfo_from_norm_lang.values():
            yield li

    def langinfo_from_lang(self, lang):
        norm_lang = self._norm_lang_from_lang(lang)
        if norm_lang not in self._langinfo_from_norm_lang:
            raise LangInfoError("no info on %r lang" % lang)
        return self._langinfo_from_norm_lang[norm_lang]

    def langinfo_from_ext(self, ext):
        """Return an appropriate LangInfo for the given filename extension, 
        or None.
        """
        if self._langinfo_from_ext is None:
            self._build_tables()
        if sys.platform in ("win32", "darwin"): # Case-insensitive filesystems.
            ext = ext.lower()
        return self._langinfo_from_ext.get(ext)

    def langinfo_from_filename(self, filename):
        """Return an appropriate LangInfo for the given filename, or None."""
        if self._langinfo_from_filename is None:
            self._build_tables()
        if filename in self._langinfo_from_filename:
            return self._langinfo_from_filename[filename]
        else:
            for regex, li in self._langinfo_from_filename_re.items():
                if regex.search(filename):
                    return li

    def langinfo_from_magic(self, head_bytes):
        if self._magic_table is None:
            self._build_tables()

        for magic_number, li in self._magic_table:
            start, format, pattern = magic_number
            if format == "string":
                end = start + len(pattern)
                if head_bytes[start:end] == pattern:
                    return li
            elif format == "regex":
                if pattern.search(head_bytes, start):
                    return li
            else:  # a struct format
                try:
                    length = struct.calcsize(format)
                except struct.error, ex:
                    warnings.warn("error in %s magic number struct format: %r"
                                      % (li, format),
                                  InvalidLangInfoWarning)
                end = start + length
                bytes = head_bytes[start:end]
                if len(bytes) == length:
                    if struct.unpack(format, bytes)[0] == pattern:
                        return li

    def _build_tables(self):
        self._langinfo_from_ext = {}
        self._langinfo_from_filename = {}
        self._langinfo_from_filename_re = {}
        self._magic_table = []  # list of (<magic-tuple>, <langinfo>)

        for li in self._langinfo_from_norm_lang.values():
            if li.exts:
                for ext in li.exts:
                    if not ext.startswith('.'):
                        log.warn("exts must start with '.': ext %r for "
                                 "lang %r", ext, li.name)
                    if sys.platform in ("win32", "darwin"):
                        ext = ext.lower()
                    if ext in self._langinfo_from_ext:
                        log.debug("ext conflict: %r for %r conflicts "
                                  "with the same for %r (%r wins)", ext, li,
                                  self._langinfo_from_ext[ext], li)
                    self._langinfo_from_ext[ext] = li
            if li.filename_patterns:
                for pat in li.filename_patterns:
                    if isinstance(pat, basestring):
                        self._langinfo_from_filename[pat] = li
                    else:
                        self._langinfo_from_filename_re[pat] = li
            if li.magic_numbers:
                for mn in li.magic_numbers:
                    self._magic_table.append((mn, li))

    def _norm_lang_from_lang(self, lang):
        return lang.lower()

    def _load(self):
        """Load LangInfo classes in this module."""
        for name, g in globals().items():
            if isinstance(g, (types.ClassType, types.TypeType)) \
               and issubclass(g, LangInfo) and g is not LangInfo:
                norm_lang = self._norm_lang_from_lang(g.name)
                self._langinfo_from_norm_lang[norm_lang] = g(self)

    def _load_dir(self, d):
        """Load LangInfo classes in langinfo_*.py modules in this dir."""
        for path in glob(join(d, "langinfo_*.py")):
            try:
                module = _module_from_path(path)
            except Exception, ex:
                log.warn("could not import `%s': %s", path, ex)
                continue
            for name in dir(module):
                attr = getattr(module, name)
                if isinstance(attr, (types.ClassType, types.TypeType)) \
                   and issubclass(attr, LangInfo) and attr is not LangInfo:
                    norm_lang = self._norm_lang_from_lang(attr.name)
                    self._langinfo_from_norm_lang[norm_lang] = attr(self)


#---- internal support stuff

_g_default_database = None
def _get_default_database():
    global _g_default_database
    if _g_default_database is None:
        _g_default_database = Database()
    return _g_default_database

# Recipe: module_from_path (1.0.1+)
def _module_from_path(path):
    import imp, os
    dir = os.path.dirname(path) or os.curdir
    name = os.path.splitext(os.path.basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)



#---- self-test

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
    

