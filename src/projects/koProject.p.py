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
import json
import logging
# cstringio would save a little time, but doesn't support unicode
from StringIO import StringIO
from hashlib import md5
from xml.sax import SAXParseException
from xml.sax.saxutils import escape, quoteattr
from xml.dom import pulldom

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject

import uriparse
import upgradeutils
from URIlib import URIParser, RemoteURISchemeTypes
from koXMLPrefs import NodeToPrefset
from eollib import newl
from findlib2 import paths_from_path_patterns
import koToolbox2
from projectUtils import *

# kpf ver 3 == komodo 4.0
# kpf ver 4 == komodo 4.1, fixing whitespace escape in macro's
# kpf ver 5 == komodo 6 -- separate tools from projects
KPF_VERSION = 5
KPF_VERSION_START_CULLING = 5
gLastProjNum = 1

ANCHOR_MARKER = '!@#_anchor'
CURRENTPOS_MARKER = '!@#_currentPos'

log = logging.getLogger("koProject")
#log.setLevel(logging.DEBUG)

_icons = {
    'file'          :   'chrome://komodo/skin/images/file_icon.png',
    'folder'        :   'chrome://komodo/skin/images/folder-closed.png',
    'live-folder'   :   'chrome://komodo/skin/images/folder-closed-blue.png',
    'project'       :   'chrome://komodo/skin/images/project_icon.png'
}

if sys.platform.startswith('linux'):
    _icons.update({
        'file'          :   'moz-icon://stock/gtk-file?size=16',
        'project'       :   'moz-icon://stock/gtk-home?size=16',
        'folder'        :   'chrome://fugue/skin/icons/box.png',
        'live-folder'   :   'moz-icon://stock/gtk-directory?size=16',
    })

#---- support routines

def _iconRelpathtoURL(relpath, project_dirname):
    # keep this here as part of an upgrade of old style url's for icons
    if relpath.startswith('[PROJECTDIR]'):
        relpath = relpath.replace('[PROJECTDIR]', project_dirname, 1)
        path = os.path.normpath(relpath) # normalize to platform-specific slashes
        url = uriparse.localPathToURI(path)
        return url

    if relpath.startswith('[ICONSDIR]'):
        url = 'chrome://komodo/skin/images' + relpath[len('[ICONSDIR]'):]
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
    _hasset_koFile = False
    _koFile = None

    def __init__(self, project):
        assert project is not None
        self._name = ''
        self._url = ''
        self._path = '' # local path
        self._attributes = {}
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

    def _storeData(self):
        # dump the old id from the child and pref maps
        if self.id in self._project._childmap:
            # this part still has a reference via self.children, no need to store
            del self._project._childmap[self.id]

    def _restoreData(self):
        if hasattr(self, 'children'):
            self._project._childmap[self.id] = self.children

    def assignId(self):
        # we will setup an id based on attributes from the project file
        if not self._attributes.has_key('id'):
            self.id = getNextId(self)
            self._attributes['id'] = self.id
            if hasattr(self, 'children') and self.id not in self._project._childmap:
                #print "assignId [%s]: add child ref to childmap" % self.id
                self._project._childmap[self.id] = self.children
        elif self.id == self._attributes['id']:
            if self._parent:
                self._idref = self._parent.id
            else:
                self._idref = None
            if self._idref == self.id:
                idmap[self.id] = self
                if hasattr(self, 'children'):
                    if self.id not in self._project._childmap:
                        #print "assignId [%s]: add child ref to childmap" % self.id
                        self._project._childmap[self.id] = self.children
                    #elif self.children is not self._project._childmap[self.id]:
                    #    print "*** assignId [%s]: children in map are not mine!" % self.id
                return
            # this part is KEY to getting non-live children into live folders
            id = self.id
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

        self._idref = self._attributes['idref'] = parent.id
        self._parent = parent
        if self._parent and self._parent._project and self._project is not self._parent._project:
            self.set_project(self._parent._project)

    def get_prefset(self):
        # if we have a project, always get the pref from the project, otherwise
        # we have our own prefset
        return self._project.prefset

    def set_prefset(self, prefset):
        errmsg = "Part type %s no longer holds its own pref set.  Only projects can hold a pref set" % (self.type)
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, errmsg)

    def getIDRef(self):
        # get an idref that points to this part
        if not self._idref:
            if not self._parent:
                self._idref = self.id
            else:
                pIDRef = self._parent.getIDRef()
                self._idref = "%s/%s" % (pIDRef, self.get_name())
        return self._idref

    # prefs observer
    def observe(self, subject, topic, message):
        #print "part observer %r,%r,%r, %s" % (subject, topic, message, self._project.get_name())
        self._project._isPrefDirty = True
        if topic == 'userEnvironmentStartupOverride':
            UnwrapObject(components.classes["@activestate.com/koUserEnviron;1"].getService()).addProjectEnvironment(self)

    def dump(self, indent):
        print " "*indent + "Part of type '" + self.type +"':"
        print ' '*(indent+1) + "id: %s" % self.id
        print ' '*(indent+1) + "idref: %s" % self.getIDRef()
        if self._parent:
            print ' '*(indent+1) + "parent id: %s" % self._parent.id
            print ' '*(indent+1) + "parent idref: %s" % self._parent.getIDRef()
        else:
            print ' '*(indent+1) + "parent: NONE"
        for k, v in self._attributes.items():
            print ' '*(indent+1) + "%s: %s" % (k, v)
        prefs = self.get_prefset()
        prefs.dump(indent+1)

    def serialize(self, writer):
        # reset idref every time we serialize.  our children will benefit
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

        if 'idref' not in attrs and self._parent:
            attrs['idref'] = self._parent.id
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

    def _serializeTail(self, writer):
        writer.write("</%s>%s" % (self.type,newl))

    def _serializePrefset(self, writer):
        errmsg = "_serializePrefset:Part type %s no longer holds its own pref set.  Only projects can hold a pref set" % (self.type)
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, errmsg)

    def set_name(self, name):
        self._name = name
        if self.hasAttribute("name"):
            del self._attributes["name"]
        if hasattr(self, '_url') and self._url:
            # using lists to make it mutable
            parts = list(urlparse.urlparse(self._url))
            slashlocation = parts[2].rindex('/')
            parts[2] = parts[2][:slashlocation+1] + name
            ext = os.path.splitext(parts[2])[1]
            if not ext in ('.kpf', koToolbox2.PROJECT_FILE_EXTENSION):
                parts[2] += koToolbox2.PROJECT_FILE_EXTENSION
            self._url = urlparse.urlunparse(tuple(parts))
            self._setPathAndName()
        self.setStringAttribute('name', self._name)
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
        self._project.set_isDirty(1)

    def get_url(self):
        if not self._url and self.hasAttribute('url'):
            self._url = self.getStringAttribute('url')
            self._uri = URIParser()
            self._uri.path = self._url
            self._setPathAndName()
        return self._url

    url = property(get_url, set_url)

    def set_uri(self, uri):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, "'project.uri' referenced, should be 'project.url'")
        
    def get_uri(self):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, "'project.uri' referenced, should be 'project.url'")

    def _setPathAndName(self):
        self._hasset_koFile = False
        self._koFile = None
        if self._uri:
            self._name = self._uri.baseName
            self._path = self._uri.path
        
    def getFile(self):
        if not self._hasset_koFile:
            self._hasset_koFile = True
            # We cache the koFile object, otherwise a koPart can cause the file
            # status service to continually re-check file status for this path.
            # This re-checking is due to the koFile being continually garbage
            # collected and re-created, which causes the file-status service to
            # drop and then re-update it's information - and notifying of this
            # update.
            #
            # Repro: have a project opened in Komodo, but Places/Projects
            #        sidebar closed, restart Komodo and switch tabs - causes
            #        calls to getFile() and the koFile is subsequently gc'd.
            if self.get_url():
                fsvc = components.classes["@activestate.com/koFileService;1"].getService(components.interfaces.koIFileService)
                self._koFile = fsvc.getFileFromURI(self.get_url())
            else:
                self._koFile = None
        return self._koFile

    def hasAttribute(self, name):
        return self._attributes.has_key(name)

    def getAttribute(self, name):
        return self._attributes[name]

    def setAttribute(self, name, value):
        if name not in self._attributes or self._attributes[name] != value: # avoid dirtification when possible.
            self._attributes[name] = value
            self._project.set_isDirty(1)

    def removeAttribute(self, name):
        if name not in self._attributes: return
        del self._attributes[name]
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
        # necessary for packaging projects with relative urls
        part._tmpAttributes = copy.copy(self._tmpAttributes)

        if hasattr(self, '_url') and part.type != 'project':  # we _don't_ want clones of projects to have a URL
            part._url = self._url
        if hasattr(self, '_name'):
            part._name = self._name
        if hasattr(self, '_path'):
            part._path = self._path

        a_names = self._attributes.keys()
        a_names.sort()
        for a_name in a_names:
            if a_name == 'id': continue # don't copy the id
            data = self.getStringAttribute(a_name)
            part.setStringAttribute(a_name,data)

        self._project.set_isDirty(dirty)
        return part

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
        self.numChildren = 0
        self._sortedBy = 'name'
        self._sortDir = 0
        self.children = []
        koPart.__init__(self, project)
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
        # This function isn't called in Komodo
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
            self._sortNodes(self.children, self._sortedBy, self._sortDir)

        if child not in self._project._childmap[self.id]:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, "child is not in the project childmap!")

        child.set_parent(self)
        child.set_project(self._project) # this calls the setter
        #child.assignId()

        self._project.set_isDirty(1)
        self._project.registerChildByURL(child)

    def getChildById(self, id):
        if self.id == id:
            return self
        # Already-closed entries don't have children
        for child in getattr(self, "children", []):
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
        previous_parent = child._parent
        child.destroy()

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
    _iconurl = _icons.get('file')
    primaryInterface = 'koIPart_file'

    def __init__(self, project):
        koPart.__init__(self, project)
        self.flavors.insert(0,'text/x-moz-url')

    def __str__(self):
        return "<koPart_file, url=%s>" % self._attributes.get('url', 'None')

    def __repr__(self):
        return "<koFilePart %s (id=%r)>" % (
            self._attributes.get("name", "?name?"),
            self._attributes.get("id", "?id?"))

def File(url, name, project):
    """Construct a 'file' koIPart."""
    assert project is not None
    part = koFilePart(project)
    part._attributes['url'] = url
    part._attributes['name'] = name
    return part

# These are in for compatibility reasons, but they no longer do anything

class koSnippetPart(koPart):
    type = 'snippet'
    
class koCommandPart(koPart):
    type = 'command'

class koTemplatePart(koPart):
    type = 'template'
    
class koURLPart(koPart):
    type = 'URL'

class koMacroPart(koPart):
    type = 'macro'

class koDirectoryShortcut(koPart):
    type = 'DirectoryShortcut'

class koMenuPart(koContainer):
    type = 'menu'

class koToolbarPart(koContainer):
    type = 'toolbar'

class koChangeListPart(koContainer):
    type = 'changelist'

class koToolbox(koPart):
    type = 'Toolbox'

class koProjectRef(koFilePart):
    type = 'ProjectRef'

# See factory functions below
class koFolderPart(koContainer):
    _com_interfaces_ = [components.interfaces.koIPart_folder]
    type = 'folder'
    prettytype = 'Folder'
    _iconurl = _icons.get('folder')
    primaryInterface = 'koIPart_folder'

    def __repr__(self):
        return "<koFolderPart %s (id=%r)>" % (
            self._attributes.get("name"),
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
                    newfolder = Folder(url, part, self._project)
                    folder.addChild(newfolder)
                    folder = newfolder
        return folder


class koLiveFolderPart(koFolderPart):
    _com_interfaces_ = [components.interfaces.koIPart_livefolder,
                        components.interfaces.koIPart_folder]
    type = 'livefolder'
    prettytype = 'Live Folder'
    _iconurl = _icons.get('live-folder')
    primaryInterface = 'koIPart_livefolder'

    def __init__(self, project):
        koFolderPart.__init__(self, project)
        self.live = 1
        self.needrefresh = 1

    def __repr__(self):
        return "<koLiveFolderPart %s (id=%r)>" % (
            self._attributes.get("name"),
            self._attributes["id"])

    # prefs observer
    def observe(self, subject, topic, message):
        koFolderPart.observe(self, subject, topic, message)
        # now, if one of our import properties has changed, lets update
        #print "livefolder got notified of change [%s][%s][%s]"%(subject,topic, message)
        #print "livefolder change in project %s" % self._project.get_name()
        if message in ("import_live"
                       "import_dirname",
                       "import_include_matches",
                       "import_exclude_matches"):
            self.needrefresh = 1
            if message == "import_dirname":
                self._removeLiveChildrenRecursiveSaveUnded()

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
            undead.append(child)
        return undead

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
        recursive = prefs.getBooleanPref("import_recursive")
        type = prefs.getStringPref("import_type")
        path = self.get_liveDirectory()
        return include, exclude, recursive, type, path

    def getChildren(self):
        return self.children

    def genLocalPaths(self, gatherDirs=False, follow_symlinks=True):
        """Generate all contained local paths."""
        from os.path import join
        
        prefset = self.get_prefset()
        base_dir = self.get_liveDirectory()
        excludes = [p for p in prefset.getStringPref("import_exclude_matches").split(';') if p]
        includes = [p for p in prefset.getStringPref("import_include_matches").split(';') if p]
        excludes.append("*.kpf")  # Live folders always exclude .kpf files.
        excludes.append("*.komodoproject")  # Live folders always exclude .komodoproject files.
        path_patterns = [join(base_dir, "*"), join(base_dir, ".*")]
        
        base_dir_length = len(base_dir)
        for path in paths_from_path_patterns(
                path_patterns,
                dirs=(gatherDirs and "always" or "never"),
                recursive=True,
                includes=includes,
                excludes=excludes,
                on_error=None,
                follow_symlinks=follow_symlinks,
                skip_dupe_dirs=True):
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
    _iconurl = _icons.get('project')
    primaryInterface = 'koIProject'
    _partSvc = None
    # The last md5 is used for comparing between load/saves to ensure that
    # there are no changes outside of what Komodo makes.
    _lastmd5 = None
    _obsoletePartNames = ('macro', 'snippet', 'command', 'template',
                          'DirectoryShortcut', 'URL')

    def __init__(self):
        # _isPrefDirty tracks changes made due to changes in pref sets
        # These should be saved quietly.
        
        self._isDirty = self._isPrefDirty = 0
        self._urlmap = weakref.WeakValueDictionary()
        # child map is a mapping of idrefs to child parts.  a part get's it's own
        # idref, then looks here for it's children
        self._childmap = {}

        self.prefset = None


        self._project = self # cycle - need to investigate WeakReference
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)


        self._quiet = 0
        self._dontoverwrite = 0

        # call parent init after we setup anything that is needed by other
        # init funcs.
        self._active = 0
        koLiveFolderPart.__init__(self, self)
        self.live = 0

        prefset = components.classes["@activestate.com/koPrefService;1"].\
                                getService(components.interfaces.koIPrefService).prefs

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

    # Override _setPathAndName to allow a project to have a user customized
    # name that will be shown in the UI, instead of always defaulting to the
    # basename of the project. Bug 82050.
    def _setPathAndName(self):
        if self._uri:
            # If the project has a name attribute, that gets precedence.
            if "name" in self._attributes:
                self._name = self._attributes.get("name")
            else:
                self._name = self._uri.baseName
            self._path = self._uri.path
            
    def _get_importDirectoryInfo(self):
        prefs = self.get_prefset()
        # Bug 87843:
        # import_live means that Komodo is pointing at another
        # directory.  v5 does this via the import_live boolean pref
        # and then the project.livefolder attribute.  v6 just looks
        # at the import_dirname field, which is also used in v5.
        import_live = (prefs.hasPref("import_live") and
                       prefs.getBooleanPref("import_live"))
        koFileEx = components.classes["@activestate.com/koFileEx;1"] \
            .createInstance(components.interfaces.koIFileEx)
        if not import_live:
            # First check v5 legacy projects.
            importedDirs = self.getChildrenByType('livefolder', True)
            if len(importedDirs) == 1:
                koFileEx.URI = importedDirs[0].get_url()
                return koFileEx
        koFileEx.path = self.get_liveDirectory()
        return koFileEx

    def get_importDirectoryURI(self):
        koFileEx = self._get_importDirectoryInfo()
        return koFileEx.URI
    
    def get_importDirectoryLocalPath(self):
        koFileEx = self._get_importDirectoryInfo()
        if not koFileEx.isLocal:
            return None
        try:
            return koFileEx.path
        except ValueError:
            return None

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
                
        self.prefset.serialize(writer, self._relativeBasedir)
        self._serializeTail(writer)

    # Fill with a new empty, unnamed project
    def create(self):
        self._name = _makeNewProjectName()
        self.setLongAttribute("kpf_version", KPF_VERSION)
        prefset = UnwrapObject(components.classes["@activestate.com/koProjectPreferenceSet;1"].\
                                        createInstance(components.interfaces.koIProjectPreferenceSet))
        self.set_prefset(prefset)

    def createPartFromType(self, type):
        # we create the koPart instance and return it
        return createPartFromType(type, self)

    def clone(self):
        dummy_project = koProject()
        dummy_project.create()
        project = self._clone(dummy_project)
        project.set_prefset(self.get_prefset().clone())
        return project

    def set_isDirty(self, dirty):
        if self._isDirty != dirty:
            self._isDirty = dirty
            try:
                self._getObserverSvc().notifyObservers(self,'update-commands','projectsChanged')
            except:
                pass # no listener

    def get_isDirty(self):
        return self._isDirty

    def get_isPrefDirty(self):
        return self._isPrefDirty
    
    def get_prefset(self):
        if self.prefset is None:
            prefset = components.classes["@activestate.com/koProjectPreferenceSet;1"] \
                .createInstance(components.interfaces.koIProjectPreferenceSet)
            self.set_prefset(UnwrapObject(prefset))
        return self.prefset

    def set_prefset(self, prefset):
        # @prefset - an unwrapped instance of koIPreferenceSet
        if self.prefset is not None:
            self.prefset.prefObserverService.removeObserver(self, "")
        if prefset is not None:
            if prefset.preftype != 'project':
                log.warn("prefset is not a koIProjectPreferenceSet %r", prefset)
            prefset.id = "project"
            prefset.idref = self.id
            prefset.chainNotifications = 1
            globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs
            prefset.set_parent(UnwrapObject(globalPrefs))
        self.prefset = prefset
        if prefset is not None:
            prefset.prefObserverService.addObserver(self, "", 1)

    def _update_lastmd5_from_contents(self, contents):
        self._lastmd5 = md5(contents).hexdigest()

    def _getContents(self, fname):
        if not os.path.exists(fname):
            err = 'File does not exist.'
            self.lastErrorSvc.setLastError(0, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)
        try:
            # Although we encode and save the contents in UTF-8 format, we
            # do not want to decode here, the decoding is left up to the dom
            # parsing routines inside _parseStream.
            contents = open(fname, "rb").read()
        except (IOError, COMException), e:
            errstr = "Can't open project file %s because %s" % (fname, e)
            log.error(errstr)
            raise
        return contents

    def haveContentsChangedOnDisk(self):
        url = self._loaded_from_url or self._url
        fname = uriparse.URIToLocalPath(url)
        try:
            contents = self._getContents(fname)
        except (IOError, COMException), e:
            # For some reason the project cannot be opened.
            contents = ""
        return self._lastmd5 != md5(contents).hexdigest()

    def _loadContents(self, contents, url, fname):
        self._update_lastmd5_from_contents(contents)
        self._parseStream(StringIO(contents), url, fname)

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
        contents = self._getContents(fname)
        self._loadContents(contents, url, fname)

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

        dirtyAtEnd = 0
        events = pulldom.parse(stream)
        kpfVer = 0
        canBeCulled = False
        basename = None
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
                        if kpfVer < KPF_VERSION_START_CULLING:
                            canBeCulled = True
                        try:
                            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
                            basename = os.path.basename(fname)
                            import koToolbox2
                            newExt = koToolbox2.PROJECT_FILE_EXTENSION
                            if not self._url.endswith(newExt):
                                oldName = self._url
                                newName = (os.path.splitext(oldName)[0] 
                                           + newExt)
                                url = newName
                                try:
                                    del self._attributes['name']
                                except KeyError:
                                    pass
                                # Do this so name fields are updated now, becauses
                                # the final set_url isn't done until the
                                # project has been completely loaded.
                                self.set_url(url)
                                msg = (("Komodo is reading a KPF file version %d(%s) and is "
                                        + "converting it to version %d, in a new file %s at [%s]") %
                                       (kpfVer, fname, KPF_VERSION,
                                        os.path.basename(newName),
                                        os.path.dirname(newName)))
                            else:
                                canBeCulled = False
                                msg = (("Komodo is reading a KPF file version %d(%s), but can't  "
                                        + "convert it to version %d, as it ends with "
                                        + "the extension %s.") %
                                       (kpfVer, fname, KPF_VERSION, koToolbox2.PROJECT_FILE_EXTENSION))
                            displayMessage = False # not self._path.startswith(koDirSvc.userDataDir)
                            if displayMessage:
                                wwatch = components.classes["@mozilla.org/embedcomp/window-watcher;1"].getService(components.interfaces.nsIWindowWatcher)
                                prompt = wwatch.getNewPrompter(wwatch.activeWindow)
                                prompt.alert("Project Upgrade Warning", msg)
                            _level = log.level
                            log.setLevel(logging.WARNING)
                            log.warn(msg)
                            log.setLevel(_level)
                            self.lastErrorSvc.setLastError(0, msg)

                            if canBeCulled:
                                koTBMiscSvc = UnwrapObject(components.classes["@activestate.com/koToolbox2Service;1"].getService(components.interfaces.koIToolbox2Service))
                                koTBMiscSvc.extractToolboxFromKPF_File(fname, os.path.splitext(basename)[0])
                        except Exception, e:
                            log.exception("Error '%s' reading project file '%s'", e, fname)
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
                    events.expandNode(node)
                    if len(partstack) != 1:
                        #log.debug('node.tagName == "preference-set": len(partstack) =%d, ignoring pref %s', len(partstack), node.toxml())
                        continue
                    # Turn dom node into a prefset. We set the 'preftype' field
                    # to ensure we get back a koIProjectPreferenceSet.
                    node.attributes['preftype'] = 'project'
                    prefset = NodeToPrefset(node, self._relativeBasedir, 1)
                    if __debug__:
                        # this should always pass
                        prefset.QueryInterface(components.interfaces.koIPreferenceRoot)
                    prefset = UnwrapObject(prefset)

                    if kpfVer < 3 or \
                        not prefset.idref:
                        # we only get here with 3.x projects, 4.x projects
                        # should always have the idref.  In this case, the idref
                        # is the part id
                        dirtyAtEnd = 1
                        prefset.idref = part.id

                    if prefset.hasPrefHere("mappedPaths"):
                        upgradeutils.upgrade_mapped_uris_for_prefset(prefset)

                    idref = prefset.idref
                    try:
                        _owning_part = idmap[idref]
                    except KeyError:
                        _owning_part = None
                    else:
                        if _owning_part.type not in ("folder", "livefolder", "group", "file"):
                            _owning_part.set_prefset(prefset)
                        else:
                            if basename is not None:
                                projectName = "project " + basename
                            else:
                                projectName = "the current project"
                            try:
                                typeName = _owning_part.type
                            except:
                                typeName = "<?unknown type>"
                            try:
                                partName = _owning_part.get_name()
                            except:
                                partName = "<?unknown name>"
                            log.warn("While loading %s, skipping assigning legacy prefset to type %s %s",
                                       projectName, typeName, partName)

                elif node.tagName == 'files':
                    # ignore the obsolete 'files' nodes, we'll grab the children
                    # later on.  This is a change from KPF Ver1 to Ver2
                    print "XXX: Keep the files in this project!"
                    continue

                elif node.tagName == 'languagefolder':
                    # convert old 'languagefolder' types to regular folders
                    part = self.createPartFromType('folder')
                    language = node.attributes['language'].value
                    part._attributes['name'] = language
                    part._attributes['language'] = language
                    partstack.append(part)
                    continue
                else:
                    # create our new part instance
                    try:
                        part = self.createPartFromType(node.tagName)
                    except TypeError, e:
                        log.error("Problem creating part from type %s", node.tagName)
                        raise
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

                    # be sure to handle children that got deserialized before the parent
                    # in this case, there are two child array's, but the one in the part
                    # will be invalid.
                    if hasattr(part, 'children') and part._attributes['id'] in self._childmap:
                        part.children = self._childmap[part._attributes['id']]
                    part.assignId()
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
        # end for (event, node) in events:
        
        # create an empty prefset if we don't have one
        self._upgradePrefs(kpfVer)

        # hook-up children
        added = []
        for idref, children in self._childmap.items():
            if idref in idmap:
                part = idmap[idref]
                for child in children:
                    child.set_parent(part)
            else:
                log.debug("    no part for children idref [%s]", idref)
                #for child in children:
                #    print "  id: %s name: %s" % (child.id,child.get_name())
        self._loaded_from_url = self._url
        self.set_url(url)

        #self.validateParts()
        # this kicks off background status checking for the projects base path
        # the project url's will be added later, from partWrapper.js
        try:
            self._getObserverSvc().notifyObservers(self,'file_project',os.path.dirname(self._url))
        except Exception, unused:
            # if noone listens, exception
            pass


        self.set_isDirty(dirtyAtEnd)
        
        if canBeCulled:
            self._cullTools()
            # Need to do this, or Komodo will think the loaded contents
            # are out of sync with the contents on disk.
            self.save()

        dt = time.clock() - t1
        log.info("project.load\t%4.4f" % (dt))

    def _upgradePrefs(self, kpf_version):
        prefs = self.get_prefset()
        
        if kpf_version < 5 and prefs.hasPrefHere("import_exclude_matches"):
            # Add filtering for the new project file types.
            value = prefs.getStringPref("import_exclude_matches")
            values = value.split(";")
            if "*.kpf" in values and not "*.komodoproject" in values:
                values.append("*.komodoproject")
                values.append(".komodotools")
                value = ";".join(values)
                prefs.setStringPref("import_exclude_matches", value)

        if prefs.hasPrefHere("prefs_version"):
            version = prefs.getLongPref("prefs_version")
        else:
            version = 0

        if version < 1:
            initSvc = UnwrapObject(components.classes["@activestate.com/koInitService;1"]
                                             .getService())
            initSvc._flattenLanguagePrefs(prefs)

        if not version > 1:
            version = 1
            prefs.setLongPref("prefs_version", version)

    def _cullTools(self):
        """ Remove any tools, and also folders that are emptied after all
        tools are removed, as part of moving to Komodo 6, project version 5.
        """
        for child in self.getChildren()[:]:  # copy because we're deleting as we go
            self._cullToolOrContainer(self, child)
    
    _toolNames = ('macro', 'snippet', 'command', 'URL',
                  'DirectoryShortcut', 'menu', 'toolbar', 'template')
    def _cullToolOrContainer(self, parent, child):
        removedItem = False
        if child.type in self._toolNames:
            parent.removeChild(child)
            removedItem = True
            self.set_isDirty(True)
        elif child.type == 'folder':
            removedGrandchild = False
            for grandchild in child.getChildren()[:]: # copy the list, as we're deleting as we iterate
                # Evaluate the function first for the side-effects
                removedGrandchild = (self._cullToolOrContainer(child, grandchild)
                                     or removedGrandchild)
            if removedGrandchild and not child.getChildren():
                # deleted all the kids, so delete self as well.
                parent.removeChild(child)
                removedItem = True
        return removedItem

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
            stream = StringIO()
            try:
                stream.write('<?xml version="1.0" encoding="UTF-8"?>'+newl)
                stream.write('<!-- Komodo Project File - DO NOT EDIT -->'+newl)
                self.serialize(stream)
            except Exception, e:
                log.exception(e)
                raise
            import tempfile
            # use a tempfile to avoid disasters if there's a failure on write.
            tempname = tempfile.mktemp()
            try:
                f = open(tempname, 'wb+')
                contents = stream.getvalue().encode('UTF-8')
                f.write(contents)
                f.close()
            # if we get this far we have probably saved it correctly.
                self._update_lastmd5_from_contents(contents)
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

    def _addTrailingSlash(self, path):
        if path[-1] == "/":
            return path
        return path + "/"
    
    def getLiveAncestor(self, url):
        for path, part in self._urlmap.items():
            if hasattr(part, 'children') and url.startswith(path):
                return part
        # Fix bug 89767 -- look at the import_dirname first, but
        # leave the code looking at the project's location anyway.
        if url.startswith(self._addTrailingSlash(os.path.dirname(self._url))):
            return self
        elif self.prefset and self.prefset.hasPrefHere("import_dirname"):
            projPath = self.prefset.getStringPref("import_dirname")
            koFileEx = components.classes["@activestate.com/koFileEx;1"] \
                .createInstance(components.interfaces.koIFileEx)
            koFileEx.path = projPath;
            if koFileEx.scheme != "file":
                return None
            projURI = koFileEx.URI
            try:
                if url.startswith(self._addTrailingSlash(projURI)):
                    return self
            except TypeError:
                log.exception("Error getting info on project %s import_dirname val: %r",
                              self._name, projPath)
        return None

    def belongsToProject(self, url):
        try:
            if self._urlmap.get(url, None):
                return True
        except:
            pass
            #log.exception("Can't get part for url %s", url)
        project_dir_url = self.get_importDirectoryURI()
        if not sys.platform.startswith("linux"):
            url = url.lower()
            project_dir_url = project_dir_url.lower()
        
        if (url == project_dir_url
            or url.startswith(self._addTrailingSlash(project_dir_url))):
            return True
        # Bug 93436: check all folders
        for f in self.getChildrenByType("livefolder", True):
            folderUrl = f.getFile().URI
            if (url == folderUrl
                or url.startswith(self._addTrailingSlash(folderUrl))):
                return True
        return False

    def getChildByURL(self, url):
        try:
            part = self._urlmap.get(url, None)
        except:
            log.exception("Can't get part for url %s", url)
            return None
        if not part:
            # if the url is in a live folder, then make a part for the url
            # this part will have no parent, until the live folder it belongs
            # to is opened.
            # This works only for local buffers (limitation while fixing bug 90607).
            ancestor = self.getLiveAncestor(url)
            if ancestor:
                part = createPartFromType("file", self)
                origIsDirty = self.get_isDirty()
                part.set_url(url)
                # Keep the project non-dirtied, if we're quietly adding
                # info to it to track which files to open when the project's
                # reopened.
                if not origIsDirty and self.get_isDirty():
                    try:
                        self.save()
                    except:
                        log.debug("Failed to save project %s", self.get_name())
                part.assignId()
                self.registerChildByURL(part)
        return part

    def containsLiveURL(self, url):
        return self.getLiveAncestor(url) is not None

    def activate(self):
        self._active = 1

    def deactivate(self):
        self._active = 0

    def close(self):
        if self._active:
            self.deactivate()

        self.set_isDirty(0)
        try:
            del self._urlmap
        except AttributeError:
            log.error("Trying to delete a _urlmap that no longer exists")
        self.destroy()

    def getPart(self, filename, url, project, live):
        basename = os.path.basename(filename)
        if os.path.isdir(filename):
            return Folder(url, basename, project, live)
        return File(url, basename, project)

    def reassignUUIDs(self):
        self._reassignChildUUIDs(self, {})
        
    def _reassignChildUUIDs(self, part, replaceUUIDMap):
        attributes = part._attributes
        id = part.id
        if id not in replaceUUIDMap:
            replaceUUIDMap[id] = getNextId(part)
        part.id = replaceUUIDMap[id]
        attributes['id'] = part.id
        idref = part._idref
        if idref:
            if idref not in replaceUUIDMap:
                replaceUUIDMap[idref] = getNextId(part)
            part._idref = replaceUUIDMap[idref]
            attributes['idref'] = part._idref
        try:
            prefset = UnwrapObject(part.get_prefset())
            if prefset:
                idref = prefset.idref
                if idref and idref in replaceUUIDMap:
                    prefset.idref = replaceUUIDMap[idref]
        except:
            log.exception("Failed to get prefset/update prefset.idref")
        for child in getattr(part, 'children', []):
            self._reassignChildUUIDs(child, replaceUUIDMap)
            

class koUnopenedProject(koProject):
    _com_interfaces_ = [components.interfaces.koIUnopenedProject]
    _reg_desc_ = "Komodo Unopened Project"
    _reg_contractid_ = "@activestate.com/koUnopenedProject;1"
    _reg_clsid_ = "{13b7604e-4113-4477-bbab-d53dc00421b7}"
    type = 'unopened_project'
    prettytype = 'Unopened Project'
    _iconurl = _icons.get('project')
    primaryInterface = 'koIUnopenedProject'
    _partSvc = None
    
    def __init__(self):
        koProject.__init__(self)
        self.flavors.insert(0, 'text/x-moz-url')

    def __str__(self):
        return "<koUnopenedProject, url=%s>" % self._attributes.get('url', 'None')

    def __repr__(self):
        return "<koUnopenedProject %s (id=%r)>" % (
            self._attributes.get("name", "?name?"),
            self._attributes.get("id", "?id?"))

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

