
#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

# There are a number of concepts WRT preferences worth getting your head around:
# The main "entry point" for preferences is generally a "preference set".

# PREFERENCE SETS
# -------------------
# * Each preference set is a container; it may have zero or more named child
#   preferences.  Each child must have a name that is unique among its siblings.
#   Each child may refer to its parent as the "container".
#
# * The "preference root" is the top of the hierachy; it has no container.
#
# * A preference root may have a base preference; when getting a preference, if
#   the named pref does not exist, the base preference is consulted (for the
#   same pref name), and its base pref and so on.
#
# TODO: I don't want to have this behavour - does this actually work?
# * When fetching a pref from a child preference (i.e. a grandchild or deeper),
#   if the preference is not found, the corresponding pref from the base of the
#   root is consulted.  That is, for A.getPref("1").grePref("2"), assuming that
#   it is is missing, A.base.getPref("1").getPref("2") is attempted.  The
#   returned prefset is known as a shadow preference.
#
# * Shadow prefs do not have any values of their own; they exist to maintain the
#   correct container relationship. They cannot be serialized to disk. Setting a
#   pref on the shadow pref will turn it (and all shadowed parent containers)
#   into a normal prefset. In practice, consumers should not have to think about
#   shadow prefs at all.
#
# * It is an error to fetch a preference from a preference set that does not
#   exist (after shadow pref lookup, of course).
#
# * Preference sets use type-safe preferences. Once a preference is created, all
#   future references to that preference must be using the same type.  Any
#   shadow prefs will be consulted for this type checking if the preference does
#   not otherwise exist.
#
# * There is currently no way to get a "typeless" preference.  getPref() and
#   setPref() can not be used for simple preference types; the typed functions
#   (getString etc) must be used.  getPref and setPref can only be used for
#   "complex" preferences, such as contained preference sets or ordered
#   preferences.

# An email from KenS on the deserialization mechanisms here:
#   
#   The change is not in how you interact with preference set objects, but
#   rather in how they are deserialized. I have written a "preference set
#   object factory", which maintains a registry of serializers which are
#   capable of generating preference objects from XML DOM nodes. That part of
#   the preference set class which used to perform deserialization has been
#   factored out into its own class, koPreferenceSetDeserializer, an instance
#   of which is registered with the preference set object factory.
#   
#   Basically, the new architecture means that, with the addition of a few more
#   preference types (such as arrays), and their associated deserializers, we
#   will have a bunch of persistable components for saving all kinds of state
#   information.
#   
#   The canonical example of how preference sets work is to be found in
#   koPrefs.py. Look at the koGlobalPrefService class for details on
#   serializing and deserializing; the setting and retrieving of preferences is
#   fairly straightforward (i.e. setString, getString, etc..) -- none
#   of that has changed :)
#   

import sys
import os
import types
import shutil
import operator
import functools
import copy
import time
import logging
import warnings
from eollib import newl

from xpcom import components, ServerException, COMException, nsError
from xpcom.server.enumerator import SimpleEnumerator
from xpcom.server import WrapObject, UnwrapObject
from xpcom.client import WeakReference
from zope.cachedescriptors.property import Lazy as LazyProperty
from zope.cachedescriptors.property import LazyClassAttribute

from fileutils import AtomicFileWriter
from koXMLPrefs import *


log = logging.getLogger('koPrefs')
#log.setLevel(logging.DEBUG)

koGlobalPreferenceSets = [
    koGlobalPreferenceDefinition(name="global",
                                 contract_id = "@activestate.com/koPreferenceRoot;1",
                                 user_file_basename="prefs",
                                 defaults_filename="prefs"),
    koGlobalPreferenceDefinition(name="viewStateMRU",
                                 contract_id = "@activestate.com/koPrefCache;1",
                                 user_file_basename="view-state",
                                 save_format=koGlobalPreferenceDefinition.SAVE_FAST_ONLY
                                 ),
    koGlobalPreferenceDefinition(name="docStateMRU",
                                 contract_id = "@activestate.com/koPrefCache;1",
                                 user_file_basename="doc-state",
                                 save_format=koGlobalPreferenceDefinition.SAVE_FAST_ONLY
                                 ),
]


def positive(value):
    return value > 0

def nonnegative(value):
    return value >= 0

_validationNamespace = {}
_validationNamespace['positive'] = positive
_validationNamespace['nonnegative'] = nonnegative

# clean up global namespace
del positive
del nonnegative

# special value to mean "not set"
NOT_SET = type("NOT_SET", (object,), {
    "__nonzero__": lambda self: False
    })()

class koPreferenceSetObjectFactory(koXMLPreferenceSetObjectFactory):
    """
    Creates new preference set objects from an input stream
    via a registry of deserialization objects.
    Could be instantiated as a singleton (i.e. service).
    """

    _com_interfaces_ = [components.interfaces.koIPreferenceSetObjectFactory]
    _reg_contractid_ = "@activestate.com/koPreferenceSetObjectFactory;1"
    _reg_clsid_ = "{d264f6ac-0c46-4bbf-993c-c5a6f8a9cb10}"
    
    def deserializeFile(self, filename):
        """Adds preferences to this preference set from a filename."""

        result = deserializeFile(filename)
        if isinstance(result, koPreferenceChild):
            # Deserializing prefsets from before Komodo 9.0.0a1; there was no
            # separate class for root prefs.
            root = koPreferenceRoot()
            root.__setstate__(result.__getstate__())
            return root
        return result

_validations = {}

class koPreferenceSetBase(object):
    """Base class for koPreferenceRoot and koPreferenceChild; this implements
    the common functionallity of generic preference sets that are key-value
    stores.
    """

    # The type of the preference; "" for default, "file" for file preferences,
    # "project" for project preferences.  This is used for deserialization.
    preftype = ''

    # The parent container that holds this preference set. A root preference set
    # will never have a container. All child preference sets must have a
    # container.
    container = None

    # The preference set this prefset inherits from.  This is needed for child
    # preferences since it will be used for lookups of prefs that are not set
    # here; see comment at top of file.
    inheritFrom = NOT_SET

    def __init__(self):
        # koIPreferenceSet attributes.
        self.id = ""
        self.idref = "" ##< Used for project preferences
        self._commonInit()

    def __str__(self):
        result = '<PrefSet: id=%s' % (self.id, )
        if self.preftype:
            result += ' type=%s' % (self.preftype, )
        if self.idref:
            result += ' idref=%s' % (self.idref, )
        if self._is_shadow:
            result += ' shadow=true'
        return result + ">"
    __repr__ = __str__

    def _commonInit(self):
        self._observerService = None
        self.prefs = {}
        self.inheritFrom = NOT_SET

    @LazyProperty
    def prefObserverService(self):
        return (components.classes['@activestate.com/koObserverService;1']
                          .createInstance(components.interfaces.nsIObserverService))

    def __getstate__(self):
        prefs = {}
        for id, (val, typ) in self.prefs.items():
            if typ=="object":
                try:
                    val = UnwrapObject(val)
                except COMException:
                    pass
                # Ignore shadow preference sets.
                if val._is_shadow:
                    continue
            prefs[id] = val, typ
        return (self.id, self.preftype, self.idref, prefs)

    def __setstate__(self, data):
        self._commonInit()

        if len(data) == 4:
            self.id, self.preftype, self.idref, self.prefs = data
        # Allow older style pickle states.
        elif len(data) == 3:
            self.id, self.idref, self.prefs = data
            self.preftype = ""
        else:
            self.id, self.prefs = data
            self.idref = ""
            self.preftype = ""

        for key, (pref, typ) in self.prefs.items()[:]:
            if getattr(pref, "_is_shadow", False):
                del self.prefs[key]
            elif hasattr(pref, "container"):
                pref.container = self

        # inheritFrom will be set by the pref restore code

    ###########################################################
    # The koIPreferenceSet interface:

    _inheritFrom = None
    @property
    def inheritFrom(self):
        """The prefset from which this prefset will inherit in the case of missing prefs"""
        if self._inheritFrom is NOT_SET and self.container:
            container_base = UnwrapObject(self.container.inheritFrom)
            if container_base:
                try:
                    self._inheritFrom = container_base.getPref(self.id)
                except ServerException:
                    self._inheritFrom = None
            else:
                self._inheritFrom = None
        elif self._inheritFrom is NOT_SET:
            self._inheritFrom = None
        return self._inheritFrom
    @inheritFrom.setter
    def inheritFrom(self, base):
        """The prefset from which this prefset will inherit in the case of missing prefs"""
        if base:
            base = UnwrapObject(base)
            if base is self:
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "Pref root can't inherit from itself")
            if __debug__:
                b = base
                while b:
                    assert b is not self, "Trying to set cyclic pref inheritance"
                    b = UnwrapObject(b.inheritFrom)
        self._inheritFrom = base

    @property
    def parent(self):
        warnings.warn("PrefSet: prefset.parent is deprecated, use prefset.inheritFrom",
                      DeprecationWarning,
                      stacklevel=2)
        return self.inheritFrom
    @parent.setter
    def parent(self, base):
        warnings.warn("PrefSet: prefset.parent is deprecated, use prefset.inheritFrom",
                      DeprecationWarning,
                      stacklevel=2)
        self.inheritFrom = UnwrapObject(base)

    def set_parent(self, base):
        warnings.warn("koIPreferenceSet.set_parent is deprecated; please use "
                      "koIPreferenceRoot.inheritFrom instead.",
                      DeprecationWarning,
                      stacklevel=2)
        self.inheritFrom = UnwrapObject(base)

    @property
    def _is_shadow(self):
        raise NotImplementedError("_is_shadow is not implemented on %s" %
                                  (self.__class__.__name__))

    def setValidation(self, prefName, validation):
        _validations[prefName] = validation

    def reset(self):
        # All preferences get dropped.
        ids = self.prefs.keys()
        self.prefs = {}
        for id in ids:
            self._notifyPreferenceChange(id)

    def getPrefIds(self):
        names = set()
        for name, (pref, typ) in self.prefs.items():
            if typ == "object" and pref._is_shadow:
                continue # skip shadow prefs
            names.add(name)
        return sorted(names)

    def getAllPrefIds(self):
        mine = set(self.prefs.keys())
        if self.inheritFrom is not None:
            mine.update(self.inheritFrom.getAllPrefIds())
        return sorted(mine)

    def _checkPrefType(self, prefid, pref_type, must_exist, pref):
        """Check that the given prefid can be set as a child pref
        (i.e. that any existing prefs of the same name has the same type)
        @param prefid {str} The name of the child pref
        @param pref_type {str} The type of the pref
        @param must_exist {bool} Whether to fail if the pref does not already exist
        @param pref {any} The new value of the preference
        """
        try:
            old_val, old_type = self.prefs[prefid]
            if old_type != pref_type:
                msg = "The preference '%s' has type '%s', but is being reset as type '%s'" % (prefid, old_type, pref_type)
                lastErrorSvc.setLastError(0, msg)
                raise ServerException(nsError.NS_ERROR_UNEXPECTED, msg)
        except KeyError:
            if must_exist:
                msg = "The preference '%s' does not exist" % (prefid,)
                lastErrorSvc.setLastError(0, msg)
                raise ServerException(nsError.NS_ERROR_UNEXPECTED, msg)

        # If this pref has a validation expression (i.e. a 'validation'
        # attribute in it XML representation), then ensure that returns
        # true.
        if prefid in _validations:
            _validationNamespace['value'] = pref
            validation = _validations[prefid]
            try:
                try:
                    isValid = eval(validation, _validationNamespace)
                except Exception, ex:
                    exstr = str(ex)
                    if exstr.startswith("invalid syntax"):
                        msg = ("The validation expression for pref '%s' is "
                               "not a valid Python expression: %s"
                               % (prefid, validation))
                    else:
                        msg = ("'%s' is not a valid value for preference "
                               "'%s'. Validating it with '%s' raised an "
                               "exception: %s"
                               % (pref, prefid, validation, exstr))
                    lastErrorSvc.setLastError(0, msg)
                    raise COMException(nsError.NS_ERROR_UNEXPECTED, msg)
                if not isValid:
                    msg = ("'%s' is not a valid value for preference "
                           "'%s'. It must satisfy the following "
                           "expression: %s" % (pref, prefid, validation))
                    lastErrorSvc.setLastError(0, msg)
                    raise COMException(nsError.NS_ERROR_UNEXPECTED, msg)
            finally:
                del _validationNamespace['value']

    def _setPrefValue(self, prefName, prefType, prefValue):
        """Set the given preference to the given value, and fire off appropriate
        notifications.  No checking is done."""
        if prefType != "object":
            if self.prefs.get(prefName, (None,None))[0] == prefValue:
                return # No change
        self.prefs[prefName] = (prefValue, prefType)
        self._notifyPreferenceChange(prefName)

    def setPref(self, prefName, pref):
        """Set a preference in the preference set"""
        pref = UnwrapObject(pref)
        self._checkPrefType(prefName, "object", False, pref)
        pref.id = prefName
        if hasattr(pref, "container"):
            pref.container = self
        self._setPrefValue(prefName, "object", pref)

    def setString(self, prefName, pref):
        self._checkPrefType(prefName, "string", 0, pref)
        self._setPrefValue(prefName, "string", unicode(pref))
    def setLong(self, prefName, pref):
        self._checkPrefType(prefName, "long", 0, pref)
        self._setPrefValue(prefName, "long", long(pref))
    def setDouble(self, prefName, pref):
        self._checkPrefType(prefName, "double", 0, pref)
        self._setPrefValue(prefName, "double", float(pref))
    def setBoolean(self, prefName, pref):
        self._checkPrefType(prefName, "boolean", 0, pref)
        self._setPrefValue(prefName, "boolean", bool(pref))
    # Deprecated pref setters - we don't care to log them as deprecated though.
    setStringPref = setString
    setLongPref = setLong
    setDoublePref = setDouble
    setBooleanPref = setBoolean

    def validateString(self, prefName, value):
        self._checkPrefType(prefName, "string", 0, pref)

    def validateLong(self, prefName, value):
        self._checkPrefType(prefName, "long", 0, pref)

    def _getPref(self, prefName, expectedPrefType, defaultPref=None):
        """get a pref from the current set, else retrieve inherited pref"""

        value, typ = self._lookupPref(prefName)
        if typ is None:
            if defaultPref is not None:
                return defaultPref
            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                  "The preference '%s' does not exist in '%r'."
                                    % (prefName, self))
        if expectedPrefType not in (None, typ):
            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                  "The preference %s has type '%s', but was requested as type '%s'."
                                    % (prefName, typ, expectedPrefType))
        return value

    def _lookupPref(self, prefName):
        """Locate the given preference (helper for _getPref).
        @returns (pref value, pref type)

        Pref lookup order:
        1. Locally set prefs (i.e. self.prefs)
        2. Base prefs chain

        @note This will, as a side-effect, construct shadow prefs as necessary.
        """
        # 1. Locally set prefs
        if prefName in self.prefs:
            return self.prefs[prefName]

        # 2. Base prefs chain
        value, typ = self._getPrefInherited(prefName)
        if typ is not None:
            return value, typ

        return None, None

    def _getPrefInherited(self, prefName):
        """Helper to get a shadow pref if can be inherited.
        @return (shadow pref, type)
        @return (None, None) if it's not on the prefset to inherit from either
        @note This assumes the pref isn't here.
        @note This will, as a side-effect, construct shadow prefs as necessary.
        """
        assert prefName not in self.prefs
        if not self.inheritFrom:
            return None, None
        value, typ = self.inheritFrom._lookupPref(prefName)
        if typ is None:
            return None, None # not found
        if typ == "object":
            # need to wrap the pref (construct the shadow pref)
            base = value
            if isinstance(base, koPreferenceSetBase):
                value = koPreferenceChild()
                value.chainNotifications = getattr(self, "chainNotifications",
                                                   False)
            elif isinstance(base, koOrderedPreference):
                value = koOrderedPreference()
            else:
                raise NotImplementedError("Don't know how to wrap a %s"
                                          % (base.__class__.__name__,))
            value.inheritFrom = base
            value.id = base.id
            value.container = self
            assert value._is_shadow
            self.prefs[prefName] = (value, typ)
        return value, typ

    def getPref(self, prefName):
        return self._getPref(prefName, "object")

    def getStringPref(self, prefName):
        return unicode(self._getPref(prefName, "string"))
    
    def getLongPref(self, prefName):
        return long(self._getPref(prefName, "long"))

    def getDoublePref(self, prefName):
        return float(self._getPref(prefName, "double"))

    def getBooleanPref(self, prefName):
        return operator.truth(self._getPref(prefName, "boolean"))

    def getString(self, prefName, defaultValue=""):
        return unicode(self._getPref(prefName, "string", defaultValue))
    
    def getLong(self, prefName, defaultValue=0):
        return long(self._getPref(prefName, "long", defaultValue))

    def getDouble(self, prefName, defaultValue=0.0):
        return float(self._getPref(prefName, "double", defaultValue))

    def getBoolean(self, prefName, defaultValue=False):
        return operator.truth(self._getPref(prefName, "boolean", defaultValue))

    def getPrefType(self, prefName):
        return self._lookupPref(prefName)[1]

    def hasPref(self, prefName):
        return self.getPrefType(prefName) is not None
    
    def hasPrefHere(self, prefName):
        if prefName not in self.prefs:
            return False
        pref, typ = self.prefs[prefName]
        if typ == "object":
            if pref._is_shadow:
                return False
        return True
        
    def hasStringPref(self, prefName):
        return self.getPrefType(prefName) == "string"
    def hasLongPref(self, prefName):
        return self.getPrefType(prefName) == "long"
    def hasDoublePref(self, prefName):
        return self.getPrefType(prefName) == "double"
    def hasBooleanPref(self, prefName):
        return self.getPrefType(prefName) == "boolean"

    def deletePref(self, prefName):
        """Remove a preference from the preference set.
        prefName is the name of the preference to be removed."""
        if self.prefs.has_key(prefName):
            del self.prefs[prefName]
            self._notifyPreferenceChange(prefName)

    def serializeToFileFast(self, filename):
        pickleCache(self, filename)

    def serializeToFile(self, filename):
        with AtomicFileWriter(filename, "wb", encoding="utf-8") as stream:
            writeXMLHeader(stream)
            self.serialize(stream, "")
            writeXMLFooter(stream)
        self.serializeToFileFast(filename + "c")


    def serialize(self, stream, basedir):
        """Serializes the preference set to a stream."""
        stream.write('<preference-set')
        if self.idref:
            stream.write(' idref="%s"' % cgi_escape(self.idref))
        if self.id:
            stream.write(' id="%s"' % cgi_escape(self.id))
        if self.preftype:
            stream.write(' preftype="%s"' % cgi_escape(self.preftype))
        stream.write('>%s' % (newl))
        for prefName in sorted(self.prefs):
            try:
                pref, pref_type = self.prefs[prefName]
            except KeyError:
                continue
            # projects need unwrapped prefs to serialize
            if pref_type == 'object':
                pref = UnwrapObject(pref)
                # A shadowed pref inherits from the base, don't write it out.
                if pref._is_shadow:
                    continue
            serializePref(stream, pref, pref_type, prefName, basedir)
        stream.write('</preference-set>%s' % newl)

    def update(self, source):
        self._update(source)
        
    def _update(self, source):
        # Manually iterate over the preferences
        source = UnwrapObject(source)
        if not isinstance(source, koPreferenceSetBase):
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "Can only update from another prefset")
        if source is self:
            return False # update from self? Haha

        something_changed = False
        for id in source.getPrefIds():
            typ = source.getPrefType(id)
            existing_val  = None
            existing_type = None
            try:
                if self.hasPrefHere(id):
                    existing_type = self.getPrefType(id)
            except COMException:
                pass
            if existing_type is not None and existing_type != typ:
                raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                      "Can't change from %s to %s during an update: prefname='%s'" %
                                      (existing_type, typ, id))
            if typ == "string":
                if existing_type is not None:
                    existing_val = self.getStringPref(id)
                new_val = source.getStringPref(id)
                changed = new_val != existing_val
            elif typ == "long":
                if existing_type is not None:
                    existing_val = self.getLongPref(id)
                new_val = source.getLongPref(id)
                changed = new_val != existing_val
            elif typ == "boolean":
                if existing_type is not None:
                    existing_val = self.getBooleanPref(id)
                new_val = source.getBooleanPref(id)
                changed = new_val != existing_val
            elif typ == "double":
                if existing_type is not None:
                    existing_val = self.getDoublePref(id)
                new_val = source.getDoublePref(id)
                changed = new_val != existing_val
            elif typ == "object":
                if existing_type is not None:
                    new_val = UnwrapObject(self.getPref(id))
                    changed = new_val._update(source.getPref(id))
                else:
                    new_val = source.getPref(id)
                    changed = True
            else:
                raise TypeError, "Unknown child of type '%s'" % (typ,)
            # XXX - may need better equality semantics here!?!?
            if changed:
                #print "notifying pref change %r of %r, new %r existing %r" % (self.id, id, new_val, existing_val)
                self.prefs[id] = new_val, typ
                self._notifyPreferenceChange(id)
                something_changed = True
        return something_changed

    def dump(self, indent, suppressPrint=False):
        buf = ["%s%r" % ("  " * indent, self)]

        if getattr(self, "chainNotifications", False):
            buf.append('%s  chained = %d' % ("  " * indent, self.chainNotifications))
        
        inheritFrom = getattr(self, "inheritFrom", None)
        if inheritFrom:
            buf.append('%s  inheritFrom=%r' % ("  " * indent, inheritFrom))

        for id, (val, typ) in self.prefs.items():
            if typ == "object":
                container = getattr(UnwrapObject(val), "container", None)
                if container not in (None, self):
                    buf.append("%s  !!!! child has wrong container !!!!" %
                               ("  " * indent))
                buf.append(val.dump(indent + 1, True))
            else:
                buf.append('%s  %s = %r' % ("  " * indent, id, val))
        buf = "\n".join(buf)
        if not suppressPrint:
            print(buf)
        return buf

    # koIPreferenceObserver interface
    # this stuff now uses koObserverService
    def _notifyPreferenceChange(self, pref_id, prefset = None):
        if prefset is None: prefset = self
        if self._observerService:
            try:
                self._observerService.notifyObservers(prefset, self.id, pref_id)
            except COMException, e:
                pass # no one is listening

        # Notify observers, but only if we've already ran the getter once. (Otherwise nobody could
        # have been registered and it's a waste of time)
        if "prefObserverService" in self.__dict__:
            try:
                self.prefObserverService.notifyObservers(prefset, pref_id, self.id)
            except COMException, e:
                pass # no one is listening

        container = getattr(self, "container", None)
        if container:
            assert container is not self, "Containing self"
            container._notifyPreferenceChange(pref_id, prefset)

class koPreferenceRoot(koPreferenceSetBase):
    _com_interfaces_ = [components.interfaces.koIPreferenceContainer,
                        components.interfaces.koIPreferenceSet,
                        components.interfaces.koIPreferenceRoot,
                        components.interfaces.koIPreferenceObserver,
                        components.interfaces.koISerializableFast]
    _reg_desc_ = "Komodo Preference Set Root"
    _reg_contractid_ = "@activestate.com/koPreferenceRoot;1"
    _reg_clsid_ = "{2a536b8d-f8c1-4892-a8ab-c184d1bdd195}"

    def clone(self, ret=None):
        if ret is None:
            ret = koPreferenceRoot()
        ret.id = self.id
        ret.idref = getattr(self, "idref", "")
        ret.inheritFrom = self.inheritFrom
        for name, (val, typ) in self.prefs.items():
            if typ == "object":
                if val._is_shadow:
                    # No point in cloning shadow prefs.
                    continue
                val = val.clone()
            ret.prefs[name] = val,typ
        return ret

    @property
    def _is_shadow(self):
        return False

class koPreferenceChild(koPreferenceSetBase):
    _com_interfaces_ = [components.interfaces.koIPreferenceContainer,
                        components.interfaces.koIPreferenceSet,
                        components.interfaces.koIPreferenceObserver,
                        components.interfaces.koISerializableFast,
                        components.interfaces.koIPreferenceChild]
    _reg_desc_ = "Komodo Preference Set Child"
    _reg_contractid_ = "@activestate.com/koPreferenceSet;1"
    _reg_clsid_ = "{EE71E26E-7394-4d3f-8B4A-CA58E6F8154D}"

    chainNotifications = False
    container = None

    def _commonInit(self):
        super(koPreferenceChild, self)._commonInit()
        self.container = None

    def __getstate__(self):
        return tuple(super(koPreferenceChild, self).__getstate__())

    def __setstate__(self, data):
        super(koPreferenceChild, self).__setstate__(data)

    @property
    def parent(self):
        warnings.warn("koIPreferenceSet.parent getter is deprecated; use "
                      "koIPreferenceChild.container instead.",
                      DeprecationWarning, stacklevel=2)
        return self.container
    @parent.setter
    def parent(self, value):
        warnings.warn("koIPreferenceSet.parent setter is deprecated; use "
                      "koIPreferenceChild.container instead.",
                      DeprecationWarning, stacklevel=2)
        self.container = UnwrapObject(value)
    def set_parent(self, value):
        warnings.warn("koIPreferenceSet.set_parent is deprecated; use "
                      "koIPreferenceChild.container instead.",
                      DeprecationWarning, stacklevel=2)
        self.container = UnwrapObject(value)

    @property
    def _is_shadow(self):
        """Whether this is a shadow pref.  This will return true if we're a
        shadow pref which should not be serialized"""
        return self.inheritFrom is not None

    def _unshadow(self, check_container=True):
        """Creates a hard copy of the inherited pref set."""
        if not self._is_shadow:
            return
        # We have to unshadow all parent preference sets.
        if check_container and self.container and self.container._is_shadow:
            self.container._unshadow()
            return

        log.debug("Unshadowing %r ", self.id)
        new_prefs = {}
        for prefid, (pref, typ) in self.inheritFrom.prefs.items():
            if typ == "object":
                # We have to unshadow all child preference sets.
                pref = self.getPref(prefid)
                pref = UnwrapObject(pref)
                assert pref._is_shadow
                pref._unshadow(check_container=False)
                assert not pref._is_shadow
            elif typ not in ("string", "long", "double", "boolean"):
                raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                      "unknown type '%s'" % (typ,))
            new_prefs[prefid] = (pref, typ)
        self.prefs = new_prefs
        self.inheritFrom = None # detach

    def _setPrefValue(self, prefName, prefType, prefValue):
        """Override koPreferenceSetBase._setPrefValue to implement the correct
        preference inheritance (i.e. deal with collapsing shadow prefs).
        @see koPreferenceSetBase._setPrefValue
        """
        if self._is_shadow:
            self._unshadow()
        super(koPreferenceChild, self)._setPrefValue(prefName, prefType, prefValue)
        assert not self._is_shadow, "Child prefset is shadow after setting"

    def setPref(self, prefName, pref):
        """Override koPreferenceSetBase.setPref to update .chainNotifications"""
        super(koPreferenceChild, self).setPref(prefName, pref)
        pref = UnwrapObject(pref) # Shut up PyXPCOM warnings about no attr
        if hasattr(pref, "chainNotifications"):
            pref.chainNotifications = self.chainNotifications

    def clone(self):
        ret = koPreferenceChild()
        ret.id = self.id
        ret.idref = getattr(self, "idref", "")
        ret.inheritFrom = self.inheritFrom
        for name, (val, typ) in self.prefs.items():
            if typ == "object":
                if val._is_shadow:
                    # No point in cloning shadow prefs.
                    continue
                val = val.clone()
            ret.prefs[name] = (val, typ)
        return ret

    def serializeToFileFast(self, filename):
        raise NotImplementedError("Can't serialize a pref child to a file")
    serializeToFile = serializeToFileFast

    ###########################################################
    # Utility methods

class koPreferenceSet(koPreferenceChild):
    """ Deprecated class used for unpickling old preferences; this should no
    longer be used, since we now have separate child and root classes.
    @deprecated since Komodo 9.0.0a1
    """
    # Clobber the XPCOM registration information
    _reg_clsid_ = None
    _reg_contractid_ = None
    def __new__(self):
        # unpickling doesn't actually call __new__ or __init__, so this works...
        raise DeprecationWarning("koPreferenceSet should not be used directly")

class koPrefSupportsString(object):
    _com_interfaces_ = [components.interfaces.nsISupportsString]
    def __init__(self, pref):
        self.pref = pref
    @property
    def data(self):
        return self.pref._get_data()
    def toString(self):
        return unicode(self.pref)


###################################################
#
# A generic "Ordered Preference"
#
###################################################


class koOrderedPreference(object):
    _com_interfaces_ = [components.interfaces.koIOrderedPreference,
                        components.interfaces.koIPreferenceContainer,
                        components.interfaces.koIPreferenceChild]
    _reg_desc_ = "Komodo Ordered Preference"
    _reg_contractid_ = "@activestate.com/koOrderedPreference;1"
    _reg_clsid_ = "{6d6f80d0-573a-45ac-8be0-ec7ce6de5329}"

    container = None

    _inheritFrom = None
    @property
    def inheritFrom(self):
        """The ordered preference this preference inherits from. Since it makes
        no sense to look up inherited preferences once this preference has been
        modified (since all the indexes would be unaligned), we just drop the
        inheritance (i.e. detach it) once we modify this preference."""
        if self._inheritFrom is NOT_SET:
            self._inheritFrom = None
        return self._inheritFrom
    @inheritFrom.setter
    def inheritFrom(self, value):
        self._inheritFrom = value

    def __init__(self):
        self.id = ""
        self._collection = []
        self.type = "ordered-preference"

    def __str__(self):
        return '<koOrderedPreference: id=%s>'%self.id
    __repr__ = __str__

    def reset(self):
        self.container = None
        self._collection = []
        # Clear any inheritance.
        self.inheritFrom = None

    def __getstate__(self):
        collection = []
        for val, typ in self._collection:
            if typ=="object":
                try:
                    val = UnwrapObject(val)
                except COMException:
                    pass
                if val._is_shadow:
                    continue
            collection.append( (val, typ) )
        return (collection, self.id, self.type)

    def __setstate__(self, data):
        (self._collection, self.id, self.type) = data

    def _forward_if_inherited(fn):
        """Decorator to forward calls of self.fn() to self.inheritFrom.fn()
        if self.inheritFrom is set
        """
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self.inheritFrom is not None:
                return getattr(self.inheritFrom, fn.__name__)(*args, **kwargs)
            return fn(self, *args, **kwargs)
        return wrapper

    @_forward_if_inherited
    def _inCollection(self, index):
        return index < len(self._collection) and \
               index > -len(self._collection)

    @property
    def _is_shadow(self):
        return (self.inheritFrom is not None)

    def _detaches(fn):
        """Decorator to detach any preference inheritance"""
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self.inheritFrom is not None:
                log.debug("Detaching %s calling %s",
                          self, fn.__name__)
                new_collection = []
                for val, typ in self.inheritFrom._collection:
                    if typ == "object":
                        val = UnwrapObject(val)
                        if isinstance(val, koPreferenceSetBase):
                            shadow = koPreferenceChild()
                            shadow.id = val.id
                            if hasattr(shadow, "container"):
                                shadow.container = self
                        elif isinstance(child_base, koOrderedPreference):
                            shadow = koOrderedPreference()
                        else:
                            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                                  "Don't know how to detach %s"
                                                    % (type(val,)))
                        shadow.inheritFrom = val
                        val = shadow
                    elif typ not in ("string", "long", "double", "boolean"):
                        raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                              "unknown type '%s'" % (typ,))
                    new_collection.append((val, typ))
                self._collection = new_collection
                self.inheritFrom = None # detach
            return fn(self, *args, **kwargs)
        return wrapper

    @_detaches
    def appendPref(self, pref):
        pref = UnwrapObject(pref)
        assert isinstance(pref, (koOrderedPreference, koPreferenceSetBase)), \
            "Appending a pref that is neither an ordered pref nor a pref set"
        self._collection.append((pref, "object"))

    @_detaches
    def appendString(self, pref):
        self._collection.append((unicode(pref), "string"))

    @_detaches
    def appendLong(self, pref):
        self._collection.append((int(pref), "long"))

    @_detaches
    def appendDouble(self, pref):
        self._collection.append((float(pref), "double"))

    @_detaches
    def appendBoolean(self, pref):
        self._collection.append((operator.truth(pref), "boolean"))

    @_detaches
    def insertPref(self, index, pref):
        pref = UnwrapObject(pref)
        assert isinstance(pref, (koOrderedPreference, koPreferenceSetBase)), \
            "Inserting a pref that is neither an ordered pref nor a pref set"
        self._collection.insert(index, (pref, "object"))

    @_detaches
    def insertString(self, index, pref):
        self._collection.insert(index, (pref,"string"))

    @_detaches
    def insertLong(self, index, pref):
        self._collection.insert(index, (pref, "long"))

    @_detaches
    def insertDouble(self, index, pref):
        self._collection.insert(index, (pref, "double"))

    @_detaches
    def insertBoolean(self, index, pref):
        self._collection.insert(index, (operator.truth(pref), "boolean"))

    @_forward_if_inherited
    def _getPref(self, index, expected_type, defaultPref=None):
        try:
            val, typ = self._collection[index]
        except IndexError:
            if defaultPref is not None:
                return defaultPref
            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                  "Ordered pref %s doesn't have a pref at index %d"
                                    % (self, index))
        if typ != expected_type:
            raise ServerException(nsError.NS_ERROR_UNEXPECTED,
                                  "Wrong type for index %d: pref type is '%s', but requested as type '%s'"
                                    % (index, typ, expected_type))
        return val

    def getPref(self, index):
        return self._getPref(index, "object")

    def getString(self, index):
        return self._getPref(index, "string")

    def getLong(self, index):
        return self._getPref(index, "long")

    def getDouble(self, index):
        return self._getPref(index, "double")

    def getBoolean(self, index):
        return self._getPref(index, "boolean")

    @_forward_if_inherited
    def getPrefType(self, index):
        try:
            return self._collection[index][1]
        except IndexError:
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "The index %s is not found in the collection" % (index,))

    @_forward_if_inherited
    def findString(self, pref):
        i = 0
        for val, typ in self._collection:
            if typ == "string" and val == pref:
                return i
            i += 1
        return -1

    @_forward_if_inherited
    def findStringIgnoringCase(self, pref):
        i = 0
        pref = pref.lower()
        for val, typ in self._collection:
            if typ == "string" and val.lower() == pref:
                return i
            i += 1
        return -1

    def findAndDeleteString(self, pref):
        i = self.findString(pref)
        if i >= 0:
            self.deletePref(i)
            return True
        return False

    def findAndDeleteStringIgnoringCase(self, pref):
        i = self.findStringIgnoringCase(pref)
        if i >= 0:
            self.deletePref(i)
            return True
        return False

    @property
    def length(self):
        if self._is_shadow:
            return self.inheritFrom.length
        return len(self._collection)

    @_detaches
    def deletePref(self, index):
        assert self._inCollection(index)
        del self._collection[index]

    def clone(self):
        ret = koOrderedPreference()
        ret.id = self.id
        for val, typ in self._collection:
            if typ == "object":
                if val._is_shadow:
                    # No point in cloning shadow prefs.
                    continue
                val = val.clone()
            ret._collection.append((val, typ))
        return ret

    @_detaches
    def update(self, source):
        self._update(source)
        
    @_detaches
    def _update(self, source):
        source = UnwrapObject(source)
        if not isinstance(source, koOrderedPreference):
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "Can only update from another ordered pref")
        if source is self:
            return False # update from self? Haha

        assert isinstance(source, koOrderedPreference)
        new_collection = []
        for i in range(source.length):
            typ = source.getPrefType(i)
            if typ in ("string", "long", "double", "boolean"):
                val = source._getPref(i, typ)
            elif typ == "object":
                val = UnwrapObject(source.getPref(i))
            else:
                raise COMException(nsError.NS_ERROR_UNEXPECTED,
                                   "unknown type '%s'" % (typ,))
            new_collection.append((val, typ))
        self._collection = new_collection
        return True

    def serializeToFile(self, filename):
        with AtomicFileWriter(filename, "wb", encoding="utf-8") as stream:
            self.serialize(stream, "")

    def serialize(self, stream, basedir):
        if self._is_shadow:
            return
        if self.id:
            stream.write('<ordered-preference id="%s">%s' \
                         % (cgi_escape(self.id), newl))
        else:
            stream.write('<ordered-preference>%s' % newl)
        for pref, typ in self._collection:
            if typ == "object":
                pref = UnwrapObject(pref)
            serializePref(stream, pref, typ, basedir)
        stream.write('</ordered-preference>%s' % newl)

    def dump(self, indent, suppressPrint=False):
        buf = ["%s%r" % ("  " * indent, self)]
        for pref, typ in self._collection:
            if typ == "object":
                buf.append(pref.dump(indent + 1, True))
            else:
                buf.append('%s  %s' % ("  " * indent, pref))
        buf = "\n".join(buf)
        if not suppressPrint:
            print(buf)
        return buf

    # Deprecated pref accessors - we don't care to log them as deprecated though.
    appendStringPref = appendString
    appendLongPref = appendLong
    appendDoublePref = appendDouble
    appendBooleanPref = appendBoolean
    insertStringPref = insertString
    insertLongPref = insertLong
    insertDoublePref = insertDouble
    insertBooleanPref = insertBoolean
    getStringPref = getString
    getLongPref = getLong
    getDoublePref = getDouble
    getBooleanPref = getBoolean
    findStringPref = findString
    findStringPrefIgnoringCase = findStringIgnoringCase
    findAndDeleteStringPref = findAndDeleteString
    findAndDeleteStringPrefIgnoringCase = findAndDeleteStringIgnoringCase


    del _detaches
    del _forward_if_inherited

###################################################
#
# The preference set cache object.
#
###################################################
class koPreferenceCache(object):
    _com_interfaces_ = [components.interfaces.koIPreferenceCache, components.interfaces.koISerializableFast]
    _reg_desc_ = "Komodo Preference Cache"
    _reg_contractid_ = "@activestate.com/koPrefCache;1"
    _reg_clsid_ = "{15e9c69e-ddd4-460a-b47d-9de299636ecc}"
    _maxsize = 300 # provide a default for those cases where the maxsize isn't
                   # being set (e.g. in the test suite)
    
    def __init__(self):
        self._maxsize = 0
        # We need to index by ID, but also keep an "index", so we can
        # move elements to the start, and bump them off the end. The
        # most common (and therefore most necessary to perform)
        # operation are adding entries to the MRU list.  This may be an
        # existing entry (meaning the item is "moved"), and may require
        # "popping" an item off the end.
        
        # So for each element in the dictionary, we keep the index - but
        # indexes may have "holes" (ie, certain index values may be
        # missing).  Thus, we also keep the smallest and largest index
        # in the set.  The largest hole can only be "n" elements large -
        # and is likely to be even smaller.  So worst case is a loop of
        # (typically) 300, and often a tiny loop.
        
        # Theoretically, these smallest and largest values may wrap
        # around, but that can only happen after 2^16 entries have been
        # pushed in a *single session* (the indexes are reset after a
        # load)
        
        self.pref_map = {} # Map of [id] = prefs, index
        self.index_map = {} # Map of [index] = id
        self.index_small = 0
        self.index_big = 0
        self.id = None
        self.type = "object"
        assert self._is_sane()

    # serializing.
    def __getstate__(self):
        pref_map = {}
        for id, (val, index) in self.pref_map.items():
            if type(val) == types.InstanceType:
                try:
                    val = UnwrapObject(val)
                except COMException:
                    pass
            pref_map[id] = val, index
        return pref_map, self.index_map, self.index_small, self.index_big, self.id, self.type

    def __setstate__(self, state):
        self.pref_map, self.index_map, self.index_small, self.index_big, self.id, self.type = state
        assert self._is_sane()
    
    def serializeToFile(self, filename):
        with AtomicFileWriter(filename, "wb", encoding="utf-8") as stream:
            writeXMLHeader(stream)
            self.serialize(stream, "")
            writeXMLFooter(stream)
        self.serializeToFileFast(filename+"c")

    def serializeToFileFast(self, filename):
        pickleCache(self, filename)

    def serialize(self, stream, basedir):
        """Serializes the preference set to a stream."""
        id = self.id or ''
        stream.write('<preference-cache id="%s" max_length="%s">%s' % (cgi_escape(id),self._maxsize, newl))
        indexes = self.index_map.keys()
        indexes.sort()
        for index in indexes:
            id = self.index_map[index]
            pref = self.pref_map[id][0]
            serializePref(stream, UnwrapObject(pref), "object", id, basedir)
        stream.write('</preference-cache>%s' % newl)

    # koIPreferenceContainer interface
    # clone a copy of this preference set and all child preferences.
    def clone(self):
        # This doesn't seem to be called at this point; skip the exception if
        # we actually need it.
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
        # Wrap the clone in a XPCOM wrapper
        sip = (components.classes["@mozilla.org/supports-interface-pointer;1"]
                         .createInstance(components.interfaces.nsISupportsInterfacePointer))
        sip.data = copy.deepcopy(self)
        return sip.data.QueryInterface(components.interfaces.koIPreferenceCache)

    def update(self): # from another preference set object - presumably a modified clone!
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    def dump(self, indent, suppressPrint=False): # For debugging.
        buf = []
        buf.append("%sPreference Set Cache: id = '%s'" %
                   ("  " * indent, self.id))
        indexes = self.index_map.keys()
        indexes.sort()
        indent += 1
        for index in indexes:
            id = self.index_map[index]
            pref = self.index_map[id]
            buf.append("%sPreference ID '%s':" % ("  " * indent, id))
            buf.append(pref.dump(indent + 1, True))
        buf = "\n".join(buf)
        if not suppressPrint:
            print(buf)
        return buf

    def _is_sane(self):
        return len(self.pref_map.keys()) == len(self.index_map.keys())

    def setPref(self, pref):
        assert self._is_sane()
        if not pref.id:
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, "The preference must have a valid ID")
        id = pref.id
        existing, index = self.pref_map.get(id, (None,None))
        if index is not None:
            del self.index_map[index]
            del self.pref_map[id]
        
        self.index_small -= 1
        self.pref_map[id] = pref, self.index_small
        self.index_map[self.index_small] = id
        # Do we need to pop the top?
        if self._maxsize > 0:
            while len(self.pref_map.keys()) > self._maxsize:
                index_look = self.index_big
                while not self.index_map.has_key(index_look):
                    index_look-=1
                pop_id = self.index_map[index_look]
                del self.index_map[index_look]
                del self.pref_map[pop_id]
                self.index_big = index_look

        assert self._is_sane()

    def getPref(self, id):
        assert self._is_sane()
        pref = UnwrapObject(self.pref_map.get(id, (None, None))[0])
        if not isinstance(pref, (koPreferenceRoot, koPreferenceChild)):
            log.warn("deserializing and reserializing prefset %r", id)
            # Deserializing prefsets from before Komodo 9.0.0a1; there was no
            # separate class for root prefs.
            root = koPreferenceRoot()
            root.__setstate__(pref.__getstate__())
            pref = root
        # Put it back in a XPCOM wrapper
        sip = (components.classes["@mozilla.org/supports-interface-pointer;1"]
                         .createInstance(components.interfaces.nsISupportsInterfacePointer))
        sip.data = pref
        return sip.data
    
    def hasPref( self, id):
        assert self._is_sane()
        return self.pref_map.has_key(id)

    @property
    def length(self):
        assert self._is_sane()
        return len(self.index_map)

    @property
    def max_length(self):
        return self._maxsize
    @max_length.setter
    def max_length(self, size):
        if size < 2:
            raise COMException(nsError.NS_ERROR_UNEXPECTED, "Max size must be >=2")
        self._maxsize = size

    def enumPreferences(self):
        indexes = self.index_map.keys()
        indexes.sort()
        ret = []
        for index in indexes:
            id = self.index_map[index]
            ret.append(self.pref_map[id][0])
        return SimpleEnumerator(ret)


###################################################
#
# Per-project and per-file preferences.
#
# These are exactly the same as a regular preference root, but can be
# QueryInterface'd to see if it belongs to a file or project.
#
###################################################

class koProjectPreferenceSet(koPreferenceRoot):
    _com_interfaces_ = [components.interfaces.koIProjectPreferenceSet] + \
                       koPreferenceRoot._com_interfaces_
    _reg_desc_ = "Komodo Project Preferences"
    _reg_contractid_ = "@activestate.com/koProjectPreferenceSet;1"
    _reg_clsid_ = "{961bad79-65e1-964e-bc84-e65941a8c5f1}"
    preftype = 'project'

    def clone(self):
        ret = koProjectPreferenceSet()
        koPreferenceRoot.clone(self, ret)
        return ret

class koFilePreferenceSet(koPreferenceRoot):
    _com_interfaces_ = [components.interfaces.koIFilePreferenceSet] + \
                       koPreferenceRoot._com_interfaces_
    _reg_desc_ = "Komodo File Preferences"
    _reg_contractid_ = "@activestate.com/koFilePreferenceSet;1"
    _reg_clsid_ = "{433a740b-bcb1-b747-8dcf-c570be6d905e}"
    preftype = 'file'

    def clone(self):
        ret = koFilePreferenceSet()
        koPreferenceRoot.clone(self, ret)
        return ret

###################################################
#
# The global preferences service.
#
###################################################

class koGlobalPrefService(object):
    _com_interfaces_ = [components.interfaces.koIPrefService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Global Preference Service"
    _reg_contractid_ = "@activestate.com/koPrefService;1"
    _reg_clsid_ = "{ad71a3ab-9f42-4fe2-9c4d-a0e4702d3e98}"

    # Pref idle save time (in seconds)
    IDLE_TIME = 5
    _addedIdleObserver = False

    def __init__(self):
        log.debug("koPrefService starting up...")
        global lastErrorSvc
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                      .getService(components.interfaces.koILastErrorService)

        self.pref_map = {}
        self.factory = koPreferenceSetObjectFactory()

        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        
        for defn in koGlobalPreferenceSets:
            self.pref_map[defn.name] = None, defn
        # And do the "global" one now, so that self.prefs "just works"
        self.prefs = self.getPrefs("global")
        self._partSvc = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService)

        # some limitation on pref sizes
        self.getPrefs("viewStateMRU").max_length = self.prefs.getLongPref("viewStateMRUSize")
        self.getPrefs("docStateMRU").max_length = self.prefs.getLongPref("docStateMRUSize")

        obsvc = components.classes["@mozilla.org/observer-service;1"].\
                    getService(components.interfaces.nsIObserverService)
        obsvc.addObserver(self, 'xpcom-shutdown', False)
        obsvc.addObserver(self, 'profile-before-change', False)
        log.debug("koPrefService started")

    @LazyClassAttribute
    def idleService(self):
        return (components.classes["@mozilla.org/widget/idleservice;1"]
                          .getService(components.interfaces.nsIIdleService))

    def _setupGlobalPreference(self, prefName):
        if not self.pref_map.has_key(prefName):
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, "No well-known preference set with name '%s'" % (prefName,))

        existing, defn = self.pref_map[prefName]
        assert existing is None, "Asked to setup a global preference that has already been setup"

        defaultPrefs = None
        if defn.defaults_filename:
            defn.defaults_filename = os.path.join(self._koDirSvc.supportDir, defn.defaults_filename)
            defaultPrefs = self.factory.deserializeFile(defn.defaults_filename + ".xml")

        # Get the user preferences (currently ignoring "common" prefs, i.e.
        # for all users on the current machine), upgrading if necessary.
        if defn.user_file_basename:
            if not defn.user_filepath:
                defn.user_filepath = os.path.join( self._koDirSvc.userDataDir, defn.user_file_basename)
            try:
                prefs = self.factory.deserializeFile(defn.user_filepath + ".xml")
            except:
                # Error loading the user file - presumably they edited it poorly.
                # Just ignore the error, and continue as if no user preferences existed at all.
                log.exception("There was an error loading the user preference file %r", defn.user_filepath + ".xml")
                # Save the prefs.xml file, in case the user can fix it themselves.
                old_name = defn.user_filepath + ".xml"
                new_name = "%s.corrupt_%s" % (old_name, time.strftime("%Y%m%d_%H%M%S"))
                try:
                    os.rename(old_name, new_name)
                except:
                    log.exception("Failed to rename %s => %s", old_name, new_name)
                    try:
                        shutil.copyfile(old_name, new_name)
                    except:
                        log.exception("Can't even copy file %s => %s", old_name, new_name)
                prefs = None
            if prefs is None:
                # No prefs?  Create a default set.
                try:
                    prefs = components.classes[defn.contract_id].createInstance()
                except:
                    log.exeception("Failed to create " + defn.contract_id)
                    raise
            prefs = UnwrapObject(prefs)
            assert isinstance(prefs, (koPreferenceRoot, koPreferenceCache))
            assert not isinstance(prefs, koPreferenceChild)
            if defaultPrefs is not None:
                prefs.inheritFrom = defaultPrefs
        else:
            # No user filename - so the prefset is just the defaults.
            assert defaultPrefs is not None, "No default prefs, and no user prefs - what do you expect me to do?"
            prefs = UnwrapObject(defaultPrefs)

        if not prefs.id:
            prefs.id = prefName

        self.pref_map[prefName] = prefs, defn

    def getPrefs(self, name):
        if not self.pref_map.has_key(name):
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, "No preference set with name '%s'" % (name,) )
        if self.pref_map[name][0] is None:
            self._setupGlobalPreference(name)
        assert self.pref_map[name][0] is not None, "Did not setup the preference set '%s'" % (name,)
        return self.pref_map[name][0]

    def resetPrefs(self, prefName):
        if not self.pref_map.has_key(prefName):
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, "No well-known preference set with name '%s'" % (prefName,))

        existing, defn = self.pref_map[prefName]
        if existing is None:
            # Not setup yet - that's fine.
            return

        # Remove any saved preferences.
        if defn.user_filepath and os.path.exists(defn.user_filepath):
            os.remove(defn.user_filepath)

        # Setup the prefs again.
        self.pref_map[prefName] = None, defn
        return self.getPrefs(prefName)

    def removeIdleObserver(self):
        if self._addedIdleObserver:
            self._addedIdleObserver = False
            self.idleService.removeIdleObserver(self, self.IDLE_TIME)

    def shutDown(self):
        log.debug("koGlobalPrefService shutting down...")
        self.removeIdleObserver()
        self.saveState()
        obsvc = components.classes["@mozilla.org/observer-service;1"].\
                    getService(components.interfaces.nsIObserverService)
        obsvc.removeObserver(self, 'xpcom-shutdown')
        obsvc.removeObserver(self, 'profile-before-change')

    def observe(self, subject, topic, data):
        if topic == 'profile-before-change':
            log.debug("global prefs: profile-before-change")
            self.saveState()
        elif topic == 'xpcom-shutdown':
            log.debug("pref service status got xpcom-shutdown, unloading");
            self.shutDown()
        elif topic == 'idle':
            # nsIIdleService has called us - it's time to save prefs
            self.removeIdleObserver()
            self.saveState()

    def saveState(self):
        self.savePrefsState("global")
        self.savePrefsState("viewStateMRU")
        self.savePrefsState("docStateMRU")

    def savePrefsState(self, prefName):
        prefs, defn = self.pref_map[prefName]
        if prefs is None: return # may not have been init'd yet
        assert defn
        fname = defn.user_filepath + ".xml"        
        if not os.path.isdir(os.path.dirname(fname)):
            # create the directory if it does not exist
            try:
                os.makedirs(os.path.dirname(fname))
            except:
                log.exception("Couldn't make directory for global preferences")
        log.info("serializing pref state %s to file: %r", prefName, fname)
        # prefs.dump(0)
        if defn.save_format in [koGlobalPreferenceDefinition.SAVE_DEFAULT, koGlobalPreferenceDefinition.SAVE_XML_ONLY]:
            UnwrapObject(prefs).serializeToFile(fname)
        if defn.save_format in [koGlobalPreferenceDefinition.SAVE_DEFAULT, koGlobalPreferenceDefinition.SAVE_FAST_ONLY]:
            UnwrapObject(prefs).serializeToFileFast(fname + "c")
        
    def saveWhenIdle(self):
        if not self._addedIdleObserver:
            # Call saveState after 5 seconds of idling.
            self._addedIdleObserver = True
            self.idleService.addIdleObserver(self, self.IDLE_TIME)

    @property
    def effectivePrefs(self):
        if self._partSvc.currentProject:
            return self._partSvc.currentProject.prefset
        return self.prefs
            
if __name__=='__main__':
    # NOTE: Most test code in prefs.js - test using xpcshell
    factory = koPreferenceSetObjectFactory()
    prefSet = factory.deserializeFile(sys.argv[1])

    prefSet = prefSet.QueryInterface(components.interfaces.koIPreferenceSet)
    prefSet.dump(0)
