if (typeof ko === 'undefined') var ko = {};

ko.__defineGetter__("notifications", function() {
    Components.utils.import("resource://gre/modules/notifications.js");
    return NotificationSvc;
});

