#!/usr/bin/env python
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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

""" Migrate old-style toolboxes to Komodo 6

See KD 252 for details.

"""
import json
import os
from os.path import exists, join
import re
import sys
import shutil
import logging
from contextlib import contextmanager
import sqlite3
from pprint import pprint, pformat
import time

import koToolbox2
log = logging.getLogger("koMigrateV5Toolboxes")
#log.setLevel(logging.DEBUG)

try:
    import cElementTree as ET # effbot's C module
except ImportError:
    logging.basicConfig()
    log.setLevel(logging.INFO)
    log.error("using element tree and not cElementTree, performace will suffer")
    if sys.version_info[:2] < (2, 5):
        import elementtree.ElementTree as ET # effbot's pure Python module
    else:
        import xml.etree.ElementTree as ET

#---- global data

nowrite = False
_version_ = (0, 1, 0)
_kpf_version = 5

class ExpandToolboxException(Exception):
    pass

#---- module API

def expand_toolbox(toolboxFile, outdir, toolboxDirName=None, force=0):
    """ Write out the contents of toolboxFile to outdir.
        Callers should wrap this in a try/except block to allow unexpected input.
    """
    tree = ET.parse(toolboxFile)
    root = tree.getroot()
    global _kpf_version
    tmp_ver = root.get('kpf_version')
    if tmp_ver is not None:
        _kpf_version = int(tmp_ver)
    prefSets = root.findall("preference-set")
    for ps in prefSets:
        root.remove(ps)
    dirTree = TreeBuilder().reassembleTree(tree)
        
    if not os.path.exists(outdir):
        # Allow an exception here
        os.makedirs(outdir)
    elif not os.path.isdir(outdir):
        raise ExpandToolboxException("outdir %s is not a directory, not expanding" % outdir)
    os.chdir(outdir)
    if toolboxDirName is None:
        toolboxDirName = koToolbox2.DEFAULT_TARGET_DIRECTORY
    if not os.path.exists(toolboxDirName):
        os.makedirs(toolboxDirName)
    os.chdir(toolboxDirName)
    obsoleteItems = []
    TreeWalker(obsoleteItems, force).expandTree(dirTree)
    #todo: Write out the misc parts
    if obsoleteItems:
        log.warn("The following items weren't converted: %s\n", obsoleteItems)
                  # "\n".join(["%s: %s" % (x[0], x[1]) for x in obsoleteItems]))
    return 0
    
# From koProject.p.py, for upgrading version 3 snippets and macros.

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

class TreeNode(object):
    def __init__(self, elt):
        self.elt = elt
        try:
            del elt.attrib['idref']
        except KeyError:
            pass
        self.children = []
    
    def addChild(self, child):
        self.children.append(child)
    
class TreeBuilder(object):
    
    def treeBuilder(self, curr_node, id):
        for child_id in self.ids_from_idref.get(id, []):
            child_elt = self.elts_from_id[child_id]
            child_node = TreeNode(child_elt)
            curr_node.addChild(child_node)
            self.treeBuilder(child_node, child_id)
            
    def reassembleTree(self, tree):
        root_id = None
        root_elt = None
        self.ids_from_idref = {}
        self.elts_from_id = {}
        for elt in tree.getiterator():
            attribs = elt.attrib
            id = attribs.get("id", None)
            if id is None:
                log.error("No id attribute for element %r", elt)
                continue
            idref = attribs.get("idref", None)
            if idref is None:
                if root_id is not None:
                    log.error("Root should be %r, but found another:%r", root_elt, elt)
                    continue
                root_id = id
                root_elt = elt
            else:
                self.ids_from_idref.setdefault(idref, []).append(id)
            self.elts_from_id[id] = elt
        newTree = TreeNode(root_elt)
        self.treeBuilder(newTree, root_id)
        return newTree
    
class TreeWalker():
    def __init__(self, obsoleteItems, force):
        self._force = force
        self.obsoleteItems = obsoleteItems
        
    def _evalChars(self, chars):
        newChars = []
        for c in chars:
            oc = ord(c)
            if c in "-=+,. #~()":
                newChars.append(c)
            elif oc < 256:
                newChars.append('%%%02x' % oc)
            else:
                newChars.append('%%u%04x' % oc)  # %uxxxx -- unicode sequence
        return ''.join(newChars)
        
    def _prepareUniqueFileSystemName(self, node, addExt=True):
        name = node.elt.get('name')
        # "slugify"
        basePart = koToolbox2.truncateAtWordBreak(re.sub(r'[^\w\d\-=\+]+', '_', name))
        extPart = (addExt and koToolbox2.TOOL_EXTENSION) or ""
        # The purpose for the next test is because abbrevs with
        # names like "+" "++" and "++??" will all be mapped to
        # the name "_".  So insist on unique filenames, even if
        # we're in force mode.
        if (nowrite
            or not os.path.exists(basePart + extPart)
            or (self._force and basePart == name)):
            return basePart + extPart
        for i in range(1, 1000000):
            candidate = "%s-%d%s" % (basePart, i, extPart)
            if not os.path.exists(candidate):
                #log.debug("Writing out file %s/%s as %s", os.getcwd(), basePart, candidate)
                return candidate
        else:
            raise ExpandToolboxException("File %s exists in directory %s, force is off" %
                                         (name, os.getcwd()))
        
    def _expand_children(self, node):
        for child in node.children:
            self.expandTree(child)
        
    def expandContainerNode(self, node, folderInfo):
        q_name = self._prepareUniqueFileSystemName(node, addExt=False)
        if not os.path.exists(q_name):
            os.makedirs(q_name)
        elif not os.path.isdir(q_name):
            raise ExpandToolboxException("Found file %s in directory %s, won't delete" % (q_name, os.getcwd()))
        os.chdir(q_name)
        try:
            fw = open(koToolbox2.UI_FOLDER_FILENAME, 'w')
            try:
                json.dump(folderInfo, fw, encoding='utf-8')
            except:
                log.exception("Failed to write out json info for folderInfo %s", folderInfo)
            fw.close()
        except:
            log.exception("Error opening file %s/%s", os.getcwd(),
                          koToolbox2.UI_FOLDER_FILENAME)
        self._expand_children(node)
        os.chdir("..")
        
    def expandNode_folder(self, node):
        #log.debug("expand folder %s", node.elt.get('name'))
        folderInfo = self._get_metadata(node.elt, [])
        folderInfo['type'] = 'folder'
        self.expandContainerNode(node, folderInfo)
        
    def _get_metadata(self, elt, names):
        vals = {'name': elt.attrib['name']}
        for name in names:
            val = elt.get(name)
            if val is not None:
                vals[name] = val
        return vals
        
    def _get_folderInfo(self, node, nodeType, properties):
        folderInfo = self._get_metadata(node.elt, properties)
        folderInfo['type'] = nodeType
        folderInfo['children'] = [c.elt.get('name') for c in node.children]
        return folderInfo
    
    def expandNode_template(self, node):
        # Map the URL attr to the value array attr
        elt = node.elt
        if node.children:
            raise ExpandToolboxException("Node %r has children: " % (elt,))
        if not nowrite:
            newDict = {'type': elt.tag}
            newDict.update(elt.attrib)
            if newDict.has_key('url'):
                payload = newDict['url']
                del newDict['url']
            else:
                payload = elt.text + elt.tail
            lines = self._split_newlines(payload.strip())
            if not lines[-1]:
                del lines[-1]
            if not lines[0]:
                del lines[0]
            newDict['value'] = lines
            self._writeOutItem(node, newDict)

    def expandNode_DirectoryShortcut(self, node):
        # These are converted into macros in v6
        newDict = {'type': 'macro',
                   }
        newDict.update(node.elt.attrib)
        newDict.update({
            "language": "JavaScript",
            "trigger_enabled": "0",
            "rank": "100",
            "async": False,
            "type": "macro",
            "icon": "chrome://komodo/skin/images/open.png",
            })
        url = newDict['url']
        del newDict['url']
        newDict['value'] = [url]
        self._writeOutItem(node, newDict)
        
    def expandNode_menu(self, node):
        self.expandContainerNode(node,
                self._get_folderInfo(node, 'menu', ['accesskey', 'priority']))
        
    def expandNode_toolbar(self, node):
        self.expandContainerNode(node,
                self._get_folderInfo(node, 'toolbar', ['priority']))
        
    def expandNode_project(self, node):
        self._expand_children(node)
        
    def expandNode_webservice(self, node):
        # Support older project files, but filter this out.
        self.obsoleteItems.append(('webservice', node.elt.attrib['name'], os.getcwd()))
        
    def expandNode_file(self, node):
        self.obsoleteItems.append(('file', node.elt.attrib['name'], os.getcwd()))
        
    def expandNode_livefolder(self, node):
        self.obsoleteItems.append(('livefolder', node.elt.attrib['name'], os.getcwd()))
        
    def expandNode_changelist(self, node):
        self.obsoleteItems.append(('changelist', node.elt.attrib['name'], os.getcwd()))
        
    def _split_newlines(self, value):
        return re.split('\r?\n', value)
        
    def _writeOutItem(self, node, newDict):
        q_filename = self._prepareUniqueFileSystemName(node)
        try:
            del newDict['id']
        except KeyError:
            pass
        #log.debug("Writing file %s in dir %s", q_filename, os.getcwd())        
        f = open(q_filename, "w")
        json.dump(newDict, f, ensure_ascii=True, indent=2)
        f.close()
    
    def expandItem(self, node, tagName):
        elt = node.elt
        if node.children:
            raise ExpandToolboxException("Node %r has children: " % (elt,))
        if not nowrite:
            newDict = {'type': tagName}
            newDict.update(elt.attrib)
            value = elt.text + elt.tail
            if _kpf_version <= 3 and tagName in ('macro', 'snippet'):
                #log.debug("Unescaping the whitespace in %s %s", tagName, newDict['name'])
                value = unescapeWhitespace(value)
            lines = self._split_newlines(value)
            if not lines[-1]:
                del lines[-1]
            if not lines[0]:
                del lines[0]
            newDict['value'] = lines
            self._writeOutItem(node, newDict)
        
    def expandTree(self, node):
        tagName = node.elt.tag
        method = getattr(self, 'expandNode_' + tagName, None)
        try:
            if method:
                method(node)
            else:
                self.expandItem(node, tagName)
        except KeyError:
            try:
                name = node.elt.get('name')
            except:
                name = "<unknown name>"
            log.exception("Failed to expand item %s:%s", tagName, name)
    
