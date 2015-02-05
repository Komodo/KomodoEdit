import os
from os.path import basename, exists, isdir, join, splitext
import logging

from zope.cachedescriptors.property import LazyClassAttribute

from xpcom import components

log = logging.getLogger('SchemeBase')
#log.setLevel(logging.DEBUG)

class SchemeBase(object):

    ext = ''

    @LazyClassAttribute
    def _koDirSvc(self):
        return components.classes["@activestate.com/koDirs;1"].\
                        getService(components.interfaces.koIDirs)
    @LazyClassAttribute
    def _userSchemeDir(self):
        return join(self._koDirSvc.userDataDir, 'schemes')

    def __init__(self, fname, userDefined, unsaved=0):
        self.unsaved = unsaved
        self.writeable = userDefined
        if unsaved:
            self.fname = join(self._userSchemeDir, fname + self.ext)
            self.name = fname
            self.data = ''
            self.isDirty = 1
        else:
            self.fname = fname
            self.name = splitext(basename(fname))[0]
            self.isDirty = 0

    def revert(self):
        self.isDirty = 0

class SchemeServiceBase(object):

    ext = ''

    def __init__(self):
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                        getService(components.interfaces.koIDirs)
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs
        self._systemSchemeDir = join(self._koDirSvc.supportDir, 'schemes')
        self._userSchemeDir = join(self._koDirSvc.userDataDir, 'schemes')
        self._schemes = {}

        self.reloadAvailableSchemes()

    def _addSchemeDetailsFromDirectory(self, dirName, userDefined):
        for candidate in os.listdir(dirName):
            name, ext = splitext(candidate)
            if ext == self.ext:
                filepath = join(dirName, candidate)
                self._scheme_details[name] = {'filepath': filepath,
                                              'userDefined': userDefined}

    def reloadAvailableSchemes(self):
        # _scheme_details contains the list of all available schemes, whilst
        # _schemes contains the lazily loaded schemes.
        self._scheme_details = {}
        self._schemes = {}

        #print self._systemSchemeDir, exists(self._systemSchemeDir)
        if isdir(self._systemSchemeDir):
            self._addSchemeDetailsFromDirectory(self._systemSchemeDir, 0)
        self._userSchemeDir = join(self._koDirSvc.userDataDir, 'schemes')
        #print self._userSchemeDir
        if not isdir(self._userSchemeDir):
            os.mkdir(self._userSchemeDir)
        else:
            self._addSchemeDetailsFromDirectory(self._userSchemeDir, 1)

        assert len(self._scheme_details) != 0 # We should always have Komodo schemes.

    def addScheme(self, scheme):
        #print "ADDING ", scheme.name
        self._scheme_details[scheme.name] = {'filepath': scheme.fname,
                                             'userDefined': scheme.writeable}
        self._schemes[scheme.name] = scheme

    def removeScheme(self, scheme):
        if scheme.name not in self._schemes:
            log.error("Couldn't remove scheme named %r, as we don't know about it", scheme.name)
            return
        self._schemes.pop(scheme.name)
        self._scheme_details.pop(scheme.name)

    def getSchemeNames(self):
        return sorted(self._scheme_details.keys())

    def getScheme(self, name):
        if name not in self._scheme_details:
            log.error("scheme %r does not exist, using Ocean_Dark instead", name)
            name = 'Tomorrow_Dark'
        scheme = self._schemes.get(name)
        if scheme is None:
            details = self._scheme_details[name]
            scheme = self._makeScheme(details['filepath'], details['userDefined'])
            if scheme is None:
                # This is primarily for tech support, to help answer the question
                # "why is my Komodo color scheme file not loading?"
                log.error("Unable to load Komodo color scheme: %r", details)
            else:
                self._schemes[name] = scheme
        return scheme

    def purgeUnsavedSchemes(self):
        for scheme in self._schemes.values():
            if scheme.unsaved:
                self.removeScheme(scheme)

    @classmethod
    def _makeScheme(cls, filepath, userDefined):
        pass # Implement in the derived class.
