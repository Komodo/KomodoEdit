(function()
{

    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const editor    = require("ko/editor");
    const timers    = require("sdk/timers");
    const doT       = require("contrib/dot");
    const prefs     = Cc['@activestate.com/koPrefService;1']
                        .getService(Ci.koIPrefService).prefs;
    const logging   = require("ko/logging");
    const winUtils  = require("sdk/window/utils");
    const log       = logging.getLogger("notify");
    const _window   = require("ko/windows").getMain();
    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    const _document = _window.document;
    const _ko = _window.ko;

    var _window_test_warning_logged = false;

    var notify = this;
    var queue = {};
    var disabledCats = {
        info: prefs.getPref('notify_disabled_categories'),
        warning: prefs.getPref('notify_disabled_categories_warning'),
        error: prefs.getPref('notify_disabled_categories_error')
    };
    var activeNotifs = {};

    this.P_INFO = Ci.koINotification.SEVERITY_INFO;
    this.P_WARNING = Ci.koINotification.SEVERITY_WARNING;
    this.P_ERROR = Ci.koINotification.SEVERITY_ERROR;
    this.P_NOW = 10;

    var defaultOpts = {
        id: false,
        icon: null,
        duration: 4000,
        from: null, // or ob: {x: 0,y: 0, center: false}
        priority: "notification",
        classlist: "",
        panel: true, /* Whether to add this to the notification panel */
        command: false
    }

    this.categories = require("./categories.js");

    var templates = {
        "panel": () => { return $("#tpl-notify-panel"); }
    }

    templates.get = function(name, params)
    {
        if ( ! templates.cache) templates.cache = {};
        if ( ! (name in templates.cache))
            templates.cache[name] = doT.template(templates[name]().html());

        return templates.cache[name](params);
    }
    
    this.init = () =>
    {
        var addScrollListener = function()
        {
            if ( ! ("views" in _ko)) return;
            
            var scimoz = _ko.views.manager.currentView ? _ko.views.manager.currentView.scimoz : false;
            if ( ! scimoz) return;
            
            scimoz.unhookEvents(onMozScroll, Ci.ISciMozEvents.SME_UPDATEUI);
            scimoz.hookEvents(onMozScroll, Ci.ISciMozEvents.SME_UPDATEUI);
        }
        
        _window.addEventListener('current_view_changed', addScrollListener);
        
        addScrollListener();
    }
    
    var delay = 0;
    var delayTimer;
    this.send = (message, category, opts, now = false) =>
    {
        if ( ! now)
        {
            // If called multiple time synchronously then notifications are incapable
            // of replacing one another, this works around that issue and allows us
            // to assume that two notifications are never called on the same pulse
            delay = delay + 10;
            timers.setTimeout(this.send.bind(this, message, category, opts, true), delay);
            
            timers.clearTimeout(delayTimer);
            delayTimer = timers.setTimeout(function() { delay = 0; }, 50);
        }
        
        if ((typeof category) == "object")
        {
            opts = category;
            category = undefined;
        }
        
        log.debug("Sending: " + message + " ("+category+")");
        log.debug("Source: " + logging.getStack(null, 0, 4));
        
        var _ = require("contrib/underscore");

        var _defaultOpts = _.clone(defaultOpts);
        if (category && this.categories.get(category))
        {
            log.debug("Category exists: " + category);
            _defaultOpts  = _.extend(_defaultOpts , this.categories.get(category).opts);
        }
        else
        {
            log.debug("Category doesnt exist: " + category);
        }

        opts = _.extend(_defaultOpts, opts || {});
        opts.message = message;
        
        opts.id = opts.id || Date.now();

        if (opts.command)
        {
            opts.classlist += " clickable"
        }

        if (isNaN(opts.priority))
        {
            if (("P_" + opts.priority.toUpperCase()) in this)
            {
                opts.classlist += " p-" + opts.priority.toLowerCase();
                opts.priority = this["P_" + opts.priority.toUpperCase()];
            }
            else
            {
                opts.classlist += " p-notification";
                opts.priority = this.P_INFO;
            }
        }
        else
        {
            switch (opts.priority)
            {
                case this.P_ERROR:
                    opts.classlist += " p-error";
                    break;
                case this.P_WARNING:
                    opts.classlist += " p-warning";
                    break;
                default:
                case this.P_INFO:
                    opts.classlist += " p-notification";
                    break;
                case this.P_NOW:
                    opts.classlist += " p-now";
                    break;
            }
        }
        
        if (opts.priority == this.P_NOW)
        {
            opts.noMenu = true;
        }
        
        if (opts.panel)
        {
            // For now we'll use the old notification library, ideally this should
            // be merged into the notify module
            try
            {
                _ko.notifications.add(message, [category], opts.id || Date.now(),
                                     {severity: opts.priority, notify: true});
            }
            catch (e)
            {
                log.exception(e, "Caught exception when trying to use legacy notification library");
            }
        }
        
        if (("panelOnly" in opts) && opts.panelOnly)
        {
            log.debug("Notification has panelOnly set, not showing notification bubble");
            return;
        }

        var cats = disabledCats[priorityName(opts.priority)] || false;
        if (cats && cats.findString(category) != -1)
        {
            log.debug("Notification category is disabled, skipping");
            return;
        }

        var notif = {
            message: message,
            category: category,
            opts: opts
        };

        // Tests do not have a window - don't run this code path in that case.
        if (typeof(window) == "undefined") {
            // Avoid spamming - just write a warning once.
            if (!_window_test_warning_logged) {
                _window_test_warning_logged = true;
                log.warn("no window available for notify.queue");
            }
        } else {
            this.queue(notif);
        }
    }

    this.queue = (notif) =>
    {
        // Create category queue if it doesnt exist
        if ( ! (notif.opts.from in queue))
        {
            queue[notif.opts.from] =
            {
                active: false,
                activeId: null,
                activePanel: null,
                items: []
            };
        }

        log.debug("Adding notification to queue");
        
        var replace = 0;
        var _queue = queue[notif.opts.from].items;
        var append = _queue.length;
        
        var maxLength = prefs.getLong("notify_max_queue_length");
        var length = _queue.length;
        if (queue[notif.opts.from].active) length++;
        if (length >= maxLength && ! notif.opts.force)
        {
            if (length == maxLength)
            {
                this.send("Repeat notifications truncated, please check your Notifications panel",
                          "internal", {force: "true"});
            }
            return;
        }
        
        // determine the notifications place in the queue
        for (let x in _queue)
        {
            if ( ! append && _queue[x].opts.priority < notif.opts.priority)
            {
                append = x;
            }

            if (_queue[x].opts.id && _queue[x].opts.id == notif.opts.id)
            {
                append = x;
                replace = 1;
            }
        }

        queue[notif.opts.from].items.splice(append, replace, notif);
        
        if (notif.opts.priority == this.P_NOW)
        {
            log.debug("Notification type is NOW, hide active Notification and show it right away");
            this.hideNotification();
        }
        
        if ( ! queue[notif.opts.from].active || notif.opts.id == queue[notif.opts.from].activeId)
        {
            log.debug("Showing notification immediately");
            queue[notif.opts.from].active = true;
            this.queue.process(notif.opts.from);
        }
    }

    this.queue.process = (from) =>
    {
        var notif = queue[from].items.shift();
        
        if (notif)
        {
            log.debug("Processing next queued notification");
            
            // Don't show notifications when the main window has no focus, bug #105975
            if ( ! _document.hasFocus())
            {
                if (notif.opts.priority < this.P_WARNING)
                {
                    // if window has no focus and this is not an important notification,
                    // drop it and process the next one
                    this.queue.process(from);
                    log.debug("Notification dropped as window has no focus and priority is low");
                }
                else
                {
                    // Wait until window has focus again
                    queue[from].items.unshift(notif);
                    
                    var onFocus = function()
                    {
                        _window.removeEventListener("focus", onFocus);
                        notify.queue.process(from);
                    }
                    
                    _window.addEventListener("focus", onFocus);
                    
                    log.debug("Notification delayed until window has focus");
                }
                
                return;
            }
            
            timers.setTimeout(this.showNotification.bind(this, notif), 0);
        }
        else
        {
            log.debug("Reached end of queue");
            queue[from].active = false;
        }
    }

    this.showNotification = (notif) =>
    {
        log.debug("Showing notification");
        
        activeNotifs[notif.opts.id] = notif;
        
        var replace = queue[notif.opts.from].activePanel &&
            queue[notif.opts.from].activePanel.exists();
        if (replace)
        {
            log.debug("Forcefully removing active panel");
            queue[notif.opts.from].activePanel.stop().remove();
        }

        this.showNotification._no = this.showNotification._no ? this.showNotification._no++ : 1;

        var panel = $(templates.get("panel", notif.opts));
        this.bindActions(notif, panel);

        queue[notif.opts.from].activeId = notif.opts.id;
        queue[notif.opts.from].activePanel = panel;

        if (notif.opts.command)
        {
            panel.find(".icon, .description").on("click", () => { notif.opts.command(); });
        }

        // Some Linux distro's have problems with setting *any* opacity on a popup -
        // as it can make the popup invisible/disappear.
        if (prefs.getBoolean("notify_use_opacity", true))
        {
            panel.css("opacity", 0);
        }

        panel.element().style.visibility = "hidden";
        $("#komodoMainPopupSet").append(panel);
        
        panel.on("popupshown", function(e)
        {
            if (e.target != panel.element()) return;
            this.doShowNotification(notif, ! replace);
        }.bind(this));
        
        // Calculate initial pos, this will have to be re-calculated
        // once the panel is actually visible as the actual position
        // depends on the size of the panel, but giving it an approximate
        // initial position makes things look less glitchy
        // When opacity works this is a non-issue
        var pos = this._calculatePosition(notif.opts.from || null, panel);
        panel.element().openPopupAtScreen(pos.x, pos.y + 30);
    }

    this.doShowNotification = (notif, animate = true) =>
    {
        log.debug("doShowing: " + notif.message);
        
        var panel = queue[notif.opts.from].activePanel;
        var pos = this._calculatePosition(notif.opts.from || null, panel);
        panel.attr("noautohide", true);
        panel.noautohide = true;
        panel.element().moveTo(pos.x, pos.y + 30);
        panel.element().style.visibility = "";

        panel.animate(
            {
                opacity: 1,
                panelY: pos.y,
                panelX: pos.x
            },
            {
                start: {panelY: pos.y + 30, panelX: pos.x},
                duration: animate ? 200 : 0
            }
        );

        var time = notif.opts.duration || prefs.getLong("notify_duration", 4000);
        panel.timeout = timers.setTimeout(function()
        {
            log.debug("Calling callback from timeout");
            this.hideNotification(notif);
        }.bind(this), time);
        
        panel.find(".close").on("command", this.hideNotification.bind(this, notif));

        log.debug("Showing for " + time + "ms");

        // Handle notification interactions
        var focus = _document.activeElement;
        var interacting = false;
        var interact = () =>
        {
            log.debug("Panel interact");

            timers.clearTimeout(panel.timeout);
            interacting = true;
        };
        var blur = () =>
        {
            log.debug("Panel blur");

            interacting = false;
            panel.timeout = timers.setTimeout(this.hideNotification.bind(this, notif), 1000);

            if ("focus" in focus)
                focus.focus();
        };

        panel.on("mouseover", interact);
        panel.on("focus", interact);

        panel.on("mouseout", blur);
        panel.on("blur", blur);
    }

    this.bindActions = (notif, panel) =>
    {
        if ("undo" in notif.opts)
        {
            panel.find(".undo").on("command", notif.opts.undo);
        }
        
        if ("actions" in notif.opts)
        {
            var popup = panel.find("menupopup");
            popup.prepend("<menuseparator/>");
            var menu = require("ko/menu");
            for (let action in notif.opts.actions)
            {
                action = notif.opts.actions[action];
                action.context = {select: popup, before: "menuseparator"};
                try
                {
                    menu.register(action);
                } catch (e) { log.exception(e); }
            }
        }

        panel.find("menuitem[anonid=disableCategory]").on("command", () =>
        {
            var cats = disabledCats[priorityName(notif.opts.priority)] || false;
            if ( ! cats) return;
            cats.appendString(notif.category);
        });

        panel.find("menuitem[anonid=preferences]").on("command", () =>
        {

        });
    }
    
    this.hideNotificationsByProp = (prop, value) =>
    {
        log.debug("Hide notification by prop " + prop + ": " + value);
        for (let k in activeNotifs)
        {
            let notif = activeNotifs[k];
            if ((prop in notif.opts) && notif.opts[prop] == value)
            {
                this.hideNotification(notif);
            }
        }
    }
    
    this.hideNotification = (notif) =>
    {
        log.debug("Hiding Notification");
        
        if ( ! notif)
        {
            log.debug("Hiding All Notifications");
            
            for (let k in activeNotifs)
            {
                let notif = activeNotifs[k];
                this.hideNotification(notif);
            }
            return;
        }
        
        var panel = queue[notif.opts.from].activePanel;
        if (panel && panel.timeout) timers.clearTimeout(panel.timeout);
        if ( ! panel || ! panel.exists())
        {
            log.warn("Notification panel has already been removed, callback is likely called twice");
            return;
        }
        
        delete activeNotifs[notif.opts.id];
        
        log.debug("Closing panel");
        
        queue[notif.opts.from].activeId = null;
        queue[notif.opts.from].activePanel = null;
        
        //if (panel.element().hasFocus)
        //{
        //    panel.on("blur", this.hideNotification.bind(this, panel, callback));
        //    return;
        //}

        panel.animate(
            {
                opacity: 0,
                panelY: panel.element().boxObject.screenY + 30,
            },
            { duration: 100 },
            function()
            {
                panel.remove();
                this.queue.process(notif.opts.from);
            }.bind(this)
        );
    }

    this._calculatePosition = (from, panel) =>
    {
        var pos,
            scintilla = _ko.views.manager.currentView ? _ko.views.manager.currentView.scintilla : false;

        var normalize = function(pos)
        {
            pos.x = Math.round(pos.x);
            pos.y = Math.round(pos.y);
            return pos;
        }

        // Check if pos is already in the correct format
        if (from && (typeof from) == 'object' && ("x" in from) && ("y" in from))
        {
            pos = from;

            if ( ! pos.center)
            {
                return normalize(pos);
            }
        }

        // Use editor cursor position
        else if (from == "editor" && editor.available())
        {
            pos = editor.getCursorWindowPosition(true);
            pos.y -= editor.defaultTextHeight();

            var computed = _window.getComputedStyle(panel.element());
            pos.y -= parseInt(computed.paddingBottom.replace(/px$/,''));
            pos.y -= parseInt(computed.paddingTop.replace(/px$/,''));

            // Editor preset cant (shouldnt) be centered
            return normalize(pos);
        }
        else
        {
            // Center horizontally on the window
            var bo = document.getElementById('komodo-editor-vbox');
            bo = bo ? bo.boxObject : document.documentElement.boxObject;
            var wx = bo.screenX,
                wy = bo.screenY,
                ww = bo.width,
                wh = bo.height;
            pos = {x: (ww / 2) + wx, y: (wy + wh) - 100};
        }

        // Center the panel
        var box = panel.element().boxObject;
        pos.x = pos.x - ((box.width || 400) / 2); // placeholder width if it is not yet available
        pos.y = pos.y - box.height;

        return normalize(pos);
    }
    
    var onMozScroll = {
        onUpdateUI: function(updated)
        {
            var ISciMoz = Ci.ISciMoz;
            if ((updated & ISciMoz.SC_UPDATE_H_SCROLL) || (updated & ISciMoz.SC_UPDATE_V_SCROLL))
            {
                notify.hideNotificationsByProp("from", "editor");
            }
        }
    }
    
    var priorityName = (priority) =>
    {
        switch (priority)
        {
            case this.P_WARNING:
                return 'warning';
                break;
            case this.P_ERROR:
                return 'error';
                break;
            default:
                return 'info';
                break;
        }
    }
    
    this.init();

}).apply(module.exports);
