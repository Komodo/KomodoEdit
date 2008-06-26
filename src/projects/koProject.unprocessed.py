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

"""
Interface to the Komodo Project Files and their constituent parts.

-- a koIPart is any chunk of data serializable as part of a project file
-- a koIProject is the toplevel koIPart.
-- koIParts can have a prefset attribute which is serialized as a child but available
   as an XPCOM property
"""

from __future__ import generators
import traceback
import os
import sys
import urlparse
import string
import fnmatch
import weakref
import operator
import re
import shutil
import tempfile
import types
import time
from pprint import pprint
import random
import logging
from xml.sax import SAXParseException
from xml.sax.saxutils import escape, unescape, quoteattr
from xml.dom import pulldom

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject

import uriparse
import upgradeutils
from URIlib import URIParser, RemoteURISchemeTypes
from koXMLPrefs import NodeToPrefset
from eollib import newl
from findlib2 import paths_from_path_patterns
from projectUtils import *

# kpf ver 3 == komodo 4.0
# kpf ver 4 == komodo 4.1, fixing whitespace escape in macro's
KPF_VERSION = 4
gLastProjNum = 1

ANCHOR_MARKER = '!@#_anchor'
CURRENTPOS_MARKER = '!@#_currentPos'

log = logging.getLogger("koProject")
#log.setLevel(logging.DEBUG)

#---- support routines

def _iconRelpathtoURL(relpath, project_dirname):
    # keep this here as part of an upgrade of old style url's for icons
    if relpath.startswith('[PROJECTDIR]'):
        relpath = relpath.replace('[PROJECTDIR]', project_dirname, 1)
        path = os.path.normpath(relpath) # normalize to platform-specific slashes
        url = uriparse.localPathToURI(path)
        return url

    if relpath.startswith('[ICONSDIR]'):
        url = 'chrome://komodo/content/icons' + relpath[len('[ICONSDIR]'):]
        return url

    return uriparse.localPathToURI(relpath)

def _makeNewProjectName():
    global gLastProjNum
    newname = "Unnamed Project %d" % gLastProjNum
    gLastProjNum += 1
    return newname


#---- PyXPCOM implementations

class koPart(object):
    _com_interfaces_ = [components.interfaces.koIPart]
    keybindable = 0
    type = 'part'
    prettytype = 'Unknown Part'
    _iconurl = ''
    _observerSvc = None
    primaryInterface = 'koIPart'

    def __init__(self, project):
        assert project is not None
        self._name = ''
        self._url = ''
        self._path = '' # local path
        self._attributes = {}
        self._value = ''
        self._tmpAttributes = {} # not serialized
        self._project = project
        self._parent = None
        self.id = getNextId(self)
        self._attributes['id'] = self.id
        self._idref = None
        self.flavors = ['text/unicode','application/x-komodo-part',\
# #if PLATFORM != "win"
                        # XXX for a later release, scintilla needs work in this area
                        'TEXT',#,'COMPOUND_TEXT','STRING','UTF-8' \
# #endif
                        ]

        # treeView support
        self.properties = {}
        self.live = 0
        self._prefset = None
        self._filterString = None
        self._uri = None

    def set_value(self, val):
        # normalize line endings to linux line endings
        val = val.replace("\r\n", "\n")
        val = val.replace("\r", "\n")
        self._value = val
    def get_value(self):
        return self._value
    value = property(get_value, set_value)

    def _storeData(self):
        self._prefset = None
        # dump the old id from the child and pref maps
        if self.id in self._project._childmap:
            # this part still has a reference via self.children, no need to store
            del self._project._childmap[self.id]
        if self.id in self._project._prefmap:
            self._prefset = self._project._prefmap[self.id]
            del self._project._prefmap[self.id]

    def _restoreData(self):
        if hasattr(self, 'children'):
            self._project._childmap[self.id] = self.children
        if self._prefset:
            self._prefset.idref = self.id
            self._project._prefmap[self.id] = self._prefset
            self._prefset = None

    def assignId(self):
        # we will setup an id based on attributes from the project file
        if not self._attributes.has_key('id'):
            self.id = getNextId(self)
            self._attributes['id'] = self.id
            if hasattr(self, 'children') and self.id not in self._project._childmap:
                #print "assignId [%s]: add child ref to childmap" % self.id
                self._project._childmap[self.id] = self.children
        elif self.id == self._attributes['id']:
            self.getIDRef()
            if self._idref == self.id:
                if self.id not in idmap:
                    #print "assignID [%s]: adding self to idmap" % self.id
                    idmap[self.id] = self
                if hasattr(self, 'children'):
                    if self.id not in self._project._childmap:
                        #print "assignId [%s]: add child ref to childmap" % self.id
                        self._project._childmap[self.id] = self.children
                    #elif self.children is not self._project._childmap[self.id]:
                    #    print "*** assignId [%s]: children in map are not mine!" % self.id
                return
            # this part is KEY to getting non-live children into live folders
            id = self._attributes['id'] = self._idref
            if id in self._project._prefmap:
                prefset = self._project._prefmap[id]
                if self._parent:
                    prefset.parent = self._parent.get_prefset().parent
                elif self.id in self._project._prefmap:
                    oldpref = self._project._prefmap[self.id]
                    prefset.parent = oldpref.parent
                self._project._prefmap[self.id] = self._project._prefmap[id]
            if id in self._project._childmap:
                children = self._project._childmap[id]
                if self.id in self._project._childmap:
                    children += self._project._childmap[self.id]
                    self._project._childmap[id] = children
                    self.children = children
                    del self._project._childmap[self.id]
                    for child in children:
                        child.set_parent(self)



        # first, dump the old id from the idmap
        if self.id in idmap:
            del idmap[self.id]

        # dump the old id from the child and pref maps
        self._storeData()

        self.id = self._attributes['id']
        self._idref = None
        idmap[self.id] = self

        # add the new id to the maps
        self._restoreData()

    def get_keybinding_description(self):
        return self.prettytype + "s: " + self._attributes['name']

    def _getObserverSvc(self):
        if not self._observerSvc:
            self._observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        return self._observerSvc

    def destroy(self):
        if hasattr(self, 'children'):
            for child in self.children:
                child.destroy()
            del self.children
            if self.id in self._project._childmap:
                del self._project._childmap[self.id]

        self.set_prefset(None)
        self._parent = None
        self._project = None

        #print "refs: ",sys.getrefcount(self)

    def get_iconurl(self):
        if self._attributes.has_key('icon'):
            return self._attributes['icon']
        else:
            return self._iconurl

    def _urltorelpath(self, urlin):
        if urlin.startswith('chrome://'):
            return None
        project_dirname = self._project._relativeBasedir
        path = uriparse.URIToLocalPath(urlin)
        return uriparse.RelativizeURL(self._project._relativeBasedir, path)

    def set_iconurl(self, url):
        if not url or url == self._iconurl:
            self.removeAttribute('icon')
            if self._tmpAttributes.has_key('relativeiconurl'):
                del self._tmpAttributes['relativeiconurl']
        else:
            self.setAttribute('icon', url)
            self._tmpAttributes['relativeiconurl'] = self._urltorelpath(url)
        try:
            self._getObserverSvc().notifyObservers(self, 'part_changed', '')
        except Exception, unused:
            pass

    def added(self):
        # we need to walk up the chain of parent containers until we hit
        # either a menu or a toolbar, and notify them that they need to be
        # redrawn
        p = self._parent
        while p and p != p._parent:
            # We need to detect changes to menus and toolbars that already exist
            # the "and p._added" bit is to avoid notifying of changes to menus
            # or toolbars in the deserialization phase (as child parts get
            # their .added() called before their parents.
            if (p.type == 'menu' or p.type == 'toolbar') and p._added:
                try:
                    self._getObserverSvc().notifyObservers(p,
                                                           p.type + '_changed',
                                                           'child added')
                except:
                    pass # no listener
                break # no point in moving any further
            p = p._parent

    def removed(self, previous_parent):
        # we need to walk up the chain of parent containers until we hit
        # either a menu or a toolbar, and notify them that they need to be
        # redrawn
        p = previous_parent
        while p and p != p._parent:
            if p.type == 'menu' or p.type == 'toolbar':
                try:
                    self._getObserverSvc().notifyObservers(p,
                                                           p.type + '_changed',
                                                           'child removed')
                except:
                    pass # no listener
                break # no point in moving any further
            p = p._parent

    def __str__(self):
        if self.type in ('file','folder'):
            return 'Part (%s): url=%s, name=%s\nChildren = %s'\
                   % (self.type, getattr(self, 'url', 'NOURL'),
                      getattr(self, 'name', 'NONAME'),
                      getattr(self, 'children', 'No Kids'))
        return 'Part (%s)' % self.type

    # XXX there are multiple problems with project/parent when changing them,
    # we must be very careful whereever we do this.  Should change this api
    # soon.
    def get_project(self):
        return self._project

    def set_project(self, project):
        project = UnwrapObject(project)
        if not project:
            errmsg = "koIPart:set_project called with a null project!"
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, errmsg)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, errmsg)
        if project == self._project:
            return

        self._storeData()
        self._project = project
        if self._parent and self._project is not self._parent._project:
            log.debug("Project changed and is now different than my parents project")
        self._idref = None
        self._restoreData()

    def get_parent(self):
        return self._parent

    def set_parent(self, parent):
        parent = UnwrapObject(parent)
        if parent == self._parent:
            return

        self._idref = None
        self._parent = parent

        if self.id in self._project._prefmap:
            if self._parent:
                self.get_prefset().parent = self._parent.get_prefset()
            else:
                self.get_prefset().parent = None
        if self._parent and self._parent._project and self._project is not self._parent._project:
            self.set_project(self._parent._project)

    def get_prefset(self):
        # if we have a project, always get the pref from the project, otherwise
        # we have our own prefset
        if not self.id in self._project._prefmap:
            prefset = components.classes["@activestate.com/koPreferenceSet;1"] \
                .createInstance(components.interfaces.koIPreferenceSet)
            prefset = UnwrapObject(prefset)
            self.set_prefset(prefset)
            prefset.chainNotifications = 1
        return self._project._prefmap[self.id]

    def set_prefset(self, prefset):
        if self.id in self._project._prefmap:
            oldprefs = self._project._prefmap[self.id]
            oldprefs.removeObserver(self)
            oldprefs.parent = None
            del self._project._prefmap[self.id]
        if prefset:
            prefset.idref = self.id
            prefset.chainNotifications = 1
            self._project._prefmap[self.id] = prefset
            if self._parent:
                prefset.parent = self._parent.get_prefset()
            elif self is self._project:
                prefset.parent = components.classes["@activestate.com/koPrefService;1"].\
                        getService(components.interfaces.koIPrefService).prefs
            elif self._project:
                # XXX FIXME BUG 56887, not necessarily the correct parent
                prefset.parent = self._project.get_prefset()
            prefset.addObserver(self)

    def getIDRef(self):
        # get an idref that points to this part
        if not self._idref:
            if not self.live or not self._parent or not self._parent.live:
                self._idref = self.id
            else:
                pIDRef = self._parent.getIDRef()
                self._idref = "%s/%s" % (pIDRef, self.get_name())
        return self._idref

    # prefs observer
    def observe(self, subject, topic, message):
        #print "project observer %r,%r,%r, %r" % (subject, topic, message, self._project)
        self._project.set_isDirty(1)

    def dump(self, indent):
        print " "*indent + "Part of type '" + self.type +"':"
        print ' '*(indent+1) + "live: %s" % self.live
        print ' '*(indent+1) + "id: %s" % self.id
        print ' '*(indent+1) + "idref: %s" % self.getIDRef()
        if self._parent:
            print ' '*(indent+1) + "parent id: %s" % self._parent.id
            print ' '*(indent+1) + "parent idref: %s" % self._parent.getIDRef()
        else:
            print ' '*(indent+1) + "parent: NONE"
        for k, v in self._attributes.items():
            print ' '*(indent+1) + "%s: %s" % (k, v)
        print ' '*(indent+1) + 'CDATA: %s' % self.value
        prefs = self.get_prefset()
        prefs.dump(indent+1)

    def serialize(self, writer):
        # reset idref every time we serialize.  our children will benefit
        self._idref = None
        do_serialize = not self.live or not self._parent.live
        if not do_serialize and \
            self.live and self._parent.live and hasattr(self, 'children'):
            # if we are not a subdirectory of the parent, we need to be
            # serialized because we were added seperatly
            if hasattr(self, 'get_liveDirectory'):
                me = self.get_liveDirectory()
                p = self._parent.get_liveDirectory()
                do_serialize = not me.startswith(p)
            else:
                do_serialize = 1
        if do_serialize:
            self._serializeHeader(writer)
            self._serializeTail(writer)
        return 1

    def _serializeHeader(self, writer):
        writer.write("<%s " % self.type)
        project = self._project
        attrs = dict(self._attributes) # use a copy of the attributes
        if self.type == 'project' and 'url' in attrs:
            del attrs['url']
        elif project._url:
            # use the relative urls from the tmpattributes if th eurl has not changed
            # because RelativizeURL is SLOW
            if 'url' in attrs:
                if attrs['url']:
                    if 'url' in self._tmpAttributes and self._tmpAttributes['url'] == attrs['url']:
                        attrs['url'] = self._tmpAttributes['relativeurl']
                    else:
                        attrs['url'] = uriparse.RelativizeURL(project._relativeBasedir, attrs['url'])
                if attrs['url'] is None:
                    del attrs['url']
            if self._tmpAttributes.has_key('relativeiconurl'):
                if 'icon' not in attrs:
                    attrs['icon'] = self._tmpAttributes['relativeiconurl']
                else:
                    attrs['icon'] = uriparse.RelativizeURL(project._relativeBasedir, attrs['icon'])

        # get our parents idref
        if self._parent:
            attrs['idref'] = self._parent.getIDRef()
        #else:
        #    print "SERIALIZE [%s][%s][%s] no parent for IDREF" % (self.type, self.get_name(), self.id)
        attributes = []
        for a_name, data in attrs.items():
            if type(data) not in types.StringTypes:
                data = str(data)
            if '\n' in data:
                errmsg = "Illegal newline character in '%s' attribute of "\
                         "%s project item" % (a_name, self.type)
                lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                    .getService(components.interfaces.koILastErrorService)
                lastErrorSvc.setLastError(0, errmsg)
                raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, errmsg)
            # XXX need to decentralize this processing
            attributes.append("%s=%s" % (a_name, quoteattr(data)))
        if attributes:
            attributes.sort()
            writer.write(' '.join(attributes))
        writer.write(">%s"%(newl))
        # write out the CDATA, i.e. self.value
        writer.write(escape(self.value))

    def _serializeTail(self, writer):
        writer.write("</%s>%s" % (self.type,newl))

    def _serializePrefset(self, writer):
        if self.id in self._project._prefmap:
            # unwrap so we can use cStringIO
            prefset = UnwrapObject(self._project._prefmap[self.id])
            # create an idref for this
            prefset.idref = self.getIDRef()
            #prefset.dump(0)
            prefset.serialize(writer, self._project._relativeBasedir)

    def set_name(self, name):
        self._name = name
        if hasattr(self, '_url') and self._url:
            # using lists to make it mutable
            parts = list(urlparse.urlparse(self._url))
            slashlocation = parts[2].rindex('/')
            parts[2] = parts[2][:slashlocation+1] + name
            if parts[2].find('.kpf') < 0:
                parts[2] = parts[2] + '.kpf'
            self._url = urlparse.urlunparse(tuple(parts))
            self._setPathAndName()
        self.setStringAttribute('name', self._name)
        if not self.live:
            self._project.set_isDirty(1)

    def get_name(self):
        if not self._name:
            if self.hasAttribute("name"):
                self._name = self.getStringAttribute("name")
            if self.hasAttribute("url"):
                self._setPathAndName()
        return self._name

    def set_url(self, url):
        # XXX should do URL validation
        self._uri = URIParser()
        self._uri.path = url
        self._url = self._uri.URI
        self.setStringAttribute('url', self._url)
        # Need to do the same checks as set_name.
        self._setPathAndName()
        self._relativeBasedir = self._url[:self._url.rindex('/')+1]
        self.setStringAttribute('name', self._name)
        if not self.live:
            self._project.set_isDirty(1)

    def get_url(self):
        if not self._url and self.hasAttribute('url'):
            self._url = self.getStringAttribute('url')
            self._uri = URIParser()
            self._uri.path = self._url
            self._setPathAndName()
        return self._url

    def _setPathAndName(self):
        if self._uri:
            self._name = self._uri.baseName
            self._path = self._uri.path
        
    def getFile(self):
        # XXX fixme, optmize.  right now this is what forces file status
        # to be retrieved.
        if self.get_url():
            fsvc = components.classes["@activestate.com/koFileService;1"].getService(components.interfaces.koIFileService)
            return fsvc.getFileFromURI(self.get_url())
        return None

    def hasAttribute(self, name):
        return self._attributes.has_key(name)

    def getAttribute(self, name):
        return self._attributes[name]

    def setAttribute(self, name, value):
        if name not in self._attributes or self._attributes[name] != value: # avoid dirtification when possible.
            self._attributes[name] = value
            if not self.live:
                self._project.set_isDirty(1)

    def removeAttribute(self, name):
        if name not in self._attributes: return
        del self._attributes[name]
        if not self.live:
            self._project.set_isDirty(1)

    def getStringAttribute(self, name):
        return unicode(self._attributes[name])

    def setStringAttribute(self, name, value):
        self.setAttribute(name, unicode(value))

    def getLongAttribute(self, name):
        return int(self._attributes[name])

    def setLongAttribute(self, name, value):
        self.setAttribute(name, int(value))

    def getBooleanAttribute(self, name):
        return self.getLongAttribute(name) and 1 or 0

    def setBooleanAttribute(self, name, value):
        self.setAttribute(name, value and 1 or 0)

    def getDragData(self):
        #print "getDragData ",repr(self.value)
        return self.value

    def getDragFlavors(self):
        return self.flavors

    def clone(self):
        return self._clone(self._project)

    def copyToProject(self, project):
        return self._clone(project)

    def _clone(self, project):
        import copy
        # This clone function handles only the basic information that is
        # in every koIPart.  Custom parts that have additional information
        # which needs to be cloned will need to implement their own clone
        # function.  One small example is koIContainer
        dirty = self._project.get_isDirty()
        part = project.createPartFromType(self.type)
        part.type = self.type
        part.value = self.value
        part.live = self.live
        # necessary for packaging projects with relative urls
        part._tmpAttributes = copy.copy(self._tmpAttributes)

        if hasattr(self, '_url') and part.type != 'project':  # we _don't_ want clones of projects to have a URL
            part._url = self._url
        if hasattr(self, '_name'):
            part._name = self._name
        if hasattr(self, '_path'):
            part._path = self._path

        if self.id in self._project._prefmap or self == self._project:
            part.set_prefset(self.get_prefset().clone())

        a_names = self._attributes.keys()
        a_names.sort()
        for a_name in a_names:
            if a_name == 'id': continue # don't copy the id
            data = self.getStringAttribute(a_name)
            part.setStringAttribute(a_name,data)

        self._project.set_isDirty(dirty)
        return part

    def applyKeybindings(self, recurse):
        if not self._project._active:
            return
        if self._attributes.get('keyboard_shortcut', ''):
            try:
                self._getObserverSvc().notifyObservers(self, 'kb-load', self.id)
            except Exception, unused:
                pass
        if recurse and hasattr(self, "children"):
            for child in self.children:
                child.applyKeybindings(recurse)

    def removeKeybindings(self, recurse):
        if not self._project._active:
            return
        if self._attributes.get('keyboard_shortcut', ''):
            try:
                self._getObserverSvc().notifyObservers(self, 'kb-unload', self.id)
            except Exception, unused:
                pass
        if recurse and hasattr(self, "children"):
            for child in self.children:
                child.removeKeybindings(recurse)

    def invoke(self):
        try:
            self._getObserverSvc().notifyObservers(self,
                                                   'part-invoke',
                                                   self.id)
        except Exception, unused:
            pass

    def generateRows(self, generator, nodeIsOpen, sortBy='name', level=0,
                     filterString=None, sortDir=0, childrenOnly=0):

        if not filterString or self.matchesFilter(filterString):
            if self._parent:
                self._parent.ensureRowAdded()
            row = {"level": level,
                   "node": self,
                   "is-open": 0,
                   "is-container": 0,
                   "is-empty": 1,
                   "scoped-name": None
                  }
            generator.addRow(row)
            return 1
        return 0

    def matchesFilter(self, filterString):
        """Returns a boolean indicating if this node matches the filter."""
        return fnmatch.fnmatch(self.get_name(), filterString)

    def getFieldValue(self, fieldname):
        text = ""
        if fieldname in self.properties:
            text = self.properties[fieldname]
        elif self.hasAttribute(fieldname):
            text = self.getStringAttribute(fieldname)
        elif hasattr(self, "get_"+fieldname):
            text = getattr(self, "get_"+fieldname)()
        elif hasattr(self, fieldname):
            text = getattr(self, fieldname)
        else:
            # XXX file should be retrieved from the row node, but we dont
            # have a row node, just a part
            file = UnwrapObject(self.getFile())
            if file and hasattr(file, fieldname):
                text = getattr(file, fieldname)
        return text

    def isAncestor(self, part):
        # is the part my ancestor?
        if not self._parent: return False
        if self._parent == UnwrapObject(part): return True
        return self._parent.isAncestor(part)

def compareNodeFolder(a, b, field):
    a_c = hasattr(a, 'children')
    b_c = hasattr(b, 'children')
    if a_c and not b_c:
        return -1
    elif b_c and not a_c:
        return 1
    return compareNode(a,b,field)

def compareNode(a, b, field):
    aval = a.getFieldValue(field)
    bval = b.getFieldValue(field)
    if isinstance(aval, types.StringTypes):
        return cmp(aval.lower(), bval.lower())
    return cmp(aval, bval)

class koContainerBase(koPart):
    def __init__(self, project):
        koPart.__init__(self, project)
        self.numChildren = 0
        self._sortedBy = None
        self._sortDir = 0
        self.children = []
        self._project._childmap[self.id] = self.children
        self._rowAdded = 1 # gets reset in generateRows

    def getChildren(self):
        return self.children

    def hasChild(self, child):
        return child in self.children

    def isEmpty(self):
        return len(self.children)==0

    def getChildrenByType(self, type, recurse):
        matching_children = []
        for child in self.children:
            if child.type == type:
                matching_children.append(child)
            if recurse and hasattr(child, 'children'):
                matching_children += child.getChildrenByType(type, recurse)
        return matching_children

    def getChildWithTypeAndStringAttribute(self, type, attrname, attrvalue, recurse):
        # This optimization assumes that all koPart implementations are
        # Python objects.  Otherwise we'd need to use getAttribute,
        # which would be much slower.
        for child in self.children:
            if child.type == type\
               and child._attributes.get(attrname,None) == attrvalue:
                return child
            elif recurse and hasattr(child, 'children'):
                c = child.getChildWithTypeAndStringAttribute(type,attrname,attrvalue,recurse)
                if c: return c
        return None

    def getChildrenWithAttribute(self, attrname, recurse):
        children = []
        for child in self.children:
            if attrname in child._attributes:
                children.append(child)
            if recurse and hasattr(child, 'children'):
                c = child.getChildrenWithAttribute(attrname, recurse)
                children = children + c
        return children

    def getChildByAttributeValue(self, attrname, attrvalue, recurse):
        for child in self.children:
            if child._attributes.get(attrname,None) == attrvalue:
                return child
            elif recurse and hasattr(child, 'children'):
                c = child.getChildByAttributeValue(attrname,attrvalue,recurse)
                if c: return c
        return None

    def addChild(self, child):
        child = UnwrapObject(child)
        if child.id in idmap and idmap[child.id] != child:
            log.error("duplicate id in child [%s], reseting id", child.id)
            if 'id' in child._attributes:
                del child._attributes['id']
        if not self.hasChild(child):
            self.children.append(child)

        if child not in self._project._childmap[self.id]:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, "child is not in the project childmap!")

        child.set_parent(self)
        child.set_project(self._project) # this calls the setter
        child.assignId()
        if child.id in child._project._prefmap:
            child.get_prefset().parent = self.get_prefset()

        self._project.set_isDirty(1)
        self._project.registerChildByURL(child)
        if child.type == "file":
            # Let the Code Intelligence system know that a file has been
            # added to one of Komodo's open projects or toolboxes.
            self._getCodeIntelSvc().ideEvent("added_file_to_project",
                                             child.getStringAttribute("url"),
                                             self._project)

        child.applyKeybindings(1)
        child.added()

    _codeIntelSvc = None
    def _getCodeIntelSvc(self):
        if not self._codeIntelSvc:
            self._codeIntelSvc = components.classes["@activestate.com/koCodeIntelService;1"]\
                .getService(components.interfaces.koICodeIntelService);
        return self._codeIntelSvc

    def getChildById(self, id):
        if self.id == id:
            return self
        for child in self.children:
            if child.id == id:
                return child
            if hasattr(child, "getChildById"):
                found = child.getChildById(id)
                if found: return found
        return None

    def get_project(self):
        return self._project

    def set_project(self, project):
        koPart.set_project(self, project)
        # Need to recursively go through the child's children to set the
        # project property.
        for child in self.children:
            child.set_project(project) # This is recursive

    def removeChild(self, child):
        child = UnwrapObject(child)
        self.children.remove(child)

        self._project.set_isDirty(1)
        self._project.forgetChildByURL(child)
        if child.type == "file":
            # Let the Code Intelligence system know that a file has been
            # removed from one of Komodo's open projects or toolboxes.
            self._getCodeIntelSvc().ideEvent("removed_file_from_project",
                                             child.getStringAttribute("url"),
                                             self._project)

        child.removeKeybindings(1)

        previous_parent = child._parent
        child.removed(previous_parent)
        child.destroy()

    def removed(self, my_previous_parent):
        # now we need to look at our children, and remove any menu's or toolbars
        needRemoved = [child for child in \
                       self.getChildrenByType('toolbar', 1) + \
                       self.getChildrenByType('menu', 1)]
        for child in needRemoved:
            child.removed(child._parent)

    def _clone(self, project):
        part = koPart._clone(self, project)
        for child in self.children:
            part.addChild(child._clone(project))
        return part

    def dump(self, indent):
        koPart.dump(self, indent)
        for child in self.children:
            child.dump(indent+2)

    def ensureRowAdded(self):
        if not self._rowAdded:
            if self._parent:
                self._parent.ensureRowAdded()
            self._generator.addRow(self._row)
            self._rowAdded = 1

    def generateRows(self, generator, nodeIsOpen, sortBy='name', level=0,
                     filterString=None, sortDir=0, childrenOnly=0):
        if not hasattr(self, "children"):
            return None

        self._row = {"level": level,
               "node": self,
               "file": self.getFile(),
               "is-open": nodeIsOpen.get(self.id,childrenOnly),
               "is-container": 1,
               "is-empty": 0, # assume it's not empty for now
               "scoped-name": None
              }
        # if we're only adding our children, mark ourselves already added
        self._rowAdded = childrenOnly
        self._generator = generator
        childrenAdded = 0
        if filterString or self._row["is-open"]:
            self._filterString = filterString
            children = self.getChildren()[:]
            self._filterString = None
            numChildren = len(children)
            hasChildren = numChildren > 0

            self._row["is-empty"] = not hasChildren
            if children:
                self._sortNodes(children, sortBy, sortDir)

            for i in range(numChildren):
                child = children[i]
                if generator.stopped():
                    return 0
                if not filterString or hasattr(child, 'children') or child.matchesFilter(filterString):
                    childrenAdded = child.generateRows(generator, nodeIsOpen, sortBy, level+1,
                                          filterString=filterString,
                                          sortDir=sortDir)

        if generator.stopped():
            return 0
        if not self._rowAdded and (not filterString or self.matchesFilter(filterString)):
            self.ensureRowAdded()
        self._generator = None
        return self._rowAdded or childrenAdded

    def _sortNodes(self, nodes, sortBy, sortDir):
        if sortDir != 0:
            nodes.sort(lambda a,b: compareNodeFolder(a, b, sortBy) * sortDir)
        else:
            nodes.sort(lambda a,b: compareNode(a, b, sortBy))

class koContainer(koContainerBase):
    def __init__(self, project):
        koContainerBase.__init__(self, project)

# See factory function below
class koFilePart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_file]
    type = 'file'
    prettytype = 'File'
    _iconurl = 'chrome://komodo/skin/images/file_icon.png'
    primaryInterface = 'koIPart_file'

    def __init__(self, project):
        koPart.__init__(self, project)
        self.flavors.insert(0,'text/x-moz-url')

    def __str__(self):
        return "<koPart_file, url=%s>" % self._attributes.get('url', 'None')

    def __repr__(self):
        return "<koFilePart %s (id=%r)>" % (
            self._attributes.get("name"), self._attributes["id"])

    def getDragData(self):
        return self.getStringAttribute('url')

def File(url, name, project):
    """Construct a 'file' koIPart."""
    assert project is not None
    part = koFilePart(project)
    part._attributes['url'] = url
    part._attributes['name'] = name
    return part

def ProjectShortcut(url, name, project):
    """Construct a 'file' koIPart."""
    assert project is not None
    part = koProjectRef(project)
    part._attributes['url'] = url
    part._attributes['name'] = name
    return part

def unescapeWhitespace(text, eol="\n"):
    newtext = u'' # THE u IS IMPORTANT!
    i = 0
    while i < len(text):
        if text[i] == '\\':
            i += 1
            if text[i] == 'n':
                newtext += eol
            elif text[i] == 't':
                newtext += '\t'
            elif text[i] == '\\':
                newtext += '\\'
            else:
                i -= 1
                newtext += '\\'
        else:
            newtext += text[i]
        i += 1
    return newtext

class koSnippetPart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_snippet]
    type = 'snippet'
    prettytype = 'Snippet'
    _iconurl = 'chrome://komodo/skin/images/snippet.png'
    primaryInterface = 'koIPart_snippet'
    keybindable = 1

    def get_url(self):
        # build a macro url
        return "snippet://%s/%s" % (self.id, self.get_name())

    def getDragData(self):
        # NOTE: IT IS IMPORTANT THAT IF UNICODE COMES IN, UNICODE GOES OUT!
        newtext = self.value
        anchor = newtext.find(ANCHOR_MARKER)
        if anchor != -1:
            newtext = newtext[:anchor] + newtext[anchor+len(ANCHOR_MARKER):]
        currentPos = newtext.find(CURRENTPOS_MARKER)
        if currentPos != -1:
            newtext = newtext[:currentPos] + newtext[currentPos+len(CURRENTPOS_MARKER):]
        # it would be good to interpolate here as well!
        isvc = components.classes["@activestate.com/koInterpolationService;1"]\
                .getService(components.interfaces.koIInterpolationService);
        psvc = components.classes["@activestate.com/koPartService;1"]\
                .getService(components.interfaces.koIPartService)
        psvc = UnwrapObject(psvc)
        toolbox = sharedToolbox = None
        if psvc._toolbox:
            toolbox = UnwrapObject(psvc._toolbox)
        if psvc._toolbox:
            sharedToolbox = UnwrapObject(psvc._sharedToolbox)
        # get additional interpolation data
        projectFile = None
        project = self.get_project()
        if project in [toolbox, sharedToolbox]:
            if psvc._currentProject:
                projectFile = psvc._currentProject.getFile().path
                prefset = psvc._currentProject.prefset
            else:
                prefset = self.get_prefset()
        else:
            projectFile = project.getFile().path
            prefset = self.get_prefset()
        try:
            queries, strings = isvc.Interpolate1([], # not bracketed
                                                  [newtext], # bracketed
                                                  None,  #filename
                                                  0, #linenum
                                                  None, #word
                                                  None, #selection
                                                  projectFile, #projectFile
                                                  prefset, #prefSet: use global prefs
                                                  )
        except Exception, e: # If e.g. %w is in the snippet, we ignore all % codes.
            log.exception(e)
            return newtext

        for query in queries:
            if query.answer == None:
                # if any of the interpolations required a question,
                # do _no_ conversion and return the full %-laden snippet
                return newtext
        if queries:
            strings = isvc.Interpolate2(strings, queries)

        return strings[0]

class koCommandPart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_command]
    type = 'command'
    prettytype = 'Run Command'
    _iconurl = 'chrome://komodo/skin/images/run_commands.png'
    primaryInterface = 'koIPart_command'
    keybindable = 1

class koTemplatePart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_template]
    type = 'template'
    prettytype = 'Template'
    _iconurl = 'chrome://komodo/skin/images/newTemplate.png'
    primaryInterface = 'koIPart_template'

class koURLPart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_URL]
    type = 'URL'
    prettytype = 'URL'
    _iconurl = 'chrome://komodo/skin/images/xlink.png'
    keybindable = 1
    primaryInterface = 'koIPart_URL'

class koMacroPart(koPart):
    _com_interfaces_ = [components.interfaces.koIPart_macro]
    type = 'macro'
    prettytype = 'Macro'
    _iconurl = 'chrome://komodo/skin/images/macro.png'
    primaryInterface = 'koIPart_macro'
    keybindable = 1

    def __init__(self, project):
        koPart.__init__(self, project)
        self.flavors.insert(0,'text/x-moz-url')
        self._attributes['language'] = 'JavaScript'  # default.

    def get_url(self):
        # build a macro url
        # hack for extension so buffers get the correct language:
        ext = ""
        if self._attributes['language'] == 'JavaScript':
            ext = ".js"
        elif self._attributes['language'] == 'Python':
            ext = ".py"
        if self._project:
            return "macro://%s/%s/%s%s" % (self.id, self._project.get_name(),
                                           self.get_name(), ext)
        return "macro://%s/%s%s" % (self.id, self.get_name(), ext)

    def added(self):
        # if we're an old-style macro, convert us to new style
        if self.hasAttribute('filename'):
            # need to upgrade
            fname = self.getAttribute('filename')
            if not os.path.exists(fname):
                log.warn("Couldn't find the file %r referred to by a macro", fname)
                return
            registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                                         getService(components.interfaces.koILanguageRegistryService)
            language = registryService.suggestLanguageForFile(os.path.basename(fname))
            try:
                file = open(fname, 'r')
                self.value = file.read()
                file.close()
                self.setAttribute('language', language)
                self.setAttribute('version', '2')
                self.setBooleanAttribute('do_trigger', 0)
                self.setLongAttribute('rank', 100)
                self.setBooleanAttribute('trigger', 'trigger_presave')
                self.removeAttribute('filename') # ADD when removeAttribute is added
            except OSError:
                log.warn("Couldn't read the macro: %r, skipping conversion", fname)
                return
        if not self._project._quiet:
            try:
                self._getObserverSvc().notifyObservers(self,'macro-load','')
            except:
                pass # no listener
        koPart.added(self)

    def removed(self, previous_parent):
        try:
            self._getObserverSvc().notifyObservers(self, 'macro-unload', '')
        except:
            pass # no listener
        koPart.removed(self, previous_parent)

    def _asyncMacroCheck(self, async):
        if async:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                .getService(components.interfaces.koILastErrorService)
            err = "Asynchronous python macros not yet implemented"
            lastErrorSvc.setLastError(1, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

    def evalAsPython(self, domdocument, window, scimoz, document,
                     view, code, async):
        self._asyncMacroCheck(async)
        evalPythonMacro(WrapObject(self,self._com_interfaces_[0]),
                        domdocument, window, scimoz, document, view, code)
        
    def evalAsPythonObserver(self, domdocument, window, scimoz, document,
                             view, code, async, subject, topic, data):
        self._asyncMacroCheck(async)
        evalPythonMacro(WrapObject(self,self._com_interfaces_[0]),
                        domdocument, window, scimoz, document, view, code,
                        subject, topic, data)

# See factory functions below
class koWebServicePart(koURLPart):
    _com_interfaces_ = [components.interfaces.koIPart_URL,
                        components.interfaces.koIPart_webservice]
    type = 'webservice'
    prettytype = 'Web Service Shortcut'
    _iconurl = 'chrome://komodo/skin/images/webServicesImg.png'
    primaryInterface = 'koIPart_URL'

    def __init__(self, project):
        koPart.__init__(self, project)
        self._attributes['wsdl'] = ''

    def hasAttribute(self, name):
        if name.lower() == 'url':
            return 'wsdl' in self._attributes
        return name in self._attributes

    def get_value(self):
        return unicode(self._attributes['wsdl'])

    def getStringAttribute(self, name):
        if name.lower() == 'url':
            return unicode(self._attributes['wsdl'])
        return unicode(self._attributes[name])

    def setStringAttribute(self, name, value):
        if name.lower() == 'url':
            name = 'wsdl'
        self.setAttribute(name, unicode(value))

    def getDragData(self):
        return self.getStringAttribute('wsdl')


class koMenuPart(koContainer):
    _com_interfaces_ = [components.interfaces.koIPart_menu]
    type = 'menu'
    prettytype = 'Custom Menu'
    _iconurl = 'chrome://komodo/skin/images/menu_icon.png'
    _added = 0
    primaryInterface = 'koIPart_menu'

    def __init__(self, project):
        koContainer.__init__(self, project)
        self._attributes['accesskey'] = ''
        self._attributes['priority'] = 100
        self._added = 0

    def setAttribute(self, name, value):
        koContainer.setAttribute(self, name, value)
        if self._added and not self._project._quiet and self._project._active:
            try:
                self._getObserverSvc().notifyObservers(self, 'menu_changed', 'attribute changed')
            except:
                pass # no listener

    def added(self):
        if self._added:
            return
        self._added = 1
        if self._project._quiet or not self._project._active:
            return
        try:
            self._getObserverSvc().notifyObservers(self, 'menu_create', 'menu_create')
        except:
            pass # no listener
        koContainer.added(self)

    def removed(self, previous_parent):
        if not self._added:
            return
        self._added = 0
        if self._project._quiet or not self._project._active:
            return
        try:
            self._getObserverSvc().notifyObservers(self, 'menu_remove', 'menu_remove')
        except:
            pass # no listener
        koContainer.removed(self, previous_parent)

    def getDragData(self):
        return self.getStringAttribute('name')


class koToolbarPart(koContainer):
    _com_interfaces_ = [components.interfaces.koIPart_toolbar]
    type = 'toolbar'
    prettytype = 'Custom Toolbar'
    _iconurl = 'chrome://komodo/skin/images/toolbar_icon.png'
    primaryInterface = 'koIPart_toolbar'

    def __init__(self, project):
        koContainer.__init__(self, project)
        self._added = 0
        self._attributes['priority'] = 100

    def setAttribute(self, name, value):
        koContainer.setAttribute(self, name, value)
        if self._added and not self._project._quiet and self._project._active:
            try:
                self._getObserverSvc().notifyObservers(self, 'toolbar_changed', 'attribute changed')
            except:
                pass # no listener

    def added(self):
        if self._added:
            return
        self._added = 1
        if self._project._quiet or not self._project._active:
            return
        # we've been created, we need to tell the JS side of things
        # that we exist.
        try:
            self._getObserverSvc().notifyObservers(self, 'toolbar_create', 'toolbar_create')
        except:
            pass # no listener
        koContainer.added(self)

    def removed(self, previous_parent):
        if not self._added:
            return
        self._added = 0
        if self._project._quiet or not self._project._active:
            return
        try:
            self._getObserverSvc().notifyObservers(self, 'toolbar_remove', 'toolbar_remove')
        except:
            pass # no listener
        koContainer.removed(self, previous_parent)

    def getDragData(self):
        return self.getStringAttribute('name')


# See factory functions below
class koFolderPart(koContainer):
    _com_interfaces_ = [components.interfaces.koIPart_folder]
    type = 'folder'
    prettytype = 'Folder'
    _iconurl = 'chrome://komodo/skin/images/folder-closed.png'
    primaryInterface = 'koIPart_folder'

    def __repr__(self):
        return "<koFolderPart %s (%d children, id=%r)>" % (
            self._attributes.get("name"), len(self.children),
            self._attributes["id"])

    def getLanguageFolder(self, language):
        for child in self.children:
            if child.hasAttribute('language') and child.getStringAttribute('language') == language:
                return child
        languagefolder = Folder('', language, self._project)
        languagefolder.setStringAttribute('language', language)
        self.addChild(languagefolder)
        return languagefolder

    ##
    # We want to get (or create, if necessary) the folder structure that
    # corresponds to the difference between basedir and targetdir.
    # e.g. if baseuri is:    file:///c:/foo/bar
    #      and targetdir is: file:///c:/foo/bar/baz/fob
    # we want to return a fob Folder inside a bar Folder, which itself would be
    # added to self.
    #
    # @baseuri {string} Base path for import folder
    # @targeturi {string} Directory path we are targeting
    #
    def getDirFolder(self, baseuri, targeturi):
        #print "getDirFolder: baseuri:%r, targeturi:%r" % (baseuri, targeturi)
        if not targeturi.startswith(baseuri):
            log.error("getDirFolder called with invalid arguments: %s, %s" % (baseuri, targeturi))
            return None
        trail = targeturi[len(baseuri):]
        folder = self
        if trail:
            path = baseuri
            parts = trail.split("/")
            for part in parts:
                if not part:
                    continue
                path = "%s/%s" % (path, part)
                url = path
                for child in folder.children:
                    if child.hasAttribute('url') and child.getStringAttribute('url') == url:
                        folder = child
                        break
                else:
                    newfolder = Folder(url, part, self._project, self.live)
                    folder.addChild(newfolder)
                    folder = newfolder
        return folder

    def getDragData(self):
        if self.hasAttribute('url'):
            return self.getStringAttribute('url');
        return self.getStringAttribute('name');

    def getDragFlavors(self):
        if self.hasAttribute('url') and self.flavors[0] != 'text/x-moz-url':
            self.flavors.insert(0,'text/x-moz-url')
        return self.flavors

    def genLocalPaths(self):
        """Generate all contained local paths."""
        for child in self.getChildren():
            type = child.type
            name = child.getStringAttribute("name")
            if type == "file":
                url = child.getStringAttribute("url")
                path = _local_path_from_url(url)
                if path is not None:
                    yield path
            elif type in ("folder", "livefolder"):
                for path in child.genLocalPaths():
                    yield path


class koLiveFolderPart(koFolderPart):
    _com_interfaces_ = [components.interfaces.koIPart_livefolder,
                        components.interfaces.koIPart_folder]
    type = 'livefolder'
    prettytype = 'Live Folder'
    _iconurl = 'chrome://komodo/skin/images/folder-closed-blue.png'
    primaryInterface = 'koIPart_livefolder'

    def __init__(self, project):
        koFolderPart.__init__(self, project)
        self.live = 1
        self.needrefresh = 1
        self._lastfetch = set([])

    def __repr__(self):
        return "<koLiveFolderPart %s (%d children, id=%r)>" % (
            self._attributes.get("name"), len(self.children),
            self._attributes["id"])

    # prefs observer
    def observe(self, subject, topic, message):
        koFolderPart.observe(self, subject, topic, message)
        # now, if one of our import properties has changed, lets update
        prefs = self.get_prefset()
        if UnwrapObject(subject) is not prefs:
            return
        #print "livefolder got notified of change [%s][%s][%s]"%(subject,topic, message)
        #print "livefolder change in project %s" % self._project.get_name()
        if message == "import_live":
            self.live = prefs.getBooleanPref("import_live")
            #print "  change our live status to %d" % self.live
            self.needrefresh = 1
            if not self.live:
                undead = self._removeLiveChildrenRecursive()
                # bring the undead back to life
                for child in undead:
                    if child in self.children:
                        continue
                    self.addChild(child)
        elif message == "import_dirname":
            self._removeLiveChildrenRecursiveSaveUnded()
            self.needrefresh = 1
        elif message in ["import_include_matches",
                       "import_exclude_matches"]:
            self.needrefresh = 1

    def _removeLiveChildrenRecursiveSaveUnded(self):
        undead = self._removeLiveChildrenRecursive()
        # bring the undead back to life
        for child in undead:
            if child in self.children:
                continue
            self.addChild(child)

    def _removeLiveChildrenRecursive(self):
        undead = []
        for child in self.children[:]:
            if child.live:
                if hasattr(child, '_removeLiveChildrenRecursive'):
                    undead += child._removeLiveChildrenRecursive()
                self.removeChild(child)
            else:
                undead.append(child)
        return undead

    def _differentImportPrefs(self, child):
        cprefs = child.get_prefset()
        prefs = self.get_prefset()
        if prefs.getStringPref("import_include_matches") != \
            cprefs.getStringPref("import_include_matches"):
            return 0
        if prefs.getStringPref("import_exclude_matches") != \
            cprefs.getStringPref("import_exclude_matches"):
            return 0
        return 1

    def get_liveDirectory(self):
        prefs = self.get_prefset()
        try:
            path = None
            if prefs.hasPrefHere("import_dirname"):
                path = prefs.getStringPref("import_dirname")
            if not path:
                if not self._uri:
                    # Has the side-effect of setting `self._uri` and
                    # `self._url` from `_attributes["url"]`.
                    self.get_url()
                if not self._path:
                    self._setPathAndName()
                if self._project == self:
                        path = os.path.dirname(self._path)
                else:
                    path = self._path
            return path
        except:
            # self.file doesn't exist, so don't import anything
            pass
        return None

    def refreshChildren(self):
        config = self._getImportConfig()
        self._updateLiveChildren(config)

    def _getImportConfig(self, recursive=0, type="makeFlat"):
        prefs = self.get_prefset()
        include = prefs.getStringPref("import_include_matches")
        # perf improvement for tree filtering
        if self._filterString:
            if not include:
                include = self._filterString
            else:
                include = "%s;%s" % (include, self._filterString)
        exclude = prefs.getStringPref("import_exclude_matches")
        if self._project == self:
            # add project kpf to exclude
            exclude = "%s;%s" % (exclude, self._name)

        # XXX in prep for combining livefolder and folder parts
        if not self.live:
            recursive = prefs.getBooleanPref("import_recursive")
            type = prefs.getStringPref("import_type")
        path = self.get_liveDirectory()
        return include, exclude, recursive, type, path
        
    # live folders are *always* non-recursive on the import, defaults for this
    # are for live folders.  They are used from the package service to do
    # a recursive import of live folders when packaging a project
    def _updateLiveChildren(self, config):
        #print "refreshChildren for %s:%s - %r" % (self.type,self.get_name(), config)
        forcerefresh = self.needrefresh
        self.needrefresh = 0
        include = config[0]
        exclude = config[1]
        recursive = config[2]
        type = config[3]
        path = config[4]
        if not path:
            return

        # perf improvement for tree filtering
        if self._filterString:
            # always refresh on the next retreival of children
            forcerefresh = self.needrefresh = 1

        #print "refreshChildren for %s:%s" % (self.type,self.get_name())
        #print "                %s:%s:%s" % (include,exclude,path)

        importService = components.classes["@activestate.com/koFileImportingService;1"].\
                        getService(components.interfaces.koIFileImportingService)
        filenames = set(importService.findCandidateFiles(self, path, include, exclude, recursive))
        if not forcerefresh and self._lastfetch and not self._lastfetch.symmetric_difference(filenames):
            #print "bail early, no change in children"
            return

        isDirty = self._project.get_isDirty()
        self._lastfetch = filenames
        # for live folders, remove live parts that are not in filenames list,
        # add anything in filenames list that is not in our child list
        newfiles = []
        oldparts = []
        if not filenames:
            # XXX - Only remove the child nodes, ToddW (r=sc).
            # http://bugs.activestate.com/show_bug.cgi?id=48098
            oldparts = [p for p in self.children if p is not self and p.live]
        else:
            for part in self._project._urlmap.values():
                fname = part._path
                if (recursive and fname[:len(path)] == path) or \
                    (not recursive and os.path.dirname(fname) == path):
                    if fname not in filenames:
                        oldparts.append(part)
            for name in filenames:
                name = os.path.abspath(name)
                url = uriparse.localPathToURI(name)
                if not self._project._urlmap.get(url, None):
                    newfiles.append(name)

        # XXX here, for non-live folders, we need to display a dialog for the
        # user to select which files they want to import
        removeMissingFiles = 0 # XXX get this from the dialog

        if self.live or removeMissingFiles:
            for part in oldparts:
                # XXX what to do with non-live children of live folders?
                parent = part.get_parent()
                if parent:
                    parent.removeChild(part)

        #print "adding Filenames", filenames
        if newfiles:
            importService.addSelectedFiles(self, type, path, newfiles)
        if self.live:
            # reset the dirty state to what it was before the refresh if
            # we are live.
            self._project.set_isDirty(isDirty)

    def getChildren(self):
        # XXX for now, always refresh since we only watch folders that are
        # opened in the project view
        #if self.needrefresh and self.live:
        if self.live:
            self.refreshChildren()
        return self.children

    def genLocalPaths(self):
        """Generate all contained local paths.

        Limitations:
        - Komodo currently allows the import_* prefs in a live folder
          tree to *change at any level* in the tree. This currently
          isn't supported here. Either it should be or Komodo's projects
          should disallow this facility.
        
        TODO: Most of this implementation is identical to
              `koProject.genLocalPaths`. They should share.
        """
        from os.path import join, dirname, basename
        
        # `self._childmap`, unfortunately mixes in "live" children with
        # "static" ones. E.g.:
        #   Project foo.kpf (live):
        #       File foo.txt (in foo.kpf's live import)
        #       File bar.txt (*not* in foo.kpf's live import, added manually)
        # So, we'll track the immediate children that we've yielded here
        # to ensure we don't emit the same one twice.
        already_yielded_child_name_set = set()

        # Handle live elements.
        # Need to do the live bits first, because these are used to
        # distinguish if elements from `self._childmap` are live or
        # static.
        prefset = self.get_prefset()
        is_live = (prefset.hasBooleanPref("import_live")
                   and prefset.getBooleanPref("import_live"))
        if is_live:
            base_dir = self.get_liveDirectory()
            recursive = prefset.getBooleanPref("import_recursive")
            excludes = [p for p in prefset.getStringPref("import_exclude_matches").split(';') if p]
            includes = [p for p in prefset.getStringPref("import_include_matches").split(';') if p]
            excludes.append("*.kpf")  # Live folders always exclude .kpf files.
            if recursive:
                path_patterns = [base_dir]
            else:
                path_patterns = [join(base_dir, "*"),
                                 join(base_dir, ".*")]
            
            base_dir_length = len(base_dir)
            for path in paths_from_path_patterns(
                    path_patterns,
                    recursive=recursive,
                    includes=includes,
                    excludes=excludes,
                    on_error=None,
                    follow_symlinks=True,
                    skip_dupe_dirs=False):
                sep_idx = path.find(os.sep, base_dir_length+1)
                if sep_idx == -1:
                    already_yielded_child_name_set.add(basename(path))
                else:
                    already_yielded_child_name_set.add(path[base_dir_length+1:sep_idx])
                yield path

        # Handle all "static" elements added to the project.
        childmap = self._project._childmap  #WARNING: accessing internal `_childmap`
        id = self._attributes["id"]
        for child in childmap[id]:
            name = child.getStringAttribute("name")
            type = child.type
            if type == "file":
                if name in already_yielded_child_name_set:
                    continue
                url = child.getStringAttribute("url")
                if not url.startswith("file://"):
                    # Only want local files.
                    continue
                yield _local_path_from_url(url)
            elif type == "folder":
                for path in child.genLocalPaths():
                    yield path
            elif type == "livefolder":
                if name in already_yielded_child_name_set:
                    # Komodo projects allow groups (aka static folders)
                    # in a live folder. If so, this shows up in
                    # `self._childmap`. We walk the child map to see
                    # if there are <koFolderPart>s under this tree.
                    #
                    # Note: We are punting on looking for static files
                    # and separate live folder bases under this live
                    # folder. Komodo projects *allow* these, but they
                    # shouldn't: it is crazy.
                    descendant_ids_to_trace = [child.getStringAttribute("id")]
                    while descendant_ids_to_trace:
                        descendant_id = descendant_ids_to_trace.pop()
                        if descendant_id not in childmap:
                            continue
                        for c in childmap[descendant_id]:
                            t = c.type
                            if t == "folder":
                                for path in c.genLocalPaths():
                                    yield path
                            elif t == "livefolder":
                                descendant_ids_to_trace.append(
                                    c.getStringAttribute("id"))
                else:
                    for path in child.genLocalPaths():
                        yield path


def Folder(url, name, project, live=0):
    """Construct a koIPart_folder from URL and name."""
    assert project is not None
    if live:
        part = koLiveFolderPart(project)
    else:
        part = koFolderPart(project)
    part._attributes['url'] = url
    part._attributes['name'] = name
    return part

class koProjectRef(koFilePart):
    _com_interfaces_ = [components.interfaces.koIPart_ProjectRef]
    type = 'ProjectRef'
    prettytype = 'Project Shortcut'
    _iconurl = 'chrome://komodo/skin/images/project_icon.png'
    primaryInterface = 'koIPart_ProjectRef'

class koDirectoryShortcut(koPart):
    _com_interfaces_ = [components.interfaces.koIDirectoryShortcut]
    type = 'DirectoryShortcut'
    prettytype = 'Open... Shortcut'
    keybindable = 1
    _iconurl = 'chrome://komodo/skin/images/open.png'
    primaryInterface = 'koIDirectoryShortcut'

    def _setPathAndName(self):
        if self._uri:
            self._name = self._path = self._uri.path

    def get_name(self):
        return self._name

class koToolbox(koPart):
    _com_interfaces_ = [components.interfaces.koIToolbox]
    type = 'Toolbox'

class koUnknown(koPart):
    _com_interfaces_ = [components.interfaces.koIPart]
    type = 'Unknown'

class koProject(koLiveFolderPart):
    _com_interfaces_ = [components.interfaces.koIProject,
                        components.interfaces.koIPart_livefolder,
                        components.interfaces.koIPart_folder]
    _reg_desc_ = "Komodo Project"
    _reg_contractid_ = "@activestate.com/koProject;1"
    _reg_clsid_ = "{39EE799F-D0F5-4b2d-A5A6-34151B2AC235}"
    type = 'project'
    prettytype = 'Project'
    _iconurl = 'chrome://komodo/skin/images/project_icon.png'
    primaryInterface = 'koIProject'
    _partSvc = None

    def __init__(self):
        self._isDirty = 0
        self._urlmap = weakref.WeakValueDictionary()
        # child map is a mapping of idrefs to child parts.  a part get's it's own
        # idref, then looks here for it's children
        self._childmap = {}

        # pref map is a mapping of idrefs to prefsets
        # a part get's it's own idref, then looks here to get it's prefset
        self._prefmap = {}


        self._project = self # cycle - need to investigate WeakReference
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)


        self._quiet = 0
        self._dontoverwrite = 0

        # call parent init after we setup anything that is needed by other
        # init funcs.
        koLiveFolderPart.__init__(self, self)
        self._active = 0

        prefset = components.classes["@activestate.com/koPrefService;1"].\
                                getService(components.interfaces.koIPrefService).prefs
        # global pref defines if projects are live or not when created
        self.live = prefset.getBooleanPref("import_live")

        if not self._partSvc:
            self._partSvc = components.classes["@activestate.com/koPartService;1"]\
                .getService(components.interfaces.koIPartService)

    def __repr__(self):
        curr_str = self._active and "current, " or ""
        prefset = self.get_prefset()
        is_live = (prefset.hasBooleanPref("import_live")
                   and prefset.getBooleanPref("import_live"))
        live_str = is_live and "live, " or ""
        return "<koProject %s (%s%s%d children, id=%r)>" % (
            self._attributes.get("name"), curr_str, live_str,
            len(self.children), self._attributes["id"])

    def isCurrent(self):
        return self._active

    def serialize(self, writer):
        # previous versions (3.x) did not force the KPF version,
        # we need to do that to allow correct upgrade/downgrade
        # of future kpf versions
        self._attributes['kpf_version'] = KPF_VERSION
        # for projects, everything is a child
        self._serializeHeader(writer)
        # serialize all children and prefs we know about, because we don't want
        # to lose our orphans (children in live folders that have not been
        # opened).
        for idref in sorted(self._childmap):
            try:
                children = self._childmap[idref]
            except KeyError:
                continue
            for child in sorted(children, key=operator.attrgetter('id')):
                child.serialize(writer)
                
        for idref in sorted(self._prefmap):
            # unwrap so we can use cStringIO
            try:
                prefset = UnwrapObject(self._prefmap[idref])
            except KeyError:
                continue
            if not hasattr(prefset,'idref'):
                prefset.idref = idref
            prefset.serialize(writer, self._relativeBasedir)

        self._serializeTail(writer)

    # Fill with a new empty, unnamed project
    def create(self):
        self._name = _makeNewProjectName()
        self.setLongAttribute("kpf_version", KPF_VERSION)

        # force the import_live pref so we can get children when
        # we're saved
        prefset = self.get_prefset()
        self.live = prefset.getBooleanPref("import_live")
        prefset.setBooleanPref("import_live", self.live)

    def createPartFromType(self, type):
        # we create the koPart instance and return it
        return createPartFromType(type, self)

    def clone(self):
        project = koProject()
        project.create()
        return self._clone(project)

    def _get_stream(self, path, mode):  # mode is 'r' or 'w'
        self.name = os.path.splitext(os.path.basename(path))[0]
        stream = components.classes["@activestate.com/koLocalFile;1"].\
             createInstance().QueryInterface(components.interfaces.koILocalFile)
        try:
            stream.init(path, mode)
        except (IOError, COMException), e:
            errstr = "Can't open project file %s because %s" % (path, e)
            log.error(errstr)
            raise
        return stream

    def set_isDirty(self, dirty):
        if self._isDirty != dirty:
            self._isDirty = dirty
            try:
                self._getObserverSvc().notifyObservers(self,'update-commands','projectsChanged')
            except:
                pass # no listener

    def get_isDirty(self):
        return self._isDirty

    def loadFromString(self, data, url):
        self.lastErrorSvc.setLastError(0, '')
        self.set_url(url)
        assert self._url
        assert self._relativeBasedir
        fname = uriparse.URIToLocalPath(self._url)
        # load into a stream that can be used for parsing
        import StringIO
        self._parseStream(StringIO.StringIO(data), url, fname)

    def loadQuiet(self, url):
        self._quiet = 1
        self.load(url)
        self._quiet = 0

    def load(self, url):
        self.lastErrorSvc.setLastError(0, '')
        self.set_url(url)
        assert self._url
        assert self._relativeBasedir
        fname = uriparse.URIToLocalPath(self._url)
        if not os.path.exists(fname):
            err = 'File does not exist.'
            self.lastErrorSvc.setLastError(0, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

        stream = self._get_stream(fname, 'r')
        self._parseStream(stream, url, fname)

    def _parseStream(self, stream, url, fname):
        t1 = time.clock()
        # part is our 'current part' that we are working on
        # we need to have this so we can add prefsets to them
        # as they pass by
        part = self
        # partstack is a list of parts by depth.  It will never have more
        # than one item if it is KPF Ver3
        partstack = []
        idlist = {} # duplicate id tracker
        # our current level of depth
        level = 0
        prefpart_id = None

        # reset to a non-live project if we're loading.  We only become live
        # if the projet has a pref to make us live
        self.live = 0

        dirtyAtEnd = 0
        events = pulldom.parse(stream)
        kpfVer = 0
        keybound_parts = []  # list of parts that have keybindings
        for (event, node) in events:
            if event == pulldom.START_ELEMENT:
                if node.tagName == 'project':
                    # assuming this is hapening in koIProject we need to
                    # add attributes to self
                    for attribute, value in node.attributes.items():
                        self._attributes[attribute] = value
                    #if 'id' in self._attributes:
                    #    print "   project id is now [%s]"%self._attributes['id']
                    self.assignId()
                    #check the kpf version number
                    if 'kpf_version' in self._attributes:
                        try:
                            kpfVer = int(self._attributes['kpf_version'])
                        except ValueError, e:
                            kpfVer = 1
                    else:
                        kpfVer = 1 # k 1.x-2.x
                    if kpfVer < KPF_VERSION:
                        # backup the kpf
                        try:
                            bakFile = fname # in case the following lines fail for some reason
                            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
                            basename = os.path.basename(fname)
                            bakFile = os.path.join(koDirSvc.userDataDir, "%s.%s.bak" % (basename,time.time()))
                            msg = "Komodo is reading a KPF file version %d and is " \
                                  "converting it to version %d: [%s], a backup " \
                                  "will be created at [%s]." % (kpfVer, KPF_VERSION, fname, bakFile)
                            wwatch = components.classes["@mozilla.org/embedcomp/window-watcher;1"].getService(components.interfaces.nsIWindowWatcher)
                            prompt = wwatch.getNewPrompter(wwatch.activeWindow)
                            prompt.alert("Project Upgrade Warning", msg)
                            log.warn(msg)
                            self.lastErrorSvc.setLastError(0, msg)

                            shutil = components.classes["@activestate.com/koShUtil;1"].\
                                        getService(components.interfaces.koIShUtil)
                            shutil.copyfile(fname, bakFile)
                        except Exception, e:
                            log.exception("Error '%s' creating backup of '%s'", e, bakFile)
                        self._attributes['kpf_version'] = KPF_VERSION
                        dirtyAtEnd = 1
                    elif kpfVer > KPF_VERSION:
                        basename = os.path.basename(fname)
                        msg = "Komodo is reading a KPF file [%s] created by a newer " \
                              "version of Komodo, you will not be able to overwrite " \
                              "this KPF file.  Some functionality may be lost." % (basename,)
                        wwatch = components.classes["@mozilla.org/embedcomp/window-watcher;1"].getService(components.interfaces.nsIWindowWatcher)
                        prompt = wwatch.getNewPrompter(wwatch.activeWindow)
                        prompt.alert("Project Load Error", msg)
                        log.error(msg)
                        self.lastErrorSvc.setLastError(0, msg)
                        self._dontoverwrite = 1

                    partstack.append(self)

                elif node.tagName == "preference-set":
                    # make a dom for the prefset, turn it into a prefset
                    events.expandNode(node)
                    prefset = UnwrapObject(NodeToPrefset(node, self._relativeBasedir, 1))

                    if kpfVer < 3 or \
                        not prefset.idref:
                        # we only get here with 3.x projects, 4.x projects
                        # should always have the idref.  In this case, the idref
                        # is the part id
                        dirtyAtEnd = 1
                        prefset.idref = part.id

                    if prefset.hasPrefHere("mappedPaths"):
                        upgradeutils.upgrade_mapped_uris_for_prefset(prefset)

                    prefset.addObserver(self)
                    self._prefmap[prefset.idref] = prefset
                    #print "adding pref to [%s]" % node.attributes['idref']

                elif node.tagName == 'files':
                    # ignore the obsolete 'files' nodes, we'll grab the children
                    # later on.  This is a change from KPF Ver1 to Ver2
                    continue

                elif node.tagName == 'languagefolder':
                    # convert old 'languagefolder' types to regular folders
                    part = self.createPartFromType('folder')
                    language = node.attributes['language'].value
                    part._attributes['name'] = language
                    part._attributes['language'] = language
                    part.value = ''
                    partstack.append(part)
                    continue

                else:
                    # create our new part instance
                    try:
                        part = self.createPartFromType(node.tagName)
                    except KeyError, e:
                        # a bad part in the project, ignore for now
                        log.error("Unknown project element with name %s", node.tagName)
                        if node.attributes.get('url'):
                            part = self.createPartFromType('file')
                        else:
                            part = self.createPartFromType('Unknown')

                    for attribute, value in node.attributes.items():
                        part._attributes[attribute] = value

                    if 'id' in part._attributes and part._attributes['id'] in idlist:
                        log.error("kpf file [%s] duplicate id [%s], id changed", fname, part._attributes['id'])
                        part._attributes['id'] = part.id # reset to autogenerated id
                        dirtyAtEnd = 1

                    # XXX need to decentralize this processing
                    if 'url' in part._attributes:
                        if (not part._attributes['url'] or
                            (part._attributes['url'] == 'None' and \
                             part.type in ("snippet", "macro", "command"))):
                            log.warn("Ignoring 'None' url attribute in %s '%s'", part.type, part._attributes.get('name') or 'Unknown')
                            del part._attributes['url']
                        else:
                            value = part._attributes['url']
                            if value.find('://') == -1: # it is not an real URL -- it must be relative
                                part._tmpAttributes['relativeurl'] = value
                                value = uriparse.UnRelativizeURL(self._relativeBasedir, value)
                                part._attributes['url'] = part._tmpAttributes['url'] = value
                            elif value.startswith("koremote://"):
                                try:
                                    re_split_url = re.compile(r'^(.*?)://(.*?)/(.*)$')
                                    url_parts_match = re_split_url.match(value)
                                    if url_parts_match:
                                        url_parts = url_parts_match.groups()
                                        server_alias = url_parts[1]
                                        url_subparts_match = re_split_url.match(url_parts[2])
                                        if url_subparts_match:
                                            url_subparts = url_subparts_match.groups()
                                            if not server_alias:
                                                server_alias = url_subparts[1]
                                            value = "%s://%s/%s" % (url_subparts[0],
                                                                    server_alias,
                                                                    url_subparts[2])
                                            part._attributes['url'] = part._tmpAttributes['url'] = value
                                except:
                                    log.exception("Unexpected exception converting koremote url: %r", value)
                            self._urlmap[value] = part
                    if 'iconrelpath' in part._attributes and part._attributes['iconrelpath']:
                        # fixup our old icon paths
                        value = part._attributes['iconrelpath']
                        if value[0] in ['/','['] or value[1] == ':':
                            # pre 3.0 project icon url's, fixem now, and mark the project
                            # as dirty so it needs to be saved with corrected urls
                            value = _iconRelpathtoURL(value, self._relativeBasedir)
                            relpath = uriparse.RelativizeURL(self._relativeBasedir, value)
                            part._attributes['icon'] = relpath
                        else:
                            part._attributes['icon'] = value
                        del part._attributes['iconrelpath']
                        dirtyAtEnd = 1
                    if 'icon' in part._attributes and part._attributes['icon']:
                        value = part._attributes['icon']
                        if value.find('://') == -1: # it is not an real URL -- it must be relative
                            part._tmpAttributes['relativeiconurl'] = value
                            value = uriparse.UnRelativizeURL(self._relativeBasedir, value)
                        elif value.find('chrome://jaguar') == 0:
                            value = 'chrome://komodo' + value[15:]
                            dirtyAtEnd = 1
                        part._attributes['icon'] = value
                    if 'startup' in part._attributes and \
                       part._attributes['startup'].find('://') == -1:
                            value = part._attributes['startup']
                            part._tmpAttributes['relativestartup'] = value
                            part._attributes['startup'] = part._tmpAttributes['startup'] = uriparse.UnRelativizeURL(self._relativeBasedir, value)
                    if 'keyboard_shortcut' in part._attributes and \
                       part._attributes['keyboard_shortcut']:
                        keybound_parts.append(part)

                    # be sure to handle children that got deserialized before the parent
                    # in this case, there are two child array's, but the one in the part
                    # will be invalid.
                    if hasattr(part, 'children') and part._attributes['id'] in self._childmap:
                        part.children = self._childmap[part._attributes['id']]
                    part.assignId()
                    part.value = ''
                    # push the part onto a stack
                    partstack.append(part)
                    idlist[part._attributes['id']] = 1

            elif event == pulldom.END_ELEMENT and \
               not node.tagName in ['files','project','preference-set']:
                # pop a part off the stack
                childpart = partstack.pop()

                if kpfVer < 3 or \
                   not 'idref' in childpart._attributes:
                    # either an initial upgrade, or K3 read/wrote a K4 project
                    # and added new stuff
                    # this can happen if a project is being shared back and forth
                    # between K3 and K4.

                    # make it a child of the parent
                    # if the parent is only a koIPart, then we
                    # get an exception, it's an invalid project
                    part = partstack[-1]
                    childpart._attributes['idref'] = part.id

                if kpfVer < 4:
                    if childpart.type in ['macro', 'snippet']:
                        # unescape the whitespace escaping from earlier kpf versions
                        childpart.value = unescapeWhitespace(childpart.value)
                        dirtyAtEnd = 1
                    elif childpart.type == "DirectoryShortcut":
                        childpart.set_url(childpart.value.strip())
                        childpart.value = ""
                        dirtyAtEnd = 1

                # we need to insert the parts into our map, so we can
                # build the structure later
                id = childpart._attributes['idref']
                if id not in self._childmap:
                    self._childmap[id] = []
                self._childmap[id].append(childpart)
                
                # set part to the parent or none so any extra text nodes
                # are place into the correct part
                if id in idmap:
                    part = idmap[id]
                elif partstack:
                    part = partstack[-1]
                else:
                    part = None
            elif event == pulldom.CHARACTERS and part:
                if node.nodeValue != "\n" or part.value:
                    part.value += unescape(node.nodeValue)

        # this is the toplevel project, parent prefs are the global prefs
        self.get_prefset().parent = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs

        # hook-up children
        added = []
        for idref, children in self._childmap.items():
            added += children
            if idref in idmap:
                part = idmap[idref]
                for child in children:
                    child.set_parent(part)
            else:
                log.debug("    no part for children idref [%s]", idref)
                #for child in children:
                #    print "  id: %s name: %s" % (child.id,child.get_name())
        for idref, prefset in self._prefmap.items():
            #print "adding prefset to idref [%s]" % idref
            if idref in idmap:
                part = idmap[idref]
                part.set_prefset(prefset)
            else:
                log.debug("    no part for prefset idref [%s]", idref)

        # this initializes menu's, toolbars, etc.  It must be done
        # after prefs are set into the children above
        for child in added:
            child.added()

        self._loaded_from_url = self._url
        self.set_url(url)

        if self._active:
            for part in keybound_parts:
                self._getObserverSvc().notifyObservers(part,'kb-load', part.id)

        # now figure out if we're a live project.  In a load, we're only live
        # if the project has prefs that says we are.
        prefs = self.get_prefset()
        if prefs.hasPrefHere("import_live"):
            self.live = prefs.getBooleanPref("import_live")
        if self.live:
            # for a refresh of the children
            self.needrefresh = 1
            self.getChildren()
        #self.validateParts()
        # this kicks off background status checking for the projects base path
        # the project url's will be added later, from partWrapper.js
        try:
            self._getObserverSvc().notifyObservers(self,'file_project',os.path.dirname(self._url))
        except Exception, unused:
            # if noone listens, exception
            pass


        self.set_isDirty(dirtyAtEnd)

        dt = time.clock() - t1
        log.info("project.load\t%4.4f" % (dt))

    def validateParts(self):
        myparts = [p for p in idmap.values() if p._project is self]
        print "I have %d parts" % len(myparts)

        mychildren = [p for p in myparts if p._parent is self]
        print "       %d direct children" % len(mychildren)

        folders = [p for p in myparts if hasattr(p, 'children')]
        print "       %d containers" % len(folders)
        for f in folders:
            print "       id %s" % f.id

        orphans = []
        allchildren = []
        print "       %d child sets" % len(self._childmap)
        for idref, children in self._childmap.items():
            print "       %d in childset [%s]" % (len(children), idref)
            if idref not in idmap:
                print "          is orphaned"
                orphans += children
            else:
                allchildren += children
        print "       %d orphans" % len(orphans)
        print "       %d tracked children" % len(allchildren)
        orphaned_prefs = []
        print "       %d prefsets" % len(self._prefmap)
        for idref, prefset in self._prefmap.items():
            if idref not in idmap:
                orphaned_prefs.append(prefset)
        print "       %d orphaned prefsets" % len(orphans)
        #self.dumpTreeFromMaps(self.id)

    def dumpTreeFromMaps(self, id, indent=0):
        print "%s%s" % ((" " * indent), id)
        if id not in self._childmap: return
        for c in self._childmap[id]:
            self.dumpTreeFromMaps(c.id, indent+2)

    def save(self):
        if self._dontoverwrite:
            err = "Komodo will not overwrite a KPF file written by a newer version of Komodo"
            self.lastErrorSvc.setLastError(0, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

        self._save(self._url)
        self.set_isDirty(0)
        self._loaded_from_url = self._url

    def _save(self, url):
        try:
            # cstringio would save a little time, but doesn't support unicode
            import StringIO
            stream = StringIO.StringIO()
            try:
                stream.write('<?xml version="1.0" encoding="UTF-8"?>'+newl)
                stream.write('<!-- Komodo Project File - DO NOT EDIT -->'+newl)
                self.serialize(stream)
            except Exception, e:
                log.exception(e)
                raise
            try:
                import tempfile
                # use a tempfile to avoid disasters if there's a failure on write.
                tempname = tempfile.mktemp()
                f = open(tempname, 'wb+')
                f.write(stream.getvalue().encode('UTF-8'))
                f.close()
            # if we get this far we have probably saved it correctly.
                fname = uriparse.URIToLocalPath(url)
                dirname = os.path.dirname(fname)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                shutil.copyfile(tempname, fname)
            finally:
                os.unlink(tempname)
        except Exception, e:
            self.lastErrorSvc.setLastError(0, str(e))
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, str(e))

    def revert(self):
        self._url = self._loaded_from_url
        self.load(self._url)
        self.set_isDirty(0)

    def dump(self, indent):
        print " "*indent + "project:"
        for x in self.__dict__.keys():
            print ' '*(indent+1) + x + ':' + str(self.__dict__[x])
        koFolderPart.dump(self, indent)

    def getAllContainedURLs(self):
        return self._urlmap.keys()

    def registerChildByURL(self, child):
        child = UnwrapObject(child) # this is necessary for the getattr to work.
        if child.hasAttribute('url'):
            url = child.getStringAttribute('url')
            self._urlmap[url] = child
        child.set_project(self)
        kids = getattr(child, 'children', None)
        if kids:
            # You don't just adopt someone, you adopt their extended family
            for _child in kids:
                self.registerChildByURL(_child)
        # some children don't-- that's ok.

    def forgetChildByURL(self, child):
        child = UnwrapObject(child) # this is necessary for the getattr to work.
        if child.hasAttribute('url'):
            url = child.getStringAttribute('url')
            if url in self._urlmap:
                del self._urlmap[url]
        # forget decendants also
        kids = getattr(child, 'children', None)
        if kids:
            # You don't just adopt someone, you adopt their extended family
            for _child in kids:
                self.forgetChildByURL(_child)

    def getLiveAncestor(self, url):
        for path, part in self._urlmap.items():
            if part.live and hasattr(part, 'children') and url.startswith(path):
                return part
        if self.live and url.startswith(os.path.dirname(self._url)):
            return self
        return None

    def getChildByURL(self, url):
        part = self._urlmap.get(url, None)
        if not part:
            # if the url is in a live folder, then make a part for the url
            # this part will have no parent, until the live folder it belongs
            # to is opened.
            ancestor = self.getLiveAncestor(url)
            if ancestor:
                part = createPartFromType("file", self)
                part.live = 1
                part.set_url(url)
                part.assignId()
                self.registerChildByURL(part)
        # support the macro url, this allows the auto-closing of files when
        # the project closes, in addition to other stuff
        if not part and url.startswith("macro:"):
            # macro://%s/
            m = re.match("macro://(.*?)/", url, re.U)
            if m and len(m.groups()) > 0:
                id = m.group(1)
                part = self.getChildById(id)
        return part

    def containsLiveURL(self, url):
        return self.getLiveAncestor(url) is not None

    def activate(self):
        try:
            self.activateKeybindings()
            self.activateMenus()
            self.activateToolbars()
        except Exception, e:
            log.exception(e)
        self._active = 1

    def deactivate(self):
        try:
            self.deactivateKeybindings()
            self.deactivateMenus()
            self.deactivateToolbars()
        except Exception, e:
            log.exception(e)
        self._active = 0

    def activateKeybindings(self):
        keybound_parts = self.getChildrenWithAttribute('keyboard_shortcut', 1)
        for part in keybound_parts:
            self._getObserverSvc().notifyObservers(part,'kb-load', part.id)

    def deactivateKeybindings(self):
        keybound_parts = self.getChildrenWithAttribute('keyboard_shortcut', 1)
        for part in keybound_parts:
            self._getObserverSvc().notifyObservers(part,'kb-unload', part.id)

    def activateMenus(self):
        menus = self.getChildrenByType('menu', 1)
        for menu in menus:
            self._getObserverSvc().notifyObservers(menu, 'menu_create', 'menu_create')

    def deactivateMenus(self):
        menus = self.getChildrenByType('menu', 1)
        for menu in menus:
            self._getObserverSvc().notifyObservers(menu, 'menu_remove', 'menu_remove')

    def activateToolbars(self):
        toolbars = self.getChildrenByType('toolbar', 1)
        for toolbar in toolbars:
            self._getObserverSvc().notifyObservers(toolbar, 'toolbar_create', 'toolbar_create')

    def deactivateToolbars(self):
        toolbars = self.getChildrenByType('toolbar', 1)
        for toolbar in toolbars:
            self._getObserverSvc().notifyObservers(toolbar, 'toolbar_remove', 'toolbar_remove')

    def unloadMacros(self):
        for macro in self.getChildrenByType('macro', 1):
            self._getObserverSvc().notifyObservers(macro, 'macro-unload', '')

    def close(self):
        if self._active:
            self.deactivate()
        self.unloadMacros()

        self.set_isDirty(0)
        del self._urlmap
        self.destroy()



#---- Utility routines

def _local_path_from_url(url):
    try:
        #TODO: The docs for URIToLocalPath say an UNC ends up as a file://
        #      URL, which is not the case. Fix those docs.
        return uriparse.URIToLocalPath(url)
    except ValueError:
        # The url isn't a local path.
        return None

_partFactoryMap = {}
for name, value in globals().items():
    if isinstance(value, object) and getattr(value, 'type', ''):
        _partFactoryMap[value.type] = value

def createPartFromType(type, project):
    if type == "project":
        project = _partFactoryMap[type]()
        project.create()
        return project
    return _partFactoryMap[type](project)

