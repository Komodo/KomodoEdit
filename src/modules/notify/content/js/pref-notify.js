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
        $('#enabled-notifications-warning-vbox').hide();
        $('#enabled-notifications-error-vbox').hide();
        
        loadCategories('notify_disabled_categories',
                       '#enabled-notifications-vbox', prefset);
        loadCategories('notify_disabled_categories_warning',
                       '#enabled-notifications-warning-vbox', prefset);
        loadCategories('notify_disabled_categories_error',
                       '#enabled-notifications-error-vbox', prefset);
        
        var level = $("#level");
        level.on("command", function()
        {
            var l = level.value();
            
            $('#enabled-notifications-vbox').hide();
            $('#enabled-notifications-warning-vbox').hide();
            $('#enabled-notifications-error-vbox').hide();
            
            switch (l)
            {
                case "INFO":
                    $('#enabled-notifications-vbox').show();
                    break;
                case "WARNING":
                    $('#enabled-notifications-warning-vbox').show();
                    break;
                case "ERROR":
                    $('#enabled-notifications-error-vbox').show();
                    break;
            }
        });
    }

    window.OnPreferencePageOK = (prefset) =>
    {
        $("checkbox").each(function()
        {
            var pref = prefset.getPref(this.getAttribute("ownerPrefName"));
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
    
    var loadCategories = (prefName, wrapper, prefset) =>
    {
        var pref = prefset.getPref(prefName);
        var categories = notify.categories.get();
        categories = _.sortBy(categories, (o) => o.label);
        wrapper = $(wrapper);
        
        log.debug("Disabled categories: " + pref.length);

        var i = 0, wrap;
        for (let key in categories)
        {
            if (++i % 2) wrap = $('<hbox>');

            let category = categories[key];
            let elem = $('<checkbox>');
            elem.attr(
            {
                id: 'category-' + category.id,
                label: category.label,
                value: category.id,
                checked: pref.findString(category.id) == -1,
                ownerPrefName: prefName
            });

            wrap.append(elem);
            if ( ! (i % 2))
            {
                wrapper.append(wrap);
            }
        }
    }

    window.addEventListener("load", parent.hPrefWindow.onpageload.bind(parent.hPrefWindow));
})();
