(function() {

    const log       = require("ko/logging").getLogger("notify-observer");
    log.setLevel(require("ko/logging").LOG_DEBUG);

    const prefs     = Cc['@activestate.com/koPrefService;1']
                        .getService(Ci.koIPrefService).prefs;

    this.init = () =>
    {
        var obsSvc = Cc["@mozilla.org/observer-service;1"].
                        getService(Ci.nsIObserverService);
        obsSvc.addObserver(this, 'status_message',false);
        obsSvc.addObserver(this, 'autoupdate-notification', false);

        Cc["@activestate.com/koNotification/manager;1"]
          .getService(Ci.koINotificationManager)
          .addListener(this);
    }

    this.observe = (subject, topic, data) =>
    {
        // Unless otherwise specified the 'subject' is the view, and 'data'
        // arguments are expected to be empty for all notifications.
        log.debug("StatusBar observed '"+topic+"': ");
        var view = subject;

        switch (topic)
        {
            case 'status_message':
                // "subject" is expected to be a koIStatusMessage object.
                require("notify/notify").send(subject.msg, subject.category,
                {
                    priority: subject.highlight ? "warning" : "info"
                });
                break;
            case 'autoupdate-notification':
                window.setTimeout(function()
                {
                    try
                    {
                        handleAutoUpdateNotify(data);
                    }
                    catch (ex)
                    {
                        log.exception(ex, "autoupdate-notification:: error with notification '" +
                            data + "'");
                    }
                }.bind(this), 5000);
                break;
        }
    }

    var handleAutoUpdateNotify = (data) =>
    {
        var notify = require("notify/notify");

        data = JSON.parse(data);
        if (data.type != "notification")
        {
            return;
        }

        var command;
        if (data.action_label)
        {
            command = () =>
            {
                ko.browse.openUrlInDefaultBrowser(data.action_url);
            }
        }

        notify.send(data.title, "autoUpdate",
        {
            command: command
        });
    }

    this.init();

})();
