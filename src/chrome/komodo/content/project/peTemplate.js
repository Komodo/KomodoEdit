/* Copyright (c) ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function()
{ // ko.projects
    var log = require('ko/logging').getLogger("toolbox.template");

    // Open a new template dialog
    this.addTemplate = function addTemplate(/*koIPart|koITool*/ parent,
                                              /*koIPart|koITool*/ part )
    {
        if (typeof(part) == "undefined")
        {
            part = parent.project.createPartFromType('template');
        }
        part.setStringAttribute('name', 'New Template');
        part.setStringAttribute('language', "Text");
        part.setStringAttribute('treat_as_ejs', "false");
        part.setStringAttribute('lang_default', "false");

        var obj = {};
        obj.item = part;
        obj.parent = parent;
        obj.task = 'new';
        ko.windowManager.openOrFocusDialog(
            "chrome://komodo/content/project/templateProperties.xul",
            "Komodo:TemplateProperties",
            "chrome,centerscreen,close=yes,dependent=no,resizable=yes",
            obj);
    };

    // Open an existing template dialog
    this.templateProperties = (item) =>
    {
        var obj = {item : item,
                task : 'edit',
                imgsrc : 'chrome://komodo/skin/images/toolbox/template.svg'};
        window.openDialog(
            "chrome://komodo/content/project/templateProperties.xul",
            "Komodo:TemplateProperties",
            "chrome,centerscreen,close=yes,dependent=no,resizable=yes",
            obj);
    };

    this.chooseTemplate = (path, callback) =>
    {
        var $ = require("ko/dom");
        var commando = require("commando");

        commando.showSubscope("scope-tools", "tool-category-template");

        var handleViewOpened = (e) =>
        {
            window.removeEventListener("editor_view_opened_from_template", handleViewOpened);

            var view = e.detail.view;
            if ( ! view.koDoc.isUntitled)
                return;

            if (path)
            {
                if ( ! path.match(/\w\.\w+$/))
                {
                    var filename = require("ko/dialogs").prompt("Saving to " + path, { label: "Filename:" });
                    path = require("ko/file").join(path, filename);
                }
                view.saveAsURI(ko.uriparse.localPathToURI(path));
            }

            callback(view);
        };

        window.addEventListener("editor_view_opened_from_template", handleViewOpened);
        $("#commando-panel").once("popuphidden", () =>
        {
            setTimeout(() =>
            {
                window.removeEventListener("editor_view_opened_from_template", handleViewOpened);
            }, 1000);
        });
    };

    this.useTemplate = (template) =>
    {
        var view = ko.views.manager.currentView;
        if ( ! view || ! view.scimoz || view.scimoz.length)
        {
            ko.views.manager.doNewViewAsync(template.getStringAttribute("language"), "editor", (view) =>
            {
                _doUseTemplate(view, template);

                var evt = new CustomEvent("editor_view_opened_from_template", { detail: { view: view } });
                window.dispatchEvent(evt);
            });
            return;
        }

        _doUseTemplate(view, template);

        var evt = new CustomEvent("editor_view_used_from_template", { detail: { view: view } });
        window.dispatchEvent(evt);
    };

    var _autoInsertTemplate = () =>
    {
        var view = ko.views.manager.currentView;
        var scimoz = view.scimoz;

        if (scimoz && ! scimoz.text.length)
        {
            var language = view.koDoc.language;
            var template = ko.toolbox2.getDefaultTemplateForLanguage(language);
            if (template)
            {
                ko.projects.useTemplate(template);
            }
        }
    };

    var _textFromEJSTemplate = (tool, view) =>
    {
        var text = tool.value;

        var eol = view.koDoc.new_line_endings;
        var eol_str;
        switch (eol)
        {
            case Components.interfaces.koIDocument.EOL_LF:
                eol_str = "\n";
                break;
            case Components.interfaces.koIDocument.EOL_CRLF:
                eol_str = "\r\n";
                break;
            case Components.interfaces.koIDocument.EOL_CR:
                eol_str = "\r";
                break;
        }
            
        var ejs = null;
        try
        {
            ejs = new ko.snippets.EJS(text);
        }
        catch(ex)
        {
            ex.fileName = this.toolPathShortName(tool);
            var msg2 = _bundle.formatStringFromName("template exception details 2",
                                                    [ex.fileName], 1);
            var msg3 = _bundle.formatStringFromName("template exception details 3",
                                                    [ex.lineNumber + 1], 1);
            var msg = ex + "\n" + msg2 + "\n" + msg3;
            ko.dialogs.alert(null, msg, "Error in template");
        }
        var ejsOut = ejs.render();
        text = (eol != Components.interfaces.koIDocument.EOL_LF ? ejsOut.replace(/\n/g, eol_str) : ejsOut);
        return text;
    };

    var _doUseTemplate = (view, template) =>
    {
        var text = template.value;
        
        var ejs = template.getStringAttribute('treat_as_ejs');
        if (ejs === true || ejs === "true")
        {
            text = _textFromEJSTemplate(template, view);
        }

        view.scimoz.text = text;
        view.koDoc.language = template.getStringAttribute("language");
    };
    
    window.addEventListener("current_view_language_changed", _autoInsertTemplate);
    window.addEventListener("view_document_attached", () => setTimeout(_autoInsertTemplate, 100)); // scimoz isnt ready when fired

}).apply(ko.projects);
