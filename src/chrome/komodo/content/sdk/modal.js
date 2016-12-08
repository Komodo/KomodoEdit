(function()
{
    
    this.open = (title, fields, callback, okLabel, cancelLabel) =>
    {
        okLabel = okLabel || "Ok";
        cancelLabel = cancelLabel || callback ? "Cancel" : "Close";
        
        var panel = require("ko/ui/panel").create({
            attributes: {
                backdrag: true,
                noautohide: true,
                width: "450px",
                class: "dialog modal-ui"
            }
        });
        
        panel.addRow(
            require("ko/ui/label").create(title),
            { attributes: { align: "center", pack: "center", class: "ui-title" } }
        );
        
        var parent = panel;
        var currentGroup;
        var groups = {};
        var mapping = {};
        
        for (let key in fields)
        {
            let field = fields[key];

            if (typeof field == "string")
                field = { label: field };
            
            if (field.group)
            {
                if ( ! (field.group in groups))
                {
                    groups[field.group] = require("ko/ui/groupbox").create({ caption: field.group });
                    panel.add(groups[field.group]);
                }
                
                parent = groups[field.group];
            }
            else
            {
                parent = panel;
                currentGroup = null;
            }
            
            let row = parent.addRow();
            
            if (field.label)
                row.add(require("ko/ui/label").create(field.label + ":"));
            
            let elem = require("ko/ui/" + (field.type || "textbox")).create(field.options || undefined);
            mapping[key] = elem;
            row.add(elem);
            
            field.elem = elem;
            
            if (field.entries && elem.entries)
                elem.entries(field.entries);
            
            if (field.value && elem.value)
                elem.value(field.value);
        }
        
        var errorLabel = require("ko/ui/label").create({ attributes: { class: "fullwidth state-error" } });
        errorLabel.hide();
        panel.addRow(
            errorLabel,
            { attributes: { align: "center", pack: "center", class: "ui-error" } }
        );
        
        var buttonRow = panel.addRow({ attributes: { align: "center", pack: "center" } });
        buttonRow.addClass("buttons-ui");
        
        if (callback)
        {
            var okButton = require("ko/ui/button").create(okLabel);
            okButton.onCommand(onFormComplete.bind(this, panel, fields, callback));
            buttonRow.add(okButton);
        }
        
        var cancelButton = require("ko/ui/button").create(cancelLabel);
        cancelButton.onCommand(function()
        {
            panel.remove();
            
            if (callback)
                callback();
        });
        buttonRow.add(cancelButton);
        
        panel.open();
        
        return [panel, mapping];
    };
    
    var onFormComplete = (panel, fields, callback) =>
    {
        var result = {};
        var hasResults = false;
        var missing = [];
        
        for (let key in fields)
        {
            hasResults = true;
            
            if ("value" in fields[key].elem)
                result[key] = fields[key].elem.value();
            else
                result[key] = null;
            
            if (fields[key].required && (result[key] === null || result[key] === ""))
                missing.push(fields[key].label);
        }
        
        if (missing.length)
        {
            var error = "Please enter a value for: " + missing.join(", ");
            panel.$element.find(".ui-error label").show().attr("value", error);
            return;
        }
        
        if ( ! hasResults)
            result = true;
        
        var validate = callback(result);
        if (validate !== true && validate !== undefined)
            panel.$element.find(".ui-error label").show().attr("value", validate);
        else
            panel.remove();
    };
    
}).apply(module.exports);
