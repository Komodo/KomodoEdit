(function()
{

    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const editor    = require("ko/editor");
    const doT       = require("contrib/dot");
    const prefs     = Cc['@activestate.com/koPrefService;1']
                        .getService(Ci.koIPrefService).prefs;
    const logging   = require("ko/logging");
    const log       = logging.getLogger("notify");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var notify = this;
    var queue = {};
    var disabledCats = prefs.getPref('notify_disabled_categories');

    this.P_INFO = Ci.koINotification.SEVERITY_INFO;
    this.P_WARNING = Ci.koINotification.SEVERITY_WARNING;
    this.P_ERROR = Ci.koINotification.SEVERITY_ERROR;

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
        "panel": $("#tpl-notify-panel")
    }

    templates.get = function(name, params)
    {
        if ( ! templates.cache) templates.cache = {};
        if ( ! (name in templates.cache))
            templates.cache[name] = doT.template(templates[name].html());

        return templates.cache[name](params);
    }

    this.send = (message, category, opts) =>
    {
        log.debug("Sending: " + message);
        log.debug("Source: " + logging.getStack(null, 0, 4));

        var _ = require("contrib/underscore");

        var _defaultOpts = _.clone(defaultOpts);
        if (this.categories.get(category))
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

        if (opts.command)
        {
            opts.classlist += " clickable"
        }

        if (isNaN(opts.priority))
        {
            if (("P_" + opts.priority.toUpperCase() in this) != 'undefined')
            {
                opts.classlist += " " + opts.priority.toLowerCase();
                opts.priority = this["P_" + opts.priority.toUpperCase()];
            }
            else
            {
                opts.classlist += " notification";
                opts.priority = this.P_INFO;
            }
        }
        else
        {
            switch (opts.priority)
            {
                case this.P_ERROR:
                    opts.classlist += " error";
                    break;
                case this.P_WARNING:
                    opts.classlist += " warning";
                    break;
                default:
                case this.P_INFO:
                    opts.classlist += " notification";
                    break;
            }
        }

        if (opts.panel)
        {
            // For now we'll use the old notification library, ideally this should
            // be merged into the notify module
            ko.notifications.add(message, [category], opts.id || window.Date.now(),
                                 {severity: opts.priority, notify: true});
        }

        if (disabledCats.findString(category) != -1 && opts.priority == this.P_INFO)
        {
            return;
        }

        var notif = {
            message: message,
            category: category,
            opts: opts
        };

        this.queue(notif);
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

        // Queue or hand off immediately
        if (queue[notif.opts.from].active && (! notif.opts.id ||
            notif.opts.id != queue[notif.opts.from].activeId))
        {
            var append = queue.length;
            var replace = 0;
            var _queue = queue[notif.opts.from].items;
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
        }
        else
        {
            this.showNotification(notif);
        }

        queue[notif.opts.from].active = true;
    }

    this.queue.process = (from) =>
    {
        var notif = queue[from].items.shift();

        if (notif)
        {
            window.setTimeout(this.showNotification.bind(this, notif), 250);
        }
        else
        {
            queue[from].active = false;
        }
    }

    this.showNotification = (notif) =>
    {
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

        panel.css("opacity", 0);
        $("#komodoMainPopupSet").append(panel);
        panel.on("popupshown", function(e)
        {
            if (e.target != panel.element()) return;
            this.doShowNotification(notif, panel, ! replace);
        }.bind(this));
        panel.element().openPopup();
    }

    this.doShowNotification = (notif, panel, animate = true) =>
    {
        log.debug("Showing: " + notif.message);

        var opts = notif.opts;

        panel.attr("noautohide", true);
        panel.noautohide = true;
        var pos = this._calculatePosition(opts.from || null, panel);
        panel.element().moveTo(pos.x, pos.y);

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

        callback = () =>
        {
            if ( ! panel.exists()) return;

            log.debug("Hiding panel");

            queue[notif.opts.from].activeId = null;
            queue[notif.opts.from].activePanel = null;
            this.hideNotification(panel, this.queue.process.bind(this,notif.opts.from))
        }

        var time = opts.duration || prefs.getLong("notify_duration", 4000);
        var timeout = window.setTimeout(() =>
        {
            log.debug("Calling callback from timeout");
            callback();
        }, time);

        log.debug("Showing for " + time + "ms");

        // Handle notification interactions
        var focus = document.activeElement;
        var interacting = false;
        var interact = () =>
        {
            log.debug("Panel interact");

            window.clearTimeout(timeout);
            interacting = true;
        };
        var blur = () =>
        {
            log.debug("Panel blur");

            interacting = false;
            timeout = window.setTimeout(callback.bind(this), 1000);

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
            disabledCats.appendString(notif.category);
        });

        panel.find("menuitem[anonid=preferences]").on("command", () =>
        {

        });
    }

    this.hideNotification = (panel, callback) =>
    {
        if (panel.element().hasFocus)
        {
            panel.on("blur", this.hideNotification.bind(this, panel, callback));
            return;
        }

        panel.animate(
            {
                opacity: 0,
                panelY: panel.element().boxObject.screenY + 30,
            },
            { duration: 100 },
            function()
            {
                panel.remove(panel);
                callback();
            }
        );
    }

    this._calculatePosition = (from, panel) =>
    {
        var pos,
            scintilla = ko.views.manager.currentView.scintilla;

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

            var computed = window.getComputedStyle(panel.element());
            pos.y -= parseInt(computed.paddingBottom.replace(/px$/,''));
            pos.y -= parseInt(computed.paddingTop.replace(/px$/,''));

            // Editor preset cant (shouldnt) be centered
            return normalize(pos);
        }

        // Center horizontally on the editor
        else if (scintilla && editor.available())
        {
            var scx = scintilla.boxObject.screenX,
                scy = scintilla.boxObject.screenY,
                scw = scintilla.boxObject.width,
                sch = scintilla.boxObject.height,
                sclh = editor.defaultTextHeight();
            pos = {x: (scw / 2) + scx, y: (scy + sch) - (sclh * 4)};
        }
        else
        {
            // Center horizontally on the window
            var w = window.innerWidth,
                h = window.innerHeight;
            pos = {x: (scw / 2) + scx, y: (scy + sch) + 100};
        }

        // Center the panel
        var box = panel.element().boxObject;
        pos.x = pos.x - (box.width / 2);

        return normalize(pos);
    }

}).apply(module.exports);
