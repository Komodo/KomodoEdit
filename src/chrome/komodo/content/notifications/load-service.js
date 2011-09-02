if (typeof ko === 'undefined') var ko = {};

Components.utils
          .import("resource://gre/modules/XPCOMUtils.jsm", {})
          .XPCOMUtils
          .defineLazyGetter(ko, "notifications", function()
{
    var {KoNotificationManagerWrapper} =
        Components.utils.import("resource://gre/modules/notifications.js", {});
    return new KoNotificationManagerWrapper(window);
});
