
/**
 * In browsers, the top-level scope is the global scope. That means that in
 * browsers if you&#39;re in the global scope var something will define a
 * global variable. In Node this is different. The top-level scope is not
 * the global scope; var something inside a Node module will be local to
 * that module.
 */
var global = {};

/**
 * Used to print to stdout and stderr. See the [console][] section.
 */
var console = {};

/**
 * The process object. See the [process object][] section.
 * @type {process}
 */
var process = {};

/**
 * To require modules. See the [Modules][] section. require isn&#39;t
 * actually a global but rather local to each module.
 */
require = function() {}

/**
 * Use the internal require() machinery to look up the location of a
 * module, but rather than loading the module, just return the resolved
 * filename.
 */
require.resolve = function() {}

/**
 * Modules are cached in this object when they are required. By deleting a
 * key value from this object, the next require will reload the module.
 */
require.cache = 0;

/**
 * Instruct require on how to handle certain file extensions.
 */
require.extensions = 0;

/**
 * The filename of the code being executed. This is the resolved absolute
 * path of this code file. For a main program this is not necessarily the
 * same filename used in the command line. The value inside a module is the
 * path to that module file.
 */
var __filename = {};

/**
 * Stop a timer that was previously created with setTimeout(). The callback
 * will not execute.
 * @param t
 */
clearTimeout = function(t) {}

/**
 * Stop a timer that was previously created with setInterval(). The
 * callback will not execute.
 */
clearInterval = function() {}

/**
 * A reference to the current module. In particular module.exports is used
 * for defining what a module exports and makes available through
 * require().
 */
var module = {};

/**
 * Run callback cb repeatedly every ms milliseconds. Note that the actual
 * interval may vary, depending on external factors like OS timer
 * granularity and system load. It&#39;s never less than ms but it may be
 * longer.
 * @param cb
 * @param ms
 */
setInterval = function(cb, ms) {}

/**
 * The name of the directory that the currently executing script resides
 * in.
 */
var __dirname = {};

/**
 * Run callback cb after at least ms milliseconds. The actual delay depends
 * on external factors like OS timer granularity and system load.
 * @param cb
 * @param ms
 */
setTimeout = function(cb, ms) {}

/**
 * Used to handle binary data. See the [buffer section][]
 */
var Buffer = {};

exports = global_objects;

