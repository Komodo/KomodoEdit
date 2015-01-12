(function()
{

    var pwin = parent.opener;
    if ( ! "ko" in pwin)
        pwin = parent.opener.ko.windowManager.getMainWindow();

    ko = pwin.ko;

    var notify  = require("notify/notify");
    var $       = require("ko/dom");
    var log     = require("ko/logging").getLogger("pref-notify");
    const _     = require("contrib/underscore");

    //log.setLevel(10);

    window.OnPreferencePageLoading = (prefset) =>
    {
        var pref = prefset.getPref('notify_disabled_categories');
        var categories = notify.categories.get();
        categories = _.sortBy(categories, (o) => o.label);
        var wrapper = $("#enabled-notifications-vbox");
        
        log.debug("Disabled categories: " + pref.length);

        var i = 0, wrap;
        for (let key in categories)
        {
            if (++i % 2) wrap = $('<hbox>');

            let category = categories[key];
            let elem = $('<checkbox>');
            elem.attr(
            {
                label: category.label,
                value: category.id,
                checked: pref.findString(category.id) == -1
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

        $("checkbox").each(function()
        {
            var id = this.getAttribute("value");
            var disabled = pref.findString(id) != -1;

            if ( ! this.checked && ! disabled)
            {
                log.debug("Add: " + id);
                pref.appendString(id);
            }
            else if (this.checked && disabled)
            {
                log.debug("Remove: " + id);
                pref.findAndDeleteString(id);
            }
        });
        return true;
    }

    window.addEventListener("load", parent.hPrefWindow.onpageload.bind(parent.hPrefWindow));
})();
