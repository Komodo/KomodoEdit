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
# * It is an error to fetch a preference from a preference set that does not exist.

# * Once you set a preference, it is deemed to "exist".  Some preference sets
# (including the global prefset) load their default preferences from a file.  Thus,
# in general, this file of default preferences are preference "declarations" for that
# preference sets.

# * Preference sets use type-safe preferences. Once a preference is created, all
# future references to that preference must be using the same type.  Thus, for
# the global preference sets, the default prefs file also declares the type.

# * There is currently no way to get a "typeless" preference.
# getPref() and setPref() can not be used for simple preference types;
# the typed functions (getStringPref etc) must be used.  getPref
# and setPref can only be used for "complex" preferences, such as
# contained preference sets or ordered preferences.

# * Preference sets can have "parents".  The parent is *only* a namespace
# parent.  If a request for a preference is not found in the current set, the
# set's parent is searched, until there are no more parents.  Whenever a
# preference is _set_, we first check the current pref value (which may
# come from the parent).  If the current value is not the same, we set
# the value in the current preference set.  Thus, all future preference
# requests for the preference will then not search the parent list, but
# use the value just set directly in the prefset

# * A preference set may itself be stored as a preference inside another
# preference set.  This is completely different than the "parent" behaviour
# above.  When a preference set is contained in another, it is simply another
# preference that can be obtained by name from the containing preference set.
# (ie, instead of getting a simple string/number preference, you can get a
# complete rich preference set).
# This containment has no relationship to the "namespace parent" - requesting
# a preference name from a contained preference set does not automatically search
# for the name in the containing preference set.
# Note that a contained preference set could theoretically set its parent to
# the containing preference set, thereby getting containment _and_ parent
# namespace lookup.

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
#   fairly straightforward (i.e. setStringPref, getStringPref, etc..) -- none
#   of that has changed :)
#   

import sys, os, types, cgi, re, shutil, operator, copy
import time
from xml.dom import minidom
from xml.sax import SAXParseException
from eollib import newl

from xpcom import components, ServerException, COMException, nsError
from xpcom.server.enumerator import SimpleEnumerator
from xpcom.server import WrapObject, UnwrapObject
from xpcom.client import WeakReference

import logging
log = logging.getLogger('koPrefs')

from koXMLPrefs import *

koGlobalPreferenceSets = [
    koGlobalPreferenceDefinition(name="global",
                                 contract_id = "@activestate.com/koPreferenceSet;1",
                                 user_filename="prefs",
                                 defaults_filename="prefs"),
    koGlobalPreferenceDefinition(name="viewStateMRU",
                                 contract_id = "@activestate.com/koPrefCache;1",
                                 user_filename="view-state",
                                 save_format=koGlobalPreferenceDefinition.SAVE_FAST_ONLY
                                 ),
    koGlobalPreferenceDefinition(name="docStateMRU",
                                 contract_id = "@activestate.com/koPrefCache;1",
                                 user_filename="doc-state",
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

        return deserializeFile(filename)

_validations = {}

class koPreferenceSet:
    _com_interfaces_ = [components.interfaces.koIPreferenceSet,
                        components.interfaces.koIPreferenceObserver,
                        components.interfaces.koISerializableFast]
    _reg_desc_ = "Komodo Preference Set"
    _reg_contractid_ = "@activestate.com/koPreferenceSet;1"
    _reg_clsid_ = "{EE71E26E-7394-4d3f-8B4A-CA58E6F8154D}"

    chainNotifications = 0

    def __init__(self):
        # koIPreferenceSet attributes.
        self.id = ""
        self.idref = ""
        self._commonInit()
        
    def __str__(self):
        if hasattr(self, 'idref'):
            return '<PrefSet: id=%s idref=%s>' % (str(self.id), str(self.idref))
        else:
            return '<PrefSet: id=%s>' % (str(self.id))
    __repr__ = __str__

    def _commonInit(self):
        self._observerService = None
        self._prefObserverService = None
        self.prefs = {}
        self.parent = None

    ##
    # @deprecated since 6.0.0
    #
    def get_observerService(self):
        # This is deprecated, everyone should be using the prefObserverService
        # below for monitoring pref changes.
        if not self._observerService:
            self._observerService = components.classes['@activestate.com/koObserverService;1'].\
                           createInstance(components.interfaces.nsIObserverService)
        return self._observerService

    def get_prefObserverService(self):
        if not self._prefObserverService:
            self._prefObserverService = components.classes['@activestate.com/koObserverService;1'].\
                           createInstance(components.interfaces.nsIObserverService)
        return self._prefObserverService
    
    def __getstate__(self):
        prefs = {}
        for id, (val, typ) in self.prefs.items():
            if typ=="object":
                try:
                    val = UnwrapObject(val)
                except COMException:
                    pass
            prefs[id] = val, typ
        if hasattr(self, 'idref'):
            return (self.id, self.idref, prefs)
        return (self.id, prefs)

    def __setstate__(self, data):
        self._commonInit()
        if len(data) == 3:
            self.id, self.idref, self.prefs = data
        else:
            self.id, self.prefs = data
            self.idref = ""

    ###########################################################
    # The koIPreferenceSet interface:
    def set_parent(self, parent):
        # Performance optimization - if a Python implemented parent,
        # we can avoid the XPCOM call overhead
        try:
            parent = UnwrapObject(parent)
        except COMException:
            pass
        self.parent = parent
        self.chainNotifications = parent.chainNotifications

    def setValidation(self, prefName, validation):
        _validations[prefName] = validation

    def reset(self):
        # Any sub-objects get reset, and simple values get dropped.
        for id, (val, typ) in self.prefs.items():
            if typ == "object":
                val.reset()
            else:
                del self.prefs[id]
            self._notifyPreferenceChange(id)

    def getPrefIds(self):
        mine = self.prefs.keys()
        mine.sort()
        return mine

    def getAllPrefIds(self):
        mine = self.prefs.keys()
        if self.parent is not None:
            for parent_id in self.parent.getAllPrefIds():
                if parent_id not in mine:
                    mine.append(parent_id)
        mine.sort()
        return mine

    def _checkPrefType(self, prefid, pref_type, must_exist, pref):
        try:
            old_val, old_type = self.prefs[prefid]
            if old_type != pref_type:
                msg = "The preference '%s' has type '%s', but is being reset as type '%s'" % (prefid, old_type, pref_type)
                lastErrorSvc.setLastError(0, msg)
                raise COMException(nsError.NS_ERROR_UNEXPECTED, msg)
        except KeyError:
            if must_exist:
                msg = "The preference '%s' does not exist" % (prefid,)
                lastErrorSvc.setLastError(0, msg)
                raise COMException(nsError.NS_ERROR_UNEXPECTED, msg)

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

    def setPref(self, prefName, pref):
        """Set a preference in the preference set"""
        pref = UnwrapObject(pref)
        pref.id = prefName
        pref.chainNotifications = self.chainNotifications
        self.prefs[prefName] = pref, "object"
        if hasattr(pref, "parent"):
            pref.parent = self
        # log.warn("setting preference " + prefName + " to " + str(pref));
        self._notifyPreferenceChange(prefName)

    def setStringPref(self, prefName, pref):
        self._checkPrefType(prefName, "string", 0, pref)
        if self.prefs.get(prefName, (None,None))[0] != pref:
            self.prefs[prefName] = unicode(pref), "string"
            self._notifyPreferenceChange(prefName)
    def setLongPref(self, prefName, pref):
        self._checkPrefType(prefName, "long", 0, pref)
        if self.prefs.get(prefName, (None,None))[0] != pref:
            self.prefs[prefName] = long(pref), "long"
            self._notifyPreferenceChange(prefName)
    def setDoublePref(self, prefName, pref):
        self._checkPrefType(prefName, "double", 0, pref)
        if self.prefs.get(prefName, (None,None))[0] != pref:
            self.prefs[prefName] = float(pref), "double"
            self._notifyPreferenceChange(prefName)
    def setBooleanPref(self, prefName, pref):
        self._checkPrefType(prefName, "boolean", 0, pref)
        if self.prefs.get(prefName, (None,None))[0] != pref:
            self.prefs[prefName] = operator.truth(pref), "boolean"
            self._notifyPreferenceChange(prefName)

    def validateString(self, prefName, value):
        self._checkPrefType(prefName, "string", 0, pref)

    def validateLong(self, prefName, value):
        self._checkPrefType(prefName, "long", 0, pref)

    def _getPref(self, prefName, parentMethodName, expectedPrefType, defaultPref=None):
        """get a pref from the current set, else retrieve from the parent"""
        pref = None
        if self.prefs.has_key(prefName):
            pref, pref_type = self.prefs[prefName]
        elif self.parent:
            # Try to find the preference in this preference set's
            # parent. And thusly preferences bubble up through the
            # tree of preference sets.
            try:
                return self.parent._getPref(prefName, parentMethodName, expectedPrefType, defaultPref=defaultPref)
            except AttributeError:
                # Fallback - it's likely an xpcom object, so try unwrapping it.
                self.parent = UnwrapObject(self.parent)
                return self.parent._getPref(prefName, parentMethodName, expectedPrefType, defaultPref=defaultPref)

        if pref is None:
            if defaultPref is not None:
                return defaultPref
            raise COMException(nsError.NS_ERROR_UNEXPECTED, "The preference '%s' does not exist in '%r'." % (prefName, self))
        if expectedPrefType is not None and pref_type is not None and pref_type != expectedPrefType:
            raise COMException(nsError.NS_ERROR_UNEXPECTED, "The preference %s has type '%s', but was requested as type '%s'." % (prefName, pref_type, expectedPrefType))
        return pref

    def getPref(self, prefName):
        return self._getPref(prefName, 'getPref', "object")

    def getStringPref(self, prefName):
        return unicode(self._getPref(prefName, 'getStringPref', "string"))
    
    def getLongPref(self, prefName):
        return long(self._getPref(prefName, 'getLongPref', "long"))

    def getDoublePref(self, prefName):
        return float(self._getPref(prefName, 'getDoublePref', "double"))

    def getBooleanPref(self, prefName):
        return operator.truth(self._getPref(prefName, 'getBooleanPref', "boolean"))

    def getString(self, prefName, defaultValue=""):
        return unicode(self._getPref(prefName, 'getStringPref', "string", defaultValue))
    
    def getLong(self, prefName, defaultValue=0):
        return long(self._getPref(prefName, 'getLongPref', "long", defaultValue))

    def getDouble(self, prefName, defaultValue=0.0):
        return float(self._getPref(prefName, 'getDoublePref', "double", defaultValue))

    def getBoolean(self, prefName, defaultValue=False):
        return operator.truth(self._getPref(prefName, 'getBooleanPref', "boolean", defaultValue))

    def getPrefType(self, prefName):
        if self.prefs.has_key(prefName):
            return self.prefs[prefName][1]
        elif self.parent:
            return getattr(self.parent, 'getPrefType')(prefName)
        else:
            return None

    def _hasPref(self, prefName, parentMethodName):
        """check for a pref in the current set, else check in parent set"""
        if self.prefs.has_key(prefName):
            return 1
        elif self.parent:
            return getattr(self.parent, parentMethodName)(prefName)
        else:
            return 0
    def hasPref(self, prefName):
        return self._hasPref(prefName, 'hasPref')
    
    def hasPrefHere(self, prefName):
        return prefName in self.prefs
        
    def hasStringPref(self, prefName):
        if self._hasPref(prefName, 'hasStringPref'):
            return self.getPrefType(prefName)=="string";
        return 0
    def hasLongPref(self, prefName):
        if self._hasPref(prefName, 'hasLongPref'):
            return self.getPrefType(prefName)=="long";
        return 0
    def hasDoublePref(self, prefName):
        if self._hasPref(prefName, 'hasDoublePref'):
            return self.getPrefType(prefName)=="double";
        return 0
    def hasBooleanPref(self, prefName):
        if self._hasPref(prefName, 'hasBooleanPref'):
            return self.getPrefType(prefName)=="boolean";
        return 0

    def deletePref(self, prefName):
        """Remove a preference from the preference set.
        prefName is the name of the preference to be removed."""
        if self.prefs.has_key(prefName):
            del self.prefs[prefName]
            self._notifyPreferenceChange(prefName)

    def set_id(self, newId):
        self.id = newId

    def get_id(self):
        return self.id

    def serializeToFileFast(self, filename):
        pickleCache(self, filename)

    def serializeToFile(self, filename):
        with file(filename, "wb") as stream:
            writeXMLHeader(stream)
            self.serialize(stream, "")
            writeXMLFooter(stream)
        self.serializeToFileFast(filename + "c")

    def serialize(self, stream, basedir):
        """Serializes the preference set to a stream."""
        if not self.prefs:
            # dont serialize empty prefsets
            return
        attrs = []
        if hasattr(self, 'idref') and self.idref:
            attrs.append('idref="%s"' % cgi.escape(self.idref))
        if self.id:
            attrs.append('id="%s"' % cgi.escape(self.id))
        stream.write('<preference-set %s>%s' % (' '.join(attrs), newl))
        for prefName in sorted(self.prefs):
            try:
                pref, pref_type = self.prefs[prefName]
            except KeyError:
                continue
            # projects need unwrapped prefs to serialize
            if pref_type == 'object':
                pref = UnwrapObject(pref)
            serializePref(stream, pref, pref_type, prefName, basedir)
        stream.write('</preference-set>%s' % newl)

    def clone(self):
        ret = koPreferenceSet()
        ret.id = self.id
        if hasattr(self, 'idref'):
            ret.idref = self.idref
        else:
            ret.idref = ""
        ret.parent = self.parent
        for name, (val, typ) in self.prefs.items():
            if typ=="object":
                val = val.clone()
            ret.prefs[name] = val,typ
        return ret

    def update(self, source):
        self._update(source)
        
    def _update(self, source):
        # Manually iterate over the preferences
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
                raise COMException(nsError.NS_ERROR_UNEXPECTED, "You can not change a preference type during an update: prefname='%s'" % id)
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

    def dump(self, indent):
        def decomify(val):
            try:
                return UnwrapObject(val)
            except:
                return val
        if hasattr(self, 'idref'):
            print "%sPreference Set: id = '%s' idref = '%s'" % ("  " * indent, self.id, self.idref)
        else:
            print "%sPreference Set: id = '%s'" % ("  " * indent, self.id)
        print '%s  chained = %d' % ("  " * indent, self.chainNotifications)
        parent = UnwrapObject(self.parent)
        if parent is not None:
            print '%s  parent = %r' % ("  " * indent, parent)
            p_vals = [decomify(val[0]) for val in parent.prefs.values()]
            if self not in p_vals:
                print "%s  !!!! parent doesn't own me !!!!" % ("  " * indent)
        else:
            print '%s  parent is None' % ("  " * indent,)
        for (foo, bar) in self.prefs.items():
            print '%s  %s = %s' % ("  " * indent, foo, bar)
            if hasattr(bar[0], "parent") and UnwrapObject(bar[0].parent) != self:
                print "%s  !!!! child has wrong parent !!!!" % ("  " * indent)
            if hasattr(bar[0], "QueryInterface"):
                subPref = bar[0].QueryInterface(components.interfaces.koIPreference)
                subPref.dump(indent + 1)
            elif hasattr(bar[0], "dump"):
                bar[0].dump(indent + 1)

    # koIPreferenceObserver interface
    # this stuff now uses koObserverService
    def _notifyPreferenceChange(self, pref_id, prefset = None):
        if prefset is None: prefset = self
        if self._observerService:
            try:
                self._observerService.notifyObservers(prefset, self.id, pref_id)
            except COMException, e:
                pass # no one is listening

        if self._prefObserverService:
            try:
                self._prefObserverService.notifyObservers(prefset, pref_id, self.id)
            except COMException, e:
                pass # no one is listening
            
        if self.parent is not None and self.chainNotifications:
            parent = UnwrapObject(self.parent)
            if parent != self:
                parent._notifyPreferenceChange(pref_id, prefset)

    ##
    # @deprecated since 6.0.0
    #
    def addObserver( self, anObserver):
        import warnings
        warnings.warn("'koPreference.addObserver' is now deprecated. Please "
                      "use 'koPreference.prefObserverService.addObserver'",
                      DeprecationWarning)
        self.get_observerService().addObserver(anObserver, '', 0)

    ##
    # @deprecated since 6.0.0
    #
    def removeObserver( self, anObserver ):
        import warnings
        warnings.warn("'koPreference.removeObserver' is now deprecated. Please "
                      "use 'koPreference.prefObserverService.removeObserver'",
                      DeprecationWarning)
        try:
            self.get_observerService().removeObserver(anObserver, '')
        except COMException, e:
            pass # wasn't in the list


    ###########################################################
    # Utility methods

from xpcom.server.policy import SupportsPrimitive

primitivesMap = {
    'long' : components.interfaces.nsISupportsPRInt32,
    'string' : components.interfaces.nsISupportsString,
    'double' : components.interfaces.nsISupportsDouble,
    'boolean' : components.interfaces.nsISupportsPRBool,
}

class koPrefSupportsString:
    _com_interfaces_ = [components.interfaces.nsISupportsString]
    def __init__(self, pref):
        self.pref = pref
    def get_data(self):
        return self.pref._get_data()
    def toString(self):
        return unicode(self.pref)

class koPrefWrapper:
    # Only need to list the interfaces we dont have explicit support for.
    # Our QI function below handles the nsISupports ones.
    _com_interfaces_ = [components.interfaces.koIPreferenceSimpleValue]
    _reg_desc_ = "Komodo Preference Wrapper"
    _reg_contractid_ = "@activestate.com/koPrefWrapper;1"
    _reg_clsid_ = "{56FD749D-98FE-4da5-B673-BA1967718921}"
    def __init__(self, owner, name, type):
        self._owner = owner
        self.id = name
        self.type = type

    def get_data(self):
        return self._get_data()

    def _get_data(self):
        if self.type == "string":
            return self._owner.getStringPref(self.id)
        elif self.type == "long":
            return self._owner.getLongPref(self.id)
        elif self.type == "double":
            return self._owner.getDoublePref(self.id)
        elif self.type == "boolean":
            return self._owner.getBooleanPref(self.id)
        else:
            return self._owner.getPref(self.id)

    def get_primitiveIID(self):
        return primitivesMap[self.type];

    def __int__(self):
        return int(self._get_data())
    def __long__(self):
        return long(self._get_data())
    def __nonzero__(self):
        return self._get_data() != 0
    def __str__(self):
        return 'koPrefWrapper[%s=%s (%s)]' % (self.id, self._get_data(), self.type)
    def dump(self, indent):
        print "Preference %s, of type %s, has value %s" % (self.id, self.type, self._get_data())

    def serializeToFileFast(self, filename):
        pickleCache(self, filename)
        
    def serializeToFile(self, filename):
        with file(filename, "wb") as stream:
            self.serialize(stream, "")
        self.serializeToFileFast(filename+"c")

    def serialize(self, stream, basedir):
        """Serialize this wrapped preference to a stream."""
        serializePref(stream, self._get_data(), self.type, self.id, basedir)

    def _query_interface_(self, iid):
        if iid in (components.interfaces.nsISupportsString):
            return koPrefSupportsString(self)
        elif iid in (components.interfaces.nsISupportsPRUint64,
                     components.interfaces.nsISupportsPRInt64):
            return SupportsPrimitive(iid, self, "__long__", long)
        elif iid in (components.interfaces.nsISupportsPRUint32,
                     components.interfaces.nsISupportsPRInt32,
                     components.interfaces.nsISupportsPRUint16,
                     components.interfaces.nsISupportsPRInt16,
                     components.interfaces.nsISupportsPRUint8,
                     components.interfaces.nsISupportsPRBool):
            return SupportsPrimitive(iid, self, "__int__", int)
        elif iid in (components.interfaces.nsISupportsDouble,
                     components.interfaces.nsISupportsFloat):
            return SupportsPrimitive(iid, self, "__float__", float)


###################################################
#
# A generic "Ordered Preference"
#
###################################################


class koOrderedPreference:
    _com_interfaces_ = [components.interfaces.koIOrderedPreference]
    _reg_desc_ = "Komodo Ordered Preference"
    _reg_contractid_ = "@activestate.com/koOrderedPreference;1"
    _reg_clsid_ = "{6d6f80d0-573a-45ac-8be0-ec7ce6de5329}"

    def __init__(self):
        self.id = ""
        self.reset()

    def __str__(self):
        return '<koOrderedPreference: id=%s>'%self.id
    __repr__ = __str__

    def reset(self):
        self._collection = []
        self.type = "ordered-preference"

    def __getstate__(self):
        collection = []
        for val, typ in self._collection:
            if typ=="object":
                try:
                    val = UnwrapObject(val)
                except COMException:
                    pass
            collection.append( (val, typ) )
        return (collection, self.id, self.type)

    def __setstate__(self, data):
        (self._collection, self.id, self.type) = data

    def _inCollection(self, index):
        return index < len(self._collection) and \
               index > -len(self._collection)

    def appendPref(self, pref):
        self._collection.append((pref, "object"))

    def appendStringPref(self, pref):
        self._collection.append((unicode(pref), "string"))

    def appendLongPref(self, pref):
        self._collection.append((int(pref), "long"))

    def appendDoublePref(self, pref):
        self._collection.append((float(pref), "double"))

    def appendBooleanPref(self, pref):
        self._collection.append(operator.truth(pref), "boolean")

    def insertPref(self, index, pref):
        self._collection.insert(index, (pref, "object"))

    def insertStringPref(self, index, pref):
        self._collection.insert(index, (pref,"string"))

    def insertLongPref(self, index, pref):
        self._collection.insert(index, (pref, "long"))

    def insertDoublePref(self, index, pref):
        self._collection.insert(index, (pref, "double"))

    def insertBooleanPref(self, index, pref):
        self._collection.insert(index, (operator.truth(pref), "boolean"))

    def _getPref(self, index, expected_type):
        assert self._inCollection(index)
        try:
            val, typ = self._collection[index]
        except IndexError:
            raise COMException(nsError.NS_ERROR_UNEXPECTED,
                               "Ordered pref %s doesn't have a pref at index %d" % (self, index))
        if typ != expected_type:
            raise COMException(nsError.NS_ERROR_UNEXPECTED,
                               "Wrong type for index %d: pref type is '%s', but requested as type '%s'" % (index, typ, expected_type))
        return val

    def getPref(self, index):
        return self._getPref(index, "object")

    def getStringPref(self, index):
        return self._getPref(index, "string")

    def getLongPref(self, index):
        return self._getPref(index, "long")

    def getDoublePref(self, index):
        return self._getPref(index, "double")

    def getBooleanPref(self, index):
        return self._getPref(index, "boolean")

    def getPrefType(self, index):
        assert self._inCollection(index)
        return self._collection[index][1]

    def findStringPref(self, pref):
        i = 0
        for val, typ in self._collection:
            if typ == "string" and val == pref:
                return i
            i += 1
        return -1

    def findStringPrefIgnoringCase(self, pref):
        i = 0
        pref = pref.lower()
        for val, typ in self._collection:
            if typ == "string" and val.lower() == pref:
                return i
            i += 1
        return -1

    def findAndDeleteStringPref(self, pref):
        i = self.findStringPref(pref)
        if i >= 0:
            self.deletePref(i)
            return True
        return False

    def findAndDeleteStringPrefIgnoringCase(self, pref):
        i = self.findStringPrefIgnoringCase(pref)
        if i >= 0:
            self.deletePref(i)
            return True
        return False

    def get_length(self):
        return len(self._collection)

    def deletePref(self, index):
        assert self._inCollection(index)
        del self._collection[index]

    def clone(self):
        ret = koOrderedPreference()
        ret.id = self.id
        for val in self._collection:
            if type(val) == types.InstanceType:
                val = val.clone()
            ret._collection.append(val)
        return ret

    def update(self, source):
        self._update(source)
        
    def _update(self, source):
        new_collection = []
        for i in range(source.length):
            typ = source.getPrefType(i)
            if typ == "string":
                val = source.getStringPref(i)
            elif typ == "long":
                val = source.getLongPref(i)
            elif typ == "double":
                val = source.getDoublePref(i)
            elif typ == "boolean":
                val = source.getBooleanPref(i)
            elif typ == "object":
                val = source.getPref(i)
            else:
                raise COMException(nsError.NS_ERROR_UNEXPECTED, "unknown type '%s'" % (typ,))
            new_collection.append((val, typ))
        self._collection = new_collection
        return True

    def serializeToFile(self, filename):
        with file(filename, "wb") as stream:
            self.serialize(stream, "")

    def serialize(self, stream, basedir):
        if self.id:
            stream.write('<ordered-preference id="%s">%s' \
                         % (cgi.escape(self.id), newl))
        else:
            stream.write('<ordered-preference>%s' % newl)
        for pref, typ in self._collection:
            if typ == "object":
                pref = UnwrapObject(pref)
            serializePref(stream, pref, typ, basedir)
        stream.write('</ordered-preference>%s' % newl)

    def dump(self, indent):
        print "%sDumping koOrderedPreference %s:" % ("  " * indent, self)
        print "%s  id == %s" % ("  " * indent, self.id)
        for pref in self._collection:
            if hasattr(pref, "QueryInterface"):
                subPref = pref.QueryInterface(components.interfaces.koIPreference)
                subPref.dump(indent + 1)
            else:
                print '%s  %s' % ("  " * indent, pref)

###################################################
#
# The preference set cache object.
#
###################################################
class koPreferenceCache:
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
        with file(filename, "wb") as stream:
            writeXMLHeader(stream)
            self.serialize(stream, "")
            writeXMLFooter(stream)
        self.serializeToFileFast(filename+"c")

    def serializeToFileFast(self, filename):
        pickleCache(self, filename)

    def serialize(self, stream, basedir):
        """Serializes the preference set to a stream."""
        id = self.id or ''
        stream.write('<preference-cache id="%s" max_length="%s">%s' % (cgi.escape(id),self._maxsize, newl))
        indexes = self.index_map.keys()
        indexes.sort()
        for index in indexes:
            id = self.index_map[index]
            pref = self.pref_map[id][0]
            serializePref(stream, UnwrapObject(pref), "object", id, basedir)
        stream.write('</preference-cache>%s' % newl)

    # koIPreference interface
    # clone a copy of this preference set and all child preferences.
    def clone(self):
        unwrapped = UnwrapObject(self)
        # XXX this is not much of an optimization because UnWrapObject isn't deep.  We need one of those.
        return WrapObject(copy.deepcopy(unwrapped), koIPreference)

    def update(self): # from another preference set object - presumably a modified clone!
        raise COMException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    def dump(self, indent): # For debugging.
        print "%sPreference Set Cache: id = '%s'" % ("  " * indent, self.id)
        indexes = self.index_map.keys()
        indexes.sort()
        indent += 1
        for index in indexes:
            id = self.index_map[index]
            pref = self.index_map[id]
            print "%sPreference ID '%s':" % ("  " * indent, id)
            pref.dump(indent+1)

    def _is_sane(self):
        return len(self.pref_map.keys()) == len(self.index_map.keys())

    def setPref( self, pref):
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
        return self.pref_map.get(id, (None, None))[0]
    
    def hasPref( self, id):
        assert self._is_sane()
        return self.pref_map.has_key(id)

    def get_length(self):
        assert self._is_sane()
        return len(self.index_map)

    def get_max_length(self):
        return self._maxsize
    def set_max_length(self, size):
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
# The global preferences service.
#
###################################################

class koGlobalPrefService:
    _com_interfaces_ = [components.interfaces.koIPrefService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Global Preference Service"
    _reg_contractid_ = "@activestate.com/koPrefService;1"
    _reg_clsid_ = "{ad71a3ab-9f42-4fe2-9c4d-a0e4702d3e98}"

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
        obsvc.addObserver(self, 'xpcom-shutdown', True)
        obsvc.addObserver(self, 'profile-before-change', True)

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
        if defn.user_filename:
            defn.user_filename = os.path.join( self._koDirSvc.userDataDir, defn.user_filename)
            try:
                prefs = self.factory.deserializeFile(defn.user_filename + ".xml")
            except:
                # Error loading the user file - presumably they edited it poorly.
                # Just ignore the error, and continue as if no user preferences existed at all.
                log.exception("There was an error loading the user preference file %r", defn.user_filename + ".xml")
                # Save the prefs.xml file, in case the user can fix it themselves.
                old_name = defn.user_filename + ".xml"
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
                prefs = components.classes[defn.contract_id].createInstance()
            prefs = UnwrapObject(prefs)
            if defaultPrefs is not None:
                prefs.set_parent(defaultPrefs)
        else:
            # No user filename - so the prefset is just the defaults.
            assert defaultPrefs is not None, "No default prefs, and no user prefs - what do you expect me to do?"
            prefs = UnwrapObject(defaultPrefs)

        self.pref_map[prefName] = prefs, defn

    def getPrefs(self, name):
        if not self.pref_map.has_key(name):
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, "No preference set with name '%s'" % (name,) )
        if self.pref_map[name][0] is None:
            self._setupGlobalPreference(name)
        assert self.pref_map[name][0] is not None, "Did not setup the preference set '%s'" % (name,)
        return self.pref_map[name][0]

    def shutDown(self):
        log.debug("koGlobalPrefService shutting down...")
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

    def saveState(self):
        self.savePrefsState("global")
        self.savePrefsState("viewStateMRU")
        self.savePrefsState("docStateMRU")

    def savePrefsState(self, prefName):
        prefs, defn = self.pref_map[prefName]
        if prefs is None: return # may not have been init'd yet
        assert defn
        fname = defn.user_filename + ".xml"        
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
        
    def get_effectivePrefs(self):
        if self._partSvc.currentProject:
            return self._partSvc.currentProject.prefset
        return self.prefs
            
if __name__=='__main__':
    # NOTE: Most test code in prefs.js - test using xpcshell
    factory = koPreferenceSetObjectFactory()
    prefSet = factory.deserializeFile(sys.argv[1])

    prefSet = prefSet.QueryInterface(components.interfaces.koIPreferenceSet)
    print "koPreferenceSet::testComponent: Dumping test prefSet after deserialization..."
    prefSet.dump(0)
