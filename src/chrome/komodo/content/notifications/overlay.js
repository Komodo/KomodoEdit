/* Original code is Mozilla Weave */

if (typeof(Cc) == "undefined")
    var Cc = Components.classes;
if (typeof(Ci) == "undefined")
    var Ci = Components.interfaces;
if (typeof Cu == "undefined")
    var Cu = Components.utils;
if (typeof Cr == "undefined")
    var Cr = Components.results;

function NotificationUIController() {
    var observerSvc = Cc["@mozilla.org/observer-service;1"].
                        getService(Components.interfaces.nsIObserverService);
    
    observerSvc.addObserver(this, "komodo:notification:added", false);
    observerSvc.addObserver(this, "komodo:notification:removed", false);
    let this_ = this;
    window.addEventListener("unload", function() {
        observerSvc.removeObserver(this_, "komodo:notification:added");
        observerSvc.removeObserver(this_, "komodo:notification:removed");
    }, false);

    // makes sure notifications are set up right for new windows
    this.onNotificationRemoved();
}
NotificationUIController.prototype = {
    observe: function(subject, topic, data) {
        if (subject && subject.hasOwnProperty("wrappedJSObject")) {
            // Unwrap the XPCOM object
            let notification = subject.wrappedJSObject;
            
            switch(topic) {
                case "komodo:notification:added":
                    this.onNotificationAdded(notification);
                    break;
                case "komodo:notification:removed":
                    this.onNotificationRemoved(notification);
                    break;
            }
        }
    },
    
    onNotificationAdded: function(notification) {
        if (notification && notification instanceof ko.notifications.Notification) {
            let box = document.getElementById("komodo-notifications-box");
            if (box)
                box.onNotificationAdded(notification);
        }
        
        let button = document.getElementById("komodo-notifications-button");
        if (!button)
            return;

        button.hidden = false;        
        let notifications = ko.notifications.notifications;
        let priority = 0;
        for (let i = 0; i < notifications.length; i++) {
            if (notifications[i].priority > priority) {
                priority = notifications[i].priority;
                var title = notifications[i].title;
            }
        }

        let image = priority >= ko.notifications.PRIORITY_WARNING ?
                                "chrome://global/skin/icons/warning-16.png" :
                                "chrome://global/skin/icons/information-16.png";
        button.setAttribute("image", image);
        button.setAttribute("label", title);
    },

    onNotificationRemoved: function(notification) {
        if (notification && notification instanceof ko.notifications.Notification) {
            let box = document.getElementById("komodo-notifications-box");
            if (box)
                box.onNotificationRemoved(notification);
        }
        
        if (ko.notifications.notifications.length == 0) {
            let button = document.getElementById("komodo-notifications-button");
            if (button)
                button.hidden = true;
        }
        else
            // Display remaining notifications (if any).
            this.onNotificationAdded();
    }
};

window.addEventListener("load", function(e) {
    ko.notifications.ui = new NotificationUIController();
}, false);
