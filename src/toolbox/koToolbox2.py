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

"""Backend for new Komodo toolbox 

See KD 252 for details.

"""
import fileutils
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

try:
    from xpcom import components
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

if not _xpcom_:
    logging.basicConfig()
log = logging.getLogger("koToolbox2")
#log.setLevel(logging.DEBUG)
eol = """
"""
_unsupported_types = ("file", "livefolder")

# for the std toolbox, shared toolboxes, and extensions
# DEPENDENCY: toolbox2.p.js::initialize also defines this value
DEFAULT_TARGET_DIRECTORY = "tools"
# for toolboxes extracted from pre-v6 kpf files:
PROJECT_TARGET_DIRECTORY = ".komodotools"

TOOL_EXTENSION = ".komodotool"
TOOL_EXTENSION_CLEAN = ".ktf"
UI_FOLDER_FILENAME = ".folderdata"
PROJECT_FILE_EXTENSION = ".komodoproject"

TOOL_META_START = "komodo tool: "

#---- errors

class Toolbox2Error(Exception):
    pass



#---- main module classes

class Database(object):
    """Wrapper API for the sqlite database of the history."""
    # Database version.
    # VERSION is the version of this Database code. The property
    # "version" is the version of the database on disk. The patch-level
    # version number should be used for small upgrades to the database.
    #
    # How to update version:
    # (a) change VERSION,
    # (b) add a change log comment here, and
    # (c) add an entry to `_upgrade_info_from_curr_ver`.
    #
    # db change log (for Database and ToolboxLoader):
    # - 1.0.5: initial version (due to copy/paste error)
    # - 1.0.6: convert DirectoryShortcut tools into specialized macros
    # - 1.0.7: signal change in items: items get their own versions
    # - 1.0.8: remove version fields from the misc_properties table.
    # - 1.0.9: signal change in items: removing id's
    # - 1.0.10: remove .svn folders, etc., from the toolbox database.
    # - 1.0.11: add auto_abbreviation property to snippets, default is false
    # - 1.0.12: signal change moving from 11 to 12, to update tool item versions,
    #           and add auto_abbreviation fields to snippets
    # - 1.0.13: add treat_as_ejs property to snippets, default is false
    # - 1.1.5:  add language field to snippets
    # - 1.1.6:  add is_clean column
    # - 1.1.7:  add file template table
    # - 1.1.8:  convert old tools
    # - 1.1.9:  import sample file templates
    VERSION = "1.1.9"
    FIRST_VERSION = "1.0.5"
    
    def __init__(self, db_path, schemaFile):
        self.path = db_path
        self.cu = self.cx = None
        self.schemaFile = schemaFile
        self.item_version_changed = False

        self.observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)

        if not exists(db_path):
            self.create()
        elif os.path.getsize(db_path) == 0:
            os.unlink(db_path)
            self.create()
        else:
            try:
                self.upgrade()
            except Exception, ex:
                log.exception("error upgrading `%s': %s", self.path, ex)
                self.reset()
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        ptnString = r"%s%sSamples[ _\(]+[\d_.]+.*?%sAbbreviations" % \
            (re.escape(join(koDirSvc.userDataDir, DEFAULT_TARGET_DIRECTORY)),
             os.path.sep,
             os.path.sep)
        self._sampleAbbrevRE = re.compile(ptnString, re.IGNORECASE)

        self._specific_names = {
            'command':['insertOutput', 'parseRegex', 'operateOnSelection',
                     'doNotOpenOutputWindow', 'showParsedOutputList',
                     'parseOutput', 'runIn', 'cwd', 'env', ],
            'macro':['async', 'trigger_enabled', 'trigger',
                          'language', 'rank'],
            'snippet':['set_selection', 'indent_relative', 'auto_abbreviation',
                       'treat_as_ejs', 'language'],
            'template':['treat_as_ejs', 'language', 'lang_default'],
            'menu':['accesskey', 'priority'],
            'toolbar':['priority'],
            'folder':[],
            }

    def _add_is_clean(self, curr_ver, result_ver):
        with self.connect(commit=True) as cu:
            cu.execute("ALTER TABLE common_details ADD COLUMN is_clean bool DEFAULT false")

    def _transition_file_templates(self, curr_ver, result_ver):
        self._add_file_template_table(curr_ver, result_ver)

        with self.connect(commit=True) as cu:
            cu.execute("DELETE FROM common_details WHERE type='template'")

        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir

        templatesDir = os.path.join(currUserDataDir, "templates")
        targetDir = os.path.join(currUserDataDir, "tools", "File Templates")

        if os.path.exists(templatesDir):
            if not os.path.exists(targetDir):
                os.makedirs(targetDir)

            toolbox2Svc = components.classes["@activestate.com/koToolbox2Service;1"]\
                            .getService(components.interfaces.koIToolbox2Service)

            try:
                toolbox2Svc.convertToTemplate(templatesDir, targetDir)

                readme = os.path.join(targetDir, "ReadMe.ktf")
                sample = os.path.join(targetDir, "My Templates", "Sample Custom Template.ktf")

                if os.path.isfile(readme):
                    os.remove(readme)

                if os.path.isfile(sample):
                    os.remove(sample)
            except:
                log.exception("Failed converting old templates")

    def _import_files_templates(self, curr_ver, result_ver):
        koDirs = components.classes["@activestate.com/koDirs;1"].\
                 getService(components.interfaces.koIDirs)
        destDir = os.path.join(koDirs.userDataDir, 'tools')
        srcDir = os.path.join(koDirs.supportDir, 'samples', 'tools', 'File Templates')

        if not os.path.isdir(os.path.join(destDir, 'File Templates')):
            import fileutils
            try:
                fileutils.copyLocalFolder(srcDir, destDir)
            except:
                log.exception("Failed to copy srcChild:%s to dest destDir:%s", srcDir, destDir)
        else:
            import shutil
            destDir = os.path.join(destDir, 'File Templates')
            for name in os.listdir(srcDir):
                srcChild = os.path.join(srcDir, name)
                try:
                    shutil.copy(srcChild, destDir)
                except:
                    log.exception("Failed to copy srcChild:%s to dest destDir:%s", srcChild, destDir)

    def _convert_komodotool_to_ktf(self, curr_ver, result_ver):
        toolbox2Svc = components.classes["@activestate.com/koToolbox2Service;1"]\
                            .getService(components.interfaces.koIToolbox2Service)

        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir

        toolsDir = os.path.join(currUserDataDir, "tools")

        toolbox2Svc.convertOldFormat(toolsDir, True)

    def _add_file_template_table(self, curr_ver, result_ver):
        """
        Add file template table
        """
        with self.connect(commit=True) as cu:
            cu.execute("create table template (\
                        path_id INTEGER PRIMARY KEY NOT NULL,\
                        treat_as_ejs bool default false,\
                        lang_default bool default false,\
                        language text)")
            
    def __repr__(self):
        return "<Toolbox2 Database %s>" % self.path
    
    # Do this to wrap large numbers of transactions
    def establishConnection(self):
        self.cx = sqlite3.connect(self.path)
        self.cu = self.cx.cursor()

    def releaseConnection(self):
        self.cx.commit()
        self.cu.close()
        self.cx.close()
        self.cu = self.cx = None
            
    @contextmanager
    def connect(self, commit=False, cu=None):
        if self.cu:
            yield self.cu
        elif cu is not None:
            yield cu
        else:
            cx = sqlite3.connect(self.path)
            # This is required
            cx.text_factory = lambda x:unicode(x, "utf-8", "ignore")
            cu = cx.cursor()
            try:
                yield cu
            finally:
                if commit:
                    cx.commit()
                cu.close()
                cx.close()

    def create(self):
        """Create the database file."""
        #TODO: error handling?
        with self.connect(commit=True) as cu:
            f = open(self.schemaFile, 'r')
            cu.executescript(f.read())
            f.close()
            self.set_meta("version", self.VERSION, cu=cu)
            
    def reset(self, backup=True):
        """Remove the current database (possibly backing it up) and create
        a new empty one.

        @param backup {bool} Should the original database be backed up.
            If so, the backup is $database_file+".bak". Default true.
        """
        import editorhistory
        if backup:
            backup_path = self.path + ".bak"
            if exists(backup_path):
                editorhistory._rm_file(backup_path)
            if exists(backup_path): # couldn't remove it
                log.warn("couldn't remove old '%s' (skipping backup)",
                         backup_path)
                editorhistory._rm_file(self.path)
            else:
                os.rename(self.path, backup_path)
        else:
            editorhistory._rm_file(self.path)
        self.create()

    def upgrade(self):
        """Upgrade the current database."""
        # 'version' is the DB ver on disk, 'VERSION' is the target ver.
        curr_ver = self.get_meta("version", self.FIRST_VERSION)
        starting_ver = curr_ver
        while curr_ver != self.VERSION:
            try:
                result_ver, upgrader, upgrader_arg \
                    = self._upgrade_info_from_curr_ver[curr_ver]
            except KeyError:
                log.info("cannot upgrade from v%s - no upgrader for this version",
                         curr_ver)
                break
            else:
                log.info("upgrading from db v%s to db v%s ...",
                         curr_ver, result_ver)
            if upgrader_arg is not None:
                upgrader(self, curr_ver, result_ver, upgrader_arg)
            else:
                upgrader(self, curr_ver, result_ver)
            curr_ver = result_ver
        if starting_ver != self.VERSION:
            self.update_meta("version", self.VERSION)

    def _delete_directory_shortcuts(self, curr_ver, result_ver):
        """These will be converted when the tools are
        reread into the database.
        """
        with self.connect(commit=True) as cu:
            cu.execute("select path_id from common_details where type = ?",
                       ("DirectoryShortcut",))
            path_ids = [row[0] for row in cu.fetchall()]
            log.info("Removing %d (ids:%s) directory shortcuts from the database",
                       len(path_ids), path_ids)
            for path_id in path_ids:
                self.deleteItem(path_id)
                         
    def _delete_version_field_from_misc_properties(self, curr_ver, result_ver):
        """
        In version 1.0.6, version fields ended up in the misc_properties
        table.  This was a mistake.
        """
        with self.connect(commit=True) as cu:
            cu.execute("delete from misc_properties where prop_name = ?",
                       ("version",))
            
    def _signal_item_version_change(self, curr_ver, result_ver):
        """Forces ToolboxLoader._testAndAddItem to update toolbox files when a
        new field is added. Assumes you added a function to
        ToolboxLoader._upgrade_item_info_from_curr_ver to add the field."""
        self.item_version_changed = True
        
    def _signal_check_remove_scc_dir(self, curr_ver, result_ver):
        # Always pull these folders out of the database
        pass

    def _add_auto_abbreviation_field_to_snippets(self, curr_ver, result_ver):
        """
        Add this field: auto_abbreviation bool default false
        """
        with self.connect(commit=True) as cu:
            cu.execute("alter table snippet add column auto_abbreviation bool default false")
        
    def _add_treat_as_ejs_to_snippets(self, curr_ver, result_ver):
        """
        Add this field: treat_as_ejs bool default false
        """
        with self.connect(commit=True) as cu:
            cu.execute("alter table snippet add column treat_as_ejs bool default false")
    

    def _add_lang_field_to_snippets_table(self, curr_ver, result_ver):
        """
        Add this field: language text default ""
        """
        self._signal_item_version_change(curr_ver, result_ver)
        with self.connect(commit=True) as cu:
            cu.execute("alter table snippet add column language text")

    _upgrade_info_from_curr_ver = {
        # <current version>: (<resultant version>, <upgrader method>, <upgrader args>)
        "1.0.5": ('1.0.6',  _delete_directory_shortcuts, None),
        "1.0.6": ('1.0.7',  _signal_item_version_change, None),
        "1.0.7": ('1.0.8',  _delete_version_field_from_misc_properties, None),
        "1.0.8": ('1.0.9',  _signal_item_version_change, None),
        "1.0.9": ('1.0.10', _signal_check_remove_scc_dir, None),
        "1.0.10": ('1.0.11', _add_auto_abbreviation_field_to_snippets, None),
        "1.0.11": ('1.0.12',  _signal_item_version_change, None),
        "1.0.12": ('1.0.13', _add_treat_as_ejs_to_snippets, None),
        "1.0.13": ('1.1.5', _add_lang_field_to_snippets_table, None),
        "1.1.5": ("1.1.6", _add_is_clean, None),
        "1.1.6": ("1.1.7", _transition_file_templates, None),
        "1.1.7": ("1.1.8", _convert_komodotool_to_ktf, None),
        "1.1.8": ("1.1.9", _import_files_templates, None),
    }

    def get_meta(self, key, default=None, cu=None):
        """Get a value from the meta table.
        
        @param key {str} The meta key.
        @param default {str} Default value if the key is not found in the db.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {str} The value in the database for this key, or `default`.
        """
        with self.connect(cu=cu) as cu:
            cu.execute("SELECT value FROM toolbox2_meta WHERE key=?", (key,))
            row = cu.fetchone()
            if row is None:
                return default
            return row[0]
            
    def set_meta(self, key, value, cu=None):
        """Set a value into the meta table.
        
        @param key {str} The meta key.
        @param value {str} The value to associate with the key.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {None}
        """
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute("INSERT INTO toolbox2_meta(key, value) VALUES (?, ?)", 
                (key, value))

    def update_meta(self, key, value, cu=None):
        with self.connect(commit=True, cu=cu) as cu:
            try:
                cu.execute("UPDATE toolbox2_meta SET value=? where key=?",
                           (value, key))
            except sqlite3.OperationalError:
                log.exception("Error updating meta table:%s")
                self.set_meta(key, value, cu)

    def del_meta(self, key):
        """Delete a key/value pair from the meta table.
        
        @param key {str} The meta key.
        """
        with self.connect(commit=True) as cu:
            cu.execute("DELETE FROM toolbox2_meta WHERE key=?", (key,))

    #---- Accessor functions
    
    _infoFromIdCache = None
    def getInfoFromIdMap(self, cu=None):
        """Return a dict mapping the tool id to toolbox relative
        path.
        """
        if self._infoFromIdCache is None:
            with self.connect(cu=cu) as cu:
                cu.execute("""select path_id, name from common_details""")
                nameFromId = dict((x[0], x[1]) for x in cu.fetchall())
                cu.execute("""select path_id, parent_path_id from hierarchy""")
                parentIdFromId = dict(cu.fetchall())
                infoFromId = self._infoFromIdCache = {}
                for id in nameFromId:
                    parents = [parentIdFromId[id]]
                    while parents[-1]:
                        parents.append(parentIdFromId[parents[-1]])
                    del parents[-1]
                    parents.reverse()
                    subDir = '/'.join(nameFromId[i] for i in parents
                        if nameFromId[i])
                    infoFromId[id] = (nameFromId[id], subDir)
        return self._infoFromIdCache
    
    def _resetInfoFromIdMap(self):
        self._infoFromIdCache = None
    
    def getTopLevelPaths(self):
        with self.connect() as cu:
            cu.execute('''select p.path
                from paths as p, hierarchy as h
                where h.parent_path_id is null
                      and h.path_id == p.id''')
            rows = cu.fetchall()
            return [row[0] for row in rows]

    def getTopLevelNodes(self):
        """
        Return (path_id, name, nodeType of each top-level item)
        """
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        stdToolboxDir = join(koDirSvc.userDataDir,
                             DEFAULT_TARGET_DIRECTORY)
        with self.connect() as cu:
            cu.execute('''select p.path, cd.path_id, cd.name, cd.type
                from common_details as cd, hierarchy as h, paths as p
                where h.parent_path_id is null
                      and h.path_id == cd.path_id
                      and h.path_id == p.id''')
            items = cu.fetchall()
        # Make sure the std toolbox shows up first
        final_items = []
        for i in range(len(items)):
            if items[i][0] == stdToolboxDir:
                final_items.append(items[i][1:])
                del items[i]
                break
        final_items += [item[1:] for item in items]
        return final_items

    def getRootIDInfo(self, id):
        with self.connect() as cu:
            cu.execute('''select h1.path_id, p1.path
                          from hierarchy as h1, paths as p1, paths as p2
                          where h1.parent_path_id is null
                                and h1.path_id = p1.id
                                and p2.id = ?
                                and p2.path like (p1.path || "%")''', (id,))
            return cu.fetchone()

    def getChildNodes(self, node_id):
        """
        Return (path_id, name, nodeType for each child)
        """
        with self.connect() as cu:
            cu.execute('''select cd.path_id, cd.name, cd.type
                from common_details as cd, hierarchy as h
                where h.parent_path_id == ? and cd.path_id == h.path_id''',
                       (node_id,))
            return cu.fetchall()
            
    def getChildIDs(self, node_id):
        with self.connect() as cu:
            cu.execute('''select path_id from hierarchy where parent_path_id == ?''',
                       (node_id,))
            return [x[0] for x in cu.fetchall()]

    def getChildPaths(self, node_id):
        with self.connect() as cu:
            cu.execute('''select p.path
                       from paths as p, hierarchy as h
                       where h.parent_path_id = ? and h.path_id = p.id''',
                       (node_id,))
            return [x[0] for x in cu.fetchall()]

    def getParentNode(self, node_id):
        """
        Return (path_id, name, nodeType for each child)
        """
        with self.connect() as cu:
            cu.execute('''select cd.path_id, cd.name, cd.type
                from common_details as cd, hierarchy as h
                where h.path_id == ? and cd.path_id == h.parent_path_id''',
                       (node_id,))
            return cu.fetchone()

    def getRootId(self, id):
        with self.connect() as cu:
            while True:
                stmt = 'select parent_path_id from hierarchy where path_id = ?'
                cu.execute(stmt, (id,))
                parent_id = cu.fetchone()[0]
                if parent_id is None or parent_id == id:
                    return id
                id = parent_id

    def getTypeAndNameFromId(self, node_id):
        """
        Return (nodeType, name based on the ID)
        """
        with self.connect() as cu:
            cu.execute('''select cd.name, cd.type
                from common_details as cd, hierarchy as h
                where h.parent_path_id == ? and cd.path_id == h.path_id''',
                       (node_id,))
            return cu.fetchall()

    def getValuesFromTableByKey(self, table_name, columnNames, keyName, keyValue, cu=None):
        stmt = "select %s from %s where %s = ?" % \
               (", ".join(columnNames), table_name, keyName)
        with self.connect(cu=cu) as cu:
            try:
                cu.execute(stmt, (keyValue,))
            except sqlite3.OperationalError:
                log.debug("Couldn't do [%s]", stmt)
                raise
            return cu.fetchone()

    def _convertAndJoin(self, names, sep):
        # Return a string of form <<"name1 = ? <sep> name2 = ? ...">>
        return sep.join([("%s = ?" % name) for name in names])
        
    def deleteRowByKey(self, table_name, key_names, key_values, cu=None):
        condition = " and ".join(["%s = ?" % kname for kname in key_names])
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute("delete from %s where %s" % (table_name, condition), key_values)

    def insertRowInTable(self, table_name, target_names, target_values, cu=None):
        cmd = "insert into %s (%s) values (%s)" % (table_name,
                                                   ", ".join(target_names),
                                                   ", ".join(['?'] * len(target_names)))
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute(cmd, target_values)

    def updateValuesInTableByKey(self, table_name, target_names, target_values,
                                 key_names, key_values, cu=None):
        target_names_str = self._convertAndJoin(target_names, ",")
        key_names_str = self._convertAndJoin(key_names, " AND ")
        cmd = 'update %s set %s where %s' % (table_name, target_names_str,
                                             key_names_str)
        args = tuple(target_values + key_values)
        with self.connect(commit=True, cu=cu) as cu:
            try:
                cu.execute(cmd, args)
            except sqlite3.OperationalError:
                log.exception("Couldn't do [%s](%s)", cmd, args)
                return False
            else:
                return True
            
    def get_id_from_path(self, path):
        stmt = "select id from paths where path = ?"
        with self.connect() as cu:
            cu.execute(stmt, (path,))
            row = cu.fetchone()
            if row is None: return None
            return row[0]
            
    def getPath(self, id, cu=None):
        stmt = "select path from paths where id = ?"
        with self.connect(cu=cu) as cu:
            cu.execute(stmt, (id,))
            row = cu.fetchone()
            if row is None: return None
            return row[0]

    def getCustomIconIfExists(self, path_id):
        with self.connect() as cu:
            cu.execute("""select prop_value from misc_properties
                          where path_id = ? and prop_name = ?""",
                       (path_id, 'icon'))
            row = cu.fetchone()
            if not row:
                return None
            return row[0]

    def getNextID(self, cu=None):
        with self.connect(cu=cu) as cu:
            cu.execute('select seq from sqlite_sequence where name=?', ('paths',))
            return cu.fetchone()[0] + 1
    
    # Adder functions

    def _addCommonDetails(self, path, name, item_type, is_clean, parent_path_id, cu):
        stmt = 'insert into paths(path) values(?)'
        cu.execute(stmt, (path,))
        id = cu.lastrowid
        stmt = '''insert into common_details
                (path_id, name, type, is_clean) values (?, ?, ?, ?)'''
        cu.execute(stmt, (id, name, item_type, is_clean))
        if parent_path_id is None and item_type == "folder":
            stmt = 'insert into hierarchy(path_id) values(?)'
            cu.execute(stmt, (id,))
        else:
            stmt = 'insert into hierarchy(path_id, parent_path_id) values(?, ?)'
            #log.debug("About to insert id:%r, parent_id:%r", id, parent_path_id)
            cu.execute(stmt, (id, parent_path_id))
        return id

    def addFolder(self, path, name, parent_path_id):
        #log.debug("About to add container %s in %s", name, path)
        with self.connect(commit=True) as cu:
            metadataPath = join(path, UI_FOLDER_FILENAME)
            if exists(metadataPath):
                try:
                    fp = open(metadataPath, 'r')
                    try:
                        data = json.load(fp, encoding="utf-8")
                    except:
                        log.exception("Couldn't load json data for path %s", path)
                        data = {}
                    fp.close()
                except:
                    log.error("Couldn't open path %s", metadataPath)
                else:
                    actual_name = data.get('name', None) or name
                    new_id = self._addCompoundItem(path, actual_name, data, parent_path_id, cu)
                    return new_id
            id = self._addCommonDetails(path, name, 'folder', False, parent_path_id, cu)
            return id

    def addContainerItem(self, data, item_type, path, fname, parent_path_id):
        with self.connect(commit=True) as cu:
            id = self._addCommonDetails(path, fname, item_type, False, parent_path_id, cu)
            names = self._specific_names[item_type]
            if names:
                final_values = [id]
                final_names = ['path_id']
                for name in names:
                    res = data.get(name, None)
                    if res is not None:
                        final_names.append(name)
                        final_values.append(res)
                questions = ", ".join(["?"] * (len(final_names)))
                stmt = 'insert into %s(%s) values(%s)' % \
                       (item_type, ", ".join(final_names), questions)
                cu.execute(stmt, final_values)
        return id
                
    def _addCompoundItem(self, path, name, data, parent_path_id, cu):
        node_type = data.get('type', 'folder')
        # Process the children in the directory
        id = self._addCommonDetails(path, name, node_type, False, parent_path_id, cu)
        if node_type == 'menu':
            stmt = 'insert into menu(path_id, accessKey, priority) values(?, ?, ?)'
            cu.execute(stmt, (id, data.get('accesskey', ""), data.get('priority', 100)))
        elif node_type == 'toolbar':
            stmt = 'insert into toolbar(path_id, priority) values(?, ?)'
            cu.execute(stmt, (id, data.get('priority', 100)))
        elif node_type == 'folder':
            pass
        else:
            log.error("Got an unexpected node type of %s", node_type)
        return id

    def finishAddingCompoundItem(self, item_type, id, name, path,
                                 attributes, parent_id):
        with self.connect(commit=True) as cu:
            self._addCommonDetails(path, name, item_type, False, parent_id, cu)
            names = self._specific_names[item_type]
    
    def addTool(self, data, item_type, path, fname, parent_path_id):
        # These should be in every item, and we don't want to keep them around
        if item_type in _unsupported_types:
            log.info("Dropping old-style tool type:%s, name:%s", item_type, fname)
            return # Goodbye
        pretty_name = data.get('name', fname)
        common_names = ['name', 'type', 'id', 'version']
        #log.debug("About to add tool %s in %s", fname, path)
        for name in common_names:
            try:
                del data[name]
            except KeyError:
                #log.debug("key %s not in tool %s(type %s)", name, fname, item_type)
                pass
        with self.connect(commit=True) as cu:
            new_id = self._addCommonDetails(path, pretty_name, item_type, data.get("is_clean", False), parent_path_id, cu)
            prefix = '_add_'
            toolMethod = getattr(self, prefix + item_type, None)
            if not toolMethod:
                toolMethod = getattr(self, prefix + 'genericTool')
            notifications = toolMethod(new_id, data, item_type, cu)
        if notifications is not None:
            for path_id, details in notifications:
                self.notifyPossibleAppearanceChange(path_id, details)
        self._resetInfoFromIdMap()
        return new_id
            
    def _getValuesFromDataAndDelete(self, id, data, names_and_defaults):
        valueList = [id]
        for key, default_value in names_and_defaults:
            try:
                valueList.append(data[key])
                del data[key]
            except KeyError:
                valueList.append(default_value)
        return valueList
            
    def _add_command(self, id, data, item_type, cu):
        self.addCommonToolDetails(id, data, cu)
        names_and_defaults = [
            ('insertOutput', '0'),
            ('parseRegex', False),
            ('operateOnSelection', False),
            ('doNotOpenOutputWindow', False),
            ('showParsedOutputList', False),
            ('parseOutput', False),
            ("runIn", "command-output-window"),
            ('cwd', ''),
            ('env', ''),
            ]
        valueList = self._getValuesFromDataAndDelete(id, data, names_and_defaults)
        nameList = ", ".join(['path_id'] + [x[0] for x in names_and_defaults])
        stmt = '''insert into command(%s)
                  values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % (nameList,)
        cu.execute(stmt, valueList)
        if data:
            return self.addMiscProperties(id, data, cu)
    
    def _add_genericTool(self, id, data, item_type, cu):
        log.debug("Handling generic tool for type %s", item_type)
        self.addCommonToolDetails(id, data, cu)
        if data:
            return self.addMiscProperties(id, data, cu)
            
    def _add_macro(self, id, data, item_type, cu):
        self.addCommonToolDetails(id, data, cu)
        names_and_defaults = [
            ('async', ''),
            ('trigger_enabled', False),
            ('trigger', ''),
            ('language', 'JavaScript'),
            ('rank', 100)
            ]
        valueList = self._getValuesFromDataAndDelete(id, data, names_and_defaults)
        stmt = '''insert into macro(
                  path_id, async, trigger_enabled, trigger, language, rank)
                  values(?, ?, ?, ?, ?, ?)'''
        cu.execute(stmt, valueList)
        if data:
            return self.addMiscProperties(id, data, cu)
            
    def _add_snippet(self, id, data, item_type, cu):
        self.addCommonToolDetails(id, data, cu)
        names_and_defaults = [
            ('set_selection', False),
            ('indent_relative', False),
            ('auto_abbreviation', False),
            ('treat_as_ejs', False),
            ('language', ''),
            ]
        valueList = self._getValuesFromDataAndDelete(id, data, names_and_defaults)
        stmt = '''insert into snippet(
                  path_id, set_selection, indent_relative, auto_abbreviation,
                  treat_as_ejs, language)
                  values(?, ?, ?, ?, ?, ?)'''
        cu.execute(stmt, valueList)
        if data:
            return self.addMiscProperties(id, data, cu)

    def _unsetTemplateDefault(self, language):
        stmt = '''UPDATE template SET lang_default='false' WHERE language=?'''
        cu.execute(stmt, [language])

    def _add_template(self, id, data, item_type, cu):
        if (data.get("lang_default", "false") is "true" or data.get("lang_default", "false") is True):
            self._unsetTemplateDefault(self, data["language"])

        self.addCommonToolDetails(id, data, cu)
        names_and_defaults = [
            ('treat_as_ejs', False),
            ('lang_default', False),
            ('language', ''),
            ]
        valueList = self._getValuesFromDataAndDelete(id, data, names_and_defaults)
        stmt = '''insert into template(
                  path_id, treat_as_ejs, lang_default, language)
                  values(?, ?, ?, ?)'''
        cu.execute(stmt, valueList)
        if data:
            return self.addMiscProperties(id, data, cu)

    def _addSimpleItem(self, id, data, item_type, cu):
        self.addCommonToolDetails(id, data, cu)
        if data:
            return self.addMiscProperties(id, data, cu)

    _add_URL = _addSimpleItem
    _add_folder_template = _addSimpleItem
            
    def addMiscProperties(self, id, data, cu):
        notifications = []
        for key, value in data.items():
            log.debug("Adding misc. property %s:%s on id:%d", key, value, id)
            stmt = '''insert into misc_properties values(?, ?, ?)'''
            cu.execute(stmt, (id, key, value))
            if key == 'icon':
                notifications.append((id, "icon addition"))
        return notifications

    def addCommonToolDetails(self, id, data, cu):
        names_and_defaults = [
            ('value', []),
            ('keyboard_shortcut', ''),
            ]
        values = self._getValuesFromDataAndDelete(id, data, names_and_defaults)
        _, content, keyboard_shortcut = values
        if not content:
            content = ""
        elif not isinstance(content, basestring):
            if not content[-1]:
                del content[-1]
            if content and not content[0]:
                del content[0]
            content = eol.join(content)
        stmt = '''insert into common_tool_details(path_id, value, keyboard_shortcut)
                  values(?, ?, ?)'''
        cu.execute(stmt, (id, content, keyboard_shortcut))
        
                
    def insertMenuItem(self, child_id, position):
        with self.connect(commit=True) as cu:
            stmt = 'insert into menuItem(path_id, position) values(?, ?)'
            #log.debug("About to insert id:%r", child_id)
            cu.execute(stmt, (child_id, position))
            
    def insertMetadataTimestamp(self, parent_id, metadataPath):
        with self.connect(commit=True) as cu:
            stmt = 'insert into metadata_timestamps(path_id, mtime) values(?, ?)'
            cu.execute(stmt, (parent_id, os.stat(metadataPath).st_mtime))

    def renameTool(self, id, newName, newPath=None):
        self.updateValuesInTableByKey('common_details',
                                      ['name'], [newName],
                                      ['path_id'], [id])
        if newPath is not None:
            self.updateValuesInTableByKey('paths',
                                          ['path'], [newPath],
                                          ['id'], [id])
        self._resetInfoFromIdMap()

    def updateChildPaths(self, root_id, old_path, new_path):
        stmt = '''select h.path_id, p.path, cd.type
                  from hierarchy as h, paths as p, common_details as cd
                  where h.parent_path_id = ? and p.id = h.path_id and cd.path_id = p.id'''
        with self.connect(commit=True) as cu:
            pending_ids = [root_id]
            changed_ids = []
            while pending_ids:
                parent_id = pending_ids.pop()
                cu.execute(stmt, (parent_id,))
                rows = cu.fetchall()
                for child_id, child_path, child_type in rows:
                    if not child_path.startswith(old_path):
                        raise Exception("child id %d, path %s doesn't start with oldPath %s" %  (child_id, child_path, old_path))
                    new_child_path = new_path + child_path[len(old_path):]
                    self.updateValuesInTableByKey('paths',
                                                  ['path'], [new_child_path],
                                                  ['id'], [child_id])
                    changed_ids.append(child_id)
                    if child_type == 'folder':
                        pending_ids.append(child_id)
        return changed_ids
            
    _tableNameFromType = {
        # Put anomalies here.
    }
    def tableNameFromType(self, itemType):
        return self._tableNameFromType.get(itemType, itemType)
                
    def getCommandInfo(self, path_id, cu=None):
        obj = {}
        names = self._specific_names['command']
        with self.connect(cu=cu) as cu:
            self.getCommonToolDetails(path_id, obj, cu)
            cu.execute(("select %s from command where path_id = ?" %
                        ", ".join(names)), (path_id,))
            row = cu.fetchone()
        for i, name in enumerate(names):
            obj[name] = row[i]
        return obj
    
    def getCommonContainerDetails(self, path_id, tableName):
        obj = {}
        names = self._specific_names[tableName]
        with self.connect() as cu:
            cu.execute("""select name from common_details
                          where path_id = ?""", (path_id,))
            row = cu.fetchone()
            if row:
                obj['name'] = row[0]
            cu.execute(("select %s from %s where path_id = ?" %
                        (", ".join(names), tableName)), (path_id,))
            row = cu.fetchone()
        if row:
            for i, name in enumerate(names):
                obj[name] = row[i]
        return obj

    def getCommonToolDetails(self, path_id, obj, cu=None):
        with self.connect(cu=cu) as cu:
            cu.execute("""select name from common_details
                          where path_id = ?""", (path_id,))
            row = cu.fetchone()
            if row is None:
                raise Exception("koToolbox2.py:getCommonToolDetails internal error: path_id:%d, table:common_details => None" % (path_id,))
            obj['name'] = row[0]
            cu.execute("""select value, keyboard_shortcut from common_tool_details
                          where path_id = ?""", (path_id,))
            row = cu.fetchone()
            if row is None:
                # Allow for a corrupt database that has a main entry
                # but no common details.
                obj['value'] = ""
                obj['keyboard_shortcut'] = None
            else:
                obj['value'] = row[0]
                obj['keyboard_shortcut'] = row[1]
            cu.execute("""select prop_name, prop_value from misc_properties
                          where path_id = ?""", (path_id,))
            rows = cu.fetchall()
            for row in rows:
                obj[row[0]] = row[1]

    def getSimpleToolInfo(self, path_id, cu=None):
        obj = {}
        with self.connect(cu=cu) as cu:
            self.getCommonToolDetails(path_id, obj, cu)
        obj['url'] = obj['value']
        # Komodo accesses the value by as a URL so it can
        # get a koFileEx obj
        return obj

    def getToolsByTypeAndName(self, toolType, name):
        stmt = "select path_id from common_details where type = ? and name = ?"
        with self.connect() as cu:
            cu.execute(stmt, (toolType, name))
            return [x[0] for x in cu.fetchall()]

    def getDefaultTemplateForLanguage(self, language):
        stmt = "SELECT path_id FROM template WHERE language=? AND lang_default='true'"
        with self.connect() as cu:
            cu.execute(stmt, [language])
            row = cu.fetchone()

            if row:
                return row[0]
            return None

    def getAbbreviationSnippetId(self, abbrev, subnames, isAutoAbbrev):
        """
        Mimic hierarchy of legacy system for snippet location:
        Project toolbox > Toolbox Root > Abbreviations folder
        
        Account for langs that have version that differ enough to warrant
        their own snippets per version, eg. `print "blah"` and `print("blah")`
        for Python and Python3 respectively.
        """
        query="""
        SELECT snippet.path_id, paths.path
        FROM snippet
        JOIN common_details on snippet.path_id = common_details.path_id
        JOIN paths ON snippet.path_id = paths.id
        WHERE common_details.name=? AND snippet.language=? AND snippet.auto_abbreviation=?""";
        abbrevID = None
        language = subnames[0]
        if isAutoAbbrev:
            isAutoAbbrev = "true"
        else:
            isAutoAbbrev = "false"
        with self.connect() as cu:
            cu.execute(query, (abbrev, language, isAutoAbbrev))
            abbrevID = self._rankSnippetResults(cu.fetchall())
            # Special cases where there is more than one versions of a language
            # in Komodo and they are different enough to warrant potentially
            # different snippets
            if abbrevID is None and ("Python" in language or "Python3" in language):
                cu.execute(query,(abbrev, "Python-common", isAutoAbbrev))
                try:
                    abbrevID = self._rankSnippetResults(cu.fetchall())
                except:
                    pass
                if abbrevID is not None:
                    return abbrevID
            if abbrevID is None and ("JavaScript" in language or "Node.js" in language):
                cu.execute(query, (abbrev, "JavaScript-common", isAutoAbbrev))
                try:
                    abbrevID = self._rankSnippetResults(cu.fetchall())
                except:
                    pass
                if abbrevID is not None:
                    return abbrevID
            if abbrevID is None and "HTML" in language:
                cu.execute(query,(abbrev, "HTML-common", isAutoAbbrev))
                try:
                    abbrevID = self._rankSnippetResults(cu.fetchall())
                except:
                    pass
                if abbrevID is not None:
                    return abbrevID
        return abbrevID
    
    def _rankSnippetResults(self, results):
        """
        Take an array of results from a snippet query and rank return a winner
        based on the following hierarchy:
        Project Tools > Toolbox Root Dir > "samples" in Abbreviations folder
        """
        projSnip = None
        rootSnip = None
        sampleSnip = None
         # If you get more than one result back prioritize
        for i in results:
            # First take project specific snippets
            if ".komodotools" in i[1]:
                projSnip = i[0]
            # then take root dir snippets
            elif "Abbreviations" not in i[1]:
                rootSnip = i[0]
            else:
                sampleSnip = i[0]
        if projSnip:
            return projSnip
        if rootSnip:
            return rootSnip
        if sampleSnip:
            return sampleSnip
        return None
        

    def getChildByName(self, id, name, recurse, typeName=None):
        """ Return the first tool that's a child of id that has the
            specified name, matching case.
            """
        stmt = """select common_details.path_id
                  from hierarchy, common_details
                  where hierarchy.parent_path_id = ?
                        and hierarchy.path_id = common_details.path_id
                        and common_details.name = ?"""
        test_values = [id, name]
        if typeName:
            stmt += " and common_details.type = ?"
            test_values.append(typeName)
        with self.connect() as cu:
            cu.execute(stmt, test_values)
            row = cu.fetchone()
            if row:
                return row[0]
            if not recurse:
                return None
            # First make sure the item exists somewhere
            stmt = """select count(*) from common_details where name = ?"""
            cu.execute(stmt, (name,))
            if not cu.fetchone()[0]:
                return None
            return self._getChildByNameInTree([[id]], name, cu, typeName)
                
    def _getChildByNameInTree(self, folder_matches, name, cu, typeName=None):
        condition = ' or '.join(['hierarchy.parent_path_id = ?'] * len(folder_matches))
        if typeName:
            qualifer = " and common_details.type = ?"
            test_values = [f[0] for f in folder_matches] + [name, typeName, 'folder']
        else:
            qualifer = ""
            test_values = [f[0] for f in folder_matches] + [name, 'folder']
        stmt = """select common_details.path_id, common_details.name, common_details.type
                from hierarchy, common_details
                where (%s)
                      and common_details.path_id = hierarchy.path_id
                      and ((common_details.name = ? %s)
                           or common_details.type = ?)""" % (condition, qualifer)
        cu.execute(stmt, test_values)
        child_rows = cu.fetchall()
        if not child_rows:
            return
        for child_row in child_rows:
            if child_row[1] == name:
                return child_row[0]
        return self._getChildByNameInTree(child_rows, name, cu, typeName)

    def getChildByTypeAndName(self, id, typeName, itemName, recurse):
        return self.getChildByName(id, itemName, recurse, typeName)

    def getIDsByType(self, nodeType, rootToolboxPath):
        with self.connect() as cu:
            if not rootToolboxPath:
                stmt = 'select path_id from %s' % nodeType
                cu.execute(stmt)
            else:
                stmt = '''select path_id from %s as t, paths as p
                          where p.id = t.path_id
                            and p.path like ?''' % nodeType
                cu.execute(stmt, (rootToolboxPath + "%",))
            res = cu.fetchall()
            if res is None: return []
        return [x[0] for x in res]
        
    def getIDsForToolsWithKeyboardShortcuts(self, rootToolboxPath):
        with self.connect() as cu:
            if not rootToolboxPath:
                stmt = 'select path_id from common_tool_details where keyboard_shortcut != ?'
                cu.execute(stmt, ("",))
            else:
                stmt = '''select path_id from common_tool_details as t, paths as p
                          where keyboard_shortcut != ?
                            and p.id = t.path_id
                            and p.path like ?'''
                cu.execute(stmt, ("", rootToolboxPath + "%"))
            res = cu.fetchall()
            if res is None: return []
        ids = [x[0] for x in res]
        return ids

    def getTriggerMacroIDs(self, dbPath):
        with self.connect() as cu:
            if dbPath:
                stmt = '''select path_id from macro as m, paths as p
                      where trigger_enabled = ?
                            and trigger != ?
                            and p.id = m.path_id
                            and p.path like ?'''
                cu.execute(stmt, (True, "", dbPath + "%"))
            else:
                stmt = '''select path_id from macro
                      where trigger_enabled = ?
                            and trigger != ?'''
                cu.execute(stmt, (True, ""))
            res = cu.fetchall()
            if res is None: return []
        ids = [x[0] for x in res]
        return ids        

    def getMacroInfo(self, path_id, cu=None):
        obj = {}
        names = self._specific_names['macro']
        with self.connect(cu=cu) as cu:
            self.getCommonToolDetails(path_id, obj, cu)
            cu.execute(("select %s from macro where path_id = ?" %
                        ", ".join(names)), (path_id,))
            row = cu.fetchone()
        for i, name in enumerate(names):
            try:
                obj[name] = row[i]
            except TypeError:
                log.error("couldn't get prop %s for macro id %r", name, i)
        return obj

    def deleteItem(self, path_id, cu=None):
        with self.connect(commit=True, cu=cu) as cu:
            stmt = "select path_id from hierarchy where parent_path_id = ?"
            cu.execute(stmt, (path_id,))
            children = cu.fetchall()
            for child_id in children:
                self.deleteItem(child_id[0], cu)
            #TODO: Send the manager a notification that will cause
            # it to remove item id from its tools cache.
            path = self.getPath(path_id, cu)
            tableNames = ['common_details',
                          'common_tool_details',
                          'misc_properties',
                          'hierarchy',
                          'favorites']
            res = self.getValuesFromTableByKey('common_details', ['type'],
                                               'path_id', path_id, cu)
            if res:
                tool_type = res[0]
                if tool_type in ['snippet', 'macro', 'command', 'menu', 'toolbar', 'tutorial']:
                    tableNames.append(tool_type)
            for t in tableNames:
                try:
                    cu.execute("DELETE FROM %s WHERE path_id=?" % t, (path_id,))
                except:
                    log.debug("Can't delete from table %s", t)
            cu.execute("DELETE FROM paths WHERE id=?", (path_id,))
            try:
                self.observerSvc.notifyObservers(None,
                                                 'tool-deleted',
                                                 "%s" % path_id)
            except Exception:
                log.exception("tool-deleted %r notification failed", id)
        self._resetInfoFromIdMap()
        
    def saveToolName(self, path_id, name, old_name=None):
        with self.connect(commit=True) as cu:
            if old_name is None:
                old_name = self.getValuesFromTableByKey('common_details', ['name'],
                                                        'path_id', path_id, cu)[0]
            if name != old_name:
                self.updateValuesInTableByKey('common_details', ['name'], [name],
                                              ['path_id'], [path_id], cu)
                return (path_id, "name: %s => %s" % (old_name, name))

    def notifyPossibleAppearanceChange(self, id, reason):
        try:
            self.observerSvc.notifyObservers(None, 'tool-appearance-changed',
                                        "%s" % id)
        except Exception:
            log.exception("notifyPossibleAppearanceChange %r/%s failed", id, reason)

    def saveContent(self, path_id, value):
        with self.connect(commit=True) as cu:
            # bug 89131: utf-8 encode, work with the unicode text factory
            # Confusing, but this makes sure round-tripping works.
            self.updateValuesInTableByKey('common_tool_details',
                                          ['value'], [value.encode("utf-8")],
                                          ['path_id'], [path_id], cu)
        
    def save_commonToolDetails(self, path_id, oldMacroInfo, attributes, new_value, cu=None):
        # Only update the changed values.
        # Reading from DB is cheaper than writing to it.
        old_value = oldMacroInfo['value']
        old_kbsc = oldMacroInfo['keyboard_shortcut']
        new_kbsc = attributes.get('keyboard_shortcut', "")
        if old_value != new_value or old_kbsc != new_kbsc:
            field_names = []
            field_values = []
            if old_value != new_value:
                field_names.append('value')
                field_values.append(new_value)
            if old_kbsc != new_kbsc:
                field_names.append('keyboard_shortcut')
                field_values.append(new_kbsc)
            with self.connect(commit=True, cu=cu) as cu:
                self.updateValuesInTableByKey('common_tool_details',
                                              field_names, field_values,
                                              ['path_id'], [path_id], cu)
                

    def _removeNonMiscAttributeNames(self, oldMacroInfo, work_attributes):
        for name in ['name', 'path', 'value', 'keyboard_shortcut']:
            try: del work_attributes[name]
            except KeyError:
                pass
            try: del oldMacroInfo[name]
            except KeyError:
                pass
    
    def _saveNamedValuesInTable(self, path_id, table_name, names, old_attributes, new_attributes, cu):
        names_to_update = []
        vals_to_update = []
        for name in names:
            if name in new_attributes:
                if old_attributes[name] != new_attributes[name]:
                    names_to_update.append(name)
                    vals_to_update.append(new_attributes[name])
                del new_attributes[name]
                del old_attributes[name]
        if names_to_update:
            self.updateValuesInTableByKey(table_name,
                                          names_to_update, vals_to_update,
                                          ['path_id'], [path_id], cu)

    def saveToolInfo(self, path_id, table_name, tool_name, value, attributes,
                     info_getter):
        work_attributes = attributes.copy()
        notifications = []
        with self.connect(commit=True) as cu:
            oldInfo = info_getter(path_id, cu)
            change_info = self.saveToolName(path_id, tool_name, oldInfo['name'])
            if change_info is not None:
                notifications.append(change_info)
            self.save_commonToolDetails(path_id, oldInfo, attributes, value, cu)
            if table_name is not None:
                specific_names = self._specific_names.get(table_name)
                if specific_names:
                    self._saveNamedValuesInTable(path_id, table_name, specific_names,
                                                 oldInfo, work_attributes, cu)
            self._removeNonMiscAttributeNames(oldInfo, work_attributes)
            change_info = self.saveMiscInfo(path_id, oldInfo, work_attributes, cu)
            if change_info is not None:
                notifications.append(change_info)
        # Notifications have to be sent after we've released a db connection,
        # since they can use the db as well.
        for path_id, details in notifications:
            self.notifyPossibleAppearanceChange(path_id, details)
        self._resetInfoFromIdMap()

    def saveContainerInfo(self, path_id, table_name, tool_name, attributes,
                          info_getter):
        work_attributes = attributes.copy()
        notifications = []
        with self.connect(commit=True) as cu:
            oldInfo = info_getter(path_id, cu)
            change_info = self.saveToolName(path_id, tool_name, oldInfo['name'])
            if change_info is not None:
                notifications.append(change_info)
            specific_names = self._specific_names.get(table_name, None)
            if specific_names:
                self._saveNamedValuesInTable(path_id, table_name, specific_names,
                                             oldInfo, work_attributes, cu)
        for path_id, details in notifications:
            self.notifyPossibleAppearanceChange(path_id, details)

    def saveCommandInfo(self, path_id, name, value, attributes):
        self.saveToolInfo(path_id, 'command', name, value, attributes,
                          self.getCommandInfo)

    def saveSimpleToolInfo(self, path_id, name, value, attributes):
        self.saveToolInfo(path_id, None, name, value, attributes,
                          self.getSimpleToolInfo)

    def saveMacroInfo(self, path_id, name, value, attributes):
        self.saveToolInfo(path_id, 'macro', name, value, attributes,
                          self.getMacroInfo)
    
    def saveSnippetInfo(self, path_id, name, value, attributes):
        self.saveToolInfo(path_id, 'snippet', name, value, attributes,
                          self.getSnippetInfo)
    
    def saveTemplateInfo(self, path_id, name, value, attributes):
        if (attributes["lang_default"] is "true" or attributes["lang_default"] is True):
            self._unsetTemplateDefault(self, attributes["language"])

        self.saveToolInfo(path_id, 'template', name, value, attributes,
                          self.getTemplateInfo)

    def saveMenuInfo(self, path_id, tool_name, attributes):
        self.saveContainerInfo(path_id, 'menu', tool_name, attributes,
                               self.getMenuInfo)
    
    def saveToolbarInfo(self, path_id, tool_name, attributes):
        self.saveContainerInfo(path_id, 'toolbar', tool_name, attributes,
                               self.getToolbarInfo)

    def saveMiscInfo(self, path_id, oldAttrList, newAttrList, cu=None):
        names_to_update = []
        vals_to_update = []
        names_to_insert = []
        vals_to_insert = []
        names_to_delete = []
        new_names = newAttrList.keys()
        old_names = oldAttrList.keys()
        for name in new_names:
            if name in old_names:
                if newAttrList[name] != oldAttrList[name]:
                    names_to_update.append(name)
                    vals_to_update.append(newAttrList[name])
                del oldAttrList[name]
            else:
                names_to_insert.append(name)
                vals_to_insert.append(newAttrList[name])
            del newAttrList[name]
        names_to_delete += oldAttrList.keys()
            
        log.debug("misc updates: names:%s, values:%s", names_to_update, vals_to_update)
        log.debug("misc inserts: names:%s, values:%s", names_to_insert, vals_to_insert)
        log.debug("misc deletions: names:%s", names_to_delete)
        with self.connect(commit=True, cu=cu) as cu:
            for name, val in zip(names_to_update, vals_to_update):
                self.updateValuesInTableByKey('misc_properties',
                                              ['prop_value'], [val],
                                              ['path_id', 'prop_name'],
                                              [path_id, name], cu)
            for name, val in zip(names_to_insert, vals_to_insert):
                self.insertRowInTable('misc_properties',
                                      ['path_id', 'prop_name', 'prop_value'],
                                      [path_id, name, val],
                                      cu)
            for name in names_to_delete:
                self.deleteRowByKey('misc_properties',
                                    ['path_id', 'prop_name'],
                                    [path_id, name], cu)
        if 'icon' in old_names or 'icon' in new_names:
            return (path_id, "icon change")
                
    def getSnippetInfo(self, path_id, cu=None):
        obj = {}
        names = self._specific_names.get('snippet')
        with self.connect() as cu:
            self.getCommonToolDetails(path_id, obj, cu)
            cu.execute(("select %s from snippet where path_id = ?" %
                        ", ".join(names)), (path_id,))
            row = cu.fetchone()
        for i, name in enumerate(names):
            obj[name] = row[i]
        return obj
    
    def getTemplateInfo(self, path_id, cu=None):
        obj = {}
        names = self._specific_names.get('template')
        with self.connect() as cu:
            self.getCommonToolDetails(path_id, obj, cu)
            cu.execute(("select %s from template where path_id = ?" %
                        ", ".join(names)), (path_id,))
            row = cu.fetchone()
        for i, name in enumerate(names):
            obj[name] = row[i]
        return obj
    
    def getMenuInfo(self, path_id, cu=None):
        return self.getCommonContainerDetails(path_id, 'menu')
    
    def getToolbarInfo(self, path_id, cu=None):
        return self.getCommonContainerDetails(path_id, 'toolbar')

    def getHierarchyMatch(self, filterPattern):
        """
        This returns a table of [id, name, type, matchesPattern, level].
        It builds a subset of the tree, giving the parent-child
        relationships for all matched items, or nodes that contain
        matches recursively.
        """
        with self.connect() as cu:
            cu.execute("""select path_id from common_details
                          where name like ?""", ("%" + filterPattern + "%", ))
            ids = [x[0] for x in cu.fetchall()]
            if not ids:
                return []
            children_by_id = {}
            processed_ids = dict([(id, True) for id in ids])
            while ids:
                q_list = " or ".join(["path_id = ?"] * len(ids))
                cu.execute("""select path_id, parent_path_id from hierarchy
                          where %s""" % q_list, ids)
                rows = cu.fetchall()
                ids = []
                for path_id, parent_path_id in rows:
                    children_by_id.setdefault(parent_path_id, []).append(path_id)
                    if parent_path_id not in processed_ids:
                        ids.append(parent_path_id)
                        processed_ids[parent_path_id] = False
            
            q_list = " or ".join(["path_id = ?"] * len(processed_ids))
            cu.execute("""select path_id, name, type from common_details
                          where %s""" % q_list, processed_ids.keys())
            rows = cu.fetchall()
            row_info_by_id = dict([(row[0], list(row)) for row in rows])
            ret_table = []
            # The top-level nodes have a parent node of null, so we
            # can start the tree by finding the children of the
            # null entry.
            self._completeTable(None, children_by_id, row_info_by_id,
                                processed_ids, 0, ret_table)
            return ret_table

    folderTypes = ('folder', 'menu', 'toolbar')
    def _compareRowInfo(self, row1, row2):
        id1, name1, type1 = row1
        id2, name2, type2 = row2
        isFolder1 = type1 in self.folderTypes
        isFolder2 = type2 in self.folderTypes
        folderDiff = cmp(not isFolder1, not isFolder2)
        if folderDiff:
            return folderDiff
        return cmp(name1.lower(), name2.lower())        

    def _completeTable(self, parent_id, children_by_id, row_info_by_id,
                       processed_ids, level,
                       ret_table):
        children_ids = children_by_id.get(parent_id, [])
        row_infos_to_sort = [row_info_by_id[x] for x in children_ids]
        sorted_ids = [row[0] for row in sorted(row_infos_to_sort,
                                               cmp=self._compareRowInfo)]
        for id in sorted_ids:
            ret_table.append(row_info_by_id[id] + [processed_ids[id], level])
            self._completeTable(id, children_by_id, row_info_by_id,
                                processed_ids, level + 1,
                                ret_table)

_slugify_re = re.compile(r'[^a-zA-Z0-9\-=\+]+')
def slugify(s):
    return re.sub(_slugify_re, '_', s)

def updateToolName(path, newBaseName):
    try:
        fp = open(path, 'r')
        data = DataParser.readData(fp)
        fp.close()
        if newBaseName.endswith(TOOL_EXTENSION):
            newToolname = newBaseName[:-len(TOOL_EXTENSION)]
        elif newBaseName.endswith(TOOL_EXTENSION_CLEAN):
            newToolname = newBaseName[:-len(TOOL_EXTENSION_CLEAN)]
        else:
            newToolname = newBaseName
        data['name'] = newToolname
        fp = open(path, 'r+')
        DataParser.writeData(fp, data)
        fp.close()
    except:
        try:
            log.exception("Error when trying to assign tool at %s name %s", path, newBaseName)
            os.unlink(path)
        except:
            pass
                
class ToolboxLoader(object):
    # Pure Python class that manages the new Komodo Toolbox back-end

    # When ITEM_VERSION changes update util/upgradeExtensionTools.py
    ITEM_VERSION = "1.1.5"
    FIRST_ITEM_VERSION = "1.0.5"

    def __init__(self, db_path, db):
        # This timestamp is only used while loading the database.
        try:
            self.dbTimestamp = os.stat(db_path).st_mtime
        except:
            self.dbTimestamp = 0
        _tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        self.db = _tbdbSvc.db = db
        self._toolsSvc = UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"].\
                       getService(components.interfaces.koIToolbox2ToolManager))
        self._loadedPaths = {}
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                       .getService(components.interfaces.koIPrefService)
        excludeFiletypesPref = prefSvc.prefs.getPref("find-excludeFiletypes")
        self._excludedFolders = []
        for i in range(excludeFiletypesPref.length):
            s = excludeFiletypesPref.getStringPref(i).strip()
            if s:
                self._excludedFolders.append(s)
        
    def deleteFolderIfMetadataChanged(self, path, fname, path_id):
        # fname is last part of path, but is in for convenience
        # path_id is id(path)
        # returns True if the item should be re-added to the database
        metadataPath = join(path, UI_FOLDER_FILENAME)
        try:
            st_res = os.stat(metadataPath)
            mtime_now = st_res.st_mtime
            has_metadata_now = True
        except:
            has_metadata_now = False
        result = self.db.getValuesFromTableByKey('metadata_timestamps', ['mtime'], 'path_id', path_id)
        if result:
            has_metadata_then = True
            mtime_then = result[0]
        else:
            has_metadata_then = False
        if has_metadata_then != has_metadata_now:
            update_tree = True
        elif not has_metadata_then:
            update_tree = False
        else:
            update_tree = mtime_now > mtime_then
        if update_tree:
            self.db.deleteItem(path_id)
        return update_tree


    def _update_version(self, curr_ver, result_ver, json_data, path):
        log.debug("Adding version %s to json_data %s",
                    result_ver, json_data['name'])
        json_data['version'] = result_ver
        try:
            fp = open(path, 'r+')
            try:
                DataParser.writeData(fp, json_data)
            except:
                log.exception("Can't write out json_data to %s", path)
            fp.close()
        except IOError:
            log.exception("Can't open path %s for writing", path)

    def _remove_id_field(self, curr_ver, result_ver, json_data, path):
        try:
            del json_data['id']
        except KeyError:
            pass
        self._update_version(curr_ver, result_ver, json_data, path)

    def _add_auto_abbrev_field_to_snippets(self, curr_ver, result_ver, json_data, path):
        try:
            if json_data['type'] == "snippet" and "auto_abbreviation" not in json_data:
                json_data["auto_abbreviation"] = "false"
        except KeyError:
            pass
        self._update_version(curr_ver, result_ver, json_data, path)

    def _add_treat_as_ejs_to_snippets(self, curr_ver, result_ver, json_data, path):
        try:
            if json_data['type'] == "snippet" and "treat_as_ejs" not in json_data:
                json_data["treat_as_ejs"] = "false"
        except KeyError:
            pass
        self._update_version(curr_ver, result_ver, json_data, path)
    
    def _add_lang_field_to_snippets(self, curr_ver, result_ver, json_data, path):
        try:
            langRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"].getService(components.interfaces.koILanguageRegistryService);
            UnwrapObject(langRegistry)
            langNames = langRegistry.getLanguageNames()
            if json_data['type'] == "snippet" and "language" not in json_data:
                json_data["language"] = ""
                processedPath = path #so I can munge the path up while searching it
                if "Abbreviations" in processedPath:
                    basename = ""
                    while basename != "Abbreviations":
                        basename = os.path.basename(processedPath)
                        processedPath = os.path.dirname(processedPath)
                        if basename in langNames:
                            json_data["language"] = basename
                            break
                        elif "common" in basename:
                            json_data["language"] = basename
                            break
        except KeyError:
            pass
        
        if json_data['version'] != result_ver:
            self._update_version(curr_ver, result_ver, json_data, path)

    _upgrade_item_info_from_curr_ver = {
        # <item's version>: (<resultant version>, <upgrader method>)
        '1.0.5': ('1.0.6', _update_version),
        '1.0.6': ('1.0.7', _remove_id_field),
        # DB changes 1.0.8, 1.0.9, 1.0.10 don't affect snippets.
        '1.0.7': ('1.0.11', _add_auto_abbrev_field_to_snippets),
        '1.0.11': ('1.0.12', _add_treat_as_ejs_to_snippets),
        '1.0.12': ('1.1.5', _add_lang_field_to_snippets)
     }

    def upgradeItem(self, json_data, path):
        if 'version' not in json_data:
            curr_ver = self.FIRST_ITEM_VERSION
        else:
            curr_ver = json_data['version']
        while curr_ver != self.ITEM_VERSION:
            try:
                result_ver, upgrader \
                    = self._upgrade_item_info_from_curr_ver[curr_ver]
            except KeyError:
                log.info("cannot upgrade tool from v%s - no upgrader for this version",
                         curr_ver)
                break
            else:
                log.info("upgrading from tool v%s to tool v%s ...",
                         curr_ver, result_ver)
            upgrader(self, curr_ver, result_ver, json_data, path)
            curr_ver = result_ver
    
    def _testAndAddItem(self, notifyNow, dirname, fname, parent_id,
                        existing_child_paths=None):
        path = join(dirname, fname)
        isDir = os.path.isdir(path)
        isTool = os.path.splitext(fname)[1] == TOOL_EXTENSION or \
                 os.path.splitext(fname)[1] == TOOL_EXTENSION_CLEAN
        isCleanFormat = os.path.splitext(fname)[1] == TOOL_EXTENSION_CLEAN

        if not isDir and not isTool:
            return
        elif not self.dbTimestamp:
            need_update = True
        else:
            need_disk_based_update_only = False
            result_list = self.db.getValuesFromTableByKey('paths',
                                                          ['id'],
                                                          'path', path)
            if result_list:
                id = result_list[0]
                if id and existing_child_paths:
                    try: del existing_child_paths[path]
                    except KeyError: pass
                if id is None:
                    need_update = True
                elif isDir:
                    need_update = self.deleteFolderIfMetadataChanged(path, fname, id)
                else:
                    mtime = os.stat(path).st_mtime
                    need_update = mtime > self.dbTimestamp
                    if need_update:
                        log.debug("db time: %r, stat time: %r", self.dbTimestamp, mtime)
                        log.debug("Rebuilding item %s (%s)", fname, dirname)
                        self.db.deleteItem(id)
                    elif self.db.item_version_changed:
                        #log.debug("self.db.item_version_changed: true. check for individual tool version change")
                        need_update = True
                        need_disk_based_update_only = True
            else:
                log.debug("No entry for path %s in the db", path)
                need_update = True
                
        if need_update:
            if isTool:
                try:
                    fp = open(path, 'r')

                    if isCleanFormat:
                        data = DataParser.readCleanData(fp)

                        if not data:
                            return

                        self.upgradeItem(data, path)
                    else:
                        try:
                            data = DataParser.readJsonData(fp)

                            if data['type'] == "DirectoryShortcut":
                                log.info("Deleting DirectoryShortcut tool %s", path)
                                os.unlink(path)
                                return

                            self.upgradeItem(data, path)
                        except:
                            log.exception("Couldn't load json data for path %s", path)
                            return
                except IOError:
                    log.error("database loader: Couldn't load file %s", path)
                    return
                except:
                    log.exception("Couldn't analyze path: %s", path)
                    return
                finally:
                    fp.close()
                if need_disk_based_update_only:
                    return
                new_id = self.db.addTool(data, data['type'], path, fname, parent_id)
            else:
                new_id = self.db.addFolder(path, fname, parent_id)
            if notifyNow:
                tool = self._toolsSvc.getToolById(new_id)
                tool.added()

            return new_id

    def updateFilePath(self, path):
        if not os.path.exists(path) or not os.path.isfile(path):
            return

        dirname = os.path.dirname(path)
        fname = os.path.basename(path)

        parent_id = self.db.get_id_from_path(dirname)
        existing_child_paths = dict([(x, 1) for x in self.db.getChildPaths(parent_id)])

        return self._testAndAddItem(True, dirname, fname, parent_id, existing_child_paths)

    def walkFunc(self, notifyNow, dirname, fnames):
        if os.path.basename(dirname) in self._excludedFolders:
            # See if we should remove this item, and its children
            # from the database
            result_list = self.db.getValuesFromTableByKey('paths', ['id'], 'path', dirname)
            if result_list is not None:
                id = result_list[0]
                 # Delete it from the db, and don't load its children
                self.db.deleteItem(id)
            # Make sure walkFunc doesn't process any of this dir's children
            del fnames[:]
            return
        parent_id = self.db.get_id_from_path(dirname)
        if self.dbTimestamp:
            existing_child_paths = dict([(x, 1) for x in self.db.getChildPaths(parent_id)])
        for fname in fnames:
            self._testAndAddItem(notifyNow, dirname, fname, parent_id,
                                 existing_child_paths)
        metadataPath = join(dirname, UI_FOLDER_FILENAME)
        if exists(metadataPath):
            result = self.db.getValuesFromTableByKey('metadata_timestamps', ['mtime'], 'path_id', parent_id)
            if result is None:
                # If it isn't None, it means it's up to date, and there's nothing to do.
                # Add the children here
                fp = open(metadataPath, 'r')
                try:
                    data = json.load(fp, encoding="utf-8")
                    self.upgradeItem(data, metadataPath)
                except ValueError:
                    log.error("Couldn't process json file %s", metadataPath)
                    data = {}
                fp.close()
                children = data.get('children', [])
                position = 0
                self.db.insertMetadataTimestamp(parent_id, metadataPath)
                for child_name in children:
                    child_path = join(dirname, slugify(child_name) + TOOL_EXTENSION)
                    child_id = self.db.get_id_from_path(child_path)
                    if child_id is None:
                        complain = True
                        try:
                            fp = open(child_path, 'r')
                            try: 
                                data2 = json.load(fp, encoding="utf-8")
                            finally:
                                fp.close()
                            complain = data2['type'] != 'file'
                        except:
                            pass
                        if complain:
                            log.error("Didn't find an ID for path %s", child_path)
                    else:
                        self.db.insertMenuItem(child_id, position)
                        position += 1
        for path in existing_child_paths:
            # Getting an id value should never fail here, or the path would
            # have been removed from existing_child_paths in _testAndAddItem
            id = self.db.getValuesFromTableByKey('paths', ['id'], 'path', path)[0]
            if notifyNow:
                tool = self._toolsSvc.getToolById(id)
                tool.removed()
            self.db.deleteItem(id)

    def loadToolboxDirectory(self, toolboxName, toolboxDir, targetDirectory):
        if os.path.basename(toolboxDir) == targetDirectory:
            actualToolboxDir = toolboxDir
        else:
            actualToolboxDir = join(toolboxDir, targetDirectory)
        if not exists(actualToolboxDir):
            os.makedirs(actualToolboxDir)
        self._loadedPaths[actualToolboxDir] = True
        log.debug("Reading dir %s", toolboxDir)
        self.db.establishConnection()
        try:
            result_list = self.db.getValuesFromTableByKey('paths',
                                                   ['id'],
                                                   'path', actualToolboxDir)
            if not result_list:
                new_id = self.db.addFolder(actualToolboxDir, toolboxName, None)
                result_list = [new_id]
                    
            os.path.walk(actualToolboxDir, self.walkFunc, False)
            # Check the name of the item
            res = self.db.getValuesFromTableByKey('paths',
                                                   ['id'],
                                                   'path', actualToolboxDir)
            if res is None:
                log.error("After walking the dir, id(%s) is None", actualToolboxDir)
                return
            currentName = self.db.getValuesFromTableByKey('common_details',
                                                          ['name'],
                                                          'path_id', res[0])[0]
            if currentName != toolboxName:
                self.db.renameTool(res[0], toolboxName)
            
        finally:
            self.db.releaseConnection()
        return result_list[0]
        
    def importDirectory(self, parentPath, pathToImport):
        parent_id = self.db.get_id_from_path(parentPath)
        toolboxName = os.path.basename(pathToImport)
        dstPath = join(parentPath, toolboxName)
        if exists(dstPath):
            dstPath = parentPath
        self.db.establishConnection()
        try:
            fileutils.copyLocalFolder(pathToImport, parentPath)
            result_list = self.db.getValuesFromTableByKey('paths',
                                                   ['id'],
                                                   'path', dstPath)
            if not result_list:
                new_id = self.db.addFolder(dstPath, toolboxName, parent_id)
                result_list = [new_id]
            os.path.walk(dstPath, self.walkFunc, True)
        finally:
            self.db.releaseConnection()
        return result_list[0]
        
    def importFiles(self, parentPath, toolPaths):
        parent_id = self.db.get_id_from_path(parentPath)
        for srcPath in toolPaths:
            ext = os.path.splitext(srcPath)[1]
            if ext == TOOL_EXTENSION or ext == TOOL_EXTENSION_CLEAN:
                destPath = join(parentPath, os.path.basename(srcPath))
                shutil.copy(srcPath, destPath)
                self._testAndAddItem(True, parentPath, destPath, parent_id)
            elif ext == ".zip":
                self._importZippedFiles(srcPath, parentPath, parent_id)
            else:
                log.warn("import tool: skipping file %s as it isn't a Komodo tool, has ext %s",
                         srcPath, os.path.splitext(srcPath)[1] )
        
    def importFileWithNewName(self, parentPath, srcPath, destPath):
        parent_id = self.db.get_id_from_path(parentPath)
        ext = os.path.splitext(srcPath)[1]
        if ext == TOOL_EXTENSION or ext == TOOL_EXTENSION_CLEAN:
            shutil.copy(srcPath, destPath)
            updateToolName(destPath, os.path.basename(destPath))
            self._testAndAddItem(True, parentPath, destPath, parent_id)
        else:
            log.warn("import tool: skipping file %s as it isn't a Komodo tool, has ext %s",
                     srcPath, os.path.splitext(srcPath)[1] )

    _up_dir_re = re.compile(r'(?:^|[/\\])\.\.(?:$|[/\\])')
    def _importZippedFiles(self, srcPath, parentPath, parent_id):
        import zipfile, tempfile
        zf = zipfile.ZipFile(srcPath, 'r')
        try:
            zipped_files = zf.namelist()
            for fname in zipped_files:
                if fname.startswith("/"):
                    raise Exception("filename in zip file is an absolute path: %s",
                                    fname)
                elif self._up_dir_re.search(fname):
                    raise Exception("filename in zip file contains a '..': %s",
                                    fname)
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            userDataDir = koDirSvc.userDataDir
            extractDir = join(userDataDir, 'extracted-kpz')
            zipExtractDir = tempfile.mkdtemp(suffix="_zip", prefix="tools_",
                                             dir=extractDir)
            zf.extractall(zipExtractDir)
        finally:
            zf.close()
        try:
            newFiles = []
            for fname in os.listdir(zipExtractDir):
                path = join(zipExtractDir, fname)
                if os.path.isdir(path):
                    self.importDirectory(parentPath, path)
                else:
                    newFiles.append(path)
            if newFiles:
                self.importFiles(parentPath, newFiles)
        finally:
            shutil.rmtree(zipExtractDir)
            
    def reloadToolsDirectory(self, toolDir):
        self.db.establishConnection()
        try:
            os.path.walk(toolDir, self.walkFunc, True) #notifyNow
        finally:
            self.db.releaseConnection()            
        
    def markAllTopLevelItemsUnloaded(self):
        self._loadedPaths = dict([(x, False) for x in self.db.getTopLevelPaths()])
        print "" #debug
        
    def deleteUnloadedTopLevelItems(self):
        for path, isLoaded in self._loadedPaths.items():
            if not isLoaded:
                id = self.db.get_id_from_path(path)
                if id is not None:
                    log.debug("We never loaded path %s (id %d)", path, id)
                    self.db.deleteItem(id)

class DataParser:

    @staticmethod
    def readData(fp):
        if fp.name.endswith(TOOL_EXTENSION_CLEAN):
            return DataParser.readCleanData(fp)
        else:
            return DataParser.readJsonData(fp)

    @staticmethod
    def writeData(fp, data):
        if data.get("is_clean", None) == "true" or data.get("is_clean", None) == True:
            DataParser.writeCleanData(fp, data)
        else:
            DataParser.writeJsonData(fp, data)

    @staticmethod
    def readJsonData(fp):
        try:
            return json.load(fp, encoding="utf-8")
        except ValueError:
            # For some reason some .komodotool files have an extra closing
            # bracket at the end, no idea why, not wasting cycles on finding out
            fp.seek(0)
            return json.loads(fp.read()[0:-1], encoding="utf-8")

    @staticmethod
    def writeJsonData(fp, data):
        json.dump(data, fp, encoding="utf-8", indent=2)

    @staticmethod
    def readCleanData(fp):
        data = { "value": "", "is_clean": "true" }
        metaRx = re.compile(r"(\w+):\s*(.*)\n")
        subMetaRx = re.compile(r"komodo meta:\s*(.*)\n")
        inMeta = True
        pastMetaStartPending = False
        pastMetaStart = False
        inSubMeta = False
        subMetaKey = "value"
        subMetaQueue = ""

        for num, line in enumerate(fp, 1):
            # Check if we are past the meta start info (TOOL_META_START)
            # and before the meta info (pastMetaStartPending)
            # This strips the --- line
            if pastMetaStartPending:
                pastMetaStart = True
                pastMetaStartPending = False
                continue

            # Detect the meta start identifier
            if not pastMetaStart:

                # If after 2 lines we still havent received the meta start info
                # then this file is not formatted as a komodo tool
                if num > 2:
                    fp.close()
                    return False

                # Detect the TOOL_META_START and extract the tool name from it
                if line.lower().find(TOOL_META_START) != -1:
                    data["name"] = line[line.lower().find(TOOL_META_START) + len(TOOL_META_START):]
                    pastMetaStartPending = True

                continue

            # Parse simple key/val meta info
            if inMeta:
                match = metaRx.search(line)

                if match:
                    data[match.group(1)] = match.group(2)

                # Check for the end indicator for meta info
                elif line.find("===") != -1:
                    inMeta = False

            # Submeta is for multi-line values, primarily intended for the
            # tutorial logic portion
            elif inSubMeta:
                match = subMetaRx.search(line)
                
                if match:
                    subMetaKey = match.group(1).strip()
                    data[subMetaKey] = ""
                else:
                    # If we didn't find the key then we werent looking at submeta
                    # after all, and we need to append the previous line to the
                    # previous entry value
                    inSubMeta = False
                    data[subMetaKey] += subMetaQueue

                subMetaQueue = ""

            # Multi-line values
            else:
                # Detect submeta
                if line.find("===") != -1:
                    inSubMeta = True
                    subMetaQueue = line

                # Else this is a regular value
                else:
                    data[subMetaKey] += line

        [name, ext] = os.path.splitext(fp.name)

        if not data.get("name", False):
            data["name"] = name

        data["name"] = data["name"].strip()

        if not data.get("language", False):
            langRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"]\
                            .getService(components.interfaces.koILanguageRegistryService)
            data["language"] = langRegistry.suggestLanguageForFile(fp.name)

        return data
    
    @staticmethod
    def writeCleanData(fp, data):
        metaRx = re.compile(r"(.*?)\w+:.*\n")
        endRx = re.compile(r"===+(.*)\n")

        inMeta = True
        pastMetaStartPending = False
        pastMetaStart = False

        namePrefix = None
        startPrefix = None
        endSuffix = None
        metaPrefix = None

        multiLineCommented = False

        # Detect namePrefix and metaPrefix
        if fp.mode == "r+":
            for num, line in enumerate(fp, 1):

                # Check if we are past the meta start info (TOOL_META_START)
                # and before the meta info (pastMetaStartPending)
                # This strips the === line
                if pastMetaStartPending:
                    pastMetaStart = True
                    pastMetaStartPending = False
                    continue
                
                # Detect the meta start identifier
                if not pastMetaStart:
                    if line.lower().find(TOOL_META_START) != -1:
                        if not namePrefix:
                            namePrefix = ""
                        else:
                            multiLineCommented = True

                        namePrefix += line[0:(line.lower().find(TOOL_META_START) + len(TOOL_META_START))]
                        pastMetaStartPending = True
                    else:
                        # If after 2 lines we still havent received the meta start info
                        # then this file is not formatted as a komodo tool
                        namePrefix = line
                        if num > 2:
                            break
                    continue

                # Detect regular meta info
                else:
                    match = metaRx.search(line)

                    if match:
                        metaPrefix = match.group(1)
                    else:

                        # End loop when we get to the meta end indicator
                        if line.find("===") != -1:
                            match = endRx.search(line)
                            endSuffix = match.group(1)
                            break

        langRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"]\
                        .getService(components.interfaces.koILanguageRegistryService)

        language = data.get("language", None)
        if not language:
            language = langRegistry.suggestLanguageForFile(fp.name)

        if multiLineCommented and not metaPrefix:
            metaPrefix = ""

        langInfo = langRegistry.getLanguage(language)
        lineComment = langInfo.getCommentDelimiter("line", 0)
        blockComment = langInfo.getCommentDelimiter("block", 0)

        if metaPrefix == None:
            if lineComment:
                metaPrefix = json.loads(lineComment).strip() + " "
            elif blockComment:
                metaPrefix = ""
                blockComment = json.loads(blockComment)
                namePrefix = blockComment[0] + "\n" + TOOL_META_START
                startPrefix = blockComment[0]
                endSuffix = blockComment[1]
            else:
                metaPrefix = "// "

        if not endSuffix:
            endSuffix = ""
        if not startPrefix:
            startPrefix = ""

        if not namePrefix:
            namePrefix = "%s%s" % (metaPrefix, TOOL_META_START)

        concatenated = "%s%s" % (TOOL_META_START, data["name"])
        separator = metaPrefix
        separator += "%s" % ("=" * len(concatenated))
        
        startSeparator = startPrefix + separator + "\n"
        endSeparator = separator + endSuffix + "\n"
        separator = separator + "\n"

        # Now lets start writing

        writeData = ""
        writeData += "%s%s\n" % (namePrefix, data["name"])
        writeData += separator

        keys = data.keys()
        keys.sort()

        multiLineKeys = ["value"]

        for key in keys:
            value = data[key]

            if key == "value" or key == "name" or value == "":
                continue

            if isinstance(value, basestring) and "\n" in value:
                multiLineKeys.append(key)
                continue
            
            writeData += "%s%s: %s\n" % (metaPrefix, key, value)

        writeData += endSeparator

        first = True
        for key in multiLineKeys:
            value = data[key]

            if not first:
                writeData += "\n"
                
                writeData += startSeparator
                writeData += "%skomodo meta: %s\n" % (metaPrefix, key)
                writeData += endSeparator

            if isinstance(data["value"], basestring):
                writeData += data["value"]
            else:
                writeData += eol.join(data["value"])
                
            first = False

        fp.seek(0)
        fp.truncate()

        fp.write(writeData)
            
# Use this class for testing only.
class ToolboxAccessor(object):
    def __init__(self, db_path):
        self.db = Database(db_path)

    #def getTopLevelNodes(self):
    #    return self.db.getTopLevelNodes()
        
    def __getattr__(self, name):
        return getattr(self.db, name)

#---- Misc. top-level routines
_MAX_FILENAME_LEN = 32
_re_capture_word_chars = re.compile(r'(\w+)')
def truncateAtWordBreak(name):
    # urllib only handles ascii chars, so we do our own quoting with the
    # other bits
    if len(name) > _MAX_FILENAME_LEN:
        m1 = _re_capture_word_chars.match(name, _MAX_FILENAME_LEN)
        if m1:
            g1 = m1.group(1)
            if len(g1) < 10:
                return name[:_MAX_FILENAME_LEN] + g1
        return name[:_MAX_FILENAME_LEN]
    else:
        return name
        

def main(argv):
    #dbFile = r"c:\Users\ericp\trash\menu-test.sqlite"
    #schemaFile = r"c:\Users\ericp\svn\apps\komodo\src\projects\koToolbox.sql"
    #toolboxLoader = ToolboxLoader(dbFile, schemaFile)
    #toolboxLoader.loadToolboxDirectory(r"c:\Users\ericp\trash\testToolbox")
    #toolboxAccessor = ToolboxAccessor(dbFile)
    #print toolboxAccessor.getTopLevelNodes()
    #return
    #
    dbFile = r"c:\Users\ericp\trash\toolbox-test.sqlite"
    schemaFile = r"c:\Users\ericp\svn\apps\komodo\src\toolbox\koToolbox.sql"
    try:
        toolboxLoader = ToolboxLoader(dbFile, schemaFile)
        toolboxLoader.markAllTopLevelItemsUnloaded()
        t1 = time.time()
        toolboxLoader.loadToolboxDirectory("standard directory",
                                           r"c:\Users\ericp\trash\stdToolbox")
        t2 = time.time()
        log.debug("Time to load std-toolbox: %g msec", (t2 - t1) * 1000.0)
        t1 = time.time()
        toolboxLoader.loadToolboxDirectory("shared directory",
                                           r"c:\Users\ericp\trash\sharedToolbox")
        t2 = time.time()
        log.debug("Time to load shared-toolbox: %g msec", (t2 - t1) * 1000.0)
        toolboxLoader.deleteUnloadedTopLevelItems()
        toolboxAccessor = ToolboxAccessor(dbFile)
        print toolboxAccessor.getTopLevelNodes()
        print "Wahoo!!!"
    except:
        log.exception("Failure")
        os.unlink(dbFile)


"""
Notes on feeding the tree via the db:

class koToolboxNode(object):
  node_id
  node_name
  node_type
  is_open: init False
  level
  child_nodes: init None, set to array of [node_id]
  

nsITreeView is trivial...

rowCount: len(self._rows) // no db
getCellProperties:(row, col, properties):
  get atom for self._rows[row].node_type
isContainer(index):
  return self._isContainerType(self._rows[index].node_type)
isContainerOpen(index):
  return self.isContainerType(self._rows[index].is_open)
isContainerEmpty(index):
  if not self.isContainer(index): return
  if self._rows[index].child_nodes is None:
     self._rows[index].child_nodes = db.getChildNodes(self._rows[index].node_id)
  return not self._rows[index].child_nodes
getParentIndex: std
hasNextSibling: std
getCellText(row, col):
  return self._rows[row].node_name
toggleOpenState(index):
  node = self._rows[index]
  if node.is_open:
    delete self._rows[index + 1: ...], updateRowCount
  else:
    update node.child_nodes
    self._sort(node.child_nodes)
    insert node.child_nodes into self._rows[index], filtering

Modern view:
Uses the following values:
* isFavorite
* # times used
* lastUsed
* context -- fileType, extensions
* tags in filter

"""

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
