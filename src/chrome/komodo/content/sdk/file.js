/**
 * @module file
 */
(function()
{
    var ioFile      = require("sdk/io/file");
    var mkCommon    = ko.moreKomodo.MoreKomodoCommon;

    var system      = require("sdk/system");
    
    this.separator = system.platform == "WINNT" ? "\\" : "/";

    /**
     * Returns the last component of the given path. For example, basename("/foo/bar/baz") returns "baz".
     * If the path has no components, the empty string is returned.
     *
     * @param {String} path
     *
     * @returns {String}
     */
    this.basename = function(path)
    {
        // Mozilla's version throws an exception if the path is not up to their standards ..
        return path.split(this.separator).pop();
    };
    
    /**
     * Returns the path of the directory containing the given file. If the file is at the top of the volume,
     * the empty string is returned.
     *
     * @param {String} path
     *
     * @returns {String}
     */
    this.dirname = function(path)
    {
        // Mozilla's version throws an exception if the path is not up to their standards ..
        path = path.split(this.separator);
        path.pop();
        return path.join(this.separator);
    };
    
    /**
     * Returns true if a file exists at the given path and false otherwise.
     *
     * @param {String} path
     *
     * @returns {Boolean}
     */
    this.exists = ioFile.exists;
    
    /**
     * Takes a variable number of strings, joins them on the file system's path separator, and returns the result.
     *
     * @param {Strings} ... A variable number of strings to join. The first string must be an absolute path.
     *
     * @returns {String}    A single string formed by joining the strings on the file system's path separator.
     */
    this.join = ioFile.join;
    
    /**
     * Returns an array of file names in the given directory.
     *
     * @param {String} path
     *
     * @returns {Array}
     */
    this.list = ioFile.list;
    
    /**
     * Makes a new directory named by the given path. Any subdirectories that do not exist are also created.
     * mkpath can be called multiple times on the same path.
     *
     * @param {String} path
     */
    this.mkpath = ioFile.mkpath;
    
    /**
     * Returns a stream providing access to the contents of a file.
     *
     * For more details see [https://developer.mozilla.org/en-US/Add-ons/SDK/Low-Level_APIs/io_file#open(path.2C_mode)]
     *
     * @param {String} path
     * @param {String} mode
     *
     * @returns {Stream}
     */
    this.open = ioFile.open;
    
    /**
     * Opens a file and returns a string containing its entire contents.
     *
     * @param {String} path
     * @param {String} mode     Can be "b" to read in binary mode
     *
     * @returns {String}
     */
    this.read = ioFile.read;
    
    /**
     * Removes a file from the file system. To remove directories, use rmdir.
     *
     * @param {String} path
     */
    this.remove = ioFile.remove;
    
    /**
     * Removes a directory from the file system. If the directory is not empty, an exception is thrown.
     *
     * @param {String} path
     */
    this.rmdir = ioFile.rmdir;
    
    /**
     * Returns true only if this path specifies a file.
     *
     * @param {String} path
     */
    this.isFile = ioFile.isFile;
    
    /**
     * Create a file at the given location (like `touch`)
     * 
     * @param   {String} path
     * @param   {String} name
     */
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

    /**
     * Rename the given file
     * 
     * @param   {String} path   
     * @param   {String} newName
     */
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

        var result = mkCommon.renameFile("file://" + path, newName, false);
    
        require("ko/dom")(window.parent).trigger("folder_touched", {path: path});
        
        return result;
    }

    /**
     * Copy the given file to the given directory
     * 
     * @param   {String} path     
     * @param   {String} toDirname
     */
    this.copy = (path, toDirname = null) =>
    {
        var result =  mkCommon.moveFile(path, toDirname, "copy");
    
        require("ko/dom")(window.parent).trigger("folder_touched", {path: toDirname});
        
        return result;
    }

    /**
     * Move (cut/paste) the given file to the given directory
     * 
     * @param   {String} path     
     * @param   {String} toDirname
     */
    this.move = (path, toDirname = null) =>
    {
        var result = mkCommon.moveFile(path, toDirname);
    
        require("ko/dom")(window.parent).trigger("folder_touched", {path: toDirname});
        require("ko/dom")(window.parent).trigger("folder_touched", {path: ioFile.dirname(path)});
        
        return result;
    }

}).apply(module.exports);
