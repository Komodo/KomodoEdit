(function()
{
    var ioFile      = require("sdk/io/file");
    var mkCommon    = ko.moreKomodo.MoreKomodoCommon;

    this.basename = ioFile.basename;
    this.dirname = ioFile.dirname;
    this.exists = ioFile.exists;
    this.join = ioFile.join;
    this.list = ioFile.list;
    this.mkpath = ioFile.mkpath;
    this.open = ioFile.open;
    this.read = ioFile.read;
    this.remove = ioFile.remove;
    this.rmdir = ioFile.rmdir;
    this.isFile = ioFile.isFile;
    
    this.create = (path, name) =>
    {
        if (name) path = ioFile.join(path, name);
        
        if (ioFile.exists(path))
        {
            throw new Error("File already exists: " + ioFile.basename(path));
        }
        
        ioFile.open(path, "w").close();
        
        require("ko/dom")(window.parent).trigger("folder_touched", {path: ioFile.dirname(path)});
        
        return true;
    }

    this.rename = (path, newName = null) =>
    {
        if ( ! newName)
        {
            var oldName = ioFile.basename(path);
            newName = require("ko/dialogs").prompt("Renaming " + path,
            {
                label: "New Name: ",
                value: oldName
            });

            if ( ! newName) return;
        }

        return mkCommon.renameFile("file://" + path, newName, false);
    }

    this.copy = (path, toDirname = null) =>
    {
        return mkCommon.moveFile(path, toDirname, "copy");
    }

    this.move = (path, toDirname = null) =>
    {
        return mkCommon.moveFile(path, toDirname);
    }

}).apply(module.exports);
