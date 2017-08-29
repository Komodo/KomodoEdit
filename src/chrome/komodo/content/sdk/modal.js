(function()
{

    const {Cc, Ci}  = require("chrome");
    
    this.open = (title, fields, onComplete, okLabel, cancelLabel) =>
    {
        var opts;

        if (typeof title == "object")
        {
            opts = title;
        }
        else
        {
            opts = {
                title: title,
                fields: fields,
                onComplete: onComplete,
                onReady: function() {},
                okLabel: okLabel,
                cancelLabel: cancelLabel,
            };
        }

        opts.okLabel = opts.okLabel || "Ok";
        opts.cancelLabel = opts.cancelLabel || opts.callback ? "Cancel" : "Close";

        var w = require("ko/windows").getMain();

        var dialog = w.openDialog("chrome://komodo/content/empty.xul?name=" + opts.title.replace(/\s+/g, ''), opts.title, "modal=true");
        dialog.title = opts.title;
        dialog.addEventListener("load", () => doOpen(opts, dialog));

        pinWindow(dialog);

        return dialog;
    };

    var doOpen = (opts, parent) =>
    {
        var wrapper = require("ko/ui/column").create({ class: "modal-ui-inner" });
        parent.document.documentElement.appendChild(wrapper.element);
        parent.document.documentElement.classList.add("modal-ui");
        parent.document.documentElement.setAttribute("title", opts.title);
        
        opts.parent = parent;
        opts.wrapper = wrapper;
        
        var currentGroup;
        var groups = {};
        var mapping = {};
        var groupParent = wrapper;
        
        for (let key in opts.fields)
        {
            let field = opts.fields[key];

            if (typeof field == "string")
                field = { label: field };
            
            if (field.group)
            {
                if ( ! (field.group in groups))
                {
                    groups[field.group] = require("ko/ui/groupbox").create({ caption: field.group });
                    wrapper.add(groups[field.group]);
                }
                
                groupParent = groups[field.group];
            }
            else
            {
                groupParent = wrapper;
                currentGroup = null;
            }

            let row = groupParent.addRow();
            
            if (field.label !== undefined)
                row.add(require("ko/ui/label").create({ attributes: { value: field.label + ":", tooltiptext: field.label, crop: "center" }}));

            var attributes = field.attributes || {};
            if (field.options)
                attributes.options = field.options;

            let elem = require("ko/ui/" + (field.type || "textbox")).create(attributes);
            mapping[key] = elem;
            row.add(elem);
            
            field.elem = elem;
            
            if (field.fullwidth)
            {
                row.addClass("fullwidth");
                elem.addClass("fullwidth");
            }

            if (field.centered)
            {
                row.addClass("centered");
            }

            if (field.entries && elem.entries)
                elem.entries(field.entries);
            
            if (field.value && elem.value)
                elem.value(field.value);
        }
        
        var errorLabel = require("ko/ui/label").create({ attributes: { class: "fullwidth state-error" } });
        errorLabel.hide();
        wrapper.addRow(
            errorLabel,
            { attributes: { align: "center", pack: "center", class: "ui-error" } }
        );
        
        var buttonRow = wrapper.addRow({ attributes: { align: "center", pack: "center" } });
        buttonRow.addClass("buttons-ui");
        
        if (opts.onComplete)
        {
            var okButton = require("ko/ui/button").create(opts.okLabel);
            okButton.onCommand(onFormComplete.bind(this, opts));
            buttonRow.add(okButton);
        }
        
        var cancelButton = require("ko/ui/button").create(opts.cancelLabel);
        cancelButton.onCommand(function()
        {
            parent.close();
            
            if (opts.onComplete)
                opts.onComplete();
        });
        buttonRow.add(cancelButton);
        
        if (opts.onReady)
            opts.onReady(parent, mapping);

        parent.sizeToContent();
    };
    
    var onFormComplete = (opts) =>
    {
        var result = {};
        var hasResults = false;
        var missing = [];
        
        for (let key in opts.fields)
        {
            hasResults = true;
            
            if ("value" in opts.fields[key].elem)
                result[key] = opts.fields[key].elem.value();
            else
                result[key] = null;
            
            if (opts.fields[key].required && (result[key] === null || result[key] === ""))
                missing.push(opts.fields[key].label);
        }
        
        if (missing.length)
        {
            var error = "Please enter a value for: " + missing.join(", ");
            parent.$element.find(".ui-error label").show().attr("value", error);
            return;
        }
        
        if ( ! hasResults)
            result = true;
        
        var validate = opts.onComplete(result);
        if (validate !== true && validate !== undefined)
            opts.wrapper.$element.find(".ui-error label").show().attr("value", validate);
        else
        {
            opts.parent.close();}
    };
    
    var pinWindow = (w) =>
    {
        function getXULWindowForDOMWindow(win)
            win.QueryInterface(Ci.nsIInterfaceRequestor)
               .getInterface(Ci.nsIWebNavigation)
               .QueryInterface(Ci.nsIDocShellTreeItem)
               .treeOwner
               .QueryInterface(Ci.nsIInterfaceRequestor)
               .getInterface(Ci.nsIXULWindow)

        w = getXULWindowForDOMWindow(w);
        let parentWin = getXULWindowForDOMWindow(require("ko/windows").getMain());

        Cc["@activestate.com/koIWindowManagerUtils;1"]
          .getService(Ci.koIWindowManagerUtils)
          .setOnTop(w, parentWin, true);
    };
    
}).apply(module.exports);
