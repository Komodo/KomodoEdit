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

"""Services for using templates in Komodo.
Particularly the "New File" dialog.
"""
#TODO:
#  - mechanism to get the "My Templates" stuff into the user folder on
#    a clean first start

import os
import sys
import re
import types
import logging
import copy
from pprint import pprint
import operator

from xpcom import components
from xpcom.server import WrapObject, UnwrapObject
from koTreeView import TreeView


log = logging.getLogger("templates")
#log.setLevel(logging.DEBUG)


class TemplateServiceError(Exception):
    pass


class Node(dict):
    """A Node is one node in the tree of "Categories" in Komodo "New File"
    dialog.
    """
    def __init__(self):
        self.files = []

    def isContainer(self):
        return len(self.keys()) > 0

    _ambiguous_language_names = ('JavaScript', 'Python', 'HTML')
    _filenames_by_path = {}
    def addTemplate(self, path):
        name = _templateNameFromPath(path)
        langRegistrySvc = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                          getService(components.interfaces.koILanguageRegistryService)
        fileNameLanguage = langRegistrySvc.suggestLanguageForFile(path)
        if fileNameLanguage in self._ambiguous_language_names:
            if path in self._filenames_by_path:
                fileNameLanguage = self._filenames_by_path[path]
            else:
                try:
                    fd = open(path, 'r')
                    buffer = "".join(fd.readlines()[:2])
                    fd.close()
                    candidateLanguages = langRegistrySvc.guessLanguageFromContents(buffer, "")
                    if candidateLanguages:
                        fileNameLanguage = candidateLanguages[0]
                        self._filenames_by_path[path] = fileNameLanguage
                except:
                    log.exception("Error determining actual language for file %s", path)
                    pass
        fdata = {"path": path,
                 "template-name": name,
                 "language": fileNameLanguage,
                 "sort-key": name.lower()}
        self.files.append(fdata)

    def sort(self):
        """Recursively sort the files at each level.
        Sorting is based on the file *base* name.
        """
        self.files.sort(key=operator.itemgetter('sort-key'))
        for name, child_node in self.items():
            child_node.sort()

    def dump(self, level=0):
        basenames = [os.path.basename(f['path']) for f in self.files]
        print "files=%s" % basenames
        for name, node in self.items():
            print "%sNode '%s':" % ("  "*level, name),
            node.dump(level+1)


class KoTemplateService:
    type = "file"
    _com_interfaces_ = [components.interfaces.koITemplateService]
    _reg_clsid_ = "{93d38c0c-3473-11db-8565-000d935d3368}"
    _reg_contractid_ = "@activestate.com/koTemplateService?type=%s;1" % type
    _reg_desc_ = "Komodo File Template Service"
    
    basename = "templates"
    sampleTemplateName = "Sample Custom Template.txt"
    sampleTemplate = """
        This is a sample custom template for Komodo. The actual template file is:
    %s

You can create your own templates with any content you wish.
See "Custom Templates" in Komodo's on-line help for more details.
"""
    readmeText = """
        Komodo User File Templates Directory

Place template files in the "My Templates" folder to have them appear
in Komodo's "New File" dialog.  Your custom templates will appear along
with Komodo's standard set of template files.

To create your own templates files, create a file in Komodo and select
"File | Save As Template..." or simply copy files into the "My Templates"
folder.

See "Custom Templates" in Komodo's on-line help for more information.
"""

    def __init__(self):
        self.koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        self.rootTemplateNode = None
        self.loaded = 0
        self.initializeUserTemplateTree()

    def initializeUserTemplateTree(self):
        """Create an empty personal templates tree if there isn't one.
        
        <AppDataDir>/
            templates/
                ReadMe.txt
                My Templates/
                    Sample Custom Template.txt
        """
        try:
            templatesDir = self.getUserTemplatesDir()
            if os.path.exists(templatesDir):
                return
            mytemplatesDir = os.path.join(templatesDir, "My Templates")
            os.makedirs(mytemplatesDir)
            
            readmeTxt = os.path.join(templatesDir, "ReadMe.txt")
            freadme = open(readmeTxt, 'w')
            freadme.write(self.readmeText)
            freadme.close()
            
            sampleTxt = os.path.join(mytemplatesDir, self.sampleTemplateName)
            fsample = open(sampleTxt, "w")
            fsample.write((self.sampleTemplate % sampleTxt).encode('utf8'))
            fsample.close()

        except EnvironmentError, ex:
            log.exception(ex)
            prompt = components.classes["@mozilla.org/embedcomp/prompt-service;1"]\
                 .getService(components.interfaces.nsIPromptService)
            prompt.alert(None, "Template Service Error",
                         """There was an error initializing your Komodo user 
settings directory with %s template information: %s. 
This may mean that you will not be able to create 
your own custom %s templates. You will still be able 
to use Komodo's numerous standard %s templates.""" % (self.type, str(ex), self.type, self.type));

    def _load_walk(self, dname, node):
        log.debug("load templates from `%s'", dname)
        for f in os.listdir(dname):
            path = os.path.join(dname, f)
            if f == ".consign": # Dev build support: skip .consign files.
                continue
            if os.path.isdir(path):
                if f not in node:
                    node[f] = Node()
                self._load_walk(path, node[f])
            elif os.path.isfile(path):
                node.addTemplate(path)

    def _genTemplateDirs(self):
        """Yield all possible templates dirs.
        
        This doesn't bother checking if they exist.
        """
        from directoryServiceUtils import getExtensionDirectories
        yield self.getUserTemplatesDir()
        yield self.getSharedTemplatesDir()
        for extensionDir in getExtensionDirectories():
            yield os.path.join(extensionDir, self.basename)
        yield self.getDefaultTemplatesDir()

    def loadTemplates(self):
        """Load template tree from disk."""
        log.info("loading templates")
        self.rootTemplateNode = Node()
        for templateDir in self._genTemplateDirs():
            if not os.path.exists(templateDir):
                continue
            self._load_walk(templateDir, self.rootTemplateNode)
        log.debug("sort template tree")
        self.rootTemplateNode.sort()
        #self.rootTemplateNode.dump()
        self.loaded = 1

    def getTemplateTree(self): # Not in IDL
        """Return a copy of the template tree."""
        if not self.loaded:
            raise TemplateServiceError("You must call .loadTemplates() "
                                       "before .getTemplateTree().")
        return copy.deepcopy(self.rootTemplateNode)

    def dumpTemplates(self):
        """Dump the currently loaded template tree."""
        print "Template Tree:",
        self.rootTemplateNode.dump(1)

    def getDefaultTemplatesDir(self):
        return os.path.join(self.koDirSvc.supportDir, "default-%s" % self.basename)

    def getUserTemplatesDir(self):
        return os.path.join(self.koDirSvc.userDataDir, self.basename)

    def getSharedTemplatesDir(self):
        return os.path.join(self.koDirSvc.commonDataDir, self.basename)

    def walkFuncForKPZOnly(self, dirname):
        items = []
        fnames = os.listdir(dirname)
        for f in fnames:
            path = os.path.join(dirname, f)
            if f.endswith(".kpz"):
                items.append(path)
            elif os.path.isdir(path):
                items += self.walkFuncForKPZOnly(path)
        return items

    def walkFuncForKPZ(self, dirname):
        if not os.path.exists(dirname):
            return []
        fnames = os.listdir(dirname)
        finalItems = []
        for f in fnames:
            path = os.path.join(dirname, f)
            if os.path.isdir(path):
                items = self.walkFuncForKPZOnly(path)
                if items:
                    items.sort()
                    finalItems.append([f, items])
        return finalItems

    def _getLeaves(self, tree):
        leaves = []
        headers = []
        for node in tree:
            headers.append(node[0])
            leaves += node[1]
        return headers, leaves
    
    
    def _sortPaths(self, pathList):
        sortPathPtn = re.compile(r'([\W\D]*\w*)(\d*)(.*)')
        fixedPathTuples = []
        for p in pathList:
            basename = os.path.basename(p)
            m = sortPathPtn.match(basename)
            if m:
                fixedPathTuples.append((m.group(1).lower(),
                                        int(m.group(2) or "0"),
                                        m.group(3).lower(),
                                        p))
            else:
                fixedPathTuples.append((basename(), 0, "", p))
        return [tup[3] for tup in sorted(fixedPathTuples)]

    def _getJSONTreeData(self):
        items = self.walkFuncForKPZ(self.getDefaultTemplatesDir())
        headers, leaves = self._getLeaves(items)
        systemItems = leaves
        userItems = []
        #candidates = ['Komodo', 'Common'];
        #if len(leaves) <= 8:
        #    for x in candidates:
        #        if x in headers:
        #            header = x
        #            break
        #    else:
        #        header = candidates[0]
        #    finalItems = [[header, leaves]]
        #else:
        #    finalItems = [items]

        items = self.walkFuncForKPZ(self.getUserTemplatesDir())
        if items:
            headers, leaves = self._getLeaves(items)
            userItems += leaves
            
        from directoryServiceUtils import getExtensionDirectories
        for extensionDir in [d for d in getExtensionDirectories()
                             if os.path.isdir(d)]:
            items = self.walkFuncForKPZ(extensionDir)
            if items:
                headers, leaves = self._getLeaves(items)
                systemItems += leaves

        sharedDir = self.getSharedTemplatesDir()
        if sharedDir:
            items = self.walkFuncForKPZ(sharedDir)
            if items:
                headers, leaves = self._getLeaves(items)
                systemItems += leaves
        return [self._sortPaths(systemItems), self._sortPaths(userItems)]
        
    def getJSONTree(self):
        import json
        return json.dumps(self._getJSONTreeData())

class KoProjectTemplateService(KoTemplateService):
    type = "project"
    _com_interfaces_ = [components.interfaces.koITemplateService]
    _reg_clsid_ = "{a1f786ee-3473-11db-8565-000d935d3368}"
    _reg_contractid_ = "@activestate.com/koTemplateService?type=%s;1" % type
    _reg_desc_ = "Komodo Project Template Service"

    basename = "project-templates"
    sampleTemplateName = "Sample Custom Template.xml"
    sampleTemplate = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Komodo Project File - DO NOT EDIT -->
<project id="e6577ca4-3483-11db-bfd4-000d935d3368" name="Sample Custom Template.kpf" kpf_version="3">
<snippet keyboard_shortcut="" name="ReadMe" set_selection="false" idref="e6577ca4-3483-11db-bfd4-000d935d3368" id="f6b2361a-3483-11db-bfd4-000d935d3368" indent_relative="false">
This is a sample custom template for Komodo. The actual template file is:\\n    %s\\n\\nYou can create your own templates with any content you wish.\\nSee "Custom Templates" in Komodo's on-line help for more details.\\n!@#_currentPos!@#_anchor</snippet>
<preference-set idref="e6577ca4-3483-11db-bfd4-000d935d3368">
  <boolean id="import_live">1</boolean>
</preference-set>
</project>"""
    readmeText = """
        Komodo User Project Templates Directory

Place template files in the "My Templates" folder to have them appear
in Komodo's "New Project" dialog.  Your custom templates will appear along
with Komodo's standard set of templates.

To create your own templates files, create a file in Komodo and select
"Projects | Save As Template..." or simply copy files into the "My Templates"
folder.

See "Custom Templates" in Komodo's on-line help for more information.
"""

    def __init__(self):
        KoTemplateService.__init__(self)


class KoTemplatesView(TreeView):
    _com_interfaces_ = [components.interfaces.koITemplatesView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{53F98D02-237E-417C-A298-D8089AE516D2}"
    _reg_contractid_ = "@activestate.com/koTemplatesView;1"
    _reg_desc_ = "Komodo Templates nsITreeView"

    def __init__(self):
        TreeView.__init__(self) #, debug="templates") #XXX
        self._data = []
        self._tree = None
        self._sortedBy = None
        self.atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self.defaultLanguageAtom = self.atomSvc.getAtom("DefaultLanguage")

    def setData(self, data):
        # Called by the template categories view when its selection changes.
        self._data = data
        if self.log:
            self.log.debug('setData %r', data)
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0,len(self._data));
        self._tree.endUpdateBatch()
        
    def getSelectedTemplate(self):
        index = self._tree.view.selection.currentIndex
        return self._data[index]["path"]

    #---- nsITreeView methods
    def get_rowCount(self):
        if self.log:
            self.log.debug("row count %d", len(self._data))
        return len(self._data)

    def getCellText(self, row, column):
        if self.log:
            self.log.debug("getCellText %d:%s", row, column.id)
        try:
            datum = self._data[row][column.id]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/show_bug.cgi?id=27487
            #log.error("no %sth result" % row)
            return ""
        except KeyError:
            log.error("unknown template column id: '%s'" % column.id)
            return ""
        if type(datum) not in (types.StringType, types.UnicodeType):
            datum = str(datum)
        return datum

    def hasNextSibling(self, rowIndex, afterIndex):
        """From the nsITreeView.idl docs:
        
        HasNextSibling is used to determine if the row at rowIndex has a
        nextSibling that occurs *after* the index specified by
        afterIndex.  Code that is forced to march down the view looking
        at levels can optimize the march by starting at afterIndex+1.
        """
        if afterIndex+1 >= len(self._data):
            return 0
        else:
            return 1

    def _getCellPropertiesNames(self, row, column):
        # Add a default language image.
        names = ["DefaultLanguage"]
        try:
            # Add individual language icon if we have one.
            lang = self._data[row]['language']
            if lang:
                # Remove some special chararacters from the language name, so
                # it can be styled via CSS.
                lang = lang.replace("+", "").replace(".", "")
                names.append("Language" + lang)
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/show_bug.cgi?id=27487
            #log.error("no %sth result" % row)
            pass
        return names

    def getCellProperties_Old(self, row, column, names, properties):
        for name in names:
            atom = self.atomSvc.getAtom(name)
            if atom is not None:
                properties.AppendElement(atom)

    def getCellProperties(self, row, column, properties=None):
        names = self._getCellPropertiesNames(row, column)
        if properties is not None:
            self.getCellProperties_Old(row, column, names, properties)
            return
        # Mozilla 22+ does not have a properties argument.
        return " ".join(names)

class KoTemplateCategoriesView(TreeView):
    _com_interfaces_ = [components.interfaces.koITemplateCategoriesView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{0723776F-EE9D-4F20-B438-3AF893192346}"
    _reg_contractid_ = "@activestate.com/koTemplateCategoriesView;1"
    _reg_desc_ = "Komodo Template Categories nsITreeView"

    def __init__(self):
        TreeView.__init__(self) #, debug="categories") #XXX
        self._tree = None
        self._sortedBy = None
        # The table used to fill in the tree. It is a list of dicts. Each
        # dict represents one row in the tree/outliner. This dictionary is
        # also (because it is convenient) used to store data in addition to
        # the named rows of the XUL tree. e.g.,
        #  [ {"category-name": "My Templates",  # row 0
        #     "node": <Node instance for this category>},
        #    ... ]
        # This attribute is re-generated from self.templateTree whenever
        # the rows change (say, by the user opening a category with
        # sub-categories).
        self._data = []
        
        self._prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                        .getService().prefs # global prefs
        self.templateTree = None # Working copy of template tree Nodes.
        self.selectedTemplateByCategory = None
        self.categoryIsOpen = None
        self.atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self.folderOpenAtom = self.atomSvc.getAtom("folderOpen")
                               
        self.folderClosedAtom = self.atomSvc.getAtom("folderClosed")

    def initialize(self, templateSvc, templatesView):
        # Need to unwrap these Python XPCOM object because we access
        # methods on them that are not in the IDL.
        self.templateSvc = UnwrapObject(templateSvc)
        self.templatesView = UnwrapObject(templatesView)
        
        if not self.templateSvc.loaded:
            self.templateSvc.loadTemplates()
        self.templateTree = self.templateSvc.getTemplateTree() # a working copy
        
        # Restore the user selections from prefs
        stbcStr = self._prefSvc.getStringPref("%s_selected_template_by_category" % self.templateSvc.basename)
        try:
            self.selectedTemplateByCategory = eval(stbcStr)
        except SyntaxError, ex:
            self.selectedTemplateByCategory = {}
        ocStr = self._prefSvc.getStringPref("%s_open_categories" % self.templateSvc.basename)
        try:
            self.categoryIsOpen = eval(ocStr)
        except SyntaxError, ex:
            self.categoryIsOpen = {}

        self._updateRowData()

    def saveSelections(self):
        # Persist the user selections in prefs.
        row = self.selection.currentIndex
        self._prefSvc.setStringPref("%s_selected_category" % self.templateSvc.basename,
                                    self._data[row]["category-name"])
        self._prefSvc.setStringPref("%s_selected_template_by_category" % self.templateSvc.basename,
                                    repr(self.selectedTemplateByCategory))
        self._prefSvc.setStringPref("%s_open_categories" % self.templateSvc.basename,
                                    repr(self.categoryIsOpen))

    def templateSelectionChanged(self):
        tindex = self.templatesView.selection.currentIndex
        index = self.selection.currentIndex
        if index < 0 or len(self._data) <= index:
            return
        cdict = self._data[self.selection.currentIndex]
        categoryPath = cdict["category-path"]
        try:
            templateName = cdict["node"].files[tindex]["template-name"]
        except IndexError: # if no template for this category, tindex==0
            pass
        else:
            if self.log:
                self.log.debug("remember user last selected '%s' template for '%s' "
                      "category", templateName, categoryPath)
            self.selectedTemplateByCategory[categoryPath] = templateName
    

    def getDefaultCategoryIndex(self):
        selectedCategory = self._prefSvc.getStringPref("%s_selected_category" % self.templateSvc.basename)
        for index in range(len(self._data)):
            if self._data[index]["category-name"] == selectedCategory:
                break
        else:
            index = 0 # default to first row
        if self.log:
            self.log.debug("getDefaultCategoryIndex: '%s' (index %s)",
                  selectedCategory, index)
        return index

    def getDefaultTemplateIndex(self):
        index = self.selection.currentIndex
        if index < 0 or len(self._data) <= index:
            return 0
        cdict = self._data[self.selection.currentIndex]
        categoryPath = cdict["category-path"]
        try:
            templateName = self.selectedTemplateByCategory[categoryPath]
        except KeyError:
            templateName = ""
            index = 0 # default to first row
        else:
            files = cdict["node"].files
            for index in range(len(files)):
                if files[index]["template-name"] == templateName:
                    break
            else:
                index = 0 # default to first row
        # Note: index==0 seems to work to select nothing if there are no
        # templates for this category.
        if self.log:
            self.log.debug("getDefaultTemplateIndex: '%s' (index %s, category '%s')",
                  templateName, index, categoryPath)
        return index

    def _getCategoryRows(self, rows, node, level=0, parentIndex=-1, path=[]):
        subnames = node.keys()
        subnames.sort()
        for subname in subnames:
            subnode = node[subname]
            subpath = list(path) # get a copy
            subpath.append(subname)
            categoryPath = '/'.join(subpath)
            cdict = {"category-name": subname,
                     "category-path": categoryPath,
                     "node": subnode,
                     "level": level,
                     "parent-index": parentIndex}
            rows.append(cdict)
            if self.categoryIsOpen.get(categoryPath, 0):
                self._getCategoryRows(rows, subnode, level=level+1,
                                      parentIndex=len(rows)-1, path=subpath)

    def _updateRowData(self):
        """Update self._data for changes in the XUL tree rows or new source
        data.
        """
        if not self.templateTree:
            raise TemplateServiceError("Cannot get category rows before "
                                       "loading from disk.")
        rows = []
        self._getCategoryRows(rows, self.templateTree)
        self._data = rows
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0,len(self._data));
        self._tree.endUpdateBatch()

    #---- nsITreeView methods
    def get_rowCount(self):
        if self.log:
            self.log.debug("rowCount %d", len(self._data))
        return len(self._data)

    def getCellText(self, row, column):
        if self.log:
            self.log.debug("getCellText %d:%s", row, column.id)
        try:
            datum = self._data[row][column.id]
        except IndexError:
            log.error("no %sth find result" % row)
            return ""
        except KeyError:
            log.error("unknown category column id: '%s'" % column.id)
            return ""
        if type(datum) not in (types.StringType, types.UnicodeType):
            datum = str(datum)
        return datum

    def isContainer(self, row):
        if self.log:
            self.log.debug("isContainer %d", row)
        return self._data[row]["node"].isContainer()

    def isContainerEmpty(self, row):
        return 0

    def isContainerOpen(self, row):
        if self.log:
            self.log.debug("isContainerOpen %d", row)
        categoryPath = self._data[row]["category-path"]
        return self.categoryIsOpen.get(categoryPath, 0)

    def toggleOpenState(self, row):
        if self.log:
            self.log.debug("toggleOpenState %d", row)
        categoryPath = self._data[row]["category-path"]
        isOpen = self.categoryIsOpen.get(categoryPath, 0)
        self.categoryIsOpen[categoryPath] = not isOpen

        # Update row data.
        self._updateRowData()
        self.selection.currentIndex = row
        self.selection.select(row);        

    def getParentIndex(self, row):
        if self.log:
            self.log.debug("getParentIndex %d", self._data[row]["parent-index"])
        return self._data[row]["parent-index"]

    def getLevel(self, row):
        if self.log:
            self.log.debug("getLevel %d", self._data[row]["level"])
        return self._data[row]["level"]

    def selectionChanged(self):
        if self.log:
            self.log.debug("selectionChanged")
        index = self.selection.currentIndex
        if index < 0 or len(self._data) <= index:
            return
        cdict = self._data[index]
        self.templatesView.setData(cdict["node"].files)

    def getCellProperties_Old(self, row, column, properties):
        categoryPath = self._data[row]["category-path"]
        if self.categoryIsOpen.get(categoryPath, 0):
            properties.AppendElement(self.folderOpenAtom)
        else:
            properties.AppendElement(self.folderClosedAtom)

    def getCellProperties(self, row, column, properties=None):
        if properties is not None:
            self.getCellProperties_Old(row, column, properties)
            return
        categoryPath = self._data[row]["category-path"]
        if self.categoryIsOpen.get(categoryPath, 0):
            return "folderOpen"
        return "folderClosed"

    def hasNextSibling(self, rowIndex, afterIndex):
        """From the nsITreeView.idl docs:
        
        HasNextSibling is used to determine if the row at rowIndex has a
        nextSibling that occurs *after* the index specified by
        afterIndex.  Code that is forced to march down the view looking
        at levels can optimize the march by starting at afterIndex+1.
        """
        if afterIndex+1 >= len(self._data):
            return 0
        else:
            return (self._data[rowIndex]["parent-index"]
                    == self._data[afterIndex+1]["parent-index"])


#---- internal support stuff

def _templateNameFromPath(path):
    """Determine a name for the given template path. Typically this is just
    the basename with the extension dropped. However, we also attempt to
    handle cases where the extension might include multiple parts or the
    template name might include a '.'.
    """
    base = os.path.basename(path)
    if '.' not in base:
        return base

    name, ext = os.path.splitext(base)
    if ext == ".erb":  # Bug 74706: Usage of .$format.erb in Rails 2.
        name, _ = os.path.splitext(name)
    elif ext == ".html":
        # Might be one of Komodo's multipart extensions for HTML template
        # filetypes.
        multipartExts = [
            ".django",   # .django.html
            ".mason",    # .mason.html
            ".ttkt",     # .ttkt.html
        ]
        for me in multipartExts:
            if name.endswith(me):
                name, _ = os.path.splitext(name)
                break
    return name


if __name__ == "__main__":
    templateSvc = components.classes["@activestate.com/koTemplateService?type=file;1"].getService()
    templateSvc.loadTemplates()
    templateSvc.dumpTemplates()

    templateSvc = components.classes["@activestate.com/koTemplateService?type=project;1"].getService()
    templateSvc.loadTemplates()
    templateSvc.dumpTemplates()
