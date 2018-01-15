/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Facilitates common file actions. It works slightly differently
 * than the mozilla io/file module which likes to throw exceptions when a simple
 * `return false` is more desirable (eg. calling basename on a path that doesn't exist)
 *
 * @module ko/file
 */
(function()
{
    var ioFile      = require("sdk/io/file");
    var system      = require("sdk/system");
    var { uuid }    = require('sdk/util/uuid');


    this.separator = system.platform == "winnt" ? "\\" : "/";

    /**
     * Returns the last component of the given path. For example, basename("/foo/bar/baz") returns "baz".
     * If the path has no components, the empty string is returned.
     *
     * @param {String} path - The file path
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
     * @param {String} path - The folder path
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
     * @param {String} path     The file path
     *
     * @returns {Boolean}
     */
    this.exists = function()
    {
        try
        {
            return ioFile.exists.apply(ioFile, arguments);
        }
        catch (e)
        {
            return false;
        }
    };

    this.isEmpty = function(path)
    {
        if ( ! this.exists(path) || this.isFile(path))
            return false;

        return this.list(path).length === 0;
    };

    /**
     * Takes a variable number of strings, joins them on the file system's path separator, and returns the result.
     *
     * @param {Strings} ... A variable number of strings to join. The first string must be an absolute path. eg. `join("foo","bar","baz") // foo\bar\baz`
     *
     * @returns {String}    A single string formed by joining the strings on the file system's path separator.
     */
    this.join = function()
    {
        var args = Array.from(arguments);
        var pathBits = [];
        for (let arg of args)
            pathBits = pathBits.concat(arg.split(/[\\\/]/g));

        return pathBits.join(this.separator);
    };

    /**
     * Returns an array of file names in the given directory.
     *
     * @param {String} path     The file path
     *
     * @returns {Array}
     */
    this.list = () => ioFile.list.apply(ioFile, arguments);

    /**
     * Makes a new directory named by the given path. Any subdirectories that do not exist are also created.
     * mkpath can be called multiple times on the same path.
     *
     * @param {String} path     The file path
     */
    this.mkpath = () => ioFile.mkpath.apply(ioFile, arguments);

    /**
     * Returns a stream providing access to the contents of a file.
     *
     * For more details see [https://developer.mozilla.org/en-US/Add-ons/SDK/Low-Level_APIs/io_file#open](https://developer.mozilla.org/en-US/Add-ons/SDK/Low-Level_APIs/io_file#open).
     *
     * @param {String} path - The file path
     * @param {String=} mode=r - The file mode, r|w|b
     *
     * @returns {Stream}
     */
    this.open = () => ioFile.open.apply(ioFile, arguments);

    /**
     * Open a temporary file with the given name as a seed,
     * the file is removed when the stream is closed
     *
     * @param   {String} name - The file path
     * @param {String=} mode=r - The file mode, r|w|b
     *
     * @returns {Stream}
     */
    this.openTemp = (name, mode, del = true) =>
    {
        var path = this.createTemp(name);
        var stream = this.open(path, mode);
        if (stream  && del)
        {
            stream.__close = stream.close;
            stream.close = () =>
            {
                stream.__close();
                this.remove(path);
            };
        }
        return stream;
    };

    /**
     * Opens a file and returns a string containing its entire contents.
     *
     * @param {String} path     The file path
     * @param {String} mode     Can be "b" to read in binary mode
     *
     * @returns {String}
     */
    this.read = () => ioFile.read.apply(ioFile, arguments);

    /**
     * Removes a file from the file system. To remove directories, use rmdir.
     *
     * @param {String} path     The file path
     */
    this.remove = () => ioFile.remove.apply(ioFile, arguments);

    /**
     * Removes a directory from the file system. If the directory is not empty, an exception is thrown.
     *
     * @param {String} path     The file path
     */
    this.rmdir = () => ioFile.rmdir.apply(ioFile, arguments);

    /**
     * Returns true only if this path specifies a file.
     *
     * @param {String} path     The file path
     */
    this.isFile = () =>
    {
        try
        {
            return ioFile.isFile.apply(ioFile, arguments);
        }
        catch (e)
        {
            return false;
        }
    };

    /**
     * Returns true only if this path specifies a directory.
     *
     * @param {String} path     The directory path
     */
    this.isDir = (path) =>
    {
        return this.exists(path) && ! this.isFile(path);
    };

    /**
     * Create a file at the given location (like `touch`)
     *
     * @param   {String} path       The path
     * @param   {String} name       The file name
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
     * Create a temporary file, this file is not automatically deleted by Komodo
     * ie. the deleting is handled by the OS/platform
     *
     * @param   {String} name
     *
     * @returns {String} path to temp file
     */
    this.createTemp = (name) =>
    {
        name = name.replace(/(?:\/|\\)/g, '');
        var tmpd = require('sdk/system').pathFor('TmpD');
        var path = this.join(tmpd, uuid() + name);
        this.create(path);
        return path;
    }

    /**
     * Rename the given file
     *
     * @param   {String} path           The file path
     * @param   {String} newName        The new file name
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

        var mkCommon = require("ko/windows").getMain().ko.moreKomodo.MoreKomodoCommon;
        var result = mkCommon.renameFile("file://" + path, newName, false);

        require("ko/dom")(window.parent).trigger("folder_touched", {path: path});

        return result;
    }

    /**
     * Copy the given file to the given directory
     *
     * @param   {String} path           The file path
     * @param   {String} toDirname      The target file path
     */
    this.copy = (path, toDirname = null) =>
    {
        var mkCommon = require("ko/windows").getMain().ko.moreKomodo.MoreKomodoCommon;
        var result =  mkCommon.moveFile(path, toDirname, "copy");

        require("ko/dom")(window.parent).trigger("folder_touched", {path: toDirname});

        return result;
    }

    /**
     * Move (cut/paste) the given file to the given directory
     *
     * @param   {String} path           The file path
     * @param   {String} toDirname      The target file path
     */
    this.move = (path, toDirname = null) =>
    {
        var mkCommon = require("ko/windows").getMain().ko.moreKomodo.MoreKomodoCommon;
        var result = mkCommon.moveFile(path, toDirname);

        require("ko/dom")(window.parent).trigger("folder_touched", {path: toDirname});
        require("ko/dom")(window.parent).trigger("folder_touched", {path: ioFile.dirname(path)});

        return result;
    }

}).apply(module.exports);
