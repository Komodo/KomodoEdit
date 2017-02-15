/* Copyright (c) ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

    var koFile = require("ko/file");
    var log = ko.logging.getLogger('peFolderTemplate');
    var nextTarget;

    this.folderTemplateProperties = (/*koIPart*/ item) =>
    {
        var obj = {};
        obj.item = item;
        obj.task = 'edit';
        obj.imgsrc = 'chrome://komodo/skin/images/toolbox/folder_template.svg';
        obj.type = 'folder_template';
        obj.prettytype = 'FolderTemplate';
        window.openDialog(
            "chrome://komodo/content/project/simplePartProperties.xul",
            "Komodo:URLProperties",
            "chrome,centerscreen,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
    };

    this.addFolderTemplate = (/*koIPart|koITool*/ parent,
                                        /*koIPart|koITool = null */ part ) =>
    {
        if (typeof(part) == "undefined") {
            part = parent.project.createPartFromType('folder_template');
        }
        part.setStringAttribute('name', 'New Folder Template');
        part.value = '';
        var obj = {};
        obj.item = part;
        obj.task = 'new';
        obj.imgsrc = 'chrome://komodo/skin/images/toolbox/folder_template.svg';
        obj.type = 'folder_template';
        obj.prettytype = 'FolderTemplate';
        obj.parent = parent;
        window.openDialog(
            "chrome://komodo/content/project/simplePartProperties.xul",
            "Komodo:URLProperties",
            "chrome,centerscreen,close=yes,modal=yes,resizable=yes", obj);
    };

    this.createFolderTemplateFromDir = (dir) =>
    {
        // Retrieve name
        var basename = koFile.basename(dir);
        var name = ko.dialogs.prompt("Saving Folder Template", "Enter name: ");
        if (!name) return;

        // Determine target folder
        var dirSvc = Components.classes["@activestate.com/koDirs;1"].getService();
        var profd = dirSvc.userDataDir;
        var target = koFile.join(profd, "folder-templates", name);

        var c = 1;
        while (koFile.exists(target))
            target = koFile.join(profd, "folder-templates", name + "-" + (c++));

        // Validate source
        if ( ! koFile.exists(dir) || koFile.isFile(dir))
        {
            require("ko/dialogs").alert("Invalid location: " + dir);
            return;
        }

        var progress = require("ko/progress").open();
        progress.message("Copying files ..");

        // Copy files recursively
        var koUtils = Cc["@activestate.com/koUtils;1"].getService(Ci.koIUtils);
        koUtils.copytree(dir, target, function(status, message)
        {
            if (status !== 0)
            {
                progress.close();
                require("ko/dialogs").alert("Copying failed with message: " + message);
                return;
            }
            
            // Create the tool and show the toolbox
            var part = ko.toolbox2.createPartFromType('folder_template');
            part.setStringAttribute('name', name);
            part.value = ko.uriparse.pathToURI(target);
            ko.toolbox2.addItem(part);
            ko.uilayout.ensureTabShown('toolbox2viewbox');

            progress.message("Done");
            setTimeout(() => progress.close(), 1000);
        });
    };

    this.chooseFolderTemplate = (target) =>
    {
        var $ = require("ko/dom");
        var commando = require("commando");

        // Commando doesn't currently support proper callback handling, so we
        // save a variable with the next target location, which gets reset when
        // Commando closes
        nextTarget = target;

        // Show the folder template subscope
        commando.showSubscope("scope-tools", "tool-category-folder_template");
        
        // When commando closes reset nextTarget
        $("#commando-panel").once("popuphidden", () =>
        {
            setTimeout(() =>
            {
                nextTarget = null;
            }, 100);
        });
    };

    this.useFolderTemplate = (url, target, prompt = true) =>
    {
        // url could also be a tool object
        if (typeof url == "object")
            url = url.value;

        var msg;

        target = target || nextTarget;
        nextTarget = null;

        // Typically the first call to this method should prompt to verify the 
        // target location
        if (prompt)
        {
            var onSelect = (path) =>
            {
                if ( ! path)
                    return;

                this.useFolderTemplate(url, path, false);
            };

            msg = "Select unpack location. Conflicting files will be overwritten.";
            require("ko/dialogs").filepicker(msg,
            {
                type: "dir",
                callback: onSelect,
                path: target
            });
            return;
        }

        var progress = require("ko/progress").open();
        progress.message("Analyzing URL ..");

        url = require("sdk/url").URL(url);

        // Check if this is a local file/folder or remote
        if (url.scheme == "file")
        {
            // No point importing a file that doesnt exist
            if ( ! koFile.exists(url.path))
            {
                progress.close();
                require("ko/dialogs").alert("Local path does not exist: " + url.path);
                return;
            }

            // If this is a file then assume it's a ZIP
            if (koFile.isFile(url.path))
            {
                _useZip(url.path, "", target, progress);
            }
            // Otherwise import a folder
            else
            {
                _useFolder(url.path, target, progress);
            }

            return;
        }

        // If the local file conditional didnt trigger then this is a ZIP url
        // and we need to download the ZIP
        _useUrl(url, target, progress);
    };

    var _useUrl = (url, target, progress) =>
    {
        var basename = koFile.basename(url.path);
        progress.message("Downloading " + basename + " ..");

        Cu.import("resource://gre/modules/FileUtils.jsm");
        Cu.import("resource://gre/modules/Downloads.jsm");
        Cu.import("resource://gre/modules/Task.jsm");

        // If this is a github zip then we need to automatically recurse into the
        // relevant subfolder, as github zips contain a folder with the repository
        // and branch name
        var subfolder = "";
        if (url.host == "github.com")
        {
            var match = url.path.match(/([\w\.\-]+)\/archive\/([\w\.\-]+).zip/);
            if (match)
            {
                subfolder = match[1] + "-" + match[2];
            }
        }

        // Download to a temp location
        var tmp = FileUtils.getFile("TmpD", [basename]).path;

        var _onFileDownloadFailed = (message) =>
        {
            // Mozilla doesnt seem to give us a clean way of getting a humanly
            // readable error message, so we have to strip it from the exception
            // message
            var match = message.toString().match(/"(.*?)"/);
            if (match)
                message = match[1];

            progress.close();
            require("ko/dialogs").alert("Download of folder template failed with message: " + message);
            return true;
        };

        var _onFileDownloaded = () =>
        {
            _useZip(tmp, subfolder, target, progress);
            return true;
        };

        Task.spawn(function ()
        {
            yield Downloads.fetch(url.toString(), tmp).catch(log.error);
        })
        .then(_onFileDownloaded, _onFileDownloadFailed);
    };

    var _useZip = (zip, subfolder, target, progress) =>
    {
        var basename = koFile.basename(zip);
        progress.message("Unzipping " + basename + " ..");

        // Have Python take care of unzipping
        var koUtils = Cc["@activestate.com/koUtils;1"].getService(Ci.koIUtils);
        koUtils.unzip(zip, subfolder, target, function(status, message)
        {
            if (status !== 0)
            {
                progress.close();
                require("ko/dialogs").alert("Unzipping failed with message: " + message);
                return;
            }

            progress.message("Done");
            setTimeout(() => progress.close(), 1000);
        });
    };

    var _useFolder = (folder, target, progress) =>
    {
        var basename = koFile.basename(folder);
        progress.message("Copying " + basename + " .. ");

        // Copy files recursively
        var koUtils = Cc["@activestate.com/koUtils;1"].getService(Ci.koIUtils);
        koUtils.copytree(folder, target, function(status, message)
        {
            if (status !== 0)
            {
                progress.close();
                require("ko/dialogs").alert("Copying failed with message: " + message);
                return;
            }

            progress.message("Done");
            setTimeout(() => progress.close(), 1000);
        });
    };

}).apply(ko.projects);
