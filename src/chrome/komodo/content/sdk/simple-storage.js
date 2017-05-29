/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState, Mozilla
 * @overview Based on the mozilla SDK simple-storage module
 */

const { Cc, Ci } = require("chrome");
const file = require("sdk/io/file");
const timer = require("sdk/timers");
const prefs = require("ko/prefs");
const ko = require("ko/windows").getMain().ko;

var global = window.global;

/**
 * simple-storage module which lets you store persistent data
 *
 * For storing preferences (user facing persistent data) use ko/prefs   
 *
 * @module ko/simple-storage
 */
(function() {
    
    if ( ! ("simpleStorage" in global))
        global.simpleStorage = {};

    var storages = global.simpleStorage;
    
    // A generic JSON store backed by a file on disk.  This should be isolated
    // enough to move to its own module if need be...
    function JsonStore(options)
    {
        this.filename = options.filename;
        this.writePeriod = options.writePeriod;
        this.writeTimer = timer.setInterval(this.write.bind(this), this.writePeriod);
    }

    JsonStore.prototype = {
        // The store's root.
        get root() {
            return this.isRootInitialized ? this._root : {};
        },

        // Performs some type checking.
        set root(val) {
            let types = ["array", "boolean", "null", "number", "object", "string"];
            if (types.indexOf(typeof(val)) < 0) {
                throw new Error("storage must be one of the following types: " +
                    types.join(", "));
            }
            this._root = val;
            return val;
        },

        // True if the root has ever been set (either via the root setter or by the
        // backing file's having been read).
        get isRootInitialized() {
            return this._root !== undefined;
        },

        // Removes the backing file and all empty subdirectories.
        purge: function JsonStore_purge() {
            try {
                // This'll throw if the file doesn't exist.
                file.remove(this.filename);
                this._root = {}
            } catch (err) {}
        },

        // Initializes the root by reading the backing file.
        read: function JsonStore_read() {
            try {
                let str = file.read(this.filename);

                this.root = JSON.parse(str);
            } catch (err) {
                this.root = {};
            }
        },

        // If the store is under quota, writes the root to the backing file.
        // Otherwise quota observers are notified and nothing is written.
        write: function JsonStore_write() {
            this._write();
        },

        // Cleans up on unload.  If unloading because of uninstall, the store is
        // purged; otherwise it's written.
        unload: function JsonStore_unload() {
            timer.clearInterval(this.writeTimer);
            this.writeTimer = null;

            this._write();
        },

        // True if the root is an empty object.
        get _isEmpty() {
            if (this.root && typeof(this.root) === "object") {
                let empty = true;
                for (let key in this.root) {
                    empty = false;
                    break;
                }
                return empty;
            }
            return false;
        },

        // Writes the root to the backing file, notifying write observers when
        // complete.  If the store is over quota or if it's empty and the store has
        // never been written, nothing is written and write observers aren't notified.
        _write: function JsonStore__write() {
            // Don't write if the root is uninitialized or if the store is empty and the
            // backing file doesn't yet exist.
            if (!this.isRootInitialized || (this._isEmpty && !file.exists(this.filename)))
                return;

            // Finally, write.
            let stream = file.open(this.filename, "w");
            try {
                stream.writeAsync(JSON.stringify(this.root), function writeAsync(err) {
                    if (err)
                        console.error("Error writing simple storage file: " + this.filename);
                }.bind(this));
            } catch (err) {
                // writeAsync closes the stream after it's done, so only close on error.
                stream.close();
            }
        }
    };
    
    /**
     * Get persistent data for the given name (will be created if it doesnt exist)
     *
     * Use the storage property to write and retrieve data.
     *
     * eg:
     * ```
     * var ss = require("ko/simple-storage").get("foo");
     * ss.storage.foobar = "foo";
     * ```
     * 
     * @param   {String} name 
     * 
     * @returns {Object} {storage: {}, filename: "...", jsonStore: {}}
     */
    this.get = function(name)
    {
        if (name in storages)
            return storages[name];
        
        storages[name] = {};
        var storage = storages[name];
        
        // Set filename
        let storeFile = Cc["@mozilla.org/file/directory_service;1"].
                        getService(Ci.nsIProperties).
                        get("ProfD", Ci.nsIFile);
        storeFile.append("simple-storage");
        file.mkpath(storeFile.path);
        storeFile.append(name + ".json");
        storage.filename = storeFile.path;
        
        storage.jsonStore = new JsonStore({
            filename: storage.filename,
            writePeriod: prefs.getLong("simple-storage.write.period", 300000),
        });
        
        Object.defineProperties(storages[name], {
            storage: {
                enumerable: true,
                get: function() {
                    if (!storage.jsonStore.isRootInitialized)
                        storage.jsonStore.read();
                    return storage.jsonStore.root;
                },
                set: function(value) {
                    storage.jsonStore.root = value;
                }
            }
        });
        
        return storages[name];
    };
    
    /**
     * Remove/purge all persistent data for the given name
     * 
     * @param   {String} name 
     * 
     * @returns {Void} 
     */
    this.remove = function(name)
    {
        this.get(name); // ensure it exists
        storages[name].jsonStore.purge();
        delete storages[name];
    };
    
    var onShutdown = function()
    {
        for (let k in storages)
        {
            storages[k].jsonStore.write();
        }
    };
    
    ko.main.addWillCloseHandler(onShutdown, this);
    
}).apply(module.exports);