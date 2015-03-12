(function() {

    const log       = require("ko/logging").getLogger("notify-observer");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var NotifyObserver = function() { }

    NotifyObserver.prototype.init = function()
    {
        log.info("init");
        // Old Komodo status messages (usually from Python).
        Services.obs.addObserver(this, 'status_message', false);
        // Simple string notifications (usually from Python).
        Services.obs.addObserver(this, 'komodo_notify_error', false);
        Services.obs.addObserver(this, 'komodo_notify_warning', false);
        Services.obs.addObserver(this, 'komodo_notify_info', false);
        // Mozilla auto update notifications (from JS/C++).
        Services.obs.addObserver(this, 'autoupdate-notification', false);

        // TODO: Is this needed (instead of 'status_message')?
        //Cc["@activestate.com/koNotification/manager;1"]
        //  .getService(Ci.koINotificationManager)
        //  .addListener(this);
    }

    NotifyObserver.prototype.observe = function(subject, topic, data)
    {
        log.debug("observed '"+topic+"': ");
        switch (topic)
        {
            case 'status_message':
                // Note: subject implements the koINotification interface.
                if (!subject.summary) {
                    // Nothing to say?
                    return;
                }
                if (subject instanceof Ci.koINotificationProgress &&
                    subject.maxProgress != Ci.koINotificationProgress.PROGRESS_INDETERMINATE)
                {
                    // Don't log repeat notifications 
                    return;
                }
                let severity_array = ["info", "warning", "error"];
                // "subject" is expected to be a koIStatusMessage object.
                require("notify/notify").send(subject.summary, subject.category + "-event",
                {
                    priority: severity_array[subject.severity]
                });
                break;
            case 'komodo_notify_error':
            case 'komodo_notify_warning':
            case 'komodo_notify_info':
                // data string expected to be in the form:
                //   "debugger: This is the error message"
                let priority = topic.substr("komodo_notify_".length);
                let message = data;
                let category = message.split(":", 1)[0];
                if (category.length < message.length) {
                    message = message.substr(category.length + 1);
                } else {
                    category = priority;
                }
                // "data" is expected to be an error message string.
                require("notify/notify").send(message, category + "-event",
                {
                    priority: priority
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

        notify.send(data.title + " - " + data.message, "autoUpdate",
        {
            command: command,
            priority: "warning"
        });
    }

    //NotifyObserver.prototype.onNotification = function(notification, oldIndex, newIndex, reason)
    //{
    //    dump('\nnotification: ' + notification + '\n');
    //    dump('oldIndex: ' + oldIndex + '\n');
    //    dump('reason: ' + reason + '\n');
    //    dump('newIndex: ' + newIndex + '\n\n');
    //}

    // Instantiate the observer.
    var observer = new NotifyObserver();
    observer.init();

})();
