/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
 
/* Breadcrumbs
 *
 * Defines the "ko.breadcrumbs" namespace.
 */
if (typeof(ko) == 'undefined')
{
    var ko = {};
}

if (typeof ko.breadcrumbs == 'undefined')
{
    ko.breadcrumbs = function()
    {
        window.addEventListener("load", this.init.bind(this));
    };
}

(function() {

    /* Dependant interfaces */
    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    const { NetUtil } =   Cu.import("resource://gre/modules/NetUtil.jsm", {});

    var RCService   = Cc["@activestate.com/koRemoteConnectionService;1"]
                        .getService(Ci.koIRemoteConnectionService);
    var os          = Cc["@activestate.com/koOs;1"].getService(Ci.koIOs);
    var osPath      = Cc["@activestate.com/koOsPath;1"]
                        .getService(Components.interfaces.koIOsPath);

    /* Logging */
    var log = ko.logging.getLogger('koBreadcrumbs');
    log.setLevel(ko.logging.LOG_DEBUG);

    /* Element References */
    var breadcrumbBar, overflowBtn;

    /* Templates */
    var template = {
        crumbFile: null,
        crumbFolder: null,
        crumbMenu: null,
        overflowItem: null
    };

    /* Contextual information for events */
    var eventContext = {
        activeCrumb: null,
        menuShowing: false,
        loadInProgress: false
    };

    /* Crumb ache */
    var crumbs = {};

    /* timeout helpers - I know Mook .. */
    var timers = {};

    /* Misc Helpers */
    var pathSeparator = window.navigator.platform.toLowerCase()
                            .indexOf("win32") !== -1 ? '\\' : '/';

    /* Class Pointer */
    var self;
    
    ko.breadcrumbs.prototype  =
    {
        
        /**
         * "Class" constructor
         * 
         * @returns {Void} 
         */
        init: function breadcrumbs_init()
        {
            self = this;

            // Record references
            breadcrumbBar           = document.getElementById('breadcrumbBar');
            template.crumbFile      = document.getElementById('breadcrumbTemplateFile');
            template.crumbFolder    = document.getElementById('breadcrumbTemplateFolder');
            template.crumbMenu      = document.getElementById('breadcrumbMenuTemplate');
            template.overflowItem   = document.getElementById('overflowMenuTemplate');
            overflowBtn             = document.getElementById('breadcrumbOverflowBtn');

            // Bind event listeners
            this.bindListeners();

            // Register Controller 
            window.controllers.appendController(this.controller);
        },

        /**
         * Reload the current breadcrumbs, currently just links to load()
         */
        reload: function breadcrumbs_reload()
        {
            this.load();
        },

        /**
         * Load breadcrumbs for the current view, everything starts here
         *
         * @param   {Boolean} noDelay   
         *
         * @returns {Void}
         */
        load: function breadcrumbs_load(noDelay = false)
        {
            // By default the load is delayed so as not to interfere with the
            // event that triggered it. 
            if ( ! noDelay || eventContext.loadInProgress)
            {
                log.debug('Delaying breadcrumb loading');
                clearTimeout(timers.load || {});
                timers.load = setTimeout(this.load.bind(this, true), 100);
                return;
            }
            
            var view = ko.views.manager.currentView;
            log.debug("Loading crumbs for view ("+view.uid+" : "+view.title+")");

            // Remove old breadcrumbs
            var buttons = breadcrumbBar.querySelectorAll('toolbarbutton') || [];
            for (let button of buttons)
            {
                if (button.hasAttribute('preserve'))
                {
                    continue;
                }
                button.parentNode.removeChild(button);
            }

            // Draw crumbs for current view only if the view has a koDoc
            // and file object
            if ("koDoc" in view && "file" in view.koDoc &&
                (view.koDoc.file.isLocal || view.koDoc.file.isRemoteFile))
            {
                this.drawCrumbs(view);
            }
            else
            {
                this.drawCrumb(view.title, view);
            }

            // Allow css styling to differentiate between local and remote files
            breadcrumbBar.classList.remove('is-remote');
            if (view.koDoc && view.koDoc.file.isRemoteFile)
            {
                breadcrumbBar.classList.add('is-remote');
            }

            // Update overflow whenever breadcrumbs are loaded
            this.checkOverflow();

            // Done loading, allow another queued load in case the user
            // is faster than us (slow filesystem?)
            eventContext.loadInProgress = false;
        },

        /**
         * Bind event listeners
         *
         * @returns {Void}
         */
        bindListeners: function breadcrumbs_bindListeners()
        {
            /**** Komodo Events ******/
            window.addEventListener('current_view_changed',
                                    this.load.bind(this, false));
            window.addEventListener('workspace_restored',
                                    this.load.bind(this, false));
            window.addEventListener('project_opened',
                                    this.load.bind(this, false));

            /* DOM Events */
            window.addEventListener('resize',
                                    this.checkOverflow.bind(this, false));
            window.addEventListener('keydown',
                                    this.onCrumbMenuKeypress.bind(this));
        },

        /**
         * Bind listeners specific to a breadcrumb
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        bindCrumbListeners: function breadcrumbs_bindCrumbListeners(crumb)
        {
            log.debug('Binding crumb listeners for: ' +
                      crumb.node.getAttribute("label"));
            
            // Bind listeners specific to a folder crumb
            if (crumb.node.getAttribute("anonid") == 'breadcrumbFolder')
            {
                // Bind menupopup listeners
                var menupopup = crumb.node.querySelector("menupopup");
                var textbox = menupopup.querySelector("textbox");
                textbox.addEventListener(
                    'keyup', this.onCrumbMenuFilter.bind(this, crumb)
                );

                // We want to load the menupopup contents only when accessed
                menupopup.addEventListener(
                    'popupshowing', this.onCrumbMenuShowing.bind(this,crumb)
                );
                menupopup.addEventListener(
                    'popupshown', this.onCrumbMenuShown.bind(this,crumb)
                );
                menupopup.addEventListener(
                    'popuphidden', this.onCrumbMenuHidden.bind(this,crumb)
                );

                // On mouse move remove menuactive attribute from irrelevant
                // items
                menupopup.addEventListener(
                    'mousemove', function(e)
                {
                    var elems = crumb.node.querySelectorAll(
                        "menuitem[_moz-menuactive]"
                    );
                    for (let [k,elem] in Iterator(elems))
                    {
                        if (elem != e.target)
                        {
                            elem.removeAttribute("_moz-menuactive");
                        }
                    }
                });

                // Track mouse click events for stuff like Shift+LMB
                // to view the file in Places
                crumb.node.addEventListener('mousedown', function(e)
                {
                    if (e.which !== 1) // Only LMB
                    {
                        return;
                    }

                    // Fast Open shortcut
                    if (e.shiftKey && e.ctrlKey)
                    {
                        this.doCommandFastOpen(crumb);
                    }

                    // Show in places shortcut
                    else if (e.shiftKey)
                    {
                        this.doCommandShowPlaces(crumb);
                    }

                    // Find in folder shortcut
                    else if (e.ctrlKey)
                    {
                        this.doCommandFind(crumb);
                    }

                    // Default - open menupopup
                    else
                    {
                        var menupopup = crumb.node.querySelector("menupopup");
                        menupopup.openPopup(crumb.node, 'before_start');
                        return;
                    }

                    e.preventDefault;
                    e.stopPropagation();
                }.bind(this));
            }

            // Crumb for a file (not folder)
            else
            {
                // Show the context menu on any sort of mouse click
                crumb.node.addEventListener('click', function() {
                    var contextMenu = document.getElementById('tabContextMenu');
                    contextMenu.openPopup(crumb.node, 'before_start');
                }.bind(this));
            }
        },

        /*
         * Command controller, for our keybinding based commands
         */
        controller:
        {
            /**
             * Open the crumb menu for the parent folder of the currently opened
             * file, allows for the breadcrumbs to be fully controlled by
             * only the keyboard
             *
             * @returns {Void}
             */
            do_cmd_openCrumbMenu: function()
            {
                var crumb = breadcrumbBar.querySelector(".breadcrumb:last-child")
                                         .previousSibling;
                if ( ! crumb.classList.contains('breadcrumb'))
                {
                    return;
                }

                var menupopup = crumb.querySelector("menupopup");
                menupopup.openPopup(crumb, 'before_start');
            },

            /**
             * Check whether command is supported
             *
             * @param   {String} command
             *
             * @returns {Bool}
             */
            supportsCommand: function(command)
            {
                return ("do_" + command) in this;
            },

            /**
             * Check whether command is enabled
             *
             * @param   {String} command
             *
             * @returns {Bool} 
             */
            isCommandEnabled: function(command)
            {
                var method = "is_" + command + "_enabled";
                return (method in this) ?
                        this["is_" + command + "_enabled"]() : true;
            },

            /**
             * Execute command
             *
             * @param   {String} command
             *
             * @returns {Mixed} 
             */
            doCommand: function(command)
            {
                return this["do_" + command]();
            }
        },

        /**
         * Execute a command on a breadcrumb menu item, this function proxies
         * the command in order to automatically supply relevant breadcrumb info
         *
         * @param   {String} command
         * @param   {Object} menuitem node
         *
         * @returns {Void} 
         */
        onCommandMenuItem: function breadcrumbs_onCommandMenuItem(command,
                                                                  menuitem)
        {
            crumb = crumbs[menuitem.parentNode.parentNode.getAttribute('id')];

            if ( ! ('doCommand' + command in this))
            {
                return log.error(
                    "Attempting to call non-existant command: " + command
                );
            }

            this['doCommand' + command](crumb, menuitem);
        },

        /**
         * Select a crumb, opens its menupopup
         *
         * @param   {Object} crumb
         * @param   {Object} menuitem node
         *
         * @returns {Void} 
         */
        doCommandSelect: function breadcrumbs_onCommandSelect(crumb, menuitem)
        {
            crumb.file.getChild(menuitem.getAttribute("label")).open();
        },

        /**
         * Open the Find in File dialog with the current crumb's folder selected
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        doCommandFind: function breadcrumbs_onCommandFind(crumb)
        {
            if ( ! crumb.file || crumb.file.isRemote()) return;
            
            ko.launch.findInFiles(null, [crumb.file.getPath()]);
        },

        /**
         * Show the current folder in Places
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        doCommandShowPlaces: function breadcrumbs_onCommandShowPlaces(crumb)
        {
            if ( ! crumb.file || crumb.file.isRemote()) return;
            
            var URI = crumb.file.getUri();

            // Strip trailing slash
            if (['/', '\\'].indexOf(URI.substr(-1)) !== -1)
            {
                URI = URI.substr(0, URI.length-1);
            }

            ko.places.manager.showTreeItemByFile(URI);
        },

        /**
         * Filter crumb menu items based on input
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        onCrumbMenuFilter: function breadcrumbs_onCrumbMenuFilter(crumb)
        {
            // Set element references
            var textbox = crumb.node.querySelector("textbox");
            var items = crumb.node.querySelectorAll("menuitem");
            var highlighted = false; // Record whether we have a highlighted item

            // Prepare the filter Regex
            var filter = textbox.value;
            filter = filter.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
            filter = filter.replace(/\s+?/, '.*?');
            filter = new RegExp(filter);

            // Iterate over menu items and apply the filter to them
            for (let [k,item] in Iterator(items))
            {
                if (item.classList.contains('file-item')
                    && textbox.value != ""
                    && ! item.label.match(filter))
                {
                    item.removeAttribute("_moz-menuactive");
                    item.setAttribute("collapsed", true);
                    continue;
                }

                item.removeAttribute("collapsed");

                // Record whether the unfiltered item is highlighted so we
                // don't need to highlight anything ourselves
                if (item.hasAttribute("_moz-menuactive"))
                {
                    highlighted = true;
                }
            }

            // If nothing is highlighted, highlight the first unfiltered item
            // manually
            if ( ! highlighted)
            {
                var item = crumb.node.querySelector(
                    "menuitem.file-item:not([collapsed])"
                );
                if (item)
                {
                    item.setAttribute("_moz-menuactive", "true");
                }
            }
        },

        /**
         * Triggered right before a crumb popupmenu is shown
         *
         * @param   {Object} crumb 
         *
         * @returns {Void} 
         */
        onCrumbMenuShowing: function breadcrumb_onCrumbMenuShowing(crumb)
        {
            log.debug("Showing menu for crumb: " + crumb.view.title);

            // Ensure we aren't showing multiple menu popups
            if (eventContext.activeCrumb && eventContext.menuShowing)
            {
                eventContext.activeCrumb.node.querySelector("menupopup")
                                             .hidePopup();
            }

            // Record the currently active crumb for events
            eventContext.activeCrumb = crumb;

            this.drawCrumbMenuItems(crumb);
        },

        /**
         * Triggered once the crumb popupmenu is shown
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        onCrumbMenuShown: function breadcrumb_onCrumbMenuShown(crumb)
        {
            // Record element references
            var menupopup = crumb.node.querySelector("menupopup");
            var textbox = menupopup.querySelector("textbox");

            // Ensure textbox is selected and ready to be typed in
            textbox.focus();
            textbox.setSelectionRange(0,0);

            // Highlight the first menu item
            menupopup.querySelector("menuitem").setAttribute("_moz-menuactive",
                                                             "true");

            // Set contextual information for events
            eventContext.menuShowing = true;
        },

        /**
         * Triggered once the crumb popupmenu has been hidden
         *
         * @param   {Object} crumb
         *
         * @returns {Void} 
         */
        onCrumbMenuHidden: function breadcrumb_onCrumbMenuHidden(crumb)
        {
            // Set contextual information for events
            eventContext.menuShowing = false;

            // Reset textbox (filter) value
            var textbox = crumb.node.querySelector("textbox");
            if (textbox)
            {
                textbox.value = "";
                xtk.domutils.fireEvent(textbox, "keyup");
            }

            // Ensure editor has focus
            ko.commands.doCommandAsync('cmd_focusEditor');
        },

        /**
         * Triggered on key press in a crumb popupmenu
         *
         * Since we can only capture events inside a popupmenu when we disable
         * the standard keypress events we need to re-implement them
         *
         * @param   {Object} e Event
         *
         * @returns {Void} 
         */
        onCrumbMenuKeypress: function breadcrumb_onCrumbMenuKeypress(e)
        {
            // Ensure we don't process rogue events due to shady focussing
            if ( ! eventContext.menuShowing)
            {
                return;
            }

            switch (e.keyCode)
            {
                /**
                 * ENTER
                 *
                 * Select a menu item
                 */
                case 13:
                    e.preventDefault();
                    e.stopPropagation();

                    var crumb = eventContext.activeCrumb.node;
                    var menuitem = crumb.querySelector(
                        'menuitem[_moz-menuactive="true"]'
                    );

                    xtk.domutils.fireEvent(menuitem, 'command');

                    break;

                /**
                 * ESCAPE
                 *
                 * If the textbox has text in it, reset it to be empty,
                 * otherwise hide the popup
                 */
                case 27:
                    e.preventDefault();
                    e.stopPropagation();

                    var crumb = eventContext.activeCrumb.node;
                    var textbox = crumb.querySelector("textbox");

                    if (textbox && textbox.value != "")
                    {
                        textbox.value = "";
                        xtk.domutils.fireEvent(textbox, "keyup");
                    }
                    else
                    {
                        crumb.querySelector("menupopup").hidePopup();
                    }

                    break;

                /**
                 * LEFT / RIGHT
                 *
                 * Navigate across the different crumbs
                 */
                case 37:
                case 39:
                    // Allow left / right on textbox elem
                    var crumbNode = eventContext.activeCrumb.node;
                    if ((e.target.nodeName == 'textbox' && e.target.value != ''))
                    {
                        return;
                    }

                    e.preventDefault();
                    e.stopPropagation();

                    // Get the next / previous sibling crumb
                    var sibCrumb = e.keyCode == 37 ?
                                        crumbNode.previousSibling :
                                        crumbNode.nextSibling;
                    var sibMenu = sibCrumb.querySelector("menupopup");
                    if ( ! sibMenu)
                    {
                        return;
                    }

                    // Show the sibling crumb's menu
                    sibMenu.openPopup(sibCrumb, 'before_start');

                    break;

                // Up / Down arrow
                case 38:
                case 40:
                    e.preventDefault();
                    e.stopPropagation();

                    // Get the active menu item to start from, if any
                    var crumbNode = eventContext.activeCrumb.node;
                    var menuitem = crumbNode.querySelector(
                        'menuitem[_moz-menuactive="true"]'
                    );
                    if ( ! menuitem)
                    {
                        // No active menu, get the first or last menu item
                        var sibMenu = crumbNode.querySelectorAll('menuitem');
                        sibMenu = sibMenu[(e.keyCode == 38 ?
                                        sibMenu.length -1 : 0)];
                    }
                    else
                    {
                        /* Get the sibling for the given menu */
                        var _sibling = function(menu)
                        {
                            var sibling = e.keyCode == 38 ?
                                            menu.previousSibling :
                                            menu.nextSibling;
                            if ( ! sibling)
                            {
                                // Get first / last menu item, depending on keycode
                                sibling = crumbNode.querySelectorAll('menuitem');
                                return sibling[(e.keyCode == 38 ?
                                                    sibling.length -1 : 0)];
                            }
                            // Skip over irrelevant items
                            if (sibling.nodeName != 'menuitem'
                                || sibling.hasAttribute("collapsed"))
                            {
                                return _sibling(sibling, e.keyCode);
                            }
                            return sibling;
                        }
                        var sibMenu = _sibling(menuitem);
                    }

                    // No sibling menu was found
                    if ( ! sibMenu)
                    {
                        return;
                    }

                    // Remove active indicator from previous menu
                    if (menuitem)
                    {
                        menuitem.removeAttribute("_moz-menuactive");
                        menuitem.blur();
                    }

                    // Select new menu item
                    //sibMenu.scrollIntoView(true); // Todo: implement after moz upgrade
                    sibMenu.setAttribute("_moz-menuactive", "true");
                    sibMenu.focus();

                    break;
            }
        },

        /**
         * Render all the crumbs to the DOM, prepares crumb info then directs
         * it to drawCrumb()
         *
         * @param   {Object} view currentView
         *
         * @returns {Void} 
         */
        drawCrumbs: function breadcrumbs_drawCrumb(view)
        {
            log.debug('Drawing crumbs for view: ' + view.title);

            // Reset the activeCrumb
            eventContext.activeCrumb = null;

            // Init file pointer for currently opened file
            var file = Cc["@mozilla.org/file/local;1"]
                        .createInstance(Ci.nsILocalFile);
            file.initWithPath(view.koDoc.file.path);

            // Get project path so we can exclude it from the crumbs
            var projectPath;
            if (ko.projects.manager.currentProject)
            {
                projectPath = ko.projects.manager.currentProject.liveDirectory;
            }

            // Iterate through files in reverse and queue them to be drawn
            // as breadcrumbs, stop at the project path
            var files = [file];
            while (file = file.parent)
            {
                files.push(file);

                if (file.path == projectPath)
                {
                    break;
                }
            }

            // Direct each file in the path to drawCrumb()
            for (let x=files.length-1;x>=0;x--)
            {
                this.drawCrumb(files[x].leafName, view, files[x]);
            }
        },

        /**
         * Draw a crumb with the given information
         *
         * @param   {String} name
         * @param   {Object} view currentView
         * @param   {Object} file
         *
         * @returns {Void} 
         */
        drawCrumb: function breadcrumbs_drawCrumb(name, view, file = false)
        {
            log.debug('Drawing crumb: ' + name);

            // Generate unique ID for this crumb
            var uuidGenerator = Cc["@mozilla.org/uuid-generator;1"]
                                    .getService(Ci.nsIUUIDGenerator);
            var uid = uuidGenerator.generateUUID();
            
            // Parse our file through our own file "classes" in order to have
            // a uniform interface to access them through
            if (file)
            {
                if (view.koDoc.file.isRemoteFile)
                {
                    file = new fileRemote(file.path,
                                          view.koDoc.file.URI,
                                          view.koDoc.file.path == file.path);
                }
                else
                {
                    file = new fileLocal(file);
                }
            }

            // Get template for file/folder
            if ( ! file || file.isFile())
            {
                var crumb = this._getTemplate('crumbFile');
            }
            else
            {
                var crumb = this._getTemplate('crumbFolder');
            }

            // Set basic crumb attributes
            crumb.setAttribute('id' ,uid);
            crumb.setAttribute('label', name || "(root)");
            crumb.setAttribute(
                'style',
                'z-index: ' +
                    (100 - breadcrumbBar.querySelectorAll(".breadcrumb").length));

            // Load in the native file icon if available
            if (file && file.isFile() &&
                ko.prefs.getBoolean("native_mozicons_available", false))
            {
                crumb.setAttribute(
                    'image', "moz-icon://" + file.getFilename() + "?size=16"
                );
            }

            // Check whether this crumb holds the root project folder and
            // indicate it as such
            if (ko.projects.manager.currentProject && file &&
                ko.projects.manager.currentProject.liveDirectory == file.getPath())
            {
                crumb.classList.add("project-folder");
            }

            // Add the created breadcrumb to the DOM
            breadcrumbBar.appendChild(crumb);

            // Record important breadcrumb information
            crumbs[uid] = {node: crumb, view: view, file: file};

            // Bind listeners
            this.bindCrumbListeners(crumbs[uid]);
        },

        /**
         * Check whether the breadcrumb bar is overflown and if so
         * start collapsing crumbs into a small overflow menu button
         *
         * @returns {Void} 
         */
        checkOverflow: function breadcrumbs_checkOverflow()
        {
            // Start off with resetting everything to normal
            overflowBtn.setAttribute("collapsed", true);
            breadcrumbBar.classList.remove("overflown");
            
            var buttons = breadcrumbBar.querySelectorAll(
                "toolbarbutton.overflown,toolbarbutton.first-child"
            );
            for (let [k,button] in Iterator(buttons))
            {
                button.classList.remove('first-child');
                button.classList.remove('overflown');
            }

            // Now check whether the breadcrumb bar is actually overflown
            if (breadcrumbBar.scrollWidth > breadcrumbBar.boxObject.width)
            {
                overflowBtn.removeAttribute("collapsed");
                breadcrumbBar.classList.add("overflown");
                
                // Iterate through the crumbs, collapsing one at a time until
                // the breadcrumb bar is no longer overflown
                var i = 0;
                buttons = breadcrumbBar.querySelectorAll("toolbarbutton.breadcrumb");
                while (breadcrumbBar.scrollWidth > breadcrumbBar.boxObject.width)
                {
                    if ( ! i in buttons)
                    {
                        break;
                    }

                    let button = buttons[i++];
                    button.classList.add("overflown");
                }

                // If there is still a button visible, mark the first one as the
                // first child
                if (i in buttons)
                {
                    buttons[i].classList.add("first-child");
                }

                // Render menu options for all the collapsed crumbs
                this.drawOverflowMenu();
            }
        },

        /**
         * Create the overflow menu items
         *
         * @returns {Void} 
         */
        drawOverflowMenu: function breadcrumbs_drawOverflowMenu()
        {
            // Start off with removing old items
            var menupopup = overflowBtn.querySelector("menupopup");
            var items = menupopup.querySelectorAll("menu");
            for (let [k,item] in Iterator(items))
            {
                item.parentNode.removeChild(item);
            }

            // Iterate over the collapsed crumbs and add them to the menu
            var buttons = breadcrumbBar.querySelectorAll("toolbarbutton.overflown");
            for (let [k,button] in Iterator(buttons))
            {
                // Create the menu 
                let item = this._getTemplate('overflowItem');
                item.setAttribute("label", button.getAttribute("label"));
                item.breadcrumb = button;

                // Bind event listener to open the menupopup when the menu
                // is hovered, as the menupopup is not a child of the menu
                item.addEventListener("mouseover", function(item,crumb)
                {
                    var menupopup = crumb.querySelector("menupopup");
                    menupopup.openPopup(item, 'end_before');
                }.bind(this, item, button));

                menupopup.appendChild(item);
            }
        },

        /**
         * Draw the menu items for a crumb menu
         *
         * @param   {Object} crumb
         *
         * @returns {Void}
         */
        drawCrumbMenuItems: function breadcrumbs_drawCrumMenuItems(crumb)
        {
            // Skip rendering the menu contents if it was already done
            var menupopup = crumb.node.querySelector("menupopup");
            if (menupopup.hasAttribute('rendered'))
            {
                log.debug("Already rendered - skip populating");
                return;
            }

            log.debug("Populating menu");

            // Get the first menu separator, we'll beed it to inser items before
            var separator = menupopup.querySelector("menuseparator");

            // Iterate through child files of current crumb
            var children = crumb.file.getChildrenSorted();
            for (let [k,child] in Iterator(children))
            {
                // Create menu item
                var elem = this._getTemplate('crumbMenu');
                elem.setAttribute('label', child.getFilename());

                // Set native file icon if available
                if (ko.prefs.getBoolean("native_mozicons_available", false))
                {
                    elem.setAttribute(
                        'image', "moz-icon://" + child.getFilename() + "?size=16"
                    );
                }

                menupopup.insertBefore(elem, separator);
            }

            log.debug("Added " + children.length + " items");

            // If there are no menu items we don't need a separator
            if (children.length==0)
            {
                separator.setAttribute('collapsed', true);
            }

            // Prevent the menu from being rendered again
            menupopup.setAttribute('rendered', true);
        },

        /**
         * Template helper, clones the template node and removes attributes
         * which are not meant to be part of the template
         *
         * @param   {String} name
         *
         * @returns {Object} node
         */
        _getTemplate: function breadcrumbs_getTemplate(name)
        {
            var elem = template[name].cloneNode(true);
            elem.removeAttribute('id');
            elem.removeAttribute('collapsed');
            elem.removeAttribute('preserve');
            return elem;
        },

    };

    var fileLocal = function(path)
    {
        var cache = {};

        if (path instanceof Ci.nsILocalFile)
        {
            cache.file = path;
            path = cache.file.path;
        }

        this._getFile = function()
        {
            if ( ! ("file" in cache))
            {
                log.debug("Initiating local file: " + path);
                
                cache.file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
                cache.file.initWithPath(path);
            }
            return cache.file;
        };

        this.open = function()
        {
            ko.open.URI(path);
        };

        this.getChild = function(name)
        {
            var children = this.getChildren();
            if (name in children)
            {
                return children[name];
            }
            return false;
        };

        this.getChildren = function()
        {
            if ( ! ("children" in cache))
            {
                cache.children = {};
                var children = os.listdir(path, {});
                for (let [k,file] in Iterator(children))
                {
                    if (osPath.isfile(path + pathSeparator + file))
                    {
                        cache.children[file] = new fileLocal(path + pathSeparator + file);
                    }
                }
            }
            return cache.children;
        };

        this.getChildrenSorted = function()
        {
            if ( ! ("childrenSorted" in cache))
            {
                cache.childrenSorted = [];
                var children = this.getChildren();

                for (let [name,child] in children)
                {
                    cache.childrenSorted.push(child);
                }

                cache.childrenSorted.sort(function(a,b) {
                    return a.getFilename().localeCompare(b.getFilename());
                });
            }
            return cache.childrenSorted;
        };

        this.getFilename = function()
        {
            return this._getFile().leafName;
        };
        
        this.getUri = function()
        {
            return NetUtil.newURI(this._getFile()).spec;
        };

        this.getPath = function()
        {
            return path;
        };

        this.isFile = function()
        {
            return this._getFile().isFile();
        };

        this.isDirectory = function()
        {
            return this._getFile().isDirectory();
        };

        this.isRemote = function()
        {
            return false;
        };

        return this;
    };

    var fileRemote = function(path, conn, isFile)
    {
        var cache = {};

        if (typeof conn == "string")
        {
            cache.uri = conn;
            conn = RCService.getConnectionUsingUri(conn);
        }

        this._getFile = function()
        {
            if ( ! ("file" in cache) ||
                (cache.file.isDirectory() && cache.file.needsDirectoryListing) )
            {
                log.debug("Initiating remote file: " + path);
                
                cache.file = conn.list(path, 1);
            }
            return cache.file;
        };

        this.open = function()
        {
            ko.open.URI(this.getUri());
        };

        this.getChild = function(name)
        {
            var children = this.getChildren();
            if (name in children)
            {
                return children[name];
            }
            return false;
        };

        this.getChildren = function()
        {
            if ( ! ("children" in cache))
            {
                cache.children = {};
                var children = this._getFile().getChildren({});
                for (let [k,child] in Iterator(children))
                {
                    if (child.isFile())
                    {
                        cache.children[child.getFilename()] = new fileRemote(path + pathSeparator + child.getFilename(), conn);
                    }
                }
            }
            return cache.children;
        };

        this.getChildrenSorted = function()
        {
            if ( ! ("childrenSorted" in cache))
            {
                cache.childrenSorted = [];
                var children = this.getChildren();

                for (let [name,child] in children)
                {
                    cache.childrenSorted.push(child);
                }

                cache.childrenSorted.sort(function(a,b) {
                    return a.getFilename().localeCompare(b.getFilename());
                });
            }
            return cache.childrenSorted;
        };

        this.getFilename = function()
        {
            // parse filename from path so we don't need to query the server
            return path.replace(/.*(?:\/|\\)/,'');
        };

        this.getUri = function()
        {
            if ( ! ("uri" in cache))
            {
                cache.uri = conn.protocol + "://";
                if (conn.alias)
                {
                    cache.uri += conn.alias;
                }
                else
                {
                    if (conn.username)
                    {
                        cache.uri += conn.username;
                        cache.uri += "@";
                    }
                    cache.uri += conn.server;
                    if (conn.port)
                    {
                        cache.uri += ":"+conn.port;
                    }
                }

                cache.uri += path;

                log.debug('remoteFile getUri: ' + cache.uri);
            }

            return cache.uri;
        };

        this.getPath = function()
        {
            return path;
        };

        this.isFile = function()
        {
            return isFile;
        };

        this.isDirectory = function()
        {
            return ! isFile;
        };

        this.isRemote = function()
        {
            return true;
        };

        return this;
    };

    ko.breadcrumbs = new ko.breadcrumbs();
    
}).apply();
