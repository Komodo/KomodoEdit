/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

CREATE TABLE toolbox2_meta (
   /* For tracking versions, etc. */
   key TEXT UNIQUE ON CONFLICT REPLACE,
   value TEXT
);

create table paths (
    id integer unique primary key autoincrement,
    path text unique not null
);
create index paths_path_index on paths(path);

create table common_details (
    path_id INTEGER PRIMARY KEY NOT NULL ,
    /* uuid CHAR(36) NOT NULL, */
    name text NOT NULL,
    type text NOT NULL
);

create table common_tool_details (
    path_id INTEGER PRIMARY KEY NOT NULL ,
    tags text,
    value TEXT,
    keyboard_shortcut text,
    lastRun DATETIME,
    favoriteRating INTEGER NOT NULL  DEFAULT 0,
    timesRun INTEGER NOT NULL DEFAULT 0
);

create table hierarchy (
    path_id INTEGER PRIMARY KEY NOT NULL,
    parent_path_id INTEGER
);
create index hierarchy_parent_path_id_index on hierarchy(parent_path_id);

create table snippet (
    path_id INTEGER PRIMARY KEY NOT NULL,
    set_selection bool default false,
    indent_relative bool default false,
    auto_abbreviation bool default false,
    treat_as_ejs bool default false
);

create table macro (
    path_id INTEGER PRIMARY KEY NOT NULL,
    async bool default false,
    trigger_enabled bool default false,
    trigger text,
    language text,
    rank INTEGER default 100
);

create table command (
    path_id INTEGER PRIMARY KEY NOT NULL,
    insertOutput bool default false,
    parseRegex bool default false,
    operateOnSelection bool default false,
    doNotOpenOutputWindow bool default false,
    showParsedOutputList bool default false,
    parseOutput bool default false,
    runIn text,
    cwd text,
    env text
);

create table metadata_timestamps (
    path_id INTEGER PRIMARY KEY NOT NULL, /* path id of path containing metadata file */
    mtime REAL
);

create table menu (
    path_id INTEGER PRIMARY KEY NOT NULL,
    priority integer default 100,
    accessKey char(10)
);

create table toolbar (
    path_id INTEGER PRIMARY KEY NOT NULL,
    priority integer default 100,
    metadata_timestamp DATETIME
);

create table menuItem (
    path_id INTEGER PRIMARY KEY NOT NULL,
    position INTEGER
);

create table misc_properties (
    path_id INTEGER NOT NULL,
    prop_name text,
    prop_value text
);
create index misc_properties_id_index on misc_properties(path_id);

create table favorites (
    path_id INTEGER PRIMARY KEY NOT NULL
);
