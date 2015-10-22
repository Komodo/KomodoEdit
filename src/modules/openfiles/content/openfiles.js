/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
 
/* Open Files
 *
 * Defines the "ko.openfiles" namespace.
 */
if (typeof(ko) == 'undefined')
{
    var ko = {};
}

if (typeof ko.openfiles == 'undefined')
{
    ko.openfiles = function()
    {
        this.init();
    };
}

(function() {
    
    /* Element References */
    var koWindow            = null;
    var listbox             = null;
    
    /* Template storage */
    var template            = {
        fileItem: null,
        groupItem: null
    };
    
    /* Internal Pointers */
    var openViews           = {};
    var timers              = {};
    
    /* Registered options */
    var groupOptions        = {};
    var sortOptions         = {};

    /* Keep track of listeners so we can remove them if needed */
    var listeners            = {};

    /* Pref Constants */
    const
        PREF_GROUPING       = 'openfiles_grouping',
        PREF_GROUPING_TYPE  = 'openfiles_grouping_type',
        PREF_SORTING_TYPE   = 'openfiles_sorting_type',
        PREF_SORTING_DIR    = 'openfiles_sorting_direction',
        PREF_SHOW_TAB_BAR   = 'openfiles_show_tab_bar';

    /* Logging */
    var log = ko.logging.getLogger('koOpenfiles');
    //log.setLevel(ko.logging.LOG_DEBUG);
        
    /* Class Pointer */
    var self;
    
    ko.openfiles.prototype  =
    {
        
        /**
         * "Class" constructor
         *
         * This prepares all the global variables, registers our build in
         * sorting and grouping options and initialized the open files list.
         * 
         * @returns {Void} 
         */
        init: function openfiles_init()
        {
            self = this;
            
            // Create references to frequently used DOM elements 
            koWindow    = window.parent;
            listbox     = document.getElementById('openfilesListbox');
            
            // Prepare item template for file items
            var tpl     = document.getElementById('fileTemplate');
            template.fileItem = tpl.cloneNode(true);
            template.fileItem.removeAttribute('collapsed');
            template.fileItem.removeAttribute('id')
            tpl.parentNode.removeChild(tpl);
            
            // Prepare item template for groups/splits
            var tpl     = document.getElementById('groupTemplate');
            template.groupItem = tpl.cloneNode(true);
            template.groupItem.removeAttribute('collapsed');
            template.groupItem.removeAttribute('id')
            tpl.parentNode.removeChild(tpl);

            // Register built in sorting options
            this.registerSortOption(
                'byName',
                this.sorters.byName
            );
            this.registerSortOption(
                'byIndex',
                this.sorters.byIndex
            );
            this.registerSortOption(
                'byLastOpen',
                this.sorters.byLastOpen
            );
            this.registerSortOption(
                'byAccessNo',
                this.sorters.byAccessNo
            );
            
            // Register built in grouping options 
            this.registerGroupOption(
                'byExt',
                this.groupers.byExt.sort,
                this.groupers.byExt.group,
                'Extension'
            );
            this.registerGroupOption(
                'byLanguage',
                this.groupers.byLanguage.sort,
                this.groupers.byLanguage.group,
                'Language'
            );
            this.registerGroupOption(
                'byFolder',
                this.groupers.byFolder.sort,
                this.groupers.byFolder.group,
                'Folder'
            );
            this.registerGroupOption(
                'byLocation',
                this.groupers.byLocation.sort,
                this.groupers.byLocation.group,
                'Location'
            );
            this.registerGroupOption(
                'byPattern',
                this.groupers.byPattern.sort,
                this.groupers.byPattern.group,
                'Pattern'
            );
            
            // Set the tab bar visibility 
            this.setTabBarVisibility(ko.prefs.getBoolean(PREF_SHOW_TAB_BAR, true));

            if ( ! ko.prefs.getBoolean(PREF_GROUPING, true))
            {
                document.getElementById("openfilesPrefPopup_ToggleGrouping").removeAttribute("checked");
            }
            
            // Bind listeners and reload (initialize) the list of open files 
            this.bindListeners();
            this.reload();
        },

        controller:
        {
            // Grouping Toggle
            do_cmd_openfilesGrouping: function()
            {
                self.toggleGrouping();
                this._updateCommands();
            },

            // Group by Language
            is_cmd_openfilesGroupByLang_enabled: function()
            {
                return !! ko.prefs.getBoolean(PREF_GROUPING, true);
            },

            do_cmd_openfilesGroupByLang: function()
            {
                self.activateGroupOption('byLanguage');
            },

            // Group by Extension
            is_cmd_openfilesGroupByExt_enabled: function()
            {
                return !! ko.prefs.getBoolean(PREF_GROUPING, true);
            },

            do_cmd_openfilesGroupByExt: function()
            {
                self.activateGroupOption('byExt');
            },

            // Group by Folder
            is_cmd_openfilesGroupByFolder_enabled: function()
            {
                return !! ko.prefs.getBoolean(PREF_GROUPING, true);
            },

            do_cmd_openfilesGroupByFolder: function()
            {
                self.activateGroupOption('byFolder');
            },

            // Group by Location
            is_cmd_openfilesGroupByLocation_enabled: function()
            {
                return !! ko.prefs.getBoolean(PREF_GROUPING, true);
            },

            do_cmd_openfilesGroupByLocation: function()
            {
                self.activateGroupOption('byLocation');
            },

            // Group by Pattern
            is_cmd_openfilesGroupByPattern_enabled: function()
            {
                return !! ko.prefs.getBoolean(PREF_GROUPING, true);
            },

            do_cmd_openfilesGroupByPattern: function()
            {
                self.activateGroupOption('byPattern');
            },

            // Sort by Name
            do_cmd_openfilesSortAlpha: function()
            {
                self.activateSortOption('byName');
            },

            // Sort Naturally
            do_cmd_openfilesSortNatural: function()
            {
                self.activateSortOption('byIndex');
            },

            // Sort by Last Opened
            do_cmd_openfilesSortLastOpened: function()
            {
                self.activateSortOption('byLastOpen');
                self.setSortDirection('DESC');
            },

            // Sort by Access No
            do_cmd_openfilesSortAccessNo: function()
            {
                self.activateSortOption('byAccessNo');
                self.setSortDirection('DESC');
            },

            // Sort direction
            do_cmd_openfilesSortAscending: function()
            {
                self.setSortDirection('ASC');
            },
            do_cmd_openfilesSortDescending: function()
            {
                self.setSortDirection('DESC');
            },

            // Re-Sort
            do_cmd_openfilesReSort: function()
            {
                self.sort();
            },
            
            is_cmd_bufferNext_supported: function()
            {
                return ! self.isTabBarVisible();
            },
            
            do_cmd_bufferNext: function()
            {
                var selItem = self.getSelectedItem();
                var next    = self.getNextItem(selItem);
                
                if (next)
                {
                    self.selectItem(next, true);
                }
            },
            
            is_cmd_bufferPrevious_supported: function()
            {
                return ! self.isTabBarVisible();
            },
            
            do_cmd_bufferPrevious: function()
            {
                var selItem = self.getSelectedItem();
                var prev    = self.getPreviousItem(selItem);
                
                if (prev)
                {
                    self.selectItem(prev, true);
                }
            },

            // Update commands helper
            _updateCommands: function()
            {
                var set = document.getElementById('cmdset_openfiles');
                ko.commands.updateCommandset(set);
            },

            // Overloading
            supportsCommand: function(command)
            {
                var method = "is_" + command + "_supported";
                return (method in this) ? this[method]() : (("do_" + command) in this);
            },

            isCommandEnabled: function(command)
            {
                var method = "is_" + command + "_enabled";
                return (method in this) ? this[method]() : true;
            },

            doCommand: function(command)
            {
                log.debug("Executing command: " + command);
                return this["do_" + command]();
            }
        },

        /**
         * Toggle Open Files pane visibility
         *
         * @param {Boolean} collapseIfFocused   If true this will only focus the tab
         *
         * @returns {Boolean}
         */
        togglePane: function openfiles_togglePane(collapseIfFocused = true)
        {
          ko.uilayout.toggleTab('openfilesViewbox', collapseIfFocused);
        },
        
        /**
         * Check if tab bar is visible
         * 
         * @returns {Boolean} 
         */
        isTabBarVisible: function openfiles_isTabBarVisible()
        {
            return koWindow.document.getElementById('topview').classList.contains('showTabs');
        },
        
        /**
         * Toggle tab bar visibility
         * 
         * @returns {Void} 
         */
        toggleTabBar: function openfiles_toggleTabBar()
        {
            this.setTabBarVisibility(
                ! this.isTabBarVisible()
            );
        },
        
        /**
         * Set tab bar visibility
         * 
         * @param   {Boolean} show Whether to show or hide the tabs bar
         * 
         * @returns {Void} 
         */
        setTabBarVisibility: function openfiles_setTabBarVisibility(show /* false */)
        {
            var classList = koWindow.document.getElementById('topview').classList;
            var menuEntry = koWindow.document.getElementById('menu_toggleTabBar');
            
            if (show)
            {
                
                classList.add('showTabs');
                menuEntry.setAttribute('checked', 'true');
                menuEntry.setAttribute('toggled', 'true');
            }
            else
            {
                classList.remove('showTabs');
                menuEntry.removeAttribute('checked');
                menuEntry.removeAttribute('toggled');
            }
            
            ko.prefs.setBooleanPref(PREF_SHOW_TAB_BAR, show);
        },
        
        /**
         * Bind event listeners
         * 
         * @returns {Void} 
         */
        bindListeners: function openfiles_bindListeners()
        {
            /**** Komodo Events ******/
            koWindow.addEventListener('view_closed', function(e)
            {
                log.debug("event: view_closed");
                this.removeItem(e.originalTarget);
            }.bind(this));
            
            koWindow.addEventListener('current_view_changed', function(e)
            {
                log.debug("event: current_view_changed");

                var editorView = e.originalTarget;
                if ( ! (editorView.uid.number in openViews))
                {
                    this.addItem(editorView);
                }

                this.selectItem(editorView);
            }.bind(this));
            
            koWindow.addEventListener('current_view_language_changed', function(e)
            {
                log.debug("event: current_view_language_changed");
                this.removeItem(e.originalTarget);
                this.addItem(e.originalTarget);
            }.bind(this));

            koWindow.addEventListener('workspace_restored', this.reload.bind(this));
            koWindow.addEventListener('project_opened', this.reload.bind(this));
            
            /**** OpenFiles Events ******/
            listbox.addEventListener('select', function(e) {
                if (e.target == listbox && e.target.selectedItem)
                {
                    this.selectItem(e.target.selectedItem, true /*sendEditorTabClick*/ );
                    ko.commands.doCommandAsync('cmd_focusEditor')
                }
            }.bind(this), true);
            
            listbox.addEventListener('contextmenu', this.onContextMenu.bind(this));
            
            // Hack to allow for unselectable richlistitem's
            var selectItem = listbox.selectItem;
            listbox.selectItem = function(item)
            {
                if (item.disabled)
                {
                    return undefined;
                }
                
                return selectItem.call(this, item);
            }

            // Register controller
            window.controllers.insertControllerAt(0, this.controller);
            parent.controllers.insertControllerAt(0, this.controller);
        },
        
        /**
         * Event triggered when a context menu has been triggered on an item
         * 
         * @param   {Object} e  Event Object
         * 
         * @returns {Void}
         */
        onContextMenu: function openfiles_onContextMenu(e)
        {
            var item    = e.currentTarget.selectedItem;
            
            var contextMenu = koWindow.document.getElementById('tabContextMenu');
            
            document.popupNode = contextMenu;
            contextMenu.openPopupAtScreen(e.screenX, e.screenY, true);
        },
        
        /**
         * Event triggered when an item has been closed
         * 
         * @param   {Object} e Event Object
         * 
         * @returns {Void} 
         */
        onClickItemClose: function openfiles_onClickItemClose(editorView)
        {
            editorView.close();
        },
        
        /**
         * Event triggered when file dirty status has been changed
         * 
         * @param   {Object} e Event
         * 
         * @returns {Void} 
         */
        onUpdateDirtyStatus: function openfiles_onUpdateDirtyStatus(e)
        {
            var editorView      = e.originalTarget;
            var dirtyIndicator  = listbox.querySelector(
                'richlistitem[id="'+editorView.uid.number+'"] .file-dirty'
            );
            
            if (editorView.koDoc.isDirty)
            {
                dirtyIndicator.removeAttribute('collapsed');
            }
            else
            {
                dirtyIndicator.setAttribute('collapsed', 'true');
            }
        },
        
        /*
         * Reloads (or initializes) the open files list. This retreives the list 
         * of editor views and calls addItem() for each.
         *
         * This clears out the list of open files and reinitializes it entirely.
         * 
         * @param {Boolean} noDelay     Execute reload immediately
         *
         * @returns {Void}
         */
        reload: function openfiles_reload(noDelay)
        {
            // Prevent multiple calls in a short amount of time (10ms)
            if ( ! noDelay) {
                clearTimeout(timers.reload || {});
                timers.reload = setTimeout(function()
                {
                    this.reload(true);
                }.bind(this),10);
            }
            
            // Remove existing items
            var items = listbox.querySelectorAll('richlistitem') || [];
            for (let item of items)
            {
                item.parentNode.removeChild(item);
            }
            
            // Reset internal pointers/handlers
            openViews = {};
            for (let timer in timers)
            {
                clearTimeout(timer);
            }
            
            // Retrieve list of open views and load them into the richlistbox
            var editorViews = ko.views.manager.getAllViews();
            for (let editorView of editorViews)
            {
                this.addItem(editorView);
            }
        },
        
        /**
         * Render the list of opened items
         *
         * This will only append new items to the list, items that are already
         * in the list will be preserved.
         *
         * This function in turn calls drawGroups.
         * 
         * @param   {Boolean} noDelay   Whether to run immediately or with a 
         *                              small delay, functionally this makes no
         *                              difference, but the delay allows for
         *                              multiple addItem() calls to utilize
         *                              the same thread for rendering.
         * 
         * @returns {Void} 
         */
        drawList: function openfiles_drawList(noDelay = false)
        {
            // Prevent multiple calls in a short amount of time (10ms)
            if ( ! noDelay) {
                clearTimeout(timers.drawList || {});
                timers.drawList = setTimeout(function()
                {
                    this.drawList(true);
                }.bind(this),10);
                return;
            }
            
            // Iterate through open views and append them to the list 
            for (let uid of Object.keys(openViews))
            {
                // Skip items that are already in the list
                if (listbox.querySelector('richlistitem[id="'+uid+'"]'))
                {
                    continue;
                }
                
                // Append the item
                var editorView  = openViews[uid];
                var listItem    = listbox.appendChild(
                                    this.createListItem(editorView));
                
                // Sort the item
                this.sortItem(listItem);
                
                // Select the item if its the current view
                if (editorView == ko.views.manager.currentView)
                {
                    this.selectItem(editorView);
                }
            }
            
            // Render the groups and splits
            this.drawGroups();
            this.updateLabelCounter();
        },
        
        /**
         * Render the item groups and splits
         *
         * This function will preserve the existing groups and only
         * render new groups as necessary.
         * 
         * @returns {Void} 
         */
        drawGroups: function openfiles_drawGroups()
        {
            // Get the preferred grouping type (eg. by language)
            var groupOption = ko.prefs.getString(PREF_GROUPING_TYPE, 'byLanguage');
            groupOption     = groupOptions[groupOption];
            
            // Remove splits, not worth preserving - they will be re-rendered
            var splits = listbox.querySelectorAll(
                'richlistitem.split-item'
            );
            for (let split of splits)
            {
                split.parentNode.removeChild(split);
            }
            
            // Get list of items and convert it into an array
            var listItems   = listbox.querySelectorAll('richlistitem');
            listItems       = Array.slice(listItems); // force array
            
            // Iterate through the items, at its core this will render a group
            // each time it comes across an item which belongs in a different
            // group than the previous one
            var previous = {group: null, split: null};
            for (let x=0;x<listItems.length;x++)
            {
                let fileItem = listItems[x];
                
                // Item is a group, we'll want to preserve it, but the sort does
                // not take groups into account so we'll need to ensure that it
                // doesn't house a sorted item not belonging to this group
                if (fileItem.classList.contains('group-item'))
                {
                    // Get the name of this group
                    let name = fileItem.querySelector('.group-title')
                                        .getAttribute('value');
                    
                    // Retrieve group info of next sibling
                    let uid         = fileItem.nextSibling.getAttribute('id');
                    let editorView  = openViews[uid];
                    let groupInfo   = groupOption.callbackGroup(editorView);
                    
                    // Validate if next sibling belongs to this group
                    if (groupInfo.name != name)
                    {
                        // Does not belong in this group, swap their positions
                        // and repeat this loop
                        fileItem.parentNode.insertBefore(fileItem.nextSibling, fileItem);
                        listItems[x]    = listItems[x+1];
                        listItems[x+1]  = fileItem;
                        x--; // repeat
                    }
                    else
                    {
                        // All good, preserve the group and tell the next
                        // loop what group we were in
                        previous.group = name;
                    }
                }
                // Item is a "file"
                else
                {
                    // Retrieve group info for this item
                    let uid         = fileItem.getAttribute('id');
                    let editorView  = openViews[uid];
                    let groupInfo   = groupOption.callbackGroup(editorView);
                    
                    // Check if we're in a new split and render it
                    if (previous.split != editorView.parentView.getAttribute("id"))
                    {
                        previous.split = editorView.parentView.getAttribute("id");
                        
                        // Check if the previous sibling is a group, in which
                        // case it belongs to this split, if so, we'll want to
                        // insert the split above this group
                        let insertBefore = fileItem;
                        if (fileItem.previousSibling &&
                            fileItem.previousSibling.classList.contains('group-item'))
                        {
                            insertBefore = fileItem.previousSibling;
                        }
                        else
                        {
                            // Previous sibling was not a group, so reset the
                            // previous group and have it render a new one
                            previous.group = null;
                        }
                        
                        // Render split
                        let groupItem = this.createGroupItem({},'split-item');
                        fileItem.parentNode.insertBefore(groupItem, insertBefore);
                    }
                    
                    // Check if we're in a group and render it
                    if (previous.group != groupInfo.name && ko.prefs.getBoolean(PREF_GROUPING, true))
                    {
                        previous.group = groupInfo.name;
                        
                        let groupItem = this.createGroupItem(groupInfo,'group-item');
                        fileItem.parentNode.insertBefore(groupItem, fileItem);
                    }
                }
            }  
        },
        
        /**
         * Create a new list item, this takes the template and injects
         * all the dynamic information
         * 
         * @param   {Object} editorView View object
         * 
         * @returns {Object} Returns element ready for insertion
         */
        createListItem: function openfiles_createListItem(editorView)
        {
            // Clone the template
            var listItem = template.fileItem.cloneNode(true);
            
            var dirName = editorView.koDoc.file ? editorView.koDoc.file.dirName : '';
            var tooltip = dirName == '' ? editorView.title : dirName;
            
            // Set ID, tooltip, title and path
            listItem.setAttribute('id', editorView.uid.number);
            listItem.setAttribute('tooltiptext', tooltip);
            listItem.querySelector('.file-title')
                        .setAttribute('value', editorView.title);
            listItem.querySelector('.file-path')
                        .setAttribute('value', dirName);
            
            // Check for duplicate names, if so we'll mark them all with a css class
            var duplicates = listbox.querySelectorAll(
                                ".file-title[value='"+editorView.title+"']");
            if (duplicates.length > 0)
            {
                listItem.classList.add('duplicate-name');
                for (let dupe of duplicates)
                {
                    dupe.parentNode.classList.add('duplicate-name');
                }
            }
            
            // Override file icon with one that is relevant to the type of file
            if (ko.prefs.getBoolean("native_mozicons_available", false))
            {
                listItem.querySelector('.file-icon').setAttribute(
                    'src',
                    "moz-icon://" + editorView.title + "?size=16"
                );
            }
            
            listItem.querySelector('.file-close-button').addEventListener(
                "mousedown", function(e) {
                    if (e.which != 1) // Only allow left click
                        return;
                    
                    // Don't bubble mousedown events on the close button
                    // We don't want to switch to a file that is being closed
                    e.preventDefault();
                }.bind(this)
            );
            
            // Bind click event on the close button
            listItem.querySelector('.file-close-button').addEventListener(
                "mouseup", function(e) {
                    if (e.which != 1) // Only allow left click
                        return;
                    
                    this.onClickItemClose(editorView);
                }.bind(this)
            );
            
            if (editorView._openfilesListeners == undefined) // prevent duplicate listeners
            {
                editorView._openfilesListeners = true;
                editorView.addEventListener(
                    'view_dirty_status_changed',
                    this.onUpdateDirtyStatus.bind(this)
                );
            }
            
            return listItem;
        },
        
        /**
         * Create a new group item, this takes the template and injects
         * all the dynamic information
         * 
         * @param   {Object} groupInfo  Object containing info about the group,
         *                              Uses keys: name, classlist, attributes
         * @param   {String} className  css class to be appended (eg. split-item)
         * 
         * @returns {Object}  Returns element ready for insertion
         */
        createGroupItem: function openfiles_createGroupItem(groupInfo, className)
        {
            // Clone the template
            var groupItem = template.groupItem.cloneNode(true);
            
            // Set name (if any)
            groupItem.querySelector('.group-title').setAttribute(
                'value', groupInfo.name || ''
            );
            groupItem.classList.add(className); // append class
            
            // Append custom classes as specified by the grouper
            if (groupInfo.classlist !== undefined)
            {
                for (let className of groupInfo.classlist)
                {
                    groupItem.classList.add(className);
                }
            }
            
            // Append custom attributes as specified by the grouper
            if (groupInfo.attributes !== undefined)
            {
                for (let attr in groupInfo.attributes)
                {
                    if ( ! groupInfo.attributes.hasOwnProperty(attr))
                    {
                        continue;
                    }
                    groupItem.setAttribute(attr, groupInfo.attributes[attr]);
                }
            }
            
            return groupItem;
        },
        
        /**
         * Remove all groups from the list
         * 
         * @returns {Void} 
         */
        removeGroups: function openfiles_removeGroups(includeSplits = true)
        {
            var groups = listbox.querySelectorAll(
                'richlistitem.group-item' + (includeSplits ? ',richlistitem.split-item' : '')
            );
            
            for (let group of groups)
            {
                group.parentNode.removeChild(group);
            }
        },
        
        /**
         * Remote empty groups from the list
         * 
         * @returns {Void} 
         */
        removeEmptyGroups: function openfiles_removeEmptyGroups()
        {
            var groups = listbox.querySelectorAll('richlistitem.group-item');
            
            for (let group of groups)
            {
                if ( ! group.nextSibling ||
                    ! group.nextSibling.classList.contains('file-item'))
                {
                    group.parentNode.removeChild(group);
                }
            }
            
            var split = listbox.querySelector('richlistitem.split-item:last-child');
            if (split)
            {
                split.parentNode.removeChild(split);
            }
        },
    
        /*
         * Adds the given file to the Open Files list.
         *
         * @param {Object} editorView    The editor view for the file, as returned by
         *                               ko.views.manager.getAllViews
         * @returns {Void}
         */
        addItem: function openfiles_addItem(editorView)
        {
            openViews[editorView.uid.number] = editorView;
            this.drawList();
        },
    
        /*
         * Removes the given item from the list. 
         *
         * @param {Object} editorView    The editor view for the file, as returned by
         *                               ko.views.manager.getAllViews
         *
         * @returns {Boolean}            whether the file existed in the list
         */
        removeItem: function openfiles_removeItem(editorView)
        {
            // Validate input
            if (typeof editorView != 'object'   ||
                editorView.uid == undefined     ||
                ! (editorView.uid.number in openViews))
            {
                return false;
            }
            
            // Delete entry from internal record
            delete openViews[editorView.uid.number];
            
            // Find item in richlist
            var listItem = listbox.querySelector(
                'richlistitem[id="'+editorView.uid.number+'"]'
            );
            if (listItem)
            {
                var title = listItem.querySelector(".file-title").getAttribute("value");

                // Delete from DOM
                listItem.parentNode.removeChild(listItem);

                // Check for items which have the same name, in case there's only
                // one then we can remove the css class indicating duplicate names
                var duplicates = listbox.querySelectorAll(
                                    '.file-title[value="'+title+'"]');
                if (duplicates.length == 1)
                {
                    duplicates[0].parentNode.classList.remove('duplicate-name');
                }
            }
            
            // Remove empty groups caused by removing this item
            this.removeEmptyGroups();
            this.updateLabelCounter();

            return true;
        },

        /**
         * Update the panel label counter
         *
         * @returns {Void}
         */
        updateLabelCounter: function()
        {
            var label = document.getElementById('openFilesPaneLabel');
            var size = listbox.querySelectorAll('richlistitem.file-item').length;
            label.value = label.value.replace(/^(.*\:\s*)[0-9]+$/,'$1' + size);
        },
    
        /*
         * Retrieve an array of open files, each entry being a EditorView.
         *
         * @returns {Array}
         */
        getItems: function openfiles_getItems()
        {
            return listbox.querySelectorAll('richlistitem.file-item');
        },
        
        /**
         * Select an item in the list using a view object as reference
         * 
         * @param   {Object}   editorView           The relevant view
         * @param   {Boolean}  sendEditorTabClick   (Optional) Fire a tab "click" event to select the editor tab.
         * 
         * @returns {Boolean}   Returns false if the item does not exist
         */
        selectItem: function openfiles_selectItem(editorView, sendEditorTabClick)
        {
            // If a richlistitem is passed, simply forward the call
            // to the relevant tab and let it come back around
            if (editorView.nodeName == 'richlistitem')
            {
                var id = editorView.getAttribute('id');
                
                if (openViews[id] == undefined)
                {
                    return false;
                }
                
                if (this._allowEditorTabClick && sendEditorTabClick) {
                    xtk.domutils.fireEvent(
                        openViews[id].parentNode._tab,
                        'click'
                    );
                }
                return true;
            }
            
            // Validate if the item exists
            var listItem = listbox.querySelector('richlistitem[id="'+editorView.uid.number+'"]');
            if ( ! listItem || listItem == listbox.selectedItem)
            {
                return false;
            }
            
            // Setting the selection here will fire the "select" event, which in
            // turn calls selectItem again - so we need to guard against that,
            // as the only time we want to send tab "click" event is when the
            // user actually selected the open files item.
            this._allowEditorTabClick = false;
            try {
                listbox.clearSelection();
                listbox.addItemToSelection(listItem);
            } finally {
                this._allowEditorTabClick = true;
            }
            
            return true;
        },
    
        /*
         * Retrieve the currently selected item, if any.
         *
         * @returns {Boolean|Object}     Returns false if none is selected, 
         *                               otherwise returns EditorView.
         */
        getSelectedItem: function openfiles_getSelectedItem()
        {
            return listbox.querySelector("richlistitem[selected]");
        },
        
        /**
         * Retrieve the previous file item (skip groups and splits)
         * 
         * @param   {Object} var Item DOM element
         * 
         * @returns {Object|Boolean} Previous Item DOM element
         */
        getPreviousItem: function openfiles_getPreviousItem(item)
        {
            var prev = item.previousSibling;
            
            // If previous sibling doesnt exist or is a file item, return it
            if ( ! prev || prev.classList.contains('file-item'))
            {
                return prev;
            }
            
            return this.getPreviousItem(prev);
        },
        
        /**
         * Retrieve the next file item (skip groups and splits)
         * 
         * @param   {Object} var Item DOM element
         * 
         * @returns {Object|Boolean} Next Item DOM element
         */
        getNextItem: function openfiles_getNextItem(item)
        {
            var next = item.nextSibling;
            
            // If previous sibling doesnt exist or is a file item, return it
            if ( ! next || next.classList.contains('file-item'))
            {
                return next;
            }
            
            return this.getNextItem(next);
        },
        
        /**
         * Sort the list of items, this is only used when switching grouping or
         * sorting preference as it strips aways all groups and resorts every
         * item.
         * 
         * @returns {Void} 
         */
        sort: function openfiles_sort()
        {
            this.removeGroups();
            
            var items = listbox.querySelectorAll('richlistitem.file-item');
            for (let item of items)
            {
                this.sortItem(item);
            }
            
            this.drawGroups();
        },
        
        /**
         * Sort one item
         * 
         * @param   {Object} item Item DOM element
         * @param   {Boolean} resort Whether to resort the item entirely
         * 
         * @returns {Void} 
         */
        sortItem: function openfiles_sortItem(item, resort = false)
        {
            if (resort)
            {
                item.parentNode.appendChild(item);
            }
            // Retrieve relevant view and user preferred grouping option
            var editorView  = openViews[item.getAttribute('id')];
            var sortOption  = this.getActiveSortOption();
            var groupOption = this.getActiveGroupOption();
            var direction   = this.getSortDirection();
            var grouping    = ko.prefs.getBoolean(PREF_GROUPING, true);
            
            log.debug("Sorting: " + editorView.title);

            // Loop until this item is positioned at its highest possible
            // position
            while (true)
            {
                // Retrieve and validate the previous item
                var prevItem = this.getPreviousItem(item);
                if ( ! prevItem ||
                    item.getAttribute('id') == prevItem.getAttribute('id'))
                {
                    break;
                }
                var editorViewPrev = openViews[prevItem.getAttribute('id')];
                
                log.debug("Sorting: Against: " + editorViewPrev.title);

                // Receive positions from sorters
                // >0 - this item goes above the previous
                // <0 - this item goes below the previous
                //  0 - they are essentially the same
                var bySort  = sortOption.callback(editorView,editorViewPrev);
                var byGroup = grouping ? groupOption.callbackSort(editorView,editorViewPrev) : 0;
                var bySplit = this.groupers.bySplit.sort(editorView,editorViewPrev);

                if (direction == 'DESC')
                {
                    bySort *= -1;
                    byGroup *= -1;
                }

                log.debug("Sorting: Sort: " + bySort + ", Group: " + byGroup + ", split: " + bySplit);
                
                // Validate whether this item should be moved above the previous
                if ((
                        // sort by name, provided the sibling has a higher or equivalent ext||split 
                        bySort > 0 && byGroup >=0 && bySplit >= 0
                    ) ||
                    (
                        // sort by ext, provided the sibling has a higher or equivalent split 
                        byGroup > 0 && bySplit >= 0
                    ) ||
                    bySplit > 0 // sort by split
                )
                {
                    log.debug("Sorting: Move Up");
                    item = item.parentNode.insertBefore(item,prevItem);
                }
                else
                {
                    log.debug("Sorting: Done");
                    break;
                }
            }
        },
        
        // Built-in sorters
        sorters:
        {
            /**
             * Sort the item by name
             * 
             * @param   {Object} current  The current view for this item
             * @param   {Object} previous The previous view for this item
             * 
             * @returns {Integer} positive=higher,negative=lower,0=same
             */
            byName: function openfiles_byName(current,previous)
            {
                return previous.title.toLowerCase().localeCompare(
                    current.title.toLowerCase()
                );
            },
            
            /**
             * Sort the item by tab index
             *
             * @param   {Object} current  The current view for this item
             * @param   {Object} previous The previous view for this item
             *
             * @returns {Integer} positive=higher,negative=lower,0=same
             */
            byIndex: function openfiles_byIndex(current,previous)
            {
                var currentTab = current.parentNode._tab;
                current = Array.prototype.indexOf.call(
                            currentTab.parentNode.childNodes,
                            currentTab);

                var previousTab = previous.parentNode._tab;
                previous = Array.prototype.indexOf.call(
                            previousTab.parentNode.childNodes,
                            previousTab);

                return previous - current;
            },

            /**
             * Sort the item by last open time
             *
             * @param   {Object} current  The current view for this item
             * @param   {Object} previous The previous view for this item
             *
             * @returns {Integer} positive=higher,negative=lower,0=same
             */
            byLastOpen: function openfiles_byLastOpen(current,previous)
            {
                current  = current.koDoc ? current.koDoc.fileLastOpened : 0;
                previous  = previous.koDoc ? previous.koDoc.fileLastOpened : 0;

                return current - previous;
            },

            /**
             * Sort the item by how frequently it was accessed
             *
             * @param   {Object} current  The current view for this item
             * @param   {Object} previous The previous view for this item
             *
             * @returns {Integer} positive=higher,negative=lower,0=same
             */
            byAccessNo: function openfiles_byAccessNo(current,previous)
            {
                current  = current.koDoc ? current.koDoc.fileAccessNo : 0;
                previous  = previous.koDoc ? previous.koDoc.fileAccessNo : 0;

                return current - previous;
            }
            
        },
        
        // Built-in groupers
        groupers:
        {
            // Group by Extension
            byExt:
            {
                /**
                 * Sort the item by its extension
                 * 
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 * 
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current  = current.koDoc.file ?
                                current.koDoc.file.ext :
                                current.title.replace(/.*?(?:\.([a-zA-Z0-9]*)|$)/,'$1');
                                
                    previous = previous.koDoc.file ?
                                previous.koDoc.file.ext :
                                previous.title.replace(/.*?(?:\.([a-zA-Z0-9]*)|$)/,'$1');
                    
                    return previous.toLowerCase().localeCompare(
                        current.toLowerCase()
                    );
                },
                
                /**
                 * Retrieve group information
                 * 
                 * @param   {Object} editorView     The current view for this item
                 * 
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    return {
                        name: editorView.koDoc.file && editorView.koDoc.file.ext ?
                                editorView.koDoc.file.ext :
                                editorView.title.replace(/.*(\..*)/,'$1') || 'none'
                    };
                }
            },
            
            // Group by language
            byLanguage:
            {
                /**
                 * Sort the item by its language
                 * 
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 * 
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current = current.koDoc ? current.koDoc.language : -1;
                    previous = previous.koDoc ? previous.koDoc.language : -1;
                    
                    return previous.localeCompare(current);
                },
                
                /**
                 * Retrieve group information
                 * 
                 * @param   {Object} editorView     The current view for this item
                 * 
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    var language = editorView.koDoc ? editorView.koDoc.language : '';
                    return {
                        name: language,
                        classlist: ['languageicon'],
                        attributes: {language: language}
                    };
                }
            },
            
            // Group by Folder
            byFolder:
            {
                /**
                 * Sort the item by its folder name
                 *
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 *
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current = self.groupers.byFolder._getFolderName(current);
                    previous = self.groupers.byFolder._getFolderName(previous)

                    return previous.localeCompare(current);
                },

                /**
                 * Retrieve group information
                 *
                 * @param   {Object} editorView     The current view for this item
                 *
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    return {
                        name: self.groupers.byFolder._getFolderName(editorView)
                    };
                },

                _getFolderName: function(editorView)
                {
                    if ("koDoc" in editorView && "file" in editorView.koDoc)
                    {
                        return editorView.koDoc.file.dirName.replace(/.*\/(.*)/, '$1');
                    }
                    else
                    {
                        return '(root)';
                    }
                }
            },

            // Group by Location
            byLocation:
            {
                /**
                 * Sort the item by its folder name
                 *
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 *
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current = self.groupers.byLocation._getPath(current);
                    previous = self.groupers.byLocation._getPath(previous)

                    return previous.localeCompare(current) || (current == '/' ? 1 : -1);
                },

                /**
                 * Retrieve group information
                 *
                 * @param   {Object} editorView     The current view for this item
                 *
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    return {
                        name: self.groupers.byLocation._getPath(editorView)
                    };
                },

                _getPath: function(editorView)
                {
                    if ("koDoc" in editorView && "file" in editorView.koDoc && editorView.koDoc.file)
                    {
                        var path = editorView.koDoc.file.dirName;

                        if (ko.projects.manager.currentProject)
                        {
                            var projectFolder = ko.projects.manager.currentProject.liveDirectory;
                            if (path.indexOf(projectFolder) === 0)
                            {
                                path = path.substring(projectFolder.length);
                            }
                        }

                        return path || '/';
                    }
                    else
                    {
                        return '/';
                    }
                }
            },

            // Group by Pattern
            byPattern:
            {
                patterns: [
                    {
                        name:       'Model',
                        pattern:    /\/(?:model|models)(?:\/|$)/i,
                        classlist:  ['pattern_model']
                    },
                    {
                        name:       'View',
                        pattern:    /\/(?:view|views)(?:\/|$)/i,
                        classlist:  ['pattern_view']
                    },
                    {
                        name:       'Controller',
                        pattern:    /\/(?:controller|controllers)(?:\/|$)/i,
                        classlist:  ['pattern_controller']
                    },
                    {
                        name:       'Vendor',
                        pattern:    /\/vendor(?:\/|$)/i,
                        classlist:  ['pattern_vendor']
                    },
                    {
                        name:       'Public',
                        pattern:    /\/public(?:\/|$)/i,
                        classlist:  ['pattern_vendor']
                    },
                    {
                        name:       'Config',
                        pattern:    /\/config(?:\/|$)/i,
                        classlist:  ['pattern_config']
                    },
                    {
                        name:       'Locale',
                        pattern:    /\/locale(?:\/|$)/i,
                        classlist:  ['pattern_locale']
                    },
                    {
                        name:       'Lang',
                        pattern:    /\/lang(?:\/|$)/i,
                        classlist:  ['pattern_lang']
                    },
                    {
                        name:       'Skin',
                        pattern:    /\/skin(?:\/|$)/i,
                        classlist:  ['pattern_skin']
                    },
                    {
                        name:       'Module',
                        pattern:    /\/(?:module|modules)(?:\/|$)/i,
                        classlist:  ['pattern_module']
                    },
                    {
                        name:       'Component',
                        pattern:    /\/(?:component|components)(?:\/|$)/i,
                        classlist:  ['pattern_component']
                    },
                ],

                /**
                 * Sort the item by its folder name
                 *
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 *
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current = self.groupers.byPattern._getPattern(current).name;
                    previous = self.groupers.byPattern._getPattern(previous).name;

                    return previous.localeCompare(current);
                },

                /**
                 * Retrieve group information
                 *
                 * @param   {Object} editorView     The current view for this item
                 *
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    return self.groupers.byPattern._getPattern(editorView);
                },

                _getPattern: function(editorView)
                {
                    var path = self.groupers.byPattern._getPath(editorView);
                    if (path != '/')
                    {
                        var patterns = self.groupers.byPattern.patterns;
                        for (let [i,p] in Iterator(patterns))
                        {
                            let matched = path.match(p.pattern);
                            if (matched)
                            {
                                let result = Object.create(p);
                                
                                if (matched.length > 1)
                                {
                                    result.name = result.name.replace('%match%', matched[1]);
                                }

                                return result;
                            }
                        }
                    }
                    
                    return {name: editorView.koDoc ? editorView.koDoc.language : 'None'};
                },

                _getPath: function(editorView)
                {
                    var path = '/';
                    
                    if ("koDoc" in editorView && "file" in editorView.koDoc)
                    {
                        var path = editorView.koDoc.file.path;

                        if (ko.projects.manager.currentProject)
                        {
                            var projectFolder = ko.projects.manager.currentProject.liveDirectory;
                            if (path.indexOf(projectFolder) === 0)
                            {
                                path = path.substring(projectFolder.length);
                            }
                        }
                    }

                    return path || '/';
                }
            },

            // Group by split - this is only used internally
            bySplit:
            {
                /**
                 * Sort the item by its split
                 * 
                 * @param   {Object} current  The current view for this item
                 * @param   {Object} previous The previous view for this item
                 * 
                 * @returns {Integer} positive=higher,negative=lower,0=same
                 */
                sort: function openfiles_sort(current,previous)
                {
                    current = current.parentView.getAttribute("id");
                    previous = previous.parentView.getAttribute("id");
                    
                    return previous.localeCompare(current);
                },
                
                /**
                 * Retrieve group information
                 * 
                 * @param   {Object} editorView     The current view for this item
                 * 
                 * @returns {Object}    Object containing group info
                 *                      keys: name, classlist, attributes
                 */
                group: function openfiles_group(editorView)
                {
                    return {
                        name: editorView.parentView.getAttribute("id")
                    };
                }
            }
        },
    
        /*
         * Get the current sorting direction.
         *
         * @returns string   ASC|DESC
         */
        getSortDirection: function openfiles_getSortDirection()
        {
            return ko.prefs.getString(PREF_SORTING_DIR, 'ASC');
        },
        
        /**
         * Set the sorting direction (ASC|DESC)
         *
         * @param {String} direction   The direction to sort in
         *
         * @returns {Void}
         */
        setSortDirection: function openfiles_setSortDirection(direction)
        {
            ko.prefs.setStringPref(PREF_SORTING_DIR, direction);
            this.sort();
        },
    
        /**
         * Register a new sorting option
         *
         * {String}     id          A unique identifier for this sorting option
         * {Function}   callback    The callback used for sorting
         *
         * @returns {Void}
         */
        registerSortOption: function openfiles_registerSortOption(id, callback)
        {
            sortOptions[id] = {
                id              :   id,
                callback        :   callback
            };
        },
    
        /*
         * Register a new grouping option
         *
         * {String}     id              A unique identifier for this grouping
         *                              option
         * {Function}   callbackSort    The callback used for grouping
         * {Function}   callbackGroup   The callback used to retrieve the
         *                              current group name and icon
         *
         * @returns {Void}
         */
        registerGroupOption: function openfiles_registerGroupOption(id, callbackSort, callbackGroup)
        {
            groupOptions[id] = {
                id              :   id,
                callbackSort    :   callbackSort,
                callbackGroup   :   callbackGroup,
            };
        },

    
        /*
         * Activate the given sorting option
         *
         * @param {String} id   A unique identifier for this sorting option
         *
         * @returns {Void}
         */
        activateSortOption: function openfiles_activateSortOption(id)
        {
            if (sortOptions[id] === undefined)
            {
                return false;
            }
            
            ko.prefs.setStringPref(PREF_SORTING_TYPE, id);
            this.sort();

            return true;
        },
        
        /*
         * Activate the given grouping option
         *
         * @param {String} id   A unique identifier for this grouping option
         *
         * @returns {Boolean}
         */
        activateGroupOption: function openfiles_activateGroupOption(id)
        {
            if (groupOptions[id] === undefined)
            {
                return false;
            }
            
            ko.prefs.setStringPref(PREF_GROUPING_TYPE, id);
            
            this.sort();
            
            return true;
        },
    
        /*
         * Toggle grouping of opened files
         *
         * @returns {Void}
         */
        toggleGrouping: function openfiles_toggleGrouping()
        {
            this.removeGroups();

            var grouping = ! ko.prefs.getBoolean(PREF_GROUPING, true);
            ko.prefs.setBooleanPref(PREF_GROUPING, grouping);

            if (grouping)
            {
                this.drawGroups();
            }

            this.sort();
        },
    
        /*
         * Retrieve array of SortItem objects
         *
         * @returns {Object}
         */
        getSortOptions: function openfiles_getSortOptions()
        {
            return sortOptions;
        },
        
        /*
         * Retrieve array of GroupItem objects
         *
         * @returns {Object}
         */
        getGroupOptions: function openfiles_getGroupOptions()
        {
            return groupOptions;
        },
    
        /*
         * Get the active sorting option
         *
         * @returns {Object} Active SortItem Object
         */
        getActiveSortOption: function openfiles_getActiveSortOption()
        {
            var id = ko.prefs.getString(PREF_SORTING_TYPE, 'byName');
            return sortOptions[id];
        },
    
        /*
         * Get the active grouping option
         *
         * @returns {Object} Active GroupItem Object
         */
        getActiveGroupOption: function openfiles_getActiveGroupOption()
        {
            var groupOption = ko.prefs.getString(PREF_GROUPING_TYPE, 'byLanguage');
            return groupOptions[groupOption];
        }
    
    };
    
    ko.openfiles = new ko.openfiles();
    
}).apply();
