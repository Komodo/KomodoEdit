(function() {
    const log       = require("ko/logging").getLogger("commando-scope-files-expand");
    const commando  = require("commando/commando");
    const $         = require("ko/dom");
    const prefs     = require("ko/prefs");
    const handler   = require("scope-files/files");

    var spref       = prefs.getPref("scope-files-shortcuts");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local       = {
        copy: null,
        cut: null
    };

    var entries = [
        {
            id: "create",
            name: "Create File",
            scope: "scope-files",
            command: doCreate,
            allowExpand: false,
            type: "dir"
        },
        {
            id: "move",
            name: "Move",
            scope: "scope-files",
            command: doMove,
            allowExpand: false
        },
        {
            id: "copy",
            name: "Copy",
            scope: "scope-files",
            command: doCopy,
            allowExpand: false
        },
        {
            id: "rename",
            name: "Rename",
            scope: "scope-files",
            command: doRename,
            allowExpand: false
        }
    ];

    var resultCache = [];
    var resultCacheVersion = -1;

    var getResults = function(query)
    {
        var item = commando.getSubscope();

        if (resultCacheVersion == item.id) return resultCache;
        resultCacheVersion  = item.id

        resultCache = entries.slice(0).filter(function(entry)
        {
            return ! ("type" in entry) || entry.type == item.data.type;
        });

        if (item.data.type == "dir" && (local.cut || local.copy))
        {
            var tip;
            if (local.cut)
                tip = "Move " + local.cut.name + " here";
            else
                tip = "Copy " + local.copy.name + " here";

            resultCache.push({
                id: "paste",
                name: "Paste",
                scope: "scope-files",
                tip: tip,
                command: doPaste,
                allowExpand: false
            });
        }

        var shortcut;
        for (let x=0;x<spref.length;x++)
        {
            let _s = spref.getString(x);
            let [s, path] = _s.split(":");
            if (path == item.data.path) shortcut = _s;
        }

        if (item.data.type == "dir" && ! shortcut)
        {
            resultCache.push({
                id: "addShortcut",
                name: "Add Shortcut",
                scope: "scope-files",
                command: addShortcut,
                allowExpand: false
            });
        }

        if (item.data.type == "dir" && shortcut)
        {
            resultCache.push({
                id: "removeShortcut",
                name: "Remove Shortcut",
                scope: "scope-files",
                tip: "Remove Shortcut: " + shortcut.split(":")[0],
                command: removeShortcut,
                allowExpand: false
            });
        }

        return resultCache;
    }

    this.onSearch = function(query, uuid, onComplete)
    {
        commando.renderResults(commando.filter(getResults(query), query), uuid);
        onComplete()
    }
    
    function doCreate()
    {
        var ioFile = require("sdk/io/file");
        var item = commando.getSubscope();

        var filename = commando.prompt("Filename: ");

        if ( ! filename) return;

        try
        {
            require("ko/file").create(item.data.path, filename);
        }
        catch (e)
        {
            commando.tip("Error: " + e.message, "error");
            return false;
        }
        
        commando.tip("File \""+filename+"\" has been created");
    }

    function doPaste()
    {
        var item = commando.getSubscope();
        var path = (local.cut || local.copy).data.path;
        var ioFile = require("ko/file");
        var newPath = ioFile.join(item.data.path, ioFile.basename(path));

        if (local.cut)
            ioFile.move(path, newPath);
        else
            ioFile.copy(path, newPath);

        item.isExpanded = false;
        commando.clear();

        if (local.cut)
        {
            commando.tip('Moved "'+local.cut.name+'" here');
            local.cut = null;
        }
        else
        {
            commando.tip('Copied "'+local.copy.name+'" here');
            local.copy = null;
        }
    }

    function doMove()
    {
        local.copy = null;
        local.cut = commando.getSubscope();

        commando.tip('Moving: "'+local.cut.name+'", expand a folder to paste it');
        commando.navBack();
    }

    function doCopy()
    {
        local.cut = null;
        local.copy = commando.getSubscope();

        commando.tip('Copying: "'+local.copy.name+'", expand a folder to paste it');
        commando.navBack();
    }

    function doRename()
    {
        var ioFile = require("sdk/io/file");
        var item = commando.getSubscope();

        var oldName = ioFile.basename(item.data.path);
        newName = commando.prompt("Renaming " + item.data.path, "New Name: ", oldName);

        if ( ! newName) return;

        var newpath = require("ko/file").rename(item.data.path, newName);

        item.data.path = newpath;
        item.name = newName;
        item.icon  = item.data.type == 'dir' ? item.icon : "koicon://" + newpath + "?size=16",

        commando.setSubscope(item, false);
        commando.reSearch();
        commando.focus();
    }

    function addShortcut()
    {
        var item = commando.getSubscope();
        var shortcut = commando.prompt(null, "Enter shortcut: ");

        if (shortcut.search(/^[A-Za-z0-9]+$/) == -1)
        {
            return commando.tip("Shortcuts need to be alphanumeric and can not contain whitespace", "error");
        }

        var _shortcut = shortcut + ":" + item.data.path;
        spref.appendString(_shortcut);
        
        resultCacheVersion = -1;
        handler.clearShortcutCache();

        commando.tip("Shortcut added, you can use it by typing '"+shortcut+"/'");
        commando.navBack();
    }

    function removeShortcut()
    {
        var item = commando.getSubscope();

        for (let x=0;x<spref.length;x++)
        {
            let [shortcut, path] = spref.getString(x).split(":");
            if (path == item.data.path)
            {
                spref.deletePref(x);
                break;
            }
        }

        resultCacheVersion = -1;
        handler.clearShortcutCache();

        commando.reSearch();
        commando.tip();
    }

}).apply(module.exports);
