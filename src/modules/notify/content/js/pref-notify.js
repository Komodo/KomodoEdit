(function()
{

    var pwin = parent.opener;
    if ( ! "ko" in pwin)
        pwin = parent.opener.ko.windowManager.getMainWindow();

    ko = pwin.ko;

    var notify  = require("notify/notify");
    var $       = require("ko/dom");
    var log     = require("ko/logging").getLogger("pref-notify");

    //log.setLevel(10);

    window.OnPreferencePageLoading = (prefset) =>
    {
        var pref = prefset.getPref('notify_disabled_categories');
        var categories = notify.categories.get();
        var wrapper = $("#enabled-notifications-vbox");

        var i = 0, wrap;
        for (let key in categories)
        {
            if (++i % 2) wrap = $('<hbox>');

            let category = categories[key];
            let elem = $('<checkbox>');
            elem.attr(
            {
                label: category.label,
                value: key,
                checked: pref.findString(key) == -1
            });

            wrap.append(elem);
            if ( ! (i % 2))
            {
                wrapper.append(wrap);
            }
        }
    }

    window.OnPreferencePageOK = (prefset) =>
    {
        var pref = prefset.getPref('notify_disabled_categories');

        pref.reset();
        $("checkbox").each(function()
        {
            if (this.checked) return;
            pref.appendString(this.getAttribute("value"));
        });
        return true;
    }

    window.addEventListener("load", parent.hPrefWindow.onpageload.bind(parent.hPrefWindow));
})();
